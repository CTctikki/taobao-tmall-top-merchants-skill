import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from preflight import detect_mcp


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


if __name__ == "__main__":
    unittest.main()

