import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / "自动关推广"
INSTALLERS = ROOT / "installers"
PACKAGE_DIR = INSTALLERS / "python_packages"


def run(args):
    print("RUN:", " ".join(str(x) for x in args))
    result = subprocess.run([str(x) for x in args], cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_dirs():
    for folder in [
        ROOT / "rizhi",
        ROOT / "logs",
        AD_DIR / "data",
        AD_DIR / "rizhi",
        AD_DIR / "logs",
        AD_DIR / "tokens",
        AD_DIR / "chrome-debug-profile",
        AD_DIR / "chrome-profiles",
        AD_DIR / "login-pages",
        AD_DIR / "账号接口信息",
    ]:
        folder.mkdir(parents=True, exist_ok=True)
    print("OK: required folders created")


def install_packages():
    packages = ["setuptools", "wheel", "requests", "websocket-client", "python-dotenv"]
    run([sys.executable, "-m", "ensurepip", "--upgrade"])
    if PACKAGE_DIR.exists():
        run([sys.executable, "-m", "pip", "install", "--no-index", "--find-links", str(PACKAGE_DIR), *packages])
    else:
        run([sys.executable, "-m", "pip", "install", "--upgrade", *packages])
    run([sys.executable, "-c", "import requests, websocket, dotenv; print('packages OK')"])


def main():
    print("========================================")
    print("OceanEngine Close-Promotion First Install")
    print(f"Root: {ROOT}")
    print("========================================")
    install_packages()
    ensure_dirs()
    run([sys.executable, str(ROOT / "tools" / "check_oceanengine_only.py"), "--allow-unconfigured"])
    print()
    print("Install finished.")
    print("Next:")
    print("1. Double click 自动关推广本地程序.bat and configure accounts and API details.")
    print("2. Double click 打开巨量登录.bat and login dedicated Chrome windows.")
    print("3. Double click 写入巨量授权码.bat or 自动导入巨量账号授权.bat.")
    print("4. Double click 一键自检.bat. It must show Errors: 0.")
    print("5. Double click 启动监控.bat.")


if __name__ == "__main__":
    main()
