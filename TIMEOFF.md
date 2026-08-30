# 自动关推广交接

## 当前目标

将 `E:\自动关推广对外版` 作为自动关推广的唯一正式源码根目录，通过 GitHub 仓库安全交接到其他电脑或会话；后续在不覆盖每台电脑独立账户授权、Token、Chrome 登录状态、运行状态和日志的前提下，继续完善与发布 Windows 本地程序。

当前远程仓库：`https://github.com/nmrsz645-bit/guantuiguang.git`。

当前提交以 `git rev-parse HEAD` 和 `git ls-remote origin refs/heads/main` 的一致结果为准；不要依赖本文档内的旧提交号。

## 已完成并验证

- 正式源码根目录已确定为 `E:\自动关推广对外版`，Git 默认分支为 `main`，远程 `origin` 已指向上述 GitHub 仓库。
- 项目已具备源码交接文件：`.gitignore`、`README.md`、`AGENTS.md`、`requirements.txt`、`config.example.json`。
- `.gitignore` 已排除用户私密配置、Token、Chrome profile、登录页面、日志、运行状态和离线安装包；最近一次提交未包含这些内容。
- 核心监控逻辑位于 `自动关推广\monitor_oceanengine_units.py`；账户文本解析和并发浏览器分配位于 `自动关推广\main_accounts.py`；账户导入逻辑位于 `自动关推广\import_account_texts.py`。
- 桌面程序入口位于 `tools\desktop_oceanengine_app.py`；监控守护进程位于 `tools\monitor_oceanengine_supervisor.py`。`tools\build_desktop_release.py` 可构建无命令窗口的 Windows EXE。
- 已添加离线自动化测试目录 `tests\` 与测试入口 `run-tests.bat`。测试不会访问巨量引擎、不会启动 Chrome，也不会读取或改动真实账号、Token、浏览器资料或推广状态。
- 已在本机执行 `py -3 -m unittest discover -s tests -v`：17 项测试全部通过，其中包含首次配置创建与已有配置保护、完整接口配置校验及端口/账户 ID 冲突校验。
- 已在本机执行 `py -3 -m py_compile 自动关推广\main_accounts.py 自动关推广\import_account_texts.py 自动关推广\monitor_oceanengine_units.py`：通过。
- 已在隔离目录从远程 `origin/main` 真实克隆，建立干净虚拟环境并执行首次安装流程：依赖安装、初始配置创建、严格自检、17 项测试、全量编译和本地程序自测均通过。
- 已构建 `release\自动关推广-v1.2.1\自动关推广.exe`，PE 子系统为 GUI（`2`），不显示命令窗口；生成的 `release\` 目录已被 Git 忽略，不能替代源码提交。

## 未完成事项

- 未进行真实巨量引擎接口调用、真实 Chrome 登录或真实关闭推广单元的自动化回归；任何此类验证都必须使用用户明确指定的测试账户，并先确认允许关闭范围。
- 未在一台全新电脑完成“克隆源码 -> 首次安装 -> 登录 -> 授权 -> 自检 -> 启动监控”的完整验收。
- 当前自动化测试覆盖离线业务规则，不覆盖桌面 EXE 打包、Windows 启动项、升级器、真实网络异常和 UI 自动化。
- 如需发布新版，必须先从本源码目录构建，做隔离升级/回滚验证，再发布；不能拿用户电脑上任意旧发布目录作为源码。

## 下一步具体操作

第一条操作（直接照做、只读）：在接手电脑克隆或打开仓库后，执行下面命令，确认源码状态和提交一致；在结果正常前不要修改、安装、授权或启动监控。

```powershell
Set-Location 'E:\自动关推广对外版'
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main
py -3 -m unittest discover -s tests -v
```

预期：`git status --short` 无输出；本地与远程提交号一致；17 项测试均为 `OK`。

确认后，如是在新电脑，再按 `README.md` 的“新电脑首次使用”执行：首次安装会在配置不存在时自动生成本机 `config.json`，再通过桌面程序填写账户和接口信息、完成独立 Chrome 登录与授权，运行 `一键自检.bat` 确认 `Errors: 0` 后才启动监控。首次安装不得覆盖已有 `config.json`。

## 关键文件与路径

- 源码根目录：`E:\自动关推广对外版`
- 核心监控：`E:\自动关推广对外版\自动关推广\monitor_oceanengine_units.py`
- 账户规则：`E:\自动关推广对外版\自动关推广\main_accounts.py`
- 账户导入：`E:\自动关推广对外版\自动关推广\import_account_texts.py`
- 桌面界面：`E:\自动关推广对外版\tools\desktop_oceanengine_app.py`
- 守护进程：`E:\自动关推广对外版\tools\monitor_oceanengine_supervisor.py`
- 自动化测试：`E:\自动关推广对外版\tests\`
- 测试入口：`E:\自动关推广对外版\run-tests.bat`
- 示例配置：`E:\自动关推广对外版\config.example.json`
- 安装与启动入口：`E:\自动关推广对外版\首次安装.bat`、`打开巨量登录.bat`、`一键自检.bat`、`启动监控.bat`、`自动关推广本地程序.bat`

## 运行与验证命令

```powershell
Set-Location 'E:\自动关推广对外版'

# 源码、远程与私密文件检查
git status --short
git check-ignore -v '自动关推广\config.json' '自动关推广\tokens\example.json' '自动关推广\chrome-profiles\Default\Preferences'
git rev-parse HEAD
git ls-remote origin refs/heads/main

# 离线自动化测试与语法检查
py -3 -m unittest discover -s tests -v
py -3 -m py_compile 自动关推广\main_accounts.py 自动关推广\import_account_texts.py 自动关推广\monitor_oceanengine_units.py

# 真实运行前的本机自检（会读取本机配置，但不应启动监控）
.\一键自检.bat
```

## 已知问题与边界

- 当前自动化测试是离线回归测试，17 项通过不等于真实巨量接口、授权、Chrome 或实际关推广已经验收。
- 监控同一时间只能运行一个实例；出现“监控已经在运行”时，先用 `停止监控.bat` 处理，再确认锁文件和进程状态，禁止直接删除用户数据目录。
- 统一 Python 启动器会设置 UTF-8 控制台代码页和 Python 输出编码；已有入口文件应保持原名和目录结构，排错优先使用 README 中的入口和 `一键自检.bat`。
- 用户反馈过其他电脑缺少运行依赖；新电脑必须执行 `首次安装.bat`，不能只复制 `app` 子目录或某一个 EXE。源码克隆不含离线安装包；没有 Python 时，入口会尝试 `winget` 安装 Python 3.12，无法使用 `winget` 则需完整发布包或管理员安装 Python。
- 发布、升级和打包行为尚未在本次测试中验证，接手后不得仅凭版本号声称发布可用。
- EXE 已完成构建和 GUI 子系统验证，但尚未用真实测试账户完成登录、授权、扫描和关推广的端到端验收。

## 绝对不能误动的数据和配置

以下内容仅属于具体用户电脑，不得提交 Git、不得用仓库版本覆盖、不得为了排错删除：

- `自动关推广\config.json`：包含 App ID、App Secret、账户映射和本机运行配置。
- `自动关推广\tokens\`、`自动关推广\账号接口信息\`：Token、授权信息和账户资料。
- `自动关推广\chrome-profiles\`、`自动关推广\chrome-debug-profile\`、`自动关推广\login-pages\`：Chrome 登录状态和独立浏览器资料。
- `自动关推广\data\`：运行状态、监控锁、扫描记录和恢复所需数据。
- `自动关推广\rizhi\`、根目录 `rizhi\`、根目录 `logs\`：运行日志；程序规则为保留 72 小时，排错时不得擅自清空。
- `installers\`：离线安装包和发布物；除非用户明确指定发布清理，否则不要删除或覆盖。
- `release\`、`dist\`、`build\`：本机生成的发布和构建产物；可用于交付，但不提交 Git，重新构建前不得覆盖唯一发布备份。
- `app.previous`、旧版本备份、用户自行保存的发布包：属于回滚资料，未经明确授权不得处理。
