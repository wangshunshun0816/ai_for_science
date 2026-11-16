# P1-2 C 组逐字段实施表与待审目标合同

依据签收提交 164ed9ce41b70f06c7afe5ff5dceee2da4031763 及绑定方案 a837a549b61cfc177756a6560e19d9fbf9d9f98c。C-01 A、C-02 A（限绑定原则）、C-03 A（限修订与生效规则）、C-04 B、C-05 B 已限定签收。本表新增字段、签名和权限方案均待审。[签收专节](decisions/A0-P1-2-consolidated-decisions.md#c-组工作包独立签收) · [绑定方案](p1-2-c-selection-lock-plan.md) · [R02 字段台账](r02-field-matrix.md)

## 已有字段、定位与权限

下表默认必填且非空，标注「可空」的字段须显式提供，标注「可省」的字段沿用现有默认值。S 表示参与已有科学投影，A 表示权威记录或签名关联。读取沿用同租户、同项目、当前委派和精确目标核验。受限快照和正文在授权之后读取。复用这些字段不新增写入、签发或可见范围。

| 合同与字段 | 写入方或组装方 | 类型、定位、空值与列表规则 | 科学投影及签名 |
| --- | --- | --- | --- |
| ScientificRef.object_type / object_id / content_version | 权威目标服务；调用方可传查询值 | 非空类型、ID、带类型域的完整科学版本 | S 普通引用投影保留类型和版本；权威读取和既有签名比对完整引用 |
| HistoricalRef.object_type / entity_id / content_version | 历史目标所有者；调用方可传查询值 | 非空类型、稳定实体 ID 和精确内容版本 | S 保留三字段 |
| RecordLocator.record_type / record_id / revision | 权威记录服务 | 非空类型、ID、非负整数，精确匹配三字段 | A，独立记录定位 |
| ApprovalLocator.purpose / record_id / revision | R09 等既定批准记录服务 | 既有用途、非空 ID、非负整数 | A，批准定位外置于科学投影 |
| CandidateFields.background / new_inference / prediction / draft | A2/A4 请求，R05 保存版本 | 非空文本；draft 含固定 plain_text 与非空正文 | S |
| CandidateFields.scope_ref / sources / original_source / source_kind / synthetic_origin | A2/A4 请求，R05 保存版本 | Scope 精确科学引用；sources 为含快照与出处位置的引用列表，投影按集合；original_source、synthetic_origin 可空；沿用现有来源分支 | S |
| CandidateRecord.object_id / content_version / tenant_id / project_id / ownership_scope | R05 权威记录 | ID、精确科学版本、非空租户及项目；固定 project | 由科学内容决定版本，归属和记录 ID 由权威读取另验 |
| CandidateRecord.created_at / created_by / status / approval_bindings | R05 服务记录与受信事件 | UTC、主体、既定状态；批准列表按完整定位去重，保留首见序及不同修订 | A，科学版本排除；批准冲突由独立守卫处理 |
| CandidateRecord.comment / display_name / cache_location | 服务元数据 | 非空文本可空且可省，默认 null | 科学版本排除 |
| SelectionTerms.candidate_ref / scope_ref / meaningful_delta | A0 决定，R09 登记，R06 消费 | 候选及 Scope 精确科学引用、规范十进制字符串 | S 进入 Prereg；A 现有 terms_digest 绑定完整三字段 |
| ThresholdTerms.question_ref / value / unit / direction / scope_ref / rationale_ref | A0 批准，R09 登记，R05/R06 引用 | 问题 HistoricalRef、规范十进制、单位、greater/less、Scope 和依据的精确科学引用 | S 进入 Prereg；A 现有 terms_digest 绑定完整条款 |
| ApprovalSubject.locator / tenant_id / project_id / target / terms_digest | R09 受信签署链 | 精确批准、非空归属、按用途选择精确目标类型、完整摘要 | A，目前消费器支持选题与阈值的具体条款 |
| SigningInput.schema_version / domain / purpose / key_id / algorithm / issuer_id | 既有受信签署服务 | 版本 1、既定用途域、既有用途、非空键和签发主体、Ed25519 | A，沿用既有规范 UTF-8 |
| SigningInput.subject_ref / subject_digest / authorization_scope / issued_at / expires_at | 同上 | 批准使用 ApprovalLocator；完整主题摘要；ApprovalScope 含租户、项目和 scope_digest；UTC 签发时间与可空 UTC 到期时间 | A，scope_digest 语义不扩展 |
| FixedQuestion.population_ref / estimand / unit / direction / scope_ref | R05 问题，受信端口装配 | 总体和 Scope 为精确 ScientificRef；非空 estimand、单位和固定方向枚举 | S，现有 research_question:v1 正文；Prereg 保留其 HistoricalRef |
| FixedFamily.question_ref / candidate_refs | R06 族，受信端口装配 | 问题 HistoricalRef 与候选 ScientificRef 列表；现有目标摘要保留列表顺序 | S，现有 family_declaration:v1；完整族签名条款待审 |
| FixedSelectionHistory.question_ref / family_ref / considered_candidates / test_exposures | R05/R08c 事实，R06 引用 | 问题及族 HistoricalRef；其余为 ScientificRef 列表，现有摘要保留顺序；固定四题预注册要求 test_exposures 为空 | S，现有 selection_history:v1；沿用原字节 |
| PreregDraft.candidate_ref / protocol_ref / question_ref / family_ref / selection_history_ref | A4 提交、R06 核验 | 前两项为精确 ScientificRef，后三项为 HistoricalRef | S，沿用分型投影 |
| PreregDraft.estimand / inference / randomness_plan / discrimination_plan | A4 提交、R06 核验 | 非空文本、exact_finite_population_only 和现有固定计划形状 | S；通用随机性及机制型保持阻断 |
| PreregDraft.test / family_alpha / family_alpha_reason | A4 提交、R06 核验 | 两项必填 null 及必填非空不适用理由 | S；固定四题不启用抽样检验、槽位或 α |
| PreregDraft.arms / stop_rule | A4 提交、R06 核验 | 至少两 Arm，现有投影按 ID 核验冲突后保留首见顺序；停止规则的 required_items 按集合 | S |
| PreregDraft.analysis_ref / failure_policy_ref / retry_policy_ref / missing_policy_ref / selection_feedback_policy_ref | A4 提交、R06 核验 | 精确 ScientificRef，沿用已有目标类型和正文核验 | S |
| PreregRecord.selection_terms / threshold_terms / selection_ref / threshold_decision_ref | R06 组装，由 A0/R09 提供批准 | 既有两类条款及各自用途的精确批准定位 | 条款 S、定位 A；R06 的锁定执行另验 |
| QuoteEstimate.nature / basis_ref / task_ref / purpose / source_kind / currency / unit / amount / valid_until | R07 依精确 R00 来源生成 | planning_estimate，精确记录定位与既有用途／来源、原币、整数微货币、UTC 截止 | 估价与预检结果均不授予预算授权，外置于科学投影 |
| DataExposure.subject / tenant_id / project_id / exposed_at | R08c | subject 含 DataExposure RecordLocator、Dataset ScientificRef、主体及用途；其余为非空归属、UTC | A，独立快照和正文一致；无科学版本投影 |
| DataExposureResult.status / event_ref | R08c 只读核验返回 | historical_contact_verified 与精确事件修订 | A，只证明指定事件，不证明全集或授予访问和发送权限 |

源码 [引用](../../danus_ai/contracts/references.py) · [候选与条款](../../danus_ai/contracts/first_objects.py) · [签名](../../danus_ai/contracts/signing.py) · [科学投影](../../danus_ai/contracts/projections.py) · [固定四题](../../danus_ai/contracts/fixed_four.py) · [权限](../../danus_ai/contracts/guards.py) · [历史暴露](../../danus_ai/contracts/data_exposure.py)

## C 组补充决定（七项，待 A0 签收）

本节是唯一的补充决定正文。每个编号同时界定推荐字段、备选、兼容和反例。字段默认必填非空，明确可空者例外；列表按本节所列语义处理。适用依据见大方案 §5.1–5.5、§6.9、§6.13、§6.26、§8.2–8.5 及附录 A／C.2。既有 C-01～C-05 限定签收继续有效，本节只审定新增选择。

### C-S01 报告与清单版本

- **推荐** · R17 清单用 RecordLocator，候选类型 IdeationChecklist。六个唯一 check_key 为 source_difference、testability_control、data_permission、resource_budget、pilot_template、a7_review。每项 required_when 指向可核验的适用规则，明确无条件时为 null；evidence_kinds 为获准目标类型集合。显示次序由工程规定，判定逐键进行。IdeationReport 用自身精确 RecordLocator，绑定 candidate_ref、checklist_ref、租户、项目、issued_at、status 及 results。每个结果含 check_key、outcome（pass／needs_revision／blocked／not_applicable／error）、精确 evidence_refs 集合、reason（pass 可空）和 applicability_basis_ref（明确无条件时可空）。R17 独立提供按报告修订查询的当前、被替代或撤销事实。按已签收优先级归并结果，并保留错误事实。
| R17 记录 | 精确字段、类型与校验 |
| --- | --- |
| IdeationChecklist | locator 为 IdeationChecklist 的 RecordLocator；tenant_id、project_id 为受信归属；checks 按唯一 check_key 组成集合，元素含 required_when（精确依据记录定位或显式 null）、evidence_kinds（获准目标类型集合）。 |
| IdeationReport | locator 为 IdeationReport 的 RecordLocator；candidate_ref 为完整 ScientificRef，checklist_ref 为清单精确定位；tenant_id、project_id、issued_at（UTC）、status（ready／needs_revision／blocked）、results（按清单键唯一）。每项含上述 outcome、完整证据引用集合、reason、applicability_basis_ref；error 保留在结果中。 |
| 独立当前性事实 | 服务侧按精确报告定位提供状态、归属及对应候选／清单定位，状态仅 current／superseded／revoked。完整报告正文须另对独立权威版本依据；无默认有效期。 |
| 暂排除 | 不冻结试点、模板、机制区分及许可的全套证据类型；尚无已批准目标或适用依据的检查禁用正式 ready。清单和报告只使用记录修订，不新增科研内容 ID。 |

- **备选及兼容** · 内嵌不可变清单快照并用独立权威摘要绑定；每份报告须核清单来源。旧报告缺清单定位或依据时保留原读法，无法证明 ready。
- **反例与依据** · 仅作业受理、错清单修订、重复键、无依据跳过试点、服务错误写成 pass，均不得 ready。试点、模板适用、机制区分及许可所需权威证据仍须逐项补齐。

### C-S02 选择决定的报告及预算签名绑定

- **推荐** · R09 的新条款版本包含完整 selection_terms、ideation_report_ref、checklist_ref 及 budget_scope。预算范围候选字段为 budget_ref、root_task_ref、tenant_id、project_id、purpose、currency、unit（microcurrency）、amount_ceiling（整数，零额规则另案）、authority_ref（目标类型待审）。若依据是批准，使用精确 ApprovalLocator 并核验用途和目标。新条款整体绑定到签名主题，决定记录保存精确批准定位。现有 SelectionTerms 继续独立供科学投影使用。报告和预算范围变化按签收原则复核。
| 层次 | 建议精确字段与预映像 |
| --- | --- |
| 条款 | selection_terms、ideation_report_ref、checklist_ref、budget_scope。report／checklist 为各自 RecordLocator；budget_ref 和 root_task_ref 为精确记录，金额限定正整数，零额等另案。authority_ref 只接受独立可核验且获准的预算依据，现阶段无获准类型的正式分支阻断。 |
| 签名主题 | locator（candidate_selection ApprovalLocator）、tenant_id、project_id、target（完整候选 ScientificRef）、terms_digest。建议用 selection-terms:v2 对完整条款做域分离摘要，用 selection-subject:v2 对主题做域分离摘要。两者均为 SHA-256 对含 body、domain 的规范 UTF-8。 |
| 签名前载荷 | schema_version=2、domain=selection-approval:v2、purpose=candidate_selection、key_id、algorithm=Ed25519、issuer_id、subject_ref、subject_digest、authorization_scope、issued_at、expires_at（可空）。作用域字段为 tenant_id、project_id、scope_digest，建议 scope_digest 用 selection-scope:v2 对完整 SelectionTerms.scope_ref 做域分离摘要。subject_ref 与 locator 精确相同；签名覆盖整体规范 UTF-8，签名字节外置。版本 2 的键和签发资格须由受信策略提供。 |
| 决定记录 | R09 保存 SelectionDecision RecordLocator、approval_ref、report_ref、checklist_ref、tenant_id、project_id、decided_at；回显的报告与清单定位必须与签名条款精确一致。仅覆盖 candidate_selection 正向批准；拒绝／撤回记录沿其既有流程。 |
| 兼容与待定 | 版本 1 仍走现有用途、主题及摘要，不得作为带新绑定的选择证据。暂不冻结 budget_use 目标载荷、预算权威依据的具体记录类型、零额及汇率。正式 R09 签发权限和运行使用另验。 |

- **备选及兼容** · 保留旧条款签名，增加签名关联记录，核对旧主题摘要、批准精确定位和新绑定摘要。新用途、签发权和撤销联动须明确。旧签名只覆盖原条款，成为新正式选择依据前须新绑定；默认报告有效期、等价报告替换及 budget_use 保持待决。
- **反例与依据** · 保持候选与批准定位不变却替换报告、清单或预算修订；更换币种、用途或扩大金额；以估价或预检冒充授权，均拒绝。R17 当前性、R07 权威预算合同及签名字段仍待审。

### C-S03 阈值历史定位与修订触发

- **推荐** · 稳定问题实体。原始问题、父问题引用、estimand、单位、目标总体、方向及 Scope 的科学实质变化列为新修订触发候选；实质阈值变更在批准生效后进入新修订。R05 追加 ThresholdEvent，使用精确 RecordLocator，字段为 action（proposed／approved／superseded）、prior_question_ref（初次可空）、target_question_ref、previous_terms（初次可空）、proposed_terms、reason_ref、seen_evidence_refs（受权精确集合）、prior_event_ref（首事件可空）、approval_ref（提出时 null，生效时必有适用批准）、recorded_at。先确定拟生效问题科学版本和阈值条款，再签署；批准定位与事件外置，避免循环。
| 触发或历史字段 | 精确规则 |
| --- | --- |
| 问题科学字段 | original_question、parent_question_ref（根问题为 null）、estimand、unit、population_ref、direction、scope_ref。按规范化后的完整引用或字段比较，有变化即要求新修订；仅注释、显示名、缓存、签发时间变化不触发。原始问题改写的语义等价规则暂排除。 |
| 生效阈值条款 | value、unit、direction、scope_ref、rationale_ref 纳入触发比较。proposed 不生效；approved 必须绑定拟生效问题精确版本及完整 ThresholdTerms。question_ref 是目标关联。拟生效问题的阈值科学输入为上述五项；问题 v2 完整投影尚待定。产生拟生效问题版本时排除其自身引用、批准定位及历史事件定位，之后才绑定该版本签署。 |
| 阈值事件定位及约束 | 精确 ThresholdEvent RecordLocator、tenant_id、project_id、action、prior_event_ref（首个为 null）、prior_question_ref（初次为 null）、target_question_ref、previous_terms（初次为 null）、proposed_terms、reason_ref、seen_evidence_refs（完整引用集合）、approval_ref、recorded_at。proposed 的 approval_ref 必为 null；approved／superseded 须指向权威适用批准。 |
| 暂排除 | 不定稿完整 ResearchQuestion 新科学版本域，不提供旧问题的自动迁移或把新阈值直接赋给旧锁定。拟生效版本必须有获准的目标投影；缺方法或已见数据依据时不生效。 |

- **备选及兼容** · 复用权威事件链的新事件类型，另定精确链位置及归属。保留当前 FixedQuestion v1 读法；完整问题字段、新修订触发准则和科学投影须审定，展示元数据沿用排除规则。
- **反例与依据** · 提议自动生效、降低阈值使旧结果达标、换单位用旧批准、遗失已见数据或跳接历史均拒绝。阈值数值和对正式推断的影响须有研究依据，已见数据须有审计依据。

### C-S04 单族 SelectionSet 与签名目标

- **推荐** · R05 提供版本化 SelectionSet，R06 关联单一固定四题族。建议以 HistoricalRef 按 SelectionSet 类型、稳定实体 ID 和精确内容版本定位；新科学版本域及投影保留待审。集合含 question_ref、considered_candidates、included_candidates、excluded_candidates（精确候选集合，先逐条核验）、selection_rule_ref、filter_event_refs、intervention_event_refs（有序历史引用）、history_basis_ref（独立上游历史截面）。纳入与排除互斥，均属于考虑过的候选。拟锁定族指向集合及上游截面；保留既有 FixedSelectionHistory.family_ref，新增上游截面不可反向指向拟锁定族。待审 family_confirmation 签名字段包含精确族、问题、集合、历史依据和首包适用条件；protocol_use 条款另行明确。
| 对象 | 推荐精确字段与投影 |
| --- | --- |
| SelectionSet 正文 | question_ref（HistoricalRef）、considered_candidates／included_candidates／excluded_candidates（完整 ScientificRef 无序集合）、selection_rule_ref（ScientificRef）、filter_event_refs／intervention_event_refs（完整 RecordLocator 有序列表）、history_basis_ref（上游清单 RecordLocator）。建议前七个字段进 selection_set:v1 科学投影；history_basis_ref 用于完整性核验及签名绑定。 |
| 拟锁定单族 | question_ref、scope_ref、selection_set_ref、history_ref 均须精确，family_confirmation 的条款建议覆盖 family_ref、question_ref、scope_ref、selection_set_ref、history_ref、history_basis_ref、test=null、family_alpha=null、family_alpha_reason。前者应在族科学版本计算后固定，签名和批准定位外置。 |
| 暂排除 | 完整族签名类型域及 protocol_use 的精确组件载荷尚未统一，先交付结构、同版比对和拒绝。多集合合并、通用统计族和跨问题冲突继续阻断。旧 FixedFamily 字节和有序列表不变。 |

- **备选及兼容** · 由 R06 将集合内嵌到新族版本并固定 R05 来源。两案均保留现有 FixedFamily 及有序目标字节。仅凭当前候选列表无法导出完整集合。多集合合并、跨问题冲突和通用统计族保持阻断。
- **反例与依据** · 候选同时纳入排除、缺筛选依据、改名重置暴露、注入抽样参数、历史与族版本循环均拒绝。族划分和反馈后确认须有独立依据。

### C-S05 A4／A7 返回白名单

**推荐** · 采用下表的精确白名单。所有定位返回前仍需按当前归属、任务、角色及委派核验，缺相应授权拒绝该视图。A7 的新增字段只在有权的受限审计包内返回。

| 角色 | 返回字段 | 约束 |
| --- | --- | --- |
| A4 摘要 | question_ref、family_ref、selection_set_ref、history_ref、coverage_status、blocking_reason_codes | 前四项均为 HistoricalRef，前三类目标和历史精确版本分别核验；coverage_status 为 complete／incomplete／unknown，blocking_reason_codes 为短代码集合。不得返回候选明细及历史事件。 |
| A7 受限审计包 | A4 六字段，另含 considered_candidate_refs、selection_rule_ref、filter_event_refs、intervention_event_refs、exposure_event_refs、history_cutoff_ref、completeness_basis_ref | 前两项为精确 ScientificRef 集合和单引用；后三组事件为精确 RecordLocator 有序列表；截面及完整性依据为精确 RecordLocator。正文、主体身份细节及许可等字段均不在白名单。 |
| 两类输出 | 仅上列字段 | 跨版本使用旧视图或输入夹带权威字段拒绝。视图投影与科学投影各自独立；覆盖状态、阻断码和权限裁剪不参与科学投影。 |

- **备选及兼容** · A4 维持已获准的阻断结果，A7 维持既有审计视图。旧记录缺历史时沿用 legacy_incomplete，未授权字段不补值。
- **验收反例** · A4 索取筛选或暴露事件，A7 缺受限审计权限仍读事件，同一科学对象因角色裁剪产生不同版本，均拒绝或保持原版本。

### C-S06 历史完整性依据

- **推荐** · 由 R05／R08c 独立提供 tenant_id、project_id、question_ref（HistoricalRef）、history_cutoff_ref（RecordLocator）、source_ranges（逐来源、含 source_id、first_cursor、last_cursor、manifest_sha256）、expected_event_refs（各来源顺序内的精确事件 RecordLocator 列表）、basis_ref（精确独立权威清单定位）。游标只在同源比较，实际完整性由各来源对精确范围、缺口及冻结截面作可核验证明。报告正文和预期清单的相同回显不足以证明完整性。
- **备选及兼容** · 沿用既有逐条可核验事实，缺独立覆盖证据时让整体历史保持不完整或未知。旧记录继续只读，禁止默认补齐。本项字段为审计与核验依据，不作为科学投影字段直接参与哈希。
- **验收反例及排除** · 遗漏范围尾部、过滤后宣称完整、游标错来源、改换同修订清单或欠缺 R08c 来源仍宣称完整，均阻断锁定。生产日志覆盖范围、游标语义及真实来源证明待各权威服务验收，不能由结构通过替代。

### C-S07 暴露引用衔接与新历史投影

- **推荐** · 在新增历史版本单列 exposure_events，每项含 event_ref（精确 DataExposure RecordLocator）、data_ref（精确 Dataset ScientificRef）和上游 history_basis_ref。建议集合按完整事件定位去重，同定位却绑定不同 Dataset 版本时拒绝；原事件的时间顺序由权威历史保留。逐项用现有 R08c 核验事件修订、主体、用途、归属与独立快照。若要进入新科学投影，须另审字段及版本域。保留 FixedSelectionHistory.test_exposures 原类型及固定四题空列表门槛。
| 新历史版本候选字段 | 科学投影及存放边界 |
| --- | --- |
| question_ref、selection_set_ref | 进入投影，均保留完整 HistoricalRef。SelectionSet 先按 C-S04 固定内容版本。 |
| exposure_events | 只拟纳入通过 R08c 核验的实际接触，每项投影含完整 event_ref 和完整 data_ref，按事件精确定位作为集合键。先按精确读取核验，同事件不同数据版本冲突拒绝。原时间顺序留在审计记录。 |
| history_basis_ref、覆盖清单、来源游标、归属、角色裁剪及状态 | 留在受信核验／审计层；缺权威依据仍阻断。actor、purpose 等事件事实通过精确事件版本绑定，历史投影不复制正文。 |
| family_ref | 新版本由拟锁定族引用历史，不反向写入拟锁定族版本。现有 FixedSelectionHistory 的反向字段继续按旧合同处理。 |
| 版本与排除 | 建议独立 selection_history:v2 域；须有完整已定映射才计算该版本。许可、接收方、其他暴露事件及无法判定事实排除在批准范围，影响相应历史时必须阻断。现有 test_exposures 不迁移、不转换，v1 固定四题仍要求空列表。 |

- **备选及兼容** · 先只在受限审计上下文携带事件定位，科学路径有暴露时继续阻断；待独立历史目标合同和投影获批再衔接。两案均无自动转换，Dataset 哈希或记录 ID 单独无法推导事件定位。
- **反例与依据** · 同一 Dataset 的两条事件互换、旧事件修订、跨项目、未接触作业冒充暴露、单条核验冒充历史全集或发送许可，均拒绝。通用用途、许可和接收方映射仍待 B 组决定。

## 同一纯契约实施包与验收

以下范围须以本节选项签收及实施授权为前提。允许在同一批纯契约中完成以下链路，输入由独立夹具提供，受信端口替身与期望值分别装配。

1. **验证上游材料与报告**。从受权的精确候选、Scope、数据和来源开始，逐条核验正文及版本。按 C-S01 消费报告与清单，核对独立当前性、逐项适用依据、六项结果及 blocked 优先。独立合成证据齐全时可得到纯契约 ready 结果；代码必须对实际依据缺失的正式路径继续拒绝。
2. **验证已有批准及新绑定合同**。先核验已有选题和阈值批准的精确条款，再用独立签名夹具验证 C-S02 载荷与报告、清单及预算范围的绑定；如需验证新阈值，按 C-S03 核对权威批准和追加事件。固定四题既有目标和已签旧条款可贯通。新增问题版本计算、实际预算依据或签发权缺失时，只验已明确的结构与守卫，正式选择签发保持阻断。
3. **核对单族、历史、授权视图及科学版本**。按 C-S04 关联单族和 SelectionSet，按 C-S05／C-S06 校验视图和来源覆盖，再按 C-S07 分别核验暴露事件和数据版本。可用经核验的独立合成历史验证新版投影及错配拒绝。仍以既有固定四题的空暴露历史贯通现行 Prereg 预映像，不把新历史或审计结果转换进 v1。任何实际覆盖或允许事件映射缺失均阻断相关科学路径。
4. **固定锁定前结果**。用预映像和现行批准证明已完成的只读子链。完整锁定前通过须另有 protocol_use 与 family_confirmation 的完整签名条款、适用历史覆盖、校准和预算证据。当前 check_lock 在已有条款核验后仍返回缺协议／族签名条款；不得以合成锁定回执消除阻断。真实 R06 事务锁定留服务验收。

| 验收项 | 通过标准 |
| --- | --- |
| 七组独立字节及摘要 | 同包纳入 FixedQuestion、FixedFamily、FixedSelectionHistory、SelectionTerms、ThresholdTerms、既有 ApprovalSubject、DataExposure 七组[手列向量](p1-2-c-selection-lock-vectors.md)。按现有正式类型或摘要入口比对原规范 UTF-8 和完整 SHA-256。每项注明现有入口、实际覆盖及待接入状态。 |
| 贯通夹具 | 现有向量的占位版本只保留作逐对象对照。链路夹具须用各自可核验的独立目标正文和由其独立重算的版本替换占位引用，并随之独立手列受影响的预映像和摘要。配齐当前授权、归属、精确版本、独立快照、现行签名和来源事实。测试同时断言确实读取并核验这些事实，序列化结果相同只计逐对象证据。 |
| 拒绝路径 | 七项逐项执行所列正反例。至少核对同修订成对替换、旧批准错版、权限缺失时受限快照与正文零读取、历史截断、事件／数据版本错配、固定四题拒绝抽样参数，以及缺协议或族条款时锁定前仍拒绝。未获批或缺独立依据的新增分支保持阻断。 |
| 发布证据 | 执行调用及接收两端契约、JSON Schema／OpenAPI、Ubuntu／Windows 同锁字节及摘要和同一交付 SHA 的 CI。保留[候选改版金样例](p1-2-candidate-revision-golden.md)、[第六批独立 Prereg 预映像](p1-2-batch6-delivery.md)、原九个金样例及手算。既有出口继续跟踪。 |

补充决定的批准与真实服务、预算执行、数据外发、建库、抽样、描述型及跨 Scope 分支分别管理。本包只验证纯契约。上述范围未取得实测证据。

## A0 补充决定签收栏（仅 C-S01～C-S07）

请在意见逐项注明编号与采用的推荐、备选或具体修订；未选择项保持待审。签收绑定本表与独立向量的审阅版本。原 C-01～C-05 签收和其他权限边界继续有效。

确认人：

日期：

意见：

验收结论：
