# 自动关推广

这是一个 Windows 本地程序：按配置读取巨量引擎投放账户的单元状态；当单元已满足二维码预览条件时，只关闭该单元开关，不删除单元，也不关闭项目。

## 新电脑首次使用

1. 复制整个发布文件夹，不要只复制某一个 `app` 子目录。
2. 运行 `首次安装.bat`，安装 Python 依赖并创建运行目录。
3. 运行 `打开巨量登录.bat`，在每个主账户各自的专用 Chrome 窗口完成登录。
4. 将每个账户的授权信息放入 `自动关推广\账号接口信息`，再运行 `自动导入巨量账号授权.bat`；也可以运行 `写入巨量授权码.bat` 手动授权。
5. 运行 `一键自检.bat`，必须看到 `Errors: 0`。
6. 运行 `启动监控.bat` 或 `自动关推广本地程序.bat`。

## 源码与用户数据

Git 仓库只保存代码、批处理入口、说明和示例配置。以下内容只留在每台电脑本地，绝不能提交或覆盖：

- `自动关推广\config.json`、Token、App Secret、账户授权文件
- `自动关推广\chrome-profiles`、`chrome-debug-profile`、`login-pages`
- `自动关推广\data`、日志、任务状态和运行锁
- `installers` 中的离线安装包

新电脑克隆代码后，需要重新执行首次安装、登录和授权；不要从旧电脑复制配置、浏览器档案或 Token 到公开仓库。

## 运行与排错

- 日志：`rizhi`、`自动关推广\rizhi`
- 配置：`自动关推广\config.json`，示例见根目录 `config.example.json`
- 依赖：`requirements.txt`
- 监控同一时间只能启动一份；先运行 `停止监控.bat` 再启动新的实例。

## Git 交接

本地初始化后可执行：

```powershell
git status
git add .
git commit -m "交接当前自动关推广源码"
```

要同步到另一台电脑，还需要一个用户自己的空 GitHub 仓库地址，再配置 `git remote add origin <仓库地址>` 和 `git push -u origin main`。未确认仓库地址前，不会自动上传任何内容。
