import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from account_config_ui import load_config_for_edit, open_account_config, save_config as save_config_for_edit


def zh(text):
    return text.encode("ascii").decode("unicode_escape")


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / zh(r"\u81ea\u52a8\u5173\u63a8\u5e7f")
CONFIG_FILE = AD_DIR / "config.json"
LOCK_FILE = AD_DIR / "data" / "monitor.lock"
SUPERVISOR_LOCK_FILE = AD_DIR / "data" / "supervisor.lock"
STOP_SUPERVISOR_FILE = AD_DIR / "data" / "stop-supervisor.flag"


def child_env():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_detached(path):
    subprocess.Popen(
        ["cmd", "/c", "start", "", str(path)],
        cwd=str(ROOT),
        shell=False,
        env=child_env(),
    )


def run_capture(args):
    return subprocess.run(
        [str(x) for x in args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=child_env(),
    )


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_config(config):
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def is_pid_running(pid):
    if not pid:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    return str(pid) in result.stdout


def taskkill_pid(pid, dry_run=False):
    if not pid:
        return False
    if dry_run:
        return True
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/F", "/T"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    return True


def pids_on_tcp_port(port):
    if not port:
        return set()
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    pids = set()
    pattern = re.compile(rf"^\s*TCP\s+\S+:{int(port)}\s+\S+\s+LISTENING\s+(\d+)\s*$", re.I)
    for line in result.stdout.splitlines():
        match = pattern.search(line)
        if match:
            pids.add(int(match.group(1)))
    return pids


def configured_debug_ports():
    config = load_config()
    try:
        sys.path.insert(0, str(AD_DIR))
        from main_accounts import normalize_main_accounts, split_accounts_for_parallel_browsers
        accounts = split_accounts_for_parallel_browsers(config, normalize_main_accounts(config))
        return sorted({int(account["chrome_debug_port"]) for account in accounts})
    except Exception:
        pass
    ports = set()
    if isinstance(config.get("chrome_debug_port"), int):
        ports.add(config["chrome_debug_port"])
    for account in config.get("main_accounts") or []:
        if not isinstance(account, dict):
            continue
        port = account.get("chrome_debug_port")
        if isinstance(port, int):
            ports.add(port)
    return sorted(ports)


def stop_all_background(dry_run=False):
    stopped = []
    errors = []

    if not dry_run:
        try:
            STOP_SUPERVISOR_FILE.parent.mkdir(parents=True, exist_ok=True)
            STOP_SUPERVISOR_FILE.write_text("stop", encoding="utf-8")
        except Exception as exc:
            errors.append(f"stop flag: {exc}")

    if SUPERVISOR_LOCK_FILE.exists():
        try:
            lock = json.loads(SUPERVISOR_LOCK_FILE.read_text(encoding="utf-8-sig"))
            pid = int(lock.get("pid") or 0)
            if pid and is_pid_running(pid):
                taskkill_pid(pid, dry_run=dry_run)
                stopped.append(f"supervisor PID {pid}")
            if not dry_run:
                try:
                    SUPERVISOR_LOCK_FILE.unlink()
                except OSError:
                    pass
        except Exception as exc:
            errors.append(f"supervisor lock: {exc}")

    if LOCK_FILE.exists():
        try:
            lock = json.loads(LOCK_FILE.read_text(encoding="utf-8-sig"))
            pid = int(lock.get("pid") or 0)
            if pid and is_pid_running(pid):
                taskkill_pid(pid, dry_run=dry_run)
                stopped.append(f"monitor PID {pid}")
            if not dry_run:
                try:
                    LOCK_FILE.unlink()
                except OSError:
                    pass
        except Exception as exc:
            errors.append(f"lock: {exc}")

    for port in configured_debug_ports():
        for pid in pids_on_tcp_port(port):
            try:
                taskkill_pid(pid, dry_run=dry_run)
                stopped.append(f"Chrome port {port} PID {pid}")
            except Exception as exc:
                errors.append(f"port {port}: {exc}")

    return stopped, errors


class App:
    def __init__(self, root):
        self.root = root
        root.title(zh(r"\u81ea\u52a8\u5173\u63a8\u5e7f\u672c\u5730\u7a0b\u5e8f"))
        root.geometry("940x650")
        root.minsize(820, 560)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        title = tk.Label(
            root,
            text=zh(r"\u81ea\u52a8\u5173\u63a8\u5e7f\u672c\u5730\u7a0b\u5e8f"),
            font=("Microsoft YaHei UI", 16, "bold"),
        )
        title.pack(anchor="w", padx=14, pady=(12, 4))

        self.status = tk.Label(root, text=f"{zh(r'\u76ee\u5f55')}: {ROOT}", anchor="w")
        self.status.pack(fill="x", padx=14)

        frame = tk.Frame(root)
        frame.pack(fill="x", padx=12, pady=10)

        buttons = [
            (zh(r"\u8d26\u6237\u914d\u7f6e"), self.configure_accounts),
            (zh(r"\u9996\u6b21\u5b89\u88c5"), lambda: self.open_bat(zh(r"\u9996\u6b21\u5b89\u88c5.bat"))),
            (zh(r"\u4e00\u952e\u81ea\u68c0"), self.self_check),
            (zh(r"\u6253\u5f00\u5de8\u91cf\u767b\u5f55"), lambda: self.open_bat(zh(r"\u6253\u5f00\u5de8\u91cf\u767b\u5f55.bat"))),
            (zh(r"\u5199\u5165\u6388\u6743\u7801"), lambda: self.open_bat(zh(r"\u5199\u5165\u5de8\u91cf\u6388\u6743\u7801.bat"))),
            (zh(r"\u5bfc\u5165\u8d26\u53f7\u6388\u6743"), lambda: self.open_bat(zh(r"\u81ea\u52a8\u5bfc\u5165\u5de8\u91cf\u8d26\u53f7\u6388\u6743.bat"))),
            (zh(r"\u542f\u52a8\u76d1\u63a7"), lambda: self.open_bat(zh(r"\u542f\u52a8\u76d1\u63a7.bat"))),
            (zh(r"\u505c\u6b62\u76d1\u63a7"), self.stop_monitor),
            (zh(r"\u5237\u65b0\u72b6\u6001"), self.refresh_status),
            (zh(r"\u6253\u5f00\u65e5\u5fd7"), lambda: self.open_bat(zh(r"\u6253\u5f00\u65e5\u5fd7\u6587\u4ef6\u5939.bat"))),
            (zh(r"\u65e7\u6587\u672c\u6863\uff08\u517c\u5bb9\uff09"), self.open_account_folder),
        ]

        for index, (text, command) in enumerate(buttons):
            btn = tk.Button(frame, text=text, width=14, height=2, command=command)
            btn.grid(row=index // 5, column=index % 5, padx=4, pady=4, sticky="ew")
        for i in range(5):
            frame.grid_columnconfigure(i, weight=1)

        setting = tk.Frame(root)
        setting.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(setting, text=zh(r"\u540c\u65f6\u68c0\u6d4b\u8d26\u6237\u6570")).pack(side="left")
        current = max(1, int(load_config().get("parallel_browser_count", 3)))
        self.parallel_count = tk.Spinbox(setting, from_=1, to=10, width=5)
        self.parallel_count.delete(0, "end")
        self.parallel_count.insert(0, str(current))
        self.parallel_count.pack(side="left", padx=8)
        tk.Button(setting, text=zh(r"\u4fdd\u5b58\u8bbe\u7f6e"), command=self.save_parallel_count).pack(side="left")

        self.output = tk.Text(root, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.write(zh(r"\u8bf4\u660e\uff1a\u8fd9\u4e2a\u7a97\u53e3\u53ea\u8d1f\u8d23\u6253\u5f00\u672c\u5730\u529f\u80fd\u548c\u67e5\u770b\u72b6\u6001\u3002\u5173\u95ed\u7a97\u53e3\u65f6\u4f1a\u505c\u6389\u76d1\u63a7\u548c\u4e13\u7528 Chrome\u3002\n"))
        self.refresh_status()
        self.root.after(60000, self.auto_refresh)

    def write(self, text):
        self.output.insert("end", text)
        self.output.see("end")

    def clear_write(self, text):
        self.output.delete("1.0", "end")
        self.write(text)

    def open_bat(self, name):
        path = ROOT / name
        if not path.exists():
            messagebox.showerror(zh(r"\u627e\u4e0d\u5230\u6587\u4ef6"), str(path))
            return
        run_detached(path)
        self.write(f"\n{zh(r'\u5df2\u6253\u5f00')}: {name}\n")

    def open_account_folder(self):
        folder = AD_DIR / zh(r"\u8d26\u53f7\u63a5\u53e3\u4fe1\u606f")
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(folder)])
        self.write(f"\n{zh(r'\u5df2\u6253\u5f00\u8d26\u53f7\u63a5\u53e3\u4fe1\u606f\u6587\u4ef6\u5939')}: {folder}\n")

    def configure_accounts(self):
        def module_loader(name):
            path = str(AD_DIR)
            if path not in sys.path:
                sys.path.insert(0, path)
            return importlib.import_module(name)

        def after_save():
            config, _ = load_config_for_edit(CONFIG_FILE)
            count = max(1, int(config.get("parallel_browser_count", 3)))
            self.parallel_count.delete(0, "end")
            self.parallel_count.insert(0, str(count))
            self.write("\n" + zh(r"\u8d26\u6237\u914d\u7f6e\u5df2\u4fdd\u5b58\u3002\u505c\u6b62\u5e76\u91cd\u65b0\u542f\u52a8\u76d1\u63a7\u540e\u751f\u6548\u3002") + "\n")
            self.refresh_status()

        open_account_config(self.root, CONFIG_FILE, module_loader, after_save)

    def save_parallel_count(self):
        try:
            count = max(1, min(10, int(self.parallel_count.get())))
            config, _ = load_config_for_edit(CONFIG_FILE)
            config["parallel_browser_count"] = count
            config["one_browser_per_advertiser"] = True
            config.setdefault("per_advertiser_port_base", 9400)
            save_config_for_edit(CONFIG_FILE, config)
            self.parallel_count.delete(0, "end")
            self.parallel_count.insert(0, str(count))
            self.write(f"\n{zh(r'\u5df2\u4fdd\u5b58\u5e76\u53d1\u6570')}: {count}。{zh(r'\u505c\u6b62\u540e\u91cd\u65b0\u542f\u52a8\u76d1\u63a7\u540e\u751f\u6548')}\n")
        except Exception as exc:
            messagebox.showerror(zh(r"\u4fdd\u5b58\u5931\u8d25"), str(exc))

    def run_python_script_async(self, script, clear=True):
        def worker():
            result = run_capture([sys.executable, str(ROOT / "tools" / script)])
            text = result.stdout
            if result.stderr:
                text += "\n--- STDERR ---\n" + result.stderr
            self.root.after(0, lambda: self.clear_write(text) if clear else self.write(text))

        threading.Thread(target=worker, daemon=True).start()

    def self_check(self):
        self.clear_write(zh(r"\u6b63\u5728\u81ea\u68c0...\n"))
        self.run_python_script_async("check_oceanengine_only.py")

    def refresh_status(self):
        self.run_python_script_async("status_oceanengine_only.py")

    def auto_refresh(self):
        self.refresh_status()
        self.root.after(60000, self.auto_refresh)

    def stop_monitor(self):
        self.clear_write(zh(r"\u6b63\u5728\u505c\u6b62\u540e\u53f0\u8fdb\u7a0b...\n"))
        stopped, errors = stop_all_background()
        lines = [zh(r"\u505c\u6b62\u5b8c\u6210\u3002")]
        if stopped:
            lines.append(zh(r"\u5df2\u505c\u6b62:"))
            lines.extend(f"- {item}" for item in stopped)
        else:
            lines.append(zh(r"\u672a\u53d1\u73b0\u9700\u505c\u6b62\u7684\u540e\u53f0\u8fdb\u7a0b\u3002"))
        if errors:
            lines.append(zh(r"\u5f02\u5e38:"))
            lines.extend(f"- {item}" for item in errors)
        self.clear_write("\n".join(lines) + "\n")

    def on_close(self):
        try:
            stop_all_background()
        finally:
            self.root.destroy()


def self_test():
    required = [
        ROOT / zh(r"\u9996\u6b21\u5b89\u88c5.bat"),
        ROOT / zh(r"\u4e00\u952e\u81ea\u68c0.bat"),
        ROOT / zh(r"\u542f\u52a8\u76d1\u63a7.bat"),
        ROOT / zh(r"\u505c\u6b62\u76d1\u63a7.bat"),
        ROOT / "tools" / "check_oceanengine_only.py",
        ROOT / "tools" / "status_oceanengine_only.py",
        AD_DIR / "monitor_oceanengine_units.py",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("missing:")
        print("\n".join(missing))
        return 1
    stop_all_background(dry_run=True)
    print("local app self-test OK")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--stop-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(self_test())
    if args.stop_only:
        stopped, errors = stop_all_background()
        print(zh(r"\u505c\u6b62\u5b8c\u6210\u3002"))
        for item in stopped:
            print(f"- {item}")
        for item in errors:
            print(f"ERROR: {item}")
        raise SystemExit(1 if errors else 0)
    window = tk.Tk()
    App(window)
    window.mainloop()


if __name__ == "__main__":
    main()
