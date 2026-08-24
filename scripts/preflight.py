import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


ENTERPRISE_TERMS = ("qcc", "企查查", "aiqicha", "爱企查", "tianyancha", "天眼查")
MIN_PYTHON_VERSION = (3, 11)
REQUIRED_PYTHON_PACKAGES = {
    "openpyxl": "openpyxl>=3.1",
    "requests": "requests>=2.32",
}
O2_INDEX_URL = "https://artifactory.jd.com/artifactory/api/pypi/libs-py-local/simple"


def python_runtime_status(version_info=None):
    version = tuple(version_info or sys.version_info[:3])
    return {
        "ok": version >= MIN_PYTHON_VERSION,
        "version": ".".join(str(part) for part in version),
        "minimum": ".".join(str(part) for part in MIN_PYTHON_VERSION),
        "executable": sys.executable,
    }


def python_packages_status():
    importlib.invalidate_caches()
    installed = []
    missing = []
    for module in REQUIRED_PYTHON_PACKAGES:
        (installed if importlib.util.find_spec(module) else missing).append(module)
    return {"ok": not missing, "installed": installed, "missing": missing}


def find_o2():
    direct = shutil.which("o2")
    if direct:
        return direct
    scripts_dir = Path(sys.executable).resolve().parent / "Scripts"
    for name in ("o2.exe", "o2"):
        candidate = scripts_dir / name
        if candidate.is_file():
            return str(candidate)
    return ""


def find_codex():
    direct = shutil.which("codex")
    if direct:
        return direct
    candidates = list((Path.home() / "AppData/Local/OpenAI/Codex/bin").glob("*/codex.exe"))
    return str(candidates[-1]) if candidates else ""


def detect_mcp(config_path):
    if not config_path.exists():
        return []
    config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    matches = []
    for name, value in config.get("mcp_servers", {}).items():
        text = f"{name} {value}".lower()
        if any(term.lower() in text for term in ENTERPRISE_TERMS):
            matches.append(name)
    return sorted(matches)


def detect_fengniao(skill_dir=None):
    path = Path(skill_dir or Path.home() / ".openclaw/skills/company-search-fengniao")
    installed = (path / "scripts/tool.mjs").is_file()
    key_configured = bool(os.environ.get("FN_API_KEY"))
    return {
        "installed": installed,
        "key_configured": key_configured,
        "ready": installed,
        "path": str(path),
    }


def run(command):
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def install_python_dependencies(requirements_path=None):
    path = Path(requirements_path or Path(__file__).resolve().parents[1] / "requirements.txt")
    code, out, err = run([sys.executable, "-m", "pip", "install", "-r", str(path)])
    return code == 0, out or err


def install_o2():
    code, out, err = run([sys.executable, "-m", "pip", "install", "-U", "--index-url", O2_INDEX_URL, "o2"])
    return code == 0, out or err


def install_webcli():
    o2 = find_o2()
    if not o2:
        return False, "o2 not installed"
    code, out, err = run([o2, "install", "webcli"])
    return code == 0, out or err


def install_qcc(config_only=False):
    codex = find_codex()
    if not codex:
        return False, "Codex CLI not found"
    command = [codex, "mcp", "add", "qcc-company", "--url", "https://agent.qcc.com/mcp/company/stream", "--bearer-token-env-var", "QCC_AUTH"]
    if not os.environ.get("QCC_AUTH") and not config_only:
        return False, "Set QCC_AUTH first; get a token at https://agent.qcc.com/"
    code, out, err = run(command)
    return code == 0, out or err


def webcli_doctor():
    o2 = find_o2()
    if not o2:
        return {"ok": False, "error": "o2 missing"}
    code, out, err = run([o2, "launch", "webcli", "--json", "doctor"])
    if code:
        return {"ok": False, "error": err or out}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"ok": False, "error": out}


def taobao_state(session):
    o2 = find_o2()
    if not o2:
        return {"ok": False, "error": "o2 missing"}
    run([o2, "launch", "webcli", "browser", session, "open", "https://www.taobao.com/"])
    script = "(()=>{const t=document.body?document.body.innerText:'';return {url:location.href,title:document.title,risk:/验证码|访问被拒绝|滑动验证/.test(t),loggedIn:/消息|购物车|我的淘宝|已买到的宝贝/.test(t)&&!/亲，请登录/.test(t)}})()"
    code, out, err = run([o2, "launch", "webcli", "browser", session, "eval", script])
    if code:
        return {"ok": False, "error": err or out}
    try:
        return {"ok": True, **json.loads(out)}
    except json.JSONDecodeError:
        return {"ok": False, "error": out}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(Path.home() / ".codex/config.toml"))
    parser.add_argument("--check-taobao", action="store_true")
    parser.add_argument("--session", default="top_merchants_preflight")
    parser.add_argument("--fengniao-skill-dir")
    parser.add_argument("--install-missing", action="store_true")
    args = parser.parse_args()

    runtime = python_runtime_status()
    packages = python_packages_status()
    o2_path = find_o2()
    actions = []

    if args.install_missing and runtime["ok"] and not packages["ok"]:
        ok, detail = install_python_dependencies()
        actions.append({"action": "install_python_dependencies", "ok": ok, "detail": detail})
        packages = python_packages_status()

    if args.install_missing and runtime["ok"] and not o2_path:
        ok, detail = install_o2()
        actions.append({"action": "install_o2", "ok": ok, "detail": detail})
        o2_path = find_o2()

    doctor = webcli_doctor()
    if not doctor.get("ok") and args.install_missing and o2_path:
        ok, detail = install_webcli()
        actions.append({"action": "install_webcli", "ok": ok, "detail": detail})
        doctor = webcli_doctor()

    config_path = Path(args.config)
    mcps = detect_mcp(config_path)
    fengniao = detect_fengniao(args.fengniao_skill_dir)
    if not mcps and not fengniao["ready"] and args.install_missing:
        ok, detail = install_qcc()
        actions.append({"action": "configure_qcc", "ok": ok, "detail": detail})
        mcps = detect_mcp(config_path)

    taobao = taobao_state(args.session) if args.check_taobao and doctor.get("ok") else None
    enterprise_ready = bool(mcps) or fengniao["ready"]
    result = {
        "ok": runtime["ok"] and packages["ok"] and bool(o2_path) and enterprise_ready and bool(doctor.get("ok")) and (taobao is None or bool(taobao.get("loggedIn"))),
        "python": runtime,
        "python_packages": packages,
        "o2": {"installed": bool(o2_path), "path": o2_path},
        "enterprise_mcps": mcps,
        "fengniao": fengniao,
        "webcli": doctor,
        "taobao": taobao,
        "actions": actions,
        "next": [],
    }
    if not runtime["ok"]:
        result["next"].append("Install Python 3.11 or newer, then rerun scripts/bootstrap.ps1")
    if not packages["ok"]:
        result["next"].append("Install required Python packages from requirements.txt")
    if not o2_path:
        result["next"].append("Install o2 with the configured JD Python package index")
    if not enterprise_ready:
        result["next"].append("Configure an enterprise-query MCP or install the Fengniao skill; FN_API_KEY is optional for private quota")
    if not doctor.get("ok"):
        result["next"].append("Install/repair o2 webcli and Browser Bridge")
    if taobao and not taobao.get("loggedIn"):
        result["next"].append("Log in to Taobao in the connected Chrome tab, then rerun preflight")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
