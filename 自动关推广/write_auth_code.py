import json
import os
import argparse
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

try:
    import websocket
except Exception:
    websocket = None


ROOT = Path(os.environ.get("OCEANENGINE_ROOT") or Path(__file__).resolve().parent)
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8-sig"))
TOKEN_FILE = ROOT / CONFIG.get("token_file", "oceanengine_tokens.json")
LOG_DIR = ROOT / "rizhi"
LOG_FILE = LOG_DIR / "auth.log"
AUTH_STATUS_FILE = LOG_DIR / "授权状态.txt"


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
            "token_file": config.get("token_file", "oceanengine_tokens.json"),
        }]
    normalized = []
    for index, account in enumerate(accounts, start=1):
        account_id = str(account.get("id") or f"main_{index:02d}")
        normalized.append({
            "id": account_id,
            "name": str(account.get("name") or account_id),
            "enabled": account.get("enabled") is not False,
            "advertiser_ids": [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()],
            "chrome_debug_port": int(account.get("chrome_debug_port") or (9221 + index)),
            "chrome_profile_dir": account.get("chrome_profile_dir") or f"chrome-profiles/{account_id}",
            "token_file": account.get("token_file") or f"tokens/{account_id}.json",
            "app_id": account.get("app_id"),
            "app_secret": account.get("app_secret"),
            "redirect_uri": account.get("redirect_uri"),
        })
    return normalized


def apply_main_account(account_id):
    global CONFIG, TOKEN_FILE
    if not account_id:
        return None
    for account in normalize_main_accounts(CONFIG):
        if account["id"].lower() == account_id.lower():
            CONFIG = dict(CONFIG)
            CONFIG["chrome_debug_port"] = account["chrome_debug_port"]
            CONFIG["chrome_profile_dir"] = account["chrome_profile_dir"]
            CONFIG["token_file"] = account["token_file"]
            CONFIG["main_account_id"] = account["id"]
            CONFIG["main_account_name"] = account["name"]
            if account.get("app_id"):
                CONFIG["app_id"] = account["app_id"]
            if account.get("app_secret"):
                CONFIG["app_secret"] = account["app_secret"]
            if account.get("redirect_uri"):
                CONFIG["redirect_uri"] = account["redirect_uri"]
            TOKEN_FILE = ROOT / account["token_file"]
            return account
    raise RuntimeError(f"没有找到主账户编号: {account_id}")


try:
    from main_accounts import normalize_main_accounts as normalize_main_accounts
except Exception:
    pass


def log(message, **fields):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
        **fields,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(json.dumps(payload, ensure_ascii=False))


def request_json(url, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_json(url, timeout=8, method="GET"):
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_code(text):
    text = text.strip()
    if text.startswith("http"):
        parsed = urllib.parse.urlparse(text)
        qs = urllib.parse.parse_qs(parsed.query)
        return (qs.get("auth_code") or qs.get("code") or [""])[0]
    return text


def build_auth_url():
    state = "auto-close-" + datetime.now().strftime("%Y%m%d%H%M%S")
    params = {
        "app_id": CONFIG["app_id"],
        "state": state,
    }
    redirect_uri = CONFIG.get("redirect_uri")
    if redirect_uri:
        params["redirect_uri"] = redirect_uri
    return "https://open.oceanengine.com/audit/oauth.html?" + urllib.parse.urlencode(params)


def write_auth_status(status, detail=None):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"状态: {status}",
        f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if detail:
        lines.append(f"说明: {detail}")
    AUTH_STATUS_FILE.write_text("\n".join(lines), encoding="utf-8")


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
    raise RuntimeError("没有找到 Google Chrome")


def devtools_url(port, path):
    return f"http://127.0.0.1:{port}{path}"


def devtools_targets(port):
    return http_json(devtools_url(port, "/json"), timeout=3)


def open_devtools_page(port, url):
    encoded = urllib.parse.quote(url, safe=":/?&=%")
    req = urllib.request.Request(devtools_url(port, f"/json/new?{encoded}"), method="PUT")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_chrome(auth_url):
    port = int(CONFIG.get("chrome_debug_port", 9222))
    profile = ROOT / CONFIG.get("chrome_profile_dir", "chrome-debug-profile")
    try:
        targets = devtools_targets(port)
        if targets:
            return port, open_devtools_page(port, auth_url)
    except Exception:
        pass

    profile.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    subprocess.Popen(
        [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--start-maximized",
            "--disable-features=Translate",
            auth_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            targets = devtools_targets(port)
            pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            if pages:
                return port, pages[0]
        except Exception:
            time.sleep(1)
    raise RuntimeError("专用 Chrome 启动失败")


class Cdp:
    def __init__(self, target):
        if websocket is None:
            raise RuntimeError("缺少 websocket-client，请先运行 首次安装.bat")
        self.target = target
        self.ws = None
        self.next_id = 1

    def __enter__(self):
        self.ws = websocket.create_connection(self.target["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self.ws.settimeout(8)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def eval(self, expression, timeout=12):
        msg_id = self.next_id
        self.next_id += 1
        self.ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": int(timeout * 1000),
            },
        }))
        deadline = time.time() + timeout + 3
        while time.time() < deadline:
            res = json.loads(self.ws.recv())
            if res.get("id") != msg_id:
                continue
            result = (res.get("result") or {}).get("result") or {}
            return result.get("value")
        return None


def auto_click_authorize(cdp):
    script = r"""
    (() => {
      const bad = /取消|拒绝|不同意|退出|返回|删除/;
      const good = /确认授权|同意授权|允许授权|确认|授权|同意|允许/;
      const visible = (el) => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);
        return r.width > 8 && r.height > 8 && s.display !== 'none' && s.visibility !== 'hidden' && !el.disabled;
      };
      for (const cb of Array.from(document.querySelectorAll('input[type="checkbox"]'))) {
        const text = (cb.closest('label') || cb.parentElement || document.body).innerText || '';
        if (!cb.checked && !bad.test(text)) cb.click();
      }
      const nodes = Array.from(document.querySelectorAll('button,a,[role="button"],.btn,.ant-btn'));
      for (const el of nodes) {
        const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim();
        if (!visible(el) || !good.test(text) || bad.test(text)) continue;
        el.click();
        return {clicked: true, text};
      }
      return {clicked: false, title: document.title, text: document.body.innerText.slice(0, 300)};
    })()
    """
    return cdp.eval(script)


def auto_get_auth_code(auth_url):
    port, target = ensure_chrome(auth_url)
    log("已打开授权页", port=port, url=auth_url)
    deadline = time.time() + 180
    with Cdp(target) as cdp:
        while time.time() < deadline:
            current = cdp.eval("location.href")
            code = parse_code(current or "")
            if code and code != (current or "").strip():
                log("已自动获取授权码", url=(current or "")[:200])
                return code
            clicked = auto_click_authorize(cdp)
            if clicked and clicked.get("clicked"):
                log("已自动点击授权按钮", text=clicked.get("text"))
            time.sleep(2)
    return ""


def save_token_response(token_response):
    old = {}
    if TOKEN_FILE.exists():
        backup = TOKEN_FILE.with_suffix(".before-auth.json")
        try:
            old = json.loads(TOKEN_FILE.read_text(encoding="utf-8-sig"))
            backup.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            old = {}
    saved = {
        **old,
        "token_response": token_response,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")


def exchange_and_save(code):
    body = {
        "app_id": CONFIG["app_id"],
        "secret": CONFIG["app_secret"],
        "grant_type": "auth_code",
        "auth_code": code,
    }
    token_response = request_json("https://api.oceanengine.com/open_api/oauth2/access_token/", body)
    save_token_response(token_response)
    if token_response.get("code") == 0:
        write_auth_status("正常", "授权写入完成")
    else:
        write_auth_status("授权写入失败", token_response.get("message"))
    log("授权写入完成", code=token_response.get("code"), api_message=token_response.get("message"), token_file=str(TOKEN_FILE))
    return 0 if token_response.get("code") == 0 else 1


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-account", default="", help="主账户编号，例如 main_01、main_02")
    parser.add_argument("auth_text", nargs="*", help="完整回调链接或 auth_code")
    args = parser.parse_args()
    account = apply_main_account(args.main_account)
    if account:
        print(f"当前写入授权的主账户：{account['name']} ({account['id']})")
        print(f"token 文件：{TOKEN_FILE}")
    raw = " ".join(args.auth_text).strip()
    if raw:
        code = parse_code(raw)
    else:
        auth_url = build_auth_url()
        print("将使用专用 Chrome 自动打开巨量授权页，并尝试自动点击确认授权。")
        print("如果出现登录、短信、验证码，请你在浏览器里手动完成。")
        print("")
        code = auto_get_auth_code(auth_url)
        if not code:
            print("")
            print("没有自动拿到授权码。请把授权后的完整回调网址粘贴到这里。")
            raw = input("回调网址或 auth_code: ").strip()
            code = parse_code(raw)
    if not code:
        write_auth_status("需要人工处理", "没有识别到 auth_code")
        raise RuntimeError("没有识别到 auth_code")
    return exchange_and_save(code)


if __name__ == "__main__":
    raise SystemExit(main())
