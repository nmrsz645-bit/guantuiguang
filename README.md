# 自动关推广

这是一个 Windows 本地程序：按配置读取巨量引擎投放账户的单元状态；当单元已满足二维码预览条件时，只关闭该单元开关，不删除单元，也不关闭项目。

## 新电脑首次使用

1. 复制整个发布文件夹，不要只复制某一个 `app` 子目录。
2. 运行 `首次安装.bat`。若本机没有 Python，会优先使用发布包内安装器；源码克隆没有安装器时会尝试通过 Windows `winget` 安装 Python。首次安装只会在 `自动关推广\config.json` 不存在时，从 `config.example.json` 创建初始配置，绝不覆盖已有配置。
3. 运行 `自动关推广本地程序.bat`，点击“账户配置”，填写投放账户 ID、千川 App ID、App Secret 和回调地址并保存。
4. 运行 `打开巨量登录.bat`，在每个主账户各自的专用 Chrome 窗口完成登录。
5. 将每个账户的授权信息放入 `自动关推广\账号接口信息`，再运行 `自动导入巨量账号授权.bat`；也可以运行 `写入巨量授权码.bat` 手动授权。
6. 运行 `一键自检.bat`，必须看到 `Errors: 0`。
7. 运行 `启动监控.bat`。

## 源码与用户数据

Git 仓库只保存代码、批处理入口、说明和示例配置。以下内容只留在每台电脑本地，绝不能提交或覆盖：

- `自动关推广\config.json`、Token、App Secret、账户授权文件
- `自动关推广\chrome-profiles`、`chrome-debug-profile`、`login-pages`
- `自动关推广\data`、日志、任务状态和运行锁
- `installers` 中的离线安装包

新电脑克隆代码后，需要重新执行首次安装、账户配置、登录和授权；不要从旧电脑复制配置、浏览器档案或 Token 到公开仓库。纯源码克隆不包含 `installers` 中的离线安装包；没有 Python 且无法使用 `winget` 的电脑，应使用完整发布包或由管理员安装 Python 3.12。

## 运行与排错

- 日志：`rizhi`、`自动关推广\rizhi`
- 配置：`自动关推广\config.json`，示例见根目录 `config.example.json`
- 依赖：`requirements.txt`
- 监控同一时间只能启动一份；先运行 `停止监控.bat` 再启动新的实例。

## 自动化测试

测试只校验离线规则，不会访问巨量接口、不启动 Chrome，也不会读取或改动真实账号、Token、浏览器登录资料和推广状态。

在项目根目录双击 `run-tests.bat`，或运行：

```powershell
py -3 -m unittest discover -s tests -v
```

当前覆盖：账户文本解析、账户导入后的旧账户停用规则、并发浏览器分配、Token 失效判定、单元状态判定、关闭保护、接口响应解析，以及 72 小时日志清理规则。

## 无黑框 EXE 发布

开发人员在已安装 Python 和 PyInstaller 的电脑上双击 `build-desktop-release.bat`。它会生成 `release\自动关推广-v<版本号>\自动关推广.exe`：这是无需 Python、双击后不显示命令窗口的桌面版。

构建前先安装 PyInstaller：

```powershell
py -3 -m pip install pyinstaller
```

发布给普通用户时，复制整个生成的发布文件夹；不要只复制 EXE。用户的 `data` 文件夹包含配置、Token、Chrome 登录资料和运行状态，升级时必须保留。

## Git 交接

本地初始化后可执行：

```powershell
git status
git add .
git commit -m "交接当前自动关推广源码"
```

要同步到另一台电脑，还需要一个用户自己的空 GitHub 仓库地址，再配置 `git remote add origin <仓库地址>` 和 `git push -u origin main`。未确认仓库地址前，不会自动上传任何内容。
