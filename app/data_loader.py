from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FROZEN_RESULT_DIR = Path("data/examples/rdi-wok-250-001")
SPIKES_ROOT = Path("data/spikes")


def find_latest_live_run() -> Path | None:

    """
    Live runs land in data/spikes/<timestamped-dir>/ (gitignored -
    see README "Reproducibility"). Picks the most recently
    modified one, if any exists on this machine.
    """

    if not SPIKES_ROOT.exists():
        return None

    candidates = [
        p
        for p in SPIKES_ROOT.iterdir()
        if p.is_dir()
        and (p / "screening" / "project_assessment_draft.json").exists()
    ]

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_json(path: Path) -> Any | None:

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


class ProjectData:

    """
    Read-only view over one project's already-computed screening
    output. Every field here is loaded verbatim from JSON produced
    by the existing pipeline (synthesize_project_assessment.py,
    scripts/export_frozen_example.py) - this class contains no
    screening, synthesis, or recommendation logic of its own.
    """

    def __init__(self, result_dir: Path, *, is_frozen: bool):

        self.result_dir = result_dir
        self.is_frozen = is_frozen

        self.draft = _read_json(
            result_dir / "screening" / "project_assessment_draft.json"
        )

        self.domain_summaries = (
            _read_json(
                result_dir
                / "investigation"
                / "domain_summaries.json"
            )
            or []
        )

        self.evidence_provenance = (
            _read_json(
                result_dir
                / "investigation"
                / "evidence_provenance.json"
            )
            or []
        )

        self.planner_decisions = (
            _read_json(
                result_dir
                / "investigation"
                / "planner_decisions.json"
            )
            or []
        )

    @property
    def has_draft(self) -> bool:
        return self.draft is not None

    @property
    def has_investigation_detail(self) -> bool:
        return bool(self.domain_summaries)

    @property
    def recommendation_draft(self) -> dict:
        return self.draft["recommendation_draft"]

    @property
    def gate_synthesis(self) -> list[dict]:
        return self.draft["gate_synthesis"]

    @property
    def cod_feasibility(self) -> dict:
        return self.draft["cod_feasibility"]

    @property
    def evidence_sufficiency(self) -> dict:
        return self.draft["evidence_sufficiency"]

    @property
    def recommendation_policy(self) -> dict:
        return self.draft["recommendation_policy"]


def load_project_data(mode: str) -> ProjectData | None:

    if mode == "frozen":
        return ProjectData(FROZEN_RESULT_DIR, is_frozen=True)

    live_dir = find_latest_live_run()

    if live_dir is None:
        return None

    return ProjectData(live_dir, is_frozen=False)
