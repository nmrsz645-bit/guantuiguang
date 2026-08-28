"""Desktop account and API configuration editor."""

import json
import re
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


def _load_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return None


def _extract_objects(raw):
    """Recover valid account objects from an old partially written config."""
    match = re.search(r'"main_accounts"\s*:\s*\[', raw)
    if not match:
        return []
    values, depth, begin, quoted, escape = [], 0, None, False, False
    for index, char in enumerate(raw[match.end():], match.end()):
        if quoted:
            if escape:
                escape = False
            elif char == "\\\\":
                escape = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            if depth == 0:
                begin = index
            depth += 1
        elif char == "}" and depth:
            depth -= 1
            if depth == 0 and begin is not None:
                try:
                    item = json.loads(raw[begin:index + 1])
                    if isinstance(item, dict):
                        values.append(item)
                except json.JSONDecodeError:
                    pass
                begin = None
    return values


def load_config_for_edit(path):
    data = _load_json(path)
    if data is not None:
        return data, False
    raw = path.read_text(encoding="utf-8-sig", errors="replace") if path.exists() else ""
    prefix = raw.split('"main_accounts"', 1)[0]
    recovered = {}
    for field in ("check_interval_seconds", "parallel_browser_count", "per_advertiser_port_base", "page_size", "max_pages", "redirect_uri"):
        found = re.search(r'"' + re.escape(field) + r'"\s*:\s*("(?:[^"\\]|\\.)*"|\d+|true|false|null)', prefix, re.I)
        if found:
            try:
                recovered[field] = json.loads(found.group(1))
            except json.JSONDecodeError:
                pass
    recovered["main_accounts"] = _extract_objects(raw)
    return recovered, True


def save_config(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path.with_name(f"config.before-desktop-edit-{stamp}.json").write_bytes(path.read_bytes())
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _ids(value):
    return [part.strip() for part in re.split(r"[\s,，;；]+", value or "") if part.strip()]


class AccountConfigDialog:
    def __init__(self, parent, config_file, module_loader, after_save=None):
        self.config_file = Path(config_file)
        self.module_loader = module_loader
        self.after_save = after_save
        self.config, recovered = load_config_for_edit(self.config_file)
        self.accounts = [dict(x) for x in self.config.get("main_accounts", []) if isinstance(x, dict)]
        self.selected = None
        self.window = tk.Toplevel(parent)
        self.window.title("账户与千川接口配置")
        self.window.geometry("980x650")
        self.window.minsize(850, 560)
        self.window.transient(parent)
        self.window.grab_set()
        text = "软件内保存的账户为准。删除账户不会删除其浏览器登录资料或 Token。"
        if recovered:
            text = "旧配置文件不完整，已恢复可用账户。首次保存会自动备份旧配置。"
        tk.Label(self.window, text=text, fg="#9a5a00", anchor="w").pack(fill="x", padx=14, pady=(12, 6))
        self._build()
        if self.accounts:
            self.choose(0)
        else:
            self.add_account()

    def _build(self):
        body = tk.Frame(self.window)
        body.pack(fill="both", expand=True, padx=14, pady=4)
        left = tk.Frame(body, width=230)
        left.pack(side="left", fill="y")
        right = tk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.listbox = tk.Listbox(left, exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        row = tk.Frame(left)
        row.pack(fill="x", pady=6)
        tk.Button(row, text="新增账户", command=self.add_account).pack(side="left", expand=True, fill="x")
        tk.Button(row, text="删除账户", command=self.delete_account).pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.widgets = {}
        fields = [
            ("name", "主账户名称", False),
            ("advertiser_ids", "投放账户 ID（可多个，逗号或换行分隔）", False),
            ("app_id", "千川 App ID", False),
            ("app_secret", "千川 App Secret", True),
            ("redirect_uri", "授权回调地址", False),
            ("callback_url", "授权回调完整链接 / auth_code", False),
            ("access_token", "access_token（可选）", True),
            ("refresh_token", "refresh_token（可选）", True),
        ]
        for index, (key, label, secret) in enumerate(fields):
            tk.Label(right, text=label, anchor="w").grid(row=index, column=0, sticky="w", pady=5)
            widget = tk.Text(right, height=3, wrap="word") if key == "advertiser_ids" else tk.Entry(right, show="*" if secret else "")
            widget.grid(row=index, column=1, sticky="ew", pady=5, padx=(12, 0))
            self.widgets[key] = widget
        self.enabled = tk.BooleanVar(value=True)
        self.allow_close = tk.BooleanVar(value=True)
        tk.Checkbutton(right, text="启用这个主账户", variable=self.enabled).grid(row=len(fields), column=1, sticky="w", padx=(12, 0))
        tk.Checkbutton(right, text="允许自动关闭推广", variable=self.allow_close).grid(row=len(fields) + 1, column=1, sticky="w", padx=(12, 0))
        right.grid_columnconfigure(1, weight=1)
        footer = tk.Frame(self.window)
        footer.pack(fill="x", padx=14, pady=(8, 14))
        tk.Button(footer, text="保存配置", command=self.save).pack(side="right")
        tk.Button(footer, text="保存并获取 Token", command=self.save_and_exchange).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="关闭", command=self.window.destroy).pack(side="right", padx=(0, 8))

    def _get(self, key):
        widget = self.widgets[key]
        return widget.get("1.0", "end-1c").strip() if isinstance(widget, tk.Text) else widget.get().strip()

    def _set(self, key, value):
        widget = self.widgets[key]
        if isinstance(widget, tk.Text):
            widget.delete("1.0", "end")
            widget.insert("1.0", value or "")
        else:
            widget.delete(0, "end")
            widget.insert(0, value or "")

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for index, item in enumerate(self.accounts, 1):
            flag = "启用" if item.get("enabled", True) else "停用"
            self.listbox.insert("end", f"{index}. {item.get('name') or item.get('id') or '未命名'} [{flag}]")

    def persist(self):
        if self.selected is None or self.selected >= len(self.accounts):
            return
        item = self.accounts[self.selected]
        for key in self.widgets:
            value = self._get(key)
            if key == "advertiser_ids":
                item[key] = _ids(value)
            elif value:
                item[key] = value
        item["enabled"] = self.enabled.get()
        item["allow_close"] = self.allow_close.get()

    def add_account(self):
        self.persist()
        index = len(self.accounts) + 1
        ports = {int(x.get("chrome_debug_port", 0) or 0) for x in self.accounts}
        port = 9222 if not ports else max(9302, max(ports) + 1)
        self.accounts.append({
            "id": f"main_{index:02d}", "name": f"主账户{index:02d}", "enabled": True, "allow_close": True,
            "advertiser_ids": [], "chrome_debug_port": port, "chrome_profile_dir": f"chrome-profiles/main_{index:02d}",
            "token_file": f"tokens/main_{index:02d}.json", "app_id": "", "app_secret": "", "redirect_uri": self.config.get("redirect_uri", ""),
        })
        self._refresh_list()
        self.choose(len(self.accounts) - 1)

    def delete_account(self):
        if self.selected is None:
            return
        item = self.accounts[self.selected]
        if not messagebox.askyesno("确认删除", f"从配置中删除“{item.get('name') or item.get('id')}”？\n不会删除浏览器资料或 Token。", parent=self.window):
            return
        del self.accounts[self.selected]
        self.selected = None
        self._refresh_list()
        if self.accounts:
            self.choose(0)
        else:
            self.add_account()

    def _on_select(self, _event):
        picked = self.listbox.curselection()
        if picked:
            self.persist()
            self.choose(picked[0])

    def choose(self, index):
        self.selected = index
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        item = self.accounts[index]
        for key in self.widgets:
            value = "\n".join(item.get(key) or []) if key == "advertiser_ids" else item.get(key, "")
            self._set(key, str(value or ""))
        self.enabled.set(item.get("enabled", True) is not False)
        self.allow_close.set(item.get("allow_close", True) is not False)

    def _clean(self):
        result = []
        for index, old in enumerate(self.accounts, 1):
            item = dict(old)
            item["id"] = str(item.get("id") or f"main_{index:02d}")
            item["name"] = str(item.get("name") or item["id"])
            item["advertiser_ids"] = _ids("\n".join(item.get("advertiser_ids") or []))
            item["chrome_debug_port"] = int(item.get("chrome_debug_port") or (9222 if index == 1 else 9300 + index))
            item["chrome_profile_dir"] = item.get("chrome_profile_dir") or f"chrome-profiles/{item['id']}"
            item["token_file"] = item.get("token_file") or f"tokens/{item['id']}.json"
            result.append(item)
        return result

    def save(self, quiet=False):
        self.persist()
        accounts = self._clean()
        enabled = [x for x in accounts if x.get("enabled") and x.get("advertiser_ids")]
        if not enabled:
            messagebox.showerror("无法保存", "至少需要一个启用账户，并填写投放账户 ID。", parent=self.window)
            return False
        config = dict(self.config)
        config["main_accounts"] = accounts
        config["account_source"] = "desktop"
        config["one_browser_per_advertiser"] = True
        for key in ("advertiser_ids", "chrome_debug_port", "chrome_profile_dir", "token_file", "app_id", "app_secret", "redirect_uri"):
            config[key] = enabled[0].get(key)

        # Tokens are kept in the per-account token file used by the monitor,
        # rather than being left in config.json with the general settings.
        manual_tokens = []
        for item in accounts:
            access_token = str(item.pop("access_token", "") or "").strip()
            refresh_token = str(item.pop("refresh_token", "") or "").strip()
            if access_token or refresh_token:
                manual_tokens.append((item, access_token, refresh_token))
        save_config(self.config_file, config)
        if manual_tokens:
            try:
                importer = self.module_loader("import_account_texts")
                for item, access_token, refresh_token in manual_tokens:
                    payload = {"code": 0, "data": {}}
                    if access_token:
                        payload["data"]["access_token"] = access_token
                    if refresh_token:
                        payload["data"]["refresh_token"] = refresh_token
                    importer.save_token(item, payload)
            except Exception as exc:
                messagebox.showerror("Token save failed", str(exc), parent=self.window)
                return False
        self.config, self.accounts = config, accounts
        self._refresh_list()
        if self.after_save:
            self.after_save()
        if not quiet:
            messagebox.showinfo("保存成功", "账户和千川接口信息已保存。停止并重新启动监控后生效。", parent=self.window)
        return True

    def save_and_exchange(self):
        if not self.save(quiet=True):
            return
        try:
            importer = self.module_loader("import_account_texts")
            messages = []
            for item in self.accounts:
                if item.get("enabled") and (item.get("callback_url") or item.get("auth_code")):
                    ok, detail = importer.exchange_auth_code(item)
                    messages.append(f"{item['name']}: {'成功' if ok else '失败'} - {detail}")
            messagebox.showinfo("Token 获取结果", "\n".join(messages) or "已保存。未填写授权回调链接，因此没有请求 Token。", parent=self.window)
        except Exception as exc:
            messagebox.showerror("Token 获取失败", str(exc), parent=self.window)


def open_account_config(parent, config_file, module_loader, after_save=None):
    return AccountConfigDialog(parent, config_file, module_loader, after_save)
