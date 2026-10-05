from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover - optional TLS certificate helper
    certifi = None

API_URL = "https://api.github.com"
CACHED_STATUSES = {404, 410}
KEPT_HEADERS = ("link",)

# (url, headers, timeout) -> (status, headers em minusculas, corpo)
Transport = Callable[[str, dict[str, str], float], tuple[int, dict[str, str], bytes]]


class GitHubAPIError(RuntimeError):
    def __init__(self, status: int, url: str, body: str = "") -> None:
        super().__init__(f"HTTP {status} em {url}: {body[:300]}")
        self.status = status
        self.url = url
        self.body = body


class GitHubNotFoundError(GitHubAPIError):
    pass


@dataclass
class Response:
    status: int
    data: Any
    headers: dict[str, str] = field(default_factory=dict)
    from_cache: bool = False

    @property
    def links(self) -> dict[str, str]:
        return parse_link_header(self.headers.get("link"))


def parse_link_header(value: str | None) -> dict[str, str]:
    """Converte o cabecalho `Link` em {rel: url}."""
    links: dict[str, str] = {}
    for part in (value or "").split(","):
        match = re.search(r'<([^>]+)>\s*;\s*rel="([^"]+)"', part)
        if match:
            links[match.group(2)] = match.group(1)
    return links


def page_number(url: str | None) -> int | None:
    if not url:
        return None
    values = parse_qs(urlparse(url).query).get("page")
    return int(values[0]) if values else None


def build_url(path_or_url: str, params: dict[str, Any] | None = None) -> str:
    """URL absoluta e deterministica (parametros ordenados), usada tambem como chave de cache."""
    if path_or_url.startswith("http"):
        base = path_or_url
    else:
        base = API_URL + "/" + path_or_url.lstrip("/")
    if not params:
        return base
    separator = "&" if "?" in base else "?"
    return base + separator + urlencode(sorted((k, str(v)) for k, v in params.items()))


class ResponseCache:
    """Uma resposta da API por arquivo JSON, agrupada por repositorio e endpoint.

    Nunca grava o token: so status, corpo e o cabecalho `Link`.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path_for(self, url: str) -> Path:
        parsed = urlparse(url)
        segments = [re.sub(r"[^A-Za-z0-9._-]", "_", s) for s in parsed.path.split("/") if s][:4]
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return self.root.joinpath(*segments, f"{digest}.json")

    def get(self, url: str) -> dict[str, Any] | None:
        path = self.path_for(url)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def put(self, url: str, status: int, data: Any, headers: dict[str, str]) -> None:
        path = self.path_for(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "url": url,
            "status": status,
            "headers": {k: headers[k] for k in KEPT_HEADERS if k in headers},
            "data": data,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(record, file, ensure_ascii=False)
        os.replace(temporary, path)


def urllib_transport(ssl_context: ssl.SSLContext | None = None) -> Transport:
    context = ssl_context or (
        ssl.create_default_context(cafile=certifi.where()) if certifi is not None else ssl.create_default_context()
    )

    def send(url: str, headers: dict[str, str], timeout: float) -> tuple[int, dict[str, str], bytes]:
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
        except HTTPError as error:
            return error.code, {k.lower(): v for k, v in error.headers.items()}, error.read()

    return send


class GitHubRestClient:
    """Transporte REST para a API do GitHub com cache em disco, retomada, rate limit e backoff.

    Nao sabe nada sobre DORA: cada lab decide quais endpoints chamar.
    """

    def __init__(
        self,
        token: str,
        cache: ResponseCache | None = None,
        transport: Transport | None = None,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        timeout: float = 30,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        log: Callable[[str], None] = print,
    ) -> None:
        self._token = token
        self.cache = cache
        self.transport = transport or urllib_transport()
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.timeout = timeout
        self.sleep = sleep
        self.clock = clock
        self.log = log
        self.remaining: int | None = None
        self.reset_at: float | None = None
        self.requests_made = 0

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "lab-medicao-github-rest-client",
        }

    def get(self, path_or_url: str, params: dict[str, Any] | None = None, use_cache: bool = True) -> Response:
        url = build_url(path_or_url, params)
        if use_cache and self.cache is not None:
            cached = self.cache.get(url)
            if cached is not None:
                if cached["status"] in CACHED_STATUSES:
                    raise GitHubNotFoundError(cached["status"], url, "(cache)")
                return Response(cached["status"], cached["data"], cached.get("headers", {}), from_cache=True)

        attempt = 0
        rate_limit_waits = 0
        while True:
            self._wait_if_exhausted()
            try:
                status, headers, body = self.transport(url, self._headers(), self.timeout)
            except (URLError, TimeoutError, ConnectionError) as error:
                attempt = self._backoff_or_raise(attempt, url, 0, f"erro de rede: {error}")
                continue
            self.requests_made += 1
            self._update_rate_limit(headers)
            text = body.decode("utf-8", errors="replace")

            if 200 <= status < 300:
                data = json.loads(text) if text else None
                kept = {k: headers[k] for k in KEPT_HEADERS if k in headers}
                if use_cache and self.cache is not None:
                    self.cache.put(url, status, data, kept)
                return Response(status, data, kept)
            if status in (403, 429) and self._is_rate_limited(status, headers, text):
                rate_limit_waits += 1
                self.sleep(self._rate_limit_wait(headers, rate_limit_waits))
                continue
            if 500 <= status < 600:
                attempt = self._backoff_or_raise(attempt, url, status, text)
                continue
            if status in CACHED_STATUSES:
                if use_cache and self.cache is not None:
                    self.cache.put(url, status, None, {})
                raise GitHubNotFoundError(status, url, text)
            raise GitHubAPIError(status, url, text)

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        item_key: str | None = None,
        max_pages: int | None = None,
    ) -> Iterator[Any]:
        """Percorre todas as paginas seguindo `Link: rel="next"`."""
        base_params = {"per_page": 100, **(params or {})}
        url: str | None = build_url(path, base_params)
        pages = 0
        while url and (max_pages is None or pages < max_pages):
            response = self.get(url)
            items = response.data.get(item_key, []) if item_key else response.data
            yield from items or []
            pages += 1
            next_url = response.links.get("next")
            next_page = page_number(next_url)
            # O GitHub troca owner/repo pelo id numerico no link; manter a URL original
            # deixa todas as paginas no mesmo diretorio de cache.
            url = build_url(path, {**base_params, "page": next_page}) if next_page else next_url

    def rate_limit(self) -> dict[str, Any]:
        """`GET /rate_limit` nao consome cota e nunca e cacheado."""
        return self.get("/rate_limit", use_cache=False).data

    def _update_rate_limit(self, headers: dict[str, str]) -> None:
        if "x-ratelimit-remaining" in headers:
            self.remaining = int(headers["x-ratelimit-remaining"])
        if "x-ratelimit-reset" in headers:
            self.reset_at = float(headers["x-ratelimit-reset"])

    def _wait_if_exhausted(self) -> None:
        if self.remaining == 0 and self.reset_at is not None:
            wait = self.reset_at - self.clock() + 1
            if wait > 0:
                self.log(f"Cota da API esgotada. Aguardando {int(wait)}s ate a renovacao.")
                self.sleep(wait)
            self.remaining = None

    @staticmethod
    def _is_rate_limited(status: int, headers: dict[str, str], text: str) -> bool:
        if headers.get("x-ratelimit-remaining") == "0" or "retry-after" in headers:
            return True
        return status == 429 or "rate limit" in text.lower()

    def _rate_limit_wait(self, headers: dict[str, str], waits: int) -> float:
        if "retry-after" in headers:
            wait = float(headers["retry-after"])
        elif headers.get("x-ratelimit-remaining") == "0" and "x-ratelimit-reset" in headers:
            wait = float(headers["x-ratelimit-reset"]) - self.clock() + 1
        else:
            wait = 60 * 2 ** (waits - 1)
        wait = max(wait, 1)
        self.log(f"Rate limit atingido. Aguardando {int(wait)}s.")
        self.remaining = None
        return wait

    def _backoff_or_raise(self, attempt: int, url: str, status: int, detail: str) -> int:
        if attempt >= self.max_retries:
            raise GitHubAPIError(status, url, f"falhou apos {self.max_retries} novas tentativas: {detail}")
        wait = self.backoff_base * 2**attempt
        self.log(f"Falha temporaria ({detail[:80]}). Nova tentativa em {wait:g}s.")
        self.sleep(wait)
        return attempt + 1
