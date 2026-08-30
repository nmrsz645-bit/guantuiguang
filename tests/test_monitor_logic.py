import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1] / "自动关推广"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import monitor_oceanengine_units as monitor


class MonitorLogicTests(unittest.TestCase):
    def test_refresh_invalid_detection(self):
        self.assertTrue(monitor.is_refresh_invalid({"code": 40103}))
        self.assertTrue(monitor.is_refresh_invalid({"message": "refresh_token 已失效，请重新授权"}))
        self.assertFalse(monitor.is_refresh_invalid({"code": 0, "message": "ok"}))

    def test_unit_open_status(self):
        self.assertTrue(monitor.is_unit_open({"ad_opt_status": 0}))
        self.assertTrue(monitor.is_unit_open({"promotion_status_name": "投放中"}))
        self.assertFalse(monitor.is_unit_open({"promotion_status_name": "已暂停"}))
        self.assertFalse(monitor.is_unit_open({"promotion_status_name": "审核中"}))

    def test_response_helpers_handle_nested_and_invalid_data(self):
        self.assertEqual(monitor.response_data_dict({"data": {"items": []}}), {"items": []})
        self.assertEqual(monitor.response_data_dict({"data": []}), {})
        self.assertEqual(monitor.preview_payload_dict({"data": {"data": {"url": "x"}}}), {"url": "x"})
        self.assertEqual(monitor.preview_payload_dict({"data": {"url": "x"}}), {"url": "x"})

    def test_account_config_forces_dry_run_when_closing_is_disabled(self):
        config = {"dry_run": False, "app_id": "global"}
        account = {
            "id": "main_01",
            "name": "主体一",
            "chrome_debug_port": 9401,
            "chrome_profile_dir": "chrome-profiles/main_01",
            "token_file": "tokens/main_01.json",
            "allow_close": False,
        }

        result = monitor.account_config(config, account)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["main_account_id"], "main_01")
        self.assertEqual(result["chrome_debug_port"], 9401)

    def test_log_retention_is_72_hours_and_only_touches_temp_logs(self):
        self.assertEqual(monitor.LOG_RETENTION_HOURS, 72)
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            old_file = log_dir / "old.log"
            old_file.write_text("old", encoding="utf-8")
            old_time = time.time() - 73 * 60 * 60
            os.utime(old_file, (old_time, old_time))

            event_file = log_dir / "events.jsonl"
            old_event = {"time": (datetime.now() - timedelta(hours=73)).isoformat(), "message": "old"}
            fresh_event = {"time": datetime.now().isoformat(), "message": "fresh"}
            event_file.write_text(
                json.dumps(old_event) + "\n" + json.dumps(fresh_event) + "\n",
                encoding="utf-8",
            )

            with patch.object(monitor, "LOG_DIR", log_dir), patch.object(monitor, "_last_log_cleanup", 0.0):
                monitor.cleanup_old_logs(force=True)

            self.assertFalse(old_file.exists())
            self.assertEqual(event_file.read_text(encoding="utf-8").count("fresh"), 1)
            self.assertNotIn("old", event_file.read_text(encoding="utf-8"))
