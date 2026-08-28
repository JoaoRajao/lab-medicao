from __future__ import annotations

from typing import Any

from shared.github_client import GitHubGraphQLClient


def paginate(
    client: GitHubGraphQLClient,
    query: str,
    variables: dict[str, Any],
    path: str,
    page_size: int,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Percorre paginas de uma query GraphQL por cursor.

    Generico para qualquer query cuja resposta siga o padrao
    `<path> { pageInfo { hasNextPage endCursor } nodes { ... } } }`.
    `variables` deve conter os parametros da query exceto `first`/`after`,
    que sao controlados por esta funcao. `path` e a chave de nivel superior
    da resposta onde `nodes`/`pageInfo` estao (ex.: "search").
    """
    nodes: list[dict[str, Any]] = []
    after = None

    while limit is None or len(nodes) < limit:
        first = page_size if limit is None else min(page_size, limit - len(nodes))
        data = client.execute(query, {**variables, "first": first, "after": after})
        page = data[path]
        page_nodes = [node for node in page["nodes"] if node is not None]
        nodes.extend(page_nodes)

        page_info = page["pageInfo"]
        if not page_info["hasNextPage"] or not page_nodes:
            break
        after = page_info["endCursor"]

    return nodes[:limit] if limit is not None else nodes
