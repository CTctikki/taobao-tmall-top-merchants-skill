# User-Provided Shop List Mode Design

## Goal

Add a second operating mode for requests where the user already supplies shops as names, URLs, pasted text, tables, spreadsheets, or mixed content. Codex must normalize that input and produce the final outreach workbook without running Taobao discovery or assortment auditing.

## Mode Selection

- Use category discovery mode when the user supplies only a category and asks Codex to find top merchants.
- Use user-provided list mode when the user supplies one or more target shops, shop URLs, or an attachment containing target shops.
- If the input contains both a category and an explicit shop list, treat the list as authoritative unless the user explicitly asks to expand it.

## Processing Rules

Codex extracts and deduplicates shop name, category, platform, shop URL, supplied company, supplied contact details, owner, and source. It preserves the raw input for traceability. Every user-specified shop enters the formal outreach sheet; missing fields never remove a shop.

This mode must not run `mine_taobao.py`, `audit_shops.py`, or fabricate target SPU, assortment share, payment lower bounds, or Top30 status. The workbook must state that the list is user-specified and has not passed the normal category-discovery admission audit.

## Company Evidence

Company enrichment follows the existing evidence hierarchy. Multiple candidates remain separate and `selected: false` until platform qualifications, exact credit-code evidence, or another strong evidence chain closes the relationship. Candidate contacts may be shown for outreach but cannot prove the shop operator.

## Output

The final workbook keeps six logical sheets: overview, formal outreach merchants, subject verification, unresolved fields, original input, and methodology. If an existing workbook template is more appropriate, Codex may adapt the sheet names while preserving the same information and evidence boundaries.

## Safety and Recovery

Prefer headless processing. Reuse available enterprise-query results and stop cleanly on quota exhaustion. Never trigger Taobao pages merely to complete company contacts. Preserve unresolved shops and describe the next verification action.
