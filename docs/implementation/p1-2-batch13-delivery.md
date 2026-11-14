# P1-2 第十三批 reserve 只读预检

基线为第十二批限定签收 `9326ae204e071169dc6b400bf999300e1b685b1f`。依据大方案 §5.1、§6.10、开发指南 §3.4／§5.3 和 Budget 台账。A0 已限定签收，提交 `17f9e0490e5d99d6ef9c6ce1d5d069062035cd4a`。见[签收记录](decisions/A0-P1-2-batch13-acceptance.md)。

| 字段 | 出处及写入方 | 精确版本、单位与可空性 |
|---|---|---|
| 请求 budget_ref、task_ref | §6.10，调用方 | 非空 Budget／ResearchTask 精确定位及修订 |
| 请求 budget_request | 现有 BudgetRequest，调用方 | 非空，保留用途及可空规划估价；估价不作为额度事实 |
| 请求 amount、currency、unit | §6.10，调用方 | 非空，严格整数微货币、三位币种码及固定单位；本预检只支持正金额，零额操作语义待明确 |
| 事实 budget_ref、task_ref、root_task_ref | §6.10，R07 受信端口 | 非空精确定位和修订；根任务来自服务装配的任务谱系 |
| 事实 tenant_id、project_id、principal_id、purpose | §5.1、§6.10，R07/R09 | 非空，绑定当前读取主体及用途 |
| 事实 currency、unit、available | §6.10，R07 | 非空原币和微货币；租户、项目、月度、用途、根任务五层整数额度均必填 |
| 结果 status、budget_ref、root_task_ref、authorization | §6.10，纯预检输出 | 非空，精确复制定位；固定 limits_checked_only 与 budget_use_terms_unresolved |

旧 guards.require_budget 与 planning.BudgetFact 消费 amount_minor／available_minor，没有明确的微货币单位元数据。新合同只接受显式 microcurrency。旧接口照常使用，二者没有别名或隐式换算。调用方不能填写额度、根任务或批准。受信端口必须按精确预算和任务返回当前权限及谱系；本批核验该事实，不定义根任务派生、月界或完整 Budget／BudgetEvent 修订语义。

budget_use 条款未审定，预检输出固定保留授权阻断。预检只读，不能作为预占回执或用于执行、扣款和发送。实际服务须在事务内重验授权、当前额度和资源请求。完整结算、释放及对账另行交付。负金额适用条件、调整关联、计量口径、关口到运行／尝试映射、调用费用最终结算、间接重试与汇总、当前绑定选择、通用材料依赖语义仍待明确。

## 验证

- Ubuntu CPython 3.12.16 完整工程检查及构建通过，362 项测试通过。[日志](evidence/p1-2-batch13-verify.log)
- Windows CPython 3.12.14 同锁第十一至十三批 62 项及生成物检查通过。三种合同各一组手列载荷，独立标准库编码的规范 UTF-8 与完整 SHA-256 两侧一致。两份 Schema 在两侧分别与仓库生成物逐字节相同。[Ubuntu](evidence/p1-2-batch13-ubuntu.json) · [Windows](evidence/p1-2-batch13-windows.json)
- 正例覆盖五层等额边界及事实未改动。反例覆盖逐层缺失及不足、错单位／币种／定位／归属／用途、请求伪造根任务或批准、子任务共用根额度、缺权威事实。已有结算、pending、零金额与 no_charge 用例继续通过。原九个金样例、手算、设计基线与锁文件无字节差异。
- [远端 CI 43569810315](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43569810315) 在 main 手动触发，实际 SHA 为 `d092e77df0a87d21f053b93fb6dcdb24f8ec5b80`，最终为 completed / success。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43569810315/job/132371526021)的 Checkout、固定工具及 Python 安装、锁定检查和构建均通过。

## 验收整改

依据大方案 §6.10 的多层额度和根任务保护，五层各携带精确预算修订、原币与微货币单位、租户／项目／主体／用途／根任务适用范围、金额和明确有效区间。各层区间可不同，以服务提供的同一评价时点核验。区间按权威端口提供的起点和失效点检查，守卫不计算月界、时区或重置周期。缺区间或权威期间依据时不得提供可用额度事实。

独立的 TaskRootFact 端口按精确请求任务提供根关系。关系缺失、歧义、根定位或修订不符、错归属均阻断。此结构用于传递已有权威关系，根任务派生规则和月界规则仍待明确。实际来源认证、额度作用域投影和事务内重验留待服务验收。零额、旧 minor 字段及缺层继续拒绝，预检仍只读，budget_use 保持未决。

Ubuntu 3.12.16 完整检查与构建通过，370 项。Windows 3.12.14 同锁第十一至十三批 70 项及 Schema 检查通过。三组手列向量和两份生成物在两侧逐字节对照一致，原九个金样例、手算、设计基线和依赖锁原字节保留。[完整日志](evidence/p1-2-batch13-remediation-verify.log) · [Ubuntu](evidence/p1-2-batch13-remediation-ubuntu.json) · [Windows](evidence/p1-2-batch13-remediation-windows.json)

[整改 CI 43570782374](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43570782374) 的 GitHub Actions 运行页显示最终结果为 Success，运行页提交链接指向完整 SHA `ac09487890a9b1f0ddef0a753bf24271f0e53452`。 前次运行保留为整改前证据。

**仍待明确。** 根任务派生、月界规则及 `budget_use` 条款继续待决。合成权威事实下的校验通过仅覆盖只读预检及其拒绝行为。真实授权保持阻断，预检不产生预占回执，实际服务须在事务内重新核验。
