# 开发约定

## 不可误动的数据

不得删除、提交、重置或批量覆盖 `自动关推广\data`、`tokens`、Chrome profiles、login-pages、账号接口信息、日志、运行锁和用户的 `config.json`。这些内容包含每台电脑独立的授权、登录状态或运行历史。

## 修改原则

- 默认只修改源码、批处理入口、文档、`config.example.json` 和依赖声明。
- 发布/升级必须保留用户数据，并创建可回退的 `app.previous`。
- 任何新版本要先在隔离副本进行自检、启动、停止和配置保留验证。
- 先读取当前真实运行目录、配置路径和进程状态，再判断问题；不要根据目录名猜测。
- 外部 API、Token 刷新和浏览器自动化失败必须记录到日志，并使用有限次重试，不能无限重启。

## Git 规则

提交前必须运行 `git status --ignored` 与 `git diff --cached --name-only`，确认没有配置、Token、Chrome profile、日志或离线安装包进入暂存区。
