# First-Run Enterprise Setup Design

## Goal

Make first use safe and beginner-friendly: Codex installs or diagnoses webcli Browser Bridge, installs the Fengniao Skill, configures the dedicated `qcc-company` MCP, and refuses merchant work until both user-owned API keys are configured and validated.

## Hard Gate

The preflight passes enterprise readiness only when all conditions are true:

- `qcc-company` is configured with the official endpoint and `QCC_AUTH` bearer-token environment reference.
- A user-provided QCC key is present and its lightweight MCP validation succeeds.
- The Fengniao Skill is installed at the configured location.
- A user-provided Fengniao key is present and its lightweight `discover` validation succeeds.

Other company MCPs and Fengniao's bundled public quota are not substitutes. Missing, invalid, exhausted, or unavailable credentials stop the business task and show both official key links.

## Credential Handling

Users send both keys to Codex instead of configuring environment variables themselves. Codex passes them to a dedicated helper over standard input. The helper accepts the QCC value with or without a `Bearer ` prefix, stores the raw token expected by `bearer_token_env_var` in the Windows current-user environment, adds exactly one prefix only for direct HTTP requests, and registers only the environment-variable name in Codex MCP configuration.

Because a child process cannot update its already-running Codex parent, repository QCC clients read the Windows current-user value as a fallback and Fengniao commands run through `scripts/run_fengniao.py`, which injects the stored Key into only the child process and redacts it from captured output. This permits immediate use without restarting Codex.

Credentials must never appear in command arguments, stdout, stderr, repository files, logs, workbooks, documentation, or final responses. Tests use placeholders and temporary paths only.

## Browser Bridge Onboarding

Preflight first installs webcli through o2 when needed, then attempts `webcli extension install` without launching a visible browser itself. If Browser Bridge is not connected, output must explain these exact beginner steps: open `chrome://extensions`, enable Developer mode, choose “Load unpacked”, select the printed `~/.webcli/extension` directory, pin Browser Bridge, and keep Chrome open.

Browser readiness requires `connectivity.ok=true` and at least one profile with `extensionConnected=true`; a top-level doctor `ok=true` alone is insufficient.

## Installation and Validation

The existing bootstrap remains the single entry point. `preflight.py --install-missing` installs missing local components, but never asks the user to type secrets into command lines. QCC validation uses a minimal MCP tool-list request and Fengniao validation uses one fixed low-cost fuzzy-search request so the private Key, service availability, and quota are genuinely exercised. Validation results expose booleans and sanitized errors only.

`-SkipTaobaoCheck` continues to suppress every Taobao page action. Credential setup and enterprise validation do not open Taobao or a visible browser window.
