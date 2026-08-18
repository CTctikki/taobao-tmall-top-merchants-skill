import argparse
import json
import sys


EVIDENCE_PRIORITY = [
    "platform_qualification",
    "credit_code_match",
    "trademark_or_official_site",
    "company_name_similarity",
    "phone_or_email",
]


def step(action, source, purpose):
    return {"action": action, "source": source, "purpose": purpose}


def company_lookup_plan(
    has_exact_identity,
    qcc_available=True,
    fengniao_available=True,
):
    if not qcc_available and not fengniao_available:
        raise ValueError("At least one enterprise data source is required")

    mode = "exact_identity" if has_exact_identity else "fuzzy_identity"
    steps = []
    if qcc_available and fengniao_available:
        if has_exact_identity:
            steps.append(step("qcc_verify", "qcc", "精确核验工商主体与标准字段"))
        else:
            steps.append(step("fengniao_discover", "fengniao", "按店铺名或品牌名模糊发现候选主体"))
            steps.append(step("qcc_verify", "qcc", "用候选公司全称或信用代码精确核验"))
        steps.append(step("fengniao_supplement", "fengniao", "补齐企查查缺失字段与品牌关联证据"))
    elif qcc_available:
        action = "qcc_verify" if has_exact_identity else "qcc_discover"
        purpose = "精确核验工商主体" if has_exact_identity else "模糊发现并核验企业候选"
        steps.append(step(action, "qcc", purpose))
    else:
        action = "fengniao_verify" if has_exact_identity else "fengniao_discover"
        purpose = "按精确主体查询并补齐字段" if has_exact_identity else "按店铺名或品牌名模糊发现候选主体"
        steps.append(step(action, "fengniao", purpose))

    return {
        "mode": mode,
        "steps": steps,
        "cross_source_review_pending": True,
        "single_source_fallback": not (qcc_available and fengniao_available),
        "evidence_priority": EVIDENCE_PRIORITY,
        "selection_rule": "phone_or_email_never_confirms_subject",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    identity = parser.add_mutually_exclusive_group()
    identity.add_argument("--company-name")
    identity.add_argument("--credit-code")
    identity.add_argument("--brand-or-shop")
    parser.add_argument("--no-qcc", action="store_true")
    parser.add_argument("--no-fengniao", action="store_true")
    args = parser.parse_args()
    result = company_lookup_plan(
        has_exact_identity=bool(args.company_name or args.credit_code),
        qcc_available=not args.no_qcc,
        fengniao_available=not args.no_fengniao,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
