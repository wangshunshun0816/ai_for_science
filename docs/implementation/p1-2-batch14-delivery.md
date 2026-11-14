# P1-2 第十四批 quote 只读契约

基线为[第十三批限定签收](decisions/A0-P1-2-batch13-acceptance.md)提交 17f9e0490e5d99d6ef9c6ce1d5d069062035cd4a。依据大方案 §5.1、§6.10、§6.14 及开发指南 §3.10／§5.3。人工验收另行进行。

## 适用计算规则及字段

报价仅投影 R00 针对精确请求任务与用途已经给定的原币总价格或保守总上界。计价单位为整个已绑定的任务报价范围，金额为整数微货币。正金额原样传递，输出性质固定为 planning_estimate。合同不接受费率或数量输入。设计未给出通用数量单位、计量、阶梯定价、换算、取整、汇率或零额规则，对应路径不可用。适用范围由受信端口按任务精确修订、主体、租户、项目及用途确定，有效区间由来源提供，以受信 UTC 时点检查起点包含、失效点排除。区间比较采用第十三批已有端口惯例，报价不计算自然月界或新时区规则。

| 合同字段 | 依据、写入方、单位与约束 |
|---|---|
| QuoteRequest.task_ref、basis_ref | §5.1、§6.10，调用方给出精确 ResearchTask 与 QuoteBasis 定位，记录类型、ID、修订均必填。QuoteBasis 为本批受限端口形状，通用 R00 产品价格目标规范待补。 |
| QuoteRequest.purpose、currency、unit | §6.10，调用方给出用途、三位原币代码及明确 microcurrency 单位，服务逐项核验。 |
| QuoteBasisScope.locator、task_ref、writer | §5.1、指南 §3.10，服务授权端口返回与请求完全一致的记录修订和 R00 来源标签。付款或批准权限不从该字段推导。 |
| QuoteBasisScope.tenant_id、project_id、principal_id、purpose | §5.1、§6.10，权威授权元数据，绑定当前受信主体和精确引用。缺失或不一致时禁止读取报价正文。 |
| QuoteBasis.source_kind、currency、unit、amount | §6.10、指南 §3.10，R00 给出 price 或 conservative_upper_bound。原币微货币正整数为适用总额，不在合同内进行费率乘数量。正文重复元数据必须一致。 |
| QuoteBasis.valid_from、valid_until | 指南 §3.10 的适用报价依据，由服务端口给出 UTC 生效和失效时点，按上述区间守卫。 |
| QuoteEstimate.nature、basis_ref、task_ref、purpose、source_kind、currency、unit、amount、valid_until | §5.1、§6.10，守卫计算，仅输出 planning_estimate 和已核验的精确依据、适用范围与数额。 |

各字段必填、不可空；引用沿用记录修订而非科研内容 ID。所有输入与消费端严格拒绝额外字段。旧 minor 字段无别名或换算路径。估价无法作为已批准证据、ReserveFacts、ReserveRequest、Usage 或结算检查载荷。授权端口的真实装配、R00 认证及适配器不预读正文留服务阶段验收。

## 验证

- Ubuntu CPython 3.12.16 运行 bash scripts/verify.sh，394 项通过，完整静态检查、两份 Schema 和构建通过。[日志](evidence/p1-2-batch14-verify.log)
- Windows CPython 3.12.14 使用第十三批同锁隔离环境，运行 pytest 第十一至十四批 94 项及 scripts/export_r02_schema.py --check，全部通过。环境中 19 项已安装发行包版本均与 uv.lock 对应。
- 四组预期 JSON 规范字节手列于 [专项测试](../../tests/contracts/test_batch14.py)，由标准库对独立预期字节计算完整 SHA-256。Windows／Ubuntu 两侧规范字节、完整摘要及 Schema 字节数／摘要一致，各侧同时与两份仓库生成物逐字节核对。[Ubuntu](evidence/p1-2-batch14-ubuntu.json) · [Windows](evidence/p1-2-batch14-windows.json)
- 正例覆盖价格、保守上界及事实未改动；反例覆盖缺依据、精确修订、身份／用途错误且正文未读、正文范围替换、期间、单位、币种、非法金额、夹带权威字段及消费端混用。九个金样例、手算、设计基线和依赖锁与基线原字节一致。
- [远端 CI 43575759816](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43575759816) 的运行页最终显示 Success，提交链接指向完整 SHA b1b754ab112a1d1f6e7d012d33322135123aeafc。该结论来自运行摘要。

整体未完见[出口台账](p1-2-r02-exit-matrix.md)。[预算操作提案](decisions/A0-P1-2-budget-operations-proposal.md)待审。完整 Budget／BudgetEvent、根任务派生、月界、budget_use、零额、负金额、调整关联、计量、调用最终结算、通用间接重试、汇总和关口映射仍保留原边界。真实报价服务、预占、余额变更、结算、对账及外发未实施。
