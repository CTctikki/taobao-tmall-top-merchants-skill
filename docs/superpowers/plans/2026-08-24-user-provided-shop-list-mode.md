# User-Provided Shop List Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach the Skill to produce final outreach workbooks from user-supplied shop names, URLs, text, tables, spreadsheets, or mixed input without adding a parser script or reopening Taobao.

**Architecture:** Add a documented mode router to `SKILL.md`, then define normalization, evidence, output, and recovery rules in the existing references. Enforce the mode contract with an offline metadata regression test.

**Tech Stack:** Markdown Skill instructions, Python `unittest`, existing Skill validator.

---

### Task 1: Add Contract Regression Test

**Files:**
- Modify: `tests/test_pipeline.py`

- [ ] Add a test that requires the Skill to recognize pasted names, multiple URLs, text, tables, spreadsheets, and mixed input.
- [ ] Require explicit instructions to skip Taobao discovery and assortment auditing in list mode.
- [ ] Require every supplied shop to enter the formal sheet without fabricated SPU, share, payment, or Top30 claims.
- [ ] Run the test and confirm it fails because the mode is absent.

### Task 2: Document Mode Routing

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`

- [ ] Extend Skill discovery metadata to cover user-supplied shop lists and links.
- [ ] Add a mode-selection section that distinguishes category discovery from user-provided lists.
- [ ] State that explicit lists are authoritative unless the user requests expansion.
- [ ] Run the focused test and confirm it passes.

### Task 3: Define Workflow and Data Contract

**Files:**
- Modify: `references/workflow.md`
- Modify: `references/data-contract.md`

- [ ] Define normalization and deduplication fields for flexible user input.
- [ ] Define six logical output sheets and original-input traceability.
- [ ] Preserve candidate evidence rules and `selected: false` behavior.
- [ ] Define quota and headless recovery without triggering Taobao.

### Task 4: Verify Skill

**Files:**
- Test: `tests/test_pipeline.py`

- [ ] Run the focused regression test.
- [ ] Run all 34 unit tests.
- [ ] Run `quick_validate.py` against the Skill root.
- [ ] Run `git diff --check` and secret scanning.
- [ ] Review the final diff without committing or pushing.
