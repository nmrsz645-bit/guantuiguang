import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import build_desktop_release as builder
from tools import publish_oss_release as publisher
from tools.verify_release import verify
from tools.update_client import EXE_NAME, PRODUCT, package_url, digest


def release_fixture(directory):
    target = directory / "自动关推广-v1.3.0"
    app = target / "app"
    app.mkdir(parents=True)
    (app / EXE_NAME).write_bytes(b"test app")
    (app / "version.json").write_text(json.dumps({"productId": PRODUCT, "version": "1.3.0", "layout": "app-v1", "runtime_data": "data"}), encoding="utf-8")
    for name in ("Start-App.cmd", "Update-Guantuiguang.exe", "README.md", "HANDOFF.md", "使用说明.txt"):
        (target / name).write_bytes(b"test public file")
    (target / "config.example.json").write_text(json.dumps({"main_accounts": [{"enabled": False, "app_secret": "填写App Secret"}]}), encoding="utf-8")
    builder.write_sha256_sums(target)
    archive = directory / "guantuiguang-1.3.0-windows-x64.zip"
    builder.create_release_archive(target, archive)
    value = {"productId": PRODUCT, "version": "1.3.0", "url": package_url("1.3.0"), "sha256": digest(archive)}
    manifest = directory / "guantuiguang-1.3.0-latest.json"
    site = directory / "guantuiguang-1.3.0-latest.js"
    manifest.write_text(json.dumps(value), encoding="utf-8")
    site.write_text("window.GUANTUIGUANG_LATEST = " + json.dumps({"productId": PRODUCT, "version": "1.3.0", "sha256": value["sha256"], "fullPackageUrl": value["url"]}) + ";", encoding="utf-8")
    return archive, manifest, site


class VerifyReleaseTests(unittest.TestCase):
    def test_exact_full_package_and_dry_run_are_offline(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = release_fixture(root)
            result = verify(*paths)
            self.assertEqual(result["version"], "1.3.0")
            with patch.object(publisher, "get_bucket") as auth:
                plan = publisher.publish(root, "1.3.0", "package", dry_run=True)
                self.assertEqual(plan["objects"], ["packages/guantuiguang/1.3.0/guantuiguang-1.3.0-windows-x64.zip"])
                auth.assert_not_called()

    def test_client_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = release_fixture(Path(temp))
            value = json.loads(paths[1].read_text())
            value["sha256"] = "0" * 64
            paths[1].write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                verify(*paths)

    def test_wrong_website_product_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = release_fixture(Path(temp))
            paths[2].write_text('window.ANOTHER_PRODUCT = {};')
            with self.assertRaises(ValueError):
                verify(*paths)


if __name__ == "__main__":
    unittest.main()
