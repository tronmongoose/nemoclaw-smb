"""payments/envelopes.py: Ed25519 signed envelope for Stripe writes.

When authority_runtime (Erik's Carryall, published to PyPI as authority-runtime
>= 0.5.0) is importable, sign_stripe_envelope builds a REAL Carryall envelope via
authority_runtime.create_simple_envelope (Ed25519) and verify_envelope checks it
via authority_runtime.verify_signature. If the package is absent, both fall back
to a thin signer built on the cryptography library (already a project dependency).

Either way the public contract is unchanged:
    sign_stripe_envelope(action, payload, *, agent_id, scopes) -> dict
        Returns a signed envelope dict carrying agent_id, signature, and
        public_key_hex. Writes to the audit log before returning.

    verify_envelope(envelope) -> bool
        Returns True when the envelope signature is valid; tamper -> False.

Internal helpers (exported for tests, always the thin path):
    sign(payload_dict, private_key_hex) -> hex signature string
    verify(payload_dict, sig_hex, public_key_hex) -> bool

The signed envelope must be written to the audit log BEFORE the Stripe write.
Callers import sign_stripe_envelope; the audit-log write is handled internally.

STRUCTURE NOTE: Stripe primitives live in payments/ (not stripe/) to avoid
shadowing the stripe pip package. Carryall is layered on here, not heavy.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from typing import Any

_logger = logging.getLogger(__name__)

# Prefix for the payload-binding entry written into the real envelope's signed
# resources list, so the Ed25519 signature covers the business payload too.
_PAYLOAD_RESOURCE_PREFIX = "payload-sha256:"

# Attempt real Carryall import; fall back to thin signer.
_USING_AUTHORITY_RUNTIME = False
try:
    import authority_runtime  # type: ignore[import]

    _USING_AUTHORITY_RUNTIME = True
    _logger.info("authority_runtime available: using real Carryall envelopes")
except ImportError:
    _logger.info(
        "authority_runtime not installed: using thin Ed25519 signer (cryptography fallback)"
    )


def _load_or_generate_key() -> tuple[str, str]:
    """Return (private_key_hex, public_key_hex).

    Reads CARRYALL_SIGNING_KEY_B64 from env. If unset, generates an ephemeral
    key for the demo session and logs a warning.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
        PublicFormat,
    )

    raw_b64 = os.environ.get("CARRYALL_SIGNING_KEY_B64", "")
    if raw_b64:
        raw_bytes = base64.b64decode(raw_b64)
        private_key = Ed25519PrivateKey.from_private_bytes(raw_bytes)
    else:
        private_key = Ed25519PrivateKey.generate()
        priv_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        _logger.warning(
            "CARRYALL_SIGNING_KEY_B64 not set: using ephemeral demo key. "
            "Signatures from this session will not verify across restarts."
        )
        _ = base64.b64encode(priv_bytes).decode()  # available in logs if needed

    priv_hex = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    ).hex()
    pub_hex = (
        private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    )
    return priv_hex, pub_hex


def _payload_hash(payload: dict[str, Any]) -> str:
    """Return a sha256 hex digest over the canonical-JSON business payload."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def sign(payload_dict: dict[str, Any], private_key_hex: str) -> str:
    """Sign payload_dict with Ed25519 private key. Returns hex signature.

    Canonical JSON (sorted keys, no whitespace) is the signing input.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv_bytes = bytes.fromhex(private_key_hex)
    private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
    canonical = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode()
    sig = private_key.sign(canonical)
    return sig.hex()


def verify(payload_dict: dict[str, Any], sig_hex: str, public_key_hex: str) -> bool:
    """Verify an Ed25519 signature over payload_dict. Returns True on valid sig."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
        canonical = json.dumps(
            payload_dict, sort_keys=True, separators=(",", ":")
        ).encode()
        public_key.verify(bytes.fromhex(sig_hex), canonical)
        return True
    except (InvalidSignature, Exception):  # noqa: BLE001
        return False


def _sign_with_authority_runtime(
    action: str,
    payload: dict[str, Any],
    agent_id: str,
    scopes: list[str],
) -> dict[str, Any]:
    """Build a real Carryall envelope and return it as a flat-augmented dict.

    The returned dict is the serialized AuthorityEnvelope (top-level agent_id +
    signature) with the public contract's extra flat fields layered on. The
    business payload is bound into the envelope's signed resources list as a
    sha256 hash, so the Ed25519 signature covers it; tampering the flat payload
    is then detected at verify time.
    """
    priv_hex, pub_hex = authority_runtime.generate_key_pair()
    real_env = authority_runtime.create_simple_envelope(
        agent_id=agent_id,
        scopes=scopes,
        private_key=priv_hex,
        skill_name=action,
        resources=[_PAYLOAD_RESOURCE_PREFIX + _payload_hash(payload)],
        root_policy_id=action,
    )
    serialized = real_env.model_dump(mode="json")
    return {
        **serialized,
        "action": action,
        "payload": payload,
        "scopes": scopes,
        "issued_at": int(time.time()),
        "public_key_hex": pub_hex,
        "envelope_source": "authority-runtime",
    }


def _sign_thin(
    action: str,
    payload: dict[str, Any],
    agent_id: str,
    scopes: list[str],
) -> dict[str, Any]:
    """Build the thin cryptography-library envelope (fallback path)."""
    priv_hex, pub_hex = _load_or_generate_key()
    envelope_payload: dict[str, Any] = {
        "action": action,
        "payload": payload,
        "agent_id": agent_id,
        "scopes": scopes,
        "issued_at": int(time.time()),
        "public_key_hex": pub_hex,
        "envelope_source": "thin-ed25519",
    }
    sig = sign(envelope_payload, priv_hex)
    return {**envelope_payload, "signature": sig}


def sign_stripe_envelope(
    action: str,
    payload: dict[str, Any],
    *,
    agent_id: str,
    scopes: list[str],
) -> dict[str, Any]:
    """Build and sign a Carryall envelope for a Stripe write action.

    Uses the real authority_runtime envelope when importable (and scopes are
    non-empty, which authority_runtime requires); otherwise the thin signer.
    Writes the envelope to the audit log before returning. The audit write must
    precede the Stripe call; enforce this at the call site.

    Returns a signed envelope dict with at least: agent_id, action, payload,
    scopes, issued_at, public_key_hex, signature.
    """
    if _USING_AUTHORITY_RUNTIME and scopes:
        try:
            envelope = _sign_with_authority_runtime(action, payload, agent_id, scopes)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "authority_runtime envelope build failed (%s); falling back to thin signer",
                exc,
            )
            envelope = _sign_thin(action, payload, agent_id, scopes)
    else:
        envelope = _sign_thin(action, payload, agent_id, scopes)

    _audit_envelope(action, payload, agent_id, scopes, envelope)
    return envelope


def _audit_envelope(
    action: str,
    payload: dict[str, Any],
    agent_id: str,
    scopes: list[str],
    envelope: dict[str, Any],
) -> None:
    """Write the signed envelope to the audit log before the Stripe write."""
    from agent.audit_log import append_action

    append_action(
        action="payment",
        vendor=str(payload.get("vendor", action)),
        amount=float(payload.get("amount_cents", 0)) / 100.0,
        decision="envelope_signed",
        actor=agent_id,
        metadata={
            "scopes": scopes,
            "envelope_action": action,
            "public_key_hex": envelope.get("public_key_hex", ""),
            "envelope_source": envelope.get("envelope_source", "thin-ed25519"),
        },
    )


def _verify_with_authority_runtime(envelope: dict[str, Any], pub_hex: str) -> bool:
    """Reconstruct the AuthorityEnvelope and verify its signature + payload binding.

    The signature covers agent_id, scopes, and the signed resources list. The
    flat payload is re-hashed and matched against the payload-binding resource so
    a tampered flat payload is rejected even though it sits outside the model.
    """
    from authority_runtime.types import AuthorityEnvelope

    try:
        real_env = AuthorityEnvelope.model_validate(envelope)
        if not authority_runtime.verify_signature(real_env, pub_hex):
            return False
        if envelope.get("scopes") is not None and (
            list(envelope["scopes"]) != list(real_env.authority.scopes)
        ):
            return False
        expected = _PAYLOAD_RESOURCE_PREFIX + _payload_hash(envelope.get("payload", {}))
        return expected in (real_env.authority.resources or [])
    except Exception:  # noqa: BLE001
        return False


def verify_envelope(envelope: dict[str, Any]) -> bool:
    """Return True when the envelope signature is valid over its payload fields.

    Routes to authority_runtime.verify_signature for envelopes produced by the
    real path (envelope_source == 'authority-runtime'); otherwise verifies the
    thin canonical-JSON signature. Tamper of any signed field returns False.
    """
    sig_hex = envelope.get("signature", "")
    pub_hex = envelope.get("public_key_hex", "")
    if not sig_hex or not pub_hex:
        return False

    if envelope.get("envelope_source") == "authority-runtime" and _USING_AUTHORITY_RUNTIME:
        return _verify_with_authority_runtime(envelope, pub_hex)

    payload_fields = {k: v for k, v in envelope.items() if k != "signature"}
    return verify(payload_fields, sig_hex, pub_hex)
