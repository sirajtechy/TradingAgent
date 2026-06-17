"""Shared utilities for MyTradingSpace loop engineering scripts."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

# MyTradingSpace root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
LOOP_DIR = ROOT / ".loop"
ROADMAP_PATH = LOOP_DIR / "roadmap.yaml"
QUEUE_PATH = LOOP_DIR / "state" / "queue.json"
FEATURE_JOURNAL = LOOP_DIR / "state" / "feature-journal.md"
OPS_JOURNAL = LOOP_DIR / "state" / "ops-journal.md"
PLANS_DIR = LOOP_DIR / "state" / "plans"
TEMPLATES_DIR = LOOP_DIR / "templates"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_roadmap() -> Dict[str, Any]:
    if not ROADMAP_PATH.is_file():
        return {"epics": [], "features": []}
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        return {"epics": data.get("epics") or [], "features": data.get("features") or []}
    return _parse_roadmap_minimal(text)


def _parse_roadmap_minimal(text: str) -> Dict[str, Any]:
    """Minimal YAML-ish parser when PyYAML is unavailable."""
    features: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    in_criteria = False
    criteria: List[str] = []

    for line in text.splitlines():
        if line.strip().startswith("- id: FEAT-"):
            if current:
                if criteria:
                    current["acceptance_criteria"] = criteria
                features.append(current)
            current = {"id": line.split("FEAT-")[1].strip()}
            current["id"] = "FEAT-" + current["id"]
            in_criteria = False
            criteria = []
        elif current and line.strip().startswith("title:"):
            current["title"] = line.split("title:", 1)[1].strip()
        elif current and line.strip().startswith("epic:"):
            current["epic"] = line.split("epic:", 1)[1].strip()
        elif current and line.strip().startswith("priority:"):
            current["priority"] = line.split("priority:", 1)[1].strip()
        elif current and line.strip().startswith("auto_eligible:"):
            val = line.split(":", 1)[1].strip().lower()
            current["auto_eligible"] = val == "true"
        elif current and line.strip().startswith("status:"):
            current["status"] = line.split("status:", 1)[1].strip()
        elif current and line.strip().startswith("risk_level:"):
            current["risk_level"] = line.split("risk_level:", 1)[1].strip()
        elif current and "acceptance_criteria:" in line:
            in_criteria = True
        elif in_criteria and line.strip().startswith("- "):
            criteria.append(line.strip()[2:].strip())

    if current:
        if criteria:
            current["acceptance_criteria"] = criteria
        features.append(current)

    return {"epics": [], "features": features}


def save_roadmap(data: Dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML required to save roadmap; pip install pyyaml")
    ROADMAP_PATH.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def load_queue() -> Dict[str, Any]:
    if not QUEUE_PATH.is_file():
        return {"generated_at": None, "selected_feature_id": None, "items": []}
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def save_queue(data: Dict[str, Any]) -> None:
    QUEUE_DIR = QUEUE_PATH.parent
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def append_journal(path: Path, entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    block = f"\n## {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n{entry.strip()}\n"
    path.write_text(existing.rstrip() + block + "\n", encoding="utf-8")


def find_todos(root: Path) -> List[Dict[str, str]]:
    pattern = re.compile(r"\b(TODO|FIXME|XXX)\b", re.IGNORECASE)
    hits: List[Dict[str, str]] = []
    skip = {".git", ".next", "node_modules", "__pycache__", ".venv", "archive"}
    for path in root.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.suffix not in {".py", ".md", ".ts", ".tsx", ".yml", ".yaml"}:
            continue
        if not path.is_file() or path.stat().st_size > 500_000:
            continue
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if pattern.search(line):
                    hits.append({
                        "file": str(path.relative_to(root)),
                        "line": str(i),
                        "text": line.strip()[:200],
                    })
        except OSError:
            continue
    return hits[:100]


def git_recent_commits(root: Path, n: int = 10) -> List[str]:
    try:
        out = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode == 0:
            return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    except OSError:
        pass
    return []


def score_feature(feature: Dict[str, Any]) -> float:
    priority_map = {"high": 3.0, "medium": 2.0, "low": 1.0}
    risk_map = {"low": 3.0, "medium": 2.0, "high": 0.0}
    pri = priority_map.get(str(feature.get("priority", "medium")).lower(), 1.0)
    risk = risk_map.get(str(feature.get("risk_level", "medium")).lower(), 1.0)
    criteria = feature.get("acceptance_criteria") or []
    crit_score = 3.0 if len(criteria) >= 3 else 1.0
    epic_boost = 1.0 if str(feature.get("epic", "")) == "EPIC-002" else 0.0
    auto = 1.0 if feature.get("auto_eligible") else 0.0
    if not auto:
        return 0.0
    if str(feature.get("status", "")).lower() in {"done", "blocked", "in_progress"}:
        return 0.0
    return round(pri * 0.4 + risk * 0.3 + crit_score * 0.2 + epic_boost * 0.1, 2)


def get_feature_by_id(feature_id: str) -> Optional[Dict[str, Any]]:
    data = load_roadmap()
    for feat in data.get("features") or []:
        if feat.get("id") == feature_id:
            return feat
    return None


def render_template(name: str, **kwargs: str) -> str:
    path = TEMPLATES_DIR / name
    text = path.read_text(encoding="utf-8")
    for key, val in kwargs.items():
        text = text.replace("{{" + key.upper() + "}}", val)
        text = text.replace("{{" + key + "}}", val)
    return text


def run_pytest(root: Path, extra_args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
    cmd = ["python3", "-m", "pytest", "tests/", "-q", "--tb=no"]
    if extra_args:
        cmd.extend(extra_args)
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True)
