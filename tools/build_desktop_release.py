"""Build a standalone no-console Windows desktop release with PyInstaller."""

import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "tools" / "desktop_oceanengine_app.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
RELEASES_DIR = ROOT / "release"
APP_NAME = "自动关推广"
HIDDEN_IMPORTS = (
    "requests",
    "websocket",
    "dotenv",
    "monitor_oceanengine_units",
    "open_main_account_logins",
    "import_account_texts",
    "write_auth_code",
    "main_accounts",
)


def app_version():
    text = ENTRY.read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise RuntimeError("Cannot determine APP_VERSION from desktop_oceanengine_app.py")
    return match.group(1)


def run(args):
    print("RUN:", subprocess.list2cmdline([str(item) for item in args]))
    subprocess.run(args, cwd=ROOT, check=True)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_sums(release_dir):
    """Write hashes for every shipped file, excluding the manifest itself."""
    manifest = release_dir / "SHA256SUMS.txt"
    files = sorted(
        (path for path in release_dir.rglob("*") if path.is_file() and path != manifest),
        key=lambda path: path.relative_to(release_dir).as_posix(),
    )
    lines = [
        f"{sha256_file(path)}  {path.relative_to(release_dir).as_posix()}"
        for path in files
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def create_release_archive(release_dir, archive_path):
    """Create a non-overwriting ZIP with the release folder as its root."""
    if archive_path.exists():
        raise RuntimeError(f"Release archive already exists and will not be overwritten: {archive_path}")
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(release_dir.rglob("*"), key=lambda item: item.as_posix()):
            if path.is_file():
                archive.write(path, path.relative_to(release_dir.parent).as_posix())
    return archive_path


def main():
    version = app_version()
    target = RELEASES_DIR / f"{APP_NAME}-v{version}"
    archive = RELEASES_DIR / f"{APP_NAME}-v{version}.zip"
    if target.exists():
        raise RuntimeError(f"Release output already exists. Choose a new APP_VERSION or remove it explicitly: {target}")
    if archive.exists():
        raise RuntimeError(f"Release archive already exists. Choose a new APP_VERSION or remove it explicitly: {archive}")

    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onefile",
        "--name", APP_NAME, "--distpath", str(DIST_DIR), "--workpath", str(BUILD_DIR),
        "--specpath", str(BUILD_DIR), "--paths", str(ROOT / "tools"), "--paths", str(ROOT / "自动关推广"),
    ]
    for module in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", module])
    command.append(str(ENTRY))
    run(command)

    executable = DIST_DIR / f"{APP_NAME}.exe"
    if not executable.exists():
        raise RuntimeError(f"PyInstaller did not produce the expected executable: {executable}")
    target.mkdir(parents=True)
    shutil.copy2(executable, target / executable.name)
    shutil.copy2(ROOT / "config.example.json", target / "config.example.json")
    shutil.copy2(ROOT / "README.md", target / "README.md")
    shutil.copy2(ROOT / "HANDOFF.md", target / "HANDOFF.md")
    shutil.copy2(ROOT / "使用说明.txt", target / "使用说明.txt")
    write_sha256_sums(target)
    create_release_archive(target, archive)
    print(f"Release created: {target}")
    print(f"Release archive created: {archive}")
    print(f"Release archive SHA-256: {sha256_file(archive)}")
    print("This folder contains the no-console EXE. Keep its data folder with the user installation.")


if __name__ == "__main__":
    main()
