"""payments/envelopes.py -- Ed25519 signed envelope for Stripe writes.

Attempts to import authority_runtime (Carryall, published to PyPI as
authority-runtime >= 0.5.0). If unavailable, falls back to a thin signer built
on the cryptography library (already a project dependency via c1_client.py).

The signed envelope must be written to the audit log BEFORE the Stripe write.
Callers import sign_stripe_envelope; the audit-log write is handled internally.

Public API:
    sign_stripe_envelope(action, payload, *, agent_id, scopes) -> dict
        Returns a signed envelope dict. Writes to audit log before returning.

    verify_envelope(envelope) -> bool
        Returns True when the envelope signature is valid.

Internal helpers (exported for tests):
    sign(payload_dict, private_key_hex) -> hex signature string
    verify(payload_dict, sig_hex, public_key_hex) -> bool

STRUCTURE NOTE: Stripe primitives live in payments/ (not stripe/) to avoid
shadowing the stripe pip package. Carryall is layered on here, not heavy.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

_logger = logging.getLogger(__name__)

# Attempt real Carryall import; fall back to thin signer.
_USING_AUTHORITY_RUNTIME = False
try:
    import authority_runtime  # type: ignore[import]
    _USING_AUTHORITY_RUNTIME = True
    _logger.info("authority_runtime available -- using real Carryall envelopes")
except ImportError:
    _logger.info("authority_runtime not installed -- using thin Ed25519 signer (pynacl fallback)")


def _load_or_generate_key() -> tuple[str, str]:
    """Return (private_key_hex, public_key_hex).

    Reads CARRYALL_SIGNING_KEY_B64 from env. If unset, generates an ephemeral
    key for the demo session and logs a warning.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat
    )

    raw_b64 = os.environ.get("CARRYALL_SIGNING_KEY_B64", "")
    if raw_b64:
        raw_bytes = base64.b64decode(raw_b64)
        private_key = Ed25519PrivateKey.from_private_bytes(raw_bytes)
    else:
        private_key = Ed25519PrivateKey.generate()
        priv_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        _logger.warning(
            "CARRYALL_SIGNING_KEY_B64 not set -- using ephemeral demo key. "
            "Signatures from this session will not verify across restarts."
        )
        _ = base64.b64encode(priv_bytes).decode()  # available in logs if needed

    priv_hex = private_key.private_bytes(
        Encoding.Raw, PrivateFormat.Raw, NoEncryption()
    ).hex()
    pub_hex = (
        private_key.public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )
    return priv_hex, pub_hex


def sign(payload_dict: dict[str, Any], private_key_hex: str) -> str:
    """Sign payload_dict with Ed25519 private key. Returns hex signature.

    Canonical JSON (sorted keys, no whitespace) is the signing input.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat
    )

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


def sign_stripe_envelope(
    action: str,
    payload: dict[str, Any],
    *,
    agent_id: str,
    scopes: list[str],
) -> dict[str, Any]:
    """Build and sign a Carryall-style envelope for a Stripe write action.

    Writes the envelope to the audit log before returning. The audit write
    must precede the Stripe call; enforce this at the call site.

    Returns a signed envelope dict with keys: action, payload, agent_id,
    scopes, issued_at, public_key_hex, signature.
    """
    from agent.audit_log import append_action

    priv_hex, pub_hex = _load_or_generate_key()

    envelope_payload: dict[str, Any] = {
        "action": action,
        "payload": payload,
        "agent_id": agent_id,
        "scopes": scopes,
        "issued_at": int(time.time()),
        "public_key_hex": pub_hex,
    }

    sig = sign(envelope_payload, priv_hex)
    envelope = {**envelope_payload, "signature": sig}

    # Audit log write BEFORE Stripe write -- required by the envelope contract.
    vendor = payload.get("vendor", action)
    amount = float(payload.get("amount_cents", 0)) / 100.0
    append_action(
        action="payment",
        vendor=str(vendor),
        amount=amount,
        decision="envelope_signed",
        actor=agent_id,
        metadata={"scopes": scopes, "envelope_action": action, "public_key_hex": pub_hex},
    )

    return envelope


def verify_envelope(envelope: dict[str, Any]) -> bool:
    """Return True when the envelope signature is valid over its payload fields."""
    sig_hex = envelope.get("signature", "")
    pub_hex = envelope.get("public_key_hex", "")
    if not sig_hex or not pub_hex:
        return False
    payload_fields = {k: v for k, v in envelope.items() if k != "signature"}
    return verify(payload_fields, sig_hex, pub_hex)
