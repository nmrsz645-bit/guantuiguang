# 自动关推广：维护与跨电脑交接

当前功能版本 **1.3.0**。代码仓库 `https://github.com/nmrsz645-bit/guantuiguang.git`，正式开发分支 main；提交/Release 状态以远端实时结果为准。发布命令与对象合同只维护在 [docs/RELEASE-GUIDE.md](docs/RELEASE-GUIDE.md)，用户使用见 [README](README.md)，不可误动数据规则见 [AGENTS](AGENTS.md)。

## 另一台 Codex 先做什么

1. 取得完整 main 源码；已有目录先检查 `git status --short`、暂存区、分支、HEAD 和远端，不覆盖原件。
2. 阅读本文件、README、发布指南和 AGENTS。不要凭旧电脑的绝对路径寻找源码或凭据。
3. 创建本机 `.venv`，装 requirements 和 requirements-build，执行离线单元测试/编译；新机器必须自己验证。
4. 开发使用 `tools/local_oceanengine_app.py`；打包使用 `tools/build_desktop_release.py`。普通用户从完整包根 Start-App.cmd 启动。
5. 各电脑独立配置、Chrome 登录和 OAuth 授权；不复制旧电脑私有配置、Token、浏览器/DPAPI 登录态、日志与运行资料。

## 用途、架构与关键模块

业务流：本机账户配置/授权 → 独立 Chrome 和账户分配 → 当日单元读取 → 打开状态/二维码预览判断 → 只检测或关闭该单元 → 本机状态与日志。

| 文件 | 修改入口 |
| --- | --- |
| tools/local_oceanengine_app.py | 源码管理窗口与 BAT 入口；源码数据根为自动关推广目录。 |
| tools/desktop_oceanengine_app.py | 无控制台 EXE、后台服务；1.3.0 的 EXE 位于 app，数据在安装根 data。 |
| 自动关推广/monitor_oceanengine_units.py | 巨量读取/二维码/关闭规则、状态、日志、授权失败处理。 |
| 自动关推广/main_accounts.py、import_account_texts.py | 主账户规范化、浏览器分配、文本账户/授权导入。 |
| tools/account_config_ui.py、config_validation.py | 配置界面及账户/端口/投放 ID 校验。 |
| tools/monitor_oceanengine_supervisor.py | 源码模式守护进程；业务异常重启与有限重试仍需持续审查。 |
| Start-App.cmd、tools/update_client.py | 启动前用户选择更新、固定产品清单、安全解包、自检、事务恢复、备份回退。 |
| tools/build_desktop_release.py | 构建桌面 EXE 和独立更新 EXE，组完整 ZIP、内部哈希清单、候选 JSON/JS。 |
| tools/verify_release.py | 离线核对精确安全文件集合、配置模板、ZIP/内部哈希和两种清单一致性。 |
| tools/publish_oss_release.py | 分阶段上传本产品不可变包和 JSON/JS，公网回下载核验；不改 ACL/其他产品。 |
| tests/test_update_client.py | 稍后/断网/坏哈希/错产品版本/恶意 ZIP/锁/失败回退/数据保留。 |

## 版本与安装合同

应用版本唯一位置：`tools/desktop_oceanengine_app.py` 的 APP_VERSION。构建脚本据此生成 app/version.json 与两个候选清单。元数据固定 `productId=guantuiguang`、`layout=app-v1`、`runtime_data=data`。更新只替换 app，根 Start-App.cmd/Update-Guantuiguang.exe 不自动升级。

1.2.1 的正式 tag 是 `v1.2.1`，对应 `7022e034e10dfbcf498caf5b6670c2b02a338e0f`；该版本无更新器。首次手工取得新完整包后才拥有后续更新能力，不能宣称 1.2.1 会自动接收 1.3.0。旧 Release 保留，禁止覆盖同版本不同字节。

## 开发、测试和构建

本轮兼容环境 Python 3.12.14、PyInstaller 6.22.3；运行依赖见 requirements.txt，构建/发布依赖见 requirements-build.txt。没有用户凭据也可运行离线测试。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tools tests 自动关推广
.\.venv\Scripts\python.exe tools\build_desktop_release.py
```

构建输出：release/自动关推广-v1.3.0、guantuiguang-1.3.0-windows-x64.zip、guantuiguang-1.3.0-latest.json/.js。不得在用户安装目录打包。目录/ZIP 已存在时构建拒绝覆盖；保留旧产物，在全新副本构建。

## 发布和网站

网站为 download.luotuoqiluotuozhaoma.com；网站源仓库 nmrsz645-bit/software-download-center 的 main/index.html。本产品卡片 guantuiguang-version / guantuiguang-download，从 window.GUANTUIGUANG_LATEST 刷新。产品专属 OSS 路径与字段详见发布指南。

严格顺序：源码/测试固定 → 构建/隐私审查 → 上传不可变 ZIP → 公网完整回下载哈希 → 隔离升级/拒绝/失败回退验证 → 网站 JS → 客户端 JSON → 网站卡片 → 网页与下载读回。Git push、GitHub Release、OSS 清单、网站 Pages 是不同动作，不可互相替代。

CLI OAuth 临时凭据由操作者在官方 CLI 配置；脚本只读本机选定 profile 并在进程内使用，不能提交 .aliyun 配置或凭据值。GitHub 使用现有授权连接或 Git Credential Manager，不扩展权限、不强推。

## 安全数据和真实验收边界

实际 App ID/App Secret/回调地址来自用户自己的巨量应用页面，投放账户 ID 来自获授权账户，Token 在专用 Chrome 完成本机 OAuth。模板账户禁用，但 dry_run=false、allow_close=true；有账户测试要明确打开只检测，不能误认为模板默认关闭动作被永久禁止。

必须保护：真实 config、tokens、Chrome profiles、账号接口文本、data、日志/锁、installers、release/dist/build、app.previous、历史备份。更新器对 root/data 不读写，不做配置迁移；同机升级前备份原 data。源程序和发布 EXE 的数据根不同。

已有历史基线：2026-10-31 v1.2.1 的 18 项离线测试、GUI 子系统构建与无配置自检；2026-11-01 之后曾仅修订文档。1.3.0 新增更新模块后的测试和真实 EXE 隔离升级应单独记录在发布验收文件，不引用旧结果代替。

仍未验收：真实巨量登录、授权、接口读取、实际关闭推广；账户余额功能未实现。无 Python 的另一台完整 Windows 客户机安装、代码签名、企业安全策略、真实业务网络异常仍待单独验证。配置自检不验证 Token 是否实际可用。更新日志为根 logs/Update-App.log；业务日志在 data/rizhi；避免把账号/Token 随日志公开。

本地测试/失败下载和旧备份保留会占用磁盘，不能默认删除它们。根更新器/启动器本身若需改版须手工替换完整包；app.previous 恢复只针对程序，不代表业务状态可跨版回退。
