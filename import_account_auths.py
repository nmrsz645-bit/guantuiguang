import runpy
import sys

from import_account_texts import find_real_script


if __name__ == "__main__":
    script = find_real_script()
    sys.path.insert(0, str(script.parent))
    sys.argv = [str(script), *sys.argv[1:]]
    runpy.run_path(str(script), run_name="__main__")
