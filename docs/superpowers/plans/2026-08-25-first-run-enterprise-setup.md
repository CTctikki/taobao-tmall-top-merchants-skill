# First-Run Enterprise Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require validated QCC and Fengniao private keys while automatically preparing their integrations and giving beginners exact Browser Bridge setup steps.

**Architecture:** Keep environment discovery in `preflight.py`, add a focused stdin-only credential helper for persistent Windows user configuration, and expose sanitized readiness states in preflight JSON. Preserve `bootstrap.ps1` as the one-command entry point and document the hard gate in the Skill and references.

**Tech Stack:** Python 3.11+, PowerShell, `unittest`, Codex MCP TOML, o2/webcli, Node-based Fengniao Skill.

---

### Task 1: Lock Readiness Rules With Tests

**Files:**
- Modify: `tests/test_preflight.py`

- [ ] Add tests requiring the exact `qcc-company` MCP rather than any enterprise MCP.
- [ ] Replace the public-quota expectation with a private-key requirement.
- [ ] Add doctor fixtures proving top-level success without a connected extension fails.
- [ ] Add a test requiring beginner steps and the exact unpacked-extension path.
- [ ] Run `python -m unittest tests.test_preflight -v` and confirm failures describe missing behavior.

### Task 2: Test Secure Credential Configuration

**Files:**
- Create: `scripts/configure_enterprise_keys.py`
- Create: `scripts/run_fengniao.py`
- Modify: `tests/test_preflight.py`

- [ ] Test QCC normalization with and without a `Bearer` prefix.
- [ ] Test temporary config output contains only `bearer_token_env_var = "QCC_AUTH"` and no key value.
- [ ] Mock current-user environment persistence and confirm neither key is emitted.
- [ ] Run the focused tests and confirm they fail before implementation.

### Task 3: Implement Installation and Hard Gates

**Files:**
- Modify: `scripts/preflight.py`
- Modify: `scripts/bootstrap.ps1`
- Create: `scripts/configure_enterprise_keys.py`

- [ ] Add exact QCC detection and sanitized QCC/Fengniao validation functions.
- [ ] Require both installed integrations, both private keys, both validation results, and a connected Browser Bridge.
- [ ] Add automatic Fengniao installation and webcli extension installation commands.
- [ ] Print both official key links and exact Chrome extension steps when blocked.
- [ ] Route optional bootstrap stdin credential setup through the helper without command-line secrets.
- [ ] Route Fengniao commands through a redacting wrapper that reads the persisted user Key.
- [ ] Run the focused tests until green.

### Task 4: Update Skill Guidance

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `references/workflow.md`
- Modify: `references/mcp-setup.md`
- Modify: `tests/test_pipeline.py`

- [ ] State that both private keys are mandatory and public quota cannot substitute.
- [ ] Tell Codex to request both keys together, never repeat them, and invoke the stdin helper.
- [ ] Add both exact acquisition links and novice Browser Bridge steps.
- [ ] Preserve `-SkipTaobaoCheck` and the no-visible-browser rule during setup.
- [ ] Add metadata assertions for these product rules.

### Task 5: Verify Without Publishing

**Files:**
- Test: `tests/test_preflight.py`
- Test: `tests/test_pipeline.py`

- [ ] Run focused tests and the complete unit suite.
- [ ] Run Skill `quick_validate.py`.
- [ ] Run `git diff --check` and a repository secret scan.
- [ ] Inspect `git status` and final diff; do not commit or push.
