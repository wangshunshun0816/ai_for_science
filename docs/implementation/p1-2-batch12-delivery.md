# P1-2 第十二批 R07 用量与费用事实

基线为第十一批限定签收 `e48fdee97814d2646f74e4498ac5bc7f901452c9`。依据大方案 §5.1、§6.10–6.11、开发指南 §3.4／§5.3 和 Usage 台账。人工验收另行登记。

| Usage 字段 | 出处和写入方 | 约束 |
|---|---|---|
| locator、tenant_id、project_id | §5.1，R07 | 必填非空，Usage 类型、记录 ID 和精确修订；当前项目 |
| subject | §5.1、§6.10，R07 | 必填非空；运行定义用精确 ScientificRef，尝试或调用用精确 RecordLocator |
| purpose | §5.1、§6.10，R07 | 必填非空，与权威执行用途及用量元数据一致 |
| currency | §6.10，R07 | 必填非空，三位大写币种码；保留原币，无折算 |
| unit | §6.10，R07 | 必填，固定 microcurrency |
| kind | §6.10，R07 | 必填，estimate／actual／adjustment 分列；调整关系未定义，读取能力阻断 |
| amount | §6.10，R07 | 必填键，严格整数微货币或 null；null 表示未知，无默认零值。各类型正负语义待定 |

运行、调用守卫读取 Usage 正文前，复用精确元数据守卫核权限、归属、主体、修订、用途和 R07 来源；独立 Usage 读取也支持精确 Attempt 主体。正文再次核对这些身份字段。提供商计量可作为后续 R07 输入证据，非 R07 元数据不能授权账务正文读取。本批保留既有 SettlementFacts 和尝试结算守卫；显式零金额不产生 no_charge，也不改变结算状态。调用费用是否必须引用最终结算、间接重试、汇总及计量子结构仍待明确。真实身份、适配器来源认证、预算预占、计量、结算和发送留待对应阶段。

## 验证

- Ubuntu CPython 3.12.16 完整检查和构建通过，327 项。Windows CPython 3.12.14 同一锁，第十一、十二批共 27 项及生成物检查通过。
- 手列 Usage 载荷用独立标准库 JSON 编码并计算 SHA-256。规范 UTF-8 及完整摘要两侧一致，两份生成物均与仓库逐字节一致。[Ubuntu](evidence/p1-2-batch12-ubuntu.json) · [Windows](evidence/p1-2-batch12-windows.json) · [完整日志](evidence/p1-2-batch12-verify.log)
- 覆盖错主体、修订、归属、用途、不可读和非 R07 来源的正文前拒绝，正文主体替换、浮点金额、错误单位、未知与显式零、no_charge 结算分离及普通入口拒绝。第十一批真实终结语义的合成回归与空费用用例继续通过。原九个金样例、手算、设计基线和锁文件无字节差异。
- [远端 CI 43558963246](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43558963246) 手动触发，实际 SHA 为 `a263ff47b6cdba261082fb27d67b6dbb4d6f06be`，最终为 completed / success。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43558963246/job/132338126000)的 Checkout、固定工具及 Python 安装、锁定检查与构建均通过。

## 验收整改

- 负 estimate／actual 保留结构解析，业务读取返回 SPEC_UNRESOLVED，原值保留。调整关联及金额符号、计量口径保持待决。
- Usage 先核元数据再读正文。正文端口同时返回受信来源事实，与已授权元数据逐项比对，再检查正文定位、修订、主体、租户／项目和用途。合成端口覆盖来源替换。真实来源认证和元数据不预读正文仍须服务验收。
- Attempt 用量核对父运行的精确定义、尝试精确修订在父记录中的唯一匹配、R08 父子事实及一致的权威用途。缺事实即阻断。此守卫验证给定关联，不自动发现逐尝试用量或推断汇总。
- GateExecution 依据 §6.10 已明确的 GateExecution → Invocation → Usage 链，要求 Usage 精确属于关口已列调用，使用 R08 调用权威用途及统一正文守卫。没有设计依据的 Gate 到运行／尝试映射阻断，保持待决。费用读取不改变结算、预算或发送授权。零金额待结回归及第十一批独立 no_charge 仍通过。
- Ubuntu 3.12.16 完整检查及构建通过，341 项。Windows 3.12.14 同锁第八、十一、十二批 46 项与生成物检查通过。原 Usage 向量、两份 Schema、设计基线、原九个金样例、手算及依赖锁无字节差异。[日志](evidence/p1-2-batch12-remediation-verify.log) · [Ubuntu](evidence/p1-2-batch12-remediation-ubuntu.json) · [Windows](evidence/p1-2-batch12-remediation-windows.json)
- [整改 CI 43560080614](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43560080614) 在 main 手动触发，实际 SHA 为 `f3d25b898b664e891d4a34aed7aec050fcb8be8b`，最终为 completed / success。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43560080614/job/132341587837)的 Checkout、固定工具与 Python 安装、锁定检查及构建均通过。 原 CI 保留为整改前证据。

**仍待明确。** 负金额的业务适用条件、调整关联、计量口径及缺依据的 GateExecution 到运行／尝试映射保持待决。负金额和调整的业务读取继续阻断。CI 通过覆盖已实现的守卫及其拒绝行为。

## 后续签收

Jack_Wang 于 2026-11-14 限定签收通过，提交 `9326ae204e071169dc6b400bf999300e1b685b1f`。见[验收记录](decisions/A0-P1-2-batch12-acceptance.md)。负金额适用条件、调整关联、计量口径与缺依据的关口到运行／尝试映射继续待决。
