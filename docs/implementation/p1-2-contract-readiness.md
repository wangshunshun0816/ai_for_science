# P1-2 R02 契约待决项核对与实施拆分

日期：2026-11-12。状态：以下为初始准备快照，现行进展见 §11–12；本文建议均不作为 A0 已批准决定。人工验收与科研资格不由文档检查代替。

## 1. 起点、依据及范围

Ubuntu checkout 为 /home/wangshunshun/danus-ai。核对开始时 main 工作区干净；本地 HEAD 与 git ls-remote origin refs/heads/main 均为 0aa4703ee810c93b46b6981587e51bd4a7466c23；git merge-base --is-ancestor 对该提交返回 0。本地及远端均包含 [P1-1 人工验收](decisions/A0-P1-1-delivery-acceptance.md)，仅限首次交付。

引用代号均指仓库固定设计，不因本准备工作改动：

- G：[开发指南](<../Danus-AI 落地开发指南：模块顺序、接口衔接与验收.md>)，§3.4 R02、§5.3 P1-2、§7.2 关闭点。
- A：[大方案 v1.2](<../Danus-AI 科研智能体产品架构与落地执行方案 v1.2 最终确认稿.md>)，§3.9、§5.1–5.5、§6.4、§6.16、§12.2、附录 A.1 和 C.1–C.5。
- R：[角色规格](<../Danus-AI Agent 角色实现与验收规格.md>)，§3.1–3.5、§3.7、§4.1–4.7、§5.1、§7.1、§8.1。
- O：[object_semantics.md](p0-2/object_semantics.md)；H：[hash_fields.md](p0-2/hash_fields.md)；D：[denominators.md](p0-2/denominators.md)；F：[金样例 README](p0-2/golden/README.md)及同目录九个 JSON；S：[P0-6 缺项与首次交付边界](p0-6-closure-and-p1-1-scope.md)。

依据 G §3.4／§5.3、A §6.4，范围包含 §5.1 全对象与消息、草稿／权威分离、租户／委派、状态与哈希、TaskPlan、Sanity、ContextManifest、角色输出合同、Schema/OpenAPI 组件及独立金样例。不得只做候选／协议三个对象就宣称 P1-2 完成。仓储、数据库迁移、真实调度、证据门运行、角色能力评测不在本次准备任务内。

## 2. 既有待决问题逐项核对

“设计已定”关闭的是规则疑问，不代表工程实现或验证完成；“部分已定”不得抹掉剩余字段级缺口。具体方案见第 3 节。

| 原问题 | 已有设计结论及出处 | 剩余缺口／影响与处置 |
| --- | --- | --- |
| O-1 独立状态与写入归属 | A §5.1 已逐对象指定权威来源；§5.3 明确 ResearchTask、候选、Protocol、Prereg、Attempt、提交、发布的状态，科学资格独立。计划执行概况由任务投影，不另建科研成功状态。R §3.1 角色结果分类也不新增项目状态机 | 未列状态机不等于遗漏了必须新建的状态机。Approval、RunRequest、RunRecord 聚合、InvocationRecord、EvidenceReport、ClaimNode、EvidenceEvent、GateExecution 推荐事实／投影表达（E-01）。暂停恢复、reconciling 出入、重复请求和终态修订的完整边集并未给齐；三维状态的权威记录位置未定，见 Q-06。影响 validate_transition 与非法转换测试 |
| O-2 run_refs/run_ids | A §5.1 ClaimSubmission 写 run_ids；C.4 写 run_refs，二者都指锁定运行而非 attempt。存在真实命名差异 | E-02 推荐单一正式字段与显式 fixture 适配，不改旧 JSON。字段名为工程选择；引用结构、归属与版本绑定依赖 Q-01/Q-03。影响 Schema、引用解析和所有 submission fixture |
| O-3／H-1 逐对象投影 | A §5.2 明确所有科研语义字段进入完整 SHA-256，排除注释／显示／缓存／状态；科研语义改变新对象新批准。逐对象字段表是必交付 | 具体字段、必填／缺省／null、列表语义、引用投影尚不全。不能以 C 的载荷片段充当完整 Schema。Q-01 逐对象表审批；影响 content_id、版本稳定性和兼容性 |
| H-1 规范化顺序 | A §5.2：严格解析拒绝重复键／NaN／Infinity → Schema 缺省与投影 → NFC、CRLF→LF → 领域十进制字符串 → RFC 8785 JCS → UTF-8 → SHA-256；无指数、去末尾零、零为字符串 0；列表按有序／集合分别处理 | 规则已定，可实施通用管线；不得擅自改为 sort_keys JSON 或把所有数组排序。对象数组分类由 Q-01 决定；NFC 后键冲突与非 Unicode 标量等明确工程拒绝建议见 E-03 |
| H-2 批准引用与科学绑定 | A §5.1–5.3、C.2 明确绑定候选版本、协议版本、预注册；批准身份／时间由服务填写。approval_ref 出现并不等于批准。C.5 候选核心改变后旧批准不覆盖 | 绑定精确版本已定，不再请 A0 选择是否绑定。selection_ref、threshold_decision_ref、approval_ref 的科学投影与授权信封分界仍需 Q-02；RunRequest 的资源上限、sanity_ref 等需 Q-01。影响避免循环哈希和旧批准拒绝 |
| 身份／归属（S P0-6c） | A §5.1／§5.2、A.1 和 R §3.2：一账户一个个人租户；私有对象有 tenant_id，项目对象有 project_id；服务验证 TrustedRequestContext／Delegation；公共对象须独立命名空间及准入，tenant=null 不放权；同哈希不能跨租户选记录；未知旧归属受限待认领 | 原则已定，不重新提议自动认领或共享私有数据。Q-03 只解决对象引用／可信信封结构及归属粒度映射；影响跨租户引用、委派、fixture 包装和 legacy_incomplete |
| H-3 论断维度、审计标识 | A §5.4 六维分离，strength/status_flags 随证据变化不能改写原陈述。§12.2 关键事件必须有序号、前事件哈希、对象摘要、actor、时间和版本；审计字段不能因不进科学哈希被删 | ClaimNode 初始 kind/outcome/origin/logical_level 与来源摘要的具体投影、EvidenceReport/Event/GateExecution 的记录 ID／内容摘要／链哈希区分待 Q-04；影响历史可核验性与事件变化不改科学 ID |
| H-4 发布签名载荷 | A §2.4、§12.2：A0 签完整 manifest，Ed25519，私钥在操作者工具，服务持公钥；修改产物须重新检查／签字；§5.1 的签字摘要不能使载荷自含其签名而循环 | Q-05 定签名前 payload、签名 envelope、发布回执、域分离和版本字段。影响 ReleaseManifest、Approval、签名摘要测试；本准备不创建密钥或实现签名服务 |
| D-1 相同／冲突行 | A C.5 重复 q3 不增加 unique_item／强度；§6.16 明确区分重复数据、合法重复试验和伪独立记录，不默认删除所有重复 | 原则已定，精确策略仍需 Q-07。影响协议 missing/duplicate_policy、评价单位、检查状态和重复分支；不得用后到行覆盖冲突 |
| D-2 缺失适用范围 | A C.2、C.5 的缺任一题即 incomplete 只适用于四题完全枚举；§5.1 RandomnessPlan、§3.9、F「P1 抽样 fixture 缺口」要求其他设计另声明 | 关闭“应有跨协议统一缺失规则”的误解；各采样模板预注册规则及参考样例仍待建设，不自动沿用枚举规则。影响 sampling fixture，而非通用 strict parser |
| O 已关闭的审计失败分类 | R §3.7、§4.6/TC-A7-03：超时／解析失败为服务 error，缺关键材料 needs_evidence；均非 accepted。A C.5 的概括不能覆盖该细分 | 沿用已有 error-audit-timeout.json，不重开该决定；角色报告 no_blocking_issue_found 与服务状态 error 分层建模 |

## 3. 决定责任与具体方案

### 3.1 常规工程建议（不是新增科研批准）

- E-01：为事实记录、不可变内容、当前状态投影定义不同模型；没有设计状态机的对象不凭空加 draft/approved。Python Protocol 承载只读引用解析，形状验证无 DB／网络。目录、类名和 Schema 导出方式由实施者负责；新增状态及权威写入归属须走 Q-06。
- E-02：推荐正式 ClaimSubmission 使用 run_ids: list[RunId]，遵从 A §5.1；旧 C/F 的 run_refs 仅由测试 fixture 适配器显式映射。对同时出现两个字段的输入拒绝，生产 strict Schema 不隐式吞掉旧字段。替代方案为正式 run_refs，但要同步对象表与所有调用者，涉及基线修订应交 A0；两者均不能允许无归属查询。RunId 是运行定义的 ID，不是 attempt_id。
- E-03：建议 NFC 后对象键碰撞、无效 Unicode 标量拒绝；十进制使用精确字符串计算，不经过二进制 float；裸 CR 不擅自扩展为 CRLF 规则；字段的 null 与缺省按已登记 Schema 处理。JCS 库选择／版本／许可与依赖锁另作工程评估；本轮不安装。测试应覆盖规则要求的拒绝，不以 Python 默认 json 行为代替规范。
- E-04：每个对象字段表固定列：名称、类型／单位、可空／缺省、可写角色或服务、锁定点、哈希参与、引用版本／归属、兼容迁移、设计出处。Schema 从同一编辑源导出，不手写第二份。全套字段表可立即起草；涉及下表 Q 的行必须保留待决。
- E-05：用独立的 fixture 构建／适配层包装旧科学载荷；身份由测试服务生成，保留 expected 与手算说明原文。运行态计算内容 ID 不等于自动生成正确答案；预期规范化字节／哈希另有冻结且可复核的独立参考。

### 3.2 需 A0 选择或批准的具体问题

下列均为待决。推荐项是待审方案；A0 可要求方法／权限负责人复核后决定，未落实负责人填“待 A0 指定”。所有候选必须遵守既有身份、科学和批准原则，不能通过选择放松红线。

| ID／对象字段／责任 | 方案与推荐项 | 影响、关闭点及验收 |
| --- | --- | --- |
| Q-01 全对象内容投影；Candidate/Protocol/Prereg/RunRequest/ClaimNode 等；科学语义负责人待 A0 指定，A0 批准 | A（推荐）：逐对象逐字段批准投影表，包括科研引用的不可变版本摘要、默认/null、列表有序性；RunRequest 中改变执行方法／停止条件的资源限制入科学定义，纯预算上限留权威信封。B：将全部资源限额均锁入运行定义，仍排除身份和执行状态 | A 能避免单纯额度调整产生新科学 ID，但需逐字段分类；B 更保守却可能增加同科学定义的运行版本。sanity 检查结果不直接当科研内容，准确依赖版本另定；不能在表未定时发放正式内容 ID。关闭：对应模型 content_id／fixture 完整哈希定稿前；验收：逐字段变化矩阵 |
| Q-02 Prereg selection_ref/threshold_decision_ref/approval_ref；权限及科学负责人待 A0 指定，A0 批准 | A（推荐）：科学 payload 存已批准的候选／协议版本、意义阈值及历史的语义投影；签署人、时间、批准 ID 放权威绑定信封，校验时必须解析当前有效批准。B：在排除身份等元数据的前提下，对批准记录定义独立不可变“科学条款摘要”，Prereg 纳入该摘要；授权信封仍单独核验 | A 直接投影利于去循环；B 增加条款模型和可追溯引用。任何方案均不得因 hash 相同自动沿用撤销批准。关闭：Prereg 锁定合同前；验收：改科研条款改 hash，改审批元数据不改科研 hash，旧版本／撤销批准拒绝 |
| Q-03 引用与归属信封；tenant/project、object_ref、public admission；权限／数据负责人待 A0 指定，A0 批准 | A（推荐）：调用 payload 仅给对象 ID／版本，TrustedRequestContext 指定受信归属；服务产生包含归属和内容版本的内部 ResolvedRef。B：payload 给显式作用域引用作为不可信查询条件，服务逐项核验并另建受信引用 | A 减少模型伪造面，公共引用需显式独立类型；B 便于跨项目显式表达但校验更复杂。都禁止模型填写有效租户身份；对象级／项目级边界需字段表逐项登记。关闭：引用解析、fixture 归属包装和 P1-2 身份合同定稿前；验收：双租户相同 ID/hash/幂等键不互读，public 非 null 放权，旧归属不猜测 |
| Q-04 ClaimNode 维度／来源及审计身份；事件模型负责人待 A0 指定，A0 审定语义 | A（推荐）：不可变科学陈述／scope／科研分类／初始 outcome 与确有科学意义的来源进入内容版本；strength/status_flags 当前值由事件投影。报告和事件另有记录 ID、内容摘要和关键事件链摘要，不混用。B：论断内容版本另附“初始接受快照”摘要，后续仍事件化 | A 避免强度变化改写内容 ID；B 多一个接受快照层，需定义重接收和等价内容规则。具体 kind/origin/logical_level/source_submission_ref 的参与矩阵待定，不能凭本描述直接落码。关闭：ClaimNode/Event 哈希定稿前；验收：actor/时间影响审计链，状态变化不偷改科学内容，删链／重排可发现 |
| Q-05 ReleaseManifest／Approval 签名 payload；部署／安全负责人待 A0 指定，A0 批准 | A（推荐）：无签名的 manifest payload 单独规范化并摘要，Ed25519 签版本化且带用途域的完整 manifest 绑定信封；签名及发布回执存外层。B：Ed25519 直接签规范化完整 manifest 字节，外置 key_id／算法／版本和回执 | 两者均排除签名自引用并绑定完整清单；A 需明确域与摘要规则，B 直接字节签名但重序列化兼容要求更严格。不得只签镜像标签或子集。关闭：签名相关 Schema 冻结前；验收：更换代码／依赖／镜像／结果快照均失配，实际签名执行留后续模块 |
| Q-06 状态边集及三维工程记录；业务责任待 A0 指定，A0 审定新增语义 | A（推荐）：按每类对象列事件／前态／后态／守卫，非明确边先阻塞；三维工程状态作为 R05 配置／追踪记录，A0 批准决定，实施和证据由各责任提交并审阅。B：独立工程验收记录合同，由管理入口维护三维状态，与科研对象解耦 | 规范只给主路径，不能据此任意允许所有跳转；ResearchTask paused 恢复目标、Attempt reconciling、报告重试需明确。A 复用存储，B 多合同但不新建 DB。关闭：相应 validate_transition 完整验收前；可先实现明确主路径和禁止跳过批准／发布回执的测试 |
| Q-07 重复／冲突观测；协议／方法复核待 A0 指定，A0 批准协议策略 | A（推荐用于固定四题）：同 evaluation_unit 且原始内容完全一致的重复行保留溯源、评价时计一次；同单位冲突行阻塞评估并报告缺陷，不挑一条；合法重复试验按预注册的新单位／attempt 区分。B：固定枚举输入发现任何重复单位即拒绝本批，保留全部原始行供修正 | 两者都符合 C.5 去重/拒绝，均不得把 14 行当 14 个单位；A 较宽容需精确定义等价，B 严格且可能增加合规误拒。冲突不自动判 harm 或科学否定。关闭：协议 duplicate_policy 与 G0/R10a 观测合同定稿前；补相同／冲突／合法重复三类独立参考 |

## 4. P1-2 实施拆分与全对象覆盖

以下路径为拟定交付位置，不表示本轮创建；“可立即实施”仅表示无新设计决定阻塞，仍需后续实现授权。所有实现限定 contracts 及测试，不编写数据库／角色运行器／证据门业务。

| 任务／拟交付文件 | 对象和交付范围／验证入口 | 依赖及可实施部分 | 验收标准／现有 fixture |
| --- | --- | --- | --- |
| T01 字段台账；docs/implementation/r02-field-matrix.md、r02-decisions.md | A §5.1 全对象逐字段登记 E-04；对齐附录 A 外部 envelope 与服务 typed signature | 可立即起草；Q-01～Q-07 的未定行保留，不当默认值 | 每对象有权威写入方、字段出处、hash 分类和迁移规则；对照 F 所有输入／expected，缺失列表不静默忽略 |
| T02 基础模型；contracts/base.py、identity.py、references.py、numbers.py、errors.py | 严格模型及 draft/authoritative 分离；PersonalAccount/Tenant/Project、TrustedRequestContext/Delegation、数字六种性质、公共引用、错误封装 | strict parser、禁止权限字段及数字性质枚举可立即实施；完整引用类型依赖 Q-03，完整三维合同 Q-06 | validate_object；extra forbid、伪造身份／measured、同 hash 跨租户、缺归属 legacy_incomplete；F 的身份包装为新增测试，不改原载荷 |
| T03 规范化；contracts/canonicalization.py、content_ids.py、projections.py | 严格 JSON、NFC、CRLF、精确十进制、JCS、完整 SHA-256、类型/版本命名空间；旧 danus_fact 原样引用 | 通用规范化可立即实施；逐对象投影和批准摘要等依赖 Q-01/Q-02/Q-04/Q-05 | canonicalize/content_id；独立字节向量、参与／排除变更测试、平台一致；全部 F 的 fixture 别名映射待投影确定 |
| T04 科学计划；contracts/research.py、protocols.py、prereg.py | ResearchTask、CandidateHypothesis、IdeationReport、SelectionDecision；Protocol、Prereg、Arm、ResearchQuestion、FamilyDeclaration、SelectionHistory/Set、RandomnessPlan、DiscriminationPlan | 状态枚举、必需引用/批准守卫可立即实施；具体完整模型依赖 Q-01/Q-02/Q-03/Q-06 | validate_object/transition；候选改版使批准不适用；两 Arm 比较与独立描述协议分型；positive、bounded-negative 及新增候选改版分支 |
| T05 执行；contracts/runs.py、modes.py | RunRequest/RunRecord/Attempt、InvocationRecord；§3.9 八个模式值（dev、val 分列）、运行 ID 与尝试 ID；资源准入、模型谱系、用量/退出引用 | 模式矩阵、科学资格与进程状态分离可立即实施；运行投影 Q-01、引用 Q-03、异常边 Q-06 | confirmation 前置齐备；sanity 不循环依赖自身报告，analysis_calibration 不要求正式锁定预注册；F 收集恢复、缺题，新增 seed/code/data/replicate_index 改运行 ID |
| T06 证据与 scope；contracts/claims.py、scope.py、events.py | ClaimSubmission、EvidenceReport、ClaimNode、EvidenceEvent、GateExecution、ReauditTask；theorem_ref；requires 与比较边分离 | 三值比较纯函数、六维枚举可立即实施；身份 Q-03、命名 E-02、内容／链 Q-04 | scope_contains/overlaps/comparable；unknown 非 true、独立样本不强求相交；F 数字错配／超范围／超时，其他证据门结果只作合同测试，非实现 G0/G2 |
| T07 批准／配置／数据；contracts/governance.py、data.py、release.py | ModelProfile、Budget/Usage/Approval、DataPolicy/SendPermit、ParameterDecision/CalibrationTask、OutcomeLearningRecord、ProductUseEvent/EvaluationCampaign、数据暴露、预算事件、ReleaseManifest | 数字性质、公开/私有原则可立即落实；审批/签名 Q-02/Q-05，归属 Q-03，工程三维 Q-06 | validate_object；金额不由模型变成已支付，外部报告有原文定位，reference_derived 有输入/推导；发布状态须实际回执；新增独立 fixture，不拿原四题代替全部对象 |
| T08 计划／角色／上下文；contracts/plans.py、roles.py、context.py | TaskPlan/PlanRevision、PlanNode/TaskContract、RoleQualification、ContextManifest；七角色输出合同及交接记录 | 输入/输出版本、DAG、角色/任务类型白名单等可立即设计；引用 Q-03，状态映射 Q-06；细分 task_kind 名称是 R02 工程固化，资格阈值仍待独立评测 | validate_object/transition；环、未知 task_kind、principal 自报、过期版本拒绝；来源撤销后 ContextManifest 失效。现有 F 未覆盖，按 A C.5、R §3/§5.1 补题 |
| T09 sanity；contracts/sanity.py | ProtocolBundle、CheckSuite、SanityRequest、SanityJobRef、SanityReport/View、ValidationProfile、精确 binding；A §6.16 请求/解析签名 | 逐项五种状态、exploration_lite/confirmation_full 及必需项规则已定；绑定模型 Q-01/Q-03，重复策略 Q-07 | error/not_covered 不变 pass、不科学否定；not_applicable 要批准依据；协议/代码/数据/配置/依赖/套件/profile/批准变化 stale；新增旧报告及缺覆盖 fixture |
| T10 导出与整体验证；contracts/api.py、export_schema.py；schemas/、tests/contracts/、fixtures/contracts/ | I-SCHEMA 七入口；JSON Schema/OpenAPI 组件从唯一源生成；只读端口替身，字段变更的调用者兼容矩阵；旧记录显式 incomplete | 可先规划；完整验收依赖 T01～T09 关闭适用 Q；不以未来 R08/R09/R13/R14/R16 未实现为由捏造联调 | 对象全覆盖、调用两侧 schema 一致、同 fixture 跨系统 hash 一致；全九题保持数值及手算，新题独立期望；真实服务联调明确留后续，不标已完成 |

七角色合同按 R §4.1–4.7 分别覆盖：A1 策略及计划草稿；A2 Candidate 草稿；A3 协议组件与 qualified_reuse/bounded_adaptation/new_protocol_design 三路径；A4 验证草案／正式设计两任务；A5 代码与运行申请／ClaimSubmission 草稿；A7 AuditReport 三类业务结论与服务 error；A12 文稿及可信数字/引用关联。每类包括 input_refs、output_contract_ref、允许动作、完成／停止／交接条件和版本；不授予模型 principal、批准或测量写权。真实角色资格与质量阈值不在 P1-2 用 mock 宣称通过。

状态覆盖最低清单：A §5.3 七主状态机（研究任务、候选、协议、预注册、运行尝试、提交、发布），科学运行 valid/invalid/incomplete 独立枚举；计划激活是版本 CAS 合同与任务投影；decision/implementation/evidence 三维独立记录。Q-06 未定前不编造暂停恢复、对账返回、重试或终态修订的全连接边。

## 5. 验证计划与独立期望

所有计划均待执行，不作为本轮测试成绩。测试命令随真正实现确定；本轮不安装依赖，不生成 Schema，也不调用产品代码。

| 验证组 | 必须覆盖的正反例／期望来源 | 验收条件 |
| --- | --- | --- |
| V01 写入权限／归属 | A §5.1、A.1、R §3.2/3.5；模型提交 tenant/project/principal/approved/hash/measured 等权威字段拒绝；合法服务信封可构造；跨租户相同内容与幂等键隔离 | 字段权限矩阵逐项有拒绝测试；公共引用走显式准入，不能靠 tenant=null；旧数据不自动认领 |
| V02 状态与运行模式 | A §5.3、§3.9、R §3.7/4.6；合法主路径、跳过审计/锁定拒绝；任务 completed 不等于 released；G2 超时 error 与缺材料 needs_evidence | 全明确边/守卫有测试，Q-06 未定边报待决而非默认通过；confirmation/replication 前置按模式校验，不制造 sanity 自循环 |
| V03 hash 参与／排除 | A §5.2、批准后的 Q-01 表；逐个参与字段变更导致新 ID；注释/显示/缓存/状态/身份等不改变科学 hash，仍影响适用授权/审计绑定 | 语义新增字段不能默认排除；内容相同不授跨租户访问；批准撤销即便 hash 不变也拒绝使用 |
| V04 严格规范化 | A §5.2；重复键、NaN/Infinity 拒绝；NFC 等价、CRLF/LF 等价，裸 CR 按原规范处理；十进制零/末尾零/指数输入规范化；null/缺省、有序与集合分开 | 独立预期字节、完整 SHA-256 与类型/版本前缀；JCS 官方测试向量须在实施时登记版本来源；不能由被测函数自动回填金标 |
| V05 Windows/Linux | 同一只读向量集在 CPython 3.12 的 WSL/Linux 与 Windows 执行纯契约检查；记录解释器补丁、工具/契约版本、输入字节和摘要 | 两侧 canonical bytes 与 ID 完全一致；宿主路径不能意外进入科学字段；Windows 不代替 Linux 运行验收 |
| V06 引用／批准／scope | A §5.5、C.1/C.2/C.5；批准精确版本、撤销/过期、unknown、不适用、独立样本可比、requires 环、数学只读引用 | unknown 不默认为 true；必填缺失拒绝；合法映射有版本/批准；生产接口拒绝 fixture 标识和 fixture_only |
| V07 计划／上下文／sanity | A §5.1/5.3/6.16、C.5、R §3/5.1；合法 DAG、环、未知 task_kind、CAS 版本冲突、旧绑定、error/not_covered、授权撤销和输入版本变化 | 新增独立期望 fixture；解析合法不等于科研/角色资格；实际并发/删除恢复等由后续模块验收，R02 只验合同与守卫 |
| V08 审计／签名结构 | A §12.2、Q-04/Q-05；链 actor/时间/序号/前 hash/对象摘要/版本，manifest 全字段变更影响摘要；签名及回执不自包含 | 内容 ID／记录 ID／链 hash／签名 payload 不混用；本阶段先验结构/摘要，密钥执行与独立检查点部署另验 |

### 5.1 九个既有金样例映射（不修改原文件）

F 中 expected_derivation 为现有手算来源；保留原文字、数值、隐藏标签和适用范围。fixture 构建器只做可信身份与引用绑定，不能把 expected 传给被测角色。依赖 Q-01/Q-02/Q-03 生成生产形状 fixture；生产入口与测试适配器分开。

| 文件（均位于 p0-2/golden/） | 不变期望及出处 | 对应任务／验收边界 |
| --- | --- | --- |
| positive.json | A C.2–C.4、手算：2/4=0.5，3/4=0.75，差0.25>0.1；interval/p_value 为 null；四题范围；仍需 G2 无阻断 | T03–T06/T10；条件接受测试可明确 mock G2，不冒充真实审计 |
| bounded-negative.json | A C.5：只改 q3 method；两臂0.5，差0，bounded_no_meaningful_gain 仅四题 | T04/T06；不外推无效或总体结论 |
| incomplete-missing-q4.json | 缺 q4 即 incomplete，不能缩成三题，accepted=false | T05/V02；不改成抽样 inconclusive |
| error-audit-timeout.json | 原差0.25不变；服务 error，accepted=false，R §4.6/TC-A7-03 | T06/V02；不把错误当科学否定 |
| rejected-number-mismatch.json | 伪报0.50与0.25不一致，G0 rejected | T06/V01；R02 只验可信引用/合同，完整 G0 重算不在本任务实现 |
| rejected-overbroad-scope.json | 四题不支持所有分类任务，原提交拒绝，收窄另建 | T06/V06 |
| rejected-duplicate-q3.json | unique_item=4，不接受14个单位或更强证据 | T09/Q-07；去重与严格拒绝策略不得改写既有伪样本量拒绝期望 |
| recovery-collector-crash.json | 恢复原 run/attempt 收集对账，不新运行，恢复前统计不可用 | T05/V02；R02 验合同，不宣称实现恢复引擎 |
| recovery-idempotent-submission.json | 相同归属内同键同内容返回原 submission，不重建 ClaimNode | T02/T06；契约/替身测试与 P1-3 事务幂等实现分开 |

### 5.2 尚需新增的独立参考

A §6.4、C.5 要求而现有九题未覆盖的：真正 sampling inconclusive、候选核心改版失效、同数据 repeatability 与新数据独立复现/范围变化、复现降级；双租户相同 hash/ID/幂等键与伪造身份；合法／有环计划、替换中对账与迟到结果；旧协议/检查摘要、error/not_covered；撤销授权的记忆引用、数据删除后的恢复引用；A2 越权提交、新协议无独立参考、A4 分析与批准协议不匹配。逐项拆成 R02 合同与后续业务验收，不能在没有服务时虚报端到端通过。

新样例由具名参考／方法责任人（待 A0 指定）提供可追溯推导或独立参考实现，审阅后冻结预期；工程可先准备格式和确定性反例。四题 hand calculation 不生成总体 p 值或置信区间，不复制 seed 伪造独立样本。现有手算与“正式独立复核人待定”事实继续保留。

## 6. 推荐执行顺序与交付门槛

下一项可执行任务为 T01 字段台账与 T02 的已定 strict/draft-authoritative 基础结构设计；获得产品实现授权后，可并行实现 T03 通用规范化、T05 模式矩阵、T06 三值 scope、T08/T09 已定枚举和结构校验。完整产品 content_id、引用解析、锁定和事件签名合同分别等待适用 Q 决定，不用宽松 Any 或静默默认掩盖空缺。

A0 优先决策 Q-03（归属引用）、Q-01（逐对象投影）及 Q-02（批准科学绑定）；随后 Q-06 状态边集、Q-04 审计身份／论断投影、Q-07 重复策略；Q-05 在签名相关 Schema 冻结前关闭。工程负责人及独立方法／权限／安全复核者尚未落实，均待 A0 指定。A0 决定须绑定具体字段表版本，不能仅以“原则同意”替代完整投影审批。

P1-2 完成要求：全对象覆盖、七入口/Schema 一致、适用待决项关闭、合法／非法与跨字段验证有证据、跨平台 hash 一致、旧/新金样例独立期望可追溯。当前只完成准备盘点，不宣称上述验收通过。S 的“远端 CI 待完成”等旧状态按 P1-1 人工验收后续记录解释，不倒退已签收结果；P0 整体缺项和 R01 后续事项仍保留。

## 7. 第三批签收后的剩余工作

基线 `4d1b3219e651723663906890655ee132a53224de` 已同步。第三批已交付及整改获限定验收。§6 是第三批前的准备顺序。后续以本清单及 [Q-04～Q-07 实施方案](p1-2-q04-q07-proposal.md) 跟踪。以下验收均待完成，拟定节点不替代开发指南的正式阶段要求。

| 剩余工作 | 实施任务与依赖 | 验收节点与证据 |
| --- | --- | --- |
| 缺失科学目标规范 | T04/T06 补真实 Scope、来源快照、历史／族／选择规则、指标、UnitSpec、TestSpec 与独立方法参考。T04/T09 补 MissingPolicy、FeedbackPolicy、StopRule、FailurePolicy、RetryPolicy、适用模板、套件及校准 | 在各目标首次被锁定或计算版本前核验版本、适用材料、归属和独立参考。T10 用真实内容的独立 fixture 验缺项阻塞，R04b/R06/R10a/R11 再按提供方职责验收 |
| 缺失权限及执行目标规范 | T05/T07/T08/T09 补任务合同、代码／数据／制品定位、准入、批准、预算、ExecutionBinding、校验 profile；依赖 Q-05/Q-06 及批准的目标版本 | T10 先用受控端口验证错目标／错版／撤销；真实接入须在首次相关准入前由 R09、R07、R08/R08b、R08c 验证 |
| 完整科学投影及版本 | T03–T06/T09，Protocol 依赖 Q-07 与策略目标，Prereg 依赖 Q-04/Q-06/Q-07 与历史、停止及批准条款目标，RunRequest/ExecutionBinding 依赖科学依赖图、Q-04/Q-06 及可信绑定；Q-05 签名在科学投影外单验 | P1-2 T10 固定逐字段参与表、独立 JCS 字节与 SHA-256、同内容跨归属及错版本反例，九个样例数值及手算原样 |
| 真实服务准入及状态／恢复 | T05/T07/T08 定端口及状态合同。P1-3 归属仓储、幂等与 CAS，P2-1/2 真实身份及预算，P2 R08/R08b/R08c/R24a/R14 接入租约、暴露、收集与对账。R13/R19 管证据事件，R21 管发布 | 纯契约验收可用替身。下游独立验证撤销、跨租户、迟到回执、重复副作用、预算和签名。P4 验计划替换，P6 验真实发布与检查点恢复 |
| 采样／描述型和完整数字性质 | T02/T04/T06/T09。补数值性质、出处和推导结构，采样／描述型待独立方法依据、单位／随机性设计及 A0 启用 | 启用前验证有效单位、合法重复、适用不确定性和独立统计参考。固定枚举样例继续作为既有回归 |
| Windows/Linux 一致性 | T03/T10，准备 Windows CPython 3.12 及同版锁定依赖，用两侧相同输入和独立预期 | P1-2 整体验收前登记两侧版本、规范字节及完整摘要比对。正式运行验收按 Linux 要求 |

## 8. 第四批实施后续

以 [第四批交付记录](p1-2-batch4-delivery.md) 为当前纯契约证据。Q-04～Q-07 的 A 方案获批准，第四批已由 A0 限定范围验收通过，签收提交为 `14162515f2a4ac5c55cd122e06e18a843291dff1`。

| 任务 | 本批工程交付 | 剩余验收节点 |
| --- | --- | --- |
| T03/T06 | 论断内容版本、证据事件和链头核对 | 补锁定来源与 Scope、真实权威事件。R13/R19 入图及 P6-3 恢复演练 |
| T07 | 签名前载荷、Ed25519 纯验证端口、受信回执和批准歧义阻断 | P2-1 接入完整冲突证据、身份、签名、撤销和替代。P6-2/P6-5 验真实包、公钥、公开回执及受限字段 |
| T05/T08 | 异常状态边、对账、止损、重试及更正纯轨迹 | 补 TaskContract、RetryPolicy、安全策略等目标。P2 验真实调度、节点、费用，P4 验计划替换 |
| T04/T09 | 固定四题去重、冲突拒绝和缺失处理 | 补锁定策略和实际标签材料，验证 R08 harness、R10a/G0。采样和描述型启用仍待批准 |
| T10 | 本地工程检查与新正反例，原样例字节核对 | 完整投影、目标规范、生成 Schema、调用方和提供方联验、Windows/Linux 一致性仍待 |

## 9. 第五批实施后续

见 [第五批交付记录](p1-2-batch5-delivery.md)。A0 已验收第五批限定范围及整改，签收提交为 `c378993cbbf19ff54452dc9165ed2cdfc59104d6`。

| 项目 | 本批证据 | 后续 |
| --- | --- | --- |
| T02/T06 归属与 Scope | 项目级受信委派、统一消息、旧缺项只读、Scope 三值比较 | 完整账号与租户记录、真实身份及只读服务接入；跨范围科研映射需获批准 |
| T03/T04 固定枚举目标 | UnitSpec、MissingPolicy、SelectionRule 子集及固定枚举 Protocol 独立预览向量 | 真实目标、精确授权及适用材料齐备前保持 Protocol 正式 ID 阻断；固定四题的 Prereg、RunRequest、ExecutionBinding 预映像及其限制见 §10 |
| T10 七入口及导出 | 首批注册、生成 JSON Schema／OpenAPI、调用双方共用合同及漂移检查 | 扩展全对象覆盖及调用／提供方契约验证，继续补金样例和状态边 |
| T03/T10 平台一致性 | Windows 3.12.14 与 Ubuntu 3.12.16 的 32 项规范字节／SHA-256 一致（含第五批整改新增 4 项），2 项非法输入均拒绝，两个 Schema SHA-256 一致 | 已完成本批向量对照。新增投影和端口继续扩大跨平台覆盖，Linux 正式运行仍单独验收 |

历史标记清除权限待 A0，其他批准用途缺少已审定条款结构时继续阻断。

## 10. 第六批固定四题纯契约

A0 已验收第六批固定四题纯契约交付及整改。签收提交为 [`8e411604`](https://github.com/wangshunshun0816/ai_for_science/commit/8e4116041114c1954c2209cbf689f6eb6d66eb84)。见[第六批签收](decisions/A0-P1-2-batch6-acceptance.md)与[交付记录](p1-2-batch6-delivery.md)。

| 项目 | 已交付 | 剩余与验收 |
| --- | --- | --- |
| T03/T04 固定枚举 Protocol | 只读目标解析、四题总体、适用性、基线及确定性预映像 | R04b 接入实际数据、切分、独立参考及协议批准。缺已审定 `protocol_use` 条款时阻断锁定 |
| T04/T05 固定枚举 Prereg | 问题／族／选择历史、完整四题停止规则、阈值和 Scope、Arm 与基线、批准科学条款投影 | R05/R06 提供完整历史及族检查，R06 核验真实有效签名后锁定。`family_confirmation` 条款仍缺；历史标记清除权限待 A0 |
| T04/T07 独立 ExecutionBinding 与确认 RunRequest | 代码／镜像／依赖／数据／方法及 sanity 的精确绑定、确定性确认预映像、对错批准的拒绝 | R08/R09/R10a 接入真实只读材料与 sanity、租约及启动授权；R07/R08c 接入实际预算及数据许可。相应用途条款缺失时阻断 |
| T03/T10 导出与平台证据 | 目标视图 Schema、能力表；整改后 Ubuntu 229 项、Windows 21 项，7 个一致预映像、7 项原拒绝、9 组整改检查和 2 份 Schema 摘要一致 | 后续补齐全对象、所有模式、I-SCHEMA 调用两侧及其余金样例覆盖。Windows 纯契约通过后仍需 Linux 正式运行验收 |

固定枚举首包采用精确 Scope，跨 Scope 的科研映射仍待审定。采样／描述型需独立方法参考及适用材料，其他未审定批准用途继续阻断。

## 11. 第七批任务与交接纯契约

见[第七批交付记录](p1-2-batch7-delivery.md)。A0 已签收限定交付及整改，提交 `e3b899b27842e1af7662252c2d0ed71781bbd6b8`，见[签收记录](decisions/A0-P1-2-batch7-acceptance.md)。本批支持 ResearchTask、TaskPlan／PlanRevision、PlanNode／TaskContract、ContextManifest、七类最小输出及授权交接。已验证的 task_kind 仅为合成夹具；生产启用须取得对应资格、批准和配置。完整计划派生政策、真实原子替换、任务调度、上下文策略及脱敏视图装配留待 R16/R08b/R14/R09。完整 SanityRequest／SanityReport、ProtocolBundle、RoleQualification、账户／租户／项目及未具备的角色工件目标继续按 P1-2 或其提供方节点跟踪。

## 12. 第八批及现行缺项

见[第八批交付记录](p1-2-batch8-delivery.md)。第八批已限定签收，提交 `126095ae4e8fc806559cbfc209e66aa8ef9b8501`。见[验收记录](decisions/A0-P1-2-batch8-acceptance.md)。固定四题 Sanity 请求与报告已交付，仍缺 SanityJobRef、SanityReportView 和完整协议工件。第五批关于计划、上下文及角色输出未注册的描述是历史快照，现行覆盖见 §11。第六批固定四题目标预映像与正式准入仍分开。

* 已批准：首组决定与 Q-04～Q-07 按绑定范围执行。Q05-C 已明确歧义阻断、保留冲突及授权撤销／替代，禁止自动取最新修订；展示排序属于工程规则，无授权效力。
* 仍待 A0：历史标记清除权限、未审定批准用途条款、跨 Scope 映射及采样／描述型启用。缺精确目标或适用依据时继续阻断对应操作。
* 仍缺契约：完整 ProtocolBundle、角色资格、账户／租户／项目、数据许可、全量工件类型及其独立金样例。多次关口混合结果的最终选择规则缺明确依据，保留待决。
* 后续服务验收：真实权限、真实报告与材料来源、审计执行、仓储、调度和原子接受。

## 13. 第九批归属契约

见[第九批交付](p1-2-batch9-delivery.md)。三种权威记录和委派引用读取守卫已限定签收，见[第九批验收](decisions/A0-P1-2-batch9-acceptance.md)。其余合同仍包括完整协议与检查工件、资格、数据许可和其他核心对象及统一出口证据。真实认证、仓储、认领和迁移按对应阶段验收，既有 A0 待决继续跟踪。

## 14. 第十批协议与 I-SANITY

见[第十批交付](p1-2-batch10-delivery.md)。固定四题协议工件与作业引用、报告视图已限定签收，见 [第十批验收](decisions/A0-P1-2-batch10-acceptance.md)。当前绑定选择规则和通用材料依赖语义仍待明确。其余缺项为运行证据、资源与数据边界、角色资格、科研历史及统一出口证据。

## 15. 第十一批执行记录

见[第十一批交付](p1-2-batch11-delivery.md)。运行及调用记录、R07 精确引用守卫已限定签收，见[第十一批验收](decisions/A0-P1-2-batch11-acceptance.md)。完整 Usage、Budget、数据政策和发送许可、角色资格、科研历史及统一出口证据仍待交付。

## 16. 第十二批 R07 用量事实

见[第十二批交付](p1-2-batch12-delivery.md)。Usage 金额事实及精确读取校验已限定签收，见[第十二批验收](decisions/A0-P1-2-batch12-acceptance.md)。计量口径、调整关联、调用结算与汇总仍待明确；预算操作、数据政策与发送许可、角色资格、科研历史及整体出口证据仍待交付。第十批的当前绑定选择规则及通用材料依赖语义仍待明确。

## 17. 第十三批预算预检

见[第十三批交付](p1-2-batch13-delivery.md)。已交付 reserve 请求、受信事实和只读额度预检，A0 已限定签收，见[第十三批签收](decisions/A0-P1-2-batch13-acceptance.md)（`17f9e0490e5d99d6ef9c6ce1d5d069062035cd4a`）。budget_use 条款、完整 Budget／BudgetEvent 与其余 I-BUDGET 操作、数据边界、角色资格和整体出口仍待跟踪。既有待决边界继续有效。

## 18. 第十四批及整体验收索引

见[第十四批交付](p1-2-batch14-delivery.md)、[整体出口台账](p1-2-r02-exit-matrix.md)及[预算操作待审提案](decisions/A0-P1-2-budget-operations-proposal.md)。§12–§16 为各批历史快照，账户归属、固定 Sanity 工件、运行记录和 Usage 的现行限定签收见整体台账及对应验收记录。
