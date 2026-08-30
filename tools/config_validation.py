"""Shared validation for account settings before monitoring starts."""

import re


REQUIRED_ACCOUNT_FIELDS = (
    ("app_id", "千川 App ID"),
    ("app_secret", "千川 App Secret"),
    ("redirect_uri", "授权回调地址"),
)


def enabled_main_accounts(config):
    return [
        account for account in (config.get("main_accounts") or [])
        if isinstance(account, dict) and account.get("enabled") is not False
    ]


def _text(value):
    return str(value or "").strip()


def _advertiser_ids(value):
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value if _text(item)]
    return [item for item in re.split(r"[\s,，;；]+", _text(value)) if item]


def validate_monitor_config(config):
    """Return user-facing errors without reading files or calling an API."""
    errors = []
    accounts = enabled_main_accounts(config)
    if not accounts:
        return ["至少需要一个已启用的主账户。"]

    ports = {}
    advertisers = {}
    for index, account in enumerate(accounts, start=1):
        account_id = _text(account.get("id")) or f"main_{index:02d}"
        name = _text(account.get("name")) or account_id
        ids = _advertiser_ids(account.get("advertiser_ids") or config.get("advertiser_ids"))
        if not ids:
            errors.append(f"{name}：缺少投放账户 ID。")
        for advertiser_id in ids:
            if not advertiser_id.isdigit() or not 10 <= len(advertiser_id) <= 30:
                errors.append(f"{name}：投放账户 ID 格式不正确：{advertiser_id}")
            elif advertiser_id in advertisers:
                errors.append(f"投放账户 ID 重复：{advertiser_id}（{advertisers[advertiser_id]} 和 {name}）。")
            else:
                advertisers[advertiser_id] = name

        for key, label in REQUIRED_ACCOUNT_FIELDS:
            value = _text(account.get(key) or config.get(key))
            if not value or value.startswith("填写"):
                errors.append(f"{name}：缺少{label}。")

        try:
            port = int(account.get("chrome_debug_port") or (9221 + index))
        except (TypeError, ValueError):
            errors.append(f"{name}：浏览器调试端口不正确。")
            continue
        if port in ports:
            errors.append(f"浏览器调试端口重复：{port}（{ports[port]} 和 {name}）。")
        else:
            ports[port] = name
    return errors
