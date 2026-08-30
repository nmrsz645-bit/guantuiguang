# 当前交接

## 当前目标

将 `E:\自动关推广对外版` 作为自动关推广的正式源码根目录，用 Git 安全交接到另一台电脑，同时保留每台电脑独立的账户授权、Token、Chrome 登录状态和运行历史。

## 已完成

- 明确正式源码根目录：`E:\自动关推广对外版`。
- 核心监控代码：`自动关推广\monitor_oceanengine_units.py`。
- 守护进程：`tools\monitor_oceanengine_supervisor.py`。
- 桌面程序：`tools\desktop_oceanengine_app.py`。
- 已新增 `.gitignore`、`README.md`、`AGENTS.md`、`requirements.txt` 和 `config.example.json`。
- `.gitignore` 排除了账号配置、授权 Token、Chrome profile、日志、运行状态和离线安装包。
- 已初始化 Git 的 `main` 分支，并创建本地首个提交：`0da63ba 建立自动关推广源码交接仓库`。
- 已验证核心 Python 脚本可通过 `py -3 -m py_compile`。
- 已连接并推送至远程仓库：`https://github.com/nmrsz645-bit/guantuiguang.git`。
- 已回读验证远程 `origin/main` 与本地提交一致。
- 已新增离线自动化测试：`tests\` 使用 Python 标准库 `unittest`，不会调用真实巨量接口、启动 Chrome，或修改用户账户、Token、浏览器资料及推广状态。
- 已新增 `run-tests.bat`；验证命令为 `py -3 -m unittest discover -s tests -v`。

## 未完成

- 新电脑克隆后必须重新首次安装、登录和授权；不能从 Git 恢复私密数据。

## 下一步（直接执行）

在另一台电脑克隆 `https://github.com/nmrsz645-bit/guantuiguang.git`，然后按照 `README.md` 执行首次安装、专用 Chrome 登录和账户授权；不得从 Git 获取或覆盖用户的私密配置。

## 关键路径

- 正式源码：`E:\自动关推广对外版`
- 账户运行配置：`E:\自动关推广对外版\自动关推广\config.json`（私密，不提交）
- 账户授权与 Token：`E:\自动关推广对外版\自动关推广\tokens`、`账号接口信息`（私密，不提交）
- 浏览器登录数据：`E:\自动关推广对外版\自动关推广\chrome-profiles`（私密，不提交）
- 日志：`E:\自动关推广对外版\rizhi`、`E:\自动关推广对外版\自动关推广\rizhi`（不提交）
- 离线安装包：`E:\自动关推广对外版\installers`（发布物，不提交 Git）

## 验证命令

```powershell
Set-Location 'E:\自动关推广对外版'
git status --ignored
git diff --cached --name-only
python -m py_compile 自动关推广\monitor_oceanengine_units.py tools\monitor_oceanengine_supervisor.py tools\desktop_oceanengine_app.py
py -3 -m unittest discover -s tests -v
```

## 已知问题

- Git 远程仓库已迁移并配置为 `https://github.com/nmrsz645-bit/guantuiguang.git`；后续推送前仍必须先检查 `git status`，确认没有私密数据或运行数据被纳入提交。
- `config.json` 中含 App Secret 和 Token 关联信息，只能保存在用户本机。
- `chrome-profiles` 很大，且包含登录状态，绝不可纳入仓库。
