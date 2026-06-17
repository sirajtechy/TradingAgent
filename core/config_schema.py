"""
Environment config schema validation for MyTradingSpace.

Validates known env keys and allowed values for data-source and LLM flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple


# Keys recognized by the platform (unknown keys → validation error).
KNOWN_ENV_KEYS: FrozenSet[str] = frozenset({
    "POLYGON_API_KEY",
    "FMP_API_KEY",
    "FRED_API_KEY",
    "OPENAI_API_KEY",
    "MACRO_DATA_SOURCE",
    "NEWS_DATA_SOURCE",
    "INSIDER_DATA_SOURCE",
    "GEOPOLITICS_DATA_SOURCE",
    "MARKET_DATA_SOURCE",
    "LLM_PROVIDER",
    "LLM_ENABLED",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "PHOENIX_POLYGON_ONLY",
    "SEC_EDGAR_USER_AGENT",
    "MYTRADING_PYTHON",
})
    "MACRO_DATA_SOURCE": frozenset({"auto", "fred", "yfinance"}),
    "NEWS_DATA_SOURCE": frozenset({"auto", "fmp", "yfinance"}),
    "INSIDER_DATA_SOURCE": frozenset({"auto", "edgar", "fmp", "yfinance"}),
    "GEOPOLITICS_DATA_SOURCE": frozenset({"auto", "fmp", "yfinance"}),
    "MARKET_DATA_SOURCE": frozenset({"auto", "polygon", "yfinance"}),
    "LLM_PROVIDER": frozenset({"deterministic", "openai"}),
    "LLM_ENABLED": frozenset({"true", "false", "1", "0", "yes", "no", "y", "n"}),
    "PHOENIX_POLYGON_ONLY": frozenset({"true", "false", "1", "0", "yes", "no", "y", "n"}),
}


@dataclass(frozen=True)
class ConfigValidationResult:
    ok: bool
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()


@dataclass
class ConfigValidationReport:
    """Detailed report including normalized values."""

    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized: Dict[str, str] = field(default_factory=dict)

    def to_result(self) -> ConfigValidationResult:
        return ConfigValidationResult(
            ok=self.ok,
            errors=tuple(self.errors),
            warnings=tuple(self.warnings),
        )


def parse_env_file(path: Path) -> Dict[str, str]:
    """Parse a dotenv-style file into key/value pairs (no expansion)."""
    if not path.is_file():
        raise FileNotFoundError(f"Env file not found: {path}")

    out: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value
    return out


def validate_config(
    env: Mapping[str, str],
    *,
    strict_unknown_keys: bool = True,
) -> ConfigValidationReport:
    """
    Validate environment mapping against the platform schema.

    Parameters
    ----------
    env:
        Key/value env vars (typically from os.environ or .env file).
    strict_unknown_keys:
        When True, keys not in KNOWN_ENV_KEYS produce errors.
    """
    report = ConfigValidationReport(ok=True)

    for key, raw_value in env.items():
        if not key or key.startswith("#"):
            continue

        value = (raw_value or "").strip()
        if strict_unknown_keys and key not in KNOWN_ENV_KEYS:
            report.errors.append(
                f"Unknown env key {key!r} — not in platform schema. "
                f"See .env.example and docs/specs/FREE_DATA_SOURCES.md"
            )
            report.ok = False
            continue

        if key in ENUM_ENV_VARS:
            normalized = value.lower()
            allowed = ENUM_ENV_VARS[key]
            if normalized not in allowed:
                report.errors.append(
                    f"Invalid value for {key}: {value!r} — allowed: {', '.join(sorted(allowed))}"
                )
                report.ok = False
            else:
                report.normalized[key] = normalized

        if key.endswith("_API_KEY") and value in {"", "your_polygon_api_key_here", "your_fmp_api_key_here", "your_fred_api_key_here"}:
            report.warnings.append(f"{key} is unset or placeholder — paid APIs may fall back to yfinance")

    return report


def validate_env_file(
    path: Path,
    *,
    strict_unknown_keys: bool = True,
) -> ConfigValidationReport:
    """Parse and validate a .env file."""
    env = parse_env_file(path)
    return validate_config(env, strict_unknown_keys=strict_unknown_keys)


def format_validation_report(report: ConfigValidationReport) -> str:
    lines: List[str] = []
    if report.ok:
        lines.append("Config validation: OK")
    else:
        lines.append("Config validation: FAILED")
    for err in report.errors:
        lines.append(f"  ERROR: {err}")
    for warn in report.warnings:
        lines.append(f"  WARN:  {warn}")
    return "\n".join(lines)


def load_and_validate_env_file(path: Optional[Path] = None) -> ConfigValidationReport:
    """Load project .env from default location and validate."""
    from core.paths import ENV_FILE

    target = path or ENV_FILE
    return validate_env_file(target)
