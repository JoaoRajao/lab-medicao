from __future__ import annotations

from datetime import date
import csv

from labs.lab03_dora.cfr_b import build

from labs.lab03_dora.metricas.cfr_b import cfr_b_for_repository, corrective_signal


def release(tag, at, previous=""):
    return {"repository": "o/r", "tag_name": tag, "published_at": at, "previous_tag": previous}


def test_issue_example_and_seven_day_boundary():
    rows = [
        release("v2.3.0", "2026-08-01T00:00:00Z", "v2.2.0"),
        release("v2.3.1", "2026-08-08T00:00:00Z", "v2.3.0"),
        release("v2.4.0", "2026-08-10T00:00:00Z", "v2.3.1"),
        release("v2.5.0", "2026-08-20T00:00:00Z", "v2.4.0"),
    ]
    detail, metric = cfr_b_for_repository(rows, date(2026, 9, 30))
    assert [row["corrective"] for row in detail] == ["nao", "sim", "nao", "nao"]
    assert [row["failed"] for row in detail] == ["true", "false", "false", "false"]
    assert detail[0]["following_corrective_tag"] == "v2.3.1"
    assert metric["cfr_b"] == 0.25


def test_censors_last_seven_days_and_does_not_count_later_release():
    rows = [
        release("v1.0.0", "2026-09-22T00:00:00Z"),
        release("v1.0.1", "2026-09-24T00:00:00Z", "v1.0.0"),
        release("v1.0.2", "2026-09-30T23:59:59Z", "v1.0.1"),
    ]
    detail, metric = cfr_b_for_repository(rows, date(2026, 9, 30))
    assert [row["censored"] for row in detail] == ["false", "true", "true"]
    assert detail[0]["failed"] == "true"
    assert metric == {"repository": "o/r", "cfr_b": 1.0, "releases_evaluated": 1, "releases_censored": 2}


def test_non_semver_and_text_signal():
    assert corrective_signal("release-q3", "release-q2") == (False, "sem_sinal")
    assert corrective_signal("release-q3", "release-q2", "Hotfix for startup") == (True, "texto:hotfix")
    assert corrective_signal("v2.5.0", "v2.4.0") == (False, "sem_sinal")


def test_build_writes_contract_consumed_by_dataset(tmp_path):
    (tmp_path / "repositories.csv").write_text("repository,default_branch\no/r,main\n", encoding="utf-8")
    (tmp_path / "releases.csv").write_text(
        "repository,tag_name,published_at,previous_tag\n"
        "o/r,v1.0.0,2026-08-01T00:00:00Z,\n"
        "o/r,v1.0.1,2026-08-02T00:00:00Z,v1.0.0\n",
        encoding="utf-8",
    )
    detail_path, metric_path = build(tmp_path, date(2026, 9, 30))
    with metric_path.open(newline="", encoding="utf-8") as file:
        metric = list(csv.DictReader(file))[0]
    assert metric == {"repository": "o/r", "cfr_b": "0.5", "releases_evaluated": "2", "releases_censored": "0"}
    assert sum(1 for _ in detail_path.open(encoding="utf-8")) == 3
