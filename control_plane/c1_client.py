"""ConductorOne API client for NemoClaw SMB policy checks.

Public surface:
    c1_configured() -> bool
    fetch_c1_token(client_id, client_secret, base_url) -> str
    check_policy_c1(vendor, amount, requester) -> PolicyDecision

Auth: OAuth2 client_credentials with Ed25519 JWT bearer assertion.
Token endpoint: POST https://{tenant}.conductor.one/auth/v1/token
Spec source: https://github.com/ConductorOne/conductorone-sdk-go/blob/main/token_source.go
             https://github.com/ConductorOne/conductorone-sdk-go/blob/main/extra_sdk_options.go

FIREWALL: This client is wired to synthetic SMB test data only.
Never point C1_BASE_URL at a real work-tenant or production C1 environment
that contains actual employee/identity data (PANW/C1 firewall, user-level CLAUDE.md rule #3).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

_logger = logging.getLogger(__name__)

_TOKEN_PATH = "auth/v1/token"
_GRANT_CHECK_PATH = "/api/v1/apps/{app_id}/entitlements/{entitlement_id}/users/{user_id}/grants"
_CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
_DEFAULT_TIMEOUT = 10.0


class C1ClientError(Exception):
    """Raised on any C1 API failure so callers can fall back gracefully."""


@dataclass
class PolicyDecision:
    """Result of a single policy evaluation — mirrors control_plane.policy_check.PolicyDecision."""

    allowed: bool
    reason: str
    limit: float | None


def c1_configured() -> bool:
    """Return True when the required C1 environment variables are present."""
    return bool(os.environ.get("C1_API_KEY")) and bool(os.environ.get("C1_BASE_URL"))


def _parse_client_secret(raw: str) -> Any:
    """Decode a C1 versioned client secret into an Ed25519 private key.

    C1 secret format: ``<prefix>:<kid>:v1:<base64url-JWK>``
    Spec: https://github.com/ConductorOne/conductorone-sdk-go/blob/main/token_source.go
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    parts = raw.split(":")
    if len(parts) != 4 or parts[2] != "v1":
        raise C1ClientError("C1_API_KEY is not a valid v1 client secret")

    try:
        jwk_bytes = base64.urlsafe_b64decode(parts[3] + "==")
        jwk = json.loads(jwk_bytes)
    except Exception as exc:
        raise C1ClientError(f"Failed to decode C1 client secret JWK: {exc}") from exc

    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519":
        raise C1ClientError("C1 client secret JWK is not an Ed25519 key")

    try:
        d_bytes = base64.urlsafe_b64decode(jwk["d"] + "==")
        return Ed25519PrivateKey.from_private_bytes(d_bytes)
    except Exception as exc:
        raise C1ClientError(f"Failed to load Ed25519 private key: {exc}") from exc


def _build_client_assertion(client_id: str, private_key: Any, audience: str) -> str:
    """Build a signed Ed25519 JWT for the client_credentials assertion.

    Spec: https://github.com/ConductorOne/conductorone-sdk-go/blob/main/token_source.go
    """
    import base64 as _b64

    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    now = int(time.time())
    header = {"alg": "EdDSA", "typ": "JWT"}
    payload = {
        "iss": client_id,
        "sub": client_id,
        "aud": audience,
        "iat": now,
        "nbf": now - 120,
        "exp": now + 120,
    }

    def _b64url(data: bytes) -> str:
        return _b64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header_enc = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_enc = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_enc}.{payload_enc}".encode()

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed

    if not isinstance(private_key, _Ed):
        raise C1ClientError("Expected Ed25519PrivateKey for JWT signing")

    sig = private_key.sign(signing_input)
    return f"{header_enc}.{payload_enc}.{_b64url(sig)}"


def fetch_c1_token(client_id: str, client_secret: str, base_url: str) -> str:
    """Exchange C1 client credentials for a short-lived bearer token.

    Returns the raw access_token string.
    Raises C1ClientError on any failure.
    """
    token_url = base_url.rstrip("/") + "/" + _TOKEN_PATH
    audience = base_url.rstrip("/").removeprefix("https://")

    try:
        private_key = _parse_client_secret(client_secret)
        assertion = _build_client_assertion(client_id, private_key, audience)
    except C1ClientError:
        raise
    except Exception as exc:
        raise C1ClientError(f"Failed to build C1 client assertion: {exc}") from exc

    body = {
        "client_id": client_id,
        "grant_type": "client_credentials",
        "client_assertion_type": _CLIENT_ASSERTION_TYPE,
        "client_assertion": assertion,
    }

    try:
        resp = httpx.post(token_url, data=body, timeout=_DEFAULT_TIMEOUT)
    except Exception as exc:
        raise C1ClientError(f"C1 token request failed: {exc}") from exc

    if resp.status_code != 200:
        raise C1ClientError(
            f"C1 token endpoint returned {resp.status_code}: {resp.text[:200]}"
        )

    try:
        token_data = resp.json()
    except Exception as exc:
        raise C1ClientError(f"C1 token response is not JSON: {exc}") from exc

    access_token = token_data.get("access_token", "")
    if not access_token:
        raise C1ClientError("C1 token response missing access_token")

    return access_token


def _entitlement_has_grant(
    bearer: str, base_url: str, app_id: str, entitlement_id: str, user_id: str
) -> bool:
    """Return True if user_id holds an active grant for the named entitlement.

    Endpoint: GET /api/v1/apps/{app_id}/entitlements/{entitlement_id}/users/{user_id}/grants
    Spec: https://github.com/ConductorOne/conductorone-sdk-python/blob/main/src/conductorone_sdk/appentitlementuserbinding.py
    #COMPLETION_DRIVE: response shape assumed; verify grant list field name against a live tenant.
    #SUGGEST_VERIFY: curl the grants endpoint with a known user/entitlement pair and log resp JSON.
    """
    path = _GRANT_CHECK_PATH.format(
        app_id=app_id, entitlement_id=entitlement_id, user_id=user_id
    )
    url = base_url.rstrip("/") + path
    headers = {"Authorization": f"Bearer {bearer}", "Accept": "application/json"}

    try:
        resp = httpx.get(url, headers=headers, timeout=_DEFAULT_TIMEOUT)
    except Exception as exc:
        raise C1ClientError(f"C1 grant-check request failed: {exc}") from exc

    if resp.status_code == 404:
        return False
    if resp.status_code != 200:
        raise C1ClientError(
            f"C1 grant-check returned {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data = resp.json()
    except Exception as exc:
        raise C1ClientError(f"C1 grant-check response is not JSON: {exc}") from exc

    grants = data.get("list", []) or data.get("grants", [])  # #COMPLETION_DRIVE: field name TBD
    return len(grants) > 0


def check_policy_c1(vendor: str, amount: float, requester: str) -> PolicyDecision:
    """Check whether ``requester`` may spend ``amount`` on ``vendor`` via C1.

    Maps the spend-authorization concept to C1 entitlement grants:
    - C1_VENDOR_APP_ID: the C1 app representing the vendor spend category
    - C1_VENDOR_ENTITLEMENT_ID: the entitlement that grants spend authorization

    Both env vars are optional; when absent the function approves unknown vendors
    up to the amount threshold defined by C1_DEFAULT_LIMIT (default 1000), which
    mirrors the local mock policy behavior so tests stay predictable.

    #COMPLETION_DRIVE: The vendor→app_id+entitlement_id mapping is a simplification.
    A production deployment would maintain a vendor catalog in C1 and look up app/
    entitlement IDs by vendor name. Verify the grant response field names against
    a real tenant before removing the #COMPLETION_DRIVE tag.
    #SUGGEST_VERIFY: deploy a test C1 tenant, create one app + entitlement, grant
    to a test user, then run check_policy_c1 with that user to confirm allowed=True.

    Raises C1ClientError on any network/auth/shape failure so the caller falls back.
    """
    client_id = os.environ.get("C1_API_KEY", "")
    client_secret = os.environ.get("C1_API_SECRET", "")
    base_url = os.environ.get("C1_BASE_URL", "")
    app_id = os.environ.get("C1_VENDOR_APP_ID", "")
    entitlement_id = os.environ.get("C1_VENDOR_ENTITLEMENT_ID", "")
    default_limit = float(os.environ.get("C1_DEFAULT_LIMIT", "1000"))

    if not base_url:
        raise C1ClientError("C1_BASE_URL is required for C1 policy checks")

    bearer = fetch_c1_token(client_id, client_secret, base_url)

    if not app_id or not entitlement_id:
        _logger.warning(
            "C1_VENDOR_APP_ID or C1_VENDOR_ENTITLEMENT_ID not set; "
            "falling back to amount-only check against default limit %.2f",
            default_limit,
        )
        if amount <= default_limit:
            return PolicyDecision(
                allowed=True,
                reason=f"C1: {vendor} approved by default limit ${default_limit}",
                limit=default_limit,
            )
        return PolicyDecision(
            allowed=False,
            reason=f"C1: {vendor} denied — ${amount} exceeds default limit ${default_limit}",
            limit=default_limit,
        )

    has_grant = _entitlement_has_grant(bearer, base_url, app_id, entitlement_id, requester)

    if has_grant:
        return PolicyDecision(
            allowed=True,
            reason=f"C1: {requester} holds an active grant for {vendor} (entitlement {entitlement_id})",
            limit=None,
        )
    return PolicyDecision(
        allowed=False,
        reason=f"C1: {requester} has no active grant for {vendor} (entitlement {entitlement_id})",
        limit=None,
    )
