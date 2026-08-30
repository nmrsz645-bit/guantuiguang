import importlib
import json
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / "自动关推广"
errors = 0
warnings = 0
allow_unconfigured = "--allow-unconfigured" in sys.argv


def ok(text):
    print(f"OK: {text}")


def warn(text):
    global warnings
    warnings += 1
    print(f"WARN: {text}")


def err(text):
    global errors
    errors += 1
    print(f"ERROR: {text}")


def check_file(path, label, required=True):
    if path.exists():
        ok(f"{label} exists")
    elif required:
        err(f"{label} missing: {path}")
    else:
        warn(f"{label} missing: {path}")


def check_writable(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        ok(f"Writable folder: {path}")
    except Exception as exc:
        err(f"Folder not writable: {path} - {exc}")


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


print("========================================")
print("OceanEngine Close-Promotion Self Check")
print(f"Root: {ROOT}")
print("========================================")

ok(f"Python executable: {sys.executable}")

chrome_candidates = [
    Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
]
if any(p.exists() for p in chrome_candidates):
    ok("Chrome found")
else:
    err("Chrome not found")

for filename, label, required in [
    ("monitor_oceanengine_units.py", "OceanEngine monitor script", True),
    ("write_auth_code.py", "OceanEngine auth script", True),
    ("open_main_account_logins.py", "OceanEngine login script", True),
    ("import_account_texts.py", "Account import script", True),
    ("config.json", "OceanEngine config", True),
    ("oceanengine_tokens.json", "Default token file", False),
]:
    check_file(AD_DIR / filename, label, required)

for bat in [
    "首次安装.bat",
    "一键自检.bat",
    "打开巨量登录.bat",
    "写入巨量授权码.bat",
    "自动导入巨量账号授权.bat",
    "启动监控.bat",
    "停止监控.bat",
    "一键状态面板.bat",
    "打开日志文件夹.bat",
]:
    check_file(ROOT / bat, bat, True)

for folder in [
    ROOT / "rizhi",
    AD_DIR / "rizhi",
    AD_DIR / "data",
    AD_DIR / "tokens",
    AD_DIR / "账号接口信息",
]:
    check_writable(folder)

for module_name in ["requests", "websocket", "dotenv"]:
    try:
        importlib.import_module(module_name)
        ok(f"Python package import OK: {module_name}")
    except Exception as exc:
        err(f"Python package import failed: {module_name} - {exc}")

try:
    config = json.loads((AD_DIR / "config.json").read_text(encoding="utf-8-sig"))
    ok("Config JSON can be parsed")
    accounts = [a for a in config.get("main_accounts", []) if a.get("enabled", True)]
    if not accounts:
        message = "No enabled main account configured. Open the desktop app and save at least one enabled account before monitoring."
        if allow_unconfigured:
            warn(message)
        else:
            err(message)
    else:
        ok(f"Enabled main accounts: {len(accounts)}")
        for account in accounts:
            ids = [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()]
            port = int(account.get("chrome_debug_port") or 0)
            if ids:
                ok(f"{account.get('id')}: advertiser_ids={len(ids)}, port={port}")
            else:
                warn(f"{account.get('id')}: no advertiser_ids")
            if port:
                if port_in_use(port):
                    warn(f"Port {port} is already in use. This is normal if the monitor/login Chrome is running.")
                else:
                    ok(f"Port {port} is free")
except Exception as exc:
    err(f"Config JSON cannot be parsed: {exc}")

print()
print("Summary")
print("-------")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")
if errors:
    print("Self-check failed. Fix the errors above before starting.")
    sys.exit(1)
print("Self-check passed. You can start monitoring.")
