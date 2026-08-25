import argparse
import json
import re
import time
from datetime import datetime
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from common import ensure_job_dir, run_o2, write_json


QUALIFICATION_FIELDS = {
    "credit_code": ("企业注册号", "统一社会信用代码", "注册号"),
    "company_name": ("企业名称",),
    "company_type": ("类型", "企业类型"),
    "address": ("住所", "注册地址"),
    "legal_person": ("法定代表人",),
    "established": ("成立时间", "成立日期"),
    "registered_capital": ("注册资本",),
    "business_term": ("营业期限",),
    "business_scope": ("经营范围",),
    "registration_authority": ("登记机关",),
}


def parse_qualification_text(text, source_url=""):
    normalized = re.sub(r"[\t\r]+", " ", str(text or ""))
    labels = [label for aliases in QUALIFICATION_FIELDS.values() for label in aliases]
    label_pattern = "|".join(sorted((re.escape(label) for label in labels), key=len, reverse=True))
    matches = list(re.finditer(rf"(?:^|\n)\s*({label_pattern})\s*[：:]\s*", normalized))
    values = {}
    alias_to_field = {alias: field for field, aliases in QUALIFICATION_FIELDS.items() for alias in aliases}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        value = normalized[match.end():end].strip()
        if value:
            values[alias_to_field[match.group(1)]] = re.sub(r"\s*\n\s*", "", value)
    company_name = values.get("company_name", "")
    credit_code = re.sub(r"\s+", "", values.get("credit_code", "")).upper()
    verified = bool(company_name and credit_code)
    return {
        "status": "verified" if verified else "incomplete",
        "evidence_type": "platform_qualification",
        "source_url": source_url,
        **values,
        "company_name": company_name,
        "credit_code": credit_code,
    }


def page_script():
    return (
        "(()=>{const text=document.body?document.body.innerText:'';"
        "const lines=Array.from(new Set(text.split(/\\n+/).map(function(s){return s.trim()}).filter(Boolean)));"
        "const terms=['企业店','个人店','淘宝店','天猫','查看资质','营业执照','店铺资质'];"
        "const signals=lines.filter(function(s){return s.length<=40&&terms.some(function(t){return s.includes(t)})}).slice(0,120);"
        "const resources=performance.getEntriesByType('resource').map(function(e){return e.name}).filter(function(u){return u.includes('mtop.taobao.shop.simple.fetch')}).slice(-3);"
        "const config=window.shop_config||{};const hiddenChallenge=Boolean(document.querySelector('iframe[src*=\"_____tmd__\"]'));const blocked=hiddenChallenge||/验证码|访问被拒绝|滑动验证/.test(text);"
        "return {url:location.href,title:document.title,signals:signals,shopFetch:resources,htmlSellerId:String(config.userId||''),htmlShopId:String(config.shopId||''),blocked:blocked}})()"
    )


def qualification_link_script():
    return (
        "(async()=>{const riskText=document.body?document.body.innerText:'';"
        "const hiddenChallenge=Boolean(document.querySelector('iframe[src*=\"_____tmd__\"]'));"
        "if(hiddenChallenge||/验证码|访问被拒绝|滑动验证/.test(riskText)){return {blocked:true,url:''}};"
        "const nodes=Array.from(document.querySelectorAll('a,button,span,div'));"
        "const trigger=nodes.find(function(node){return (node.textContent||'').trim().includes('查看资质')});"
        "if(trigger){['mouseover','mouseenter'].forEach(function(name){trigger.dispatchEvent(new MouseEvent(name,{bubbles:true}))});"
        "await new Promise(function(resolve){setTimeout(resolve,800)})};"
        "const links=Array.from(document.querySelectorAll('a'));"
        "const target=links.find(function(link){const text=(link.textContent||'').trim();const href=link.href||'';"
        "return text.includes('查看商家公示信息')||href.includes('liangzhao.htm')});"
        "return {blocked:false,url:target?(target.href||target.getAttribute('href')||''):''}})()"
    )


def qualification_page_script():
    return (
        "(()=>{const text=document.body?document.body.innerText:'';"
        "const hiddenChallenge=Boolean(document.querySelector('iframe[src*=\"_____tmd__\"]'));"
        "const blocked=hiddenChallenge||/验证码|访问被拒绝|滑动验证/.test(text);"
        "const relevant=/企业名称|企业注册号|统一社会信用代码/.test(text);"
        "return {url:location.href,blocked:blocked,relevant:relevant,text:text}})()"
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
    qualification_path = job_dir / "platform_qualifications.json"
    qualifications = json.loads(qualification_path.read_text(encoding="utf-8")) if qualification_path.exists() else {}
    for index, target in enumerate(targets, 1):
        shop_name = target["shop_name"]
        qualification_complete = target["platform"] != "天猫" or qualifications.get(shop_name, {}).get("status") in {"verified", "incomplete", "not_found"}
        if shop_name in existing and existing[shop_name].get("official_url") and qualification_complete:
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
        if target["platform"] == "天猫":
            link = run_o2(args.session, "eval", qualification_link_script())
            if link.get("blocked"):
                qualifications[shop_name] = {"status": "risk_control", "evidence_type": "platform_qualification", "source_url": ""}
                write_json(qualification_path, qualifications)
                raise RuntimeError(f"Taobao risk control detected while opening qualification at {shop_name}; stop and ask user to verify")
            qualification_url = urljoin(page.get("url") or target.get("shop_url", ""), link.get("url", ""))
            if qualification_url:
                run_o2(args.session, "open", qualification_url)
                time.sleep(3)
                qualification_page = run_o2(args.session, "eval", qualification_page_script())
                if qualification_page.get("blocked"):
                    qualifications[shop_name] = {"status": "risk_control", "evidence_type": "platform_qualification", "source_url": qualification_page.get("url") or qualification_url}
                    write_json(qualification_path, qualifications)
                    raise RuntimeError(f"Taobao risk control detected on qualification page at {shop_name}; stop and ask user to verify")
                qualifications[shop_name] = parse_qualification_text(
                    qualification_page.get("text", ""),
                    qualification_page.get("url") or qualification_url,
                )
            else:
                qualifications[shop_name] = {"status": "not_found", "evidence_type": "platform_qualification", "source_url": ""}
            write_json(qualification_path, qualifications)
        print(f"[{index}/{len(targets)}] {shop_name} shopId={existing[shop_name]['shop_id'] or '-'} sellerId={existing[shop_name]['seller_id'] or '-'}", flush=True)
        if index < len(targets):
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
