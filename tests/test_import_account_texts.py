import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "自动关推广"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import import_account_texts


class ImportAccountTextsTests(unittest.TestCase):
    def test_parse_code_accepts_callback_url_and_plain_code(self):
        callback = "https://example.test/callback?state=abc&auth_code=code-123"
        self.assertEqual(import_account_texts.parse_code(callback), "code-123")
        self.assertEqual(import_account_texts.parse_code(" plain-code "), "plain-code")
        self.assertEqual(import_account_texts.parse_code(""), "")

    def test_accounts_only_preserves_existing_authorization(self):
        account = {"id": "main_01", "name": "新名称", "advertiser_ids": ["1000000000000001"]}
        config = {
            "app_id": "global-app",
            "app_secret": "global-secret",
            "main_accounts": [
                {
                    "id": "main_01",
                    "app_id": "saved-app",
                    "app_secret": "saved-secret",
                    "redirect_uri": "https://saved.test/callback",
                    "chrome_debug_port": 9410,
                    "chrome_profile_dir": "chrome-profiles/saved",
                    "token_file": "tokens/saved.json",
                }
            ],
        }

        result = import_account_texts.account_defaults(
            account, config, 1, preserve_existing_authorization=True
        )

        self.assertEqual(result["app_id"], "saved-app")
        self.assertEqual(result["app_secret"], "saved-secret")
        self.assertEqual(result["chrome_debug_port"], 9410)
        self.assertEqual(result["token_file"], "tokens/saved.json")

    def test_sync_config_disables_accounts_removed_from_text_files(self):
        config = {
            "main_accounts": [
                {"id": "main_01", "name": "旧主体一", "enabled": True},
                {"id": "main_02", "name": "旧主体二", "enabled": True},
            ]
        }
        imported = [
            {
                "id": "main_02",
                "name": "新主体二",
                "chrome_debug_port": 9402,
                "chrome_profile_dir": "chrome-profiles/main_02",
                "token_file": "tokens/main_02.json",
                "advertiser_ids": ["1000000000000002"],
                "app_id": "app-id",
                "app_secret": "app-secret",
                "redirect_uri": "https://example.test/callback",
            }
        ]

        result = import_account_texts.sync_config(config, imported)
        accounts = {item["id"]: item for item in result["main_accounts"]}

        self.assertEqual(result["account_source"], "text_files")
        self.assertFalse(accounts["main_01"]["enabled"])
        self.assertTrue(accounts["main_02"]["enabled"])
        self.assertEqual(result["advertiser_ids"], ["1000000000000002"])

    def test_status_line_reports_result_summary(self):
        line = import_account_texts.status_line(
            {
                "ok": True,
                "id": "main_01",
                "name": "主体一",
                "advertiser_ids": ["1000000000000001"],
                "detail": "账号配置已同步",
            }
        )
        self.assertIn("成功 | main_01 | 主体一", line)
        self.assertIn("子账户 1 个", line)
