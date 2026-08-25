import argparse
import json
import re
import time
import tomllib
from pathlib import Path

import requests

from common import ensure_job_dir, write_json
from configure_enterprise_keys import QCC_ENV_NAME, normalize_qcc_auth, read_user_environment


def load_qcc_server(config_path, server_name="qcc-company"):
    config = tomllib.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    server = config.get("mcp_servers", {}).get(server_name)
    if not server:
        raise RuntimeError(f"{server_name} MCP is not configured; run preflight.py")
    auth = read_user_environment(QCC_ENV_NAME)
    if not auth:
        auth = server.get("http_headers", {}).get("Authorization", "")
    if not auth:
        raise RuntimeError("QCC authorization missing; set QCC_AUTH or configure local MCP headers")
    return server["url"], auth


class QccClient:
    def __init__(self, url, auth):
        self.url = url
        self.headers = {"Authorization": normalize_qcc_auth(auth), "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        self.request_id = 0

    def call(self, name, arguments):
        self.request_id += 1
        response = requests.post(self.url, headers=self.headers, json={"jsonrpc": "2.0", "id": self.request_id, "method": "tools/call", "params": {"name": name, "arguments": arguments}}, timeout=90)
        response.raise_for_status()
        response.encoding = "utf-8"
        for event in response.text.strip().split("\n\n"):
            parts = [line[6:] for line in event.splitlines() if line.startswith("data: ")]
            if not parts:
                continue
            envelope = json.loads("\n".join(parts))
            if "error" in envelope:
                error = envelope["error"]
                if error.get("code") == 300008:
                    raise RuntimeError("QCC credit balance insufficient; recharge or switch token")
                return {"error": error}
            for item in envelope.get("result", {}).get("content", []):
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except json.JSONDecodeError:
                        return {"raw": item["text"]}
        return {"error": "no SSE data"}


def brand_query(shop_name):
    value = shop_name
    suffixes = ["官方旗舰店", "旗舰店", "专卖店", "专营店", "品牌店", "官方企业店", "工厂企业店", "企业店", "工厂店", "直营店", "淘宝店", "店"]
    for suffix in suffixes:
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    value = re.sub(r"\s+", "", value)
    return value or shop_name


def discover(job_dir, client, interval):
    audit = json.loads((job_dir / "assortment_audit.json").read_text(encoding="utf-8"))
    output_path = job_dir / "company_candidates.json"
    output = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    targets = [row for row in audit.values() if row.get("passes_minimum")]
    for index, row in enumerate(targets, 1):
        shop = row["shop_name"]
        if shop in output:
            print(f"[{index}/{len(targets)}] cached {shop}", flush=True)
            continue
        query = brand_query(shop)
        result = client.call("get_company_by_query", {"searchKey": query})
        output[shop] = {"query": query, "result": result}
        write_json(output_path, output)
        companies = result.get("企业信息", []) if isinstance(result, dict) else []
        print(f"[{index}/{len(targets)}] {shop}: {[(x.get('企业名称'), x.get('状态')) for x in companies[:5]]}", flush=True)
        if index < len(targets):
            time.sleep(interval)


def load_subjects(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        rows = []
        for shop, value in data.items():
            if isinstance(value, str):
                rows.append({"shop_name": shop, "company": value})
            elif isinstance(value, dict):
                rows.append({"shop_name": shop, **value})
        return rows
    return data


def enrich(job_dir, client, subjects_path, interval):
    subjects = load_subjects(subjects_path)
    output_path = job_dir / "company_enrichment.json"
    output = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    cache = {item.get("company"): item for values in output.values() for item in values if item.get("company")}
    for index, subject in enumerate(subjects, 1):
        shop = subject["shop_name"]
        company = subject["company"]
        output.setdefault(shop, [])
        if any(item.get("company") == company for item in output[shop]):
            print(f"[{index}/{len(subjects)}] cached {shop} / {company}", flush=True)
            continue
        if company in cache:
            record = {**cache[company], **{key: value for key, value in subject.items() if key not in {"registration", "contact"}}}
        else:
            registration = client.call("get_company_registration_info", {"searchKey": company})
            time.sleep(interval)
            contact = client.call("get_contact_info", {"searchKey": company, "excludeInvalidPhone": True})
            record = {**subject, "registration": registration, "contact": contact}
            cache[company] = record
        output[shop].append(record)
        write_json(output_path, output)
        print(f"[{index}/{len(subjects)}] enriched {shop} / {company}", flush=True)
        if index < len(subjects):
            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["discover", "enrich"])
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--subjects")
    parser.add_argument("--config", default=str(Path.home() / ".codex/config.toml"))
    parser.add_argument("--interval", type=float, default=0.8)
    args = parser.parse_args()
    job_dir = ensure_job_dir(args.job_dir)
    url, auth = load_qcc_server(args.config)
    client = QccClient(url, auth)
    if args.action == "discover":
        discover(job_dir, client, args.interval)
    else:
        subjects = args.subjects or str(job_dir / "subjects.json")
        if not Path(subjects).exists():
            raise FileNotFoundError(f"Missing {subjects}; review company_candidates.json and create confirmed subject mappings")
        enrich(job_dir, client, subjects, args.interval)


if __name__ == "__main__":
    main()
