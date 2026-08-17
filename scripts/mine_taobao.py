import argparse
import json
import time
from collections import defaultdict
from datetime import datetime

from common import classify_item, clean_title, ensure_job_dir, load_job, make_search_script, open_search, platform_name, run_o2, write_json


def summarize(job, raw):
    buckets = defaultdict(lambda: {"items": {}, "queries": set(), "platform_counts": defaultdict(int), "electric_seen": 0, "accessory_seen": 0})
    for query, rows in raw.items():
        for item in rows:
            classification = classify_item(item.get("title"), job)
            if not classification["category_match"] or not item.get("shop"):
                continue
            key = item["shop"]
            bucket = buckets[key]
            bucket["shop_name"] = item["shop"]
            bucket["shop_url"] = item.get("shop_url") or bucket.get("shop_url", "")
            bucket["user_id"] = item.get("user_id") or bucket.get("user_id", "")
            bucket["queries"].add(query)
            bucket["platform_counts"][platform_name(item)] += 1
            bucket["electric_seen"] += int(classification["electric"])
            bucket["accessory_seen"] += int(classification["accessory"])
            if classification["relevant"]:
                item_id = item.get("item_id") or f'{clean_title(item.get("title"))}::{item["shop"]}'
                bucket["items"].setdefault(item_id, {**item, "title": clean_title(item.get("title"))})
    results = []
    for bucket in buckets.values():
        platform = max(bucket["platform_counts"], key=bucket["platform_counts"].get)
        results.append({
            "category": job["category"],
            "shop_name": bucket["shop_name"],
            "platform": platform,
            "discovered_target_spu": len(bucket["items"]),
            "electric_items_seen": bucket["electric_seen"],
            "accessory_items_seen": bucket["accessory_seen"],
            "queries": sorted(bucket["queries"]),
            "shop_url": bucket.get("shop_url", ""),
            "user_id": bucket.get("user_id", ""),
            "items": sorted(bucket["items"].values(), key=lambda item: item.get("item_id") or item.get("title")),
        })
    return sorted(results, key=lambda row: (-row["discovered_target_spu"], row["shop_name"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--session", default="top_merchants_mining")
    parser.add_argument("--pages", type=int)
    parser.add_argument("--interval", type=int)
    args = parser.parse_args()
    job_dir = ensure_job_dir(args.job_dir)
    job = load_job(job_dir)
    raw_path = job_dir / "discovery_raw.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.exists() else {}
    pages = args.pages or job.get("pages", 2)
    interval = args.interval or job.get("interval_seconds", 20)
    for index, query in enumerate(job["queries"], 1):
        if query in raw:
            print(f"[{index}/{len(job['queries'])}] cached {query}", flush=True)
            continue
        print(f"[{index}/{len(job['queries'])}] {query}", flush=True)
        open_search(args.session, query)
        time.sleep(7)
        rows = run_o2(args.session, "eval", make_search_script(query, pages))
        raw[query] = rows
        write_json(raw_path, raw)
        print(f"  returned={len(rows)}", flush=True)
        if index < len(job["queries"]):
            time.sleep(interval)
    candidates = summarize(job, raw)
    write_json(job_dir / "candidates.json", {
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "category": job["category"],
        "queries": job["queries"],
        "candidates": candidates,
    })
    print(f"candidates={len(candidates)}")


if __name__ == "__main__":
    main()

