import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

try:
    import websocket
except Exception:
    websocket = None


# A desktop build supplies a writable data folder; source installs preserve
# their original folder-based layout when the variable is absent.
ROOT = Path(os.environ.get("OCEANENGINE_ROOT") or Path(__file__).resolve().parent)
CONFIG_FILE = ROOT / "config.json"
STATE_WRITE_LOCK = threading.Lock()
TOKEN_REFRESH_LOCK = threading.Lock()
LOG_DIR = ROOT / "rizhi"
DATA_DIR = ROOT / "data"
MAIN_LOG = LOG_DIR / "monitor.log"
EVENT_LOG = LOG_DIR / "events.jsonl"
CRASH_LOG = LOG_DIR / "crash.log"
STATE_FILE = DATA_DIR / "unit_state.json"
LOCK_FILE = DATA_DIR / "monitor.lock"
AUTH_STATUS_FILE = LOG_DIR / "授权状态.txt"
OPEN_API_BASE = "https://api.oceanengine.com"
HEARTBEAT_SECONDS = int(os.getenv("OCEANENGINE_HEARTBEAT_SECONDS", "60"))
AUTO_AUTH_TIMEOUT_SECONDS = int(os.getenv("OCEANENGINE_AUTO_AUTH_TIMEOUT_SECONDS", "240"))
LOG_RETENTION_HOURS = int(os.getenv("OCEANENGINE_LOG_RETENTION_HOURS", "72"))
LOG_CLEANUP_INTERVAL_SECONDS = 60 * 60
_last_log_cleanup = 0.0


class AuthRequired(RuntimeError):
    pass


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cleanup_old_logs(force=False):
    """Keep diagnostic output bounded, including log files that are appended forever."""
    global _last_log_cleanup
    now_ts = time.time()
    if not force and now_ts - _last_log_cleanup < LOG_CLEANUP_INTERVAL_SECONDS:
        return
    _last_log_cleanup = now_ts
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(hours=max(1, LOG_RETENTION_HOURS))
    cutoff_ts = cutoff.timestamp()
    for path in LOG_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff_ts:
                path.unlink()
                continue
            if path.suffix.lower() not in {".log", ".jsonl"}:
                continue
            kept = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                timestamp = None
                if line.startswith("[") and len(line) >= 20:
                    try:
                        timestamp = datetime.strptime(line[1:20], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                elif path.suffix.lower() == ".jsonl":
                    try:
                        raw_time = json.loads(line).get("time")
                        timestamp = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        pass
                if timestamp is None or timestamp >= cutoff:
                    kept.append(line)
            new_text = "\n".join(kept)
            if kept:
                new_text += "\n"
            path.write_text(new_text, encoding="utf-8")
        except OSError:
            # Logging must never stop the monitor.
            continue


def log(message, **fields):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_old_logs()
    line = f"[{now_text()}] {message}"
    if fields:
        line += " " + json.dumps(fields, ensure_ascii=False, default=str)
    print(line, flush=True)
    with MAIN_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    payload = {"time": now_text(), "message": message, **fields}
    with EVENT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def auto_reauthorize():
    script = ROOT / "write_auth_code.py"
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--auth-service"]
    elif not script.exists():
        log("自动重新授权脚本不存在", script=str(script))
        return False
    else:
        command = [sys.executable, str(script)]
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    log("开始自动重新授权", script=str(script), timeout_seconds=AUTO_AUTH_TIMEOUT_SECONDS)
    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            env=env,
            timeout=AUTO_AUTH_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log("自动重新授权超时，等待下轮继续尝试", timeout_seconds=AUTO_AUTH_TIMEOUT_SECONDS)
        return False
    except Exception as exc:
        log("自动重新授权异常，等待下轮继续尝试", error=str(exc))
        return False
    if result.returncode == 0:
        write_auth_status("正常", "授权失效后已自动重新获取")
        log("自动重新授权成功")
        return True
    log("自动重新授权失败，等待下轮继续尝试", returncode=result.returncode)
    return False


def write_auth_status(status, detail=None):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        f"状态: {status}",
        f"时间: {now_text()}",
    ]
    if detail:
        lines.append(f"说明: {detail}")
    lines.append("")
    lines.append("如果显示需要重新授权，请双击“重新授权并写入.bat”。")
    AUTH_STATUS_FILE.write_text("\n".join(lines), encoding="utf-8")


def write_crash_log(title, error):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with CRASH_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{now_text()}] {title}: {error}\n")
        f.write(traceback.format_exc())
        f.write("\n")


def is_refresh_invalid(result):
    code = str(result.get("code") or "")
    msg = str(result.get("message") or result.get("api_message") or result.get("msg") or "")
    return code == "40103" or "refresh_token" in msg and ("失效" in msg or "重新授权" in msg)


def load_config():
    if not CONFIG_FILE.exists():
        raise RuntimeError(f"缺少配置文件: {CONFIG_FILE}")
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
            "token_file": config.get("token_file", "oceanengine_tokens.json"),
        }]
    normalized = []
    used_ports = set()
    for index, account in enumerate(accounts, start=1):
        if not account or account.get("enabled") is False:
            continue
        advertisers = [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()]
        if not advertisers:
            continue
        account_id = str(account.get("id") or f"main_{index:02d}")
        port = int(account.get("chrome_debug_port") or (9221 + index))
        if port in used_ports:
            raise RuntimeError(f"主账户端口重复: {port}")
        used_ports.add(port)
        normalized.append({
            "id": account_id,
            "name": str(account.get("name") or account_id),
            "enabled": True,
            "advertiser_ids": advertisers,
            "chrome_debug_port": port,
            "chrome_profile_dir": account.get("chrome_profile_dir") or f"chrome-profiles/{account_id}",
            "token_file": account.get("token_file") or f"tokens/{account_id}.json",
            "app_id": account.get("app_id"),
            "app_secret": account.get("app_secret"),
            "redirect_uri": account.get("redirect_uri"),
            "allow_close": account.get("allow_close", True),
        })
    return normalized


def account_config(config, account):
    merged = dict(config)
    merged["chrome_debug_port"] = account["chrome_debug_port"]
    merged["chrome_profile_dir"] = account["chrome_profile_dir"]
    merged["token_file"] = account["token_file"]
    merged["main_account_id"] = account["id"]
    merged["main_account_name"] = account["name"]
    if account.get("app_id"):
        merged["app_id"] = account["app_id"]
    if account.get("app_secret"):
        merged["app_secret"] = account["app_secret"]
    if account.get("redirect_uri"):
        merged["redirect_uri"] = account["redirect_uri"]
    if account.get("allow_close") is False:
        merged["dry_run"] = True
    return merged


try:
    from main_accounts import normalize_main_accounts as normalize_main_accounts
except Exception:
    pass


def load_state():
    if not STATE_FILE.exists():
        return {"units": {}, "last_cycle": None}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        backup = STATE_FILE.with_suffix(f".broken-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
        STATE_FILE.replace(backup)
        log("状态文件损坏，已备份并重建", backup=str(backup))
        return {"units": {}, "last_cycle": None}


def save_state(state):
    with STATE_WRITE_LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)


def pid_running(pid):
    if not pid:
        return False
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def acquire_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        old_pid = data.get("pid")
        if pid_running(old_pid):
            raise RuntimeError(f"监控已经在运行，PID={old_pid}")
        log("发现旧锁文件但进程不存在，自动清理", old_pid=old_pid)
        LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(json.dumps({"pid": os.getpid(), "started_at": now_text()}, ensure_ascii=False), encoding="utf-8")


def release_lock():
    try:
        if LOCK_FILE.exists():
            data = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            if int(data.get("pid", 0)) == os.getpid():
                LOCK_FILE.unlink(missing_ok=True)
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
    raise RuntimeError("没有找到 Google Chrome，请先安装谷歌浏览器，或设置 CHROME_PATH")


def http_json(url, timeout=10, method="GET", body=None, headers=None):
    data = None
    req_headers = headers or {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers = {"Content-Type": "application/json", **req_headers}
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {"raw": text}
        parsed["http_status"] = exc.code
        return parsed
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "code": "network_error",
            "message": str(exc),
            "http_status": None,
        }


def devtools_url(port, path):
    return f"http://127.0.0.1:{port}{path}"


def devtools_targets(port):
    targets = http_json(devtools_url(port, "/json"), timeout=3)
    if isinstance(targets, list):
        return targets
    log("Chrome 调试端口未返回页面列表", port=port, result_type=type(targets).__name__, result=str(targets)[:500])
    return []


def open_devtools_page(port, url):
    encoded = urllib.parse.quote(url, safe=":/?&=%")
    req = urllib.request.Request(devtools_url(port, f"/json/new?{encoded}"), method="PUT")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_chrome(config, first_advertiser):
    port = int(config.get("chrome_debug_port", 9222))
    profile = ROOT / config.get("chrome_profile_dir", "chrome-debug-profile")
    url = f"https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid={first_advertiser}"
    try:
        targets = devtools_targets(port)
        if targets:
            return port
    except Exception:
        pass
    chrome = find_chrome()
    profile.mkdir(parents=True, exist_ok=True)
    args = [
        chrome,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--start-maximized",
        "--disable-features=Translate",
        url,
    ]
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("已启动专用 Chrome", port=port, profile=str(profile))
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            if devtools_targets(port):
                return port
        except Exception:
            time.sleep(1)
    raise RuntimeError("专用 Chrome 启动失败，请先运行 打开巨量登录.bat")


class Cdp:
    def __init__(self, port, advertiser_id):
        if websocket is None:
            raise RuntimeError("缺少 websocket-client，请先运行 首次安装.bat")
        self.port = port
        self.advertiser_id = str(advertiser_id)
        self.ws = None
        self.next_id = 1

    def __enter__(self):
        target = self.pick_target()
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self.ws.settimeout(45)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def pick_target(self):
        targets = devtools_targets(self.port)
        pages = [t for t in targets if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        wanted = f"aadvid={self.advertiser_id}"
        for target in pages:
            url = target.get("url") or ""
            if "ad.oceanengine.com" in url and wanted in url:
                return target
        page_url = f"https://ad.oceanengine.com/promotion/promote-manage/ad?aadvid={self.advertiser_id}"
        try:
            target = open_devtools_page(self.port, page_url)
            time.sleep(3)
            return target
        except Exception:
            pass
        for target in pages:
            if "ad.oceanengine.com" in (target.get("url") or ""):
                return target
        if pages:
            return pages[0]
        raise RuntimeError("没有找到可调试的 Chrome 页面")

    def eval(self, expression):
        msg_id = self.next_id
        self.next_id += 1
        self.ws.send(json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
                "timeout": 60000,
            },
        }))
        deadline = time.time() + 65
        while time.time() < deadline:
            try:
                res = json.loads(self.ws.recv())
            except Exception as exc:
                if "timed out" in str(exc).lower():
                    raise RuntimeError("浏览器接口等待超时 45 秒，已跳过本轮")
                raise
            if res.get("id") != msg_id:
                continue
            if "exceptionDetails" in res:
                raise RuntimeError(json.dumps(res["exceptionDetails"], ensure_ascii=False)[:1200])
            result = (res.get("result") or {}).get("result") or {}
            if "value" in result:
                return result["value"]
            return result
        raise RuntimeError("CDP 执行超时")

    def fetch_json(self, path, method="GET", body=None):
        body_js = "undefined" if body is None else json.dumps(body, ensure_ascii=False)
        expr = f"""
        (async () => {{
          const resp = await fetch({json.dumps(path)}, {{
            method: {json.dumps(method)},
            credentials: 'include',
            headers: {{'content-type': 'application/json'}},
            body: {body_js} === undefined ? undefined : JSON.stringify({body_js})
          }});
          const text = await resp.text();
          let data = null;
          try {{ data = JSON.parse(text); }} catch(e) {{ data = {{raw: text}}; }}
          return {{ok: resp.ok, status: resp.status, data}};
        }})()
        """
        return self.eval(expr)


def today_range():
    day = datetime.now().strftime("%Y-%m-%d")
    return day, day


def list_units(cdp, advertiser_id, page, page_size):
    st, et = today_range()
    body = {
        "project_ids": [],
        "project_status": [-1],
        "promotion_status": [-1],
        "page": page,
        "limit": page_size,
        "fields": [],
        "cascade_fields": [],
        "campaign_type": [1],
        "sort_stat": "create_time",
        "isSophonx": 1,
        "sort_order": 1,
        "st": st,
        "et": et,
    }
    path = f"/ad/api/promotion/ads/list?aadvid={advertiser_id}"
    result = cdp.fetch_json(path, "POST", body)
    return result


def preview_info(cdp, advertiser_id, promotion_id, auto_ad_id):
    params = urllib.parse.urlencode({
        "aadvid": str(advertiser_id),
        "promotion_id": str(promotion_id),
        "ad_id": str(auto_ad_id or promotion_id),
    })
    return cdp.fetch_json(f"/superior/api/promote/ads/get_preview_info?{params}", "GET")


def token_data(config):
    token_file = ROOT / config.get("token_file", "oceanengine_tokens.json")
    if not token_file.exists():
        raise RuntimeError(f"缺少授权文件: {token_file}")
    data = json.loads(token_file.read_text(encoding="utf-8-sig"))
    token = ((data.get("token_response") or {}).get("data") or {}).get("access_token")
    refresh = ((data.get("token_response") or {}).get("data") or {}).get("refresh_token")
    if not token:
        raise RuntimeError("授权文件里没有 access_token，请重新授权")
    return token, refresh, token_file, data


def refresh_token(config):
    # Several advertiser workers may share one main-account token file.
    with TOKEN_REFRESH_LOCK:
        return _refresh_token_locked(config)


def _refresh_token_locked(config):
    token, refresh, token_file, saved = token_data(config)
    if not refresh:
        return token
    body = {
        "app_id": config["app_id"],
        "secret": config["app_secret"],
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }
    result = http_json(f"{OPEN_API_BASE}/open_api/oauth2/refresh_token/", method="POST", body=body, timeout=30)
    if result.get("code") == 0 and (result.get("data") or {}).get("access_token"):
        saved["token_response"] = result
        saved["saved_at"] = now_text()
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
        write_auth_status("正常", "access_token 已自动刷新")
        log("access_token 已刷新")
        return result["data"]["access_token"]
    if is_refresh_invalid(result):
        write_auth_status("需要重新授权", result.get("message") or "refresh_token 已失效")
        log("refresh_token 已失效，已停止本轮关推广，请运行重新授权并写入.bat", code=result.get("code"), api_message=result.get("message"), http_status=result.get("http_status"))
        raise AuthRequired("refresh_token 已失效，请运行 重新授权并写入.bat")
    log("access_token 刷新失败，继续使用旧 token", code=result.get("code"), api_message=result.get("message"), http_status=result.get("http_status"))
    return token


def close_unit_open_api(config, advertiser_id, promotion_id):
    access_token = refresh_token(config)
    body = {
        "advertiser_id": int(advertiser_id),
        "data": [
            {
                "promotion_id": int(promotion_id),
                "opt_status": "DISABLE",
            }
        ],
    }
    headers = {"Access-Token": access_token}
    result = http_json(f"{OPEN_API_BASE}/open_api/v3.0/promotion/status/update/", method="POST", body=body, headers=headers, timeout=30)
    return result


def is_unit_open(ad):
    text = " ".join(str(ad.get(k) or "") for k in [
        "promotion_status_name",
        "promotion_status_first_name",
        "promotion_status_second_name",
        "project_status_name",
    ])
    opt = ad.get("ad_opt_status")
    if opt == 0:
        return True
    if any(word in text for word in ["投放中", "启用中"]):
        return True
    if any(word in text for word in ["已暂停", "已删除"]):
        return False
    return False


def ad_summary(ad):
    return {
        "promotion_id": str(ad.get("promotion_id") or ""),
        "auto_ad_id": str(ad.get("auto_ad_id") or ""),
        "ad_id": str(ad.get("ad_id") or ""),
        "name": ad.get("promotion_name") or ad.get("name"),
        "project_name": ad.get("project_name"),
        "ad_opt_status": ad.get("ad_opt_status"),
        "promotion_status": ad.get("promotion_status"),
        "promotion_status_name": ad.get("promotion_status_name"),
        "promotion_status_first_name": ad.get("promotion_status_first_name"),
        "promotion_status_second_name": ad.get("promotion_status_second_name"),
        "is_preview_able": ad.get("is_preview_able"),
    }


def response_data_dict(result):
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else {}


def preview_payload_dict(prev):
    outer = response_data_dict(prev)
    inner = outer.get("data")
    if isinstance(inner, dict):
        return inner
    return outer


def scan_advertiser(config, state, port, advertiser_id, once=False, no_close=False):
    page_size = int(config.get("page_size", 20))
    max_pages = int(config.get("max_pages", 120))
    total = 0
    open_count = 0
    qr_ready_count = 0
    closed_count = 0
    errors = 0
    with Cdp(port, advertiser_id) as cdp:
        for page in range(1, max_pages + 1):
            if page == 1 or page % 10 == 0:
                log("正在读取单元列表页", advertiser_id=advertiser_id, page=page)
            result = list_units(cdp, advertiser_id, page, page_size)
            if not isinstance(result, dict):
                log("读取单元列表返回异常类型", advertiser_id=advertiser_id, page=page, result_type=type(result).__name__, result=str(result)[:1000])
                errors += 1
                break
            if not result.get("ok"):
                log("读取单元列表失败", advertiser_id=advertiser_id, page=page, status=result.get("status"), data=result.get("data"))
                errors += 1
                break
            data = result.get("data") or {}
            if not isinstance(data, dict):
                log("读取单元列表内容不是JSON对象，本轮跳过", advertiser_id=advertiser_id, page=page, data_type=type(data).__name__, data=str(data)[:1000])
                errors += 1
                break
            if data.get("code") not in (None, 0):
                extra = data.get("extra") or {}
                log(
                    "读取单元列表返回错误，可能需要先登录专用 Chrome",
                    advertiser_id=advertiser_id,
                    page=page,
                    code=data.get("code"),
                    msg=data.get("msg") or data.get("message"),
                    redirect_url=extra.get("redirect_url"),
                    request_id=data.get("request_id"),
                )
                errors += 1
                break
            payload = data.get("data") or data
            if not isinstance(payload, dict):
                log("读取单元列表数据格式异常，本轮跳过", advertiser_id=advertiser_id, page=page, payload_type=type(payload).__name__, payload=str(payload)[:1000])
                errors += 1
                break
            ads = payload.get("ads") or payload.get("list") or []
            if not isinstance(ads, list):
                log("读取单元列表 ads 格式异常，本轮跳过", advertiser_id=advertiser_id, page=page, ads_type=type(ads).__name__)
                errors += 1
                break
            if not ads:
                break
            total += len(ads)
            for ad in ads:
                if not isinstance(ad, dict):
                    log("跳过异常单元记录", advertiser_id=advertiser_id, page=page, ad_type=type(ad).__name__, ad=str(ad)[:500])
                    continue
                summary = ad_summary(ad)
                promotion_id = summary["promotion_id"]
                if not promotion_id:
                    continue
                key = f"{advertiser_id}:{promotion_id}"
                unit_state = state.setdefault("units", {}).setdefault(key, {})
                unit_state.update({
                    "advertiser_id": str(advertiser_id),
                    "promotion_id": promotion_id,
                    "auto_ad_id": summary["auto_ad_id"],
                    "name": summary["name"],
                    "project_name": summary["project_name"],
                    "last_seen_at": now_text(),
                    "last_status": summary,
                })
                if not is_unit_open(ad):
                    continue
                open_count += 1
                log("发现打开状态单元", advertiser_id=advertiser_id, unit=summary)
                auto_ad_id = summary["auto_ad_id"] or summary["ad_id"] or promotion_id
                prev = preview_info(cdp, advertiser_id, promotion_id, auto_ad_id)
                prev_data = preview_payload_dict(prev)
                preview_url = prev_data.get("preview_url") or prev_data.get("qr_code_url") or ""
                unit_state["last_preview_check_at"] = now_text()
                unit_state["last_preview_response"] = {
                    "ok": prev.get("ok"),
                    "status": prev.get("status"),
                    "code": prev_data.get("code") if isinstance(prev_data, dict) else None,
                    "has_preview_url": bool(preview_url),
                }
                if not preview_url:
                    log("二维码未生成，本轮跳过", advertiser_id=advertiser_id, promotion_id=promotion_id, auto_ad_id=auto_ad_id)
                    continue
                qr_ready_count += 1
                unit_state["qr_ready_at"] = unit_state.get("qr_ready_at") or now_text()
                if config.get("dry_run") or no_close:
                    log("测试模式：二维码已生成但不关闭", advertiser_id=advertiser_id, promotion_id=promotion_id, name=summary["name"])
                    continue
                close_result = close_unit_open_api(config, advertiser_id, promotion_id)
                if is_refresh_invalid(close_result):
                    write_auth_status("需要重新授权", close_result.get("message") or "关闭接口提示授权失效")
                    raise AuthRequired("巨量授权已失效，请运行 重新授权并写入.bat")
                unit_state["last_close_attempt_at"] = now_text()
                unit_state["last_close_result"] = close_result
                if close_result.get("code") == 0:
                    closed_count += 1
                    unit_state["closed_at"] = now_text()
                    log("已关闭单元开关", advertiser_id=advertiser_id, promotion_id=promotion_id, name=summary["name"], result=close_result.get("data"))
                else:
                    errors += 1
                    log("关闭单元失败", advertiser_id=advertiser_id, promotion_id=promotion_id, code=close_result.get("code"), api_message=close_result.get("message"), http_status=close_result.get("http_status"), result=close_result)
                save_state(state)
            if len(ads) < page_size:
                break
    return {
        "advertiser_id": str(advertiser_id),
        "rows_seen": total,
        "open_count": open_count,
        "qr_ready_count": qr_ready_count,
        "closed_count": closed_count,
        "errors": errors,
    }


def run_cycle_sequential(config, state, accounts, once=False, no_close=False):
    summaries = []
    for account in accounts:
        acct_config = account_config(config, account)
        advertisers = account["advertiser_ids"]
        try:
            port = ensure_chrome(acct_config, advertisers[0])
            log("开始检测主账户", main_account=account["name"], main_account_id=account["id"], port=port, advertisers=advertisers)
            for advertiser_id in advertisers:
                try:
                    item = scan_advertiser(acct_config, state, port, str(advertiser_id), once=once, no_close=no_close)
                    item["main_account"] = account["name"]
                    item["main_account_id"] = account["id"]
                    summaries.append(item)
                except Exception as exc:
                    log("检测账号失败", main_account=account["name"], main_account_id=account["id"], advertiser_id=str(advertiser_id), error=str(exc), traceback=traceback.format_exc())
                    summaries.append({"main_account": account["name"], "main_account_id": account["id"], "advertiser_id": str(advertiser_id), "errors": 1, "error": str(exc)})
                save_state(state)
        except Exception as exc:
            log("主账户浏览器启动或检测失败", main_account=account["name"], main_account_id=account["id"], error=str(exc), traceback=traceback.format_exc())
            summaries.append({"main_account": account["name"], "main_account_id": account["id"], "advertiser_id": "", "errors": 1, "error": str(exc)})
            save_state(state)
    state["last_cycle"] = {"time": now_text(), "summary": summaries}
    save_state(state)
    log("本轮检测完成", summary=summaries)
    return summaries


def run_cycle(config, state, accounts, once=False, no_close=False):
    workers = max(1, int(config.get("parallel_browser_count", 3)))
    log("parallel advertiser scan", workers=workers, account_count=len(accounts), one_browser_per_advertiser=bool(config.get("one_browser_per_advertiser")))
    summaries = []
    with ThreadPoolExecutor(max_workers=min(workers, len(accounts))) as pool:
        futures = [pool.submit(run_cycle_sequential, config, state, [account], once, no_close) for account in accounts]
        for future in as_completed(futures):
            try:
                summaries.extend(future.result())
            except Exception as exc:
                log("parallel advertiser worker failed", error=str(exc))
                summaries.append({"error": str(exc)})
    state["last_cycle"] = {"time": now_text(), "summary": summaries}
    save_state(state)
    log("parallel advertiser scan complete", summary=summaries)
    return summaries


def prepare_accounts(config):
    accounts = normalize_main_accounts(config)
    try:
        from main_accounts import split_accounts_for_parallel_browsers
        accounts = split_accounts_for_parallel_browsers(config, accounts)
    except Exception as exc:
        log("parallel browser account split failed", error=str(exc))
    if not accounts:
        raise RuntimeError("No enabled main account or advertiser ID was found in config.json")
    return accounts


def account_signature(accounts):
    return tuple(
        (
            str(account.get("id") or ""),
            tuple(str(item) for item in account.get("advertiser_ids") or []),
            int(account.get("chrome_debug_port") or 0),
            str(account.get("token_file") or ""),
        )
        for account in accounts
    )


def sleep_with_heartbeat(total_seconds, label):
    remaining = max(0, int(total_seconds))
    heartbeat = max(5, int(HEARTBEAT_SECONDS))
    while remaining > 0:
        step = min(heartbeat, remaining)
        time.sleep(step)
        remaining -= step
        if remaining > 0:
            log("监控心跳", status=label, remaining_seconds=remaining)


def main():
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="只检测一次")
    parser.add_argument("--no-close", action="store_true", help="只检测不关闭")
    args = parser.parse_args()

    config = load_config()
    accounts = normalize_main_accounts(config)
    try:
        from main_accounts import split_accounts_for_parallel_browsers
        accounts = split_accounts_for_parallel_browsers(config, accounts)
    except Exception as exc:
        log("parallel browser account split failed", error=str(exc))
    if not accounts:
        raise RuntimeError("config.json 里没有启用的主账户或 advertiser_ids 为空")

    acquire_lock()
    try:
        state = load_state()
        interval = int(config.get("check_interval_seconds", 40))
        write_auth_status("正常", "监控已启动")
        log("监控启动", root=str(ROOT), main_accounts=[{"id": a["id"], "name": a["name"], "advertisers": a["advertiser_ids"], "port": a["chrome_debug_port"]} for a in accounts], interval_seconds=interval, dry_run=bool(config.get("dry_run")), no_close=args.no_close)
        while True:
            try:
                # Authorization import can update advertiser IDs while the monitor is running.
                latest_config = load_config()
                latest_accounts = prepare_accounts(latest_config)
                if account_signature(latest_accounts) != account_signature(accounts):
                    log(
                        "account configuration reloaded",
                        main_accounts=[{"id": a["id"], "advertisers": a["advertiser_ids"], "port": a["chrome_debug_port"]} for a in latest_accounts],
                    )
                config = latest_config
                accounts = latest_accounts
                interval = int(config.get("check_interval_seconds", 40))
                summaries = run_cycle(config, state, accounts, once=args.once, no_close=args.no_close)
            except AuthRequired as exc:
                log("授权失效，开始尝试自动重新获取", error=str(exc))
                write_crash_log("授权失效，尝试自动重新获取", exc)
                if auto_reauthorize():
                    continue
                write_auth_status("需要重新授权", "自动重新授权未完成，请确认专用 Chrome 是否已登录巨量账号")
                if args.once:
                    return 2
                log("自动重新授权未完成，等待下轮继续尝试", seconds=interval)
                sleep_with_heartbeat(interval, "等待下轮授权重试")
                continue
            if args.once:
                if any(int(item.get("errors") or 0) > 0 for item in summaries):
                    return 2
                break
            log("等待下轮检测", seconds=interval)
            sleep_with_heartbeat(interval, "等待下轮检测")
    finally:
        release_lock()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("用户手动停止")
    except AuthRequired as exc:
        log("授权需要处理，程序已停止", error=str(exc))
        write_crash_log("授权需要处理", exc)
        print("")
        print("巨量授权已失效。请双击：重新授权并写入.bat")
        print("授权写入成功后，再重新启动监控。")
        raise SystemExit(3)
    except Exception as exc:
        log("程序异常退出", error=str(exc))
        write_crash_log("程序异常退出", exc)
        raise
