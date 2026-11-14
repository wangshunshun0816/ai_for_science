# P1-2 第十三批 reserve 只读预检

基线为第十二批限定签收 `9326ae204e071169dc6b400bf999300e1b685b1f`。依据大方案 §5.1、§6.10、开发指南 §3.4／§5.3 和 Budget 台账。人工验收另行登记。

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
- 远端 CI 待核验本批实际 SHA。
