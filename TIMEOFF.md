# 自动关推广交接入口

本文件保留为历史交接入口，避免旧会话或脚本找不到文件；当前完整、可维护的交接内容已迁移至 [HANDOFF.md](HANDOFF.md)。

新会话的只读顺序：

1. 阅读 `TIMEOFF.md`、`README.md`、`AGENTS.md` 与 `HANDOFF.md`。
2. 在不改动文件的前提下执行：

   ```powershell
   git status --short
   git rev-parse HEAD
   git ls-remote origin refs/heads/main refs/tags/v1.2.1
   py -3 -m unittest discover -s tests -v
   ```

3. 本地与远程提交一致、测试通过且工作区状态已核实后，才按 README 配置或按 HANDOFF 构建/发布。

不要依据旧电脑路径、旧 Release 哈希或历史聊天恢复任何私密数据。`config.json`、Token、账户资料、浏览器 profile、日志、运行状态和本机构建产物均不属于 Git 交接内容。
