import os
import re
from pathlib import Path


ROOT = Path(os.environ.get("OCEANENGINE_ROOT") or Path(__file__).resolve().parent)
ACCOUNT_INFO_DIR = ROOT / "账号接口信息"
TXT_DIR = ACCOUNT_INFO_DIR / "主账户模板"


def _value_after_colon(line):
    if "：" in line:
        return line.split("：", 1)[1].strip()
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return ""


def _is_enabled(text):
    value = text.strip().lower()
    return value in {"是", "yes", "y", "true", "1", "启用", "開啟", "开启"}


def _id_from_file(path):
    match = re.search(r"(\d+)", path.stem)
    if match:
        return f"main_{int(match.group(1)):02d}"
    safe = re.sub(r"\W+", "_", path.stem, flags=re.UNICODE).strip("_")
    return safe or path.stem


def _read_text(path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def parse_account_file(path):
    text = _read_text(path)
    account = {
        "id": _id_from_file(path),
        "name": path.stem,
        "enabled": False,
        "advertiser_ids": [],
        "chrome_debug_port": None,
        "chrome_profile_dir": None,
        "token_file": None,
        "app_id": None,
        "app_secret": None,
        "redirect_uri": None,
        "auth_code": None,
        "callback_url": None,
        "uid": None,
        "state": None,
        "allow_close": True,
        "source_file": str(path),
    }
    ids = []
    in_advertiser_block = False
    section_stoppers = (
        "授权信息",
        "是否已用当前巨量应用授权",
        "授权完整回调链接",
        "auth_code",
        "uid",
        "state",
        "App ID",
        "Secret",
        "Redirect URL",
        "需要监控",
        "是否允许自动关闭",
        "浏览器信息",
        "chrome_debug_port",
        "chrome_profile_dir",
        "token_file",
        "所属主体",
        "备注",
        "是否已在巨量应用",
        "App ID",
        "Secret",
        "Redirect URL",
        "说明",
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(line.startswith(prefix) for prefix in section_stoppers):
            in_advertiser_block = False
        if line.startswith("主账户编号"):
            account["id"] = _value_after_colon(line) or account["id"]
        elif line.startswith("主账户名称") or line.startswith("账号名称"):
            account["name"] = _value_after_colon(line) or account["name"]
        elif line.startswith("是否启用") or line.startswith("需要监控"):
            account["enabled"] = _is_enabled(_value_after_colon(line))
        elif line.startswith("是否允许自动关闭"):
            account["allow_close"] = _is_enabled(_value_after_colon(line))
        elif line.startswith("chrome_debug_port"):
            value = _value_after_colon(line)
            if value.isdigit():
                account["chrome_debug_port"] = int(value)
        elif line.startswith("chrome_profile_dir"):
            account["chrome_profile_dir"] = _value_after_colon(line) or None
        elif line.startswith("token_file"):
            account["token_file"] = _value_after_colon(line) or None
        elif line.startswith("授权完整回调链接"):
            account["callback_url"] = _value_after_colon(line) or None
        elif line.startswith("auth_code"):
            account["auth_code"] = _value_after_colon(line) or None
        elif line.startswith("uid"):
            account["uid"] = _value_after_colon(line) or None
        elif line.startswith("state"):
            account["state"] = _value_after_colon(line) or None
        elif line.startswith("App ID"):
            account["app_id"] = _value_after_colon(line) or None
        elif line.startswith("Secret"):
            account["app_secret"] = _value_after_colon(line) or None
        elif line.startswith("Redirect URL"):
            account["redirect_uri"] = _value_after_colon(line) or None
        elif "advertiser_id" in line or "投放账户ID" in line or "子账户" in line:
            in_advertiser_block = True
            ids.extend(re.findall(r"\b\d{10,30}\b", _value_after_colon(line)))
        elif in_advertiser_block:
            ids.extend(re.findall(r"\b\d{10,30}\b", line))
    seen = set()
    account["advertiser_ids"] = [item for item in ids if not (item in seen or seen.add(item))]
    return account


def load_text_accounts():
    paths = []
    if ACCOUNT_INFO_DIR.exists():
        paths.extend(sorted(ACCOUNT_INFO_DIR.glob("账号*.txt")))
    if TXT_DIR.exists():
        paths.extend(sorted(TXT_DIR.glob("主账户*.txt")))
    if not paths:
        return []
    accounts = []
    seen_ids = set()
    for path in paths:
        account = parse_account_file(path)
        if account["id"] in seen_ids:
            continue
        if account["enabled"] and account["advertiser_ids"]:
            accounts.append(account)
            seen_ids.add(account["id"])
    return accounts


def normalize_main_accounts(config):
    text_accounts = load_text_accounts()
    config_accounts = list(config.get("main_accounts") or [])
    # The desktop application's saved account list wins over old text files.
    # Text files remain authoritative only after the legacy import is used.
    text_accounts_are_authoritative = (
        config.get("account_source") == "text_files"
        and (ACCOUNT_INFO_DIR.exists() or TXT_DIR.exists())
    )
    if text_accounts_are_authoritative:
        config_by_id = {
            str(account.get("id") or f"main_{index:02d}"): account
            for index, account in enumerate(config_accounts, start=1)
            if isinstance(account, dict)
        }
        source_accounts = []
        fields_from_text = (
            "name", "enabled", "advertiser_ids", "chrome_debug_port",
            "chrome_profile_dir", "token_file", "app_id", "app_secret",
            "redirect_uri", "allow_close", "source_file",
        )
        for index, text_account in enumerate(text_accounts, start=1):
            account_id = str(text_account.get("id") or f"main_{index:02d}")
            merged = dict(config_by_id.get(account_id) or {})
            for field in fields_from_text:
                value = text_account.get(field)
                if value not in (None, "", []):
                    merged[field] = value
            merged["id"] = account_id
            source_accounts.append(merged)
    else:
        source_accounts = config_accounts
    if not source_accounts:
        if text_accounts_are_authoritative:
            return []
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
    existing_by_id = {}
    for existing_index, existing_account in enumerate(config.get("main_accounts") or [], start=1):
        if not isinstance(existing_account, dict):
            continue
        existing_id = str(existing_account.get("id") or f"main_{existing_index:02d}")
        existing_by_id[existing_id] = existing_account
    for index, account in enumerate(source_accounts, start=1):
        if not account or account.get("enabled") is False:
            continue
        advertisers = [str(x).strip() for x in account.get("advertiser_ids", []) if str(x).strip()]
        if not advertisers:
            continue
        account_id = str(account.get("id") or f"main_{index:02d}")
        old = existing_by_id.get(account_id, {})
        port = int(account.get("chrome_debug_port") or old.get("chrome_debug_port") or (9300 + index))
        if port in used_ports:
            raise RuntimeError(f"主账户端口重复: {port}")
        used_ports.add(port)
        normalized.append({
            "id": account_id,
            "name": str(account.get("name") or account_id),
            "enabled": True,
            "advertiser_ids": advertisers,
            "chrome_debug_port": port,
            "chrome_profile_dir": account.get("chrome_profile_dir") or old.get("chrome_profile_dir") or f"chrome-profiles/{account_id}",
            "token_file": account.get("token_file") or old.get("token_file") or f"tokens/{account_id}.json",
            "app_id": account.get("app_id") or old.get("app_id"),
            "app_secret": account.get("app_secret") or old.get("app_secret"),
            "redirect_uri": account.get("redirect_uri") or old.get("redirect_uri"),
            "allow_close": account.get("allow_close", True),
            "source_file": account.get("source_file"),
        })
    return normalized


def split_accounts_for_parallel_browsers(config, accounts):
    """Use one dedicated Chrome profile and port per advertiser when enabled."""
    if not config.get("one_browser_per_advertiser", False):
        return accounts

    base_port = int(config.get("per_advertiser_port_base", 9400))
    workers = []
    index = 0
    for account in accounts:
        for advertiser_id in account.get("advertiser_ids") or []:
            index += 1
            worker = dict(account)
            worker["id"] = f"{account['id']}__{advertiser_id}"
            worker["name"] = f"{account['name']} / {advertiser_id}"
            worker["advertiser_ids"] = [str(advertiser_id)]
            worker["chrome_debug_port"] = base_port + index
            worker["chrome_profile_dir"] = f"chrome-profiles/advertiser_{advertiser_id}"
            worker["parent_main_account_id"] = account["id"]
            workers.append(worker)
    return workers
