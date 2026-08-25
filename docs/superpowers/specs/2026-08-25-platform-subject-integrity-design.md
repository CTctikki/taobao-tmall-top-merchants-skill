# Platform Subject Integrity Design

## Problem

Enterprise fuzzy search can return companies whose names resemble a shop but do not operate it. A previous workbook showed Dongguan and Shenzhen companies for `艾佳运动户外旗舰店`, while the Tmall qualification page identified `义乌市昊杜缝纫电子商务有限公司` with credit code `91330201MA284E2D7K`.

## Root Cause

`audit_storefronts.py` recorded store IDs and type signals but did not persist qualification-page identity fields. `build_workbook.py` trusted any enrichment row marked `selected: true` without checking its evidence type or comparing it with the platform license.

## Resolution

- Capture and parse the Tmall `liangzhao.htm` page into `platform_qualifications.json`.
- Treat a verified platform company name and credit code as the formal subject anchor.
- Allow non-platform selection only for an exact credit-code evidence type.
- Demote mismatched search, trademark, official-site, phone, and email evidence to outreach candidates.
- Separate the workbook columns for platform license identity, confirmed subject, and non-subject outreach candidates.
- Fail final verification if a workbook's confirmed company or credit code differs from a verified platform qualification.

## Safety

Qualification-page captcha, slider, or hidden `_____tmd__` challenges stop the workflow. The system does not bypass risk controls or replace a missing platform subject with the first company-search result.
