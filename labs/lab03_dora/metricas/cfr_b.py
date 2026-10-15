"""Proxy de falha de entrega baseado em releases corretivas (RQ 03 b)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

VERSION = "semver-patch-v1"
SEMVER = re.compile(r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
FIX_WORDS = re.compile(r"\b(fix(?:es|ed)?|bugfix|hotfix|revert|regression|corrig(?:e|ido|ir))\b", re.I)


def corrective_signal(tag: str, previous_tag: str, text: str = "") -> tuple[bool, str]:
    """Classifica sem usar rótulos da amostra-ouro nem predições de outra versão."""
    current, previous = SEMVER.fullmatch(tag or ""), SEMVER.fullmatch(previous_tag or "")
    if current and previous:
        current_parts = tuple(map(int, current.groups()))
        previous_parts = tuple(map(int, previous.groups()))
        if current_parts[:2] == previous_parts[:2] and current_parts[2] > previous_parts[2]:
            return True, "incremento_patch_semver"
    match = FIX_WORDS.search(text or "")
    if match:
        return True, f"texto:{match.group(0).lower()}"
    return False, "sem_sinal"


def cfr_b_for_repository(releases: list[dict], window_end: date) -> tuple[list[dict], dict]:
    """Atribui falha a R se houver release corretiva nos sete dias seguintes."""
    ordered = sorted(releases, key=lambda row: (row["published_at"], row["tag_name"]))
    cutoff = datetime.combine(window_end + timedelta(days=1), datetime.min.time(), timezone.utc) - timedelta(days=7)
    classified = []
    for row in ordered:
        corrective, evidence = corrective_signal(
            row["tag_name"], row.get("previous_tag", ""), row.get("text", ""),
        )
        classified.append((row, datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")), corrective, evidence))
    detail = []
    for index, (row, published, corrective, evidence) in enumerate(classified):
        censored = published >= cutoff
        following = next(
            (
                later_row["tag_name"]
                for later_row, later_at, later_corrective, _ in classified[index + 1:]
                if later_corrective and timedelta(0) < later_at - published <= timedelta(days=7)
            ),
            "",
        ) if not censored else ""
        detail.append({
            "repository": row["repository"], "tag_name": row["tag_name"],
            "published_at": row["published_at"], "corrective": "sim" if corrective else "nao",
            "evidence": evidence, "heuristic_version": VERSION,
            "censored": str(censored).lower(), "failed": "" if censored else str(bool(following)).lower(),
            "following_corrective_tag": following,
        })
    evaluated = [row for row in detail if row["censored"] == "false"]
    failures = sum(row["failed"] == "true" for row in evaluated)
    metric = {
        "repository": ordered[0]["repository"] if ordered else "",
        "cfr_b": failures / len(evaluated) if evaluated else "",
        "releases_evaluated": len(evaluated),
        "releases_censored": len(detail) - len(evaluated),
    }
    return detail, metric
