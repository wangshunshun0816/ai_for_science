# R02 首组契约提案（结构修订版）

日期：2026-11-12。起点：2c89500274682e3e2d550388382982704a333935。本版替换 f538edd 版本的首组提案；**只是实施文档，没有生成业务模型、正式内容 ID 或新的批准**。旧字段名只能在明确的测试/迁移适配器使用，不自动兼容生产输入。

依据：[A 大方案](<../Danus-AI 科研智能体产品架构与落地执行方案 v1.2 最终确认稿.md>) §3.9、4.1/4.2、5.1–5.3、6.9、6.16、附录 C；[G 开发指南](<../Danus-AI 落地开发指南：模块顺序、接口衔接与验收.md>) §3.4/5.3；[R 角色规格](<../Danus-AI Agent 角色实现与验收规格.md>) §3.2/3.5、4.2–4.5。A0 剩余选择见 [精简清单](decisions/A0-R02-first-contracts-checklist.md)。

标记：**D**=设计已经明确，直接落实；**E**=不改变科研/权限的工程组织选择，本文确定，不另列 A0 审批；**P**=涉及科研投影或权限语义，方案具体但仍待审。E 不代表已编写代码。所有字段均拒绝未知键；Text 为非空字符串，ID 为不透明标识，Int 不接受 bool，Decimal 为精确十进制字符串。列表、null、缺省在下文明确；科研数值附数值性质/依据，不能把角色自报值当 measured。

## 1. 四对象的草稿与权威边界

D：角色只提交建议，服务写身份、真实摘要、批准状态、测量事实及时间。E：每类分 Draft、Authoritative 两种合同；编辑器不完整保存使用单独 WorkingCopy（不具备锁定/运行资格），不降低 Draft 提交合同。下表“提交必填”不代表在 UI 每键输入后都要校验。

### 1.1 公共字段：仅权威记录

| 字段 | 类型/必填/null/缺省 | 写入与锁定 | 投影 |
|---|---|---|---|
| object_id | ID，必填非null，无缺省 | 所属服务分配稳定记录定位，不能由角色授予正式 ID | X |
| content_version | Version，服务派生，非null | 唯一正式科研版本字段；版本生成后固定 | 派生不自含 |
| tenant_id | 私有记录 ID 必填非null | 认证/领域服务绑定 | X |
| project_id | 项目级 ID 非null；租户级明确null | 服务核验；具体资源映射 P1 | X |
| ownership_scope | project/tenant；公开另用 public 记录类型 | 服务生成，不能靠 tenant=null 公开 | X |
| created_at / created_by | UTC时间 / ID，分别必填非null | 服务器时钟/认证主体 | X，审计 Q04 |
| status | 仅 Candidate/Protocol/Prereg 有，对应 A §5.3 | 各权威服务写，转换完整边集 Q06 | X |
| approval_bindings | ApprovalLocator[]，必填，未有批准为[] | R09/领域服务；集合按目的/record/revision精确去重 | X |
| comment / display_name / cache_location | 分别可省略；出现为 Text 或null，不填默认 | 服务按权限维护，不能存科研定义 | X |

**RunRequest 没有 status、scientific_validity 或 attempt_id 字段。** queued/running/collecting 等属于 Attempt；valid/invalid/incomplete 属于运行科学资格记录，不能由进程成功推定。RunRecord 保存定义引用和尝试事实，不再建立第二份可改的运行定义（D：A §5.1–5.3）。

E：统一采用 object_id/content_version；candidate_id/protocol_id/prereg_id/version_ref 是旧 DTO/fixture 别名，明确适配后映射，生产拒绝双名和旧名；run_id 表示锁定运行定义，映射其 content_version 的类型化 ID，不另造不同版本权威源。原九个 JSON 和手算保持不变。

### 1.2 逐字段 Draft→Authoritative 表

约定：D栏“写”表示提交时必填，且无缺省；“禁”表示 Draft 根本没有此字段。权威栏“同”表示服务验证后原值入科学版本；“解析”表示从可信来源产生，不接受模型给出的权威事实。除标明 ? 的 nullable 字段和 §3 模式矩阵外均非null。S=直接科学投影，R=科研引用投影，H=历史实体投影，X=仅权威/授权事实。投影的具体语义仍由 P2/P3/P4 审定，不是生产默认表。

#### CandidateHypothesis（A §5.1/C.2；R §4.2；R05 权威）

| 字段 | 类型/顺序/null | Draft | Authoritative | 投影 |
|---|---|---|---|---|
| background | Text | 写 | 同 | S |
| sources | SourceRef[] 集合，可[] | 写 | 同，核对来源 | R及位置 S |
| new_inference | Text | 写 | 同 | S |
| prediction | Text | 写 | 同 | S |
| draft | DraftText={format:"plain_text",body:Text} | 写 | 同 | S |
| original_source | SourceRef?，分支见§6 | 写 | 同 | R及位置 S |
| source_kind | original/external_reported/synthetic_design | 写 | 同 | S |
| scope_ref | ScientificRef | 写 | 同 | R |
| synthetic_origin | local/external?；仅synthetic_design非null | 写 | 同，分支§6 | S |

草稿不拥有 object_id/content_version；修订目标用外部操作参数 expected_version，而不是让草稿自授版本。每次科学变更新版本；选中状态不改变内容摘要。

#### Protocol（A §5.1/C.2/6.16；R §4.3；R04b 权威）

| 字段 | 类型/顺序/null | Draft | Authoritative | 投影 |
|---|---|---|---|---|
| design_type | finite_population_enumeration/comparative_sampling/descriptive | 写 | 同；类型分支 P2 | S |
| dataset_ref | ScientificRef | 写 | 同 | R |
| split_ref | ScientificRef? | 写 | 同；null必须理由 | R |
| split_not_applicable_reason | Text?，与 split_ref 恰有一个非null | 写 | 同 | S |
| metric | MetricSpec，见§6 | 写 | 同 | S |
| baseline_refs | ScientificRef[]集合；比较非空，描述型可[] | 写 | 同 | R |
| tuning_space | ParameterRange[]集合，name唯一，可[] | 写 | 同 | S |
| sanity_suite_ref | ScientificRef | 写 | 同 | R |
| applicability_template | ScientificRef | 写 | 同 | R |
| evaluation_unit | unique_item/independent_sample/cluster | 写 | 同 | S |
| required_items | ID[]集合；固定枚举非空，其他[] | 写 | 同 | S，数据内局部ID |
| duplicate_policy | 显式 Q07 已批准策略值；无默认 | 写建议 | 解析/核验批准，不自选策略 | S |
| missing_policy_ref | ScientificRef<MissingPolicy> | 写 | 同 | R |
| approval_ref | ApprovalLocator?；未批准null，approved非null | 禁 | R09/R04b解析 | X |

#### Prereg（A §5.1/6.9/C.2；R §4.4；R06 权威）

| 字段 | 类型/顺序/null | Draft | Authoritative | 投影 |
|---|---|---|---|---|
| candidate_ref | ScientificRef<CandidateHypothesis> | 写 | 同，精确批准版本 | R |
| protocol_ref | ScientificRef<Protocol> | 写 | 同，精确批准版本 | R |
| question_ref | HistoricalRef<ResearchQuestion> | 写 | 同 | H，P3 |
| family_ref | HistoricalRef<FamilyDeclaration> | 写 | 同；替代裸 family_id | H，P3 |
| selection_history_ref | HistoricalRef<SelectionHistory> | 写 | 同；不复制另建历史事实 | H，Q04边界 |
| randomness_plan | RandomnessPlan，见§6 | 写 | 同 | S |
| discrimination_plan | DiscriminationPlan，见§6 | 写 | 同 | S |
| family_alpha | Decimal?；固定枚举null，采样0<α<1 | 写 | 同，核对族分配 | S |
| family_alpha_reason | Text?；alpha为null时必有，否则null | 写 | 同 | S |
| arms | Arm[]有序；比较至少2，描述型单独分支 | 写 | 同 | S |
| estimand | Text | 写 | 同，与问题/协议一致 | S |
| test | ScientificRef<TestSpec>?；固定枚举null | 写 | 同 | R |
| analysis_ref | ScientificRef，锁定分析脚本/包版本 | 写 | 同；独立校准核验 | R |
| failure_policy_ref / retry_policy_ref | 分别 ScientificRef<FailurePolicy/RetryPolicy> | 写 | 同；明确失败/重试规则，不按结果挑尝试 | R |
| inference | exact_finite_population_only/sampling | 写 | 同 | S |
| missing_policy_ref | ScientificRef<MissingPolicy> | 写 | 同，与协议相容 | R |
| selection_feedback_policy_ref | ScientificRef<FeedbackPolicy> | 写 | 同 | R |
| stop_rule | StopSpec，§4 | 写 | 同，锁定后唯一试验停止权威 | S |
| selection_ref / threshold_decision_ref | 分别 ApprovalLocator，正式锁定必有 | 禁 | R06按候选/问题解析有效A0决定 | X |
| selection_terms | 已批准候选/范围/意义阈值的语义投影 | 禁 | 从 selection_ref 精确记录解析 | S，P4 |
| threshold_terms | 问题/值/单位/方向/范围/理由版本 | 禁 | 从 threshold_decision_ref 解析 | S，P4 |

E：不存独立 effect_threshold 副本，读视图提供 threshold_terms.value；不存独立 candidate_version_ref/family_id/family_declaration_ref 别名。显式 fixture 适配器须比对原值一致而不是覆盖。方法代码通常由 A5 在 Prereg 锁定后形成（A §6.9），因此 Arm 不强求尚不存在的代码 commit：Arm={arm_id:ID,role:reference/candidate/descriptive,method_spec_ref:ScientificRef,baseline_ref:ScientificRef?}，方法设计与实际实现引用分开。

#### RunRequest（A §3.9/5.1/5.2/6.16；R §4.5；R08 权威）

| 字段 | 类型/顺序/null | Draft | Authoritative | 投影 |
|---|---|---|---|---|
| mode | 八模式，§3 | 写 | 同，核验发起角色 | S |
| code_ref / image_ref / data_ref | 分别 ScientificRef | 写定位建议 | 服务核实实际 commit/digest/manifest | R |
| method_config_ref | ScientificRef<MethodConfig> | 写 | 同，独立配置版本 | R |
| seed | Int?；deterministic时null，否则随机计划确定值 | 写建议 | 同/计划解析；不能挑结果有利种子 | S |
| deterministic | Bool | 写 | 同但需方法核验 | S |
| arm_id | ID?，§3 | 写 | 在锁定计划内核对 | S |
| prereg_ref | ScientificRef<Prereg>?，§3 | 写 | 同/核验锁定 | R |
| replicate_index | Int?，普通null；API复现预声明非负 | 写建议 | 锁定复现计划核验 | S |
| mode_inputs | 按mode区分的§3具名引用，不接受任意键 | 写 | 服务核验具体版本 | R/H，授权部分X |
| budget_request | {purpose:Text,estimated_cost:NumericValue?} | 写，无估价时null | 仅建议；不能扩大额度 | X |
| execution_binding_ref | ScientificRef<ExecutionBinding> | 禁 | 服务根据独立依赖构造 | R中仅科学部分，P2 |
| sanity_ref | RecordLocator<SanityReport>?，§3 | 禁 | R10a/R08核验结果与当前绑定 | X |
| authorization_receipt | RecordLocator<RunAuthorization> | 禁 | 每次准入由R09/R08生成 | X |
| budget_binding / safety_limits | §4的权威结构 | 禁 | R07/R08/R08b解析 | X，P2 |

普通角色只能给代码/镜像/数据定位建议，真实摘要由服务补全；不能把“允许引用”误作“允许填有效批准”。运行的已解析记录没有把相同科学字段再存一份可编辑覆盖值。

## 2. 引用类型与正式版本（E；权限原则 D，投影 P）

| 类型 | 精确字段（均必填非null，无缺省） | 用途/规则 |
|---|---|---|
| ScientificRef | object_type:Text, object_id:ID, content_version:Version | 内容版本引用；Version 为类型/哈希版本/完整摘要，不用latest；服务先限定归属后核实 |
| HistoricalRef | object_type:Text, entity_id:ID, content_version:Version | 科学历史实体与内容同时绑定，不能因内容相同合并族/问题/暴露；科研投影 P3 |
| RecordLocator | record_type:Text, record_id:ID, revision:Int≥0 | 事实记录定位，不冒充科研摘要 |
| ApprovalLocator | purpose:§5枚举, record_id:ID, revision:Int≥0 | RecordLocator专用形状；用于A0决定，解析 actor/target/状态，不凭出现即批准 |
| PublicRef | namespace:"public", ref:ScientificRef, admission:RecordLocator<PublicAdmission> | 独立公共准入；无 tenant=null 隐式放权 |
| PrivateResolvedRef | ref:ScientificRef或HistoricalRef, tenant_id:ID, project_id:ID或null, authorization:RecordLocator | 服务独占；租户级null也要项目使用授权 |
| PublicResolvedRef | namespace:"public", ref:ScientificRef, admission:RecordLocator, use_authorization:RecordLocator | 服务核验准入/撤销及当前用途，和私有结构分型 |

私有请求中的 ScientificRef 不包含有效身份；公共分型允许显式请求准入引用，服务仍核验。不同服务的 record_type/object_type 白名单工程固化，不靠自由字符串寻找任意服务。错误：不可访问统一 REFERENCE_UNAVAILABLE，不泄漏异租户存在性；有权限才返回 VERSION_MISMATCH、REFERENCE_TYPE_MISMATCH；批准失效 APPROVAL_INVALID，字段冲突 CONTRACT_CONFLICT。名称 E，不新增权限决定。

唯一正式字段 content_version 用于对象与科研引用；revision 仅是记录修订序号，schema_version 是结构版本，三者不互换。历史链摘要/事件ID算法保留 Q04，不以 revision 充当防篡改证明。

## 3. 八种运行模式矩阵（前置 D；字段组织 E）

每个 RunRequest Draft 均要求 mode/code_ref/image_ref/data_ref/method_config_ref/deterministic/seed/arm_id/prereg_ref/replicate_index/mode_inputs/budget_request；无隐式缺省。B=必填非null，N=显式null且不适用（不得为取得更强资格而填无关对象），C=下述条件决定，不是任意可选。所有模式都有任务/有效委派、预算和数据授权；这些从受信上下文解析，不由模型自报。seed 在全部模式：deterministic=true 为 N，否则 B；replicate_index 仅预声明API复现为 B，其余 N。实际随机性分配须在运行前锁定，不能运行后补。

| mode/发起者/数据 | prereg_ref | arm_id | 额外 mode_inputs（全部B，除注明） | suite/profile | sanity_ref（权威） |
|---|---|---|---|---|---|
| exploration / A2 / dev | N | N | task_ref；探索额度由服务解析 | N；基础检查 profile=exploration_lite | N；不要求既有正式报告 |
| baseline_dev / A3 / synthetic或dev | N | N | protocol_draft_ref,task_template_ref；校准额度服务解析 | 校准任务要求套件时B，否则N并记录适用依据；exploration_lite | N |
| analysis_calibration / A4或A6 / synthetic/dev或受控模拟 | N | N | analysis_draft_ref,calibration_suite_ref | B；exploration_lite，校准配置精确版本 | N |
| dev / A5 / dev | C | C | selection_candidate_ref,protocol_ref；服务解析有效选题决定/额度，调参空间取协议 | 套件适用时B否则N；exploration_lite | N；不以报告豁免基本检查 |
| val / A5 / val | C | C | 同dev，切分授权必须val | 同dev | N |
| sanity / A3/A5/A6 / synthetic或dev | N | N | sanity_request_ref（待检查代码/环境/套件精确绑定） | B；由批准检查合同选profile，不由角色skip | N，绝不引用本次将生成的报告 |
| confirmation / A5 / hidden confirmation | B，锁定 | B，锁定Arm中存在 | protocol_ref；有效选题/阈值/族/分析批准服务解析 | B，confirmation_full | B，匹配当前binding且必需项合格 |
| replication / A10 /原数据或预注册新数据 | B，原/适用预注册 | B，锁定复现计划的Arm映射 | original_claim_ref,replication_plan_ref（锁定） | B，confirmation_full | B，匹配本次代码/数据/配置 |

**dev/val 的 C 明确条件：** A §3.9 不把正式锁定 Prereg 列为统一前置，而 R §4.5 的 A5 实现任务输入列含锁定 Prereg。不能仅以命名消除此差异：本提案按 task_kind 的已批准合同判断；若该合同要求锁定Prereg则B、arm绑定该计划，否则N，不准客户端自行选分支。未有明确 task_kind 合同则阻塞该分支；由剩余 P5 决定是否首批统一采用更严格的B。此冲突不影响 exploration/sanity/analysis_calibration 的明确豁免。

### 3.1 无循环的绑定图

E：MethodConfig 不含 RunRequest/run_id、ExecutionBinding 或 sanity报告引用。ExecutionBinding={code_ref,image_ref,dependency_ref,data_ref,split_ref?,method_config_ref,protocol_ref?,suite_ref?,validation_profile_ref}；均为独立已存在对象，nullable由上表和适用合同确定。data/split/code/dependency的摘要由可信服务核验。没有套件模式的suite明确null，profile仍指适用基础检查规则，不编造批准协议。

SanityReport.binding_ref→ExecutionBinding；RunRequest.execution_binding_ref→ExecutionBinding；RunRequest.sanity_ref→报告（X），**ExecutionBinding 不反向引用 RunRequest 或报告**。授权/批准变化另由报告的 approval_bindings 与当前有效性核验使报告 stale（A §6.16），不把批准对象循环嵌入其自身科学摘要。sanity_request_ref 的目标 SanityRequest 也只含独立依赖，不含本次运行引用。configuration_ref 旧名迁移到 method_config_ref，禁止指含它的父对象。

## 4. 方法、科学限额和停止规则：只有一个权威值

| 内容 | 唯一保存位置/写入者 | 下游使用方式/冲突规则 |
|---|---|---|
| 具体算法参数、精度、硬件科学约束 | MethodConfig；实现角色提议、R08验证，按协议允许范围锁定 | parameters 为 name唯一的 typed集合；不得再含 max_steps/max_output_tokens/stop_rule 等保留名 |
| 算法内部限额 | MethodConfig.science_limits={max_steps?,max_output_tokens?,method_wall_time_seconds?,method_memory_bytes?}；正数或null显式不适用 | ScienceLimits 只是此子结构，不在 RunRequest/resource_limits 另存一份；若已属预注册规则，必须满足其精确约束 |
| 试验级采样/评价停止条件 | 确认时 Prereg.stop_rule；复现时锁定 ReplicationPlan 的停止规范（不得暗改原方法） | MethodConfig 不含 stopping；RunRequest 不含stop_rule；只读解析，不允许覆盖/取min/取max |
| 非确认任务停止 | mode_inputs 中任务/协议校准/分析校准/检查任务的 stop_spec（§6） | 由相应任务权威服务锁定；不是空白检查 |
| 纯付款额度 | R07预算/批准记录，RunRequest.budget_binding仅引用 | max_cost_minor/currency/purpose 来自授权；角色估价不成为额度，不进入科研投影（P2） |
| 纯基础设施保护 | R08/R08b批准资源策略；safety_limits={wall_time_seconds?,memory_bytes?,lease_deadline?} | 只有不定义方法时X；保护中止不能缩分母/自动判科学否定，状态边Q06 |

D：科学语义改变必须新版本/适用批准；运行授权不能扩大额度。P2：混合用途限制在 science_limits（S）登记，同时受预算硬约束；保护限额更紧造成提前中止，保留尝试事实并按协议判完整性，不重解释为原设计完成。

E冲突拒绝：同名参数重复、旧resource_limits携带科研覆盖值、方法配置与锁定规则不同、单位不一致、方法范围越界一律 CONTRACT_CONFLICT；没有“最后一个值胜出”。StopSpec={kind:complete_items/fixed_count/registered_rule,required_items:ID[]集合,sample_count:Int?,rule_ref:ScientificRef<StopRule>?}，分支恰一项有值（集合空相当无）：枚举完整items；固定量count>0；注册规则必须能解析阈值/窗口/单位/检查频率及独立参考。尚缺的具体规则不可运行。

## 5. 批准、锁定和授权动作完整表

D：**每次运行由服务核验已有批准、权限、数据和预算，不新增 A0 每run签字。** A0负责选题/价值、协议、意义阈值、预算与数据权限等设计规定的决定；R06执行锁定。prereg_lock、run_authorize 是工程操作名，不伪装为新增人工批准purpose。依据 A §3.9、4.1/4.2、6.9，R §4.4/4.5。

| purpose/操作（E命名） | 决定者/执行者 | 目标版本 | 前置条件 | 重新批准/重新校验 |
|---|---|---|---|---|
| candidate_selection（Approval） | A0决定；R09登记/R05引用 | 候选精确版本+范围+阈值条款 | R17适用检查、范围/价值及预算范围明确 | 候选核心/范围/意义阈值变更须新决定；旧决定不覆盖 |
| protocol_use（Approval） | A0批准；R04b登记 | Protocol精确版本及组件/套件 | 审核/适用性/独立参考通过 | 科研字段/适用性变化新版本新批准；撤销使使用失效 |
| meaningful_threshold（Approval） | A0决定；R09/R06引用 | ResearchQuestion历史实体+范围+阈值/单位/方向 | 先于确认输出；保留提出/批准/修改历史 | 降阈值/换目标须新设计路径，不能事后覆盖 |
| family_confirmation（Approval） | A0按管理批准路径；R06锁定 | FamilyDeclaration版本、槽位/α/历史 | 问题/候选/选择/暴露一致；首次确认前锁定 | 改族/槽位/分配不得消除暴露或重置检验；新增设计重新核查 |
| budget_use（Approval） | A0授权；R07核验/预占 | 预算记录revision、用途/额度/归属 | 有真实授权、计价单位/范围 | 扩额/换用途/付款归属另批；使用前每次重验 |
| data_use（Approval/许可） | A0批准政策；R08c按许可执行 | DataPolicy/Permit版本、数据/切分/用途 | 来源/许可/伦理/地域/角色适用 | 变更/过期/撤销重新授权；历史暴露不清零 |
| prereg_lock（服务操作） | A4申请；R06验证和锁定 | Prereg精确科学版本 | 有效选题/协议/阈值、族历史、随机性/分析独立校准、预算可行；R17条件满足 | 新科学内容新版本及适用上游批准；看过结果后新设计/新数据授权；不另加逐份人工签字 |
| run_authorize（服务操作） | 模式准许角色申请；R09/R08/R07/R08c核验 | 锁定运行定义+所需批准记录revision | §3模式条件、当前身份/租约/预算/数据/代码/配置/sanity | 每次准入重验；代码/数据/种子变新定义，旧sanity不可用；基础设施重试保留run但新增attempt |
| public_admission（准入记录） | 具权限操作者按资源准入；服务登记 | 公共资源精确版本/许可/用途 | 明确公开许可，不由复用自动公开 | 版本/许可/公开范围变更重新准入，撤销停止新使用；启用范围P1 |

ApprovalRecord最小形状：record_id/revision/purpose、target（ScientificRef或HistoricalRef或具名预算/数据RecordLocator）、terms_version、actor、decided_at、effective_scope、valid_until?、revocation_ref?；身份/时间服务填写。signature载荷/域/算法字段最终形状依Q05，本轮不定稿。RunAuthorization是事实记录：record_id/revision、run_definition_ref、validated_approvals[]、data_permit_ref、budget_reservation_ref、actor、checked_at、result；**不能放进 approval_bindings 冒充 A0 新批准**，审计身份依Q04。

P4科研条款直接投影：selection_terms={candidate_ref,scope_ref,meaningful_delta}；threshold_terms={question_ref,value,unit,direction,scope_ref,rationale_ref}。从批准记录解析，A4无写权；相同值不豁免批准有效性核验。批准记录只引用其target，不被target科学内容递归引用；内容含条款而非批准ID/签名。纯预算改动不改变科学版本（P2），仍要新授权；不要求对无关对象全部重批。

## 6. 来源、集合、历史与目标规范

### 6.1 来源分支（结构E；科学来源语义P3）

SourceRef={snapshot_ref:ScientificRef,location:SourceLocation}；SourceLocation={kind:page/line/section/whole_document,locator:Text}。source项与位置一一对应，不靠平行数组猜映射。original_source 使用同型。
- original：original_source=null；sources可为空或含背景文献，不能把引用背景误当原始外部主张。
- external_reported：original_source非null并含精确位置，sources须包含该源位置；不变成本系统measured。
- synthetic_design：original_source=null表示本项目合成设计；若基于外部合成案例则非null并保留来源位置。两种情形由额外必填 synthetic_origin=local/external 明确区分；其他source_kind的synthetic_origin=null。
sources规范化后相同snapshot/version+location才是同一项；同一个源不同位置不去掉。原九题 synthetic_design 通过显式测试包装添加local，不修改原数据。

### 6.2 历史实体与集合

P3推荐：候选/协议/代码/数据引用科学投影为 object_type+content_version；问题、族、选择集合/选择历史、数据暴露历史用 HistoricalRef，保留entity_id+content_version，不因同内容合并不同族/历史。entity_id为归属内稳定语义标识，权限仍单独限定；审计actor/time/链hash不直接混入科学历史版本，具体科学/审计字段切分仍依Q04。family_id旧名只映射family_ref.entity_id，不能同时接受两个独立值。

E集合算法：先逐项严格校验→字段投影→NFC/换行/十进制→JCS字节；对**已声明集合**按完整字节升序并去除完全相同项。name/arm_id等标识相同但内容不同拒绝，不能当两项或后写覆盖。SourceRef以科学版本+位置完整字节为键；HistoricalRef保留entity。参数/依赖前置集合按相同规则；arms、cluster_levels、选择事件顺序、反馈轮次保持原序，不全局排序。观测行是否去重是Q07，绝不使用本集合算法擅自裁决样本。

### 6.3 目标规范与子结构的具体合同

以下每个子字段均必填无缺省；?允许显式null；[]规则写明。结构/单位/错误组织E；阈值、适用性和算法/采样方法P/Q依赖不能由工程设默认。所有目标有公共 {schema_version,content_version,owner_service}，内容生成版本；解析时核验归属/类型/版本/适用状态，缺任一目标报 SPEC_UNRESOLVED、不可锁定/运行。目标清单不是已存在资源或通过资格声明。

| 目标/子结构 | 具体字段与校验方案 | 权威/依据/待审边界 |
|---|---|---|
| NumericValue | value:Decimal,unit:Text,nature:六类枚举,basis_ref:ScientificRef或RecordLocator；external需source位置，reference_derived需inputs[]+derivation | A §5.1；角色不能自填可信measured；具体测量合同后续 |
| MetricSpec | name,unit,direction:maximize/minimize,implementation_ref | R04b；单位取版本化指标注册项，不增全局随意单位枚举；C.2 accuracy用比例单位；P2 |
| ParameterRange | name,kind:integer/decimal/categorical,lower?,upper?,lower_inclusive:Bool,upper_inclusive:Bool,step?,values:Text[]集合,unit,selection_rule_ref | 数值下界≤上界，步长正且可达；integer整数界/步长；categorical两界/step=null、inclusive=false、values非空；P2科研范围待审 |
| MethodConfig | method_spec_ref,parameters:{name,kind,value}[]集合,precision,hardware_semantics_ref?,science_limits | R08核实；方法代码独立；参数保留名冲突拒绝；§4 |
| MissingPolicy | evaluation_unit_ref,expected_universe_ref,missing_definition,action:incomplete/reject/registered_adjustment,adjustment_spec_ref?,reason | R04b/R06；非调整时ref=null；固定枚举缺题incomplete已有依据，采样调整必须独立规范，不能缩分母；A C.5/6.9 |
| FeedbackPolicy | allowed_fields:Text[]集合,allowed_roles:角色[]集合,phase,maximum_rounds:Int或null,exposure_rule_ref,stop_spec | R08c/R06；受权限/预注册限制，不能配置开放隐藏标签；A §3.6/6.9 |
| TestSpec | estimand_ref,operator_ref,comparison_refs[]有序,alpha_allocation_ref,multiplicity_ref,unit_spec_ref,assumptions[]集合,calibration_ref | R11算子/R06引用；未注册方法须独立参考与校准，P2不批准具体检验；R §4.4 |
| RandomnessPlan | seed_generalization_target,random_sources:RandomSource[]集合,repetitions:Int?,unit_spec_ref?,cluster_levels:ScientificRef[]有序,estimation_method_ref?,reason? | 不适用则sources/levels=[]、其余null、reason必有；适用次数正且单位/方法有ref；A §5.1/6.9 |
| RandomSource | name,kind,seed_schedule_ref,independence_basis_ref | 同名冲突拒绝；种子不是独立数据单位；具体随机性模板P2 |
| UnitSpec | evaluation_unit,unit_key_fields[]有序,population_ref,sampling_frame_ref?,cluster_mapping_ref?,repetition_mapping_ref?,independence_basis_ref | R11/R06，区分单位/簇/重复；采样/聚类要求对应映射，不能以增行数替代；A §6.9 |
| DiscriminationPlan | applicability,explanations:ScientificRef[]集合,predictions:Prediction[]有序,observable_differences:Text[]有序,minimal_design_ref?,indistinguishable_conditions:Text[]集合,reason? | 适用至少两个解释且预测覆盖每个解释；不适用列表[]、design=null、reason必有；A §5.1/8.5 |
| Prediction | explanation_ref,observable_ref,prediction_spec_ref | 显式映射，无平行数组；预测目标版本须存在，不以长度相同替代覆盖 |
| MinimalDesign | contrast_refs[]有序,measurement_refs[]集合,unit_spec_ref,identification_conditions[]集合,stop_spec,independent_reference_ref | R06分析设计，设计有效性需方法复核P2；不因字段齐全赋科研资格 |
| SelectionRule | candidate_universe_ref,rule_spec_ref,inputs[]集合,exposure_constraints_ref,independent_reference_ref | R05/R06记录选择过程；rule_spec需精确可复核算法/规则全文，不能只填名称 |
| FailurePolicy | failure_categories[]集合,classification_rule_ref,missing_policy_ref,reporting_requirements[]集合 | R06/R11；A §6.9要求失败规则；不能把系统error当科学否定；具体规则P2、状态Q06 |
| RetryPolicy | allowed_infrastructure_reasons[]集合,max_attempts:Int或null,eligibility_rule_ref,selection_rule_ref,stop_spec | R06/R08；A §5.3/6.9；默认首个有效完整尝试的原则不变，多完整尝试按预注册规则；不得按结果选优 |
| StopRule | rule_spec_ref,thresholds:NumericValue[]有序,window:NumericValue?,evaluation_frequency:NumericValue,unit_spec_ref,independent_reference_ref | R06/任务领域服务；科学值需预先批准/校准，引用缺失阻塞；§4 |
| TaskStopSpec | task_kind,stop_spec,authorization_basis:RecordLocator | 非确认任务停止规则绑定任务模板；无已批准任务合同不能自由运行 |
| PublicAdmission | record_id,revision,resource_ref,license_ref,allowed_uses[]集合,approved_by,approved_at,expires_at?,revocation_ref? | 具权限操作者/服务；公开范围P1；记录链/签名Q04/05 |

以上给出必需内容与核验入口；具体 reference 数据、独立方法依据、注册算子/单位/适用性资源仍待提供，不能宣称“有表就可用”。未实现研究轨道可以明确blocked，但不缩减 G 的全R02最终范围。

## 7. 可逐项选择的 A0 决定（已压缩为5项）

| ID/原问题映射 | 具体推荐及影响 | 备选/未决边界 |
|---|---|---|
| P1（Q03-1）归属与公开启用 | 候选/预注册/运行项目级；Protocol允许租户级复用，项目使用另授权；public独立准入 | 首批仅项目级，跨项目/公共暂不启用；影响可用能力，不改变权限红线 |
| P2（Q01-1～5）首组科学字段/模式与方法资源投影 | 采纳§1/3/4/6科学形状；纯预算/保护外置、方法限制入科学内容；各研究类型仅在目标规范/独立参考齐备后启用 | 可只批准固定枚举首包，其余明确blocked；特别需审定来源/列表语义、资源分界、采样子结构，不能统称原则同意 |
| P3（Q03-3/Q04）历史身份与来源投影 | 按§6将历史实体ID保留，普通内容引用不含工作ID；SourceRef包含精确位置 | A0可指定额外需保留稳定ID的引用；Q04未关闭的历史科学投影不能最终冻结 |
| P4（Q02-2）批准科研条款 | 直接投影selection_terms/threshold_terms；批准定位/身份/时间外置，当前权限仍核验 | 独立条款摘要方案增加对象及迁移；任何方案不得循环含签名/自批准 |
| P5（Q01-4，设计交叉条款）dev/val前置 | 推荐按已批准task_kind区分是否需要锁定Prereg，未有合同就阻塞分支；A5正式实现任务按R §4.5严格要求 | 首批dev/val统一要求锁定Prereg，更保守但收窄A §3.9允许的调试组织；明确选择后写模式守卫 |

Q03-2字段组织、唯一content_version、RecordLocator拆分、错误码、集合实现顺序不再单独请A0批准。Q02-1“是否每run人审”按设计关闭为服务核验；Q02-3科研变更新版本/适用批准是已定规则，纯预算例外随P2。以上不是宣称P1～P5已获批准。

Q04审计链/历史科学投影、Q05签名载荷、Q06完整状态边与保护中止分类、Q07重复观测策略保持独立未决。它们阻塞对应生产合同，不阻塞本轮文档修订。

## 8. 缺口关闭记录与验收边界

| 原清单§4缺口 | 本轮处置 | 剩余 |
|---|---|---|
| 草稿/权威与RunRequest状态 | §1逐字段分离；RunRequest不含status，Attempt/运行资格分开 | Q06边集 |
| 双版本名/两种引用 | §1/2唯一content_version；科研/历史/批准/事实定位分型 | Q04/05记录摘要/签名 |
| 来源分支 | §6 synthetic local/external与精确位置挂载 | 科学投影P2/P3 |
| 目标规范/类型分支/计划映射 | §6具体字段、边界、显式解释→预测关系及独立单位 | 实际方法参考资源未提供不可启用；P2 |
| 八模式/绑定循环 | §3完整矩阵，独立依赖无反向引用 | dev/val设计交叉条款P5 |
| 停止规则重复 | §4唯一保存位置，所有重复/越界拒绝 | 科研分类P2，中止Q06 |
| 批准动作 | §5明确A0决定与服务lock/authorize，不新增逐run签字 | 科学条款P4，签名Q05 |
| 历史/集合 | §6历史实体例外和字节排序去重、同键异值拒绝 | P3/Q04，观测去重Q07 |

后续验证（本轮未执行）：草稿注入权威字段拒绝、模式null/必填矩阵、循环引用拒绝、冲突规则拒绝、同内容不同历史不合并、公共/私有隔离、撤销/错版本批准拒绝、科学限制/预算变更对照、旧fixture显式迁移。三份设计基线及原九题不改，不新增代码/数据库/依赖。Windows CPython 3.12 缺失与跨平台一致性仍待办；第二批代码的远端CI成功事实不因本次文档修订升级为业务验收。
