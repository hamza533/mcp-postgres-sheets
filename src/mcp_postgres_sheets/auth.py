"""OAuth 2.1 resource-server side: validate bearer JWTs from any OIDC provider.

The server never issues tokens (no built-in authorization server). It checks the signature
against the issuer's JWKS, then `iss`, `aud`, `exp`/`nbf`, and reads the granted scopes.

Scopes are read from `scope` (space-separated, RFC 9068 / Keycloak / Auth0), `scp` (Entra ID
delegated) and `roles` (Entra ID app-only). Entra ID cannot use ':' in scope names, so
`db.read` is accepted as an alias of `db:read` (same for the other two scopes).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken

log = logging.getLogger(__name__)

SCOPES = ("db:read", "sheets:read", "sheets:write")
_ALIASES = {s.replace(":", "."): s for s in SCOPES}
ALLOWED_ALGORITHMS = [
    "RS256",
    "RS384",
    "RS512",
    "PS256",
    "PS384",
    "PS512",
    "ES256",
    "ES384",
    "ES512",
]
LEEWAY_S = 30


def extract_scopes(claims: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for claim in ("scope", "scp", "roles"):
        value = claims.get(claim)
        if isinstance(value, str):
            found.extend(value.split())
        elif isinstance(value, list):
            found.extend(str(v) for v in value)
    normalised = [_ALIASES.get(s, s) for s in found]
    return list(dict.fromkeys(normalised))


async def discover_jwks_url(issuer: str, timeout_s: float = 5.0) -> str:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=False) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        jwks_uri = resp.json().get("jwks_uri")
    if not isinstance(jwks_uri, str) or not jwks_uri.startswith(("https://", "http://")):
        raise ValueError("OIDC discovery document has no jwks_uri")
    return jwks_uri


class JWTTokenVerifier:
    """`mcp.server.auth.provider.TokenVerifier` for JWT access tokens."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str | None = None,
        key_resolver: Callable[[str], Any] | None = None,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self._jwks_url = jwks_url
        self._jwks_client: PyJWKClient | None = None
        self._key_resolver = key_resolver  # tests inject a static key set here
        self._lock = asyncio.Lock()

    async def _resolve_key(self, token: str) -> Any:
        if self._key_resolver is not None:
            return self._key_resolver(token)
        if self._jwks_client is None:
            async with self._lock:
                if self._jwks_client is None:
                    url = self._jwks_url or await discover_jwks_url(self.issuer)
                    # Keys are cached for an hour; an unknown `kid` triggers one refetch (key rotation).
                    self._jwks_client = PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=5)
        client = self._jwks_client
        return (await asyncio.to_thread(client.get_signing_key_from_jwt, token)).key

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in ALLOWED_ALGORITHMS:
                log.info("rejected token: algorithm %s not allowed", header.get("alg"))
                return None
            key = await self._resolve_key(token)
            claims: dict[str, Any] = jwt.decode(
                token,
                key=key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                leeway=LEEWAY_S,
                options={"require": ["exp", "iss", "aud"], "verify_signature": True},
            )
        except jwt.PyJWTError as exc:
            log.info("rejected token: %s", type(exc).__name__)
            return None
        except (httpx.HTTPError, ValueError, OSError) as exc:
            log.warning(
                "could not fetch signing keys from the identity provider: %s", type(exc).__name__
            )
            return None

        aud = claims.get("aud")
        resource = (
            self.audience
            if (aud == self.audience or (isinstance(aud, list) and self.audience in aud))
            else None
        )
        client_id = claims.get("azp") or claims.get("client_id") or claims.get("appid") or "unknown"
        exp = claims.get("exp")
        return AccessToken(
            token=token,
            client_id=str(client_id),
            scopes=extract_scopes(claims),
            expires_at=int(exp) if isinstance(exp, int | float) else None,
            resource=resource,
            subject=str(claims["sub"]) if claims.get("sub") else None,
            claims={"iss": claims.get("iss"), "iat": claims.get("iat", int(time.time()))},
        )
