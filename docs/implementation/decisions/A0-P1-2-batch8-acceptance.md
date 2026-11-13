# P1-2 第八批人工验收记录

状态：A0（Jack_Wang）于 2026-11-13 签收通过，范围仅限 P1-2 第八批固定四题纯契约的已交付及整改内容。第 3 节保留整改前发现，第 4 节记录整改证据。

## 1\. 依据与交付范围

基线为第七批签收 `e3b899b27842e1af7662252c2d0ed71781bbd6b8`。依据开发指南 §3.4、§5.3，大方案 §5.1、§5.3、§6.16–6.20、§6.29 与附录 C，沿用首组批准及 Q-04～Q-07。交付提交为 `6f0f92575b3a374e2ddcf348081c6938952ed6c6`。范围是固定四题提交、Sanity、证据报告和关口记录的纯契约及 Schema。字段、写入方和验证边界见[交付记录](../p1-2-batch8-delivery.md)。

## 2\. 已核实证据

* Ubuntu 3.12.16 的完整工程检查和构建通过，271 项测试通过。原九个金样例及手算记录与 `412e67e` 无字节差异。[完整日志](../evidence/p1-2-batch8-verify.log)
* Windows 3.12.14 的第八批 4 项行为测试通过。唯一独立字节向量为 SanityRequest，两侧规范 UTF-8 字节和 SHA-256 一致，完整摘要为 `2b4818797c41a3acf8a43377d58d7900123934de7d478cf480b0b6b192685eaf`。[Ubuntu 向量](../evidence/p1-2-batch8-ubuntu.json) · [Windows 向量](../evidence/p1-2-batch8-windows.json)
* GitHub API 确认[运行 43373228351](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43373228351) 在 `main` 手动触发，结果为 `completed / success`，实际 SHA 为 `6f0f92575b3a374e2ddcf348081c6938952ed6c6`。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43373228351/job/131713642231)的 Checkout、固定依赖检查及构建通过。证据提交 `d6a516a9653cc38f0ee5e5678b2828cf1155d334` 仅修改交付记录及提交日志。

## 3\. 验收发现与复验要求

|项目|发现|整改及复验要求|
|-|-|-|
|正式运行字段及旧样例适配|大方案 §5.1 使用 `run\_ids`，附录 C.4 与旧样例使用 `run\_refs`。[准备文档 E-02](../p1-2-contract-readiness.md)和[字段台账](../r02-field-matrix.md)记录正式入口采用 `run\_ids`，旧名由测试／迁移适配器显式转换。实际 ClaimSubmissionDraft、守卫及生成物使用 `run\_refs`，未见该适配器。仅提供 `run\_ids` 的输入会因字段不匹配被拒绝。|统一正式字段及生成物，显式适配旧样例，保留原 JSON 字节。复验正式单字段通过、生产入口旧字段和双字段拒绝、旧样例经适配后逐条核验精确运行版本与归属，拒绝 attempt ID。采用不同正式约定须同步设计决定。|
|新增合同跨平台证据|一组 SanityRequest 向量只满足该请求的字节核对。ClaimSubmissionDraft、ClaimSubmission、SanityReport、EvidenceReport、GateExecution 及两份生成 Schema 均没有本批逐字节对照记录。Windows 行为测试及 Linux CI 不提供这些对象的规范字节证据。|为未覆盖合同手列独立预期，在同一锁的 Windows／Ubuntu 环境逐项比较规范 UTF-8 和完整 SHA-256。记录两份生成 Schema 的跨平台对照及运行版本；如验收范围缩减，由 A0 明示。|

真实审计执行、仓储、调度及服务准入按后续阶段验收。混合关口结果的最终尝试选择仍待明确；Q05-C 的歧义阻断与显式撤销／替代已批准。正式内容 ID、未审定批准用途及采样／描述型维持既有边界。

## 4\. 整改与复验

整改提交 `16df8ec216ceae4e8ccc7edf7e1ab425284183b2` 保留既有证据提交 `d6a516a9653cc38f0ee5e5678b2828cf1155d334`。

* 正式字段已统一为 `run\_ids`，每项保留运行定义类型、ID 与精确版本。正式字段通过，旧字段、双字段与 Attempt 引用被拒绝。显式测试适配器将旧正例的两个别名按原序映射到对应运行定义。
* Ubuntu CPython 3.12.16 完整检查 272 项通过。Windows CPython 3.12.14 对应 5 项纯契约及生成物检查通过。原锁下，两侧六种指定合同各一个独立预期向量的规范 UTF-8 与完整 SHA-256 一致。两份 Schema 在两侧分别与仓库生成物逐字节一致。原九个金样例、手算记录及设计基线无字节差异。详细正反例范围见[交付记录](../p1-2-batch8-delivery.md)。
* [整改 CI 运行 43375110700](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43375110700) 由 `workflow\_dispatch` 在 `main` 手动触发。GitHub API 核实实际 SHA 为 `16df8ec216ceae4e8ccc7edf7e1ab425284183b2`，最终状态为 `completed / success`。运行自 2026-11-13 05:54:54 UTC 开始，05:55:12 UTC 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43375110700/job/131719664882)的 Checkout、固定工具和 Python 安装、锁定检查及构建均通过。 第 2 节保留整改前运行记录。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.13

意见：已审阅第八批交付及整改证据。正式运行引用统一为 run\_ids，旧样例通过显式适配处理；六种合同的独立规范字节与 SHA-256、两份 Schema 已完成所测 Windows/Linux 环境对照。整改 CI 对应提交 16df8ec216ceae4e8ccc7edf7e1ab425284183b2，通过。本次验收仅覆盖第八批固定四题纯契约的已交付及整改内容，不代表 P1-2 整体完成，不批准真实服务准入、付费调用或发布；其余待决事项继续按交付记录跟踪。

验收结论：通过，仅限 P1-2 第八批已交付及整改内容。

