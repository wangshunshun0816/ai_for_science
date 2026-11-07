# P0-2a 对象语义

依据开发指南 v1.0 §5.2 P0-2 卡片及 §3.4 R02 卡片。以下章节号均指大方案 v1.2。本文整理已确认语义，§5.3 未定义独立状态机的对象以「未列」注明。附录 C 是科学载荷片段，不能充当完整 Schema。

## 1. 草稿与权威对象

| 对象 | 模型可提议的内容及权威写入方 | §5.3 状态机或关联状态 | 依据 |
| --- | --- | --- | --- |
| CandidateHypothesis | A2/A4 可以提交背景、来源、新推断、预测和草案。R05 保存候选及版本，候选检查由 R17 产生。 | `draft → checked_ready / needs_revision / blocked → selected / rejected`。修改产生新版本。 | §5.1、§5.3、§6.8、C.2、C.5 |
| Protocol | 协议作者可提出数据快照、切分、指标、基线、调参空间、sanity 套件和适用模板。R04b 写入协议，批准来自 A0。 | `draft → audited → approved → superseded/revoked`。已批准内容不可变。 | §2.4、§5.1、§5.3、§6.7、C.2 |
| Prereg | A4 提议候选、批准、协议等引用及假设族、arms、estimand、检验、阈值、分析脚本和停止规则。R06 校验、写入并记录服务器锁定时间。 | `draft → validated → locked → active → completed/invalidated`。锁定后不就地编辑。 | §5.1、§5.3、§6.9、C.2 |
| ClaimSubmission | A5 经 R09 提交陈述、scope、运行、协议、预注册和前提引用。测量字段由可信路径产生。 | 适用提交状态机，见第 5 节。 | §5.1、§5.3、C.4 |
| ClaimNode | R13 唯一提交入口。经证据门接受后，系统记录不可变陈述与范围、结果及证据强度。提交稿及提交判定分别保留。 | §5.3 未列独立状态机。论断维度及后续变化见第 4、5 节。 | §5.1、§5.4–5.5、C.4 |

模型可提议科学内容、方法、阈值和已有对象的引用。服务端从认证与委派取得可信身份，填入私有对象的 `tenant_id` 和项目级对象的 `project_id`，解析对象引用并校验归属。批准者身份、服务端记录时间、锁定时间、生成的哈希和批准状态由服务端依据实际批准及校验结果填写。模型提交的引用是校验输入，不能自行赋予权限。测量值由可信收集与分析路径生成，方法输出的预测等工件进入该路径，模型不得自行标记数值为 `measured`。依据 §1.4、§5.1–5.2、§6.9、§6.11、A.1、C.2。

## 2. 批准

| 对象或动作 | 权威写入方和批准绑定 | §5.3 状态机或关联状态 | 依据 |
| --- | --- | --- | --- |
| SelectionDecision | R09 的 A0 入口。绑定 `candidate_version + selection_decision`、批准范围、意义阈值及预算范围。候选核心改变后须重新检查和批准。 | §5.3 未列独立状态机。被选候选版本进入 `selected`。 | §2.4、§5.1、§5.3、C.2、C.5 |
| 协议批准 | A0 批准，R04b 记录，绑定被审计的 `protocol_id` 所指具体版本。 | 使用 Protocol 状态机。 | §2.4、§5.1、§5.3、§6.7 |
| 预注册锁定 | R06 校验被批准的候选、批准决定、协议及分析设计后锁定具体预注册。确认运行绑定该锁定对象与代码版本。 | 使用 Prereg 状态机。 | §3.9、§5.1、§5.3、§6.9、C.2–C.3 |
| Budget | R07/R09 管理。A0 批准项目总额度及用途额度，R07 处理预占与结算。追加额度、改变用途保留额或进入高算力等级须取得新的具体资源批准。 | §5.3 未列独立状态机。 | §2.4、§5.1、§6.10 |
| Approval | R07/R09 权威记录，依据实际批准填写，记录被批准对象摘要。资源批准与科研关口分别记录。 | §5.3 未列独立状态机。 | §2.4、§5.1–5.2 |
| ReleaseManifest 签字 | R21/A11 生成发布清单，A0 对具体 `release_manifest_hash` 签字。改变产物版本后重新检查并签字。价值评审绑定的 claim 集合与报告范围仍须单独记录。 | `draft → checked → awaiting_signature → signed → released → withdrawn`。只有实际发布回执才能进入 `released`。 | §2.4、§5.1、§5.3、§6.30 |

工程决定的三维状态按 §5.3 分别记录：

| 维度 | 所回答的问题 | 取值 |
| --- | --- | --- |
| `decision_status` | 设计决定是否获确认并生效 | 待确认、批准、延期、撤回 |
| `implementation_status` | 工程实现和验收进展如何 | 未开发、开发中、已实现、验收通过 |
| `evidence_status` | 目标效果获得了怎样的证据 | 未评测、证据不足、达标、负面结果 |

实施基线确认只更新决策维度。实现与效果证据按各自事实记录。§5.3 未为三维状态记录指定独立对象或统一写入接口，见待决问题。

## 3. 运行

| 对象 | 权威写入方和语义 | §5.3 状态机或关联状态 | 依据 |
| --- | --- | --- | --- |
| RunRequest | 允许的发起方可提议运行模式、代码、镜像、数据、种子、arm、prereg、配置和资源上限。R08 接收并补全服务端绑定，按模式校验前置对象、预算和数据授权。 | §5.3 未为请求列独立状态机。实际尝试及科学资格分别记录。 | §3.9、§5.1、§5.3、§6.11 |
| RunRecord | R08 可信收集。记录锁定运行身份、各次尝试、可信制品、用量与退出原因。 | §5.3 列运行尝试与科学资格，未列运行聚合的独立状态机。 | §5.1–5.3、§6.11、C.3 |
| Attempt | R08 可信收集。一条实际执行尝试及其状态。 | `queued → reserved → running → collecting → succeeded/failed/cancelled`。外部状态未知用 `reconciling`。 | §5.1–5.3、C.3、C.5 |
| InvocationRecord | R08 模型代理记录用途、模型配置、请求摘要、用量、费用、重试、响应版本。 | §5.3 未列独立状态机。 | §5.1、§6.11 |

`run_id` 标识锁定运行定义。改变方法代码、随机种子或数据产生新 `run_id`。同一运行的基础设施重试保留原 `run_id`，每次执行用独立 `attempt_id`。API 复现使用 Prereg 预声明的 `replicate_index` 形成新运行定义。尝试的进程状态与科学运行资格 `valid / invalid / incomplete` 分开，进程成功不能授予科学资格。依据 §5.2–5.3、C.3、C.5。

§3.9 分开规定 exploration、baseline_dev、analysis_calibration、dev / val、sanity、confirmation、replication 的发起方、数据、前置对象和结果地位。确认须绑定选题批准、获批协议、已锁定预注册、代码及有效 sanity。复现须绑定原论断/预注册、锁定复现计划、数据授权及有效 sanity。

## 4. 论断

| 对象 | 权威写入方和语义 | §5.3 状态机或关联状态 | 依据 |
| --- | --- | --- | --- |
| ClaimSubmission | A5 经 R09 提交待审陈述和引用，具有独立 `submission_id`。 | 适用提交状态机，见第 5 节。 | §5.1、§5.3、C.4 |
| EvidenceReport | R10–R13 写入提交引用、阶段判定、依据、统计、审计引用和修复范围。被拒提交也保留完整报告。 | §5.3 未列报告独立状态机，报告记录关联提交及各关口结果。 | §5.1、§5.3、C.4–C.5 |
| ClaimNode | R13 唯一写入入口。保存不可变陈述与范围，后续有效性和证据通过事件维护。 | §5.3 未列独立状态机，按 §5.4 的维度记录。 | §5.1、§5.4–5.5、C.4 |

| 维度 | §5.4 取值与含义 |
| --- | --- |
| `kind` | empirical、joint、method、efficiency、scaling_law、theorem_ref。协议和 sanity 属于工件类型。 |
| `outcome` | improvement、bounded_no_meaningful_gain、harm、inconclusive。不确定性按已检验范围表述。 |
| `strength` | preliminary、supported、replicated。仅用于经验论断。负面结论也可为 supported 或 replicated。 |
| `status_flags` | needs_reaudit、stale、scope_aged、revoked、contamination_risk 等。 |
| `origin` | internal_experiment、external_report、math_reference。 |
| `logical_level` | L0 协议、L1 健全性、L2 单项经验、L3 联合实验、L4 经价值评审的头条组合。表示工件层次。 |

证据不足保留报告。首次提交不能凭 preliminary 写入已支持论断区。Scope 分开绑定目标总体和实际观察数据，范围不明时保留 `unknown`。依赖关系 `requires` 与比较关系分别保存。数学事实图是数学记录的权威来源，经验库仅保存只读 `theorem_ref`。依据 §5.4–5.5。

## 5. 事件

| 对象 | 权威写入方和语义 | §5.3 状态机或关联状态 | 依据 |
| --- | --- | --- | --- |
| EvidenceEvent | R13 是唯一提交入口。随有效证据维护论断历史，复现、撤销等变化保留原记录。 | §5.3 未列独立状态机。关联论断状态与历史变化按 §5.4–5.5 记录。 | §3.9、§5.1、§5.4–5.5 |
| GateExecution | R12/R13 写入关口事件，记录关口类型、尝试、结果、trace、调用与用量引用。费用金额引用 R07。 | §5.3 未列独立状态机。关口尝试结果与提交状态分别记录。 | §5.1、§6.19、§6.29 |

提交状态为 `received → checking → accepted/rejected/needs_evidence/error`。`error` 表示处理或验证出错，不是科学否定。C.5 中审计超时可能对应 error 或 needs_evidence，均不产生 accepted。重复提交相同幂等键且内容相同，返回原 submission，不重复建图。依据 §5.3、C.5。

## 待决问题

1. **对象状态与写入归属。** §5.3 没有给批准记录、RunRequest、RunRecord 聚合、InvocationRecord、EvidenceReport、ClaimNode、EvidenceEvent、GateExecution 各自的独立状态机，也未指定三维工程状态记录的统一写入接口。需明确哪些仅保存事实或投影，哪些确实需要独立转换规则。
2. **提交失败分类。** C.5 允许审计超时落入 `error` 或 `needs_evidence`，未指定两者的判定边界及恢复路径。附录 C 的 `run_refs` 与 §5.1 的 `run_ids` 也需在 R02 定稿时明确字段名和引用类型。
3. **逐对象哈希投影。** 审批引用如何进入锁定设计、论断维度及证据记录如何参与内容标识，详见 [哈希字段](hash_fields.md#待决问题)。
4. **重复与缺失的适用范围。** 固定枚举和一般评测的边界见 [分母定义](denominators.md#待决问题)。
