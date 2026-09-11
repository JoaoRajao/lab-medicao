from __future__ import annotations

import json
import os
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover - optional TLS certificate helper
    certifi = None

from shared.dates import parse_datetime

GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubGraphQLClient:
    """Transporte GraphQL puro para a API do GitHub.

    Nao sabe nada sobre o "tema" de nenhum lab -- so autentica, envia a query
    recebida e trata retry em erro 5xx e espera de rate limit. Cada lab define
    suas proprias queries e como interpretar a resposta.
    """

    def __init__(self, token: str, timeout: int = 30) -> None:
        self.token = token
        self.timeout = timeout
        self.ssl_context = (
            ssl.create_default_context(cafile=certifi.where())
            if certifi is not None
            else ssl.create_default_context()
        )

    def execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = Request(
            GRAPHQL_URL,
            data=payload,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "lab-medicao-github-graphql-client",
            },
            method="POST",
        )

        while True:
            try:
                with urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                    raw = response.read().decode("utf-8")
            except HTTPError as error:
                raw = error.read().decode("utf-8", errors="replace")
                if 500 <= error.code < 600:
                    print(f"GitHub retornou HTTP {error.code}. Tentando novamente em 30s.")
                    time.sleep(30)
                    continue
                if error.code in {403, 429}:
                    wait_seconds = self._rate_limit_wait_seconds(error.headers, raw)
                    print(f"GitHub rate limit atingido. Aguardando {wait_seconds}s.")
                    time.sleep(wait_seconds)
                    continue
                raise RuntimeError(f"Erro HTTP {error.code} na API GraphQL: {raw}") from error
            except (TimeoutError, URLError) as error:
                print(f"Erro de rede na API GraphQL: {error}. Tentando novamente em 30s.")
                time.sleep(30)
                continue

            data = json.loads(raw)
            errors = data.get("errors", [])
            if errors and self._has_rate_limit_error(errors):
                reset_at = data.get("data", {}).get("rateLimit", {}).get("resetAt")
                wait_seconds = self._wait_seconds_from_reset_at(reset_at) if reset_at else 60
                print(f"GitHub rate limit atingido. Aguardando {wait_seconds}s.")
                time.sleep(wait_seconds)
                continue
            if errors:
                raise RuntimeError(f"Erro na query GraphQL: {errors}")
            return data["data"]

    @staticmethod
    def _has_rate_limit_error(errors: list[dict[str, Any]]) -> bool:
        return any("rate limit" in error.get("message", "").lower() for error in errors)

    @staticmethod
    def _rate_limit_wait_seconds(headers: Any, body: str) -> int:
        reset_header = headers.get("X-RateLimit-Reset")
        if reset_header:
            return max(int(reset_header) - int(time.time()) + 2, 1)

        try:
            data = json.loads(body)
            reset_at = data.get("data", {}).get("rateLimit", {}).get("resetAt")
        except json.JSONDecodeError:
            reset_at = None
        return GitHubGraphQLClient._wait_seconds_from_reset_at(reset_at) if reset_at else 60

    @staticmethod
    def _wait_seconds_from_reset_at(reset_at: str | None) -> int:
        if not reset_at:
            return 60
        reset_datetime = parse_datetime(reset_at)
        if reset_datetime is None:
            return 60
        return max(int((reset_datetime - datetime.now(timezone.utc)).total_seconds()) + 2, 1)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
