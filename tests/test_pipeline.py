import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_workbook import build
from common import classify_item, parse_sales_lower_bound
from create_job import create_job
from verify_job import verify


class PipelineTests(unittest.TestCase):
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
            workbook = build(job_dir)
            result = verify(job_dir, workbook)
            self.assertEqual(result["formal_records"], 2)
            self.assertEqual(result["platforms"], ["天猫", "淘宝"])


class SkillMetadataTests(unittest.TestCase):
    def test_skill_has_no_secret_and_correct_name(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: taobao-tmall-top-merchants", text)
        self.assertIn("淘宝/天猫top商家清单", text)
        self.assertNotIn("Bearer MX", text)


if __name__ == "__main__":
    unittest.main()

