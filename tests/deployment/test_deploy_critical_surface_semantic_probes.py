from __future__ import annotations

from pathlib import Path

from engine.main import transform
from scripts.probes.deploy_critical_surface import CASES
from scripts.probes.run_semantic_probes import CORE_PROBES


def test_deploy_critical_surface_probe_is_in_the_core_suite() -> None:
    assert any(path.name == "deploy_critical_surface.py" for path in CORE_PROBES)


def test_deploy_critical_surface_probe_cases_match_local_engine() -> None:
    assert CASES
    for case in CASES:
        assert transform(case.text) == case.expected, case.name


def test_core_probe_suite_ships_the_deploy_critical_probe_file() -> None:
    probe_path = Path("scripts/probes/deploy_critical_surface.py")
    assert probe_path.is_file()
    assert probe_path.resolve() in {path.resolve() for path in CORE_PROBES}
