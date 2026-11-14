# P1-2 整体出口覆盖台账

以大方案 §5.1、§5.2–5.5、§6.4 和开发指南 §3.4／§5.3 为出口依据。字段详见 [R02 台账](r02-field-matrix.md)。下表的批次记录链接到各批独立测试、Windows／Ubuntu 对照及验收范围。两份生成物为 [JSON Schema](../../schemas/r02.schema.json) 和 [OpenAPI](../../schemas/r02.openapi.json)，入口注册与运行时守卫见 [api.py](../../danus_ai/contracts/api.py)。子类型未单独注册时，不视为已有通用入口。第十四批已[限定签收](decisions/A0-P1-2-batch14-acceptance.md)（24c5c0635db7aa34df4edf41fdebb02a540a46f5）；第十五批待验收。

| 设计对象／要求 | 类型、入口、守卫及证据 | 现状与剩余出口 |
|---|---|---|
| ResearchTask | [planning](../../danus_ai/contracts/planning.py)、[任务转换](../../danus_ai/contracts/transitions.py)、[第七批](p1-2-batch7-delivery.md) | 已签收草稿、活动快照及权限拒绝子集；真实激活与持久化后续验收。 |
| CandidateHypothesis | [first_objects](../../danus_ai/contracts/first_objects.py)、[projections](../../danus_ai/contracts/projections.py)、[第三批](p1-2-batch3-delivery.md) | 固定首包及内容版本已签收；整体需独立候选改版失效样例。 |
| IdeationReport | [字段台账](r02-field-matrix.md) | 通用记录、入口和独立预期未交付；真实评估后续。 |
| SelectionDecision | [SelectionTerms](../../danus_ai/contracts/first_objects.py)、[第三批](p1-2-batch3-delivery.md) | 已有批准条款子集；完整决定记录、权限和独立向量仍缺。 |
| Protocol、Arm | [first_objects](../../danus_ai/contracts/first_objects.py)、[fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定四题投影和跨对象守卫已签收；采样／描述型继续阻断。 |
| Prereg | [fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定科学投影及锁定守卫已签收；通用目标、适用依据与真实审批后续。 |
| RunRequest、ExecutionBinding | [runs](../../danus_ai/contracts/runs.py)、[fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定确定性 confirmation 路径已签收；其余模式逐项核对目标规范、正式投影及运行前置条件。 |
| RunRecord、Attempt | [execution_records](../../danus_ai/contracts/execution_records.py)、[transitions](../../danus_ai/contracts/transitions.py)、[第十一批](p1-2-batch11-delivery.md) | 已签收主体绑定、状态分离、尝试结算；通用修订集合与汇总待决。 |
| InvocationRecord | [尝试和调用守卫](../../danus_ai/contracts/execution_records.py)、[第十一批](p1-2-batch11-delivery.md) | 精确调用和重试子集已签收；通用间接关系及费用最终结算待决。 |
| ClaimSubmission、EvidenceReport、GateExecution | [submission](../../danus_ai/contracts/submission.py)、[第八批](p1-2-batch8-delivery.md)、[第十二批](p1-2-batch12-delivery.md) | 固定四题已签收，正式 run_ids 经独立适配读取旧样例；关口到运行／尝试映射与混合结果选择待决，真实关口后续。 |
| ClaimNode、EvidenceEvent | [claims](../../danus_ai/contracts/claims.py)、[第四批](p1-2-batch4-delivery.md) | 科学内容、定义性来源、事件／审计摘要分离已签收；历史标记清除权限待决。 |
| ModelProfile、ModelLineage | [字段台账](r02-field-matrix.md)、[调用记录](../../danus_ai/contracts/execution_records.py) | 精确模型依据消费已有子集；通用配置、谱系和启用合同缺。 |
| Budget、BudgetEvent、I-BUDGET | [reserve](../../danus_ai/contracts/budget_preflight.py)、[quote](../../danus_ai/contracts/budget_quote.py)、[第十三批](p1-2-batch13-delivery.md)、[第十四批](p1-2-batch14-delivery.md) | reserve 只读预检已签收；quote 限 R00 总额投影。其余操作及 Budget／BudgetEvent 待补，待决见 [提案](decisions/A0-P1-2-budget-operations-proposal.md)。 |
| Usage | [R07 读取守卫](../../danus_ai/contracts/execution_records.py)、[第十二批](p1-2-batch12-delivery.md) | 精确读取、金额及来源边界已签收；负金额、调整关系、计量及汇总待决，真实账务后续。 |
| Approval | [signing](../../danus_ai/contracts/signing.py)、[approval_conflicts](../../danus_ai/contracts/approval_conflicts.py)、[第四批](p1-2-batch4-delivery.md) | 精确目标、用途、签名和歧义阻断已签收；缺已审定条款的用途继续阻断。 |
| ReleaseManifest | [信封、载荷与回执](../../danus_ai/contracts/signing.py)、[第四批](p1-2-batch4-delivery.md) | 签名子集已签收；发布清单目标覆盖与真实发布、撤回待验收。 |
| ResearchQuestion、FamilyDeclaration、SelectionHistory／Set | [固定目标](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 已有固定版；通用父问题、阈值记录、族与暴露沿革及独立向量未齐。 |
| RandomnessPlan、DiscriminationPlan | [字段台账](r02-field-matrix.md)、[固定预注册](../../danus_ai/contracts/fixed_four.py) | 固定枚举和确定性守卫可复用；完整随机性计划、抽样及区分性设计依赖方法与启用决定。 |
| OutcomeLearningRecord | [字段台账](r02-field-matrix.md) | 通用合同、引用、复用限制及拒绝测试未交付。 |
| ParameterDecision、CalibrationTask、数字性质、ScientificStatistics | [字段台账](r02-field-matrix.md)、[第八批固定结果](p1-2-batch8-delivery.md) | 固定结果与性质已有子集；数值依据通用入口、参数批准和校准合同未齐。 |
| DataPolicy、SendPermit、DataExposure | [守卫与类型](../../danus_ai/contracts/data_policy.py)、[第十五批](p1-2-batch15-delivery.md) | 政策／许可只读约束核验已交付待签收；data_use 条款与真实许可、扫描、发送、挂载仍受阻或留服务验收。DataExposure 未交付。 |
| ReauditTask、AuditProfile、AuditReport | [审计摘要](../../danus_ai/contracts/claims.py)、[角色输出](../../danus_ai/contracts/role_outputs.py)、[第七批](p1-2-batch7-delivery.md) | 已有审计链和 A7 输出子集；通用配置、报告及复审任务入口未齐。 |
| ProductUseEvent、EvaluationCampaign | [字段台账](r02-field-matrix.md) | 冻结范围、独立性、采用事实和投入的通用合同未交付，实际评测后续。 |
| PersonalAccount、PersonalTenant、Project | [ownership](../../danus_ai/contracts/ownership.py)、[第九批](p1-2-batch9-delivery.md) | 精确关系和待认领边界已签收；真实认证、创建、迁移与认领后续。 |
| TrustedRequestContext、Delegation、错误消息 | [messages](../../danus_ai/contracts/messages.py)、[第五批](p1-2-batch5-delivery.md)、[第九批](p1-2-batch9-delivery.md) | 纯契约和撤销／旧修订拒绝已签收；真实鉴权、委派签发和适配器不预读后续。 |
| TaskPlan、PlanRevision、PlanNode、TaskContract | [planning](../../danus_ai/contracts/planning.py)、[第七批](p1-2-batch7-delivery.md) | 已签收任务计划、DAG、激活授权守卫；原子 CAS、调度及真实租约后续。 |
| RoleQualification、ResourceAdmission | [planning](../../danus_ai/contracts/planning.py)、[字段台账](r02-field-matrix.md) | 受信资格消费有子集；完整资格、资源准入证据未交付，选取与能力启用待实际评测。 |
| ContextManifest、七角色输出与交接 | [context](../../danus_ai/contracts/context.py)、[role_outputs](../../danus_ai/contracts/role_outputs.py)、[第七批](p1-2-batch7-delivery.md) | 最小输入输出、接收和隔离已签收；各角色全目标合同和实际模型质量后续。 |
| ProtocolBundle、CheckSuite、ValidationProfile | [sanity_artifacts](../../danus_ai/contracts/sanity_artifacts.py)、[第十批](p1-2-batch10-delivery.md) | 固定子集已签收；通用材料依赖与适用扩展待明确。 |
| SanityRequest、SanityReport、SanityJobRef、SanityReportView | [submission](../../danus_ai/contracts/submission.py)、[sanity_artifacts](../../danus_ai/contracts/sanity_artifacts.py)、[第八批](p1-2-batch8-delivery.md)、[第十批](p1-2-batch10-delivery.md) | 固定四题与当前绑定检查已签收；绑定选择规则仍待决。 |
| Scope、TheoremRef | [scope](../../danus_ai/contracts/scope.py)、[第五批](p1-2-batch5-delivery.md) | 三值逻辑已签收；跨 Scope 映射待决，数学精确引用的通用目标合同未交付。 |
| 哈希、版本、状态与兼容 | [规范化](../../danus_ai/contracts/canonicalization.py)、[状态边](../../danus_ai/contracts/transitions.py)、[第二批](p1-2-batch2-delivery.md)、[第四批](p1-2-batch4-delivery.md) | 基础规则已有实现；待逐对象核对七入口、状态边、投影／明确不适用、错误与迁移适配。 |
| 独立金样例及集成出口 | [原九件映射和新增参考](p1-2-contract-readiness.md#5-验证计划与独立期望) | 逐件登记调用双方、预期来源、Ubuntu／Windows 和当前 CI；待补真正抽样不确定、独立复现降级、候选改版等适用案例。服务效果不能用合成端口证明。 |

收尾顺序为先维护此表并给阻断项指定决定责任，再推进数据边界、模型／资源／角色资格、科研生命周期与证据对象。预算可在相关决定签收后并行补齐。最后以同一出口提交核对所有 §5.1 对象、§6.4 金样例、七入口、调用兼容与跨平台证据。缺项须完成或由 A0 明确批准出口处理；模块数、Schema 数及测试数量仅作索引。

## 逐项证据补录

Schema 名称定位 JSON Schema 的 $defs 与 OpenAPI 的 components.schemas。测试入口链接覆盖对应子集；平台报告中的实际向量键是覆盖依据，未列同名向量的对象不计为已经完成平台逐对象验证。未列入补录的行仍缺逐项直接证据。

| 子集 | Schema 定义键 | 专项正反例 | 平台证据及限制 |
|---|---|---|---|
| ResearchTask | ResearchTask、ResearchTaskDraft | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| CandidateHypothesis | CandidateDraft、CandidateRecord | [test_first_batch.py](../../tests/contracts/test_first_batch.py) | 缺直接平台证据 |
| SelectionDecision | 通用键缺 | [test_first_batch.py](../../tests/contracts/test_first_batch.py)、[test_batch6.py](../../tests/contracts/test_batch6.py) | [6 批平台证据](evidence/p1-2-batch6-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch6-remediation-windows.json) |
| Protocol、Arm | ProtocolDraft、ProtocolRecord | [test_batch6.py](../../tests/contracts/test_batch6.py) | [6 批平台证据](evidence/p1-2-batch6-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch6-remediation-windows.json) |
| Prereg | PreregDraft、PreregRecord | [test_batch6.py](../../tests/contracts/test_batch6.py) | [6 批平台证据](evidence/p1-2-batch6-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch6-remediation-windows.json) |
| RunRequest、ExecutionBinding | RunRequestDraft、RunRequestRecord、ExecutionBinding | [test_batch6.py](../../tests/contracts/test_batch6.py) | [6 批平台证据](evidence/p1-2-batch6-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch6-remediation-windows.json) |
| RunRecord、Attempt | RunRecord、AttemptSnapshot | [test_batch11.py](../../tests/contracts/test_batch11.py) | [11 批平台证据](evidence/p1-2-batch11-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch11-remediation-windows.json) |
| InvocationRecord | InvocationRecord | [test_batch11.py](../../tests/contracts/test_batch11.py) | [11 批平台证据](evidence/p1-2-batch11-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch11-remediation-windows.json) |
| ClaimSubmission、EvidenceReport、GateExecution | ClaimSubmissionDraft、ClaimSubmission、EvidenceReport、GateExecution | [test_batch8.py](../../tests/contracts/test_batch8.py)、[test_batch12.py](../../tests/contracts/test_batch12.py) | [8 批平台证据](evidence/p1-2-batch8-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch8-remediation-windows.json)；[12 批平台证据](evidence/p1-2-batch12-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch12-remediation-windows.json) |
| ClaimNode、EvidenceEvent | ClaimRecord、EvidenceEvent | [test_q04_q05.py](../../tests/contracts/test_q04_q05.py) | 缺直接平台证据 |
| Budget、BudgetEvent、I-BUDGET | ReserveRequest、ReserveFacts、ReservePreflightResult、QuoteRequest、QuoteBasis、QuoteEstimate | [test_batch13.py](../../tests/contracts/test_batch13.py)、[test_batch14.py](../../tests/contracts/test_batch14.py) | [13 批平台证据](evidence/p1-2-batch13-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch13-remediation-windows.json)；[14 批平台证据](evidence/p1-2-batch14-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch14-remediation-windows.json) |
| Usage | Usage | [test_batch12.py](../../tests/contracts/test_batch12.py) | [12 批平台证据](evidence/p1-2-batch12-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch12-remediation-windows.json) |
| Approval | ApprovalSubject、ApprovalEvidence、ApprovalDisposition | [test_q04_q05.py](../../tests/contracts/test_q04_q05.py) | 缺直接平台证据 |
| ReleaseManifest | ReleaseManifestBody、ReleaseReceipt | [test_q04_q05.py](../../tests/contracts/test_q04_q05.py) | 缺直接平台证据 |
| ResearchQuestion、FamilyDeclaration、SelectionHistory／Set | FixedQuestion、FixedFamily、FixedSelectionHistory | [test_batch6.py](../../tests/contracts/test_batch6.py) | [6 批平台证据](evidence/p1-2-batch6-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch6-remediation-windows.json) |
| PersonalAccount、PersonalTenant、Project | PersonalAccount、PersonalTenant、Project | [test_batch9.py](../../tests/contracts/test_batch9.py) | [9 批平台证据](evidence/p1-2-batch9-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch9-remediation-windows.json) |
| TrustedRequestContext、Delegation、错误消息 | TrustedRequestContext、Delegation、ErrorDetail | [test_batch5.py](../../tests/contracts/test_batch5.py)、[test_batch9.py](../../tests/contracts/test_batch9.py) | [5 批平台证据](evidence/p1-2-batch5-remediation-cross-platform.json)；[9 批平台证据](evidence/p1-2-batch9-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch9-remediation-windows.json) |
| TaskPlan、PlanRevision、PlanNode、TaskContract | TaskPlan、PlanRevision、PlanNode、TaskContract | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| ContextManifest、七角色输出与交接 | ContextManifest、RoleOutputEnvelope、HandoffDraft、Handoff | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| ProtocolBundle、CheckSuite、ValidationProfile | ProtocolBundle、CheckSuite | [test_batch10.py](../../tests/contracts/test_batch10.py) | [10 批平台证据](evidence/p1-2-batch10-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch10-remediation-windows.json) |
| SanityRequest、SanityReport、SanityJobRef、SanityReportView | SanityRequest、SanityReport、SanityJobRef、SanityReportView | [test_batch8.py](../../tests/contracts/test_batch8.py)、[test_batch10.py](../../tests/contracts/test_batch10.py) | [8 批平台证据](evidence/p1-2-batch8-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch8-remediation-windows.json)；[10 批平台证据](evidence/p1-2-batch10-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch10-remediation-windows.json) |
| Scope、TheoremRef | Scope | [test_batch5.py](../../tests/contracts/test_batch5.py) | [5 批平台证据](evidence/p1-2-batch5-remediation-cross-platform.json) |
| DataPolicy／SendPermit 只读子集 | DataConstraintQuery、DataPolicy、SendPermit、DataConstraintResult | [专项](../../tests/contracts/test_batch15.py) | [Ubuntu](evidence/p1-2-batch15-ubuntu.json) · [Windows](evidence/p1-2-batch15-windows.json)，四个根合同及两份 Schema。 |
