import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import preflight
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

    def test_python_runtime_requires_311_or_newer(self):
        self.assertFalse(preflight.python_runtime_status((3, 10, 9))["ok"])
        self.assertTrue(preflight.python_runtime_status((3, 11, 0))["ok"])

    def test_python_packages_report_missing_dependencies(self):
        def fake_find_spec(name):
            return object() if name == "requests" else None

        with patch("preflight.importlib.util.find_spec", side_effect=fake_find_spec):
            result = preflight.python_packages_status()

        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["openpyxl"])

    @patch("preflight.run", return_value=(0, "installed", ""))
    def test_o2_install_uses_internal_package_index(self, run):
        ok, detail = preflight.install_o2()

        self.assertTrue(ok)
        self.assertEqual(detail, "installed")
        self.assertEqual(
            run.call_args.args[0],
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                "--index-url",
                "https://artifactory.jd.com/artifactory/api/pypi/libs-py-local/simple",
                "o2",
            ],
        )

    def test_bootstrap_script_installs_python_then_runs_preflight(self):
        script = (ROOT / "scripts" / "bootstrap.ps1").read_text(encoding="utf-8")

        self.assertIn("Python.Python.3.11", script)
        self.assertIn("--install-missing", script)

if __name__ == "__main__":
    unittest.main()
