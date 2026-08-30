import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1] / "自动关推广"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import main_accounts


class MainAccountsTests(unittest.TestCase):
    def test_parse_account_file_reads_only_advertiser_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account_file = Path(temp_dir) / "账号03.txt"
            account_file.write_text(
                "\n".join(
                    [
                        "主账户编号：main_03",
                        "主账户名称：测试主体",
                        "是否启用：是",
                        "投放账户ID：1869328450104332",
                        "1868328728432327",
                        "1869328450104332",
                        "是否允许自动关闭：否",
                        "chrome_debug_port：9403",
                        "chrome_profile_dir：chrome-profiles/test",
                        "授权信息",
                        "1869999999999999",
                    ]
                ),
                encoding="utf-8",
            )

            account = main_accounts.parse_account_file(account_file)

        self.assertEqual(account["id"], "main_03")
        self.assertEqual(account["name"], "测试主体")
        self.assertTrue(account["enabled"])
        self.assertFalse(account["allow_close"])
        self.assertEqual(account["chrome_debug_port"], 9403)
        self.assertEqual(
            account["advertiser_ids"], ["1869328450104332", "1868328728432327"]
        )

    def test_normalize_uses_saved_accounts_and_skips_disabled_entries(self):
        config = {
            "main_accounts": [
                {
                    "id": "main_01",
                    "name": "可用主体",
                    "enabled": True,
                    "advertiser_ids": ["1000000000000001"],
                },
                {
                    "id": "main_02",
                    "enabled": False,
                    "advertiser_ids": ["1000000000000002"],
                },
            ]
        }

        with patch.object(main_accounts, "load_text_accounts", return_value=[]):
            accounts = main_accounts.normalize_main_accounts(config)

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]["id"], "main_01")
        self.assertEqual(accounts[0]["chrome_debug_port"], 9301)
        self.assertEqual(accounts[0]["token_file"], "tokens/main_01.json")

    def test_normalize_rejects_duplicate_browser_ports(self):
        config = {
            "main_accounts": [
                {"id": "main_01", "advertiser_ids": ["1000000000000001"], "chrome_debug_port": 9401},
                {"id": "main_02", "advertiser_ids": ["1000000000000002"], "chrome_debug_port": 9401},
            ]
        }

        with patch.object(main_accounts, "load_text_accounts", return_value=[]):
            with self.assertRaisesRegex(RuntimeError, "端口重复"):
                main_accounts.normalize_main_accounts(config)

    def test_split_creates_one_browser_worker_per_advertiser(self):
        accounts = [
            {
                "id": "main_01",
                "name": "主体一",
                "advertiser_ids": ["1000000000000001", "1000000000000002"],
            }
        ]

        workers = main_accounts.split_accounts_for_parallel_browsers(
            {"one_browser_per_advertiser": True, "per_advertiser_port_base": 9500},
            accounts,
        )

        self.assertEqual([worker["chrome_debug_port"] for worker in workers], [9501, 9502])
        self.assertEqual(workers[0]["advertiser_ids"], ["1000000000000001"])
        self.assertEqual(workers[1]["parent_main_account_id"], "main_01")
