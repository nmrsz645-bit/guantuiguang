import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLERS = ROOT / "installers"


def run(args):
    return subprocess.run([str(x) for x in args], cwd=str(ROOT), check=False).returncode


def chrome_exists():
    candidates = [
        Path(os.environ.get("ProgramFiles", "")) / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Google/Chrome/Application/chrome.exe",
    ]
    return any(p.exists() for p in candidates)


def install_chrome_if_needed():
    if chrome_exists():
        print("OK: Chrome exists")
        return
    installers = sorted(INSTALLERS.glob("GoogleChrome*.msi"))
    if not installers:
        print("WARN: Chrome installer not found. Please install Chrome manually.")
        return
    print("Installing Chrome...")
    run(["msiexec", "/i", installers[0], "/qn", "/norestart"])


def ensure_initial_config():
    target = ROOT / "自动关推广" / "config.json"
    if target.exists():
        print("OK: Existing local config preserved")
        return False
    example = ROOT / "config.example.json"
    if not example.exists():
        raise RuntimeError(f"Missing default config template: {example}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".tmp")
    shutil.copyfile(example, temp)
    temp.replace(target)
    print("OK: Created local config from config.example.json")
    return True


def main():
    install_chrome_if_needed()
    ensure_initial_config()
    script = ROOT / "tools" / "install_oceanengine_only.py"
    raise SystemExit(run([sys.executable, script]))


if __name__ == "__main__":
    main()
