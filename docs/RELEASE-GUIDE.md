# 新 Windows 电脑接手、更新与网站发布指南

本指南只记录已由本仓库脚本和 GitHub 状态核实的流程。它不授权启动监控、调用巨量接口、关闭推广、上传 OSS、修改下载站或操作另一台电脑。

## 1. 仓库、分支与版本关系

正式仓库为 `https://github.com/nmrsz645-bit/guantuiguang.git`，默认分支为 `main`。新 Windows 电脑应只克隆源码：

```powershell
git clone https://github.com/nmrsz645-bit/guantuiguang.git C:\Projects\guantuiguang
Set-Location C:\Projects\guantuiguang
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main refs/tags/v1.2.1
```

正式桌面版本是 GitHub Release tag `v1.2.1`；应用版本唯一来源是 `tools/desktop_oceanengine_app.py` 的 `APP_VERSION = "1.2.1"`。`main` 可以包含仅文档修订且比 tag 更新的提交，这不会自行改变 EXE 版本。发布候选必须先在隔离副本通过验证，再创建新的、与 `APP_VERSION` 一致的 tag；仓库没有测试分支、测试 Release 或“测试包”脚本。未打 tag 的 `main` 只可作为开发/验证源码，不能宣称为正式可分发版本。

## 2. 新电脑环境与接手

### 依赖与离线验证

- Windows 10/11、Git、Python 3.12 或 3.13；本项目已验证的构建环境为 Python 3.13.15 与 PyInstaller 6.22.2。
- `requirements.txt` 的准确版本下限为 `requests>=2.31`、`websocket-client>=1.8`、`python-dotenv>=1.0`；PyInstaller 不在 requirements 中，构建时单独安装。
- Google Chrome 仅在用户实际登录/监控时需要；离线单元测试不需要 Chrome、账户或网络接口。

```powershell
py -3 --version
py -3 -m pip install -r requirements.txt
py -3 -m pip install pyinstaller
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q .
```

也可在源码根目录运行 `首次安装.bat`。它实际调用 `tools/run_py.bat` 和 `tools/bootstrap_oceanengine_only.py`：只有当 `自动关推广\config.json` 不存在时才由 `config.example.json` 创建模板，并可能使用 `winget` 安装 Python 或用 pip 安装依赖。它不是离线保证，也不应在未经许可的企业设备上假定可安装系统软件。

### 能迁移与不能迁移的数据

Git 只迁移源码、批处理入口、测试、示例配置与文档。不得复制、提交、打包或公开以下本机数据：

- `自动关推广\config.json`、`tokens\`、`账号接口信息\`；
- `chrome-profiles\`、`chrome-debug-profile\`、`login-pages\`；
- `data\`、日志、锁文件、`installers\`、旧 `release\`/`dist\`/`build\` 产物。

浏览器登录态不可作为可分发资料；Windows DPAPI 保护的凭据即使存在也可能绑定到原用户/机器，不能作为跨电脑迁移方案。当前源码不包含 DPAPI 导出/导入工具，因此新电脑必须由用户在本机完成账户配置、Chrome 登录和授权。

## 3. 版本、完整包、哈希与正式发布

1. 仅在计划发布新版本时修改 `tools/desktop_oceanengine_app.py` 中的 `APP_VERSION`；不能为了重新上传同一包而重写已有 tag。
2. 在干净隔离副本运行第 2 节的离线验证，然后运行 `build-desktop-release.bat`。该批处理实际调用 `tools/build_desktop_release.py`。
3. 现有脚本只生成完整包，没有增量/差分包、补丁包或升级器：
   - 本地完整目录：`release\自动关推广-v<版本>\`；
   - 本地完整 ZIP：`release\自动关推广-v<版本>.zip`；
   - 文件夹内有 EXE、`config.example.json`、README、HANDOFF、`使用说明.txt` 和 `SHA256SUMS.txt`。
4. 构建脚本拒绝覆盖同版本目录或 ZIP。计算 ZIP 哈希并核对包内清单：

   ```powershell
   Get-FileHash -Algorithm SHA256 'release\自动关推广-v<版本>.zip'
   Get-Content 'release\自动关推广-v<版本>\SHA256SUMS.txt'
   ```

5. 审查 ZIP 不含真实 `config.json`、Token、Cookie、Chrome profile、账号文本、日志、`data\`、`.env` 或个人资料后，创建新的 tag 和 GitHub Release，再上传 ZIP。GitHub Release 的公开资产名采用 ASCII `guantuiguang-v<版本>.zip`；ZIP 内顶层目录仍为 `自动关推广-v<版本>`。

当前 `v1.2.1` 正式附件是 `guantuiguang-v1.2.1.zip`，其 SHA-256 以该 Release 页面和 Release 说明为准。Git push 只同步源码；它不等于客户端更新、OSS 上传或下载站更新。

## 4. 客户端更新的真实机制

本项目**没有**自动更新代码、下载 manifest、OSS bucket/key、增量包、版本检查接口或客户端更新命令。源码搜索仅发现 PyInstaller 完整包构建和 GitHub Release 分发。

因此，当前唯一真实的客户端更新步骤是手工下载对应 GitHub Release 的完整 ZIP，校验 SHA-256，备份并保留原安装的 `data` 文件夹，再用新文件夹中的 EXE 替换程序文件。不要把新包解压到旧 `data` 上方，也不要用 Git 克隆覆盖用户数据。

发布后只读核验可使用：

```powershell
git ls-remote https://github.com/nmrsz645-bit/guantuiguang.git 'refs/tags/v1.2.1^{}'
gh release view v1.2.1 --repo nmrsz645-bit/guantuiguang --json tagName,assets,url
```

`gh` 仅用于发布者的 GitHub 验证；普通用户不需要安装它。下载后应在隔离目录运行 `自动关推广.exe --self-check`，预期未配置账户时会报告缺少配置且不启动监控；有用户配置时，须先检查自检输出再决定是否运行。

## 5. 下载站与共享发布指南

截至本指南核验时，下载站仓库 `nmrsz645-bit/software-download-center` 的 GitHub Pages 源是 `main` 根目录 `index.html`；其中没有本项目的静态卡片、卡片 ID、项目 manifest 或运行时更新元数据。该站当前的 `updates/` 数据只覆盖其他产品，不能据此推导本项目的 OSS key、catalog 字段或发布命令。

因此本项目目前没有下载站发布步骤；不要编造 OSS 上传、catalog 修改、HTML 卡片 ID 或客户端自动更新协议。若后续单独添加网站卡片，网站维护者应以共享指南的 [website](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#website)、[catalog](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#catalog)、[client-update](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#client-update)、[verify-rollback](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#verify-rollback) 与 [credentials](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#credentials) 为通用约束；本项目仍需明确自己的新卡片 ID、静态 `index.html` 改动、外部 catalog 对象及其字段后才能执行。

本次检查时该仓库的 `docs-cross-pc-handoff` 分支尚不存在，所以上述链接是等待网站更新会话发布后的协作入口，不是已验证可读的项目发布流程。本项目本轮不会写该仓库、不会上传 OSS，也不会部署 Pages。

## 6. 发布后验证与回滚

1. 从 GitHub Release 重新下载资产，核对 ZIP SHA-256、`SHA256SUMS.txt`、资产名/大小、tag 指向和 `APP_VERSION`。
2. 在隔离目录测试解压结构和 `--self-check`；不得用真实账户自动执行监控或关闭动作作为发布验证。
3. 升级前备份用户本机 `data`，升级后确认配置仍在原位置、没有将 Token/profile 混入新包。
4. 可行回滚是下载一个先前已验证的完整 GitHub Release，恢复对应程序文件并保留同一份 `data`。当前 GitHub 只存在 `v1.2.1`，没有可供本项目验证的先前 Release；不要删除或重写现有 Release/tag 来伪造回滚测试。

## 7. 权限与凭证

- 源码推送、tag 和 Release 发布需要用户自己的 GitHub 仓库写入权限。发布者可用 `gh auth status` 检查 GitHub CLI 的 `github.com` 登录状态；令牌由操作系统凭据存储管理，不写入仓库、文档、脚本或 `.env`。
- 本项目没有已核实的 OSS 凭证配置名、bucket/key 或网站 catalog 凭证；在网站卡片和外部对象实际设计完成前，不能猜测或创建这些凭证。
- 巨量 App ID、App Secret、OAuth code、Token 和 Chrome 登录资料只由实际账户所有者从其授权的管理页面在本机取得，永不进入 GitHub Release 或项目文档。

## 8. 已知缺项与未验证流程

- 未进行真实巨量登录、授权、接口读取或关闭推广；离线测试不能替代端到端验收。
- 未在无 Python 的全新 Windows 设备完成 `v1.2.1` Release 的完整安装/升级回归。
- 未进行 EXE 代码签名；Windows SmartScreen、杀毒软件和企业策略可能影响安装/启动。
- 没有本项目的自动更新、增量更新、OSS 发布、下载站卡片或外部 catalog 实现；这些必须先有实际源码/对象设计和独立授权，不能从本指南推断。
