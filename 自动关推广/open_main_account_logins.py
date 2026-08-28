import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path


ROOT = Path(os.environ.get("OCEANENGINE_ROOT") or Path(__file__).resolve().parent)
CONFIG_FILE = ROOT / "config.json"
LOGIN_PAGES_DIR = ROOT / "login-pages"


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))


def normalize_main_accounts(config):
    accounts = config.get("main_accounts")
    if not accounts:
        advertisers = [str(x).strip() for x in config.get("advertiser_ids", []) if str(x).strip()]
        if not advertisers:
            return []
        return [{
            "id": "main_01",
            "name": config.get("main_account_name") or "主账户01",
            "enabled": True,
            "advertiser_ids": advertisers,
            "chrome_debug_port": int(config.get("chrome_debug_port", 9222)),
            "chrome_profile_dir": config.get("chrome_profile_dir", "chrome-debug-profile"),
        }]
    normalized = []
    for index, account in enumerate(accounts, start=1):
        if not account or account.get("enabled") is False:
            continue
        advertisers = [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()]
        if not advertisers:
            continue
        account_id = str(account.get("id") or f"main_{index:02d}")
        normalized.append({
            "id": account_id,
            "name": str(account.get("name") or account_id),
            "enabled": True,
            "advertiser_ids": advertisers,
            "chrome_debug_port": int(account.get("chrome_debug_port") or (9221 + index)),
            "chrome_profile_dir": account.get("chrome_profile_dir") or f"chrome-profiles/{account_id}",
        })
    return normalized


try:
    from main_accounts import normalize_main_accounts as normalize_main_accounts
    from main_accounts import split_accounts_for_parallel_browsers
except Exception:
    pass


def find_chrome():
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for item in candidates:
        if item and Path(item).exists():
            return item
    raise RuntimeError("没有找到 Google Chrome，请先运行首次安装。")


def write_login_page(account):
    LOGIN_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    advertisers = "\n".join(f"<li>{item}</li>" for item in account["advertiser_ids"])
    first_advertiser = account["advertiser_ids"][0]
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{account['name']} - 巨量登录说明</title>
  <style>
    body {{ font-family: "Microsoft YaHei", Arial, sans-serif; margin: 48px; line-height: 1.7; }}
    .box {{ max-width: 880px; border: 1px solid #ddd; border-radius: 8px; padding: 28px; }}
    h1 {{ margin-top: 0; }}
    code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }}
    .tip {{ color: #b45309; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>请在这个浏览器登录：{account['name']}</h1>
    <p class="tip">这个浏览器只给这个主账户使用，不要登录其他主账户。</p>
    <p>浏览器编号：<code>{account['id']}</code></p>
    <p>调试端口：<code>{account['chrome_debug_port']}</code></p>
    <p>子账户 / advertiser_id：</p>
    <ul>{advertisers}</ul>
    <p>登录完成后保持这个浏览器登录状态即可。以后程序会继续使用这个独立浏览器配置。</p>
    <p><a href="https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid={first_advertiser}">打开这个主账户的巨量后台</a></p>
  </div>
</body>
</html>
"""
    path = LOGIN_PAGES_DIR / f"{account['id']}.html"
    path.write_text(html, encoding="utf-8")
    return path


def file_url(path):
    return path.resolve().as_uri()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    config = load_config()
    accounts = normalize_main_accounts(config)
    try:
        accounts = split_accounts_for_parallel_browsers(config, accounts)
    except NameError:
        pass
    if not accounts:
        raise RuntimeError("没有启用的主账户，请先填写 config.json 的 main_accounts。")
    chrome = find_chrome()
    print("准备打开巨量多主账户专用浏览器：")
    for account in accounts:
        profile = ROOT / account["chrome_profile_dir"]
        profile.mkdir(parents=True, exist_ok=True)
        help_page = write_login_page(account)
        first_advertiser = account["advertiser_ids"][0]
        ad_url = f"https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid={urllib.parse.quote(first_advertiser)}"
        args = [
            chrome,
            f"--remote-debugging-port={account['chrome_debug_port']}",
            f"--user-data-dir={profile}",
            "--start-maximized",
            "--disable-features=Translate",
            file_url(help_page),
            ad_url,
        ]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"已打开：{account['name']}  端口:{account['chrome_debug_port']}  子账户:{', '.join(account['advertiser_ids'])}")
    print("")
    print("请按每个浏览器说明页登录对应主账户。")


if __name__ == "__main__":
    raise SystemExit(main())
