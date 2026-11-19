import hashlib
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools import update_client as updater


def metadata(version):
    return {"productId": "guantuiguang", "version": version, "layout": "app-v1", "runtime_data": "data"}


def make_app(path, version):
    path.mkdir(parents=True)
    (path / updater.EXE_NAME).write_bytes(b"test exe " + version.encode())
    (path / "version.json").write_text(json.dumps(metadata(version)), encoding="utf-8")


def make_package(path, version="1.3.0", extra=None):
    prefix = f"自动关推广-v{version}/"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(prefix + "app/" + updater.EXE_NAME, b"test candidate")
        archive.writestr(prefix + "app/version.json", json.dumps(metadata(version)))
        archive.writestr(prefix + "Start-App.cmd", b"launcher")
        archive.writestr(prefix + "Update-Guantuiguang.exe", b"updater")
        if extra:
            archive.writestr(prefix + extra, b"private or unsafe")


class UpdateClientTests(unittest.TestCase):
    def test_manifest_accepts_only_product_specific_https_package(self):
        value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": "a" * 64, "notes": "update"}
        self.assertEqual(updater.validate_manifest(value)["version"], "1.3.0")
        for changes in ({"productId": "another-product"}, {"version": "1.3"}, {"sha256": "bad"}, {"url": "https://example.com/program.zip"}, {"url": value["url"] + "?token=bad"}, {"url": value["url"].replace("https:", "http:")}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                updater.validate_manifest(dict(value, **changes))

    def test_semantic_versions_do_not_downgrade(self):
        self.assertGreater(updater.version_tuple("1.10.0"), updater.version_tuple("1.9.9"))
        for value in ("v1.3.0", "1.3.0-beta", "../1.3.0", "1.3"):
            with self.assertRaises(ValueError):
                updater.version_tuple(value)

    def test_extract_only_program_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "package.zip"
            make_package(package)
            app = updater.extract_candidate(package, root / "stage", "1.3.0")
            self.assertEqual(updater.read_version(app)["version"], "1.3.0")
            self.assertEqual({p.name for p in app.iterdir()}, {updater.EXE_NAME, "version.json"})
            self.assertFalse((root / "stage/Start-App.cmd").exists())

    def test_private_state_and_unsafe_archive_paths_are_rejected(self):
        for extra in ("data/config.json", "app/config.json", "app/tokens/private.json", "../escape.exe", "app/../outside.exe", "app\\escape.exe", "app/C:/evil.exe", "app/VERSION.JSON"):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package = root / "bad.zip"
                make_package(package, extra=extra)
                with self.assertRaises(ValueError):
                    updater.extract_candidate(package, root / "stage", "1.3.0")

    def test_symlink_archive_member_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "bad.zip"
            info = zipfile.ZipInfo("自动关推广-v1.3.0/app/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr(info, "../../outside")
            with self.assertRaises(ValueError):
                updater.extract_candidate(package, root / "stage", "1.3.0")

    def test_update_preserves_data_and_previous_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            make_app(root / "app.previous", "1.2.0")
            make_app(root / ".stage/app", "1.3.0")
            data = root / "data/config.json"
            data.parent.mkdir()
            data.write_bytes(b"isolated fixture, not an account")
            updater.install_candidate(root, root / ".stage/app", "1.3.0")
            self.assertEqual(updater.read_version(root / "app")["version"], "1.3.0")
            self.assertEqual(updater.read_version(root / "app.previous")["version"], "1.2.1")
            self.assertEqual(len(list((root / ".update-history").iterdir())), 1)
            self.assertEqual(data.read_bytes(), b"isolated fixture, not an account")

    def test_swap_failure_restores_old_program(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            make_app(root / ".stage/app", "1.3.0")
            with self.assertRaises(OSError):
                updater.install_candidate(root, root / ".stage/app", "1.3.0", inject_failure=True)
            self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")
            self.assertFalse((root / updater.TRANSACTION).exists())

    def test_transaction_recovers_missing_app(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app.previous", "1.2.1")
            (root / updater.TRANSACTION).write_text(json.dumps({"oldVersion": "1.2.1", "newVersion": "1.3.0"}), encoding="utf-8")
            updater.recover_transaction(root)
            self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")

    def test_later_and_network_failure_leave_app_intact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": "a" * 64}
            with patch.object(updater, "fetch_manifest", return_value=value), patch.object(updater, "download_package") as download:
                self.assertEqual(updater.check_and_update(root, choice="later"), "later")
                download.assert_not_called()
            with patch.object(updater, "fetch_manifest", side_effect=OSError("offline")):
                self.assertEqual(updater.check_and_update(root, choice="later"), "fallback")
            self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")

    def test_bad_hash_never_installs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": "a" * 64}
            def download(url, output, **kwargs):
                output.write_bytes(b"incorrect zip")
            with patch.object(updater, "fetch_manifest", return_value=value), patch.object(updater, "download_package", side_effect=download), patch.object(updater, "is_app_running", return_value=False):
                self.assertEqual(updater.check_and_update(root, choice="now"), "fallback")
            self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")

    def test_app_running_prevents_update(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            with patch.object(updater, "is_app_running", return_value=True), patch.object(updater, "fetch_manifest") as fetch:
                self.assertEqual(updater.check_and_update(root, choice="later"), "busy")
                fetch.assert_not_called()

    def test_complete_update_runs_smoke_before_replacing_program(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            package = root / "candidate.zip"
            make_package(package)
            value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": updater.digest(package)}
            def download(url, output, **kwargs):
                output.write_bytes(package.read_bytes())
            def smoke(app, version, work):
                self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")
                self.assertEqual(updater.read_version(app)["version"], "1.3.0")
            with patch.object(updater, "fetch_manifest", return_value=value), patch.object(updater, "download_package", side_effect=download), patch.object(updater, "smoke_candidate", side_effect=smoke) as check, patch.object(updater, "is_app_running", return_value=False):
                self.assertEqual(updater.check_and_update(root, choice="now"), "updated")
                check.assert_called_once()
            self.assertEqual(updater.read_version(root / "app")["version"], "1.3.0")
            self.assertEqual(updater.read_version(root / "app.previous")["version"], "1.2.1")

    def test_failed_smoke_retains_old_app(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.2.1")
            package = root / "candidate.zip"
            make_package(package)
            value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": updater.digest(package)}
            def download(url, output, **kwargs):
                output.write_bytes(package.read_bytes())
            with patch.object(updater, "fetch_manifest", return_value=value), patch.object(updater, "download_package", side_effect=download), patch.object(updater, "smoke_candidate", side_effect=ValueError("failed dependency check")), patch.object(updater, "is_app_running", return_value=False):
                self.assertEqual(updater.check_and_update(root, choice="now"), "fallback")
            self.assertEqual(updater.read_version(root / "app")["version"], "1.2.1")

    def test_same_version_never_downloads(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            make_app(root / "app", "1.3.0")
            value = {"productId": "guantuiguang", "version": "1.3.0", "url": updater.package_url("1.3.0"), "sha256": "a" * 64}
            with patch.object(updater, "fetch_manifest", return_value=value), patch.object(updater, "download_package") as download, patch.object(updater, "is_app_running", return_value=False):
                self.assertEqual(updater.check_and_update(root, choice="now"), "current")
                download.assert_not_called()

    def test_package_metadata_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "candidate.zip"
            make_package(package, "1.2.1")
            with self.assertRaises(ValueError):
                updater.extract_candidate(package, root / "stage", "1.3.0")

    def test_update_lock_prevents_second_installer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with updater.update_lock(root):
                with self.assertRaises((OSError, BlockingIOError)):
                    with updater.update_lock(root):
                        self.fail("Second updater acquired the installation lock")


if __name__ == "__main__":
    unittest.main()
