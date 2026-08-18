import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from company_source_routing import EVIDENCE_PRIORITY, company_lookup_plan


class CompanySourceRoutingTests(unittest.TestCase):
    def test_fuzzy_identity_uses_fengniao_then_qcc_then_fengniao(self):
        plan = company_lookup_plan(has_exact_identity=False)

        self.assertEqual(plan["mode"], "fuzzy_identity")
        self.assertEqual(
            [step["action"] for step in plan["steps"]],
            ["fengniao_discover", "qcc_verify", "fengniao_supplement"],
        )
        self.assertTrue(plan["cross_source_review_pending"])
        self.assertFalse(plan["single_source_fallback"])

    def test_exact_identity_uses_qcc_then_fengniao(self):
        plan = company_lookup_plan(has_exact_identity=True)

        self.assertEqual(plan["mode"], "exact_identity")
        self.assertEqual(
            [step["action"] for step in plan["steps"]],
            ["qcc_verify", "fengniao_supplement"],
        )

    def test_single_provider_fallback_keeps_review_pending(self):
        qcc_only = company_lookup_plan(
            has_exact_identity=False,
            qcc_available=True,
            fengniao_available=False,
        )
        fengniao_only = company_lookup_plan(
            has_exact_identity=False,
            qcc_available=False,
            fengniao_available=True,
        )

        self.assertEqual([step["action"] for step in qcc_only["steps"]], ["qcc_discover"])
        self.assertEqual([step["action"] for step in fengniao_only["steps"]], ["fengniao_discover"])
        self.assertTrue(qcc_only["cross_source_review_pending"])
        self.assertTrue(fengniao_only["cross_source_review_pending"])
        self.assertTrue(qcc_only["single_source_fallback"])
        self.assertTrue(fengniao_only["single_source_fallback"])

    def test_no_provider_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "enterprise data source"):
            company_lookup_plan(
                has_exact_identity=False,
                qcc_available=False,
                fengniao_available=False,
            )

    def test_conflict_evidence_priority_is_fixed(self):
        self.assertEqual(
            EVIDENCE_PRIORITY,
            [
                "platform_qualification",
                "credit_code_match",
                "trademark_or_official_site",
                "company_name_similarity",
                "phone_or_email",
            ],
        )

    def test_cli_emits_json_plan(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "company_source_routing.py"),
                "--company-name",
                "深圳市城华贸易有限公司",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["mode"], "exact_identity")
        self.assertEqual(result["steps"][0]["action"], "qcc_verify")


if __name__ == "__main__":
    unittest.main()
