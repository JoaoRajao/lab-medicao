from __future__ import annotations

from labs.lab03_dora.sugestoes_rotulagem import corrective, project_type, real_delivery


def test_suggestions_are_explicitly_uncertain_when_evidence_is_mixed():
    assert corrective("New feature and bug fixes", "")[0] == "incerto"
    assert corrective("", "fix: crash")[0] == "incerto"
    assert corrective("Hotfix for crash", "")[0] == "sim"
    assert project_type("Python SDK for an API", "")[0] == "biblioteca/framework"
    assert real_delivery("Curated list of examples", "")[0] == "incerto"
