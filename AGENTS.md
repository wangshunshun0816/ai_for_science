# Danus-AI 项目执行约束

依据：用户于 2026-11-07 明确指定的开发前约束；业务要求见 docs 中大方案 v1.2、落地开发指南及角色规格 v0.2。

## 上游基线

- `~/upstream/Danus`（`/home/wangshunshun/upstream/Danus`）是 U-01 的 WSL 原生第三方只读源码基线。该克隆已移除写权限，作为项目审计输入。`D:\Danus_Coding\reference\Danus` 保留为历史副本，停止用于日常审计。
- 固定上游提交：`6d92e8d415933ca2ef52fd1a4da73fdfcd418f1c`。
- A0 于 2026-11-07 批准扩大 P0-1 的只读范围。在路径盘点、行数统计和 LICENSE 阅读之外，可以阅读 `bin/`、`agents/` 及大方案 3.4 所列文件的内容，可以查询 `git --no-optional-locks status --porcelain`、`git rev-parse`、`git log -1 --format="%H %cI"`，并对单个文件计算 SHA-256。不得执行上游代码或测试。
- 两份上游副本均保持只读。不得改文件、执行 `git pull`、执行上游代码或测试、安装依赖或生成缓存。不得把整个目录复制进本项目。
- 禁止 `pip install -e`、`uv pip install -e` 或其他可编辑依赖/路径注入指向该目录。
- P1 每项复用须显式选择并登记：受控迁移、隔离保留、关闭。
- 受控迁移：选择具体文件迁入 `danus_ai/` 后改造，保留版权/许可声明，在修改文件中显著标注修改，登记来源提交、源路径、目标路径及变更。
- 隔离保留：固定 commit，以独立服务通过端口提供只读引用/状态；只读基线不是运行时可写数据目录。数学核按此处理，经验侧无数学图写权。
- 关闭：明确不采用；数学证明搜索的 Agent 主体不进入首版。
- `THIRD_PARTY_NOTICES.md` 和分发许可证随实际采纳情况更新；不得宣称尚未完成的移植或验证已通过。

## Python 与运行存储

- 项目使用 CPython 3.12；不因本机默认解释器为 3.14 而切换基线。
- `.python-version` 目前限制到 3.12 系列；P1 验证安装后固定实际补丁版本、依赖锁和镜像 digest。
- Windows Python 用于允许的纯契约/路径兼容检查，不能代替 Linux 运行验收。
- 正式控制服务运行在 Linux；Windows 开发采用 WSL2 Linux 文件系统。
- `control.db` 及 WAL/SHM 文件不得位于 Windows 盘、`/mnt/c`、`/mnt/d`、其他 Windows 共享挂载或网络盘；UNC 只作 Windows 编辑访问入口，数据库由 WSL 内的 Linux 进程直接打开。
- 权威开发 checkout 为 Ubuntu ext4 上的 `/home/wangshunshun/danus-ai`。Windows 可经 `\\wsl.localhost\Ubuntu\home\wangshunshun\danus-ai` 编辑。项目的 Git、uv 和 Python 命令在 WSL 内执行。
- `D:\AI_for_science` 为只读归档副本，后续提交在 WSL checkout 进行。
- D-02 已确认本地 SQLite/WAL 为唯一生产后端。数据库尚未创建。建库前核对数据库、WAL/SHM、制品和备份的实际路径、文件系统与权限。

## 实施与验收

- 按 P0–P6 工作包推进；设计决定、工程完成、效果证据分别记录。
- 不把文档中的示例预算当实际付费授权，不把脚本或 mock 当真实角色资格。
- 阶段验收按各自交付证据和 A0 记录判断。
