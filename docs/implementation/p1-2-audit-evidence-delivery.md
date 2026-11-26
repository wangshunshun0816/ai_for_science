# 审计、复审证据合同及已交付范围统一出口

本包依据大方案 §5.1、§5.2–5.5、§6.4、§6.16、§6.17、§6.28 和角色规格 §4.6，沿用已签收 A7 输出、失效证据、审计链和数字合同。实施起点为数字合同签收提交 4dec2fafd18ef948995a8fb51f65189654980f41。工程完成、方法资格和服务验收分别登记。

## 字段依据及责任

所有表内字段显式必填，无隐式默认值。权威记录定位为完整 RecordLocator，模型配置与科研材料引用为完整 ScientificRef，历史引用沿用已有 HistoricalRef。tenant_id、project_id 由受信服务填写。列表保持原顺序及重复项，逐项校验，未新增去重或汇总规则。新记录的正文完整摘要只用于既有不可变版本核验，不分配新的科研内容 ID。

| 合同及精确字段 | 类型、null 与来源 | 写入、版本及权限 |
| --- | --- | --- |
| AuditProfile.locator | AuditProfile 精确记录定位，不可空。大方案 §6.4、角色 §4.6。 | 审计配置管理服务持有，按独立记录版本核验。 |
| AuditProfile.tenant_id、project_id | 非空文本，沿用项目归属。 | 控制服务附加，普通调用方不可自报权威记录。 |
| AuditProfile.task_kind | candidate_review、protocol_review、empirical_review 三值，不可空。角色 §4.6。 | 配置服务写，不允许任务类型互换。结构可解析不等于每种材料已支持。 |
| AuditProfile.model_profile_ref、lineage_ref | ModelProfile 为既有 ScientificRef，ModelLineage 为精确 RecordLocator，均不可空。角色 §4.6；A-R01 整改。 | 服务持有，与独立任务配置逐项匹配，权限先于受限读取。实际模型质量和资格评测另验，本包未重复执行 A 组完整执行资格核验。 |
| AuditProfile.required_materials | 非空精确引用列表，沿用 Ref。角色 §4.6 冻结审计包。 | 与独立任务材料清单逐项精确匹配，不从待检报告反推。 |
| AuditReportRecord.locator、tenant_id、project_id | AuditReport 记录定位及服务归属，不可空。 | R12 持有，经独立完整正文摘要核验。 |
| AuditReportRecord.task_kind、target_ref、profile_ref | 三类审计任务、精确科研目标和 AuditProfile 定位，不可空。角色 §4.6。 | R12 绑定，不因同科学哈希而替换精确对象。候选、协议／预注册、提交的任务类型不可混用。 |
| AuditReportRecord.result | error、needs_evidence、blocking_issue、no_blocking_issue_found，不可空。 | error 由服务记录，其余与 A7 草稿的既定结论严格相等。 |
| AuditReportRecord.draft | 复用 role_outputs.AuditReport，仅 error 时为空。 | A7 提议，R12 校验，未增加另一个草稿含义。 |
| draft.role、outcome、issues、reviewed_refs | 沿用 A7、三类非错误结论、问题列表及非空材料列表。角色 §4.6 与第七批签收。 | 不授予真实 A7 身份。材料须在独立清单内，必需材料必须覆盖。 |
| issues.code、evidence、impact、severity、remediation | 沿用已交付 AuditIssue，证据非空，severity 仅 blocking／non_blocking。 | 原样的诊断建议，不作为通用代码白名单、方法严重性分级或资格恢复政策。未知严重度拒绝。 |
| AuditReportRecord.error_ref | 精确服务诊断定位，error 时非空，其余为空。 | R12 错误事实的关联定位。此次不实现通用 ServiceError 正文读取或以诊断定位授予任何资格。 |
| AuditQuery.report_ref、profile_ref、target_ref、task_kind | 调用方明确查询的精确对象，不可空。 | 服务在当前委派和独立任务事实下核对，不把查询声明当权威事实。 |
| AuditReadResult.report_ref、result、qualification | 精确报告、四类结果、固定 evidence_checked_only。 | 仅输出，接收方重新核验当前事实并比较。 |
| ReauditTask.locator、tenant_id、project_id、trigger、affected_refs | 直接复用 ReauditTaskLink。触发为精确 EvidenceEvent，受影响者为非空 ClaimEvidenceRef 列表。大方案 §5.1 与既有失效证据签收。 | R19 事实只读投影，科学版本及记录修订分别保留。本入口仅验证单个已证实依赖目标。 |
| ReauditTask 的 priority、next_action、deadline、owner 等扩展 | 未形成完整已批准枚举、派发或生命周期规则。 | 本次模型未加入这些字段，额外输入拒绝。未给默认值，不能执行通用复审队列。 |

AuditAssignment 是服务端只读端口事实，绑定精确查询、归属、模型配置／谱系及完整有序材料清单，并核对当前 revoked／expires_at。AuditMaterialVersion 绑定精确材料与归属、完整记录摘要。它们不注册为调用方输入，端口须独立于待检正文取得事实。查询授权使用既有委派、关系修订、租约、任务与用途守卫，逐条读取权限继续复用 ImpactScope。

## 实际支持与明确阻断

- 已贯通候选审计读取与接收校验。目标正文使用现有 CandidateRecord，完整摘要与独立版本依据匹配后，核对归属、候选 ID、科学版本并调用既有 validate_candidate_version。原候选科学投影、授权及归属语义直接复用。
- AuditProfile 与 AuditReportRecord 的完整正文均匹配独立权威记录锚点。报告任务类型、目标、配置版本与独立冻结材料清单一致，错误、补证、阻断和未发现阻断分别返回 evidence_checked_only。
- 协议／预注册和经验审计的完整材料适配器未接入本包，相关形状可解析，业务读取返回 AUDIT_MATERIAL_SPEC_UNRESOLVED。通用材料类型和跨材料方法适用性须补独立目标合同和证据，不能用字段齐全代替审计资格。
- ReauditTask 通过既有 check_invalidation_impact 校验原论断、三类有效失效报告、追加事件、成功且时点有效的审计链、真实 requires 传播和精确 R19 定位。单目标通过后返回受控历史结构，多目标返回 REAUDIT_MULTI_TARGET_SPEC_UNRESOLVED。不执行队列、复现或资格恢复。I-R03 异修订适用映射仍阻断。
- ReleaseManifestBody 的字段与签名载荷未改。新增 check_release_evidence 仅核验已授权清单正文，以及独立证据快照清单中精确的 release_ref、snapshot_ref、scope_ref 和 report_refs。它不计算发布资格，也未读取通用快照／报告的全部语义，缺独立清单时拒绝。签名、回执和实际发布沿原合同及服务阶段验收。
- 当前无批准来源、配置、精确材料或读取权限时拒绝，越权不读取受限版本快照或正文。报告及复审均不创建科学有效、选择批准、预算或数据发送资格。

## 独立向量、Schema 与兼容

十组固定对象包括 AuditProfile、AuditQuery、AuditReportRecord、AuditReadResult、ReauditTask，以及补齐整对象证据的 CandidateRecord、ClaimRecord、EvidenceEvent、ApprovalSubject、ReleaseManifestBody。固定 JSON 输入与逐字节文件独立于产品规范化实现编制，预期摘要由 Python 标准库和 OpenSSL 分别对文件核算。候选科学版本复用已签收的候选改版样例，论断科学版本复用原独立失效向量。仅序列化的批准或发布向量不代表签名或真实发布通过。[独立材料](../../tests/fixtures/audit_evidence/independent.json)

新 Schema 来自唯一类型源，新增五个根合同及其运行时能力说明。error 时草稿为空且错误定位非空、非 error 时二者反向互斥的可表达条件已写入 Schema allOf；精确版本、权限、独立材料和覆盖等条件仍由运行时守卫验证。AuditReportRecord 与已有嵌套 A7 AuditReport 草稿区别命名，历史角色输出不变。ReauditTask 是既有定位投影的严格命名子型，旧数据不自动补调度字段。固定输入、来源模型、科学哈希和原签名载荷无变更。新版两份生成物的摘要随证据保存。[注册能力](../../danus_ai/contracts/api.py)

## 统一出口执行结果

清单共 29 行。12 行真实执行已交付的行为子路径，10 行登记整对象序列化证据，7 行明确未覆盖。测试收集只表示被选中，实际行为通过另由断言决定。无本轮完成的“预期阻断”行被计为完整能力。

原九件中的正面、有限否定、缺题、审计超时、数字错配和十次重复分别覆盖结果／接收或错误报告子路径。原正面并未因此获得完整 G0/G1/G2 或入图证据。过宽 Scope 的原变体完整提交链、收集崩溃恢复和提交幂等事务未覆盖。抽样不确定、数值复现、范围变更和资格恢复同列未覆盖，后两类真实事务留对应服务阶段。[可执行清单](../../tests/fixtures/exit_coverage.json) · [实际结果](evidence/p1-2-exit-coverage.json) · [执行入口](../../tests/contracts/test_exit_coverage.py)

## 实测与仍开放出口

Ubuntu CPython 3.12.16 完整 scripts/verify.sh 通过，包含锁定安装、Ruff、mypy、导入边界、Schema、默认测试 693 通过／18 项 SQLite 专项跳过、wheel 与源码包构建。为使源码包能够运行新清单，MANIFEST.in 包含全部原九件 JSON，原文件字节未变。[工程日志](evidence/p1-2-audit-verify.log)

Windows CPython 3.12.14 以同一 uv.lock 离线同步隔离环境，57 项审计及统一清单专项通过。两端十组 UTF-8 与完整 SHA-256 一致，各自从类型源生成两份 Schema 并逐字节校验，29 行清单实际结果也一致。[Ubuntu](evidence/p1-2-audit-ubuntu.json) · [Windows](evidence/p1-2-audit-windows.json)

本包关闭候选审计读／接收、单目标已证实失效复审定位与已定发布引用关联的合同子集，补齐十组整对象字节和统一出口索引。通用审计材料、方法资格、完整复审调度合同、其他 §5.1 合同及 D 组总体仍开放。原数字 CI 44236133594 绑定 835263bdae9a7d42962fd42f8d9faa0f41885104，整改 CI 45097230926 绑定 997b262c5724f715bd40f620eb100bf3ed0cd280，两次详细日志未取得。本包须核验自身提交的新 CI，人工验收另行进行。


## 出口逐项结论

| 原台账要求 | 本包证据 | 本包关闭范围与剩余 |
| --- | --- | --- |
| AuditProfile、AuditReport | 候选材料正文和配置／报告的独立版本、调用与接收守卫、57 项专项中的审计部分 | 关闭候选审计只读子集。协议／经验材料适配器和通用配置资格仍未关闭。 |
| ReauditTask | 已证实失效报告、事件、审计链、真实依赖和精确任务定位 | 关闭单目标只读结构与触发校验。优先级、后续动作、截止和完整队列合同仍缺。 |
| ReleaseManifest | 已有签名载荷不变，独立证据快照清单与完整 manifest 正文核验 | 关闭已有引用的关联子集。快照全部内容、正式签署资格、发布和撤回仍按各自条件验收。 |
| Candidate、Claim、EvidenceEvent、Approval、ReleaseManifest 的直接平台字节 | 补齐五组既有整对象预期，含在十组向量中 | 关闭所列固定输入的字节证据空白。未据此关闭各对象全部行为或科学资格。 |
| D 组独立金样例 | 29 行清单和实际结果，12 行行为子路径、10 行序列化、7 行未覆盖 | 关闭已交付范围缺统一执行索引的问题，完整合格提交、Scope 变体、真实恢复／幂等及方法缺项保留。 |
| 数字合同限定签收及历史状态 | 4dec2fa 签收链接、两次原数字 CI SHA 与详细日志限制 | 同步现行状态，未重复签收，原发现保留。 |
| P1-2 其他合同与整体出口 | 收尾计划及台账继续列明 Budget／BudgetEvent、学习／参数／评测、数学引用等 | 未因本包注册类型或预期阻断而记为完成。 |

独立复核已登记 A-R01 配置／谱系实际正文与引用桥接缺口、A-R02 重复样例输入追踪缺陷，均待整改。本轮 57 项专项通过不能关闭这两项。发布报告及快照正文适用性仍缺证据。本包尚无对应远端运行，用户确认须先手动推送后运行。 [独立复核](evidence/p1-2-audit-independent-review.md)

## A-R01、A-R02 整改后的现行交付

2026-11-26 复用 A 组精确配置科学引用、谱系定位、独立版本／正文和当前有效性守卫，拒绝配置／谱系错配及同修订替换。旧 ModelProfile 记录定位形状拒绝，要求显式提供已有 ModelProfile.ref，不自动转换。合法新配置科学版本与新谱系、审计配置及报告修订两入口通过；未授予真实审计资格。

执行器消费原变体逐行内容，q99 和冲突内存变体不再报告原预期通过，原十条重复 q3 合法。审计超时行因未贯通实际 G2 提交而降为未覆盖；其他已定分支沿用已有入口与独立材料。

现行清单为 31 行：11 行行为子路径、12 行序列化、8 行未覆盖。[实际结果](evidence/p1-2-exit-coverage-remediation.json)。原 29 行和原发现作为历史保留。Ubuntu 完整检查 715 通过、18 项 SQLite 跳过，Windows 同锁专项 79 通过，12 组向量及两份 Schema 一致。[整改证据](evidence/p1-2-audit-independent-review.md#a-r01a-r02-整改与复验2026-11-26)

发布报告／快照正文适用性仍缺，真实来源认证、完整审计材料和复审队列继续按原边界阻断。旧提交 28d113e 尚无已核实 CI，整改须有自身新 CI，人工验收另行进行。
