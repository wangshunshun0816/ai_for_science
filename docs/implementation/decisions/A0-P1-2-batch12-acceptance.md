# P1-2 第十二批人工验收记录

状态：A0（Jack_Wang）于 2026-11-14 签收通过，范围仅限 P1-2 第十二批已交付及整改内容，明确保留的待决能力除外。第 3 节保留整改前发现。

## 1\. 批准与范围

依据第十二批授权、大方案 §5.1、§6.10–6.11、开发指南 §3.4／§5.3、Usage 字段台账及已批准的精确引用、归属和尝试结算决定。起点为第十一批签收 `e48fdee97814d2646f74e4498ac5bc7f901452c9`。本批交付 `a263ff47b6cdba261082fb27d67b6dbb4d6f06be` 限于 Usage 金额事实与纯读取守卫、运行及调用接入和生成物。

## 2\. 证据

* Ubuntu CPython 3.12.16 完整检查及构建通过，327 项测试通过。Windows CPython 3.12.14 同锁，第十一、十二批共 27 项测试及生成物检查通过。一组 Usage 手列规范 UTF-8 和完整 SHA-256 两侧一致，两份 Schema 在两侧分别与仓库文件逐字节相同。原九个金样例、手算、设计基线及锁文件无字节差异。见[交付记录及原始证据](../p1-2-batch12-delivery.md)。本轮复核查阅既有日志与用例。
* [运行 43558963246](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43558963246) 最终为 completed / success，实际 SHA 为 `a263ff47b6cdba261082fb27d67b6dbb4d6f06be`。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43558963246/job/132338126000)的 Checkout、固定工具与 Python 安装、锁定检查和构建均通过。证据提交 `e34a16f4430305bdf98e2f133cf69339e9643737` 仅修改交付记录和提交日志。

## 3\. 逐项复核

|项目|已核实行为|发现与复验要求|
|-|-|-|
|R07 来源、用途与正文读取顺序|[元数据守卫](../../../danus_ai/contracts/execution_records.py#L123)核对 R07 写入方、权限、归属、精确定位和主体，再由 [read\_usage](../../../danus_ai/contracts/execution_records.py#L143)核对用途后调用正文端口。现有反例验证这类拒绝不调用正文端口。|真实适配器须证明元数据查询自身不预读正文，来源识别和委派装配按服务验收。|
|元数据与正文一致性|[正文守卫](../../../danus_ai/contracts/execution_records.py#L158)重验定位、主体、用途及租户／项目。|[正文替换测试](../../../tests/contracts/test_batch12.py#L81)只覆盖主体替换。补错正文定位／修订、用途、租户及项目。金额、币种及种类没有独立元数据摘要，正文来源真实性仍由受信端口保证。|
|运行／尝试／调用|[运行接入](../../../danus_ai/contracts/execution_records.py#L172)使用精确运行定义与 R08 运行用途，[调用接入](../../../danus_ai/contracts/execution_records.py#L240)使用已核对的 R08 调用与用途。Usage 允许 Attempt 精确定位。|当前 Attempt 仅覆盖独立读取；运行尝试循环没有逐尝试 Usage 引用，独立入口比较所给主体和用途，未独立解析 Attempt 的父运行及权威用途。补同一 Attempt ID 错修订、正确 R07 Usage 配错执行主体／用途的端到端证据；逐尝试关联缺合同处明确阻断或限定范围。|
|未知、零与结算／预算|[Usage](../../../danus_ai/contracts/execution_records.py#L70)金额为必填键、严格整数或 null，单位固定。现有测试区分未知和显式零并拒绝把 no\_charge 填作金额种类。尝试结算仍走独立守卫。|补同一运行携带零金额 Usage 但仍待结的显式断言。费用记录不产生 no\_charge、结算完成、预算或发送授权。调用费用是否必须指向最终结算仍待决定。|
|待决金额和计量|没有金额默认值或任意计量字典。调整种类形状可解析，业务读取因关联未定义被阻断。|**金额正负仍有业务缺口。** 严格 int 没有限制符号，read\_usage 会把负的 estimate／actual 原样作为可读费用返回。此举不能当作正负语义已批准，也没有实际扣款或计算。应补负金额反例并明确已知结构与业务适用资格的界线，未定义的正负、调整关联及计量口径继续待决。|
|入口和下游边界|[统一结构入口](../../../danus_ai/contracts/api.py#L267)拒绝普通调用方提交服务持有 Usage。|GateExecution 现有 [Usage 引用检查](../../../danus_ai/contracts/submission.py#L318)仍为 R07 元数据校验，不能当作已完成精确主体、用途及正文校验。后续接入时需独立验收。|

当前绑定选择规则、通用材料依赖语义、通用间接重试关系与汇总规则均保持待决。真实计量、扣款、预算预占、结算、对账及发送按对应阶段验收。

## 4\. 整改与复验

整改提交 `f3d25b898b664e891d4a34aed7aec050fcb8be8b`，保留原 CI 证据提交 `e34a16f4430305bdf98e2f133cf69339e9643737`。

* 负估价与实际金额可按历史载荷结构保存，业务读取明确阻断；调整关系继续阻断。Usage 正文须与已授权元数据、受信来源和精确身份字段一致。
* Attempt 依据 R08 父运行和尝试精确事实核验用途。GateExecution 的用量仅沿已明确的精确调用关联，使用统一正文守卫。缺依据的其他关联不推定。未授权路径不调用正文端口，真实适配器行为留服务验收。
* 未知、显式零和 no\_charge 继续分开；零金额运行的尝试仍为待结。金额符号、调整关联、计量口径和 Gate 到运行／尝试的映射仍待明确。Usage 不产生结算、预算或发送授权。
* Ubuntu 3.12.16 完整检查 341 项，Windows 3.12.14 同锁专项 46 项及生成物检查通过。原向量和两份 Schema 两侧一致且无漂移。原九个金样例、手算及设计基线保留。见[交付及原始证据](../p1-2-batch12-delivery.md)。
* [整改 CI 43560080614](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43560080614) 在 main 手动触发，实际 SHA 为 `f3d25b898b664e891d4a34aed7aec050fcb8be8b`，最终为 completed / success。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43560080614/job/132341587837)的 Checkout、固定工具与 Python 安装、锁定检查及构建均通过。 第 2 节保留整改前运行证据。

**仍待明确。** 负金额的业务适用条件、调整关联、计量口径及缺依据的 GateExecution 到运行／尝试映射保持待决。负金额和调整的业务读取继续阻断。CI 通过覆盖已实现的守卫及其拒绝行为。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.14

意见：已审阅第十二批交付及整改证据。Usage 权威记录、正文一致性核验及 Attempt／GateExecution 的已明确关联完成限定验证。Ubuntu 341 项、Windows 46 项检查通过，Usage 向量与两份 Schema 跨平台一致，整改 CI 对应提交 f3d25b898b664e891d4a34aed7aec050fcb8be8b，通过。负金额适用条件、调整关联、计量口径及缺依据的关口到运行／尝试映射继续待决，对应业务路径保持阻断。真实计量、结算和服务准入不在本次范围，不代表 P1-2 整体完成。

验收结论：通过，仅限 P1-2 第十二批已交付及整改内容，不含明确保留的待决能力。

