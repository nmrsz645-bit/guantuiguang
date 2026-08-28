import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SELF = Path(__file__).resolve()


def find_real_script():
    for path in ROOT.rglob("open_main_account_logins.py"):
        path = path.resolve()
        if path != SELF and path.is_file():
            return path
    raise FileNotFoundError("Cannot find inner open_main_account_logins.py")


if __name__ == "__main__":
    script = find_real_script()
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script), *sys.argv[1:]]
    runpy.run_path(str(script), run_name="__main__")
