import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "tools" / "build_desktop_release.py"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_desktop_release", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildDesktopReleaseTests(unittest.TestCase):
    def test_release_archive_contains_manifest_and_preserves_release_folder(self):
        builder = load_builder_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            release = root / "自动关推广-v1.2.1"
            release.mkdir()
            (release / "自动关推广.exe").write_bytes(b"desktop binary fixture")
            (release / "README.md").write_text("release notes", encoding="utf-8")
            archive = root / "自动关推广-v1.2.1.zip"

            builder.write_sha256_sums(release)
            builder.create_release_archive(release, archive)

            manifest = (release / "SHA256SUMS.txt").read_text(encoding="utf-8")
            expected_hash = hashlib.sha256(b"desktop binary fixture").hexdigest()
            self.assertIn(f"{expected_hash}  自动关推广.exe", manifest)
            with zipfile.ZipFile(archive) as package:
                self.assertIn("自动关推广-v1.2.1/自动关推广.exe", package.namelist())
                self.assertIn("自动关推广-v1.2.1/SHA256SUMS.txt", package.namelist())


if __name__ == "__main__":
    unittest.main()
