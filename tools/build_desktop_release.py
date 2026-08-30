"""Build a standalone no-console Windows desktop release with PyInstaller."""

import re
import shutil
import subprocess
import sys
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


def main():
    version = app_version()
    target = RELEASES_DIR / f"{APP_NAME}-v{version}"
    if target.exists():
        raise RuntimeError(f"Release output already exists. Choose a new APP_VERSION or remove it explicitly: {target}")

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
    (target / "使用说明.txt").write_text(
        "双击 自动关推广.exe 进入管理界面。\n"
        "首次使用请先在“账户配置”填写投放账户 ID、千川 App ID、App Secret 和授权回调地址，再完成登录和授权。\n"
        "data 文件夹会在首次运行时自动创建；不要覆盖已有 data 文件夹。\n",
        encoding="utf-8",
    )
    print(f"Release created: {target}")
    print("This folder contains the no-console EXE. Keep its data folder with the user installation.")


if __name__ == "__main__":
    main()
