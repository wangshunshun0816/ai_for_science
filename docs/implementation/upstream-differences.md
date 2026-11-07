# 上游差异与采纳登记

日期：2026-11-07。阶段：P0-1。按 A0 当日批准的只读范围核查。

| 项目 | 事实/处置 | 状态 |
|---|---|---|
| 上游 HEAD | `6d92e8d415933ca2ef52fd1a4da73fdfcd418f1c`，与大方案 3.4 相同 | 已核对 |
| MCP 包装路径 | 大方案列 `gateway/_mcp.py`；实际文件为 `danus/_mcp.py` | 采纳映射采用实际路径 |
| 数学核 | `danus/core/factgraph.py`、`danus/core/schema.py` | P1 按隔离保留落地；服务未实现 |
| 检索、执行、验证和展示组件 | P1 逐项选择具体文件受控迁入 `danus_ai/`，保留版权并登记修改 | 尚未复制或改造 |
| 数学证明搜索 Agent 主体 | 不作为首版采纳项 | 相关 launcher、角色合同和技能的处置见 `entry_points.json` |
| 工作树与提交一致性 | `git --no-optional-locks status --porcelain` 输出为空 | Git 工作树状态干净；不含被忽略文件的核验 |
| 测试与能力 | 本次不执行上游代码/测试 | 未验证 |

源路径与行数见 `reuse_manifest.json`；它是盘点记录，不是源码完整性证明、迁移完成记录或 P0 全量验收报告。

P1 每项实际采纳补充：固定提交、源路径、目标模块/服务端口、采纳方式、版权与许可、修改文件内声明、具体变更、代码提交、测试及残余限制。所有改造只发生在项目副本；原基线始终只读。

## U-01 WSL 原生基线

A0 在 2026-11-07 的本轮指令中确认批准 U-01。该指令引用的 `A0-U01-upstream-wsl-clone.md` 在执行前的项目 `main` 和 GitHub `main` 中均未找到。

从上游 GitHub 仓库克隆至 `/home/wangshunshun/upstream/Danus`，以分离 HEAD 检出固定提交 `6d92e8d415933ca2ef52fd1a4da73fdfcd418f1c`。核对工作树干净并执行 `chmod -R a-w`。WSL 克隆与 D 盘历史上游副本的 `HEAD^{tree}` 均为 `68116644a623580efb7a7510b84ed37465bce525`。

Linux Git 默认检查 D 盘历史副本时报告 213 个路径为修改。只在该次只读状态命令中传入 `core.autocrlf=true` 后报告为空，证实观察到的差异来自 Windows 检出的换行转换。历史副本原样保留，今后审计使用 WSL 原生基线。

| LICENSE 来源 | SHA-256 | 字节说明 |
| --- | --- | --- |
| D 盘历史上游副本与原项目副本 | `61bd88cc691cd7683d203a92c8b8b2934bab9fd5f102fdd115ae3d5f261717a8` | Windows 检出转换为 CRLF 后的字节 |
| WSL 上游副本、固定提交中的 LICENSE 对象与新项目副本 | `d51dbb6676bff13e23abd800608ec96bd6e637fd5b5194ef9ea8d848416d8ef3` | 固定提交中的原始字节 |

已确认旧 LICENSE 字节等于新 LICENSE 字节按 LF 到 CRLF 转换后的结果，许可证文本相同。复算清单仍为 91 个 Python 文件、17,073 行，逐文件路径及行数与原登记一致。

## 提交归属和复算

本次 P0-1 交付由 AI 生成；审核记录见下表。

[提交日志与审核记录](commit_log.md)

从项目根目录运行下列命令。脚本保留 manifest 中人工登记字段，重新采集可机器核对的字段，向标准输出写入 UTF-8（无 BOM）和 LF。使用保留原生输出字节的重定向方式保存到临时文件，即可与已提交 manifest 逐字节比较。

```text
uv run --python 3.12 --no-project --offline --no-python-downloads --no-cache python -B scripts/p0_audit_upstream.py --upstream "$HOME/upstream/Danus"
```
