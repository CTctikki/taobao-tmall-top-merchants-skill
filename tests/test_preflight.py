import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight import detect_fengniao, detect_mcp


class PreflightTests(unittest.TestCase):
    def test_detects_qcc_and_other_enterprise_mcp(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.toml"
            config.write_text(
                '[mcp_servers.qcc-company]\nurl="https://agent.qcc.com/mcp/company/stream"\n'
                '[mcp_servers.aiqicha]\nurl="https://example.com/aiqicha"\n',
                encoding="utf-8",
            )
            self.assertEqual(detect_mcp(config), ["aiqicha", "qcc-company"])

    def test_detects_fengniao_skill_and_temporary_key(self):
        with tempfile.TemporaryDirectory() as directory:
            skill_dir = Path(directory) / "company-search-fengniao"
            (skill_dir / "scripts").mkdir(parents=True)
            (skill_dir / "scripts" / "tool.mjs").write_text("", encoding="utf-8")
            with patch.dict("os.environ", {"FN_API_KEY": "temporary-test-key"}, clear=False):
                result = detect_fengniao(skill_dir)

            self.assertTrue(result["installed"])
            self.assertTrue(result["key_configured"])
            self.assertTrue(result["ready"])
            self.assertNotIn("temporary-test-key", str(result))

    def test_fengniao_public_quota_is_ready_without_private_key(self):
        with tempfile.TemporaryDirectory() as directory:
            skill_dir = Path(directory) / "company-search-fengniao"
            (skill_dir / "scripts").mkdir(parents=True)
            (skill_dir / "scripts" / "tool.mjs").write_text("", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                result = detect_fengniao(skill_dir)

            self.assertTrue(result["installed"])
            self.assertFalse(result["key_configured"])
            self.assertTrue(result["ready"])


if __name__ == "__main__":
    unittest.main()
