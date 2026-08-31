# Independent Merchant Review Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent workbook review mode that audits listed Taobao/Tmall shops, calculates category SPU and high-sales evidence, safely resumes interrupted runs, and preserves the source workbook.

**Architecture:** `review_workbook.py` owns semantic workbook discovery, task grouping, result reuse, output writing, and invariant checks. `audit_review_shops.py` owns serial Browser Bridge navigation, evidence extraction, classification, and atomic checkpoints behind a testable browser adapter. Existing discovery and user-provided-list paths remain unchanged.

**Tech Stack:** Python 3.11, `unittest`, `openpyxl`, JSON checkpoints, PowerShell, `o2`, `webcli`, Browser Bridge, Chrome.

**Execution constraint:** Do not commit or push during implementation. The user will review all changes and validation evidence first.

---

## File Map

- Create `scripts/review_workbook.py`: workbook semantics, task selection/reuse, output copy/write, invariant verification, CLI orchestration.
- Create `scripts/audit_review_shops.py`: sales parsing, evidence model, browser adapter, fallback state machine, checkpoint persistence, priority classification.
- Create `tests/test_review_mode.py`: behavior tests for workbook and browser audit logic.
- Modify `tests/test_preflight.py`: audit-only environment behavior and bootstrap contract tests.
- Modify `tests/test_pipeline.py`: Skill routing/documentation regressions and legacy-mode guards.
- Create `references/review-mode.md`: user-facing workflow and recovery instructions.
- Create `references/review-data-contract.md`: workbook, evidence, and checkpoint schemas.
- Modify `SKILL.md`, `README.md`, `agents/openai.yaml`: third-mode routing and invocation examples.
- Modify `scripts/preflight.py`, `scripts/bootstrap.ps1`: `--audit-only` / `-AuditOnly` environment path.
- Modify `scripts/common.py` only if safe URL argument serialization is genuinely shared.

### Task 1: Semantic Workbook Discovery

**Files:**
- Create: `tests/test_review_mode.py`
- Create: `scripts/review_workbook.py`

- [ ] **Step 1: Write failing semantic-header and row-selection tests**

Create workbooks in `TemporaryDirectory` with shuffled columns and assert semantic fields, selected owner, blank-row exclusion, and partial-result diagnostics:

```python
class ReviewWorkbookSelectionTests(unittest.TestCase):
    def test_discovers_shuffled_semantic_headers(self):
        workbook = make_review_book([
            "负责人", "店铺链接", "引入优先级", "店铺名称", "是否符合引入画像"
        ])
        table = discover_review_tables(workbook)[0]
        self.assertEqual(table.columns["shop_name"], 4)
        self.assertEqual(table.columns["profile_result"], 5)
        self.assertEqual(table.columns["priority"], 3)
        self.assertEqual(table.columns["owner"], 1)

    def test_selects_only_matching_owner_with_both_results_blank(self):
        table = workbook_with_rows(owner="张萍云")
        selection = select_review_rows(table, owner="张萍云")
        self.assertEqual([row.shop_name for row in selection.pending], ["甲店"])
        self.assertEqual([row.shop_name for row in selection.inconsistent], ["半填店"])

    def test_excludes_blank_and_merged_subordinate_rows(self):
        selection = select_review_rows(workbook_with_blank_merged_rows(), owner="张萍云")
        self.assertEqual(selection.source_rows, [2, 4])
```

- [ ] **Step 2: Run the new test file and verify RED**

Run:

```powershell
python -m unittest discover -s tests -p "test_review_mode.py" -v
```

Expected: import failure because `review_workbook` does not exist.

- [ ] **Step 3: Implement minimal workbook semantics**

Add focused types and functions:

```python
@dataclass(frozen=True)
class ReviewTable:
    sheet_name: str
    header_row: int
    columns: dict[str, int]

@dataclass(frozen=True)
class ReviewRow:
    sheet_name: str
    row_number: int
    shop_name: str
    owner: str
    shop_url: str
    category: str

@dataclass
class ReviewSelection:
    pending: list[ReviewRow]
    completed: list[ReviewRow]
    inconsistent: list[ReviewRow]

```

Implement exact public call signatures `discover_review_tables(workbook, scan_rows=30) -> list[ReviewTable]`, `resolve_owner(workbook, tables, requested_owner=None) -> str`, and `select_review_rows(workbook, tables, owner) -> ReviewSelection`. Use normalized alias sets for `shop_name`, `profile_result`, `priority`, `owner`, `shop_url`, `category`, and `phone`. Reject missing or duplicate required mappings with `ReviewWorkbookError`.

- [ ] **Step 4: Run the targeted tests and verify GREEN**

Run the same discovery command. Expected: all Task 1 tests pass.

### Task 2: Sales Parsing and Priority Classification

**Files:**
- Modify: `tests/test_review_mode.py`
- Create: `scripts/audit_review_shops.py`

- [ ] **Step 1: Write failing parsing, deduplication, and classification tests**

```python
class ReviewEvidenceTests(unittest.TestCase):
    def test_parses_public_sales_lower_bounds(self):
        cases = {
            "1万+人付款": 10000,
            "10万+人付款": 100000,
            "总销量：100万+": 1000000,
            "已售1000+件": 1000,
            "9999人付款": 9999,
            "10000人付款": 10000,
        }
        for text, expected in cases.items():
            self.assertEqual(parse_review_sales_lower_bound(text), expected)

    def test_counts_unique_product_ids_only(self):
        evidence = [product("1", 20000), product("1", 20000), product("2", 9999)]
        summary = summarize_evidence(evidence)
        self.assertEqual(summary.relevant_spu, 2)
        self.assertEqual(summary.high_sales_links, 1)

    def test_classifies_all_four_results(self):
        self.assertEqual(classify_review(20, 3, complete=True).priority, "高")
        self.assertEqual(classify_review(15, 1, complete=True).priority, "中")
        self.assertEqual(classify_review(14, 5, complete=True).priority, "低")
        self.assertEqual(classify_review(30, 5, complete=False).priority, "待核验")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: missing imports/functions from `audit_review_shops.py`.

- [ ] **Step 3: Implement the pure evidence core**

```python
HIGH_SALES_THRESHOLD = 10_000

@dataclass(frozen=True)
class ProductEvidence:
    product_id: str
    product_url: str
    title: str
    sales_text: str
    sales_lower_bound: int | None
    relevant: bool
    source_type: str
    final_page_url: str

```

Implement exact public call signatures `parse_review_sales_lower_bound(text: str) -> int | None`, `extract_product_id(url: str, explicit_id: str = "") -> str`, `deduplicate_products(items: Iterable[ProductEvidence]) -> list[ProductEvidence]`, `summarize_evidence(items: Iterable[ProductEvidence]) -> EvidenceSummary`, and `classify_review(relevant_spu: int, high_sales_links: int, complete: bool) -> ReviewDecision`. When duplicate evidence differs, retain the highest parsed lower bound while preserving all source URLs in the checkpoint record.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Expected: all parsing, deduplication, threshold, and result-text assertions pass.

### Task 3: Safe Browser Navigation and Fallbacks

**Files:**
- Modify: `tests/test_review_mode.py`
- Modify: `scripts/audit_review_shops.py`
- Modify: `scripts/common.py` only if the argument-array runner is reused

- [ ] **Step 1: Write failing URL-safety and fallback tests**

```python
class ReviewBrowserTests(unittest.TestCase):
    def test_long_ad_url_is_serialized_without_shell_splitting(self):
        url = "https://click.simba.taobao.com/x?名称=%E6%B5%8B%E8%AF%95&s=1&k=2&e=3"
        browser = RecordingBrowser(home_products=[], search_products=[product("1", 10000)])
        audit_shop(task(url=url), browser, sleeper=lambda _: None)
        self.assertEqual(browser.assigned_urls, [url])
        self.assertNotIn("shell", browser.process_options)

    def test_falls_back_home_then_hot_sales_then_public_list(self):
        browser = RecordingBrowser(home_products=[], search_products=[], public_products=[product("1", 10000)])
        result = audit_shop(task(), browser, sleeper=lambda _: None)
        self.assertEqual(browser.sources, ["shop_home", "shop_hot_sales", "public_shop_list"])
        self.assertEqual(result.evidence[0].source_type, "public_shop_list")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: missing `BrowserAdapter`, `safe_assign`, or `audit_shop` behavior.

- [ ] **Step 3: Implement the browser adapter and state machine**

```python
def make_safe_assign_script(url: str) -> str:
    return f"location.assign({json.dumps(url, ensure_ascii=False)})"
```

Define `BrowserAdapter` with `open_controlled_taobao()`, `assign_url(url)`, and `inspect_page(source_type)` methods. Implement `audit_shop(task, browser, sleeper=time.sleep) -> ShopAuditResult` to inspect `shop_home`, then `shop_hot_sales`, then `public_shop_list` only while the accumulated product set remains empty; merge all returned evidence by product ID before classification.

Production calls must remain arrays such as:

```python
subprocess.run(
    ["o2", "launch", "webcli", "browser", session, "eval", script],
    shell=False,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    check=False,
)
```

- [ ] **Step 4: Run tests and verify GREEN**

Expected: URL bytes/characters are preserved and fallback order is exact.

### Task 4: Risk Control and Atomic Checkpoints

**Files:**
- Modify: `tests/test_review_mode.py`
- Modify: `scripts/audit_review_shops.py`

- [ ] **Step 1: Write failing pause and recovery tests**

Cover login loss, captcha, slider, hidden `_____tmd__` iframe, Bridge disconnect, timeout, and incompatible DOM:

```python
class ReviewCheckpointTests(unittest.TestCase):
    def test_risk_condition_saves_checkpoint_and_stops_queue(self):
        browser = RecordingBrowser(failure="hidden_tmd_challenge")
        checkpoint = temporary_checkpoint()
        with self.assertRaises(AuditPaused):
            audit_queue([task("甲店"), task("乙店")], browser, checkpoint, sleeper=lambda _: None)
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], "paused")
        self.assertEqual(saved["current_task"]["shop_name"], "甲店")
        self.assertEqual(browser.visited_shop_names, ["甲店"])
        self.assertNotIn("cookie", json.dumps(saved).lower())

    def test_completed_checkpoint_skips_browser(self):
        checkpoint = checkpoint_with_completed_shop("甲店", "https://shop.taobao.com/a")
        browser = RecordingBrowser()
        result = audit_queue([task("甲店")], browser, checkpoint, sleeper=lambda _: None)
        self.assertEqual(browser.visited_shop_names, [])
        self.assertEqual(result[0].priority, "高")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: queue/checkpoint APIs are absent.

- [ ] **Step 3: Implement versioned atomic checkpoints and stop semantics**

```python
CHECKPOINT_SCHEMA_VERSION = 1

class AuditPaused(RuntimeError):
    def __init__(self, reason: str, checkpoint_path: Path):
        self.reason = reason
        self.checkpoint_path = checkpoint_path
        super().__init__(f"{reason}; checkpoint={checkpoint_path}")

def write_checkpoint_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)

```

Implement `detect_page_failure(inspection: PageInspection) -> str | None` using explicit inspection flags and known risk terms. Implement `audit_queue(tasks, browser, checkpoint_path, sleeper=time.sleep, rng=random.uniform) -> list[ShopAuditResult]`. Persist after each completed shop and before raising `AuditPaused`. Use `rng(18, 22)` only between shops. Reject invalid schema/fingerprint instead of ignoring it. Serialize allowlisted fields only.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Expected: each failure writes a paused checkpoint, prevents later visits, and never returns Low.

### Task 5: Duplicate Reuse and Workbook-Preserving Output

**Files:**
- Modify: `tests/test_review_mode.py`
- Modify: `scripts/review_workbook.py`

- [ ] **Step 1: Write failing grouping, incremental, and preservation tests**

Build a source workbook containing duplicate shops, merged blank rows, styles, formulas, hyperlinks, dimensions, filters, freezes, multiple sheets, and a numeric phone cell:

```python
class ReviewWorkbookOutputTests(unittest.TestCase):
    def test_duplicate_shop_is_audited_once_and_fills_all_blank_duplicates(self):
        source = save_review_fixture(duplicate_shop="卡贝官方旗舰店")
        auditor = FakeAuditor({"卡贝官方旗舰店": medium_result()})
        build_review_output(source, output_path(), owner="张萍云", auditor=auditor)
        self.assertEqual(auditor.calls, ["卡贝官方旗舰店"])
        self.assertEqual(read_result_rows(output_path(), "卡贝官方旗舰店"), [medium_result(), medium_result()])

    def test_existing_result_and_checkpoint_only_audit_new_shop(self):
        source = save_incremental_fixture()
        auditor = FakeAuditor({"新增店": high_result()})
        build_review_output(source, output_path(), owner="张萍云", auditor=auditor,
                            checkpoint=completed_checkpoint_for("旧店"))
        self.assertEqual(auditor.calls, ["新增店"])

    def test_source_is_untouched_and_non_target_invariants_match(self):
        before = workbook_snapshot(source_path())
        build_review_output(source_path(), output_path(), owner="张萍云", auditor=FakeAuditor())
        self.assertEqual(workbook_snapshot(source_path()), before)
        assert_allowed_differences_only(source_path(), output_path())
```

Also assert source/output path equality is rejected, formula cells remain formulas, hyperlinks and styles match, duplicate and blank rows remain, and the numeric phone digits become equivalent text only when necessary.

- [ ] **Step 2: Run tests and verify RED**

Expected: orchestration, snapshot, and preservation functions are absent.

- [ ] **Step 3: Implement grouping, reuse, copy-on-write, and invariants**

```python
def ensure_distinct_paths(source, output):
    source_path = Path(source).resolve()
    output_path = Path(output).resolve()
    if source_path == output_path:
        raise ReviewWorkbookError("output must not overwrite source workbook")
    return source_path, output_path
```

Implement exact public call signatures `provisional_shop_key(shop_name: str) -> str`, `group_pending_rows(rows: Iterable[ReviewRow]) -> list[ReviewTask]`, `workbook_snapshot(path: Path) -> WorkbookSnapshot`, `compare_workbooks(source: Path, output: Path, allowed_cells: set[CellRef]) -> list[str]`, and `build_review_output(source, output, owner=None, checkpoint=None, auditor=None) -> ReviewRunSummary`. `build_review_output` must call `ensure_distinct_paths`, copy with `shutil.copy2`, write only selected blank result cells or digit-equivalent phone text, reopen the output, and reject any invariant differences. Resolve results by stable identity when available and provisional normalized name otherwise. If the same normalized name resolves to conflicting official URLs, return a pending identity conflict and pause.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Expected: duplicate visit count is one, all matching blank rows are filled, source bytes remain unchanged, and invariant comparison passes.

- [ ] **Step 5: Add CLI argument tests and minimal CLI**

Test and implement:

```powershell
python scripts/review_workbook.py INPUT.xlsx --output OUTPUT.xlsx --owner "张萍云" --checkpoint OUTPUT.review-checkpoint.json
python scripts/review_workbook.py INPUT.xlsx --output OUTPUT.xlsx --owner "张萍云" --dry-run
```

`--dry-run` prints semantic mappings and unique pending shops without launching a browser or writing audit conclusions.

### Task 6: Audit-Only Bootstrap and Preflight

**Files:**
- Modify: `tests/test_preflight.py`
- Modify: `scripts/preflight.py`
- Modify: `scripts/bootstrap.ps1`

- [ ] **Step 1: Write failing audit-only environment tests**

```python
def test_audit_only_does_not_require_enterprise_sources(self):
    result = preflight.build_status(
        audit_only=True,
        runtime={"ok": True}, packages={"ok": True},
        doctor=connected_doctor(), taobao={"ok": True, "loggedIn": True},
        qcc={"configured": False}, fengniao={"ready": False},
    )
    self.assertTrue(result["ready"])
    self.assertNotIn("enterprise_sources", result["required_checks"])

def test_normal_mode_still_requires_both_enterprise_sources(self):
    result = preflight.build_status(audit_only=False, qcc={"configured": False},
                                    fengniao={"ready": False}, **ready_browser_inputs())
    self.assertFalse(result["ready"])

def test_bootstrap_rejects_audit_only_with_skip_taobao(self):
    source = (ROOT / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8-sig")
    self.assertIn("$AuditOnly", source)
    self.assertIn("cannot be combined", source)
```

- [ ] **Step 2: Run preflight tests and verify RED**

Run:

```powershell
python -m unittest discover -s tests -p "test_preflight.py" -v
```

Expected: missing `audit_only` behavior and bootstrap switch.

- [ ] **Step 3: Implement isolated audit-only readiness**

Add `--audit-only` to `preflight.py` and `[switch]$AuditOnly` to `bootstrap.ps1`. In audit-only mode require runtime, packages, `o2`, `webcli`, connected Browser Bridge, Taobao login, and review files; skip QCC/Fengniao installation and validation entirely.

Bootstrap argument construction must be equivalent to:

```powershell
if ($AuditOnly -and $SkipTaobaoCheck) {
    throw "-AuditOnly and -SkipTaobaoCheck cannot be combined."
}
if ($AuditOnly) {
    $arguments += "--audit-only"
}
```

Refactor readiness assembly into a pure `build_status` helper so tests do not access the network.

- [ ] **Step 4: Run preflight and legacy regression tests**

Run:

```powershell
python -m unittest discover -s tests -p "test_preflight.py" -v
python -m unittest discover -s tests -p "test_company_source_routing.py" -v
```

Expected: audit-only works without enterprise keys; normal enterprise behavior remains unchanged.

### Task 7: Skill Routing and Review Documentation

**Files:**
- Modify: `tests/test_pipeline.py`
- Create: `references/review-mode.md`
- Create: `references/review-data-contract.md`
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `agents/openai.yaml`

- [ ] **Step 1: Write failing documentation-contract tests**

```python
def test_skill_routes_three_modes_without_merging_list_and_review_modes(self):
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    self.assertIn("审核筛选模式", skill)
    self.assertIn("用户指定名单模式", skill)
    self.assertIn("不得把审核筛选模式并入用户指定名单模式", skill)
    self.assertIn("references/review-mode.md", skill)

def test_review_docs_keep_enterprise_and_evidence_boundaries(self):
    text = (ROOT / "references" / "review-mode.md").read_text(encoding="utf-8")
    for phrase in ["不要求企查查", "不要求风鸟", "唯一商品ID", "18–22秒", "待核验"]:
        self.assertIn(phrase, text)
    self.assertNotIn("近30天销量", text)

def test_agent_metadata_mentions_review_workbooks(self):
    metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    self.assertIn("审核", metadata)
```

- [ ] **Step 2: Run documentation tests and verify RED**

Run:

```powershell
python -m unittest discover -s tests -p "test_pipeline.py" -v
```

Expected: missing review-mode wording or files.

- [ ] **Step 3: Write concise progressive-disclosure documentation**

`SKILL.md` contains the routing decision and non-negotiable mode boundaries. `references/review-mode.md` contains operator steps, pause/resume instructions, browser safety, and output behavior. `references/review-data-contract.md` defines semantic fields, result values, evidence records, stable identity, and checkpoint schema. `README.md` documents the command examples and `-AuditOnly` setup. `agents/openai.yaml` expands discovery text to include review workbooks without becoming a catchall.

Required command examples:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -AuditOnly
python scripts/review_workbook.py "审核筛选.xlsx" --output "审核筛选_已完成.xlsx" --owner "张萍云"
```

- [ ] **Step 4: Run documentation and Skill validation tests**

Run:

```powershell
$env:PYTHONUTF8='1'
python -m unittest discover -s tests -p "test_pipeline.py" -v
python "C:\Users\caotong.888\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

Expected: targeted tests pass and output contains `Skill is valid!`.

### Task 8: Full Regression and Real-Sample Acceptance

**Files:**
- Modify only files already listed if failures reveal in-scope defects
- Generate outside Git: a new timestamped output/checkpoint directory for the real sample

- [ ] **Step 1: Run the complete Python suite in a clean key context**

Temporarily hide user-level enterprise-key environment values only for the subprocess that tests missing-key behavior; do not print or persist their values.

```powershell
python -m unittest discover -s tests -v
```

Expected: all existing and new tests pass.

- [ ] **Step 2: Run Skill and patch validation**

```powershell
$env:PYTHONUTF8='1'
python "C:\Users\caotong.888\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
git diff --check
```

Expected: `Skill is valid!` and no diff errors.

- [ ] **Step 3: Run audit-only environment validation**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -AuditOnly
```

Expected: Python, packages, Chrome, `o2`, `webcli`, Browser Bridge, Taobao login, and Skill structure pass without QCC/Fengniao checks.

- [ ] **Step 4: Dry-run the real workbook before browser access**

```powershell
python scripts/review_workbook.py "D:\caotong.888\Documents\ChatGPT\全网热销\审核筛选.xlsx" --output "D:\caotong.888\Documents\ChatGPT\全网热销\outputs\20260831-review-mode-acceptance\审核筛选_已完成.xlsx" --owner "张萍云" --dry-run
```

Expected: 14 valid rows, 13 unique unresolved shops, duplicate `卡贝官方旗舰店` grouped once, and blank merged placeholders excluded.

- [ ] **Step 5: Run the real serial audit and resume if safely required**

Use the same command without `--dry-run`. Keep daily Chrome open and Browser Bridge connected. Never bypass login or risk control. If paused, verify the checkpoint and resume only after the page is safe; do not restart from the first shop.

Expected: either a verified completed workbook or a correctly paused checkpoint with no false Low result.

- [ ] **Step 6: Verify XLSX structure and formulas**

Run the project verifier plus an explicit ZIP/openpyxl scan:

```powershell
python scripts/verify_job.py "D:\caotong.888\Documents\ChatGPT\全网热销\outputs\20260831-review-mode-acceptance"
python -c "import zipfile; from openpyxl import load_workbook; p=r'D:\caotong.888\Documents\ChatGPT\全网热销\outputs\20260831-review-mode-acceptance\审核筛选_已完成.xlsx'; assert zipfile.is_zipfile(p); w=load_workbook(p, data_only=False); assert all(c.data_type != 'e' for s in w.worksheets for row in s.iter_rows() for c in row)"
```

Expected: valid package, readable worksheets, no formula-error cells, and workbook invariant report passes.

- [ ] **Step 7: Render and visually inspect every worksheet**

Use the bundled spreadsheet runtime to render every sheet. Compare output against the source for column widths, row heights, merges, links, styles, blank rows, and only the approved result/phone changes.

Expected: no clipping, structural drift, missing hyperlinks, changed formulas, or filled placeholder rows.

- [ ] **Step 8: Run a sanitized sensitive-information scan**

Search tracked and untracked implementation files for credential patterns without echoing matching secret values. Scan for forbidden credential-bearing field names and review the filenames/counts only.

Expected: no API key, bearer token, cookie, or Authorization value appears in source, logs, docs, checkpoints, workbook, or Git diff.

- [ ] **Step 9: Prepare the user handoff without commit or push**

Report changed files, exact test counts, audit-only status, output/checkpoint paths, workbook verification, visual review, and any live-access risk. Wait for explicit approval before `git commit` or `git push`.
