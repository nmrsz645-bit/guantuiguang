import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def zh(text):
    return text.encode("ascii").decode("unicode_escape")


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / zh(r"\u81ea\u52a8\u5173\u63a8\u5e7f")
CONFIG_FILE = AD_DIR / "config.json"
LOCK_FILE = AD_DIR / "data" / "monitor.lock"
LOG_CANDIDATES = [
    AD_DIR / "rizhi" / "monitor.log",
    ROOT / "rizhi" / "monitor.log",
    AD_DIR / "logs" / "monitor.log",
    ROOT / "logs" / "monitor.log",
]


def read_text(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(read_text(CONFIG_FILE))
    except Exception:
        return {}


def newest_existing(paths):
    existing = [p for p in paths if p.exists()]
    if not existing:
        return paths[0]
    return max(existing, key=lambda p: p.stat().st_mtime)


LOG_FILE = newest_existing(LOG_CANDIDATES)


def is_pid_running(pid):
    if not pid:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    return str(pid) in result.stdout


def tail(path, count):
    if not path.exists():
        return []
    return read_text(path).splitlines()[-count:]


def seconds_ago(dt):
    return max(0, int((datetime.now() - dt).total_seconds()))


def parse_log_time(line):
    match = re.match(r"^\[(.*?)\]", line)
    if not match:
        return ""
    return match.group(1)


def parse_json_payload(line):
    pos = line.find("{")
    if pos < 0:
        return None
    try:
        return json.loads(line[pos:])
    except Exception:
        return None


def extract_rounds(lines):
    rounds = []
    for line in lines:
        if '"summary"' not in line:
            continue
        data = parse_json_payload(line)
        if not isinstance(data, dict):
            continue
        summary = data.get("summary")
        if not isinstance(summary, list):
            continue
        item = {
            "time": parse_log_time(line),
            "rows_seen": 0,
            "qr_ready_count": 0,
            "closed_count": 0,
            "errors": 0,
            "open_count": 0,
            "accounts": 0,
        }
        for account in summary:
            if not isinstance(account, dict):
                continue
            item["accounts"] += 1
            for key in ["rows_seen", "qr_ready_count", "closed_count", "errors", "open_count"]:
                try:
                    item[key] += int(account.get(key) or 0)
                except Exception:
                    pass
        rounds.append(item)
    return rounds


def find_latest_error_lines(lines):
    keywords = [
        "error",
        "exception",
        "traceback",
        "access_token",
        "refresh_token",
        zh(r"\u5931\u8d25"),
        zh(r"\u9519\u8bef"),
        zh(r"\u672a\u767b\u5f55"),
        zh(r"\u5931\u6548"),
        zh(r"\u8bfb\u53d6\u5355\u5143\u5217\u8868\u5931\u8d25"),
    ]
    result = []
    for line in lines:
        low = line.lower()
        if any(k.lower() in low for k in keywords):
            result.append(line)
    return result[-8:]


def get_running_pid():
    if not LOCK_FILE.exists():
        return None
    try:
        lock = json.loads(read_text(LOCK_FILE))
        return int(lock.get("pid") or 0)
    except Exception:
        return None


def token_files(config):
    files = []
    token_file = config.get("token_file")
    if isinstance(token_file, str) and token_file:
        files.append(AD_DIR / token_file)
    for account in config.get("main_accounts") or []:
        if not isinstance(account, dict):
            continue
        token_file = account.get("token_file")
        if isinstance(token_file, str) and token_file:
            files.append(AD_DIR / token_file)
    return sorted(set(files))


def enabled_accounts(config):
    try:
        if str(AD_DIR) not in sys.path:
            sys.path.insert(0, str(AD_DIR))
        from main_accounts import normalize_main_accounts
        return normalize_main_accounts(config)
    except Exception:
        pass
    accounts = []
    for account in config.get("main_accounts") or []:
        if isinstance(account, dict) and account.get("enabled"):
            accounts.append(account)
    return accounts


def interface_status(config, recent_errors):
    if not config:
        return zh(r"\u5f02\u5e38\uff1a\u914d\u7f6e\u6587\u4ef6\u8bfb\u53d6\u5931\u8d25")
    tokens = token_files(config)
    if not any(p.exists() for p in tokens):
        return zh(r"\u5f02\u5e38\uff1a\u6ca1\u6709\u627e\u5230 token \u6587\u4ef6")
    joined = "\n".join(recent_errors).lower()
    bad_words = ["access_token", "refresh_token", zh(r"\u672a\u767b\u5f55"), zh(r"\u5931\u6548"), zh(r"\u8bfb\u53d6\u5355\u5143\u5217\u8868\u5931\u8d25")]
    if any(word.lower() in joined for word in bad_words):
        return zh(r"\u7591\u4f3c\u5f02\u5e38\uff1a\u6700\u8fd1\u65e5\u5fd7\u51fa\u73b0\u6388\u6743\u6216\u63a5\u53e3\u9519\u8bef")
    return zh(r"\u6b63\u5e38\uff1a\u672a\u53d1\u73b0\u6388\u6743\u6216\u63a5\u53e3\u5f02\u5e38")


def format_round(label, item):
    if not item:
        return [
            f"{label}: {zh(r'\u6682\u65e0\u8bb0\u5f55')}",
            f"  {zh(r'\u626b\u63cf\u4e86\u591a\u5c11\u672c')}: 0",
            f"  {zh(r'\u51fa\u4e86\u51e0\u4e2a\u4e8c\u7ef4\u7801')}: 0",
            f"  {zh(r'\u5173\u95ed\u4e86\u51e0\u4e2a\u4e8c\u7ef4\u7801')}: 0",
        ]
    return [
        f"{label}: {item['time'] or zh(r'\u672a\u77e5')}",
        f"  {zh(r'\u626b\u63cf\u4e86\u591a\u5c11\u672c')}: {item['rows_seen']}",
        f"  {zh(r'\u51fa\u4e86\u51e0\u4e2a\u4e8c\u7ef4\u7801')}: {item['qr_ready_count']}",
        f"  {zh(r'\u5173\u95ed\u4e86\u51e0\u4e2a\u4e8c\u7ef4\u7801')}: {item['closed_count']}",
        f"  {zh(r'\u6253\u5f00\u72b6\u6001\u5355\u5143')}: {item['open_count']} | {zh(r'\u9519\u8bef')}: {item['errors']} | {zh(r'\u8d26\u6237\u6570')}: {item['accounts']}",
    ]


def main():
    config = load_config()
    lines = tail(LOG_FILE, 1000)
    rounds = extract_rounds(lines)
    recent_errors = find_latest_error_lines(lines)

    pid = get_running_pid()
    running = bool(pid and is_pid_running(pid))
    status_text = zh(r"\u6b63\u5e38\u8fd0\u884c") if running else zh(r"\u672a\u8fd0\u884c")

    print(f"{zh(r'\u5f53\u524d\u65f6\u95f4')}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{zh(r'\u6839\u76ee\u5f55')}: {ROOT}")
    print("=" * 52)
    print(f"{zh(r'\u72b6\u6001\u662f\u5426\u6b63\u5e38')}: {status_text}" + (f" | PID: {pid}" if pid else ""))
    print(f"{zh(r'\u63a5\u53e3\u662f\u5426\u6b63\u5e38')}: {interface_status(config, recent_errors)}")

    if LOG_FILE.exists():
        last = datetime.fromtimestamp(LOG_FILE.stat().st_mtime)
        print(f"{zh(r'\u6700\u540e\u65e5\u5fd7\u65f6\u95f4')}: {last.strftime('%Y-%m-%d %H:%M:%S')} ({seconds_ago(last)} {zh(r'\u79d2\u524d')})")
        print(f"{zh(r'\u65e5\u5fd7\u6587\u4ef6')}: {LOG_FILE}")
    else:
        print(f"{zh(r'\u65e5\u5fd7\u6587\u4ef6')}: {zh(r'\u672a\u627e\u5230')}")

    accounts = enabled_accounts(config)
    max_rows = int(config.get("page_size") or 0) * int(config.get("max_pages") or 0)
    interval = config.get("check_interval_seconds", "")
    print()
    print(zh(r"\u3010\u914d\u7f6e\u3011"))
    parallel = max(1, int(config.get("parallel_browser_count", 3)))
    independent = bool(config.get("one_browser_per_advertiser"))
    advertiser_count = sum(len(account.get("advertiser_ids") or []) for account in accounts)
    print(f"{zh(r'\u68c0\u6d4b\u95f4\u9694')}: {interval} {zh(r'\u79d2')} | {zh(r'\u6bcf\u4e2a\u8d26\u6237\u6700\u591a\u68c0\u67e5')}: {max_rows} {zh(r'\u6761')} | {zh(r'\u5df2\u542f\u7528\u4e3b\u8d26\u6237')}: {len(accounts)} | {zh(r'\u5df2\u542f\u7528\u6295\u653e\u8d26\u6237')}: {advertiser_count}")
    print(f"{zh(r'\u6bcf\u4e2a\u6295\u653e\u8d26\u6237\u72ec\u7acb\u6d4f\u89c8\u5668')}: {zh(r'\u662f') if independent else zh(r'\u5426')} | {zh(r'\u540c\u65f6\u68c0\u6d4b\u8d26\u6237\u6570')}: {parallel}")
    if accounts:
        for account in accounts:
            advertisers = account.get("advertiser_ids") or []
            if isinstance(advertisers, dict):
                advertisers = []
            ids = ", ".join(str(item) for item in advertisers) or zh(r'\u65e0')
            print(f"- {account.get('id', '')}: {len(advertisers)} {zh(r'\u4e2a\u6295\u653e\u8d26\u6237')} [{ids}] | {zh(r'\u7aef\u53e3')} {account.get('chrome_debug_port', '')}")

    print()
    print(zh(r"\u3010\u626b\u63cf\u7edf\u8ba1\u3011"))
    previous_round = rounds[-2] if len(rounds) >= 2 else None
    current_round = rounds[-1] if rounds else None
    for line in format_round(zh(r"\u4e0a\u6b21\u626b\u63cf\u65f6\u95f4"), previous_round):
        print(line)
    for line in format_round(zh(r"\u8fd9\u6b21\u626b\u63cf\u65f6\u95f4"), current_round):
        print(line)

    print()
    print(zh(r"\u3010\u6700\u8fd1\u9519\u8bef\u3011"))
    if recent_errors:
        for line in recent_errors:
            print(line)
    else:
        print(zh(r"\u6700\u8fd1\u65e5\u5fd7\u672a\u53d1\u73b0\u660e\u663e\u9519\u8bef\u3002"))

    print()
    print(zh(r"\u8bf4\u660e\uff1a\u5173\u95ed\u672c\u5730\u7a97\u53e3\u4f1a\u505c\u6b62\u76d1\u63a7\u8fdb\u7a0b\u548c\u5df2\u914d\u7f6e\u7aef\u53e3\u7684\u4e13\u7528 Chrome\u3002"))


if __name__ == "__main__":
    main()
