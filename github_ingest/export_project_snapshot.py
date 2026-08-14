from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingest_github import GitHubGraphQLClient, load_env_file

ROOT_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = ROOT_DIR / "data" / "project_snapshots"

PROJECT_ITEMS_QUERY = """
query ProjectSnapshot($login: String!, $number: Int!, $first: Int!, $after: String) {
  user(login: $login) {
    projectV2(number: $number) {
      title
      url
      items(first: $first, after: $after) {
        totalCount
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          type
          content {
            ... on Issue {
              number
              title
              url
              state
              repository {
                nameWithOwner
              }
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
            ... on PullRequest {
              number
              title
              url
              state
              repository {
                nameWithOwner
              }
              assignees(first: 10) {
                nodes {
                  login
                }
              }
            }
          }
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
              ... on ProjectV2ItemFieldTextValue {
                text
                field {
                  ... on ProjectV2FieldCommon {
                    name
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
"""


def fetch_project_items(
    client: GitHubGraphQLClient, login: str, project_number: int, page_size: int
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    after = None

    while True:
        data = client.execute(
            PROJECT_ITEMS_QUERY,
            {"login": login, "number": project_number, "first": page_size, "after": after},
        )
        project = data["user"]["projectV2"]
        if project is None:
            raise RuntimeError(f"Project {project_number} nao encontrado para o usuario {login}.")

        page = project["items"]
        items.extend(node for node in page["nodes"] if node is not None)

        page_info = page["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    return items


def field_value(item: dict[str, Any], field_name: str) -> str:
    for value in item["fieldValues"]["nodes"]:
        if value.get("field", {}).get("name") != field_name:
            continue
        if "name" in value:
            return value["name"]
        if "text" in value:
            return value["text"]
    return ""


def build_snapshot_row(item: dict[str, Any], sprint: str, exported_at: datetime) -> dict[str, Any]:
    content = item.get("content") or {}
    assignees = ", ".join(node["login"] for node in content.get("assignees", {}).get("nodes", []))

    return {
        "sprint": sprint,
        "exported_at": exported_at.isoformat(),
        "project_item_id": item["id"],
        "item_type": item["type"],
        "issue_number": content.get("number"),
        "title": content.get("title"),
        "repository": (content.get("repository") or {}).get("nameWithOwner"),
        "url": content.get("url"),
        "state": content.get("state"),
        "assignees": assignees,
        "status": field_value(item, "Status"),
    }


def write_snapshot_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sprint",
        "exported_at",
        "project_item_id",
        "item_type",
        "issue_number",
        "title",
        "repository",
        "url",
        "state",
        "assignees",
        "status",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta os itens do GitHub Projects (v2) e seu status atual para CSV."
    )
    parser.add_argument(
        "--sprint",
        required=True,
        help="Identificador da sprint sendo fechada (ex.: Lab01S01).",
    )
    parser.add_argument("--login", default="JoaoRajao", help="Dono do GitHub Projects (v2).")
    parser.add_argument("--project-number", type=int, default=4, help="Numero do Project (v2).")
    parser.add_argument(
        "--page-size", type=int, default=50, help="Itens por pagina da query GraphQL."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Caminho do CSV de saida. Default: data/project_snapshots/snapshot_<sprint>_<data>.csv",
    )
    return parser.parse_args()


def main() -> None:
    load_env_file(ROOT_DIR / ".env")
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(f"Configure GITHUB_TOKEN em {ROOT_DIR / '.env'}.")

    exported_at = datetime.now(timezone.utc)
    client = GitHubGraphQLClient(token=token)
    items = fetch_project_items(client, args.login, args.project_number, args.page_size)
    rows = [build_snapshot_row(item, args.sprint, exported_at) for item in items]

    output_path = args.output or (
        SNAPSHOT_DIR / f"snapshot_{args.sprint}_{exported_at.date().isoformat()}.csv"
    )
    write_snapshot_csv(rows, output_path)
    print(f"OK: {len(rows)} itens exportados para {output_path}")


if __name__ == "__main__":
    main()
