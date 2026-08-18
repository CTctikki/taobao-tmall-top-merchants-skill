import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_workbook import build, contact_row_height, extract_contacts
from audit_shops import classify_browser_failure, select_candidates
from common import BrowserTransientError, classify_item, make_search_script, parse_sales_lower_bound, run_o2
from create_job import create_job
from crosscheck_trademarks import match_trademarks
from verify_job import verify


class PipelineTests(unittest.TestCase):
    def test_extract_contacts_keeps_all_unique_values(self):
        contact = {
            "联系方式信息": {
                "电话": [
                    {"电话号码": f"1380000000{index}"}
                    for index in range(8)
                ]
                + [{"电话号码": "13800000000"}],
                "邮箱": [
                    {"邮箱": f"contact{index}@example.com"}
                    for index in range(7)
                ]
                + [{"邮箱": "contact0@example.com"}],
            }
        }

        phones, emails = extract_contacts(contact)

        self.assertEqual(len(phones.split("；")), 8)
        self.assertEqual(len(emails.split("；")), 7)
        self.assertEqual(phones.split("；")[0], "13800000000")
        self.assertEqual(emails.split("；")[0], "contact0@example.com")

    def test_contact_row_height_expands_for_long_lists(self):
        phones = "；".join(f"1380000000{index}" for index in range(8))
        emails = "；".join(f"contact{index}@example.com" for index in range(7))

        self.assertEqual(contact_row_height("", "", 68), 68)
        self.assertGreaterEqual(contact_row_height(phones, emails, 68), 120)

    def test_massage_comb_profile_keeps_taobao_and_electric_products(self):
        with tempfile.TemporaryDirectory() as directory:
            job = create_job("按摩梳", directory)
            self.assertFalse(job["exclude_electric"])
            self.assertTrue(classify_item("电动红光头皮按摩梳", job)["relevant"])
            self.assertFalse(classify_item("宠物狗狗按摩梳", job)["relevant"])
            self.assertFalse(classify_item("按摩梳替换头配件", job)["relevant"])

    def test_sales_lower_bound(self):
        self.assertEqual(parse_sales_lower_bound("1.2万人付款"), 12000)
        self.assertEqual(parse_sales_lower_bound("800+人付款"), 800)
        self.assertIsNone(parse_sales_lower_bound(""))

    def test_trademark_crosscheck_requires_brand_and_relevant_class(self):
        marks = [
            {"商标名称": "RAFFINI", "国际分类": "21类 厨房洁具"},
            {"商标名称": "RAFFINI", "国际分类": "33类 酒"},
            {"商标名称": "OTHER", "国际分类": "21类 厨房洁具"},
        ]
        self.assertEqual(
            match_trademarks(marks, ["raffini"], ["8", "20", "21"]),
            [marks[0]],
        )

    def test_tiered_audit_recovers_low_exposure_c_stores(self):
        with tempfile.TemporaryDirectory() as directory:
            job = create_job("按摩梳", directory)
            rows = [
                {"shop_name": "大综合百货", "discovered_target_spu": 1, "queries": ["按摩梳"]},
                {"shop_name": "叶梳匠品牌店", "discovered_target_spu": 1, "queries": ["按摩梳"]},
                {"shop_name": "低露出品牌店", "discovered_target_spu": 1, "queries": ["a", "b", "c", "d"]},
            ]
            selected = select_candidates(job, rows)
            self.assertEqual({row["shop_name"] for row in selected}, {"叶梳匠品牌店", "低露出品牌店"})

    @patch("common.time.sleep", return_value=None)
    @patch("common.subprocess.run")
    def test_browser_transient_abort_retries_without_retrying_risk_control(self, run, _sleep):
        aborted = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "This operation was aborted"})()
        success = type("Result", (), {"returncode": 0, "stdout": '{"ok": true}', "stderr": ""})()
        run.side_effect = [aborted, success]
        self.assertEqual(run_o2("session", "eval", "1+1"), {"ok": True})
        self.assertEqual(run.call_count, 2)

    @patch("common.time.sleep", return_value=None)
    @patch("common.subprocess.run")
    def test_browser_timeout_raises_structured_transient_error(self, run, _sleep):
        import subprocess

        run.side_effect = subprocess.TimeoutExpired(["o2", "browser"], 1)
        with self.assertRaises(BrowserTransientError) as context:
            run_o2("session", "eval", "script containing 验证码 text", timeout=1)
        self.assertEqual(str(context.exception), "webcli timed out after 1 seconds")

    def test_search_script_detects_hidden_challenge_and_bounds_mtop_wait(self):
        script = make_search_script("按摩梳", 2)
        self.assertIn("_____tmd__", script)
        self.assertIn("TAOBAO_RISK_CONTROL", script)
        self.assertIn("Promise.race", script)
        self.assertIn("MTOP_REQUEST_TIMEOUT", script)

    def test_risk_control_is_recorded_separately_from_transient_failures(self):
        self.assertEqual(classify_browser_failure("Error: TAOBAO_RISK_CONTROL"), "risk_control")
        self.assertEqual(classify_browser_failure("webcli timed out after 90 seconds"), "browser_transient_error")

    def test_workbook_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            job_dir = Path(directory)
            create_job("按摩梳", job_dir)
            audit = {
                "淘宝优质店": {
                    "category": "按摩梳",
                    "shop_name": "淘宝优质店",
                    "platform": "淘宝",
                    "exact_shop_spu_seen": 20,
                    "target_spu": 10,
                    "electric_spu": 2,
                    "accessory_spu": 1,
                    "unrelated_spu": 9,
                    "target_share": 0.5,
                    "passes_minimum": True,
                    "match_grade": "高匹配",
                    "shop_url": "https://shop.example/taobao",
                    "user_id": "1",
                    "target_items": [{"sales": "100+人付款"}],
                },
                "天猫达标店": {
                    "category": "按摩梳",
                    "shop_name": "天猫达标店",
                    "platform": "天猫",
                    "exact_shop_spu_seen": 30,
                    "target_spu": 10,
                    "electric_spu": 0,
                    "accessory_spu": 2,
                    "unrelated_spu": 18,
                    "target_share": 1 / 3,
                    "passes_minimum": True,
                    "match_grade": "达标",
                    "shop_url": "https://shop.example/tmall",
                    "user_id": "2",
                    "target_items": [{"sales": "80+人付款"}],
                },
            }
            (job_dir / "assortment_audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            (job_dir / "storefronts.json").write_text("{}", encoding="utf-8")
            (job_dir / "company_candidates.json").write_text("{}", encoding="utf-8")
            (job_dir / "company_enrichment.json").write_text("{}", encoding="utf-8")
            (job_dir / "audit_errors.json").write_text(
                json.dumps(
                    {
                        "风控待续跑店": {
                            "status": "risk_control",
                            "reason": "TAOBAO_RISK_CONTROL",
                            "target": {"platform": "淘宝", "shop_url": "https://shop.example/risk"},
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            workbook = build(job_dir)
            loaded = load_workbook(workbook, data_only=False)
            unresolved_values = [cell.value for row in loaded["未确认字段"].iter_rows() for cell in row]
            self.assertIn("风控待续跑店", unresolved_values)
            self.assertIn("店铺商品结构审计", unresolved_values)
            result = verify(job_dir, workbook)
            self.assertEqual(result["formal_records"], 2)
            self.assertEqual(result["platforms"], ["天猫", "淘宝"])


class SkillMetadataTests(unittest.TestCase):
    def test_skill_has_no_secret_and_correct_name(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: taobao-tmall-top-merchants", text)
        self.assertIn("淘宝/天猫top商家清单", text)
        self.assertIn("_____tmd__", text)
        self.assertIn("MTOP_REQUEST_TIMEOUT", text)
        self.assertIn("查看商家公示信息", text)
        self.assertIn("liangzhao.htm", text)
        self.assertIn("FN_API_KEY", text)
        self.assertIn("biz_fuzzy_search", text)
        self.assertIn("biz_basic_info", text)
        self.assertIn("联系方式不能单独证明店铺主体", text)
        self.assertIn("selected: false", text)
        self.assertNotIn("Bearer MX", text)


if __name__ == "__main__":
    unittest.main()
