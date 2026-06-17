# Implementation Plan — FEAT-001

**Generated:** 2026-06-10  
**Status:** done  
**Title:** Config schema validator for env and data-source flags

## 1. Feature summary

Platform schema validator for `.env` data-source and LLM flags. CLI entry: `./bin/mts config validate`.

## 2. Acceptance criteria

- [x] Validates MACRO_DATA_SOURCE, NEWS_DATA_SOURCE, INSIDER_DATA_SOURCE values
- [x] Also validates GEOPOLITICS_DATA_SOURCE, MARKET_DATA_SOURCE, LLM_PROVIDER
- [x] Emits clear errors for unknown keys
- [x] Unit tests cover valid and invalid configs (`tests/test_config_schema.py`)
- [x] Documented in FREE_DATA_SOURCES.md

## 3. File impact map

| File | Change |
|------|--------|
| `core/config_schema.py` | New — schema + validate_config |
| `tests/test_config_schema.py` | New — unit tests |
| `cli/__main__.py` | `config validate` subcommand |
| `docs/specs/FREE_DATA_SOURCES.md` | Validation section |
| `Trading-Journals/DailyCommands.md` | config validate in session |

## 6. Done checklist

- [x] Acceptance criteria met
- [x] pytest green
- [ ] Reviewer approve (human)
- [x] Quant-risk no escalation
- [x] Docs updated
- [x] feature-journal updated
- [ ] Human merge
