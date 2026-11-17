# P1-2 整体出口覆盖台账

以大方案 §5.1、§5.2–5.5、§6.4 和开发指南 §3.4／§5.3 为出口依据。字段详见 [R02 台账](r02-field-matrix.md)。下表的批次记录链接到各批独立测试、Windows／Ubuntu 对照及验收范围。两份生成物为 [JSON Schema](../../schemas/r02.schema.json) 和 [OpenAPI](../../schemas/r02.openapi.json)，入口注册与运行时守卫见 [api.py](../../danus_ai/contracts/api.py)。子类型未单独注册时，不视为已有通用入口。第十四批已[限定签收](decisions/A0-P1-2-batch14-acceptance.md)（24c5c0635db7aa34df4edf41fdebb02a540a46f5）；第十五批已[限定签收](decisions/A0-P1-2-batch15-acceptance.md)（b69299896cf2c737146b1a42e893f0fc63dde2b7）。见[收尾计划](p1-2-closure-plan.md)。

| 设计对象／要求 | 类型、入口、守卫及证据 | 现状与剩余出口 |
|---|---|---|
| ResearchTask | [planning](../../danus_ai/contracts/planning.py)、[任务转换](../../danus_ai/contracts/transitions.py)、[第七批](p1-2-batch7-delivery.md) | 已签收草稿、活动快照及权限拒绝子集；真实激活与持久化后续验收。 |
| CandidateHypothesis | [first_objects](../../danus_ai/contracts/first_objects.py)、[projections](../../danus_ai/contracts/projections.py)、[第三批](p1-2-batch3-delivery.md) | 固定首包及内容版本已签收；候选改版后旧批准不适用的独立样例缺项已关闭，见[两端向量及默认工程 CI](p1-2-candidate-revision-golden.md)。 |
| IdeationReport、IdeationChecklist | [C 组交付](p1-2-c-selection-lock-delivery.md)、[专项测试](../../tests/contracts/test_selection_review.py) | 六项固定检查及现行版本、逐项证据守卫已交付；正式 ready 缺权威检查依据时拒绝，真实评估后续。报告证据集合整改 C-R04 已定向复验，整改 CI 成功，已获[A0 C 组限定验收](decisions/A0-P1-2-c-selection-lock-acceptance.md)，见[独立复核](evidence/p1-2-c-selection-review.md)。 |
| SelectionDecision、ThresholdEvent | [C 组交付](p1-2-c-selection-lock-delivery.md)、[签收字段](p1-2-c-selection-lock-fields.md) | 精确报告／清单／预算范围签名及现行阈值事件已交付只读子集。预算权威、正式选择签发和新问题投影仍受阻，历史前驱批准整改 C-R03 已定向复验，整改 CI 成功，已获[A0 C 组限定验收](decisions/A0-P1-2-c-selection-lock-acceptance.md)，见[独立复核](evidence/p1-2-c-selection-review.md)。 |
| Protocol、Arm | [first_objects](../../danus_ai/contracts/first_objects.py)、[fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定四题投影和跨对象守卫已签收；采样／描述型继续阻断。 |
| Prereg | [fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定科学投影及锁定守卫已签收；通用目标、适用依据与真实审批后续。 |
| RunRequest、ExecutionBinding | [runs](../../danus_ai/contracts/runs.py)、[fixed_four](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定确定性 confirmation 路径已签收；其余模式逐项核对目标规范、正式投影及运行前置条件。 |
| RunRecord、Attempt | [execution_records](../../danus_ai/contracts/execution_records.py)、[transitions](../../danus_ai/contracts/transitions.py)、[第十一批](p1-2-batch11-delivery.md) | 已签收主体绑定、状态分离、尝试结算；通用修订集合与汇总待决。 |
| InvocationRecord | [尝试和调用守卫](../../danus_ai/contracts/execution_records.py)、[第十一批](p1-2-batch11-delivery.md) | 精确调用和重试子集已签收；通用间接关系及费用最终结算待决。 |
| ClaimSubmission、EvidenceReport、GateExecution | [submission](../../danus_ai/contracts/submission.py)、[第八批](p1-2-batch8-delivery.md)、[第十二批](p1-2-batch12-delivery.md) | 固定四题已签收，正式 run_ids 经独立适配读取旧样例；关口到运行／尝试映射与混合结果选择待决，真实关口后续。 |
| ClaimNode、EvidenceEvent | [claims](../../danus_ai/contracts/claims.py)、[第四批](p1-2-batch4-delivery.md) | 科学内容、定义性来源、事件／审计摘要分离已签收；历史标记清除权限待决。 |
| ModelProfile、ModelLineage | [字段台账](r02-field-matrix.md)、[调用记录](../../danus_ai/contracts/execution_records.py) | 同项目精确配置／谱系核验子集已交付；同修订正文绑定已[限定签收](decisions/A0-P1-2-execution-qualification-acceptance.md)，完整谱系、配置和启用条款仍受阻。见[A 组字段与证据](p1-2-execution-qualification.md)。 |
| Budget、BudgetEvent、I-BUDGET | [reserve](../../danus_ai/contracts/budget_preflight.py)、[quote](../../danus_ai/contracts/budget_quote.py)、[第十三批](p1-2-batch13-delivery.md)、[第十四批](p1-2-batch14-delivery.md) | reserve 只读预检已签收；quote 限 R00 总额投影。其余操作及 Budget／BudgetEvent 待补，待决见 [提案](decisions/A0-P1-2-budget-operations-proposal.md)。 |
| Usage | [R07 读取守卫](../../danus_ai/contracts/execution_records.py)、[第十二批](p1-2-batch12-delivery.md) | 精确读取、金额及来源边界已签收；负金额、调整关系、计量及汇总待决，真实账务后续。 |
| Approval | [signing](../../danus_ai/contracts/signing.py)、[approval_conflicts](../../danus_ai/contracts/approval_conflicts.py)、[第四批](p1-2-batch4-delivery.md) | 精确目标、用途、签名和歧义阻断已签收；缺已审定条款的用途继续阻断。 |
| ReleaseManifest | [信封、载荷与回执](../../danus_ai/contracts/signing.py)、[第四批](p1-2-batch4-delivery.md) | 签名子集已签收；发布清单目标覆盖与真实发布、撤回待验收。 |
| ResearchQuestion、FamilyDeclaration、SelectionHistory／Set | [固定目标](../../danus_ai/contracts/fixed_four.py)、[第六批](p1-2-batch6-delivery.md) | 固定版及 C 组限定子集均有测试证据。A4 阻断码和事件归类整改 C-R01、C-R02 已定向复验，整改 CI 成功，已获[A0 C 组限定验收](decisions/A0-P1-2-c-selection-lock-acceptance.md)，见[独立复核](evidence/p1-2-c-selection-review.md)。通用父问题、新族签名及暴露映射依赖保留。 |
| RandomnessPlan、DiscriminationPlan | [字段台账](r02-field-matrix.md)、[固定预注册](../../danus_ai/contracts/fixed_four.py) | 固定枚举和确定性守卫可复用；完整随机性计划、抽样及区分性设计依赖方法与启用决定。 |
| OutcomeLearningRecord | [字段台账](r02-field-matrix.md) | 通用合同、引用、复用限制及拒绝测试未交付。 |
| ParameterDecision、CalibrationTask、数字性质、ScientificStatistics | [字段台账](r02-field-matrix.md)、[第八批固定结果](p1-2-batch8-delivery.md) | 固定结果与性质已有子集；数值依据通用入口、参数批准和校准合同未齐。 |
| DataPolicy、SendPermit、DataExposure | [守卫与类型](../../danus_ai/contracts/data_policy.py)、[第十五批](p1-2-batch15-delivery.md) | 政策／许可只读约束核验已限定签收；data_use 条款与真实许可、扫描、发送、挂载仍受阻或留服务验收。[DataExposure 实际接触只读子集](p1-2-data-exposure.md)已[限定签收](decisions/A0-P1-2-data-exposure-acceptance.md)（b1d17152b0bb6857eff08b4442b18e61a1ed4cd6）；接收方、许可及用途／事件映射继续待定，真实台账与执行留服务验收。 |
| ReauditTask、AuditProfile、AuditReport | [审计摘要](../../danus_ai/contracts/claims.py)、[角色输出](../../danus_ai/contracts/role_outputs.py)、[第七批](p1-2-batch7-delivery.md) | 已有审计链和 A7 输出子集；明确失效事件的 R19 触发和受影响论断定位已交付[只读子集](p1-2-invalidation-contract.md)；通用配置、报告及复审任务入口未齐。 |
| ProductUseEvent、EvaluationCampaign | [字段台账](r02-field-matrix.md) | 冻结范围、独立性、采用事实和投入的通用合同未交付，实际评测后续。 |
| PersonalAccount、PersonalTenant、Project | [ownership](../../danus_ai/contracts/ownership.py)、[第九批](p1-2-batch9-delivery.md) | 精确关系和待认领边界已签收；真实认证、创建、迁移与认领后续。 |
| TrustedRequestContext、Delegation、错误消息 | [messages](../../danus_ai/contracts/messages.py)、[第五批](p1-2-batch5-delivery.md)、[第九批](p1-2-batch9-delivery.md) | 纯契约和撤销／旧修订拒绝已签收；真实鉴权、委派签发和适配器不预读后续。 |
| TaskPlan、PlanRevision、PlanNode、TaskContract | [planning](../../danus_ai/contracts/planning.py)、[第七批](p1-2-batch7-delivery.md) | 已签收任务计划、DAG、激活授权守卫；原子 CAS、调度及真实租约后续。 |
| RoleQualification、ResourceAdmission | [planning](../../danus_ai/contracts/planning.py)、[字段台账](r02-field-matrix.md) | 计划／调用已覆盖版本兼容与单资源准入证据定位；同修订报告／许可替换拒绝已[限定签收](decisions/A0-P1-2-execution-qualification-acceptance.md)，真实能力启用、完整费用／权限条款及资源选择映射仍受阻。见[A 组字段与证据](p1-2-execution-qualification.md)。 |
| ContextManifest、七角色输出与交接 | [context](../../danus_ai/contracts/context.py)、[role_outputs](../../danus_ai/contracts/role_outputs.py)、[第七批](p1-2-batch7-delivery.md) | 最小输入输出、接收和隔离已签收；各角色完整目标合同仍为 P1-2 出口，实际模型质量后续验收。 |
| ProtocolBundle、CheckSuite、ValidationProfile | [sanity_artifacts](../../danus_ai/contracts/sanity_artifacts.py)、[第十批](p1-2-batch10-delivery.md) | 固定子集已签收；通用材料依赖与适用扩展待明确。 |
| SanityRequest、SanityReport、SanityJobRef、SanityReportView | [submission](../../danus_ai/contracts/submission.py)、[sanity_artifacts](../../danus_ai/contracts/sanity_artifacts.py)、[第八批](p1-2-batch8-delivery.md)、[第十批](p1-2-batch10-delivery.md) | 固定四题与当前绑定检查已签收；绑定选择规则仍待决。 |
| Scope、TheoremRef | [scope](../../danus_ai/contracts/scope.py)、[第五批](p1-2-batch5-delivery.md) | 三值逻辑已签收；跨 Scope 映射待决，数学精确引用的通用目标合同未交付。 |
| 哈希、版本、状态与兼容 | [规范化](../../danus_ai/contracts/canonicalization.py)、[状态边](../../danus_ai/contracts/transitions.py)、[第二批](p1-2-batch2-delivery.md)、[第四批](p1-2-batch4-delivery.md) | 基础规则已有实现；待逐对象核对七入口、状态边、投影／明确不适用、错误与迁移适配。 |
| 独立金样例及集成出口 | [原九件映射和新增参考](p1-2-contract-readiness.md#5-验证计划与独立期望) | 逐件登记调用双方、预期来源、Ubuntu／Windows 和当前 CI；候选改版失效样例已补并核验对应工程 CI，SQLite 专项跳过且无新增存储验收证据；已补明确实现错误、污染和协议失效的[复现降级子场景](p1-2-invalidation-contract.md)。真正抽样不确定、数值复现方法等适用案例仍待补。服务效果不能用合成端口证明。 |

收尾顺序为先维护此表并给阻断项指定决定责任，再推进数据边界、模型／资源／角色资格、科研生命周期与证据对象。预算可在相关决定签收后并行补齐。最后以同一出口提交核对所有 §5.1 对象、§6.4 金样例、七入口、调用兼容与跨平台证据。缺项须完成或由 A0 明确批准出口处理；模块数、Schema 数及测试数量仅作索引。

## 逐项证据补录

Schema 名称定位 JSON Schema 的 $defs 与 OpenAPI 的 components.schemas。测试入口链接覆盖对应子集；平台报告中的实际向量键是覆盖依据，未列同名向量的对象不计为已经完成平台逐对象验证。未列入补录的行仍缺逐项直接证据。

| 子集 | Schema 定义键 | 专项正反例 | 平台证据及限制 |
|---|---|---|---|
| ResearchTask | ResearchTask、ResearchTaskDraft | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| CandidateHypothesis | CandidateDraft、CandidateRecord | [test_first_batch.py](../../tests/contracts/test_first_batch.py) | 缺直接平台证据 |
| C 组报告与清单 | IdeationReport、IdeationChecklist | [test_selection_review.py](../../tests/contracts/test_selection_review.py) | [七组逐对象向量](p1-2-c-selection-lock-vectors.md)、[两端摘要和范围](p1-2-c-selection-lock-delivery.md#验证)、[独立复核](evidence/p1-2-c-selection-review.md)。无报告或清单单独的平台字节向量。 |
| C 组选题与阈值历史 | SelectionDecision、SelectionBoundTerms、SelectionSignature、ThresholdEvent | [test_selection_review.py](../../tests/contracts/test_selection_review.py) | 贯通签名前载荷和独立条款有证据。无决定或阈值历史整对象字节向量。[独立复核](evidence/p1-2-c-selection-review.md) |
| C 组单族、历史和授权视图 | SelectionSet、SingleFamily、HistoryCoverage、SelectionHistoryV2、A4HistoryView、A7HistoryView | [test_selection_review.py](../../tests/contracts/test_selection_review.py) | v2 历史投影有两端贯通字节，固定 v1 另有逐对象预期。未列其他模型的逐对象字节。[独立复核](evidence/p1-2-c-selection-review.md) |
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
| 明确失效与资格 | InvalidationQuery、InvalidationReport、DependencySnapshot、ReauditTaskLink、InvalidationImpact | [独立金样例](../../tests/contracts/test_invalidation.py) | [六组双端字节和两份 Schema](evidence/p1-2-invalidation-cross-platform.json)，数值复现和完整队列合同未覆盖。 |
| PersonalAccount、PersonalTenant、Project | PersonalAccount、PersonalTenant、Project | [test_batch9.py](../../tests/contracts/test_batch9.py) | [9 批平台证据](evidence/p1-2-batch9-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch9-remediation-windows.json) |
| TrustedRequestContext、Delegation、错误消息 | TrustedRequestContext、Delegation、ErrorDetail | [test_batch5.py](../../tests/contracts/test_batch5.py)、[test_batch9.py](../../tests/contracts/test_batch9.py) | [5 批平台证据](evidence/p1-2-batch5-remediation-cross-platform.json)；[9 批平台证据](evidence/p1-2-batch9-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch9-remediation-windows.json) |
| TaskPlan、PlanRevision、PlanNode、TaskContract | TaskPlan、PlanRevision、PlanNode、TaskContract | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| ContextManifest、七角色输出与交接 | ContextManifest、RoleOutputEnvelope、HandoffDraft、Handoff | [test_batch7.py](../../tests/contracts/test_batch7.py) | [7 批平台证据](evidence/p1-2-batch7-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch7-remediation-windows.json) |
| ProtocolBundle、CheckSuite、ValidationProfile | ProtocolBundle、CheckSuite | [test_batch10.py](../../tests/contracts/test_batch10.py) | [10 批平台证据](evidence/p1-2-batch10-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch10-remediation-windows.json) |
| SanityRequest、SanityReport、SanityJobRef、SanityReportView | SanityRequest、SanityReport、SanityJobRef、SanityReportView | [test_batch8.py](../../tests/contracts/test_batch8.py)、[test_batch10.py](../../tests/contracts/test_batch10.py) | [8 批平台证据](evidence/p1-2-batch8-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch8-remediation-windows.json)；[10 批平台证据](evidence/p1-2-batch10-remediation-ubuntu.json)、[Windows](evidence/p1-2-batch10-remediation-windows.json) |
| Scope、TheoremRef | Scope | [test_batch5.py](../../tests/contracts/test_batch5.py) | [5 批平台证据](evidence/p1-2-batch5-remediation-cross-platform.json) |
| DataPolicy／SendPermit 只读子集 | DataConstraintQuery、DataPolicy、SendPermit、DataConstraintResult | [专项](../../tests/contracts/test_batch15.py) | [Ubuntu](evidence/p1-2-batch15-ubuntu.json) · [Windows](evidence/p1-2-batch15-windows.json)，四个根合同及两份 Schema。 |
| A 组执行证据已定子集 | ModelProfile、ModelLineage、RoleQualification、ResourceAdmission | [两入口专项](../../tests/contracts/test_execution_qualification.py) | [Ubuntu](evidence/p1-2-execution-qualification-ubuntu.json) · [Windows](evidence/p1-2-execution-qualification-windows.json)，四组规范字节和两份生成物；原运行早于 A 组交付；[整改工程 CI 已核验成功](p1-2-execution-qualification.md#整改-ci-与本轮定向复核)，详细步骤日志未取得，SQLite 专项跳过。 |
| DataExposure 实际接触只读子集 | DataExposureQuery、DataExposure、DataExposureResult | [专项](../../tests/contracts/test_data_exposure.py) | [Ubuntu](evidence/p1-2-data-exposure-ubuntu.json) · [Windows](evidence/p1-2-data-exposure-windows.json)，三组独立向量及两份生成物；[对应工程 CI 成功](p1-2-data-exposure.md#远端-ci-与独立复核)，29 项默认收集及定向复验由 WSL 证实，远端详细日志未取得，SQLite 专项跳过。 |

## 收尾与 P1-3 准备

[收尾计划](p1-2-closure-plan.md)按工作卡定义关闭条件，[最小切片计划](p1-3-minimum-slice-plan.md)记录可复用合同、实施条件和验收。P1-3 隔离切片专节已获限定授权，交付及整改已[限定验收](decisions/A0-P1-3-test-slice-acceptance.md)（454503c29065f99be170cacad4188376c9664583）。集中决策中的其他提案仍待审。原证据及工作卡出口范围继续有效。

[A 组同修订正文整改](p1-2-execution-qualification.md#同修订正文绑定整改)覆盖四类合同的独立版本快照及两条入口的替换拒绝。CI 43797949960 只覆盖旧提交 4d20e18，整改 CI 43800243706 对应整改 SHA 且成功，详细日志未取得。其余字段、语义与服务责任继续按行登记。

C 组交付的 SelectionSet、单族精确绑定、A4／A7 白名单、来源覆盖守卫及 SelectionHistory v2 证据见[逐项交付与未放行条件](p1-2-c-selection-lock-delivery.md)。既有固定四题预映像另行复算，固定四题 v1 仍要求空暴露，完整锁定前通过依赖协议、族签名和其他权威事实。

C 组整改在对应 SHA 已通过[远端 CI 作业与步骤核验](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44027827660)，远端详细日志未取得。本地默认路径收集和定向复跑均为 40 项，SQLite 专项跳过。[覆盖范围与证据](evidence/p1-2-c-selection-review.md#整改-ci-与定向复验)

C 组已交付范围与四项整改已通过[A0 C 组限定验收](decisions/A0-P1-2-c-selection-lock-acceptance.md)（a3ab1ec77746055fb7199145b228db4fb5a155ea），CI 历史日志限制、SQLite 跳过及未关闭依赖维持原记录。

明确失效三类子场景具备本地正向及反例证据。审计失败／未来时点仍接纳待整改，同科学版本异修订的影响须明确适用范围，金样例出口保持打开。尚无本交付对应远端 CI。[独立复核](evidence/p1-2-invalidation-independent-review.md)

明确失效 I-R01 审计结果及查询时点已完成整改并双端复验，I-R03 同科学版本异修订由明确阻断守卫保留，真正适用范围仍待 A0。CI 及人工验收待对应整改 SHA 证据。三个子场景以外的要求保持待办。[独立复核与整改](evidence/p1-2-invalidation-independent-review.md)

I-R01 整改在[对应 SHA 的远端 CI](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891)成功，详细日志未取得。I-R03 的不明适用关系继续拒绝，权威映射仍待 A0。默认收集 35 项及定向结果为本地证据，SQLite 专项跳过。人工验收待登记。[定向复验](evidence/p1-2-invalidation-independent-review.md#整改-ci-与定向复验)
