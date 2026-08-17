import argparse
import json
import re
import time
from pathlib import Path

from common import ensure_job_dir, write_json
from enrich_companies import QccClient, load_qcc_server


def normalize_mark(value):
    return re.sub(r"\s+", "", str(value or "")).lower()


def match_trademarks(marks, brand_terms, relevant_classes=None):
    terms = [normalize_mark(term) for term in brand_terms if term]
    classes = [str(value) for value in relevant_classes or []]
    matches = []
    for mark in marks:
        name = normalize_mark(mark.get("商标名称"))
        mark_class = str(mark.get("国际分类") or "")
        if terms and not any(term in name for term in terms):
            continue
        if classes and not any(mark_class.startswith(value) or f"{value}类" in mark_class for value in classes):
            continue
        matches.append(mark)
    return matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--mapping")
    parser.add_argument("--config", default=str(Path.home() / ".codex/config.toml"))
    parser.add_argument("--interval", type=float, default=0.8)
    args = parser.parse_args()
    job_dir = ensure_job_dir(args.job_dir)
    mapping_path = Path(args.mapping) if args.mapping else job_dir / "trademark_queries.json"
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Missing {mapping_path}. Create a mapping of shop_name to brand_terms, relevant_classes and candidate companies."
        )
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    url, auth = load_qcc_server(args.config, "qcc-ipr")
    client = QccClient(url, auth)
    output_path = job_dir / "company_trademarks.json"
    output = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    for shop, config in mapping.items():
        output.setdefault(shop, [])
        known = {row.get("company") for row in output[shop]}
        for company in config.get("companies", []):
            if company in known:
                continue
            result = client.call("get_trademark_info", {"searchKey": company, "status": ["已注册"]})
            marks = result.get("商标信息", []) if isinstance(result, dict) else []
            matched = match_trademarks(marks, config.get("brand_terms", []), config.get("relevant_classes"))
            output[shop].append({
                "company": company,
                "summary": result.get("摘要", "") if isinstance(result, dict) else "",
                "matched": matched,
            })
            write_json(output_path, output)
            print(f"{shop} / {company}: matched={len(matched)}", flush=True)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()

