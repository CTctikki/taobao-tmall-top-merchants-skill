# Dynamic Company Source Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make company lookup order deterministic from identity precision and provider availability.

**Architecture:** Add a pure routing module that returns ordered query steps and evidence priority. Keep provider calls in existing workflows while documenting the exact route in the Skill and workbook reuse guidance.

**Tech Stack:** Python 3, `unittest`, Markdown, openpyxl workbook builder.

---

### Task 1: Routing Contract

**Files:**
- Create: `scripts/company_source_routing.py`
- Create: `tests/test_company_source_routing.py`

- [x] Write failing tests for fuzzy identity, exact identity, one-provider fallback, and no-provider failure.
- [x] Run `python -m unittest tests.test_company_source_routing -v` and confirm the module or behavior is missing.
- [x] Implement `company_lookup_plan()` and a JSON CLI.
- [x] Re-run the targeted tests and confirm they pass.

### Task 2: Skill Integration

**Files:**
- Modify: `SKILL.md`
- Modify: `references/workflow.md`
- Modify: `references/mcp-setup.md`
- Modify: `README.md`
- Modify: `scripts/build_workbook.py`
- Modify: `tests/test_pipeline.py`

- [x] Add failing metadata assertions for both dynamic routes and evidence priority.
- [x] Update Skill instructions and workbook reuse guidance to match the router.
- [x] Run the metadata and workbook contract tests.

### Task 3: Verification

**Files:**
- Verify all modified files.

- [x] Run `python -m unittest discover -s tests -v`.
- [x] Run the official Skill `quick_validate.py` in UTF-8 mode.
- [x] Scan for API key and bearer token patterns.
- [x] Run `git diff --check` and review the diff; commit and push follow this plan update.
