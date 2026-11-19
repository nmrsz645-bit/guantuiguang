"""Exercise the real release updater on loopback with an immutable old EXE.

No monitor, auth, account API, or production manifest is started or modified.
The 1.2.1 binary is placed in an isolated app-v1 protocol fixture: this is not
a claim that an unmodified 1.2.1 installation already has an updater.
"""

import argparse
import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
import zipfile
from pathlib import Path

try:
    from tools import update_client as update
except ModuleNotFoundError:
    import update_client as update


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(package, legacy, report):
    package = Path(package).resolve()
    legacy = Path(legacy).resolve()
    if update.digest(legacy) != "f31d62561c653c70fe0394ee2ed172d660bc794790475e45360fd58954e78396":
        raise ValueError("Old public ZIP does not match the immutable 1.2.1 release")
    root = Path(tempfile.mkdtemp(prefix="guantuiguang-update-smoke-"))
    public = root / "http"
    public.mkdir()
    shutil.copy2(package, public / "full.zip")
    with zipfile.ZipFile(package) as archive:
        prefix = next(name[:-len("app/version.json")] for name in archive.namelist() if name.endswith("app/version.json"))
        version = json.loads(archive.read(prefix + "app/version.json"))["version"]
        helper = root / "Update-Guantuiguang.exe"
        helper.write_bytes(archive.read(prefix + "Update-Guantuiguang.exe"))
        candidate_exe = archive.read(prefix + "app/" + update.EXE_NAME)
    with zipfile.ZipFile(legacy) as archive:
        old_exe = archive.read(next(name for name in archive.namelist() if name.endswith("/" + update.EXE_NAME)))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(public)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    results = []
    def prepare(name):
        install = root / name
        (install / "app").mkdir(parents=True)
        (install / "app" / update.EXE_NAME).write_bytes(old_exe)
        (install / "app/version.json").write_text(json.dumps({"productId": "guantuiguang", "version": "1.2.1", "layout": "app-v1", "runtime_data": "data"}), encoding="utf-8")
        (install / "data/tokens").mkdir(parents=True)
        (install / "data/chrome-profiles").mkdir()
        (install / "data/config.json").write_bytes(b"isolated preservation fixture; no account data")
        (install / "data/tokens/fixture.txt").write_bytes(b"no token")
        (install / "data/chrome-profiles/fixture.txt").write_bytes(b"no login")
        return install
    try:
        for scenario, expected, new in (("upgrade", "updated", True), ("later", "later", False), ("offline", "fallback", False), ("bad-hash", "fallback", False), ("wrong-product", "fallback", False), ("swap-failure", "fallback", False)):
            install = prepare(scenario)
            before = {p.relative_to(install / "data").as_posix(): update.digest(p) for p in (install / "data").rglob("*") if p.is_file()}
            manifest = {"productId": "guantuiguang", "version": version, "url": url + "/full.zip", "sha256": update.digest(package), "notes": "isolated test"}
            if scenario == "bad-hash":
                manifest["sha256"] = "0" * 64
            if scenario == "wrong-product":
                manifest["productId"] = "unrelated"
            (public / "latest.json").write_text(json.dumps(manifest), encoding="utf-8")
            command = [str(helper), "--root", str(install), "--test-mode", "--manifest-url", "http://127.0.0.1:1/unavailable" if scenario == "offline" else url + "/latest.json", "--choice", "later" if scenario == "later" else "now", "--no-launch"]
            if scenario == "swap-failure":
                command.append("--inject-swap-failure")
            completed = subprocess.run(command, cwd=str(install), timeout=120)
            result = json.loads((install / ".last-update-result.json").read_text(encoding="utf-8"))
            after = {p.relative_to(install / "data").as_posix(): update.digest(p) for p in (install / "data").rglob("*") if p.is_file()}
            if completed.returncode or result["result"] != expected or before != after:
                raise ValueError(f"Scenario {scenario} failed: {completed.returncode}, {result}")
            if (install / "app" / update.EXE_NAME).read_bytes() != (candidate_exe if new else old_exe):
                raise ValueError(f"Scenario {scenario} has incorrect retained/updated program")
            if new and (install / "app.previous" / update.EXE_NAME).read_bytes() != old_exe:
                raise ValueError("Old immutable binary backup differs")
            results.append({"scenario": scenario, "result": expected, "privateFixtureHashesUnchanged": True})
        # Construct the actual new GUI briefly in its isolated root; never click/launch workers.
        ui_report = root / "ui-smoke.json"
        gui = root / "upgrade/app" / update.EXE_NAME
        completed = subprocess.run([str(gui), "--ui-smoke-test", "--report", str(ui_report)], timeout=60)
        ui = json.loads(ui_report.read_text(encoding="utf-8"))
        if completed.returncode or ui["worker_started"] is not False or ui["version"] != version:
            raise ValueError("Real GUI smoke failed")
        outcome = {"productId": "guantuiguang", "version": version, "packageSha256": update.digest(package), "realExeScenarios": results, "gui": ui, "businessNetworkCalls": 0, "legacyFixture": "Original 1.2.1 EXE inside isolated app-v1 wrapper; old clients still require first manual full install."}
        Path(report).write_text(json.dumps(outcome, ensure_ascii=False, indent=2), encoding="utf-8")
        return outcome
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--legacy", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.package, args.legacy, args.report), ensure_ascii=False))
