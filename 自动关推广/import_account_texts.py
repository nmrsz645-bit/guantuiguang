import argparse
import json
import os
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from main_accounts import load_text_accounts, parse_account_file


ROOT = Path(os.environ.get("OCEANENGINE_ROOT") or Path(__file__).resolve().parent)
CONFIG_FILE = ROOT / "config.json"
LOG_DIR = ROOT / "rizhi"
LOG_FILE = LOG_DIR / "account-import.log"
STATUS_FILE = LOG_DIR / "账号接口导入状态.txt"
OPEN_API_BASE = "https://api.oceanengine.com"


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message, **fields):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"time": now_text(), "message": message, **fields}
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def read_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    return {}


def write_config(config):
    backup = CONFIG_FILE.with_suffix(f".before-account-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    if CONFIG_FILE.exists():
        backup.write_text(CONFIG_FILE.read_text(encoding="utf-8-sig"), encoding="utf-8")
    # Replace in one operation so a running monitor never reads a half-written file.
    temp_file = CONFIG_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(config, ensure_ascii=False, indent=4), encoding="utf-8")
    temp_file.replace(CONFIG_FILE)
    return backup


def parse_code(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text.startswith("http"):
        parsed = urllib.parse.urlparse(text)
        qs = urllib.parse.parse_qs(parsed.query)
        return (qs.get("auth_code") or qs.get("code") or [""])[0]
    return text


def request_json(url, body):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except Exception:
            data = {"message": raw}
        data["http_status"] = exc.code
        return data


def save_token(account, token_response):
    token_path = ROOT / account["token_file"]
    token_path.parent.mkdir(parents=True, exist_ok=True)
    old = {}
    if token_path.exists():
        try:
            old = json.loads(token_path.read_text(encoding="utf-8-sig"))
        except Exception:
            old = {}
    saved = {
        **old,
        "main_account_id": account["id"],
        "main_account_name": account["name"],
        "app_id": account["app_id"],
        "advertiser_ids": account["advertiser_ids"],
        "token_response": token_response,
        "saved_at": now_text(),
    }
    token_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return token_path


def token_file_is_valid(account):
    token_path = ROOT / account["token_file"]
    if not token_path.exists():
        return False, "没有 token 文件"
    try:
        data = json.loads(token_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return False, f"token 文件读取失败: {exc}"
    payload = (data.get("token_response") or {}).get("data") or {}
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    if not access_token:
        return False, "token 文件里没有 access_token"
    if not refresh_token:
        return True, "已有 access_token"
    body = {
        "app_id": account["app_id"],
        "secret": account["app_secret"],
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    result = request_json(f"{OPEN_API_BASE}/open_api/oauth2/refresh_token/", body)
    if result.get("code") == 0 and (result.get("data") or {}).get("access_token"):
        save_token(account, result)
        return True, "已有 refresh_token，已刷新成功"
    return False, result.get("message") or result.get("api_message") or "refresh_token 刷新失败"


def exchange_auth_code(account):
    code = parse_code(account.get("callback_url")) or parse_code(account.get("auth_code"))
    if not code:
        return False, "没有 auth_code 或完整回调链接"
    body = {
        "app_id": account["app_id"],
        "secret": account["app_secret"],
        "grant_type": "auth_code",
        "auth_code": code,
    }
    result = request_json(f"{OPEN_API_BASE}/open_api/oauth2/access_token/", body)
    if result.get("code") == 0 and (result.get("data") or {}).get("access_token"):
        save_token(account, result)
        return True, "auth_code 换 token 成功"
    log("auth_code 换 token 失败，未覆盖旧 token", account_id=account["id"], name=account["name"], code=result.get("code"), api_message=result.get("message"), http_status=result.get("http_status"))
    return False, result.get("message") or result.get("api_message") or f"接口返回 code={result.get('code')}"


def account_defaults(account, config, index, preserve_existing_authorization=False):
    account = dict(account)
    old = {}
    for idx, item in enumerate(config.get("main_accounts") or [], start=1):
        old_id = str(item.get("id") or f"main_{idx:02d}")
        if old_id == account["id"]:
            old = item
            break
    if preserve_existing_authorization and old:
        account["app_id"] = old.get("app_id") or config.get("app_id")
        account["app_secret"] = old.get("app_secret") or config.get("app_secret")
        account["redirect_uri"] = old.get("redirect_uri") or config.get("redirect_uri")
        account["chrome_debug_port"] = int(old.get("chrome_debug_port") or (9222 if account["id"] == "main_01" else 9300 + index))
        account["chrome_profile_dir"] = old.get("chrome_profile_dir") or ("chrome-debug-profile" if account["id"] == "main_01" else f"chrome-profiles/{account['id']}")
        account["token_file"] = old.get("token_file") or f"tokens/{account['id']}.json"
    else:
        account["app_id"] = account.get("app_id") or old.get("app_id") or config.get("app_id")
        account["app_secret"] = account.get("app_secret") or old.get("app_secret") or config.get("app_secret")
        account["redirect_uri"] = account.get("redirect_uri") or old.get("redirect_uri") or config.get("redirect_uri")
        account["chrome_debug_port"] = int(account.get("chrome_debug_port") or old.get("chrome_debug_port") or (9222 if account["id"] == "main_01" else 9300 + index))
        account["chrome_profile_dir"] = account.get("chrome_profile_dir") or old.get("chrome_profile_dir") or ("chrome-debug-profile" if account["id"] == "main_01" else f"chrome-profiles/{account['id']}")
        account["token_file"] = account.get("token_file") or old.get("token_file") or f"tokens/{account['id']}.json"
    return account


def sync_config(config, accounts):
    config["account_source"] = "text_files"
    existing = {}
    for idx, item in enumerate(config.get("main_accounts") or [], start=1):
        account_id = str(item.get("id") or f"main_{idx:02d}")
        # Account text files are authoritative. A removed text file must not
        # leave its previous account silently enabled in config.json.
        existing[account_id] = dict(item, id=account_id, enabled=False)
    for account in accounts:
        old = existing.get(account["id"], {})
        merged = {
            **old,
            "id": account["id"],
            "name": account["name"],
            "enabled": True,
            "chrome_debug_port": account["chrome_debug_port"],
            "chrome_profile_dir": account["chrome_profile_dir"],
            "token_file": account["token_file"],
            "advertiser_ids": account["advertiser_ids"],
            "app_id": account["app_id"],
            "app_secret": account["app_secret"],
            "redirect_uri": account["redirect_uri"],
            "allow_close": account.get("allow_close", True),
        }
        existing[account["id"]] = merged
    def sort_key(item):
        digits = "".join(ch for ch in item[0] if ch.isdigit())
        return int(digits or 9999), item[0]
    config["main_accounts"] = [item for _, item in sorted(existing.items(), key=sort_key)]
    if accounts:
        first = accounts[0]
        config["advertiser_ids"] = first["advertiser_ids"]
        config["chrome_debug_port"] = first["chrome_debug_port"]
        config["chrome_profile_dir"] = first["chrome_profile_dir"]
        config["token_file"] = first["token_file"]
        config["app_id"] = first["app_id"]
        config["app_secret"] = first["app_secret"]
        config["redirect_uri"] = first["redirect_uri"]
    return config


def status_line(result):
    prefix = "成功" if result["ok"] else "失败"
    return f"{prefix} | {result['id']} | {result['name']} | 子账户 {len(result['advertiser_ids'])} 个 | {result['detail']}"


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--accounts-only",
        action="store_true",
        help="只同步账号配置，不检查或更新授权和 token",
    )
    return parser.parse_args(argv)


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = parse_args(argv)
    config = read_config()
    raw_accounts = load_text_accounts()
    accounts = []
    results = []
    for index, raw in enumerate(raw_accounts, start=1):
        account = account_defaults(
            raw,
            config,
            index,
            preserve_existing_authorization=args.accounts_only,
        )
        if not account.get("app_id") or not account.get("app_secret"):
            results.append({**account, "ok": False, "detail": "缺少 App ID 或 Secret"})
            continue
        if not account.get("advertiser_ids"):
            results.append({**account, "ok": False, "detail": "缺少 advertiser_id"})
            continue
        accounts.append(account)
    if not accounts and not results:
        raise RuntimeError("没有找到已启用且填写了 advertiser_id 的账号文本档。")
    config = sync_config(config, accounts)
    backup = write_config(config)
    print(f"已同步账号配置，备份: {backup}")
    print("")
    for account in accounts:
        try:
            if args.accounts_only:
                ok, detail = True, "账号配置已同步，原授权、token 和登录资料保持不变"
            else:
                ok, detail = token_file_is_valid(account)
                if not ok:
                    ok, detail = exchange_auth_code(account)
            result = {**account, "ok": ok, "detail": detail}
        except Exception as exc:
            result = {**account, "ok": False, "detail": str(exc)}
            log("账号导入异常", account_id=account["id"], name=account["name"], error=str(exc), traceback=traceback.format_exc())
        results.append(result)
        print(status_line(result))
        log("账号接口导入结果", account_id=result["id"], name=result["name"], ok=result["ok"], detail=result["detail"], advertisers=result["advertiser_ids"], token_file=result["token_file"])
    ok_count = sum(1 for item in results if item["ok"])
    fail_count = len(results) - ok_count
    lines = [
        "账号配置导入状态" if args.accounts_only else "账号接口导入状态",
        f"时间: {now_text()}",
        f"模式: {'仅导入账号（不处理授权）' if args.accounts_only else '导入账号并处理授权'}",
        f"成功: {ok_count}",
        f"失败: {fail_count}",
        "",
        *[status_line(item) for item in results],
    ]
    STATUS_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("")
    print(f"结果已写入: {STATUS_FILE}")
    if args.accounts_only and ok_count:
        print("仅账号导入完成：没有读取、刷新或覆盖授权码、回调链接、token 和浏览器登录资料。")
    if fail_count and not args.accounts_only:
        print("有失败项：通常是 auth_code 已用过/过期，或 App ID/Secret 不匹配。需要重新授权后把新回调链接填进对应文本档。")
    return 0 if ok_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
