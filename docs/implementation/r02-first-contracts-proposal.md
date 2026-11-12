# R02 首组完整字段合同提案（第二批）

日期：2026-11-12。**待 A0 审定，未生成业务模型或生产投影。** 本表是四类对象的闭合字段形状提案；外部版本化规范仍须各领域负责人提供内容及审阅，不能以 ref 代替内容完整性校验。所有表内建议均需批准，不能把“必填”读成设计已经确定。

依据：[大方案](<../Danus-AI 科研智能体产品架构与落地执行方案 v1.2 最终确认稿.md>) A §3.9、5.1–5.5、6.4、6.9、6.16、附录 C；[开发指南](<../Danus-AI 落地开发指南：模块顺序、接口衔接与验收.md>) G §3.4/5.3；[角色规格](<../Danus-AI Agent 角色实现与验收规格.md>) R §3.2/3.5/4.2–4.5。衔接 [首批全对象台账](r02-field-matrix.md) 和 [Q 草案](r02-decisions.md)。本表只细化 CandidateHypothesis/Protocol/Prereg/RunRequest，不替代其余对象的未决状态。

## 1. 统一规则与精确引用

Text=非空 Unicode 字符串；Int=严格整数不接受 bool；Bool=严格布尔；DecimalText=精确十进制字符串；ID=非空不透明标识；Version=类型/版本化完整摘要，不接受 latest。所有字段**无隐式缺省**：标为必填的必须出现；仅表内显式 null 分支允许 null；其余一律非 null；标量列表顺序列为“—”。空集合 [] 与缺字段/null 不等价。所有对象/子对象 extra forbid；科学字段变更新版本。

S=科学投影直接参与；R=引用的类型及精确内容版本参与，访问身份/记录定位外置；X=排除科学投影但仍持久保存并核验权限/审计。X+R=批准定位本身外置，已批准科研条款明确另投影；M 必须按子字段拆分。任何新增字段不允许默认为 X。字段出处使用对象标题的章节；Q 编号是需要审定的具体条目，见 §7。

Ref 的请求形状：私有为 {object_id: ID, version: Version}（两个键均必填非 null，无缺省）；公共为 {namespace: "public", object_id: ID, version: Version, admission_ref: AdmissionLocator}（全必填），AdmissionLocator={record_id: ID, revision: Int}，不得递归无限 public ref。R 投影为 {object_type: Text, content_version: Version}，由服务解析，不直接相信模型的 version。相同科学版本的不同工作记录在科学层可以等价，但授权不等价；是否需保留稳定 object_id 的科学意义按 Q03-3 决定。来源引用附 SourceLocation={locator:Text, snapshot_ref:Ref}，用于定位原文页/行/段，定位规则亦锁版本。

内部 ResolvedRef={namespace,tenant_id,project_id,object_type,object_id,content_version,authorization_ref}，仅服务生成。private 项目对象 tenant/project 非 null；租户级资源 project_id 明确 null 只表示租户级，仍有 tenant 且核验项目可用授权；public 使用另一结构及准入，绝不靠 tenant=null 放权。授权/批准是精确记录 ID+revision，不伪装成已批准的科学内容摘要。

## 2. 公共权威记录字段（四表都继承，草稿不接受）

| 字段 | 类型 | 必填/缺省/null | 顺序 | 写入方 | 科学投影 | 版本/锁定/待决 |
|---|---|---|---|---|---|---|
| tenant_id | ID | 私有必填非 null；无缺省 | — | 控制服务 | X | 创建时绑定；Q03-1 |
| project_id | ID/null | Candidate/Prereg/RunRequest 必填非 null；Protocol 按 scope | — | 控制服务 | X | 项目/租户映射 Q03-1 |
| ownership_scope | project/tenant/public | 必填非 null；无缺省 | — | 控制服务 | X | public 走独立准入记录；Q03-1 |
| created_at | RFC3339 UTC text | 必填非 null；无客户端缺省 | — | 服务 | X | 创建时固定；审计 Q04 |
| created_by | ID | 必填非 null | — | 认证服务 | X | 不进入科学摘要；Q03-1/Q04 |
| status | 对应 A §5.3 枚举 | 必填非 null；服务设初态 | — | 对象服务 | X | 无全连接转换；RunRequest 不增自有状态机，执行态在 Attempt；Q06 |
| content_version | Version | 服务派生；未定稿前不发放 | — | 契约服务 | X(自身派生) | 同 version_ref 不重复存两份权威事实；Q01-1 |
| comment/display_name/cache_location | Text/null（分别独立字段） | 可省略；若出现 null 不等于空文本；无默认 | — | 按服务字段权限 | X | 禁止放科研方法/阈值；Q01-1 |
| approval_bindings | ApprovalLocator[] | 必填；无批准 []，锁定时须满足目的列表 | 集合，purpose+record唯一 | R09/R06/R08 | X | 精确记录 revision，当前有效性每次重验；Q02-1 |

Candidate 锁定点：每个候选内容版本生成；Protocol：approved 后科学内容不可变；Prereg：locked 后不可变；RunRequest：运行定义锁定后不可变。状态、归属、授权与审计事实分开，不就地编辑科学内容。公共字段重复名只保留一个权威值，不允许两处不同 tenant/version；RunRequest 的权威执行记录包含表内元数据，模型 DTO 不接受这些字段。


## 3. CandidateHypothesis

出处：A §5.1/5.2；C.2；R §4.2。继承 §1/2 的无缺省、锁定与归属规则。

| 字段 | 类型/列表顺序 | 必填/null | 写入方 | 科学投影 | 引用与约束 | 待审条目 |
|---|---|---|---|---|---|---|
| candidate_id | ID | 服务必填；无隐式缺省 | R05 | X | 稳定工作标识；不代替版本 | Q03-1 |
| version_ref | Version | 服务派生；无隐式缺省 | R05 | X | 当前科学版本；排除自引用 | Q01-1 |
| background | Text | 必填；无隐式缺省 | A2/A4→R05 | S | — | Q01-1 |
| sources | Ref[] 集合 | 必填；允许 []；无隐式缺省 | A2/A4→R05 | R | 来源精确版本；集合按 ref 科学投影排序 | Q03-2 |
| new_inference | Text | 必填；无隐式缺省 | A2/A4→R05 | S | — | Q01-1 |
| prediction | Text | 必填；无隐式缺省 | A2/A4→R05 | S | — | Q01-1 |
| draft | DraftText | 必填；无隐式缺省 | A2/A4→R05 | S | 正文直接入投影；非任意 JSON | Q01-1 |
| original_source | Ref|null | 必填；原创为 null 且 source_kind=original；无隐式缺省 | A2/A4→R05 | R | 原始来源版本；外部摘录还需位置 | Q03-2 |
| source_kind | original/external_reported/synthetic_design | 必填；无隐式缺省 | A2/A4→R05 | S | 新增来源种类须版本化 | Q01-1 |
| scope_ref | Ref | 必填；无隐式缺省 | A2/A4→R05 | R | 范围精确版本 | Q03-1 |

## 4. Protocol

出处：A §5.1/5.2；C.2；R §4.3。继承 §1/2 的无缺省、锁定与归属规则。

| 字段 | 类型/列表顺序 | 必填/null | 写入方 | 科学投影 | 引用与约束 | 待审条目 |
|---|---|---|---|---|---|---|
| protocol_id | ID | 服务必填；无隐式缺省 | R04b | X | 稳定工作标识 | Q03-1 |
| approval_ref | Ref|null | 必填；草稿 null，approved 不可 null；无隐式缺省 | A0/R09 | X | 当前有效 protocol_use 批准；精确协议版本 | Q02-1 |
| design_type | finite_population_enumeration/comparative_sampling/descriptive | 必填；无隐式缺省 | A3→R04b | S | 类型名后两项为提案 | Q01-2 |
| dataset_ref | Ref | 必填；无隐式缺省 | A3→R04b | R | 数据 manifest 精确版本 | Q03-2 |
| split_ref | Ref|null | 必填；无切分须 null + reason；无隐式缺省 | A3→R04b | R | 切分版本；不能省略授权 | Q01-2 |
| split_not_applicable_reason | Text|null | 必填；与 split_ref 互斥；无隐式缺省 | A3→R04b | S | 新增显式理由字段 | Q01-2 |
| metric | MetricSpec | 必填；无隐式缺省 | A3→R04b | S | 单位/方向/实现版本见子表 | Q01-2 |
| baseline_refs | Ref[] 集合 | 必填；描述型可 []；无隐式缺省 | A3→R04b | R | 至少一个比较基线；精确实现版本 | Q01-2 |
| tuning_space | ParameterRange[] 集合(name 唯一) | 必填；无调参 []；无隐式缺省 | A3→R04b | S | 界限及选择机制不可隐藏为配置元数据 | Q01-2 |
| sanity_suite_ref | Ref | 必填；无隐式缺省 | A3→R04b | R | 规范套件精确版本；实测结果不入此处 | Q01-2 |
| applicability_template | Ref | 必填；无隐式缺省 | A3→R04b | R | 适用性模板版本 | Q03-2 |
| evaluation_unit | unique_item/independent_sample/cluster | 必填；无隐式缺省 | A3→R04b | S | 枚举扩展需批准 | Q01-2 |
| required_items | ID[] 集合 | 必填；固定枚举非空，其余 []；无隐式缺省 | A3→R04b | S | 单位 ID 仅在已锁定数据 manifest 内解释 | Q01-2 |
| duplicate_policy | identical_once_conflict_block/reject_any_duplicate | 必填；无隐式缺省 | A0/方法负责人→R04b | S | Q07 未审不能默认任一 | Q07 |
| missing_policy_ref | Ref | 必填；无隐式缺省 | A3→R04b | R | 新增：锁定缺失策略版本，与 Prereg 相容 | Q01-2 |

## 5. Prereg

出处：A §5.1/5.2；§6.9/C.2；R §4.4。继承 §1/2 的无缺省、锁定与归属规则。

| 字段 | 类型/列表顺序 | 必填/null | 写入方 | 科学投影 | 引用与约束 | 待审条目 |
|---|---|---|---|---|---|---|
| prereg_id | ID | 服务必填；无隐式缺省 | R06 | X | 版本锁定后不可变 | Q03-1 |
| selection_ref | Ref | 必填；无隐式缺省 | R06 核验 A0 | X+R | ID 外置；已批准候选/阈值/范围条款投影见 selection_terms | Q02-2 |
| candidate_version_ref | Ref | 必填；无隐式缺省 | A4→R06 | R | 必须等于批准候选版本 | Q02-2 |
| protocol_ref | Ref | 必填；无隐式缺省 | A4→R06 | R | 必须绑定有效批准的精确版本 | Q02-1 |
| family_id | ID | 必填；无隐式缺省 | R06 | S | 在同项目族声明中解析；不得裸跨租户 | Q03-1 |
| question_ref | Ref | 必填；无隐式缺省 | A4→R06 | R | 问题/估计目标精确版本 | Q02-2 |
| threshold_decision_ref | Ref | 必填；无隐式缺省 | R06 核验 A0 | X+R | ID 外置；threshold_terms 进入投影 | Q02-2 |
| selection_terms | SelectionTerms | 必填；无隐式缺省 | R06 从批准版本解析 | S | 新增：不是 A4 自报已批准 | Q02-2 |
| threshold_terms | ThresholdTerms | 必填；无隐式缺省 | R06 从批准版本解析 | S | 新增：意义阈值不等于 alpha | Q02-2 |
| family_declaration_ref | Ref | 必填；无隐式缺省 | A4→R06 | R | 首次确认前已批准版本 | Q02-1 |
| selection_history_ref | Ref | 必填；无隐式缺省 | R05/R08c→R06 | R | 历史科学事实投影版本；审计元数据另存 | Q02-2/Q04 |
| randomness_plan | RandomnessPlanSpec | 必填；无隐式缺省 | A4→R06 | S | 见子表；枚举不制造独立种子样本 | Q01-3 |
| discrimination_plan | DiscriminationPlanSpec | 必填；无隐式缺省 | A4→R06 | S | 见子表；不适用需理由 | Q01-3 |
| family_alpha | DecimalText|null | 必填；仅不推断时 null；无隐式缺省 | A4→R06 | S | 采样时 0<alpha<1，族分配一致 | Q01-3 |
| family_alpha_reason | Text|null | 必填；alpha 为 null 时非空；无隐式缺省 | A4→R06 | S | 非 null alpha 时 null | Q01-3 |
| arms | ArmSpec[] 有序 | 必填；无隐式缺省 | A4→R06 | S | 比较至少2；单方法须描述型协议 | Q01-3 |
| estimand | Text | 必填；无隐式缺省 | A4→R06 | S | 与 question/协议一致 | Q01-3 |
| test | Ref|null | 必填；枚举 null；无隐式缺省 | A4→R06 | R | 改为精确检验规范引用，非任意 JSON | Q01-3 |
| analysis_ref | Ref | 必填；无隐式缺省 | A4→R06 | R | 代码/独立校准的精确版本 | Q01-3 |
| effect_threshold | DecimalText | 必填；无隐式缺省 | R06 核验阈值 | S | 必须与 threshold_terms 相等 | Q02-2 |
| inference | exact_finite_population_only/sampling | 必填；无隐式缺省 | A4→R06 | S | 后者名称提案；不得推断外推 | Q01-3 |
| missing_policy | Ref | 必填；无隐式缺省 | A4→R06 | R | C.2 字符串经显式适配，不改旧文件 | Q01-3 |
| selection_feedback_policy | Ref | 必填；无隐式缺省 | A4→R06 | R | 精确反馈规范；不凭文案权限 | Q01-3 |
| stop_rule | StopSpec | 必填；无隐式缺省 | A4→R06 | S | 原字符串显式迁移；见子表 | Q01-3 |

## 6. RunRequest

出处：A §5.1/5.2；§3.9/6.16/C.3；R §4.5。继承 §1/2 的无缺省、锁定与归属规则。

| 字段 | 类型/列表顺序 | 必填/null | 写入方 | 科学投影 | 引用与约束 | 待审条目 |
|---|---|---|---|---|---|---|
| mode | 八模式 enum | 必填；无隐式缺省 | 发起角色→R08 | S | A §3.9：exploration/baseline_dev/analysis_calibration/dev/val/sanity/confirmation/replication | Q01-4 |
| code_ref | Ref | 必填；无隐式缺省 | 角色提议→R08 | R | 精确代码版本 | Q03-2 |
| image_ref | Ref | 必填；无隐式缺省 | R08 核验 | R | 镜像 digest 非 tag | Q03-2 |
| data_ref | Ref | 必填；无隐式缺省 | R08/R08c | R | 精确数据 manifest 和当前授权 | Q03-2 |
| seed | Int|null | 必填；deterministic=true 时 null；无隐式缺省 | 角色提议→R08 | S | 随机任务必有或按随机性计划精确分配 | Q01-4 |
| arm_id | ID|null | 必填；非科学比较模式可 null；无隐式缺省 | 角色提议→R08 | S | confirmation 在 Prereg arms 内查；其他按模式 | Q01-4 |
| prereg_ref | Ref|null | 必填；confirmation/replication 不可 null；无隐式缺省 | R08 核验 | R | 不得让 sanity/analysis_calibration 自循环 | Q01-4 |
| configuration | MethodConfig | 必填；无隐式缺省 | 角色提议→R08 | S | 版本化方法配置与科学限制，见子表 | Q01-4 |
| resource_limits | ResourceLimits | 必填；无隐式缺省 | R07/R08/R09 | M | 方法限制与保护/付款分层，见子表 | Q01-5 |
| sanity_ref | Ref|null | 必填；sanity 可 null，确认/复现不可 null；无隐式缺省 | R10a→R08 | X | 实测报告授权/绑定校验；定义不含结果摘要 | Q01-4 |
| deterministic | Bool | 必填；无隐式缺省 | 角色提议→R08 | S | 须与方法/随机性计划一致，不是声明即可证明 | Q01-4 |
| replicate_index | Int|null | 必填；普通运行 null，API复现非负且预注册；无隐式缺省 | R08 核验 | S | 不能把重新采样当基础设施重试 | Q01-4 |
| binding_spec_ref | Ref | 必填；无隐式缺省 | R08 | R | 新增：sanity 规范依赖的协议/套件/配置/环境版本；非结果 | Q01-4 |

## 7. 可逐项选择的 A0 决定

每项均**待 A0 审定**；空白不是批准。A 为推荐方向；B 是不违反已确认红线的备选。负责人/独立复核者待 A0 指定。

| 条目 | A（推荐） | B | 影响/关闭点 |
|---|---|---|---|
| Q03-1 归属映射 | Candidate/Prereg/RunRequest 项目级；私有 Protocol 可租户级，引用须项目授权；public 独立准入 | 首批四类全部项目级，公共/租户级 Protocol 暂不启用 | A 需显式 scope 与授权；B 范围较小；身份/引用模型定稿前 |
| Q03-2 请求引用 | 私有 payload 仅 ID+精确版本，服务填归属；公共独立结构 | payload 带不可信 scope，服务逐项重验 | 前者减少伪造面，后者接口更复杂；禁止裸 hash 查询 |
| Q03-3 科学引用投影 | type+content_version，稳定 ID 仅定位/授权 | 对有科学历史含义的引用另纳入稳定 ID | 前者不因复制工作记录改科学定义；后者避免历史实体被误合并，需逐类列例外 |
| Q01-1 候选字段 | 使用 §3；draft 为 DraftText；source/source_kind 的原创/外部分支；来源集合去重 | draft 改为版本化独立科学规范 Ref，sources 有序 | 改源/预测/草稿均新版本；不能用文本袋掩盖可计算字段；候选模型冻结前 |
| Q01-2 协议类型 | §4 及下方子结构；固定枚举/采样比较/描述型分支 | 首批仅固定枚举；其余分支明确 blocked | B 不能宣称覆盖全部 R02，A 需更多方法独立参考；协议冻结前 |
| Q01-3 预注册结构 | §5，arms 有序；缺省不填；null 条件明列；停止规则结构化，规范规则用 Ref | 暂保留 C.2 文本规则但只接受具名模板枚举及版本 | A 更通用但迁移复杂；B 窄范围但不能接受自由文本当可执行规则 |
| Q01-4 运行模式/绑定 | §6 按模式允许 null；sanity 报告 X，规范依赖 binding_spec_ref 为 R | 将有效报告的独立规范绑定摘要纳入定义，报告 ID 仍外置 | 避免 sanity 自循环；依赖变化应使检查过期；运行定义冻结前 |
| Q01-5 运行限额 | 科学限额 S，纯费用 X；混合用途一律 S 并另验费用 | 所有资源限额均 S，身份仍 X | A 不因纯额度变更改科学 ID，B 更保守但增版本；见 §9逐字段表 |
| Q02-1 批准目的 | selection_use→Candidate版本；protocol_use→Protocol版本；prereg_lock→Prereg版本；run_authorize→运行定义+数据/预算授权 | 维持前三种科研批准，run 仅引用预算/数据授权不新增 A0 每次签字动作 | 目的命名为提案，不等于新增人工流程；建议 B 的 run 自动核验实现 A 的绑定目的，无隐含逐run人工批准 |
| Q02-2 科学批准条款 | selection_terms/threshold_terms 直接投影；批准人/时间/记录 ID 外置 | 独立不可变“批准科研条款”摘要入 Prereg | 两者都核验当前有效批准；避免循环哈希；Prereg 锁定前 |
| Q02-3 重新批准 | 科学变更新版本并重做适用批准；纯预算变更只更新预算授权且重验运行资格 | 科学变更同 A；纯预算也要求新增运行定义/相关批准 | A 对应 Q01-5 A；B 对应 Q01-5 B；不能放宽既有科研批准 |
| Q07 重复观测 | 同单位同内容计一次且保留溯源，冲突阻塞 | 任意重复单位拒绝本批 | 未决定不得设 duplicate_policy 缺省；JSON 键冲突拒绝不替代此决定 |

Q04：selection_history 科学内容摘要与完整审计链区别仍未定；Q05：签名 payload/域分离保持待决；Q06：各分支完整状态边/中止状态保持待决。它们不阻塞本轮纯规范化，但阻塞对应业务合同/签名/状态实现。四表完整形状是提案，科研/权限意义未审的字段不会进入生产代码。

## 8. 子结构完整形状提案与新增决定

以下**每个列出的子字段均必填、无隐式缺省**，除明确 null 外均非 null；仅这组字段，禁止额外键。子结构继承父字段写入方、锁定点、归属；除显式 X 外均 S，Ref 为 R。列表分类逐项标注。以下形状本身全部属于 Q01-1～5，服务权威条款属 Q02-2；不是设计原文逐字给出的 Schema。

| 子结构 | 逐字段类型/空值/顺序 | 引用/规则 |
|---|---|---|
| DraftText | format:"plain_text"; body:Text | 无任意对象；代码/可执行方法用版本 Ref；禁止把模型写的已批准字样当批准 |
| MetricSpec | name:Text; unit:Text; direction:maximize/minimize; implementation_ref:Ref | 实现精确版本；C.2 accuracy 显式适配 |
| ParameterRange | name:Text; kind:integer/decimal/categorical; lower:DecimalText或null; upper:DecimalText或null; values:Text[]集合; unit:Text; selection_rule_ref:Ref | categorical 两界 null 且 values 非空；数值范围两界非null且 values=[]；整数界必须为整数；name唯一 |
| SelectionTerms | candidate_version_ref:Ref; scope_ref:Ref; meaningful_delta:DecimalText | 服务从具体批准解析；预算 scope 不入科学条款 |
| ThresholdTerms | question_ref:Ref; value:DecimalText; unit:Text; direction:greater/less; scope_ref:Ref; rationale_ref:Ref | 与 effect_threshold、SelectionTerms 一致；提出/批准/修改历史保留权威引用 |
| ArmSpec | arm_id:ID; role:reference/candidate/descriptive; method_ref:Ref; baseline_ref:Ref或null | reference/candidate 比较对应协议，descriptive 不强加基线；arms 有序，arm_id唯一 |
| RandomnessPlanSpec | seed_generalization_target:not_applicable/fixed_seed/random_seed_population; random_sources:Ref[]集合; repetitions:Int或null; independent_units_ref:Ref或null; cluster_levels:Ref[]有序; estimation_method_ref:Ref或null; reason:Text或null | not_applicable 时 sources/levels=[]、其余null且 reason非空；适用时 repetitions>=1、单位/估计方法必有，reason可null；层级顺序有语义 |
| DiscriminationPlanSpec | applicability:applicable/not_applicable; explanations:Ref[]集合; predictions:Ref[]有序; observable_differences:Text[]有序; minimal_design_ref:Ref或null; indistinguishable_conditions:Text[]集合; reason:Text或null | 不适用时列表[]、设计null、reason非空；适用时解释至少2，预测按解释明确映射(引用内容须具 explanation_ref)，最小设计必有；映射完整性不得靠相同长度 |
| StopSpec | kind:complete_items/fixed_count/registered_rule; required_items:ID[]集合; sample_count:Int或null; rule_ref:Ref或null | complete_items非空集合且余null；fixed_count count>0且items=[]/rule=null；registered_rule有ref且items=[]/count=null；版本化规则内容含阈值/窗口 |
| MethodConfig | method_ref:Ref; parameters:ParameterValue[]集合(name唯一); precision:Text; hardware_semantics_ref:Ref或null; stopping:StopSpec | 配置不是任意键值 JSON；硬件无科学相关性才能null并在权威解释记录说明 |
| ParameterValue | name:Text; kind:integer/decimal/text/boolean; value:Int或DecimalText或Text或Bool | kind限定对应值，禁止双义；所有参数参与科学投影；无默认 |
| ResourceLimits | science:ScienceLimits; budget:BudgetLimits; safety:SafetyLimits | 分支固定，不能用一个 timeout 同时当两种含义 |
| ScienceLimits | max_steps:Int或null; max_output_tokens:Int或null; method_wall_time_seconds:DecimalText或null; method_memory_bytes:Int或null | 正数或null(方法无此限制)；同用途若也是费用约束仍S |
| BudgetLimits | max_cost_minor:Int; currency:Text; approval_ref:ApprovalLocator; payer_ref:ID; credential_ref:ID或null | 全X；金额>=0、单位与币种契约版本一致；credential 仅引用非密钥；模型无权填有效身份/批准 |
| SafetyLimits | wall_time_seconds:DecimalText或null; memory_bytes:Int或null; lease_deadline:UTC时间或null | 全X仅适用于基础设施保护；若决定方法/结果必须转到 science；中止不等于有效完成 |
| ApprovalLocator | purpose:Text; record_id:ID; revision:Int | 全X；revision>=0，目的白名单见 §7；记录由服务解析并验证当前有效性 |
| BindingSpec（外部精确版本对象） | protocol_ref:Ref或null; suite_ref:Ref; code_ref:Ref; data_ref:Ref; image_ref:Ref; configuration_ref:Ref; validation_profile_ref:Ref | 科学规范绑定 R；sanity无自身报告依赖；实际报告覆盖/批准失效必须另验 |

外部 Ref 的目标不是“随便一段 JSON”：须声明 object_type、内容版本、字段 schema 版本及权威来源；未提供目标规范或找不到版本则 blocked，不能利用外置 Ref 偷渡未审科研字段。上述 ParameterRange、随机性/区分设计分支及 type/enum 名称均是新增细化决定；A0 可以只批准有限枚举首包，并明确其他分支暂不启用，不把全 R02 标完成。

## 9. 资源与重新批准验收例

| 变更 | 科学定义/批准建议 A | 仍需核验 |
|---|---|---|
| max_steps、max_output_tokens、StopSpec 阈值/样本量 | 新科学版本；适用候选/协议/预注册/运行批准重新核验或重新批准 | 不容许看结果后改变规则 |
| method_wall_time_seconds、method_memory_bytes | 新科学版本 | 即使金额相同也不是原方法 |
| BudgetLimits.max_cost_minor/currency | 科学定义不变，新预算授权版本 | 当前用途/上限/付款归属；不能因为相同hash继续用旧授权 |
| SafetyLimits.wall_time_seconds/memory_bytes | 只有纯硬保护才 X | 截断不能降低样本量/缩分母后成功；按Q06处理不完整事实 |
| seed、data/code/image版本、replicate_index | 新run定义，所有适用上游批准重验 | 新方法不能伪装基础设施重试 |
| Candidate预测、Protocol指标/切分、Prereg阈值/分析脚本 | 新对象版本与适用科研批准；旧检查/批准不覆盖新版本 | 传播 sanity/上下文/计划绑定失效 |
| 签署人/时间/撤销状态、租户/项目 | 科学hash不变，但授权不同或失效 | 跨租户不能借批准；撤销立即阻止后续使用 |

无论 A/B，最终权限判断必须解析当前有效批准，不因示例存在 approval_ref 放行。草稿阶段允许结构缺项的编辑视图不能复用成已锁定权威对象；正式锁定记录按本表严格检查。旧九题不改数据，通过单独、显式、可审阅 fixture 适配器包装；missing_policy/stop_rule/metric 的结构变化须版本化，不能生产接口静默猜值。
