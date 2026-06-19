"""Tests for control_plane/c1_client.py.

All tests run offline via monkeypatched httpx; no real C1 tenant required.
Live cases are in tests/live/test_live_integrations.py.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from control_plane.c1_client import (
    C1ClientError,
    PolicyDecision,
    _build_client_assertion,
    _parse_client_secret,
    c1_configured,
    check_policy_c1,
    fetch_c1_token,
)
from control_plane.policy_check import check_policy


# ---------------------------------------------------------------------------
# Helpers: synthetic Ed25519 key + C1 secret
# ---------------------------------------------------------------------------

def _make_ed25519_private_key():
    """Return a fresh Ed25519 private key for test use only."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.generate()


def _make_c1_secret(private_key=None) -> tuple[str, object]:
    """Return a (secret_string, private_key) pair in C1's v1 format.

    Format: ``<prefix>:<kid>:v1:<base64url-JWK>``
    """
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    if private_key is None:
        private_key = _make_ed25519_private_key()

    private_bytes = private_key.private_bytes_raw()
    pub_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode(),
        "d": base64.urlsafe_b64encode(private_bytes).rstrip(b"=").decode(),
    }
    jwk_b64 = base64.urlsafe_b64encode(json.dumps(jwk).encode()).rstrip(b"=").decode()
    secret = f"smb-test:kid-test:v1:{jwk_b64}"
    return secret, private_key


# ---------------------------------------------------------------------------
# c1_configured
# ---------------------------------------------------------------------------

def test_c1_configured_false_when_no_env(monkeypatch):
    monkeypatch.delenv("C1_API_KEY", raising=False)
    monkeypatch.delenv("C1_BASE_URL", raising=False)
    assert c1_configured() is False


def test_c1_configured_false_when_only_key(monkeypatch):
    monkeypatch.setenv("C1_API_KEY", "somekey")
    monkeypatch.delenv("C1_BASE_URL", raising=False)
    assert c1_configured() is False


def test_c1_configured_true_when_both_set(monkeypatch):
    monkeypatch.setenv("C1_API_KEY", "somekey")
    monkeypatch.setenv("C1_BASE_URL", "https://test.conductor.one")
    assert c1_configured() is True


# ---------------------------------------------------------------------------
# _parse_client_secret
# ---------------------------------------------------------------------------

def test_parse_client_secret_valid():
    secret, _ = _make_c1_secret()
    key = _parse_client_secret(secret)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    assert isinstance(key, Ed25519PrivateKey)


def test_parse_client_secret_wrong_version():
    with pytest.raises(C1ClientError, match="v1"):
        _parse_client_secret("a:b:v2:xxxx")


def test_parse_client_secret_too_few_parts():
    with pytest.raises(C1ClientError):
        _parse_client_secret("not:enough")


def test_parse_client_secret_bad_jwk():
    bad_b64 = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
    with pytest.raises(C1ClientError):
        _parse_client_secret(f"a:b:v1:{bad_b64}")


# ---------------------------------------------------------------------------
# _build_client_assertion — shape and verifiability
# ---------------------------------------------------------------------------

def test_build_client_assertion_is_three_part_jwt():
    secret, private_key = _make_c1_secret()
    key = _parse_client_secret(secret)
    token = _build_client_assertion("test-client-id", key, "test.conductor.one")
    parts = token.split(".")
    assert len(parts) == 3, "JWT must have header.payload.signature"


def test_build_client_assertion_header_alg_eddsa():
    secret, _ = _make_c1_secret()
    key = _parse_client_secret(secret)
    token = _build_client_assertion("cid", key, "aud")
    header_bytes = base64.urlsafe_b64decode(token.split(".")[0] + "==")
    header = json.loads(header_bytes)
    assert header["alg"] == "EdDSA"


def test_build_client_assertion_payload_fields():
    secret, _ = _make_c1_secret()
    key = _parse_client_secret(secret)
    token = _build_client_assertion("my-cid", key, "my.conductor.one")
    payload_bytes = base64.urlsafe_b64decode(token.split(".")[1] + "==")
    payload = json.loads(payload_bytes)
    assert payload["iss"] == "my-cid"
    assert payload["sub"] == "my-cid"
    assert payload["aud"] == "my.conductor.one"
    assert "exp" in payload and "iat" in payload


# ---------------------------------------------------------------------------
# fetch_c1_token — monkeypatched httpx
# ---------------------------------------------------------------------------

def _mock_token_response(access_token="tok-abc", status=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = {"access_token": access_token, "token_type": "Bearer", "expires_in": 3600}
    mock_resp.text = json.dumps({"access_token": access_token})
    return mock_resp


def test_fetch_c1_token_sends_client_credentials_grant(monkeypatch):
    """Token request must include grant_type=client_credentials and a client_assertion."""
    secret, _ = _make_c1_secret()
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = dict(data or {})
        return _mock_token_response()

    monkeypatch.setattr("httpx.post", fake_post)
    monkeypatch.setenv("C1_API_SECRET", secret)

    fetch_c1_token("test-cid", secret, "https://test.conductor.one")

    assert captured["url"].endswith("auth/v1/token")
    assert captured["data"]["grant_type"] == "client_credentials"
    assert "client_assertion" in captured["data"]
    assert captured["data"]["client_assertion_type"] == (
        "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    )


def test_fetch_c1_token_returns_access_token(monkeypatch):
    secret, _ = _make_c1_secret()
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response("my-tok"))
    result = fetch_c1_token("cid", secret, "https://test.conductor.one")
    assert result == "my-tok"


def test_fetch_c1_token_raises_on_4xx(monkeypatch):
    secret, _ = _make_c1_secret()
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response(status=401))
    with pytest.raises(C1ClientError, match="401"):
        fetch_c1_token("cid", secret, "https://test.conductor.one")


def test_fetch_c1_token_raises_on_5xx(monkeypatch):
    secret, _ = _make_c1_secret()
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response(status=500))
    with pytest.raises(C1ClientError, match="500"):
        fetch_c1_token("cid", secret, "https://test.conductor.one")


def test_fetch_c1_token_raises_on_network_error(monkeypatch):
    secret, _ = _make_c1_secret()

    def bad_post(*a, **kw):
        raise httpx.ConnectError("refused")

    import httpx as _httpx
    monkeypatch.setattr("httpx.post", bad_post)
    with pytest.raises(C1ClientError):
        fetch_c1_token("cid", secret, "https://test.conductor.one")


def test_fetch_c1_token_raises_on_empty_access_token(monkeypatch):
    secret, _ = _make_c1_secret()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"token_type": "Bearer"}
    monkeypatch.setattr("httpx.post", lambda *a, **kw: resp)
    with pytest.raises(C1ClientError, match="access_token"):
        fetch_c1_token("cid", secret, "https://test.conductor.one")


# ---------------------------------------------------------------------------
# check_policy_c1 — grant endpoint shape + PolicyDecision mapping
# ---------------------------------------------------------------------------

def _setup_c1_env(monkeypatch, secret):
    """Set env vars needed by check_policy_c1."""
    monkeypatch.setenv("C1_API_KEY", "test-cid")
    monkeypatch.setenv("C1_API_SECRET", secret)
    monkeypatch.setenv("C1_BASE_URL", "https://test.conductor.one")
    monkeypatch.setenv("C1_VENDOR_APP_ID", "app-123")
    monkeypatch.setenv("C1_VENDOR_ENTITLEMENT_ID", "ent-456")


def _grant_resp(has_grant=True):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"list": [{"id": "g1"}] if has_grant else []}
    return mock_resp


def test_check_policy_c1_allowed_when_grant_exists(monkeypatch):
    secret, _ = _make_c1_secret()
    _setup_c1_env(monkeypatch, secret)
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())
    monkeypatch.setattr("httpx.get", lambda *a, **kw: _grant_resp(has_grant=True))

    result = check_policy_c1("AWS", 500.0, "user@example.com")

    assert isinstance(result, PolicyDecision)
    assert result.allowed is True
    assert "user@example.com" in result.reason or "ent-456" in result.reason


def test_check_policy_c1_denied_when_no_grant(monkeypatch):
    secret, _ = _make_c1_secret()
    _setup_c1_env(monkeypatch, secret)
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())
    monkeypatch.setattr("httpx.get", lambda *a, **kw: _grant_resp(has_grant=False))

    result = check_policy_c1("AWS", 500.0, "user@example.com")

    assert isinstance(result, PolicyDecision)
    assert result.allowed is False


def test_check_policy_c1_grant_url_includes_ids(monkeypatch):
    """GET request must include app_id, entitlement_id, user_id in the URL."""
    secret, _ = _make_c1_secret()
    _setup_c1_env(monkeypatch, secret)
    captured_get = {}

    def fake_get(url, headers=None, timeout=None):
        captured_get["url"] = url
        return _grant_resp(has_grant=True)

    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())
    monkeypatch.setattr("httpx.get", fake_get)

    check_policy_c1("AWS", 100.0, "alice")

    assert "app-123" in captured_get["url"]
    assert "ent-456" in captured_get["url"]
    assert "alice" in captured_get["url"]


def test_check_policy_c1_bearer_in_get_header(monkeypatch):
    """Authorization header must be 'Bearer <token>' on the grant request."""
    secret, _ = _make_c1_secret()
    _setup_c1_env(monkeypatch, secret)
    captured_headers = {}

    def fake_get(url, headers=None, timeout=None):
        captured_headers.update(headers or {})
        return _grant_resp(has_grant=True)

    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response("xyz-token"))
    monkeypatch.setattr("httpx.get", fake_get)

    check_policy_c1("AWS", 100.0, "alice")

    assert captured_headers.get("Authorization") == "Bearer xyz-token"


def test_check_policy_c1_raises_on_grant_4xx(monkeypatch):
    secret, _ = _make_c1_secret()
    _setup_c1_env(monkeypatch, secret)
    bad_resp = MagicMock()
    bad_resp.status_code = 403
    bad_resp.text = "Forbidden"

    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())
    monkeypatch.setattr("httpx.get", lambda *a, **kw: bad_resp)

    with pytest.raises(C1ClientError, match="403"):
        check_policy_c1("AWS", 100.0, "alice")


def test_check_policy_c1_no_app_id_uses_default_limit_allow(monkeypatch):
    secret, _ = _make_c1_secret()
    monkeypatch.setenv("C1_API_KEY", "cid")
    monkeypatch.setenv("C1_API_SECRET", secret)
    monkeypatch.setenv("C1_BASE_URL", "https://test.conductor.one")
    monkeypatch.delenv("C1_VENDOR_APP_ID", raising=False)
    monkeypatch.delenv("C1_VENDOR_ENTITLEMENT_ID", raising=False)
    monkeypatch.setenv("C1_DEFAULT_LIMIT", "1000")
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())

    result = check_policy_c1("Unknown", 500.0, "alice")
    assert result.allowed is True


def test_check_policy_c1_no_app_id_uses_default_limit_deny(monkeypatch):
    secret, _ = _make_c1_secret()
    monkeypatch.setenv("C1_API_KEY", "cid")
    monkeypatch.setenv("C1_API_SECRET", secret)
    monkeypatch.setenv("C1_BASE_URL", "https://test.conductor.one")
    monkeypatch.delenv("C1_VENDOR_APP_ID", raising=False)
    monkeypatch.delenv("C1_VENDOR_ENTITLEMENT_ID", raising=False)
    monkeypatch.setenv("C1_DEFAULT_LIMIT", "1000")
    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())

    result = check_policy_c1("Unknown", 2000.0, "alice")
    assert result.allowed is False


# ---------------------------------------------------------------------------
# policy_check.check_policy falls back to mock on C1ClientError
# ---------------------------------------------------------------------------

def test_policy_check_falls_back_to_mock_on_c1_error(monkeypatch):
    """check_policy must fall back to local YAML policy when C1 raises C1ClientError."""
    monkeypatch.setenv("C1_API_KEY", "test-key")

    def bad_post(*a, **kw):
        raise ConnectionError("C1 unreachable")

    monkeypatch.setattr("httpx.post", bad_post)
    # Adobe limit is 400 in policy_mock.yaml
    decision = check_policy("Adobe", 340.0)
    assert decision.allowed is True
    assert decision.limit == 400.0


def test_policy_check_falls_back_on_c1_error_denies_over_limit(monkeypatch):
    """Fallback still enforces local policy limits when C1 is unreachable."""
    monkeypatch.setenv("C1_API_KEY", "test-key")

    def bad_post(*a, **kw):
        raise ConnectionError("refused")

    monkeypatch.setattr("httpx.post", bad_post)
    decision = check_policy("Adobe", 500.0)
    assert decision.allowed is False
    assert decision.limit == 400.0


def test_policy_check_no_key_uses_mock(monkeypatch):
    """Without C1_API_KEY, check_policy never calls C1."""
    monkeypatch.delenv("C1_API_KEY", raising=False)
    decision = check_policy("Adobe", 340.0)
    assert decision.allowed is True


def test_policy_check_c1_result_propagated(monkeypatch):
    """When C1 succeeds, its PolicyDecision is returned, not the mock's."""
    secret, _ = _make_c1_secret()
    monkeypatch.setenv("C1_API_KEY", "test-cid")
    monkeypatch.setenv("C1_API_SECRET", secret)
    monkeypatch.setenv("C1_BASE_URL", "https://test.conductor.one")
    monkeypatch.setenv("C1_VENDOR_APP_ID", "app-x")
    monkeypatch.setenv("C1_VENDOR_ENTITLEMENT_ID", "ent-y")

    monkeypatch.setattr("httpx.post", lambda *a, **kw: _mock_token_response())
    monkeypatch.setattr("httpx.get", lambda *a, **kw: _grant_resp(has_grant=False))

    decision = check_policy("Adobe", 340.0, "alice")
    # C1 says no grant → denied, overriding the local "Adobe 340 allowed"
    assert decision.allowed is False
    assert "C1" in decision.reason
