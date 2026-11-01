# 自动关推广维护交接

> 这是面向下一位 Codex/维护者的当前交接文档。先读本文件、[README.md](README.md)、[docs/RELEASE-GUIDE.md](docs/RELEASE-GUIDE.md) 与 [AGENTS.md](AGENTS.md)；不要把 `TIMEOFF.md` 中的旧机器路径、旧构建产物或历史说明当作当前状态。

## 另一台电脑的 Codex 从这里开始

接手目标是取得完整源码，建立可维护开发环境，按实际入口启动/测试/构建；之后的上传更新分为“提交源码”和“发布完整 ZIP”两个阶段。详细可执行命令统一放在 [发布指南](docs/RELEASE-GUIDE.md)，不依赖本次聊天。

1. 新电脑无目录时克隆 `main` 到 `C:\Projects\guantuiguang`；已有目录先报告远端、分支、HEAD、暂存与未提交改动，不覆盖原件。
2. 在实际源码根先读本文件、README、AGENTS 和发布指南；安装/确认 Python 3.13.15 与 PyInstaller 6.22.2，执行本机离线测试。旧电脑的测试不能代替新机结果。
3. 源码 GUI 是 `py -3.13 .\tools\local_oceanengine_app.py`；构建是 `py -3.13 .\tools\build_desktop_release.py`。二者用途不同，启动监控另须用户指定账户和授权范围。
4. 修改源码后按指南的显式文件列表暂存、普通提交/推送；只有未来新程序版本获批才创建新 tag 和 Release。当前 v1.2.1 已发布，不能重打 tag 或覆盖包。
5. 真实配置、Token 和 Chrome 登录态在目标电脑重新取得；不向旧电脑索取资料。源码已完整，不需要逆向 EXE。

## 版本、仓库与范围

- 仓库：`https://github.com/nmrsz645-bit/guantuiguang.git`
- 默认分支：`main`
- 应用版本：`1.2.1`，定义在 `tools/desktop_oceanengine_app.py` 的 `APP_VERSION`
- 正式版本依据：GitHub Release tag `v1.2.1` 解引用指向 `7022e034e10dfbcf498caf5b6670c2b02a338e0f`。接手时执行 `git ls-remote origin refs/heads/main 'refs/tags/v1.2.1^{}'`；`main` 后续文档修订不改变这个程序包。
- 作用：读取经授权的巨量引擎投放账户；二维码预览条件满足时可关闭对应单元开关，不删除单元、不关闭项目。

此项目不包含也绝不恢复其他电脑的配置、账户授权、Token、App Secret、浏览器资料、运行数据或日志。不能用离线测试结果宣称真实接口、登录或关闭动作已验收。

## 架构与关键目录

| 位置 | 职责 |
| --- | --- |
| `tools/desktop_oceanengine_app.py` | PyInstaller 桌面入口；管理窗口、配置保存、后台监控/授权服务及本机 `data` 目录。 |
| `tools/account_config_ui.py` | Tkinter 账户配置界面。 |
| `tools/config_validation.py` | 启动前对账户、投放 ID、端口、App 配置的离线校验。 |
| `tools/monitor_oceanengine_supervisor.py` | 源码模式守护进程、锁、重启及专用 Chrome 清理。 |
| `自动关推广/monitor_oceanengine_units.py` | 单元读取、二维码条件判断、关闭保护、状态/日志及 OAuth 失效处理。 |
| `自动关推广/main_accounts.py` | 主账户文本解析、账户规范化和浏览器任务分配。 |
| `自动关推广/import_account_texts.py`、`write_auth_code.py` | 本机授权文本导入与 OAuth 授权码写入。 |
| `tools/bootstrap_oceanengine_only.py`、`tools/check_oceanengine_only.py` | 首次安装、依赖/文件/配置/端口自检。 |
| `tools/build_desktop_release.py` | PyInstaller 构建、Release 文件夹、哈希清单和 ZIP 打包。 |
| `tests/` | 不接网的 unittest 回归测试。 |

根目录 `.bat` 是用户入口。`自动关推广本地程序.bat` 打开配置界面，`一键自检.bat` 不启动监控，`启动监控.bat` 才会启动实际守护进程；任何验证都不得误运行后者。

业务流为：本机账户配置/授权 → 独立 Chrome 与账户分配 → 当日单元读取 → 打开状态与预览二维码判断 → 只检测或关闭该单元 → 写本机状态与日志。源码 GUI 和打包 EXE 共用业务模块，但使用不同数据根；修改账户规则从 main_accounts/config_validation 入手，修改二维码/关闭规则从 monitor_oceanengine_units 入手，修改桌面模式从 desktop_oceanengine_app 入手。

## 本机运行环境

- 支持 Windows 10/11、Python 3.12 或 3.13、Git；本轮已验证 Python 3.13.15 与 PyInstaller 6.22.2，开发/构建命令固定使用 `py -3.13`。
- 运行依赖：`requests`、`websocket-client`、`python-dotenv`，见 `requirements.txt`。
- 发行构建额外需要 `PyInstaller`；普通用户运行 EXE 不需要 Python。
- 实际登录/监控需要本机 Chrome 和用户自行取得的巨量授权；离线测试不需要。

开发环境命令：

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 -m pip install "pyinstaller==6.22.2"
py -3.13 -m unittest discover -s tests -v
py -3.13 -m compileall -q .
```

## 安全配置与获取方式

仅将 `config.example.json` 作为模板。真实配置写入本机 `自动关推广/config.json`（源码）或 EXE 同级 `data/config.json`（桌面版），并且必须保持未跟踪。

| 数据 | 从何处取得 | 禁止事项 |
| --- | --- | --- |
| 投放账户 ID | 用户本人有权访问的巨量引擎账户页面 | 不在仓库、Issue、Release 文本中记录。 |
| App ID、App Secret、回调地址 | 用户本人创建/获授权的巨量应用配置页面；回调地址需按该应用登记 | 不猜测、生成或提交 Secret。 |
| OAuth code / Token | 用户在专用 Chrome 登录后通过本机授权入口获得 | 不复制旧电脑 Token、不共享 Token 文件。 |
| Chrome profile、账号接口文本 | 当前电脑 `data` 或源码本机受忽略目录 | 不同步到 Git、Release、网盘公开链接。 |

模板账户默认 `enabled: false`，但 `dry_run: false`、`allow_close: true`；启用后不能假定是只检测。先确保账户 ID、端口、Token 路径唯一；有账户测试需在本机配置设 `dry_run: true` 或取消允许关闭。`--no-close` 仅属于监控脚本，EXE 不实现此参数；只检测仍会连接真实平台。

## 构建、测试与发布

1. 从 `origin/main` 的干净、隔离副本开始；运行 `git status --ignored`，确认无真实配置或构建产物将进入提交。
2. 执行上述依赖安装、`unittest` 和 `compileall`。测试必须全绿；测试只证明离线逻辑。
3. 在隔离副本运行 `py -3.13 .\tools\build_desktop_release.py`；兼容 BAT 会选用泛化 `py -3`，不保证固定解释器。构建生成：
   - `release/自动关推广-v1.2.1/`，包含 EXE、`config.example.json`、README、HANDOFF、`使用说明.txt` 与 `SHA256SUMS.txt`；
   - `release/自动关推广-v1.2.1.zip`，以同名文件夹为 ZIP 根目录。
4. 审查 ZIP 文件名与内容，确认不含 `config.json`、`tokens/`、`chrome-profiles/`、`账号接口信息/`、日志、`data/`、`.env` 或个人资料；再计算并记录 ZIP SHA-256。
5. 未来新版本的 tag、推 tag 与 `gh release create --verify-tag` 命令见 [上传程序包](docs/RELEASE-GUIDE.md#github-release)。GitHub 资产名使用 ASCII `guantuiguang-v<版本>.zip`，但 ZIP 内顶层文件夹保持 `自动关推广-v<版本>`。不要强推、重打已有 tag、覆盖旧附件或删除旧 Release。
6. 发布后从 GitHub API/网页重新确认 tag 指向、Release 资产名、资产大小和哈希；仅本地成功构建不等于发布完成。

脚本对同版本的 `release` 文件夹或 ZIP 存在时会失败，目的是保护现有产物。必须发布新版本时，先更改并测试应用版本后再构建；不可通过删除唯一旧包来“重新发布”。

## 完成状态、已知边界与下一步

本次版本的离线测试覆盖：配置初始创建/不覆盖、配置校验、文本账户导入、端口去重、浏览器分配、Token 失效判定、单元状态、关闭保护、72 小时日志保留，以及 Release ZIP/清单结构。

已有验收记录（2026-10-31）：运行代码对应构建提交 `7022e03…`，18 项 unittest 和 compileall 通过，PyInstaller 构建成功，EXE 为 GUI 子系统，ZIP/文件哈希通过；隔离 EXE 自检依赖与 Chrome 正常，因无配置退出码 1，没有真实账户验证。2026-11-01 核验到的文档基线 `25a89b3…` 与该提交的运行源码/测试相同；本次仍只改文档。

正式 ZIP 的远端大小、SHA-256、下载链接见 [下载验证与手工更新](docs/RELEASE-GUIDE.md#manual-update)。当前包内的 README/HANDOFF 是构建时快照，不包含后续发布指南修订；下一位 Codex 必须读取仓库 `main` 的最新交接。

尚未完成且不能臆测完成的事项：

- 没有使用真实巨量账户执行登录、授权、接口读取或关闭推广；进行端到端测试前必须取得用户指定的测试账户和明确关闭范围。
- 没有在一台无 Python 的全新 Windows 主机上完成最终 GitHub Release 的端到端安装验证。
- 未实施 Windows 代码签名；SmartScreen/杀毒软件提示和企业终端策略仍可能影响 EXE 启动。
- 测试不覆盖真实网络异常、Windows 启动项或完整 GUI 自动化。
- 无自动更新/增量包/OSS 上传器，本项目在共享下载站没有卡片；目前用户通过 GitHub Release 手工更新完整包。守护进程会重启异常监控，重试上限/告警需要以后单独审查，不能当作已完成的有限重试保证。

常见排查入口：`一键自检.bat` 的逐项错误、`自动关推广/rizhi/monitor.log`、`crash.log`、`授权状态.txt`，以及 `一键状态面板.bat`。出现“监控已在运行”先执行 `停止监控.bat`；禁止直接删除 Token、profile、data 或锁文件来规避问题。

## 必须保留的 Git 边界

提交前运行：

```powershell
git status --ignored
git diff --cached --name-only
git check-ignore -v '自动关推广/config.json' '自动关推广/tokens/example.json' '自动关推广/chrome-profiles/Default/Preferences'
```

绝不提交、覆盖或删除以下本机内容：`自动关推广/config.json`、`tokens/`、`账号接口信息/`、`chrome-profiles/`、`chrome-debug-profile/`、`login-pages/`、`data/`、日志、运行锁、`installers/`、`release/`、`dist/`、`build/`、`app.previous` 或用户自行保存的旧包。
