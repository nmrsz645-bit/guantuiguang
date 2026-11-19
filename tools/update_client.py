"""Opt-in, full-package updater. Mutable account data never enters the app swap."""

import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path

PRODUCT = "guantuiguang"
EXE_NAME = "自动关推广.exe"
ORIGIN = "https://luotuoruanjiangengx.oss-cn-beijing.aliyuncs.com"
MANIFEST_URL = ORIGIN + "/updates/guantuiguang/latest.json"
TRANSACTION = ".update-transaction.json"
MAX_PACKAGE_BYTES = 256 * 1024 * 1024
ROOT_FILES = {"Start-App.cmd", "Update-Guantuiguang.exe", "README.md", "HANDOFF.md", "使用说明.txt", "config.example.json", "SHA256SUMS.txt"}
APP_FILES = {EXE_NAME, "version.json"}


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,6}\.\d{1,6}\.\d{1,6}", value):
        raise ValueError("Invalid three-part version")
    return tuple(map(int, value.split(".")))


def package_url(version):
    version_tuple(version)
    return f"{ORIGIN}/packages/{PRODUCT}/{version}/{PRODUCT}-{version}-windows-x64.zip"


def plain_path(path):
    path = Path(os.path.abspath(path))
    for parent in (path, *path.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ValueError("Reparse point in installation path")
    return path


def validate_manifest(value, test_mode=False):
    if not isinstance(value, dict) or value.get("productId") != PRODUCT:
        raise ValueError("Manifest product mismatch")
    version_tuple(value.get("version"))
    if not re.fullmatch(r"[a-fA-F0-9]{64}", str(value.get("sha256", ""))):
        raise ValueError("Invalid SHA-256")
    url = value.get("url")
    if test_mode:
        parsed = urllib.parse.urlsplit(str(url))
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Test package must use loopback HTTP")
    elif url != package_url(value["version"]):
        raise ValueError("Untrusted package URL")
    if len(str(value.get("notes", ""))) > 2000:
        raise ValueError("Release notes too long")
    return value


def read_version(app):
    app = plain_path(app)
    value = json.loads(plain_path(app / "version.json").read_text(encoding="utf-8-sig"))
    if value.get("productId") != PRODUCT or value.get("layout") != "app-v1" or value.get("runtime_data") != "data":
        raise ValueError("App metadata contract mismatch")
    version_tuple(value.get("version"))
    if not plain_path(app / EXE_NAME).is_file():
        raise ValueError("App executable missing")
    return value


def write_json(path, value):
    path = plain_path(path)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def log(root, message):
    directory = plain_path(root / "logs")
    directory.mkdir(exist_ok=True)
    with plain_path(directory / "Update-App.log").open("a", encoding="utf-8") as output:
        output.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(message) + "\n")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Update redirects are not allowed")


def response(url, timeout):
    request = urllib.request.Request(url, headers={"User-Agent": "GuantuiguangUpdater/1", "Cache-Control": "no-cache"})
    return urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout)


def fetch_manifest(url=MANIFEST_URL, test_mode=False):
    if test_mode:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Test manifest must use loopback HTTP")
    elif url != MANIFEST_URL:
        raise ValueError("Untrusted manifest URL")
    with response(url, 8) as remote:
        body = remote.read(65537)
    if len(body) > 65536:
        raise ValueError("Manifest too large")
    return validate_manifest(json.loads(body.decode("utf-8-sig")), test_mode)


def download_package(url, output, **kwargs):
    deadline = time.monotonic() + 180
    total = 0
    with response(url, 30) as remote, output.open("xb") as target:
        if int(remote.headers.get("Content-Length", 0)) > MAX_PACKAGE_BYTES:
            raise ValueError("Package too large")
        while True:
            chunk = remote.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_PACKAGE_BYTES or time.monotonic() > deadline:
                raise ValueError("Package download limit exceeded")
            target.write(chunk)


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def extract_candidate(package, stage, version):
    prefix = f"自动关推广-v{version}/"
    seen = set()
    entries = []
    with zipfile.ZipFile(package) as archive:
        infos = archive.infolist()
        if len(infos) > 50 or sum(info.file_size for info in infos) > MAX_PACKAGE_BYTES:
            raise ValueError("Expanded package limit exceeded")
        for info in infos:
            name = info.filename
            if info.is_dir():
                raise ValueError("Explicit ZIP directories are not permitted")
            if not name.startswith(prefix) or "\\" in name or ":" in name:
                raise ValueError("Unsafe archive path")
            relative = name[len(prefix):]
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or relative.casefold() in seen:
                raise ValueError("Symlink or duplicate ZIP entry")
            seen.add(relative.casefold())
            if relative not in ROOT_FILES and relative not in {"app/" + file for file in APP_FILES}:
                raise ValueError("Unexpected file or private data in package")
            entries.append((info, relative))
        required = {"app/" + file for file in APP_FILES} | {"Start-App.cmd", "Update-Guantuiguang.exe"}
        if not required.issubset({relative for _, relative in entries}):
            raise ValueError("Incomplete full package")
        stage = plain_path(stage)
        stage.mkdir(exist_ok=False)
        app = stage / "app"
        app.mkdir()
        for info, relative in entries:
            if relative.startswith("app/"):
                with archive.open(info) as source, (app / relative.split("/")[1]).open("xb") as target:
                    while chunk := source.read(1024 * 1024):
                        target.write(chunk)
    if read_version(app)["version"] != version:
        raise ValueError("Package version mismatch")
    return app


def recover_transaction(root):
    transaction = plain_path(root / TRANSACTION)
    if not transaction.exists():
        return
    record = json.loads(transaction.read_text(encoding="utf-8"))
    old = record["oldVersion"]
    new = record["newVersion"]
    version_tuple(old)
    version_tuple(new)
    app = plain_path(root / "app")
    previous = plain_path(root / "app.previous")
    if app.exists():
        if read_version(app)["version"] not in (old, new):
            raise ValueError("Unrecognized transaction app; manual inspection required")
    else:
        if read_version(previous)["version"] != old:
            raise ValueError("Recovery version mismatch")
        os.replace(previous, app)
    transaction.unlink()
    log(root, "Recovered interrupted update")


def install_candidate(root, candidate, version, inject_failure=False):
    root = plain_path(root)
    candidate = plain_path(candidate)
    if not candidate.is_relative_to(root) or candidate == root / "app":
        raise ValueError("Candidate must be isolated inside installation")
    if read_version(candidate)["version"] != version:
        raise ValueError("Candidate version mismatch")
    app = plain_path(root / "app")
    old = read_version(app)["version"]
    if version_tuple(version) <= version_tuple(old):
        raise ValueError("Downgrade or same-version replacement refused")
    previous = plain_path(root / "app.previous")
    if previous.exists():
        history = plain_path(root / ".update-history")
        history.mkdir(exist_ok=True)
        os.replace(previous, history / ("app.previous-" + uuid.uuid4().hex))
    write_json(root / TRANSACTION, {"oldVersion": old, "newVersion": version})
    try:
        os.replace(app, previous)
        if inject_failure:
            raise OSError("Injected isolated swap failure")
        os.replace(candidate, app)
        if read_version(app)["version"] != version:
            raise ValueError("Installed version mismatch")
    except Exception:
        if not app.exists() and previous.exists():
            os.replace(previous, app)
        if app.exists() and read_version(app)["version"] == old:
            plain_path(root / TRANSACTION).unlink(missing_ok=True)
        raise
    plain_path(root / TRANSACTION).unlink()


def is_app_running(root):
    if os.name != "nt":
        return False
    # Return paths only, not command lines or account data. Any query failure is fail-closed.
    result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -eq '自动关推广.exe' } | Select-Object -ExpandProperty ExecutablePath | ConvertTo-Json -Compress"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, creationflags=0x08000000)
    if result.returncode:
        raise OSError("Cannot check running application")
    paths = json.loads(result.stdout.strip() or "[]")
    if isinstance(paths, str):
        paths = [paths]
    expected = str((root / "app" / EXE_NAME).absolute()).casefold()
    return any(not path or str(Path(path).absolute()).casefold() == expected for path in paths)


@contextlib.contextmanager
def update_lock(root):
    lock = plain_path(root / ".update.lock")
    with lock.open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            if lock.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
                handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def prompt(old, new, notes):
    import tkinter as tk
    from tkinter import messagebox
    window = tk.Tk()
    window.withdraw()
    try:
        return "now" if messagebox.askyesno("自动关推广 - 发现新版本", f"当前版本：{old}\n新版本：{new}\n\n{notes}\n\n现在更新吗？选择“否”将继续使用当前版本。", parent=window) else "later"
    finally:
        window.destroy()


def smoke_candidate(app, version, work):
    report = work / "release-check.json"
    result = subprocess.run([str(app / EXE_NAME), "--release-check", "--report", str(report)], cwd=str(work), timeout=60, creationflags=0x08000000 if os.name == "nt" else 0)
    if result.returncode or not report.is_file():
        raise ValueError("Candidate self-check failed")
    info = json.loads(report.read_text(encoding="utf-8"))
    if info != {"productId": PRODUCT, "version": version, "ok": True}:
        raise ValueError("Candidate self-check product/version mismatch")


def check_and_update(root, choice="prompt", manifest_url=MANIFEST_URL, test_mode=False, inject_failure=False):
    root = plain_path(root)
    root.mkdir(exist_ok=True)
    with update_lock(root):
        if is_app_running(root):
            return "busy"
        recover_transaction(root)
        old = read_version(root / "app")["version"]
        try:
            manifest = validate_manifest(fetch_manifest(manifest_url, test_mode), test_mode)
            new = manifest["version"]
            if version_tuple(new) <= version_tuple(old):
                return "current"
            selected = prompt(old, new, str(manifest.get("notes", ""))) if choice == "prompt" else choice
            if selected != "now":
                return "later"
            work = root / (".update-" + uuid.uuid4().hex)
            work.mkdir()
            package = work / "package.zip"
            download_package(manifest["url"], package, test_mode=test_mode)
            if digest(package).lower() != manifest["sha256"].lower():
                raise ValueError("Package SHA-256 mismatch")
            candidate = extract_candidate(package, work / "stage", new)
            smoke_candidate(candidate, new, work)
            if is_app_running(root):
                return "busy"
            install_candidate(root, candidate, new, inject_failure and test_mode)
            log(root, f"Updated {old} -> {new}; data unchanged")
            return "updated"
        except Exception as error:
            recover_transaction(root)
            read_version(root / "app")
            log(root, f"Update failed; retained usable app: {type(error).__name__}: {error}")
            log(root, traceback.format_exc())
            return "fallback"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest-url", default=MANIFEST_URL)
    parser.add_argument("--test-mode", action="store_true")
    parser.add_argument("--choice", choices=("prompt", "now", "later"), default="prompt")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--inject-swap-failure", action="store_true")
    args = parser.parse_args(argv)
    if not args.test_mode and (args.manifest_url != MANIFEST_URL or args.choice != "prompt" or args.inject_swap_failure):
        parser.error("Production uses the fixed manifest and a user prompt")
    root = plain_path(args.root)
    try:
        result = check_and_update(root, args.choice, args.manifest_url, args.test_mode, args.inject_swap_failure)
        if result == "busy":
            return 5
        info = read_version(root / "app")
        write_json(root / ".last-update-result.json", {"result": result, "version": info["version"]})
        if not args.no_launch:
            subprocess.Popen([str(root / "app" / EXE_NAME)], cwd=str(root))
        return 0
    except Exception as error:
        try:
            log(root, f"Startup stopped for safety: {type(error).__name__}: {error}")
        except Exception:
            pass
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
