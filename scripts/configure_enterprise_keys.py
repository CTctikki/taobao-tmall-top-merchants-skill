import argparse
import getpass
import json
import os
import re
import sys
import tomllib
from pathlib import Path


QCC_MCP_URL = "https://agent.qcc.com/mcp/company/stream"
QCC_ENV_NAME = "QCC_AUTH"
FENGNIAO_ENV_NAME = "FN_API_KEY"


def normalize_qcc_key(value):
    token = value.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise ValueError("QCC Key 不能为空")
    return token


def normalize_qcc_auth(value):
    return f"Bearer {normalize_qcc_key(value)}"


def read_user_environment(name):
    value = os.environ.get(name, "").strip()
    if value or os.name != "nt":
        return value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value).strip()
    except OSError:
        return ""


def ensure_qcc_mcp_config(config_path):
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if content:
        tomllib.loads(content)
    section = (
        "[mcp_servers.qcc-company]\n"
        f'url = "{QCC_MCP_URL}"\n'
        f'bearer_token_env_var = "{QCC_ENV_NAME}"\n'
    )
    pattern = re.compile(
        r"(?ms)^\[mcp_servers\.qcc-company(?:\.[^\]]+)?\]\s*\r?\n.*?(?=^\[|\Z)"
    )
    content = pattern.sub("", content).rstrip()
    path.write_text(f"{content}\n\n{section}" if content else section, encoding="utf-8")


def persist_user_environment(name, value):
    if os.name != "nt":
        raise RuntimeError("仅支持自动配置 Windows 当前用户环境")
    import ctypes
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None)


def configure_enterprise_keys(qcc_key, fengniao_key, config_path=None, persist=None):
    qcc_auth = normalize_qcc_key(qcc_key)
    fengniao_auth = fengniao_key.strip()
    if not fengniao_auth:
        raise ValueError("风鸟 Key 不能为空")
    persist_value = persist or persist_user_environment
    persist_value(QCC_ENV_NAME, qcc_auth)
    persist_value(FENGNIAO_ENV_NAME, fengniao_auth)
    os.environ[QCC_ENV_NAME] = qcc_auth
    os.environ[FENGNIAO_ENV_NAME] = fengniao_auth
    ensure_qcc_mcp_config(config_path or Path.home() / ".codex/config.toml")
    return {
        "ok": True,
        "qcc_configured": True,
        "fengniao_configured": True,
        "message": "双企业数据源凭证已安全配置；请运行 bootstrap.ps1 验证可用性。",
    }


def read_credentials():
    if sys.stdin.isatty():
        qcc_key = getpass.getpass("请粘贴企查查 Key（输入不会显示）：")
        fengniao_key = getpass.getpass("请粘贴风鸟 Key（输入不会显示）：")
        return qcc_key, fengniao_key
    return sys.stdin.readline().rstrip("\r\n"), sys.stdin.readline().rstrip("\r\n")


def main():
    parser = argparse.ArgumentParser(description="通过标准输入安全配置企查查与风鸟 Key")
    parser.add_argument("--config", default=str(Path.home() / ".codex/config.toml"))
    args = parser.parse_args()
    try:
        qcc_key, fengniao_key = read_credentials()
        result = configure_enterprise_keys(qcc_key, fengniao_key, args.config)
    except (ValueError, RuntimeError, OSError) as error:
        result = {"ok": False, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
