import argparse
import json
import time
from datetime import datetime

from common import classify_item, clean_title, ensure_job_dir, load_job, make_search_script, normalize, open_search, platform_name, run_o2, write_json


def audit_rows(job, target, rows):
    items = {}
    platform_counts = {"淘宝": 0, "天猫": 0}
    for item in rows:
        if normalize(item.get("shop")) != normalize(target["shop_name"]):
            continue
        platform_counts[platform_name(item)] += 1
        item_id = item.get("item_id") or f'{clean_title(item.get("title"))}::{target["shop_name"]}'
        items.setdefault(item_id, item)
    relevant, electric, accessories, unrelated = [], [], [], []
    for item in items.values():
        classification = classify_item(item.get("title"), job)
        output = {**item, "title": clean_title(item.get("title"))}
        if classification["relevant"]:
            relevant.append(output)
        elif classification["accessory"] and classification["category_match"]:
            accessories.append(output)
        elif classification["electric"] and classification["category_match"]:
            electric.append(output)
        else:
            unrelated.append(output)
    total = len(items)
    share = len(relevant) / total if total else 0
    platform = max(platform_counts, key=platform_counts.get) if total else target["platform"]
    passes = len(relevant) >= job["min_spu"] and share >= job["min_share"]
    grade = "高匹配" if passes and share >= job["high_match_share"] else "达标" if passes else "不达标"
    return {
        "category": job["category"],
        "shop_name": target["shop_name"],
        "platform": platform,
        "expected_platform": target["platform"],
        "exact_shop_spu_seen": total,
        "target_spu": len(relevant),
        "electric_spu": len(electric),
        "accessory_spu": len(accessories),
        "unrelated_spu": len(unrelated),
        "target_share": round(share, 4),
        "passes_minimum": passes,
        "match_grade": grade,
        "shop_url": next((item.get("shop_url") for item in items.values() if item.get("shop_url")), target.get("shop_url", "")),
        "user_id": next((item.get("user_id") for item in items.values() if item.get("user_id")), target.get("user_id", "")),
        "target_items": relevant,
        "electric_samples": electric[:8],
        "accessory_samples": accessories[:8],
        "unrelated_samples": unrelated[:8],
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--session", default="top_merchants_audit")
    parser.add_argument("--pages", type=int)
    parser.add_argument("--interval", type=int)
    parser.add_argument("--max-shops", type=int)
    args = parser.parse_args()
    job_dir = ensure_job_dir(args.job_dir)
    job = load_job(job_dir)
    candidate_data = json.loads((job_dir / "candidates.json").read_text(encoding="utf-8"))
    candidates = [row for row in candidate_data["candidates"] if row["discovered_target_spu"] >= job["minimum_discovery_spu"]]
    candidates = candidates[: args.max_shops or job.get("max_candidate_shops", 40)]
    output_path = job_dir / "assortment_audit.json"
    existing = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    pages = args.pages or job.get("pages", 2)
    interval = args.interval or job.get("interval_seconds", 20)
    for index, target in enumerate(candidates, 1):
        shop_name = target["shop_name"]
        if shop_name in existing:
            print(f"[{index}/{len(candidates)}] cached {shop_name}", flush=True)
            continue
        print(f"[{index}/{len(candidates)}] {target['platform']} / {shop_name}", flush=True)
        open_search(args.session, shop_name)
        time.sleep(7)
        rows = run_o2(args.session, "eval", make_search_script(shop_name, pages))
        existing[shop_name] = audit_rows(job, target, rows)
        write_json(output_path, existing)
        record = existing[shop_name]
        print(f"  target={record['target_spu']}/{record['exact_shop_spu_seen']} share={record['target_share']:.1%} {record['match_grade']}", flush=True)
        if index < len(candidates):
            time.sleep(interval)
    print(f"passed={sum(row['passes_minimum'] for row in existing.values())} audited={len(existing)}")


if __name__ == "__main__":
    main()

