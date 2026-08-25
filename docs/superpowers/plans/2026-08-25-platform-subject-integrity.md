# Platform Subject Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every confirmed merchant subject matches platform qualification evidence and keep unrelated companies only as labeled outreach candidates.

**Architecture:** Persist qualification data separately, resolve confirmed subjects with platform evidence first, render explicit workbook columns, and add an acceptance-time mismatch assertion.

**Tech Stack:** Python, webcli Browser Bridge, openpyxl, unittest.

---

### Task 1: Reproduce the Mismatch

- [ ] Add a fixture with the reported Tmall license and mismatched selected search candidates.
- [ ] Assert the license company and credit code occupy formal subject columns.
- [ ] Assert mismatched companies remain only in the outreach-candidate column.

### Task 2: Capture Platform Qualifications

- [ ] Add qualification-link discovery and risk-control detection scripts.
- [ ] Parse license company, credit code, legal person, address, and establishment date.
- [ ] Persist one record per shop in `platform_qualifications.json`.

### Task 3: Enforce Subject Resolution

- [ ] Accept only platform qualification or exact credit-code evidence as confirmed.
- [ ] Override stale mismatched `selected: true` values with platform identity.
- [ ] Add platform identity and consistency columns to the formal workbook.
- [ ] Label all mismatches as non-subject outreach candidates.

### Task 4: Add Delivery Guard

- [ ] Compare workbook company and credit code with verified platform records.
- [ ] Fail `verify_job.py` on any mismatch.
- [ ] Update Skill, workflow, README, and data contract.

### Task 5: Verify

- [ ] Run focused and full unit tests.
- [ ] Run Skill validation, `git diff --check`, and secret scanning.
