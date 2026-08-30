import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from config_validation import validate_monitor_config


def account(**overrides):
    result = {
        "id": "main_01",
        "name": "主体一",
        "enabled": True,
        "advertiser_ids": ["1869328450104332"],
        "chrome_debug_port": 9401,
        "app_id": "app-id",
        "app_secret": "app-secret",
        "redirect_uri": "https://example.test/callback",
    }
    result.update(overrides)
    return result


class ConfigValidationTests(unittest.TestCase):
    def test_requires_a_complete_enabled_account(self):
        errors = validate_monitor_config({"main_accounts": [account(app_secret="", redirect_uri="")]})

        self.assertTrue(any("App Secret" in error for error in errors))
        self.assertTrue(any("回调地址" in error for error in errors))

    def test_rejects_placeholder_and_duplicate_account_settings(self):
        config = {
            "main_accounts": [
                account(app_id="填写App ID"),
                account(id="main_02", name="主体二"),
            ]
        }

        errors = validate_monitor_config(config)

        self.assertTrue(any("缺少千川 App ID" in error for error in errors))
        self.assertTrue(any("投放账户 ID 重复" in error for error in errors))
        self.assertTrue(any("浏览器调试端口重复" in error for error in errors))

    def test_accepts_complete_unique_accounts(self):
        config = {
            "main_accounts": [
                account(),
                account(
                    id="main_02",
                    name="主体二",
                    advertiser_ids=["1868328728432327"],
                    chrome_debug_port=9402,
                ),
            ]
        }

        self.assertEqual(validate_monitor_config(config), [])
