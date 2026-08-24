import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_workbook import build, candidate_outreach, contact_row_height, extract_contacts, selected_company
from audit_shops import classify_browser_failure, select_candidates, should_reuse_recorded_failure
from common import BrowserTransientError, classify_item, make_search_script, parse_sales_lower_bound, run_o2
from create_job import create_job
from crosscheck_trademarks import match_trademarks
from verify_job import verify


class PipelineTests(unittest.TestCase):
    def test_default_candidate_audit_limit_is_thirty(self):
        with tempfile.TemporaryDirectory() as directory:
            job = create_job("按摩梳", directory)

            self.assertEqual(job["max_candidate_shops"], 30)

    def test_unconfirmed_single_company_candidate_is_not_selected(self):
        enrichment = {
            "候选店": [
                {
                    "company": "候选公司有限公司",
                    "selected": False,
                }
            ]
        }

        self.assertEqual(selected_company(enrichment, "候选店"), {})

    def test_explicitly_selected_company_is_used(self):
        selected = {
            "company": "已确认公司有限公司",
            "selected": True,
        }
        enrichment = {
            "确认店": [
                {"company": "其他候选有限公司", "selected": False},
                selected,
            ]
        }

        self.assertEqual(selected_company(enrichment, "确认店"), selected)

    def test_candidate_outreach_exposes_contacts_without_confirming_subject(self):
        enrichment = {
            "候选店": [
                {
                    "company": "候选公司有限公司",
                    "selected": False,
                    "registration": {
                        "企业名称": "候选公司有限公司",
                        "注册地址": "上海市候选路1号",
                    },
                    "contact": {
                        "联系方式信息": {
                            "电话": [{"电话号码": "021-12345678"}],
                            "邮箱": [{"邮箱": "contact@example.com"}],
                        }
                    },
                }
            ]
        }

        outreach = candidate_outreach(enrichment, "候选店")

        self.assertEqual(selected_company(enrichment, "候选店"), {})
        self.assertIn("候选公司有限公司", outreach["candidate_companies"])
        self.assertIn("021-12345678", outreach["candidate_phones"])
        self.assertIn("contact@example.com", outreach["candidate_emails"])
        self.assertIn("上海市候选路1号", outreach["candidate_addresses"])
        self.assertIn("先核验", outreach["outreach_note"])

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
                {"shop_name": "大综合百货", "discovered_target_spu": 1, "queries": ["按摩梳"], "items": [{"sales": "2万+人付款"}]},
                {"shop_name": "叶梳匠品牌店", "discovered_target_spu": 1, "queries": ["按摩梳"], "items": [{"sales": "2万+人付款"}]},
                {"shop_name": "低露出品牌店", "discovered_target_spu": 1, "queries": ["a", "b", "c", "d"], "items": [{"sales": "1.5万+人付款"}]},
            ]
            selected = select_candidates(job, rows)
            self.assertEqual({row["shop_name"] for row in selected}, {"叶梳匠品牌店", "低露出品牌店"})

    def test_quality_shortlist_filters_and_ranks_by_payment_lower_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            job = create_job("按摩梳", directory)
            rows = [
                {"shop_name": "高销量专业店", "discovered_target_spu": 5, "queries": ["a", "b", "c"], "items": [{"sales": "5万+人付款"}]},
                {"shop_name": "中销量专业店", "discovered_target_spu": 4, "queries": ["a", "b", "c"], "items": [{"sales": "3万+人付款"}]},
                {"shop_name": "低销量铺货店", "discovered_target_spu": 20, "queries": ["a", "b", "c", "d"], "items": [{"sales": "100+人付款"}]},
                {"shop_name": "天猫超市", "discovered_target_spu": 30, "queries": ["a", "b", "c", "d"], "items": [{"sales": "20万+人付款"}]},
            ]

            selected = select_candidates(job, rows)

            self.assertEqual([row["shop_name"] for row in selected], ["高销量专业店", "中销量专业店"])
            self.assertEqual(selected[0]["payment_lower_bound"], 50000)

    def test_sales_top_n_mode_keeps_single_query_high_sales_shop(self):
        with tempfile.TemporaryDirectory() as directory:
            job = create_job("按摩梳", directory)
            job.update(
                {
                    "sales_top_n_mode": True,
                    "minimum_payment_lower_bound": 0,
                    "minimum_quality_query_coverage": 1,
                    "max_candidate_shops": 30,
                }
            )
            rows = [
                {"shop_name": "单词高销量店", "discovered_target_spu": 1, "queries": ["按摩梳"], "items": [{"sales": "10万+人付款"}]},
                {"shop_name": "多词普通店", "discovered_target_spu": 3, "queries": ["a", "b", "c"], "items": [{"sales": "1万+人付款"}]},
            ]

            selected = select_candidates(job, rows)

            self.assertEqual([row["shop_name"] for row in selected], ["单词高销量店", "多词普通店"])
            self.assertEqual(selected[0]["audit_reason"], "sales_top")

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

    def test_recorded_risk_control_is_reused_without_overwriting_error(self):
        errors = {
            "风控店": {"status": "risk_control", "reason": "TAOBAO_RISK_CONTROL"},
            "瞬时错误店": {"status": "browser_transient_error", "reason": "timeout"},
        }

        self.assertTrue(should_reuse_recorded_failure(errors, "风控店"))
        self.assertFalse(should_reuse_recorded_failure(errors, "瞬时错误店"))
        self.assertFalse(should_reuse_recorded_failure(errors, "新店"))

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
                    "category": "采耳工具",
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
            (job_dir / "company_enrichment.json").write_text(
                json.dumps(
                    {
                        "淘宝优质店": [
                            {
                                "company": "候选公司有限公司",
                                "selected": False,
                                "registration": {
                                    "企业名称": "候选公司有限公司",
                                    "注册地址": "上海市候选路1号",
                                },
                                "contact": {
                                    "联系方式信息": {
                                        "电话": [{"电话号码": "021-12345678"}],
                                        "邮箱": [{"邮箱": "contact@example.com"}],
                                    }
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
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
            formal_categories = {
                loaded["正式招商商家"].cell(row, 2).value
                for row in range(4, loaded["正式招商商家"].max_row + 1)
            }
            self.assertEqual(formal_categories, {"按摩梳", "采耳工具"})
            headers = {cell.value: cell.column for cell in loaded["正式招商商家"][3]}
            self.assertFalse(loaded["正式招商商家"].cell(4, headers["公司名称"]).value)
            self.assertIn("021-12345678", loaded["正式招商商家"].cell(4, headers["候选电话（待核验）"]).value)
            self.assertIn("上海市候选路1号", loaded["正式招商商家"].cell(4, headers["候选地址（待核验）"]).value)
            unresolved_values = [cell.value for row in loaded["未确认字段"].iter_rows() for cell in row]
            self.assertIn("风控待续跑店", unresolved_values)
            self.assertIn("店铺商品结构审计", unresolved_values)
            result = verify(job_dir, workbook)
            self.assertEqual(result["formal_records"], 2)
            self.assertEqual(result["platforms"], ["天猫", "淘宝"])


    def test_workbook_preserves_subject_metadata_and_labels_exact_search_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            job_dir = Path(directory)
            create_job("\u6309\u6469\u68b3", job_dir)
            audit = {
                "selected-shop": {
                    "category": "\u6309\u6469\u68b3",
                    "shop_name": "\u5929\u732b\u8fbe\u6807\u5e97",
                    "platform": "\u5929\u732b",
                    "exact_shop_spu_seen": 20,
                    "target_spu": 10,
                    "electric_spu": 0,
                    "accessory_spu": 0,
                    "unrelated_spu": 10,
                    "target_share": 0.5,
                    "passes_minimum": True,
                    "match_grade": "\u9ad8\u5339\u914d",
                    "shop_url": "https://shop.example/tmall",
                    "user_id": "2",
                    "target_items": [{"sales": "80+\u4eba\u4ed8\u6b3e"}],
                }
            }
            (job_dir / "assortment_audit.json").write_text(json.dumps(audit, ensure_ascii=False), encoding="utf-8")
            (job_dir / "company_enrichment.json").write_text(
                json.dumps(
                    {
                        "\u5929\u732b\u8fbe\u6807\u5e97": [
                            {
                                "company": "\u54c1\u724c\u6743\u5229\u516c\u53f8\u6709\u9650\u516c\u53f8",
                                "selected": True,
                                "subject_role": "\u5546\u6807\u6743\u5229\u4e3b\u4f53",
                                "subject_confidence": "\u9ad8\uff08\u54c1\u724c\u5546\u6807+\u76f8\u5173\u7c7b\u522b\uff09",
                                "pending": "\u5f53\u524d\u5929\u732b\u6301\u8bc1\u8fd0\u8425\u4e3b\u4f53\u4ecd\u5f85\u5e73\u53f0\u8d44\u8d28\u9875\u6700\u7ec8\u786e\u8ba4",
                                "registration": {"\u4f01\u4e1a\u540d\u79f0": "\u54c1\u724c\u6743\u5229\u516c\u53f8\u6709\u9650\u516c\u53f8"},
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (job_dir / "audit_errors.json").write_text(
                json.dumps(
                    {
                        "\u7cbe\u786e\u53cd\u67e5\u672a\u547d\u4e2d\u5e97": {
                            "status": "search_no_exact_shop_items",
                            "reason": "100 search results contained no exact shop-name match",
                            "target": {"platform": "\u6dd8\u5b9d", "shop_url": "https://shop.example/no-match"},
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            workbook = build(job_dir)
            loaded = load_workbook(workbook, data_only=False)
            headers = {cell.value: cell.column for cell in loaded["\u6b63\u5f0f\u62db\u5546\u5546\u5bb6"][3]}
            self.assertEqual(loaded["\u6b63\u5f0f\u62db\u5546\u5546\u5bb6"].cell(4, headers["\u4e3b\u4f53\u89d2\u8272"]).value, "\u5546\u6807\u6743\u5229\u4e3b\u4f53")
            self.assertEqual(loaded["\u6b63\u5f0f\u62db\u5546\u5546\u5bb6"].cell(4, headers["\u4e3b\u4f53\u7f6e\u4fe1\u5ea6"]).value, "\u9ad8\uff08\u54c1\u724c\u5546\u6807+\u76f8\u5173\u7c7b\u522b\uff09")
            self.assertEqual(loaded["\u6b63\u5f0f\u62db\u5546\u5546\u5bb6"].cell(4, headers["\u5f85\u786e\u8ba4\u9879"]).value, "\u5f53\u524d\u5929\u732b\u6301\u8bc1\u8fd0\u8425\u4e3b\u4f53\u4ecd\u5f85\u5e73\u53f0\u8d44\u8d28\u9875\u6700\u7ec8\u786e\u8ba4")
            unresolved_values = [cell.value for row in loaded["\u672a\u786e\u8ba4\u5b57\u6bb5"].iter_rows() for cell in row]
            self.assertTrue(any("\u641c\u7d22\u53cd\u67e5\u672a\u547d\u4e2d\u7cbe\u786e\u5e97\u94fa\u5546\u54c1" in str(value) for value in unresolved_values))


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
        self.assertIn("风鸟模糊发现 → 企查查精确核验 → 风鸟补缺", text)
        self.assertIn("企查查精确核验 → 风鸟补缺", text)
        self.assertIn("平台资质页 > 信用代码一致 > 商标/品牌官网 > 企业名称相似 > 电话邮箱", text)
        self.assertNotIn("Bearer MX", text)
        self.assertIn("scripts/bootstrap.ps1", text)
        self.assertIn("--install-missing", text)

    def test_skill_supports_user_provided_shop_list_mode(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("用户指定名单模式", text)
        for input_type in ["店铺名", "多个链接", "文本", "表格", "电子表格", "混合信息"]:
            self.assertIn(input_type, text)
        self.assertIn("不运行 `mine_taobao.py`、`audit_shops.py`", text)
        self.assertIn("全部进入正式招商商家", text)
        self.assertIn("不得补造目标SPU、店内目标商品占比、付款人数展示下限或Top30结论", text)
        self.assertIn("用户指定名单，不代表Top30或主营准入达标", text)
        self.assertIn("名单模式跳过第3至第7步", text)
        self.assertIn("不运行 `create_job.py`、`mine_taobao.py`、`audit_shops.py`、`audit_storefronts.py`", text)


if __name__ == "__main__":
    unittest.main()
