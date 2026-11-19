# 自动关推广 v1.3.0

Windows 本地桌面程序：检测巨量引擎投放账户当天的单元，满足二维码预览条件后，按用户允许的范围关闭对应单元开关；不删除单元、不关闭项目。当前不提供账户余额查询。

v1.3.0 新增网站下载与**启动前由用户选择更新**。业务监控和账户授权逻辑不变。维护者先读 [HANDOFF](HANDOFF.md)、[发布指南](docs/RELEASE-GUIDE.md) 和 [AGENTS](AGENTS.md)。

## 下载与第一次启动

在 [下载站](https://download.luotuoqiluotuozhaoma.com/) 找到“自动关推广”，下载完整 Windows ZIP 并解压。也可从 [GitHub Releases](https://github.com/nmrsz645-bit/guantuiguang/releases) 取得同一完整包。

**从根目录 `Start-App.cmd` 启动**，也可以双击根目录 `Update-Guantuiguang.exe`。不要只复制 EXE 或直接运行 `app/自动关推广.exe`，后者会跳过启动前更新检查。完整包已包含 Python，真实浏览器登录仍需要 Google Chrome。

安装目录结构：

```text
Start-App.cmd                 日常入口
Update-Guantuiguang.exe        检查更新、提示用户、校验与回退
app/自动关推广.exe            桌面程序
app/version.json              产品、版本、布局合同
data/                         本机配置、Token、Chrome 登录态与运行资料
app.previous/                 更新时保留的上一版程序
```

`data` 在本机使用时创建，发布包不包含它。解压后的顶层文件夹为 `自动关推广-v1.3.0`。v1.2.1 没有更新入口，必须首次手动取得 v1.3.0 完整包；旧版不会凭空自动升级。在同一台电脑保留已有 data 前先停止旧程序并备份，不能从其他电脑复制 Token 或浏览器资料。

## 更新如何工作

从日常入口启动后检查关推广专属 HTTPS 清单。发现更高版本提示“现在更新吗”：选择是才下载，选择否继续当前版本。下载后检查产品/版本、SHA-256、安全 ZIP 布局和新程序隔离自检，随后只替换 `app`。

- 断网、哈希错误、损坏包、自检或替换失败时保留/恢复可用旧版；同版或更低版不替换。
- 有此安装的程序进程运行时不进行更新。先正常停止监控并关闭窗口，再从日常入口启动。
- 配置、授权、Chrome profile、日志与状态位于根目录 `data`，更新不操作它。
- 上一版 `app.previous` 和更早的 `.update-history` 会保留；测试/下载临时目录也保留以便排查，会占用额外磁盘空间，未经许可不要自动清理。
- 根启动器和更新器不自动替换；将来若它们需要修复，应重新取得完整包。

## 配置与实际操作

1. 打开界面“账户配置”，填写本人获授权的投放账户 ID、App ID、App Secret 和回调地址。应用配置来自用户有权限的巨量应用管理页面。
2. “打开巨量登录”，在各账户专用 Chrome 登录；再“写入授权码”或“导入账户授权”。OAuth code/Token 均在本机取得。
3. “一键自检”通过后，只有用户明确允许才“启动监控”；“停止监控”停止本程序及专用浏览器。关闭管理窗口也会停止相关进程。

模板 `config.example.json` 默认账户 `enabled: false`，但 `dry_run: false`、`allow_close: true`；启用账户后不能认定是只检测。有账户的只检测需在本机配置设 `dry_run: true` 或取消“允许自动关闭推广”。`--no-close` 只属于监控 Python 脚本，不能传给 EXE 当作保护开关；只检测仍会访问平台。

EXE 配置为安装根 `data/config.json`；源码模式为 `自动关推广/config.json`。不要混淆数据根或覆盖现有配置。真实配置、Secret、Token、Cookie、浏览器 profile、账号文本、日志及运行资料不得进入 Git/Release。

## 排错与验证边界

| 情况 | 操作 |
| --- | --- |
| 没有更新提示 | 从 Start-App.cmd 启动；同版本无提示，断网继续旧版。查看根 logs/Update-App.log。 |
| 更新入口无启动结果 | 查看 logs/Update-App.log；锁/已有进程为退出码 5，缺少安全可用程序为 6。不要直接删锁或 app.previous。 |
| Chrome 未找到 | 安装 Chrome 后重跑一键自检。 |
| 授权失效 | 在对应专用 Chrome 重新登录/授权，不能复制他人 Token。 |
| 配置自检 | EXE 成功显示“自检通过，可以启动监控。”；源码 BAT 输出 Errors: 0。配置自检不验证真实 Token。 |

隔离 `--release-check --report <新文件>` 检查版本、依赖和 Tcl，不读账户或启动监控；普通 `--self-check` 会检查本机配置，空配置时失败是预期结果。生产监控、真实登录/接口和实际关闭推广均需用户专门指定账户验收；离线测试和更新验证不代表业务验收。

## 开发

本轮构建验证环境为 Windows x64、Python 3.12.14、PyInstaller 6.22.3，依赖放在项目 `.venv`；无需 Node/npm 或 .NET SDK。源码 GUI 是 `tools/local_oceanengine_app.py`，桌面打包入口是 `tools/desktop_oceanengine_app.py`。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tools tests 自动关推广
.\.venv\Scripts\python.exe tools\local_oceanengine_app.py
```

源码 GUI 部分按钮经 BAT 使用系统 `py -3`，不自动选 `.venv`。纯代码检查不要启动监控或读取真实账户。构建、上传 ZIP、启用客户端清单和网站卡片分别执行，详见 [发布指南](docs/RELEASE-GUIDE.md)。
