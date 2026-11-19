# 自动关推广：接手、构建、上架与用户选择更新

适用版本 1.3.0。源码 main、GitHub Release、OSS 不可变包、客户端清单和下载站分别核验；Git push 不等于客户端更新。真实推广监控不是发布测试的一部分。

当前发布的完整包大小、SHA、源码/网站提交和已执行/未执行检查见 [2026-11-19 验收](validation/2026-11-19-v1.3.0.md)。GitHub Release 的本次二进制附件上传网络超时，网页只标注发布说明与校验；不能假定备用附件已存在。

## 1. 新 Windows 电脑接手

```powershell
git clone --branch main https://github.com/nmrsz645-bit/guantuiguang.git C:\Projects\guantuiguang
Set-Location C:\Projects\guantuiguang
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tools tests 自动关推广
```

已验证环境 Windows x64 / Python 3.12.14 / PyInstaller 6.22.3。没有 py 时安装官方 Python 3.12（含 Tk/pip/启动器），或使用本机已核实的兼容 Python 路径创建 venv；不能复制旧 .venv。普通用户完整 EXE 包不需要 Python，真实平台登录需要 Chrome。源码 GUI 可用 `.\.venv\Scripts\python.exe tools\local_oceanengine_app.py`；其中 BAT 按钮仍可能选系统 Python。

已有源码目录先核对状态并保留别人修改。读取 README/HANDOFF/AGENTS；不要把 Codex 项目栏外层索引目录当源码根。真实配置/Token/浏览器登录态/DPAPI/日志/任务数据均不分发，新电脑自行配置和授权。

<a id="source-update"></a>
## 2. 源码更新

先修改、测试和审查本次明确文件，普通提交推送到本仓库；禁止 add .、强推或覆盖他人提交。远端有变化时先读差异正常整合。源码完整，不需要逆向 EXE。

```powershell
git fetch origin
git status --short
git diff --check
git log --oneline HEAD..origin/main
# 逐个 git add -- 本次已审查的源码/测试/文档；不要暂存配置或构建产物。
git diff --cached --name-only
git diff --cached --check
git commit -m "发布本次经验证的程序更新"
git push origin HEAD:main
```

本地分支不是 main 也必须确认目标 main 的 HEAD 未变化；被拒绝后不能强推。GitHub 身份/凭据由本人现有连接或官方交互登录配置。

<a id="build"></a>
## 3. 版本、完整包与离线验证

真实版本位置是 tools/desktop_oceanengine_app.py 的 APP_VERSION。新功能版本为 1.3.0；每次正式改版先同步版本和用户说明，同版本不同字节不能覆盖旧包。构建脚本自动生成 app/version.json 与两种清单，无需手填版本或哈希。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\build_desktop_release.py
.\.venv\Scripts\python.exe tools\verify_release.py release\guantuiguang-1.3.0-windows-x64.zip --manifest release\guantuiguang-1.3.0-latest.json --site-manifest release\guantuiguang-1.3.0-latest.js
Get-FileHash -Algorithm SHA256 release\guantuiguang-1.3.0-windows-x64.zip
```

构建必须在固定源码、全新输出目录/副本中进行。已有 release/自动关推广-v1.3.0 或完整 ZIP 会拒绝重建；不删除旧产物来重新发布。脚本通过当前解释器调用 PyInstaller，创建 app/自动关推广.exe 和根 Update-Guantuiguang.exe，ZIP 内只有安全文件白名单及 SHA256SUMS。发布源码、配置模板和文档，不带真实 data、授权、Chrome profile、日志或缓存。

只有完整 ZIP，没有增量/差分包。测试版用隔离目录与 loopback 测试清单，不能改正式清单来做升级测试。新候选须完成拒绝/稍后、断网、坏哈希、错误布局/版本、运行中拒绝替换、隔离自检、失败回退与数据保留验证。

## 4. 客户端和网站的真实对象

| 对象 | 固定合同 |
| --- | --- |
| Bucket / endpoint | luotuoruanjiangengx / oss-cn-beijing |
| 不可变 ZIP key | packages/guantuiguang/1.3.0/guantuiguang-1.3.0-windows-x64.zip，未来只替换两处版本 |
| 客户端 JSON | updates/guantuiguang/latest.json；productId、version、url、sha256、notes |
| 网站 JS | updates/guantuiguang/latest.js；window.GUANTUIGUANG_LATEST，字段 productId、version、sha256、fullPackageUrl |
| HTTPS origin | https://luotuoruanjiangengx.oss-cn-beijing.aliyuncs.com |
| app 元数据 | productId=guantuiguang、layout=app-v1、runtime_data=data、version=APP_VERSION |
| 网站卡片 | main/index.html 的 guantuiguang-version / guantuiguang-download |
| 网站源仓库 | https://github.com/nmrsz645-bit/software-download-center |

更新器只接受此产品固定 HTTPS JSON/ZIP 地址，无 query、fragment、凭据和重定向；版本必须三段数字，产品/哈希/布局错误即失败。安装互斥、事务日志和 app.previous 用于保留旧版；早期备份移入 .update-history，不被静默删除。更新只改 app，root/data 保留。根启动器/更新器不在自动替换范围，将来修复需完整包手动升级。

从 Start-App.cmd（或根 Update-Guantuiguang.exe）启动才能检查更新；app 内 EXE 直接运行会绕过检查。1.2.1 没有更新器，必须先手工下载一次新完整包；不能把新清单称为老用户已自动升级。

## 5. OSS 发布顺序与命令

先使用官方 Alibaba Cloud CLI 的 OAuth 登录，选择有该 bucket/产品目录权限的现有 profile。`tools/publish_oss_release.py` 仅刷新并使用临时 OAuth 凭据，不创建长期 Key、不改 ACL、不删除对象、不操作其他产品。

下面命令由操作者填写自己的 CLI 路径与 profile；不把凭据内容写入命令或源码。可先运行 --help，不触发上传。

```powershell
$aliyunCli = Read-Host '本机官方 aliyun.exe 绝对路径'
$publishProfile = Read-Host '本人已有的 OAuth profile 名称'
.\.venv\Scripts\python.exe tools\publish_oss_release.py --directory release --version 1.3.0 --stage package --dry-run
# 安全审查和隔离验证通过后，真实上传不可变包并从公网完整回下载验哈希。
.\.venv\Scripts\python.exe tools\publish_oss_release.py --directory release --version 1.3.0 --stage package --cli $aliyunCli --profile $publishProfile
# 上一步成功、回读与升级验收通过后才启用网站 JS，再启用客户端 JSON。
.\.venv\Scripts\python.exe tools\publish_oss_release.py --directory release --version 1.3.0 --stage manifests --cli $aliyunCli --profile $publishProfile
```

不可变 key 已存在时同哈希复用，不同哈希停止。403/授权失败不是“对象不存在”，禁止通过改 ACL 或扩权绕过。JSON/JS 替换前备份公开旧元数据并复核并发变化；新产品 key 使用禁止覆盖头。任一步失败，检查远端实际结果，不能只根据本地命令发送成功报告发布完成。

没有可用 OAuth 时可以由获授权用户在 OSS 官方控制台手工上传上述**同一 key**：先完整 ZIP → 公网回下载比对字节数/SHA → 再 latest.js → 再 latest.json。不得把整个安装目录或用户 data 上传。

<a id="github-release"></a>
## 6. GitHub Release 与下载站

GitHub Release 是源码/下载备用渠道，和客户端 OSS 清单分开。固定源码提交、测试通过后正常创建新 tag；不重写旧 tag，不覆盖旧附件。

```powershell
$version = '1.3.0'
$commit = git rev-parse HEAD
git tag -a "v$version" $commit -m "自动关推广 v$version"
git push origin "v$version"
gh release create "v$version" "release\guantuiguang-$version-windows-x64.zip" --repo nmrsz645-bit/guantuiguang --title "自动关推广 v$version" --notes-file release-notes.txt --verify-tag
```

release-notes.txt 由发布者写入真实提交、大小、SHA、入口、更新/数据保护和未验收项。网页也可选择已存在 tag、上传同一 ZIP。不要将测试或未公开的产物伪装成正式版。

网站只编辑本产品卡片和独立 JS 加载器，静态链接是清单失败时的兜底，不能改其他产品、CNAME 或 Pages 配置。JS 加载器校验 productId、三段版本、SHA 和由版本推导出的本产品 HTTPS 完整包 URL。网站 main 推送会发布 Pages，是用户要求上架时单独执行的生产动作；上传 ZIP 或清单不会自动修改静态 index。

从网站最新 main 的干净副本修改 index.html，显式暂存该文件，正常提交/推送后查询 Pages built，再读自定义域名实际页面；卡片显示版本和最终下载链接都必须匹配。共享规则见 [网站指南](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#website)、[客户端更新](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#client-update)、[凭据](https://github.com/nmrsz645-bit/software-download-center/blob/docs-cross-pc-handoff/docs/PUBLISHING.md#credentials)。本产品不依赖统一 catalog.json。

<a id="manual-update"></a>
## 7. 发布验证、手动过渡与回滚

```powershell
$url = 'https://luotuoruanjiangengx.oss-cn-beijing.aliyuncs.com/packages/guantuiguang/1.3.0/guantuiguang-1.3.0-windows-x64.zip'
$verifyDir = Join-Path $env:TEMP ('guantuiguang-verify-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $verifyDir | Out-Null
Invoke-WebRequest -Uri $url -OutFile (Join-Path $verifyDir 'full.zip')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $verifyDir 'full.zip')
Invoke-RestMethod -Uri 'https://luotuoruanjiangengx.oss-cn-beijing.aliyuncs.com/updates/guantuiguang/latest.json'
```

上面只下载包；客户端 JSON 的真实地址是 `https://luotuoruanjiangengx.oss-cn-beijing.aliyuncs.com/updates/guantuiguang/latest.json`，网站 JS 同路径 latest.js。对照候选记录检查产品、版本、ZIP 字节数和哈希，不从文件名猜版本。包内普通 --self-check 空配置失败是预期；升级器专用 --release-check --report 只检查运行依赖和版本，不检查账户。

手动从 1.2.1 过渡时停止旧监控并退出，先在**同一电脑**备份 data，保留旧 EXE，然后将新完整包的 root 启动器与 app 放到将继续使用的安装根，不能覆盖/替换其 data。另一台电脑应重新授权，不迁移旧 Token/profile。

新更新失败自动回退；需要手动回滚时保留当前 app、检查 app.previous 的版本和完整性，在隔离副本确认兼容后恢复旧程序。不要直接修改业务状态或删除账户数据。网站可以正常 git revert 本产品的错误卡片提交；清单回滚必须先确认旧完整包仍可用，恢复旧 JSON/JS 原文而不是删除版本包。

仍待实际用户另行验收：真实巨量登录/Token/接口/关闭动作、无 Python 的另一台电脑安装和业务状态跨版回滚。EXE 未代码签名，系统安全策略可能提示。不要把更新成功当作推广业务已成功。
