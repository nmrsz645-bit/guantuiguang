import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "config.json"


def load_accounts():
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    accounts = config.get("main_accounts") or []
    result = []
    for index, account in enumerate(accounts, start=1):
        account_id = str(account.get("id") or f"main_{index:02d}")
        advertisers = [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()]
        result.append({
            "id": account_id,
            "name": str(account.get("name") or account_id),
            "enabled": account.get("enabled") is not False,
            "advertiser_ids": advertisers,
        })
    return result


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    accounts = load_accounts()
    if not accounts:
        raise RuntimeError("config.json 里没有 main_accounts。")
    print("请选择要写入授权的主账户：")
    for account in accounts:
        status = "启用" if account["enabled"] else "未启用"
        child_count = len(account["advertiser_ids"])
        print(f"{account['id']} | {account['name']} | {status} | 子账户数量:{child_count}")
    print("")
    account_id = input("请输入主账户编号，例如 main_01：").strip()
    if not account_id:
        raise RuntimeError("没有输入主账户编号")
    cmd = [sys.executable, str(ROOT / "write_auth_code.py"), "--main-account", account_id]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
