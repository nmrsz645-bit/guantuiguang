"""Windows desktop entry point for the close-promotion monitor.

The same executable has a visible management mode and hidden worker modes.
PyInstaller bundles Python and dependencies, while mutable configuration stays
next to the executable in ``data``.
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog
from account_config_ui import load_config_for_edit, open_account_config, save_config as save_config_for_edit
from config_validation import enabled_main_accounts, validate_monitor_config


CREATE_NO_WINDOW = 0x08000000
APP_VERSION = "1.2.1"
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parents[1]
SOURCE_AD_DIR = Path(__file__).resolve().parents[1] / "自动关推广"
# A desktop release must be isolated from older installations.  Old BAT files
# may have left OCEANENGINE_ROOT in the user's environment, so do not inherit it.
if IS_FROZEN:
    os.environ.pop("OCEANENGINE_ROOT", None)
    DATA_DIR = APP_DIR / "data"
else:
    DATA_DIR = Path(os.environ.get("OCEANENGINE_ROOT") or SOURCE_AD_DIR)
CONFIG_FILE = DATA_DIR / "config.json"
LOG_DIR = DATA_DIR / "rizhi"
STATE_DIR = DATA_DIR / "data"
SUPERVISOR_LOCK = STATE_DIR / "desktop-supervisor.lock"
STOP_FLAG = STATE_DIR / "desktop-stop.flag"


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_runtime_dirs():
    for folder in (DATA_DIR, LOG_DIR, STATE_DIR, DATA_DIR / "tokens", DATA_DIR / "chrome-profiles", DATA_DIR / "账号接口信息"):
        folder.mkdir(parents=True, exist_ok=True)


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default if default is not None else {}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def child_env():
    env = os.environ.copy()
    env["OCEANENGINE_ROOT"] = str(DATA_DIR)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def service_command(flag):
    if IS_FROZEN:
        return [sys.executable, flag]
    return [sys.executable, str(Path(__file__).resolve()), flag]


def pid_running(pid):
    if not pid:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {int(pid)}", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="ignore",
        check=False,
    )
    return str(int(pid)) in result.stdout


def kill_pid(pid):
    if pid and pid_running(pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
        return True
    return False


def configured_ports():
    config = read_json(CONFIG_FILE)
    ports = set()
    for index, account in enumerate(config.get("main_accounts") or [], start=1):
        if account and account.get("enabled") is not False:
            try:
                ports.add(int(account.get("chrome_debug_port") or 9221 + index))
            except (TypeError, ValueError):
                pass
    return sorted(ports)


def kill_dedicated_chrome():
    stopped = []
    for port in configured_ports():
        result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, encoding="gbk", errors="ignore", check=False)
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3].upper() == "LISTENING":
                try:
                    pid = int(parts[4])
                except ValueError:
                    continue
                if kill_pid(pid):
                    stopped.append(f"Chrome 端口 {port}")
    return stopped


def import_module(name):
    os.environ["OCEANENGINE_ROOT"] = str(DATA_DIR)
    if not IS_FROZEN:
        source = str(SOURCE_AD_DIR)
        if source not in sys.path:
            sys.path.insert(0, source)
    return importlib.import_module(name)


def invoke_module_main(name, args=None):
    old_argv = sys.argv[:]
    try:
        sys.argv = [sys.argv[0], *(args or [])]
        return import_module(name).main()
    finally:
        sys.argv = old_argv


def monitor_service():
    ensure_runtime_dirs()
    return int(invoke_module_main("monitor_oceanengine_units") or 0)


def auth_service():
    ensure_runtime_dirs()
    return int(invoke_module_main("write_auth_code") or 0)


def supervisor_service():
    ensure_runtime_dirs()
    old = read_json(SUPERVISOR_LOCK)
    if old.get("pid") and pid_running(old.get("pid")):
        return 0
    STOP_FLAG.unlink(missing_ok=True)
    proc = None
    try:
        while not STOP_FLAG.exists():
            proc = subprocess.Popen(service_command("--monitor-service"), cwd=str(APP_DIR), env=child_env(), creationflags=CREATE_NO_WINDOW)
            write_json(SUPERVISOR_LOCK, {"pid": os.getpid(), "monitor_pid": proc.pid, "started_at": now_text()})
            while proc.poll() is None and not STOP_FLAG.exists():
                time.sleep(3)
            if STOP_FLAG.exists() and proc.poll() is None:
                kill_pid(proc.pid)
            if not STOP_FLAG.exists():
                time.sleep(10)
        return 0
    finally:
        if proc and proc.poll() is None:
            kill_pid(proc.pid)
        SUPERVISOR_LOCK.unlink(missing_ok=True)
        STOP_FLAG.unlink(missing_ok=True)


def start_monitor():
    ensure_runtime_dirs()
    old = read_json(SUPERVISOR_LOCK)
    if old.get("pid") and pid_running(old.get("pid")):
        return False, "监控已经在运行。"
    STOP_FLAG.unlink(missing_ok=True)
    proc = subprocess.Popen(service_command("--supervisor-service"), cwd=str(APP_DIR), env=child_env(), creationflags=CREATE_NO_WINDOW)
    return True, f"监控已后台启动，进程号：{proc.pid}"


def stop_monitor():
    ensure_runtime_dirs()
    STOP_FLAG.write_text("stop", encoding="utf-8")
    stopped = []
    lock = read_json(SUPERVISOR_LOCK)
    for name in ("monitor_pid", "pid"):
        if kill_pid(lock.get(name)):
            stopped.append(name)
    stopped.extend(kill_dedicated_chrome())
    SUPERVISOR_LOCK.unlink(missing_ok=True)
    return stopped


def self_check_text():
    ensure_runtime_dirs()
    lines = [f"自动关推广桌面版 v{APP_VERSION} 自检", f"数据目录：{DATA_DIR}"]
    errors = []
    if not CONFIG_FILE.exists():
        errors.append(f"缺少配置文件：{CONFIG_FILE}")
    else:
        try:
            config = read_json(CONFIG_FILE)
            accounts = enabled_main_accounts(config)
            errors.extend(validate_monitor_config(config))
            if accounts:
                lines.append(f"已启用主账户：{len(accounts)}")
        except Exception as exc:
            errors.append(f"配置读取失败：{exc}")
    for module_name in ("requests", "websocket"):
        try:
            importlib.import_module(module_name)
            lines.append(f"运行依赖 {module_name}：正常")
        except Exception as exc:
            details = traceback.format_exc()
            errors.append(f"运行依赖 {module_name} 异常：{exc}")
            (LOG_DIR / "desktop-self-check-error.log").write_text(details, encoding="utf-8")
    chrome = next((Path(item) for item in (r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe") if Path(item).exists()), None)
    if chrome:
        lines.append(f"Chrome：{chrome}")
    else:
        errors.append("未找到 Google Chrome。")
    if errors:
        lines.extend(["", "错误：", *[f"- {item}" for item in errors]])
    else:
        lines.extend(["", "自检通过，可以启动监控。"])
    report = "\n".join(lines)
    (LOG_DIR / "desktop-self-check.log").write_text(report + "\n", encoding="utf-8")
    return report, not errors


def tail_log(lines=16):
    path = LOG_DIR / "monitor.log"
    if not path.exists():
        return "暂无监控日志。"
    return "\n".join(path.read_text(encoding="utf-8-sig", errors="replace").splitlines()[-lines:])


class DesktopApp:
    def __init__(self, root):
        self.root = root
        root.title(f"自动关推广 v{APP_VERSION}")
        root.geometry("920x650")
        root.minsize(760, 520)
        root.protocol("WM_DELETE_WINDOW", self.close)
        tk.Label(root, text=f"自动关推广 v{APP_VERSION}", font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", padx=18, pady=(16, 2))
        self.hint = tk.Label(root, text=f"数据目录：{DATA_DIR}", anchor="w")
        self.hint.pack(fill="x", padx=18, pady=(0, 10))
        controls = tk.Frame(root)
        controls.pack(fill="x", padx=14)
        actions = [
            ("账户配置", self.configure_accounts),
            ("启动监控", self.start), ("停止监控", self.stop), ("刷新状态", self.refresh),
            ("打开巨量登录", self.login), ("导入账户授权", self.import_accounts), ("仅导入账号", self.import_accounts_only),
            ("写入授权码", self.authorize), ("一键自检", self.check), ("打开日志", self.open_logs),
            ("账户接口信息", self.open_accounts),
        ]
        for index, (label, command) in enumerate(actions):
            tk.Button(controls, text=label, width=15, height=2, command=command).grid(row=index // 3, column=index % 3, padx=5, pady=5, sticky="ew")
        for index in range(3):
            controls.grid_columnconfigure(index, weight=1)
        settings = tk.Frame(root)
        settings.pack(fill="x", padx=18, pady=8)
        tk.Label(settings, text="同时检测账户数：").pack(side="left")
        current = max(1, int(read_json(CONFIG_FILE).get("parallel_browser_count", 3)))
        self.parallel = tk.Spinbox(settings, from_=1, to=10, width=5)
        self.parallel.delete(0, "end")
        self.parallel.insert(0, str(current))
        self.parallel.pack(side="left")
        tk.Button(settings, text="保存", command=self.save_parallel).pack(side="left", padx=8)
        self.output = tk.Text(root, font=("Consolas", 10), wrap="word")
        self.output.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.refresh()
        root.after(60000, self.auto_refresh)

    def show(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.see("end")

    def background(self, title, callback):
        self.show(title + "...\n")
        def work():
            try:
                result = callback()
                text = result if isinstance(result, str) else str(result)
            except Exception as exc:
                text = f"操作失败：{exc}"
            self.root.after(0, lambda: self.show(text))
        threading.Thread(target=work, daemon=True).start()

    def refresh(self):
        lock = read_json(SUPERVISOR_LOCK)
        running = bool(lock.get("pid") and pid_running(lock.get("pid")))
        state = "正常运行" if running else "未运行"
        text = f"监控状态：{state}\n"
        if lock:
            text += f"启动时间：{lock.get('started_at', '未知')}\n"
        text += f"已配置账户端口：{', '.join(map(str, configured_ports())) or '无'}\n\n最近日志：\n{tail_log()}"
        self.show(text)

    def auto_refresh(self):
        self.refresh()
        self.root.after(60000, self.auto_refresh)

    def start(self):
        ok, message = start_monitor()
        self.show(message)

    def stop(self):
        stopped = stop_monitor()
        self.show("监控和专用浏览器已停止。\n" + ("\n".join(stopped) if stopped else "未发现运行中的后台进程。"))

    def login(self):
        self.background("正在打开各账户的专用 Chrome", lambda: invoke_module_main("open_main_account_logins") or "已打开登录浏览器。")

    def import_accounts(self):
        self.background("正在导入账户接口信息", lambda: invoke_module_main("import_account_texts") or "账户授权导入完成。")

    def import_accounts_only(self):
        self.background(
            "正在仅导入账号",
            lambda: invoke_module_main("import_account_texts", ["--accounts-only"])
            or "账号导入完成，原授权、回调链接、token 和登录资料保持不变。",
        )

    def authorize(self):
        text = simpledialog.askstring(
            "写入巨量授权",
            "粘贴巨量授权完成后跳转的完整网址，或直接粘贴 auth_code。\n\n"
            "此操作不会打开黑框窗口。",
            parent=self.root,
        )
        if text is None:
            return
        if not text.strip():
            messagebox.showinfo("需要授权码", "请完成巨量授权后，再把完整回调网址粘贴到这里。", parent=self.root)
            return
        self.background("正在写入授权", lambda: invoke_module_main("write_auth_code", [text]) or "授权写入完成。")

    def check(self):
        self.show(self_check_text()[0])

    def open_logs(self):
        ensure_runtime_dirs()
        subprocess.Popen(["explorer", str(LOG_DIR)])

    def configure_accounts(self):
        ensure_runtime_dirs()
        open_account_config(self.root, CONFIG_FILE, import_module, self.refresh)

    def open_accounts(self):
        ensure_runtime_dirs()
        subprocess.Popen(["explorer", str(DATA_DIR / "账号接口信息")])

    def save_parallel(self):
        try:
            count = max(1, min(10, int(self.parallel.get())))
            config, _ = load_config_for_edit(CONFIG_FILE)
            config["parallel_browser_count"] = count
            config["one_browser_per_advertiser"] = True
            save_config_for_edit(CONFIG_FILE, config)
            self.show(f"并发账户数已保存为 {count}。重新启动监控后生效。")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def close(self):
        stop_monitor()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--monitor-service", action="store_true")
    parser.add_argument("--supervisor-service", action="store_true")
    parser.add_argument("--auth-service", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args, _ = parser.parse_known_args()
    if args.monitor_service:
        return monitor_service()
    if args.supervisor_service:
        return supervisor_service()
    if args.auth_service:
        return auth_service()
    if args.self_check:
        _, ok = self_check_text()
        return 0 if ok else 1
    ensure_runtime_dirs()
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
