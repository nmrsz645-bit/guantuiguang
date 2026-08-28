import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / "自动关推广"


def remove_path(path):
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def main():
    print("Preparing portable close-promotion package...")
    remove_path(AD_DIR / "data" / "monitor.lock")
    for cache in AD_DIR.rglob("__pycache__"):
        remove_path(cache)
    for folder in [
        ROOT / "rizhi",
        AD_DIR / "data",
        AD_DIR / "rizhi",
        AD_DIR / "tokens",
        AD_DIR / "账号接口信息",
    ]:
        folder.mkdir(parents=True, exist_ok=True)
    print("Cleaned lock files and Python cache.")
    print("API tokens and account text files were kept.")
    print(f"Package root: {ROOT}")


if __name__ == "__main__":
    main()
