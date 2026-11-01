# 另一台 Windows 电脑接手与上传更新

核验日期：2026-11-01。先读 [HANDOFF](../HANDOFF.md)、[README](../README.md) 与 [AGENTS](../AGENTS.md)。以下安装、GUI、构建和发布命令供接手者按阶段执行；本次文档修订没有重新构建或发布程序，也没有启动监控。

## 1. 取得完整源码，确认正式版与开发源码

仓库：`https://github.com/nmrsz645-bit/guantuiguang.git`；开发分支：`main`。另一台电脑没有项目目录时执行：

```powershell
git clone --branch main https://github.com/nmrsz645-bit/guantuiguang.git C:\Projects\guantuiguang
Set-Location C:\Projects\guantuiguang
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main 'refs/tags/v1.2.1^{}'
```

已有目录时先检查 `git remote -v`、分支、暂存区与未提交改动；不要重复克隆到已有目录，也不要用 reset/checkout 覆盖本机改动。源码根以含 `tools`、`tests`、`自动关推广` 和本指南的 Git 仓库为准；旧电脑的 Codex 项目栏目录未必是源码根。

- 当前正式版：[v1.2.1](https://github.com/nmrsz645-bit/guantuiguang/releases/tag/v1.2.1)，构建提交 `7022e034e10dfbcf498caf5b6670c2b02a338e0f`。
- `main` 在该提交之后的修订目前均是文档；接手时以实时 HEAD 为准。修改程序用 `main` 的完整源码，普通用户下载 Release 的完整 ZIP。
- 本仓库没有固定测试分支或已发布测试包。隔离测试副本不是正式版本，`main` 新提交也不会自动替换已发布 EXE。
- 版本唯一读取位置：`tools/desktop_oceanengine_app.py` 的 `APP_VERSION`。既有 tag/资产不可覆盖；以后发新版需先批准并实际修改版本。

## 2. 新电脑准备、配置与启动

### 环境与离线验收

安装 Git、Windows x64 版 Python 及启动器 `py`；实际已验证组合是 Python **3.13.15**、PyInstaller **6.22.2**。Python 从 [官方 Windows 下载页](https://www.python.org/downloads/windows/) 获取，确认安装结果，不能只根据下载文件名认定版本。普通用户运行 EXE 不需要单独安装 Python；真实浏览器登录另需 Google Chrome。

`requirements.txt` 为版本下限：`requests>=2.31`、`websocket-client>=1.8`、`python-dotenv>=1.0`，不是完整锁定文件。以下命令固定 Python 3.13 系列；若输出不是已验证的 3.13.15，记录差异并重新验收，不声称位级可复现。

```powershell
py -3.13 --version
py -3.13 -m pip install -r requirements.txt
py -3.13 -m pip install "pyinstaller==6.22.2"
py -3.13 -m pip check
py -3.13 -m unittest discover -s tests -v
py -3.13 -m compileall -q .
```

当前离线基线为 18 项测试；全绿只证明规则/打包测试。新电脑必须自己执行测试，不能照抄旧电脑结果。`compileall .` 会递归子目录，以上适用于未在仓库内放置虚拟环境的源码副本。若另建虚拟环境，使用该环境的 python 直接运行脚本并避免编译依赖目录；批处理入口不自动选择虚拟环境。

### GUI 与本机账户

固定解释器的源码 GUI 命令：

```powershell
py -3.13 .\tools\local_oceanengine_app.py
```

标准批处理 `自动关推广本地程序.bat` 也会打开该文件，但经 `tools/run_py.bat` 选用 `py -3`；GUI 中部分按钮仍会调用这些批处理。因此系统存在多个 Python 时，既要检查 `py -3.13 --version`，也要检查 `py -3 --version` 与该解释器的依赖。打开 GUI 只显示管理界面；关闭窗口会停止本程序管理的监控及专用 Chrome。

源码首次安装入口 `首次安装.bat` 调用 `tools/bootstrap_oceanengine_only.py`，只在配置不存在时从模板创建 `自动关推广/config.json`；可能使用 winget/pip 安装运行环境。若只需检查代码，不必运行安装或填写账户。

用户真实使用顺序：账户配置 → 对应主账户专用 Chrome 登录 → 授权码或账户授权导入 → 一键自检 → 在用户明确允许后启动监控。App ID、App Secret、回调地址来自用户获授权的巨量应用管理页面；投放账户 ID 来自本人账户；Token 由本机 OAuth 授权取得。

| 模式 | 配置和私有数据根 | 自检结果 |
| --- | --- | --- |
| 源码/BAT | `自动关推广/config.json`；同目录下 tokens、chrome-profiles、rizhi、data | `一键自检.bat` / `tools/check_oceanengine_only.py` 输出 `Errors: 0` |
| Release EXE | EXE 同级 `data/config.json`；Token/profile/日志也在该 `data` 下 | 界面显示“自检通过，可以启动监控。”；`--self-check` 写 `data/rizhi/desktop-self-check.log`，成功退出码 0 |

两个模式的数据根不同，不能假定源码配置会自动被 EXE 读取。EXE 可在全新隔离目录执行 `自动关推广.exe --self-check`：未配置时退出码 1、报告缺少配置是预期结果；它不启动监控，但会创建本机空目录和自检日志。

模板默认 `enabled: false`，但同时 `dry_run: false`、`allow_close: true`。因此模板不能被称为“默认只检测”；首次有账户测试应在**本机配置**设 `dry_run: true` 或关闭该账户的“允许自动关闭推广”。`--no-close`、`--once` 只属于 `自动关推广/monitor_oceanengine_units.py`，EXE 不实现这两个参数；只检测仍会访问真实平台，不属于离线验收。

Git 只迁移源码和安全示例。真实 config、Token、App Secret、Cookie、账号接口文本、Chrome 登录态、日志、运行状态、安装器都不能随 Git 或 Release 分发。新电脑重新配置和授权；不要复制浏览器资料或依赖 Windows DPAPI 凭据跨用户/跨机器迁移。仓库没有 DPAPI 迁移工具。

<a id="source-update"></a>

## 3. 修改后怎样推送源码和文档

先在隔离源码副本修改，运行适合改动的测试，检查 `git status`、`git diff`，读取远端差异后正常整合。远端变化时禁止强推。

以下为**本次只改交接文档**的显式暂存示例；若以后修改程序，应逐个列出已审查的实际源码/测试文件：

```powershell
git fetch origin
git status --short
git log --oneline HEAD..origin/main
git diff --stat
git status --ignored
git add -- README.md HANDOFF.md TIMEOFF.md docs/RELEASE-GUIDE.md
git diff --cached --name-only
git diff --cached --check
git commit -m "docs: clarify project handoff"
git push origin main
git ls-remote origin refs/heads/main
```

暂存必须逐文件审查，禁止 `git add .`。`HEAD..origin/main` 有新提交时先停止推送并阅读/整合；推送被拒绝时也不能用 `--force`。Git 身份由接手者本人配置，可使用自己的 GitHub no-reply 邮箱；GitHub CLI 采用 `gh auth login` 浏览器交互登录，不把令牌写进命令、仓库或文档。

2026-11-01 核验本仓库没有 Actions 工作流、仓库 Webhook 或配置的 Pages 站点；以后每次发布仍需重新核实触发条件。`git push` 保存源码，**不会推送客户端更新**。

<a id="build"></a>

## 4. 新版本完整包怎样构建

前提：新版本已经批准，`APP_VERSION` 和相关说明已修改、测试通过、源码已正常提交推送。纯文档修订无需改版本或重发程序。

在源码根用 PowerShell 提取版本（避免在 `python -c` 中嵌套双引号）：

```powershell
$versionMatches = @(Select-String -LiteralPath '.\tools\desktop_oceanengine_app.py' -Pattern '^APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"\s*$')
if ($versionMatches.Count -ne 1) { throw 'APP_VERSION 必须唯一且为三段版本号' }
$releaseVersion = $versionMatches[0].Matches[0].Groups[1].Value
git ls-remote --tags origin "refs/tags/v$releaseVersion" "refs/tags/v$releaseVersion^{}"
```

上一步若有同名 tag 输出立即停止，保留旧版。然后从远端 `main` 建立**新的**隔离构建目录：

```powershell
$buildRoot = "C:\Projects\guantuiguang-build-$releaseVersion"
if (Test-Path -LiteralPath $buildRoot) { throw '构建目录已存在，请保留并另选新目录' }
git clone --branch main --single-branch https://github.com/nmrsz645-bit/guantuiguang.git $buildRoot
if ($LASTEXITCODE -ne 0) { throw '隔离克隆失败' }
Set-Location $buildRoot
$buildCommit = (git rev-parse HEAD).Trim()
$builtVersionMatch = @(Select-String -LiteralPath '.\tools\desktop_oceanengine_app.py' -Pattern '^APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"\s*$')
if ($builtVersionMatch.Count -ne 1 -or $builtVersionMatch[0].Matches[0].Groups[1].Value -ne $releaseVersion) { throw '隔离副本版本与预期不一致' }
py -3.13 -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
py -3.13 -m pip install "pyinstaller==6.22.2"
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 安装失败' }
py -3.13 -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '测试失败，禁止发布' }
py -3.13 -m compileall -q .
if ($LASTEXITCODE -ne 0) { throw '编译失败，禁止发布' }
py -3.13 .\tools\build_desktop_release.py
if ($LASTEXITCODE -ne 0) { throw '构建失败，禁止发布' }
```

核对隔离副本 `APP_VERSION` 仍等于 `$releaseVersion`，`$buildCommit` 是本次获批提交，且 `git status --short` 为空。依赖安装失败同样必须停止。本机无 Python/依赖问题不能以旧 EXE 冒充新构建。

脚本生成 `release/自动关推广-v<版本>/` 和同名 `.zip`，目录含 EXE、模板、README、HANDOFF、使用说明、SHA256SUMS。脚本不复制本机 data，也不复制 docs 目录；包内 README 中的发布指南相对链接应改从 GitHub 查看。它拒绝覆盖同名发布目录/ZIP。只有完整包，没有增量包、补丁包或自动升级器。

<a id="github-release"></a>

## 5. 怎样上传 GitHub Release（以后发布时执行）

以下命令会真实写 GitHub，只有新版构建/安全审查完成且拥有发布授权时执行；此次交接只验证命令，没有执行该阶段。`gh` 从 GitHub CLI 官方发行获取，命令参数可用 `gh release create --help` 核对。

先审查 ZIP 结构、`SHA256SUMS.txt` 和版本，确保不含任何真实配置/Token/profile/日志/data。再生成 ASCII 名资产并确认两份 ZIP 的哈希相同：

```powershell
$localZip = "release\自动关推广-v$releaseVersion.zip"
$uploadZip = "release\guantuiguang-v$releaseVersion.zip"
if (Test-Path -LiteralPath $uploadZip) { throw '上传副本已存在，禁止覆盖' }
Copy-Item -LiteralPath $localZip -Destination $uploadZip -ErrorAction Stop
$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $localZip).Hash
$sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $uploadZip).Hash
if ($sourceHash -ne $sha256) { throw '两个 ZIP 哈希不一致' }
git status --short
git tag -a "v$releaseVersion" $buildCommit -m "Release v$releaseVersion"
if ($LASTEXITCODE -ne 0) { throw 'tag 创建失败，禁止发布' }
git push origin "v$releaseVersion"
if ($LASTEXITCODE -ne 0) { throw 'tag 推送失败，禁止发布' }
$notesFile = New-TemporaryFile
@("Windows 完整包；源码提交：$buildCommit", "ZIP SHA-256：$sha256", '只完成离线和隔离验证；真实账户业务未验收。') | Set-Content -LiteralPath $notesFile.FullName -Encoding UTF8
gh release create "v$releaseVersion" $uploadZip --repo nmrsz645-bit/guantuiguang --title "自动关推广 v$releaseVersion" --notes-file $notesFile.FullName --verify-tag
if ($LASTEXITCODE -ne 0) { throw 'Release 创建失败，先查远端状态再处理' }
gh release view "v$releaseVersion" --repo nmrsz645-bit/guantuiguang --json tagName,assets,url
```

不确定上传是否成功时，先读回 Release，不能直接重试覆盖。也可以网页 Releases → Draft a new release → 选择已推送的新 tag → 上传 ASCII ZIP → 填版本/提交/哈希/验证边界 → Publish release。测试产物必须标为 Pre-release，不得伪装成已验收正式版。

发布成功的标准是：远端 tag 解引用指向 `$buildCommit`、资产名/字节数/摘要正确，并能从 GitHub 下载。上传包失败时先保留既有 tag/资产并调查；不可强推、重打 tag、`--clobber` 覆盖附件或删除旧 Release。

<a id="manual-update"></a>

## 6. 下载验证、手工更新与回滚

当前正式资产：[guantuiguang-v1.2.1.zip](https://github.com/nmrsz645-bit/guantuiguang/releases/download/v1.2.1/guantuiguang-v1.2.1.zip)。大小 **15,344,589 bytes**，SHA-256：`f31d62561c653c70fe0394ee2ed172d660bc794790475e45360fd58954e78396`。

下面只下载到全新的临时目录并读哈希，不启动程序：

```powershell
$verifyDir = Join-Path $env:TEMP ('guantuiguang-verify-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $verifyDir | Out-Null
gh release download v1.2.1 --repo nmrsz645-bit/guantuiguang --pattern 'guantuiguang-v1.2.1.zip' --dir $verifyDir
if ($LASTEXITCODE -ne 0) { throw '下载失败' }
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $verifyDir 'guantuiguang-v1.2.1.zip')
```

新版发布后替换上述 tag/资产名并核对新版记录。解压后逐项核验清单哈希，隔离运行 EXE 自检，检查依赖、版本和退出；配置为空时应报告缺失，不能伪造账户取得绿色结果。

客户端更新是**手工安装完整包**：用户停止监控并关闭旧程序，在本机备份整个现有 data，旧程序文件另存 `app.previous`（手动备份，程序无自动回滚实现）；保留数据原件，校验新包后在已有数据位置更新程序文件。不得通过 Git 克隆覆盖用户安装目录。跨电脑应重新授权而非复制旧 data。

回滚用原先保留的已验证程序文件/完整包和兼容的数据备份。先在隔离副本验证配置保留、启停和数据兼容，再操作用户安装；关闭范围须获用户授权。当前 GitHub 只有 v1.2.1，没有已验证的前一版远端包可供回滚；没有完成真实客户机升级/回滚，不能声称这一步已验收。

## 7. 网站、OSS 与自动更新的边界

本仓库没有自动更新器、更新 manifest、OSS bucket/key、上传脚本、增量包或客户端更新命令。2026-11-01 只读核验共享下载站 `nmrsz645-bit/software-download-center` 的 `main/index.html` 没有“自动关推广”卡片、卡片 ID 或元数据映射；Pages 从该站 `main` 根目录构建。

因此发布本项目到 GitHub Release 不会更新网站，也不会给已安装用户自动升级。当前没有可写的本项目 OSS/catalog 对象或可执行的网站上传命令，不能套用其他产品的更新协议。

如未来单独增加网站入口，按共享 [网站指南](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#website)、[catalog 规则](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#catalog)、[客户端更新规则](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#client-update)、[验证/回滚](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#verify-rollback)、[凭据](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#credentials) 处理，并先确定本项目卡片 ID、index 改动和实际存储对象。共享指南不能替代这些缺失对象的设计与授权。本次没有修改网站、OSS 或生产配置。

## 8. 完成判定与后续工作

另一台电脑接手完成至少要记录：源码远端/分支/HEAD 和脏状态、Python/依赖版本、离线测试结果、入口路径、构建与包校验结果，以及未进行的真实账户验证。当前源码完整，不需要逆向 EXE；外部 Chrome、用户账户/OAuth 授权、网络条件与签名策略仍依赖目标电脑。

尚未验证真实登录/接口/关推广、无 Python 客户机完整安装、真实网络异常、Windows 启动项与完整 GUI 自动化；EXE 未代码签名。配置自检不会验证真实 Token 可用。异常时先读本机自检/monitor/crash 日志；守护进程可能重启失败的监控，不能将“后台进程存在”视为业务正常。下一位 Codex 先报告这些边界，再按用户具体修改任务继续。
