import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
AD_DIR = ROOT / "自动关推广"
DATA_DIR = AD_DIR / "data"
LOG_DIR = AD_DIR / "rizhi"
MONITOR_SCRIPT = AD_DIR / "monitor_oceanengine_units.py"
MONITOR_LOG = LOG_DIR / "monitor.log"
CONFIG_FILE = AD_DIR / "config.json"
SUPERVISOR_LOCK = DATA_DIR / "supervisor.lock"
STOP_FLAG = DATA_DIR / "stop-supervisor.flag"
SUPERVISOR_LOG = LOG_DIR / "supervisor.log"
STALE_LOG_SECONDS = 300
STARTUP_GRACE_SECONDS = 120
LOG_RETENTION_HOURS = int(os.getenv("OCEANENGINE_LOG_RETENTION_HOURS", "72"))
LOG_CLEANUP_INTERVAL_SECONDS = 60 * 60
_last_log_cleanup = 0.0


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def cleanup_old_logs(force=False):
    """Remove expired diagnostic records without touching config, tokens, or profiles."""
    global _last_log_cleanup
    now_ts = time.time()
    if not force and now_ts - _last_log_cleanup < LOG_CLEANUP_INTERVAL_SECONDS:
        return
    _last_log_cleanup = now_ts
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(hours=max(1, LOG_RETENTION_HOURS))
    cutoff_ts = cutoff.timestamp()
    for path in LOG_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff_ts:
                path.unlink()
                continue
            if path.suffix.lower() not in {".log", ".jsonl"}:
                continue
            kept = []
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                timestamp = None
                if line.startswith("[") and len(line) >= 20:
                    try:
                        timestamp = datetime.strptime(line[1:20], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass
                elif path.suffix.lower() == ".jsonl":
                    try:
                        raw_time = json.loads(line).get("time")
                        timestamp = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        pass
                if timestamp is None or timestamp >= cutoff:
                    kept.append(line)
            path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
        except OSError:
            continue


def log(message, **data):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_old_logs()
    suffix = " " + json.dumps(data, ensure_ascii=False) if data else ""
    line = f"[{now_text()}] {message}{suffix}"
    print(line, flush=True)
    with SUPERVISOR_LOG.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


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


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def is_monitor_log_stale(log_path, now_ts, process_started_ts, stale_seconds, startup_grace_seconds):
    if now_ts - process_started_ts < startup_grace_seconds:
        return False
    if not log_path.exists():
        return True
    try:
        return now_ts - log_path.stat().st_mtime > stale_seconds
    except OSError:
        return True


def enabled_chrome_ports():
    config = read_json(CONFIG_FILE)
    try:
        sys.path.insert(0, str(AD_DIR))
        from main_accounts import normalize_main_accounts, split_accounts_for_parallel_browsers
        accounts = split_accounts_for_parallel_browsers(config, normalize_main_accounts(config))
        return {int(account["chrome_debug_port"]) for account in accounts}
    except Exception:
        pass
    ports = set()
    for account in config.get("main_accounts") or []:
        if not account.get("enabled"):
            continue
        try:
            ports.add(int(account.get("chrome_debug_port") or account.get("port")))
        except (TypeError, ValueError):
            continue
    return ports


def is_dedicated_chrome_command(commandline, root, ports):
    command = commandline or ""
    if "chrome.exe" not in command.lower():
        return False
    root_text = str(root).lower()
    if root_text not in command.lower():
        return False
    return any(f"--remote-debugging-port={port}" in command for port in ports)


def stop_dedicated_chrome():
    ports = enabled_chrome_ports()
    if not ports:
        return
    ps_script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'chrome.exe' } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    try:
        items = json.loads(result.stdout or "[]")
    except Exception:
        items = []
    if isinstance(items, dict):
        items = [items]
    for item in items:
        pid = item.get("ProcessId")
        command = item.get("CommandLine") or ""
        if not is_dedicated_chrome_command(command, ROOT, ports):
            continue
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, check=False)
        log("已关闭卡住的专用 Chrome", pid=pid)


def acquire_lock():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SUPERVISOR_LOCK.exists():
        old_pid = read_json(SUPERVISOR_LOCK).get("pid")
        if old_pid and pid_running(old_pid):
            log("守护已经在运行，当前进程退出", pid=old_pid)
            return False
        try:
            SUPERVISOR_LOCK.unlink()
        except OSError:
            pass

    try:
        STOP_FLAG.unlink()
    except OSError:
        pass

    SUPERVISOR_LOCK.write_text(
        json.dumps(
            {"pid": os.getpid(), "started_at": now_text(), "root": str(ROOT)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return True


def release_lock():
    try:
        current = read_json(SUPERVISOR_LOCK)
        if int(current.get("pid") or 0) == os.getpid():
            SUPERVISOR_LOCK.unlink()
    except OSError:
        pass


def start_monitor():
    if not MONITOR_SCRIPT.exists():
        raise FileNotFoundError(f"Cannot find {MONITOR_SCRIPT}")
    return subprocess.Popen([sys.executable, str(MONITOR_SCRIPT)], cwd=str(AD_DIR))


def stop_process(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def restart_stale_monitor(proc, process_started_ts):
    if not is_monitor_log_stale(MONITOR_LOG, time.time(), process_started_ts, STALE_LOG_SECONDS, STARTUP_GRACE_SECONDS):
        return False
    age = None
    if MONITOR_LOG.exists():
        age = int(time.time() - MONITOR_LOG.stat().st_mtime)
    log("关推广监控疑似卡住，准备重启", pid=proc.pid, monitor_log_age_seconds=age)
    stop_process(proc)
    stop_dedicated_chrome()
    return True


def main():
    if not acquire_lock():
        return 0

    restart_count = 0
    proc = None
    try:
        log("关推广守护启动", root=str(ROOT))
        while not STOP_FLAG.exists():
            log("启动关推广监控", restart_count=restart_count)
            proc = start_monitor()
            process_started_ts = time.time()

            while proc.poll() is None:
                if STOP_FLAG.exists():
                    log("收到停止信号，正在停止监控", pid=proc.pid)
                    stop_process(proc)
                    return 0
                if restart_stale_monitor(proc, process_started_ts):
                    break
                time.sleep(5)

            if STOP_FLAG.exists():
                return 0

            restart_count += 1
            log("关推广监控已退出，10秒后自动重启", exit_code=proc.returncode, restart_count=restart_count)
            time.sleep(10)
        return 0
    except KeyboardInterrupt:
        log("收到 Ctrl+C，正在退出")
        if proc is not None:
            stop_process(proc)
        return 0
    except Exception as exc:
        log("守护异常退出", error=repr(exc))
        raise
    finally:
        release_lock()
        try:
            STOP_FLAG.unlink()
        except OSError:
            pass
        log("关推广守护已退出")


if __name__ == "__main__":
    raise SystemExit(main())
