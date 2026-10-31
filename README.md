# 自动关推广

Windows 本地桌面程序。它根据本机配置读取巨量引擎投放账户中的单元状态；仅当单元满足二维码预览条件时，才会尝试关闭该单元的投放开关。它不会删除单元，也不会关闭项目。

当前正式源码版本为 **1.2.1**。完整的维护交接信息请先读 [HANDOFF.md](HANDOFF.md)，协作与敏感数据规则见 [AGENTS.md](AGENTS.md)。

> 安全边界：本仓库和 Release 不含账户 ID、App Secret、Token、Cookie、浏览器登录资料、真实配置、日志或运行状态。程序只有在本机账户已启用、授权完成，并且配置允许关闭时才可能改变投放状态。首次验证请保持只检测模式，或不要启动监控。

## 普通用户：从 Release 安装

1. 在 GitHub Release 下载完整的 `自动关推广-v1.2.1.zip`，解压整个文件夹。不要只复制 `自动关推广.exe`。
2. 确认 Windows 已安装 Google Chrome。EXE 自带 Python 运行时，不需要单独安装 Python。
3. 双击 `自动关推广.exe`，在“账户配置”中填写自己拥有并获授权的投放账户 ID、App ID、App Secret 和授权回调地址后保存。
4. 使用“打开巨量登录”在每个主账户的专用 Chrome 窗口完成登录；再使用“写入授权码”或从本机 `账号接口信息` 导入授权。
5. 运行“一键自检”，仅在显示 `Errors: 0` 后，才考虑启动监控。

首次运行会在 EXE 同级的 `data` 文件夹保存本机配置、Token、Chrome profile、日志和运行状态。升级时保留整个旧 `data` 文件夹；不要将它提交到 Git、上传公开链接或与其他电脑混用。

## 开发者：从源码运行

### 环境

- Windows 10/11
- Git
- Python 3.12 或 3.13（`py -3 --version` 可确认）
- 网络用于安装 Python 依赖；Chrome 仅在实际登录或监控时需要

在仓库根目录执行：

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q .
```

这些测试只覆盖离线规则：不会访问巨量接口、不会启动 Chrome、不会读取本机账户文件，也不会关闭推广。

首次在源码目录配置本机环境时，可运行 `首次安装.bat`。它会在 `自动关推广\config.json` 不存在时由 `config.example.json` 创建初始模板；已有配置不会被覆盖。该流程可能通过 `winget` 安装 Python 或通过 pip 下载依赖，因此不应在没有网络/安装权限的环境中假定它能成功。

### 常用入口

| 入口 | 用途 | 是否会触发实际监控 |
| --- | --- | --- |
| `自动关推广本地程序.bat` / `自动关推广.exe` | 打开本地管理界面和账户配置 | 否 |
| `打开巨量登录.bat` | 为已启用主账户启动专用 Chrome 登录窗口 | 否，但会打开浏览器 |
| `写入巨量授权码.bat` | 粘贴 OAuth 回调链接/授权码 | 否 |
| `自动导入巨量账号授权.bat` | 从本机账号文本目录导入授权 | 否 |
| `一键自检.bat` | 校验依赖、配置、端口和目录 | 否 |
| `启动监控.bat` | 启动守护进程与检测循环 | **是** |
| `停止监控.bat` | 发送停止信号并结束本程序启动的监控 | 会停止本程序子进程 |
| `一键状态面板.bat` | 读取锁、日志和最近状态 | 否 |

## 配置与安全

模板文件是 `config.example.json`；实际文件必须是本机未跟踪的 `自动关推广\config.json`。每个主账户需要独立且有效的：

- 投放账户 ID；
- 巨量应用的 App ID、App Secret 和已登记的回调地址；
- 专用 Chrome 调试端口和 profile 目录；
- 本机 Token 文件路径。

请只从本人有权限的巨量引擎/应用管理页面获取这些值。不要猜测、生成或在 Issue、Commit、Release 说明、截图或日志中粘贴任何 Secret/Token。模板中主账户默认 `enabled: false`，用于阻止未配置时运行；启用账户前先检查账户 ID 和端口均不重复。

`dry_run: true` 或命令行 `--no-close` 代表只检测不关闭。实际关闭还受已启用账户、`allow_close`、有效授权及二维码预览条件共同限制；这些保护不是生产账户验收的替代品。

## 常见问题

| 现象 | 先检查什么 |
| --- | --- |
| 找不到 Python | 重新运行 `首次安装.bat`，或安装 Python 3.12/3.13 并确保 `py -3` 可用；源码克隆不含离线 Python 安装器。 |
| `Chrome not found` | 安装 Google Chrome 后重新运行自检。 |
| 自检不是 `Errors: 0` | 逐项修复缺失依赖、未启用/不完整账户、重复投放账户 ID 或重复调试端口；不要通过伪造 Token 绕过检查。 |
| 提示需要重新授权或 Token 失效 | 重新打开对应主账户的专用 Chrome，再通过授权入口写入本机授权；不要复制其他电脑的 Token。 |
| 监控已在运行/无法停止 | 先用 `停止监控.bat`，再检查 `自动关推广\data` 的锁与 `自动关推广\rizhi` 日志；不要直接删除 data、Token 或 profile。 |
| 升级后找不到历史状态 | 新版 EXE 必须与原 `data` 文件夹一起使用；先备份该文件夹，再替换程序文件。 |

日志位于 `rizhi` 或 `自动关推广\rizhi`；程序的临时日志保留策略为 72 小时。排错时请保留原始日志和配置的脱敏副本，不要上传真实授权资料。

## 构建与发布

在隔离、干净的源码副本中构建：

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m pip install pyinstaller
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q .
build-desktop-release.bat
```

构建会生成：

- `release\自动关推广-v<版本>\`：EXE、配置模板、README、HANDOFF、使用说明和 `SHA256SUMS.txt`；
- `release\自动关推广-v<版本>.zip`：上述文件夹的可上传 Release 附件。

构建拒绝覆盖同版本的文件夹或 ZIP。发布新版本应先修改并审查应用版本、在全新副本构建和测试、检查 ZIP 内容不含私有数据，再创建新的 Git tag/Release；绝不重写旧 tag、覆盖旧附件或用用户 `data` 文件夹打包。
