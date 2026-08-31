# Independent Merchant Review Mode Design

## Goal

Add a third, independent mode for reviewing shops already listed in a business workbook. It visits each pending shop, verifies category-relevant SPU and public high-sales evidence, assigns introduction priority, and writes results into a copy of the source workbook.

The three modes remain separate:

- Category discovery discovers Top merchants and performs enterprise-subject enrichment.
- User-provided list mode normalizes supplied shops without opening Taobao or inferring SPU.
- Review mode audits listed shops and does not perform enterprise-subject enrichment.

The implementation must not modify `jd-taobao-hot-sales` or weaken existing enterprise-source, platform-license, and subject-integrity rules.

## Confirmed Rules

### High-Sales Evidence

A product qualifies only when a public page visibly shows `人付款`, `已售`, or `总销量` with a parsed lower bound of at least 10,000.

- `1万+人付款`, `10万+人付款`, and `总销量：100万+` qualify.
- `已售1000+件` and a lower bound of `9999` do not qualify.
- A lower bound of `10000` qualifies.

The recorded number is a public display lower bound, not a claim about 30-day sales, GMV, paid traffic, or margin.

### Priority

- High: relevant unique SPU >= 20 and high-sales links >= 3.
- Medium: not High, but relevant unique SPU >= 15 and high-sales links >= 1.
- Low: relevant unique SPU < 15 or the Medium requirements are not met.
- Pending: page failure, access interruption, unclear identity/category, or insufficient evidence. These conditions must never become Low.

High and Medium profile text:

`待业务复核｜类目与销量证据已核验；主图能力待人工确认；非KA待业务复核；付费/毛利仅以公开销量代理`

Low profile text:

`否｜相关SPU或高销链接未达到引入门槛；其余画像维度待复核`

For failures or insufficient evidence, both result columns receive `待核验`. The priority column otherwise receives `高`, `中`, or `低`.

### Evidence Boundaries

- Count relevant SPU by unique Taobao/Tmall product ID, never page rows or pagination totals.
- Do not auto-judge image quality; state `主图能力待人工确认`.
- Without an explicit KA list, state `非KA待业务复核`.
- Sales are only a business-scale proxy; do not claim true paid traffic, GMV, or margin.
- Enterprise candidates and contact details cannot prove shop identity, category fit, or priority.

## Architecture

Use a two-stage pipeline.

### `scripts/review_workbook.py`

- Discover semantic columns and header rows.
- Select pending rows for the current owner.
- Preserve blank placeholders and duplicate rows.
- Group duplicate shops into one audit task.
- Reuse complete workbook results and checkpoints.
- Copy the source workbook, write allowed cells, and verify invariants.
- Accept a fake auditor for browser-free unit tests.

### `scripts/audit_review_shops.py`

- Consume unique pending shop tasks.
- Visit shops serially through `o2 + webcli + Browser Bridge` using daily Chrome.
- Navigate long URLs without shell parsing.
- Apply three-level page fallback.
- Extract product identity, title, sales display, source, and final URL.
- Deduplicate products, classify results, and save checkpoints.
- Pause on authentication, risk-control, Bridge, or compatibility failures.

It must not call `enrich_companies.py`, `run_fengniao.py`, or enterprise-subject workflows.

Add `references/review-mode.md`, `references/review-data-contract.md`, and `tests/test_review_mode.py`. Update `SKILL.md`, `README.md`, `agents/openai.yaml`, `scripts/bootstrap.ps1`, and `scripts/preflight.py`; extend `scripts/common.py` only for small shared utilities.

Route to review mode only when the user asks to audit, screen, or fill review conclusions for shops already listed. A plain supplied outreach list remains in user-provided list mode unless shop-page auditing is explicitly requested.

## Workbook Discovery

Scan worksheets without fixed column letters. Search a bounded leading area for a row containing the required semantic fields: shop name, introduction-profile result, introduction priority, and owner. Shop URL, category, phone, and notes/evidence are optional.

Normalize aliases by trimming whitespace and harmless punctuation/line breaks. Ambiguous mappings, duplicate required semantic columns, or missing required fields stop with a diagnostic rather than guessing.

Owner selection order:

1. Explicit `--owner`.
2. Automatically use the only normalized owner among eligible rows.
3. If multiple owners remain, stop and request `--owner`.

A row is eligible only when its shop name is nonempty, owner matches, and both review cells are empty. Rows with both review cells populated are complete. A row with only one populated review cell remains untouched, is reported as inconsistent, and does not trigger browser access. Blank and merged subordinate rows remain blank.

Complete duplicate results may fill blank duplicate rows without browser access. Partial results may not propagate. Completed checkpoints may fill matching rows; paused or incomplete checkpoints may restore progress but are not completed reviews. Thus only newly appended, unresolved shops enter the browser queue.

## Identity and Duplicates

Before navigation, provisionally group rows by normalized shop name. Normalization handles whitespace, case, common platform-suffix punctuation, and Unicode-width differences without deleting meaningful brand words.

After navigation, the stable identity is `normalized shop name + normalized final official shop URL`. The checkpoint keeps supplied, redirect, and previous URL aliases so changed advertising links can reuse evidence.

All original duplicate rows remain and receive the same result. If one normalized name resolves to conflicting official shop URLs, pause as an identity conflict instead of silently selecting or merging one.

## Browser Audit

### Environment and Timing

Reuse daily Chrome through Browser Bridge. Visit shops strictly serially and wait a random 18–22 seconds between different shops. Do not use parallel tabs, account switching, risk-control bypass, or high-frequency restarts.

### Safe Navigation

Never pass a long advertising URL through a shell command string. Browser commands use argument arrays with `shell=False`.

For `click.simba.taobao.com` and similar URLs:

1. Open a controlled Taobao page.
2. Pass the target URL as serialized data.
3. Navigate with page-side `location.assign(...)`.

Chinese characters, percent-encoding, fragments, and every `&` parameter must remain intact. Never interpolate the raw URL as executable shell or JavaScript source.

### Page Fallback

For each unique shop:

1. Open the supplied entry and resolve the official shop page.
2. If no product evidence appears, navigate on the same origin to `/search.htm?search=y&orderType=hotsell_desc`.
3. If still empty, use a public Taobao shop-list page for supplementary verification.

Each source records requested URL, final URL, source type, retrieval time, product ID/URL/title, public sales text, parsed lower bound, and category-relevance decision. Merge evidence by product ID; never treat pagination such as `1/25页` as a product count.

Use an explicit category column when present. Every counted product needs a repeatable match to configured category terms. If no category is supplied, derive one only when navigation and titles establish one stable product family. Mixed or unclear stores receive `待核验`. Record category terms and the match reason for each counted product.

### Stop Conditions

Detect login loss, captcha, slider verification, visible or hidden `__tmd__` challenge iframe, Bridge disconnection, navigation timeout, incompatible page structure, and shop-identity conflict.

On detection:

1. Save the current URL and non-sensitive failure metadata.
2. Save completed shops and current progress.
3. Mark the task paused, never Low.
4. Stop before visiting another shop.

Do not store cookies, Authorization headers, API keys, browser storage, or raw secrets.

## Checkpoint Contract

The default checkpoint path derives from the output workbook and can be overridden. Use versioned JSON and atomic replacement.

Top-level fields include schema version, source fingerprint, selected owner, run status, timestamps, completed identities, aliases, pending queue, current paused task, and non-sensitive failure reason.

Each shop record includes display/normalized name, source row references, supplied URLs, final official URL, category terms, page-source records, deduplicated evidence, relevant SPU count, high-sales count, result, priority, and completeness status.

Write checkpoints through a temporary file, flush, then replace. A corrupt or incompatible checkpoint stops with a diagnostic and is never silently ignored.

## Workbook Preservation

The source workbook is read-only and must never be overwritten. The resolved output path must differ from the source. Copy the source package, then edit the copy with settings that preserve formulas and VBA when applicable.

Allowed cell changes are limited to:

- Blank introduction-profile cells selected for processing or reuse.
- Blank introduction-priority cells selected for processing or reuse.
- Numeric phone cells whose displayed digits would otherwise be damaged; convert only to equivalent text without changing digits.

Do not change unrelated values, formulas, hyperlinks, styles, number formats, row heights, column widths, merges, frozen panes, filters, sheet order, hidden state, print settings, or duplicate rows.

Capture a workbook invariant snapshot before writing. After saving and reopening, compare source and output and reject any unapproved difference. Also verify:

- The XLSX is a valid ZIP package.
- Workbook relationships and worksheets are readable.
- Formula cells remain formulas and gain no new formula-error literals.
- Hyperlink targets/display text remain intact.
- Blank placeholders and merged subordinate cells remain blank.

## Environment Entry Point

Add:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -AuditOnly
```

Audit-only checks supported Python, required packages, Chrome, `o2`, `webcli`, Browser Bridge, Taobao login state, and review-mode Skill structure. It does not install, request, or validate Qichacha or RiskBird keys. Existing modes retain their enterprise-data requirements.

`-AuditOnly` and `-SkipTaobaoCheck` are incompatible; reject the combination clearly.

## Command Interface

The orchestration command accepts source workbook, output workbook, optional owner, optional checkpoint, optional category configuration, and optional KA list. A dry-run/list option may report mappings and pending unique shops without opening a browser, but must never fabricate audit results.

## Testing Strategy

Implementation follows RED-GREEN-REFACTOR. Required automated behavior:

1. Semantic headers without fixed letters.
2. Owner and blank-review filtering.
3. Blank/merged placeholder exclusion.
4. Duplicate shops audited once and filled everywhere.
5. Complete workbook/checkpoint result reuse.
6. Browser access only for newly appended shops.
7. Parsing `1万+人付款`, `10万+人付款`, `总销量：100万+`, and `已售1000+件`.
8. Boundary behavior for 9999 and 10000.
9. Unique product-ID deduplication.
10. High, Medium, Low, and Pending classification.
11. Home-page fallback to in-shop hot-sales search.
12. In-shop fallback to a public shop-list page.
13. Long Chinese, percent-encoded, multi-`&` URL safety.
14. Checkpoint-and-pause for login, captcha, hidden challenge iframe, Bridge loss, timeout, and incompatible pages.
15. Source workbook never overwritten.
16. No unapproved cell-value changes.
17. Preservation of duplicates, blanks, styles, hyperlinks, dimensions, merges, filters, freezes, and sheet order.
18. Valid output XLSX with preserved formulas and no new formula errors.
19. Audit-only bootstrap without enterprise keys.
20. Existing modes still enforce enterprise keys and subject integrity.

Use deterministic browser adapters/fakes for automated tests. Reserve live Chrome for final real-sample acceptance, obeying timing and stop rules.

## Acceptance Run

Use the real input only after automated tests pass:

`D:\caotong.888\Documents\ChatGPT\全网热销\审核筛选.xlsx`

The manually completed workbook is only a format/regression reference. Never copy or hard-code its conclusions.

Final acceptance includes:

- All Python tests.
- Skill `quick_validate.py` with UTF-8 enabled where Windows requires it.
- Audit-only bootstrap and preflight.
- Real-sample end-to-end run.
- Confirmation that 14 valid rows produce 13 unique tasks before reuse.
- Confirmation that both `卡贝官方旗舰店` rows share one audited result.
- XLSX ZIP-integrity check.
- Formula-error scan.
- Visual inspection of every worksheet.
- `git diff --check`.
- Sensitive-information scan.

Any live Taobao interruption must produce a resumable checkpoint and a clearly reported pending state. It does not justify a false Low result or a claim that the end-to-end run completed.

## Delivery Boundaries

- Do not modify or commit files outside this repository.
- Do not modify historical JSON, PDF, PNG, Excel, or work data.
- Put generated sample output in a new output directory; do not commit it unless explicitly requested.
- Do not commit or push until the user approves the completed implementation and explicitly requests it.
- Never write API keys, bearer tokens, cookies, or Authorization headers to code, logs, workbooks, documentation, Git, or the final response.
