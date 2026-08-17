import argparse
import re
from datetime import datetime
from pathlib import Path

from common import ensure_job_dir, write_json


PROFILES = {
    "按摩梳": {
        "queries": [
            "按摩梳",
            "头皮按摩梳",
            "头部按摩梳",
            "气垫按摩梳",
            "经络按摩梳",
            "木质按摩梳",
            "檀木按摩梳",
            "洗头按摩梳",
            "头皮清洁按摩梳",
        ],
        "include_patterns": [
            "按摩梳",
            "头皮梳",
            "经络梳",
            "气垫梳",
            "头疗梳",
            "洗头梳",
            "头皮按摩",
        ],
        "exclude_patterns": ["宠物|猫咪|狗狗|犬用", "假发|娃娃|模型", "教程|维修|租赁"],
        "accessory_patterns": ["替换头|替换齿|配件|收纳袋|包装盒|充电线|底座|保护套|梳套"],
        "electric_patterns": ["电动|充电|插电|红光|激光|震动|智能|射频|微电流"],
        "exclude_electric": False,
        "scope_note": "按摩梳类目默认同时保留手动与电动按摩梳；排除宠物梳、假发梳、配件和非商品。",
    }
}


def generic_profile(category):
    return {
        "queries": [category],
        "include_patterns": [re.escape(category)],
        "exclude_patterns": ["宠物|猫咪|狗狗|犬用", "教程|维修|租赁|模型|玩具"],
        "accessory_patterns": ["配件|替换|收纳袋|包装盒|说明书|保护套"],
        "electric_patterns": ["电动|充电|插电|恒温|加热|红光|激光|智能|震动"],
        "exclude_electric": False,
        "scope_note": "默认保留命中类目词的成品，排除配件、宠物用品和非商品；请抽查后完善同义词。",
    }


def create_job(category, job_dir, queries=None, exclude_electric=None):
    profile = dict(PROFILES.get(category, generic_profile(category)))
    if queries:
        profile["queries"] = queries
    if exclude_electric is not None:
        profile["exclude_electric"] = exclude_electric
    job = {
        "category": category,
        **profile,
        "min_spu": 10,
        "min_share": 0.30,
        "high_match_share": 0.50,
        "pages": 2,
        "interval_seconds": 20,
        "minimum_discovery_spu": 3,
        "max_candidate_shops": 40,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_json(ensure_job_dir(job_dir) / "job.json", job)
    return job


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category")
    parser.add_argument("--job-dir")
    parser.add_argument("--query", action="append", dest="queries")
    electric = parser.add_mutually_exclusive_group()
    electric.add_argument("--exclude-electric", action="store_true")
    electric.add_argument("--include-electric", action="store_true")
    args = parser.parse_args()
    job_dir = args.job_dir or str(Path("work") / re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", args.category))
    exclude_electric = True if args.exclude_electric else False if args.include_electric else None
    job = create_job(args.category, job_dir, args.queries, exclude_electric)
    print(Path(job_dir).resolve() / "job.json")
    print(job["scope_note"])


if __name__ == "__main__":
    main()

