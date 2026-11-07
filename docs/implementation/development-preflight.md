# 开发前基线记录

日期：2026-11-07。本记录细化用户本次要求，不改写原设计文档，不表示 P0 或 P1 已整体验收。

## 仓库

已在 `D:\AI_for_science` 执行 `git init -b main`。本次未提交、推送或设置 GitHub remote；用户尚未提供目标仓库 URL。

## Python

采用大方案 3.3 的 CPython 3.12。Windows 本机 `uv python list --only-installed` 实际列出 3.12.11 和 3.14.5；因此本机已有 Windows 版 3.12，无须为本次准备重复安装。

`.python-version` 写为 `3.12`，限制所选系列，不代表已固定补丁或完成依赖兼容验收。P1 创建 `pyproject.toml` 时使用 `requires-python = ">=3.12,<3.13"`，安装测试后记录准确解释器版本、生成依赖锁并固定部署镜像。不得使用宽泛 `>=3.12` 来默许未经验证的 3.14。

WSL 中的 Python/uv 尚未检查；Windows 安装不等于 Linux 环境已就绪。在已准备 Linux uv 的 WSL 环境中，缺少解释器时使用 `uv python install 3.12`，随后显式使用 3.12 创建环境。见 [uv 官方说明](https://docs.astral.sh/uv/guides/install-python/)。本次没有安装或升级解释器。

## WSL 与运行目录

`wsl --list --verbose` 已确认 Ubuntu 为 WSL2（查询时停止），另有运行中的 docker-desktop。尚未启动 Ubuntu 核查 Linux 用户、挂载和依赖，故不填写虚构的实际 Linux 路径。

建议采用 A：正式开发/运行 checkout 位于 WSL Linux 文件系统，例如 `~/danus-ai`；venv、数据库及运行制品位于明确的 Linux 本地目录。Windows 可通过 `\\wsl.localhost\Ubuntu\home\<Linux用户>\danus-ai` 编辑源码。数据库必须由 WSL 内进程以 Linux 路径访问，不经 UNC 打开。

代码留在 D 盘并不单独违反“数据库不得放 Windows 挂载”的限制，但仅把数据库移入 WSL，尚不能证明满足大方案 3.2 对控制服务运行位置的完整要求。当前 D 盘工作区只用于文档与纯契约准备；正式运行采用 WSL 本地 checkout 是推荐方案，迁移尚未执行。

P1 建库前关闭部署/StorageDecision：确认唯一生产后端、唯一权威开发 checkout、Linux 运行目录、venv、数据库（含 WAL/SHM）、制品、备份和权限；在 Linux 中解析真实路径并验证文件系统，拒绝指向 Windows 挂载或网络存储的数据库，包括符号链接绕行。只有路径字符串类似 `/home` 不足以证明底层挂载正确。

不必在当前阅读/文档阶段移动整个仓库。切换时可先保留 D 盘副本，核对 Git 历史和未提交文件后转用 Linux checkout，避免两处同时编辑导致漂移。迁移方案与具体路径仍待落实。

Microsoft 建议 Linux 工具使用 WSL 文件系统以获得较好的性能；本项目还需验证工具链、大小写及权限行为，不预先断言 UNC 编辑必然更慢。参考：[WSL 文件系统说明](https://learn.microsoft.com/en-us/windows/wsl/filesystems)。

## 第三方基线

用户指定的只读范围已写入根目录 `AGENTS.md`。新增 `THIRD_PARTY_NOTICES.md`、LICENSE 原文副本、初始 `reuse_manifest.json` 与差异登记。本次不复制源码、不改上游、不执行 pull 或 editable install。

后续正式实施仍需读取角色规格相关合同、落实首包与独立复核责任。运行预算和资源采购不因本次工程准备自动获批。
