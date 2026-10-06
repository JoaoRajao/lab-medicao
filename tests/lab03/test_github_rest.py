from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from shared.github_rest import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRestClient,
    ResponseCache,
    build_url,
    page_number,
    parse_link_header,
)

TOKEN = "ghp_segredo_de_teste"


class FakeTransport:
    """Responde a partir de uma fila por URL e registra cada chamada."""

    def __init__(self, routes: dict[str, list]) -> None:
        self.routes = {url: list(responses) for url, responses in routes.items()}
        self.calls: list[str] = []
        self.headers_seen: list[dict[str, str]] = []

    def __call__(self, url, headers, timeout):
        self.calls.append(url)
        self.headers_seen.append(headers)
        outcome = self.routes[url].pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        status, body, extra = outcome
        return status, extra, json.dumps(body).encode("utf-8")


class FakeClock:
    def __init__(self, start: float = 1_000_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(transport, cache=None, clock=None, **kwargs):
    clock = clock or FakeClock()
    return GitHubRestClient(
        TOKEN, cache=cache, transport=transport, sleep=clock.sleep, clock=clock.time, log=lambda _: None, **kwargs
    )


def page_url(page: int) -> str:
    return build_url("/repos/o/r/releases", {"per_page": 100, "page": page} if page > 1 else {"per_page": 100})


def paged_routes(pages: int = 3) -> dict[str, list]:
    routes = {}
    for page in range(1, pages + 1):
        headers = {"link": f'<{page_url(page + 1)}>; rel="next"'} if page < pages else {}
        routes[page_url(page)] = [(200, [{"id": page * 10 + i} for i in range(2)], headers)]
    return routes


def test_build_url_is_deterministic_and_accepts_absolute_urls():
    assert build_url("/repos/o/r", {"b": 2, "a": 1}) == build_url("repos/o/r", {"a": 1, "b": 2})
    assert build_url("https://api.github.com/x?page=2") == "https://api.github.com/x?page=2"
    assert build_url("/x?y=1", {"z": 2}) == "https://api.github.com/x?y=1&z=2"


def test_parse_link_header_and_page_number():
    header = '<https://api.github.com/x?page=2>; rel="next", <https://api.github.com/x?page=9>; rel="last"'
    links = parse_link_header(header)
    assert links["next"].endswith("page=2")
    assert page_number(links["last"]) == 9
    assert parse_link_header(None) == {}
    assert page_number(None) is None
    assert page_number("https://api.github.com/x") is None


def test_paginate_follows_link_header_until_the_end():
    transport = FakeTransport(paged_routes(3))
    client = make_client(transport)

    ids = [item["id"] for item in client.paginate("/repos/o/r/releases")]

    assert ids == [10, 11, 20, 21, 30, 31]
    assert len(transport.calls) == 3


def test_paginate_reads_items_from_key_and_respects_max_pages():
    url = build_url("/search/repositories", {"per_page": 100, "q": "stars:>1000"})
    nxt = build_url("/search/repositories", {"per_page": 100, "q": "stars:>1000", "page": 2})
    transport = FakeTransport({url: [(200, {"total_count": 4, "items": [{"id": 1}, {"id": 2}]}, {"link": f'<{nxt}>; rel="next"'})]})

    items = list(make_client(transport).paginate("/search/repositories", {"q": "stars:>1000"}, item_key="items", max_pages=1))

    assert [i["id"] for i in items] == [1, 2]
    assert transport.calls == [url]


def test_next_pages_keep_the_original_path_even_when_link_uses_repository_id():
    first = page_url(1)
    by_id = "https://api.github.com/repositories/123/releases?per_page=100&page=2"
    transport = FakeTransport({
        first: [(200, [{"id": 1}], {"link": f'<{by_id}>; rel="next"'})],
        page_url(2): [(200, [{"id": 2}], {})],
    })

    assert [i["id"] for i in make_client(transport).paginate("/repos/o/r/releases")] == [1, 2]
    assert transport.calls == [first, page_url(2)]


def test_next_link_without_page_number_is_followed_as_is():
    first = page_url(1)
    cursor = "https://api.github.com/repos/o/r/releases?per_page=100&after=abc"
    transport = FakeTransport({first: [(200, [{"id": 1}], {"link": f'<{cursor}>; rel="next"'})], cursor: [(200, [{"id": 2}], {})]})

    assert [i["id"] for i in make_client(transport).paginate("/repos/o/r/releases")] == [1, 2]


def test_cache_avoids_repeating_calls_and_never_stores_the_token(tmp_path):
    cache = ResponseCache(tmp_path)
    first = FakeTransport(paged_routes(2))
    list(make_client(first, cache).paginate("/repos/o/r/releases"))

    second = FakeTransport({})
    ids = [item["id"] for item in make_client(second, cache).paginate("/repos/o/r/releases")]

    assert ids == [10, 11, 20, 21]
    assert second.calls == []
    stored = [p.read_text(encoding="utf-8") for p in tmp_path.rglob("*.json")]
    assert stored and all(TOKEN not in text for text in stored)
    assert all("repos" in str(p) and "releases" in str(p) for p in tmp_path.rglob("*.json"))


def test_interrupted_collection_resumes_where_it_stopped(tmp_path):
    cache = ResponseCache(tmp_path)
    routes = paged_routes(3)
    routes[page_url(3)] = [KeyboardInterrupt()] + routes[page_url(3)]
    transport = FakeTransport(routes)

    with pytest.raises(KeyboardInterrupt):
        list(make_client(transport, cache).paginate("/repos/o/r/releases"))
    calls_before = len(transport.calls)

    ids = [item["id"] for item in make_client(transport, cache).paginate("/repos/o/r/releases")]

    assert ids == [10, 11, 20, 21, 30, 31]
    assert transport.calls[calls_before:] == [page_url(3)]


def test_waits_for_reset_when_rate_limit_is_exhausted():
    clock = FakeClock()
    url = build_url("/repos/o/r")
    reset = str(int(clock.now) + 120)
    transport = FakeTransport({url: [
        (403, {"message": "API rate limit exceeded"}, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset}),
        (200, {"full_name": "o/r"}, {"x-ratelimit-remaining": "4999"}),
    ]})

    response = make_client(transport, clock=clock).get("/repos/o/r")

    assert response.data == {"full_name": "o/r"}
    assert clock.sleeps == [121]


def test_pauses_before_the_next_request_when_quota_reaches_zero():
    clock = FakeClock()
    reset = str(int(clock.now) + 30)
    transport = FakeTransport({
        build_url("/a"): [(200, {}, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset})],
        build_url("/b"): [(200, {}, {"x-ratelimit-remaining": "5000"})],
    })
    client = make_client(transport, clock=clock)

    client.get("/a")
    client.get("/b")

    assert clock.sleeps == [31]
    assert client.remaining == 5000


def test_secondary_rate_limit_honors_retry_after_then_grows_exponentially():
    clock = FakeClock()
    url = build_url("/x")
    transport = FakeTransport({url: [
        (403, {"message": "secondary rate limit"}, {"retry-after": "7"}),
        (429, {"message": "too many"}, {}),
        (200, {"ok": True}, {}),
    ]})

    make_client(transport, clock=clock).get("/x")

    assert clock.sleeps == [7, 120]


def test_server_errors_retry_with_exponential_backoff():
    clock = FakeClock()
    url = build_url("/x")
    transport = FakeTransport({url: [(502, {}, {}), (503, {}, {}), (200, {"ok": True}, {})]})

    assert make_client(transport, clock=clock).get("/x").data == {"ok": True}
    assert clock.sleeps == [1, 2]


def test_gives_up_after_max_retries():
    clock = FakeClock()
    url = build_url("/x")
    transport = FakeTransport({url: [(500, {}, {})] * 6})

    with pytest.raises(GitHubAPIError) as error:
        make_client(transport, clock=clock, max_retries=5).get("/x")

    assert clock.sleeps == [1, 2, 4, 8, 16]
    assert error.value.status == 500


def test_network_errors_are_retried():
    clock = FakeClock()
    url = build_url("/x")
    transport = FakeTransport({url: [URLError("sem rede"), TimeoutError(), (200, {"ok": True}, {})]})

    assert make_client(transport, clock=clock).get("/x").data == {"ok": True}
    assert clock.sleeps == [1, 2]


def test_not_found_raises_and_is_cached(tmp_path):
    cache = ResponseCache(tmp_path)
    url = build_url("/repos/o/r/compare/v1...v2")
    transport = FakeTransport({url: [(404, {"message": "Not Found"}, {})]})

    for _ in range(2):
        with pytest.raises(GitHubNotFoundError):
            make_client(transport, cache).get("/repos/o/r/compare/v1...v2")

    assert transport.calls == [url]


def test_other_client_errors_raise_immediately_without_cache(tmp_path):
    url = build_url("/x")
    transport = FakeTransport({url: [(401, {"message": "Bad credentials"}, {})]})

    with pytest.raises(GitHubAPIError) as error:
        make_client(transport, ResponseCache(tmp_path)).get("/x")

    assert error.value.status == 401
    assert not list(tmp_path.rglob("*.json"))


def test_permission_403_without_rate_limit_signal_is_an_error():
    url = build_url("/x")
    transport = FakeTransport({url: [(403, {"message": "Resource not accessible"}, {"x-ratelimit-remaining": "4000"})]})

    with pytest.raises(GitHubAPIError):
        make_client(transport).get("/x")


def test_rate_limit_endpoint_is_never_cached(tmp_path):
    url = build_url("/rate_limit")
    transport = FakeTransport({url: [(200, {"rate": {"remaining": 1}}, {}), (200, {"rate": {"remaining": 2}}, {})]})
    client = make_client(transport, ResponseCache(tmp_path))

    assert client.rate_limit()["rate"]["remaining"] == 1
    assert client.rate_limit()["rate"]["remaining"] == 2


def test_sends_token_and_api_headers():
    url = build_url("/x")
    transport = FakeTransport({url: [(200, {}, {})]})

    make_client(transport).get("/x")

    headers = transport.headers_seen[0]
    assert headers["Authorization"] == f"Bearer {TOKEN}"
    assert headers["Accept"] == "application/vnd.github+json"
