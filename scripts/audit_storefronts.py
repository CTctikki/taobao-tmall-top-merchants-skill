import argparse
import json
import time
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

from common import ensure_job_dir, run_o2, write_json


def page_script():
    return (
        "(()=>{const text=document.body?document.body.innerText:'';"
        "const lines=Array.from(new Set(text.split(/\\n+/).map(function(s){return s.trim()}).filter(Boolean)));"
        "const terms=['企业店','个人店','淘宝店','天猫','查看资质','营业执照','店铺资质'];"
        "const signals=lines.filter(function(s){return s.length<=40&&terms.some(function(t){return s.includes(t)})}).slice(0,120);"
        "const resources=performance.getEntriesByType('resource').map(function(e){return e.name}).filter(function(u){return u.includes('mtop.taobao.shop.simple.fetch')}).slice(-3);"
        "const config=window.shop_config||{};const blocked=/验证码|访问被拒绝|滑动验证/.test(text);"
        "return {url:location.href,title:document.title,signals:signals,shopFetch:resources,htmlSellerId:String(config.userId||''),htmlShopId:String(config.shopId||''),blocked:blocked}})()"
    )


def parse_shop_fetch(urls):
    for url in reversed(urls or []):
        try:
            raw = parse_qs(urlparse(url).query).get("data", [""])[0]
            data = json.loads(unquote(raw))
            return str(data.get("shopId") or ""), str(data.get("sellerId") or "")
        except (ValueError, TypeError, json.JSONDecodeError):
            continue
    return "", ""


def shop_type(platform, title, signals):
    text = " ".join([title, *(signals or [])])
    if platform == "天猫" or "天猫Tmall.com" in title:
        return "天猫店"
    if "企业店" in text or "营业执照" in text:
        return "淘宝企业店"
    return "淘宝店（企业/个人待核验）"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--session", default="top_merchants_storefront")
    parser.add_argument("--interval", type=int, default=12)
    args = parser.parse_args()
    job_dir = ensure_job_dir(args.job_dir)
    audit = json.loads((job_dir / "assortment_audit.json").read_text(encoding="utf-8"))
    targets = [row for row in audit.values() if row.get("passes_minimum")]
    output_path = job_dir / "storefronts.json"
    existing = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    for index, target in enumerate(targets, 1):
        shop_name = target["shop_name"]
        if shop_name in existing and existing[shop_name].get("official_url"):
            print(f"[{index}/{len(targets)}] cached {shop_name}", flush=True)
            continue
        user_id = target.get("user_id") or ""
        if not user_id:
            existing[shop_name] = {"shop_name": shop_name, "expected_platform": target["platform"], "official_url": target.get("shop_url", ""), "shop_id": "", "seller_id": "", "shop_type": f'{target["platform"]}（页面未取得）', "status": "missing_user_id"}
            write_json(output_path, existing)
            continue
        run_o2(args.session, "open", f"https://store.taobao.com/category.htm?appUid={user_id}")
        time.sleep(7)
        page = run_o2(args.session, "eval", page_script())
        if page.get("blocked"):
            raise RuntimeError(f"Taobao risk control detected at {shop_name}; stop and ask user to verify")
        fetch_shop_id, fetch_seller_id = parse_shop_fetch(page.get("shopFetch"))
        existing[shop_name] = {
            "shop_name": shop_name,
            "expected_platform": target["platform"],
            "official_url": page.get("url") or target.get("shop_url", ""),
            "page_title": page.get("title", ""),
            "user_id": user_id,
            "shop_id": fetch_shop_id or page.get("htmlShopId", ""),
            "seller_id": fetch_seller_id or page.get("htmlSellerId", ""),
            "shop_type": shop_type(target["platform"], page.get("title", ""), page.get("signals")),
            "signals": page.get("signals") or [],
            "status": "captured",
            "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        write_json(output_path, existing)
        print(f"[{index}/{len(targets)}] {shop_name} shopId={existing[shop_name]['shop_id'] or '-'} sellerId={existing[shop_name]['seller_id'] or '-'}", flush=True)
        if index < len(targets):
            time.sleep(args.interval)


if __name__ == "__main__":
    main()

