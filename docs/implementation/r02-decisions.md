# R02 具体决策草案（Q-03 → Q-01 → Q-02）

日期：2026-11-12。**全部为待 A0 审定提案**；推荐准备文档的 A 方向，不是批准记录。负责人及科研/权限/数据独立复核者均待 A0 指定。

依据：[准备文档 §3.2](p1-2-contract-readiness.md)、[逐字段台账](r02-field-matrix.md)。A/G/R 代号及文件链接见台账 §1。本轮基础解析不依赖本草案批准，没有实现下列业务结构或生成正式 ID。例中的 angle-placeholder 不是有效 ID、摘要或生产载荷。

## 1. Q-03：不可信引用与受信归属分离

设计已定：A §5.1/5.2、§4.2、附录 A.1，R §3.2：模型不得提供有效身份；所有私有关系有 tenant，项目级有 project；公共独立命名空间/准入；相同 hash 不是访问权。

推荐 A：私有请求只携带定位条件；认证服务从连接/委派取归属并解析内部引用。建议结构（字段名称/必填规则本身待审）：

```json
{
  "private_request_ref": {"object_id": "<stable-object-id>", "version": "<exact-content-version>"},
  "trusted_context_server_only": {
    "tenant_id": "<tenant>", "project_id": "<project>",
    "principal": "<authenticated-principal>", "on_behalf_of_account": "<account>"
  },
  "resolved_ref_server_only": {
    "namespace": "private", "tenant_id": "<tenant>", "project_id": "<project>",
    "object_type": "CandidateHypothesis", "object_id": "<stable-object-id>",
    "content_version": "<exact-content-version>", "authorization_ref": "<verified-authorization>"
  },
  "public_request_ref": {
    "namespace": "public", "object_id": "<public-object-id>",
    "version": "<exact-content-version>", "admission_ref": "<public-admission>"
  }
}
```

这些是四种结构示意，不是一个可以同时提交身份和 payload 的接口。private_request_ref 无 tenant/project 字段；public 不以 tenant=null 表示，准入必须由服务核验。ResolvedRef 不是可序列化后永久复用的权限票据；每次操作复核当前权限/撤销。租户级资源是否要求 project_id，以及账户/全局配置/公共资源的范围按台账 §2 审定，不能把 null 当通行证。

建议校验顺序：认证/委派→当前 task/operation 权限→在受信归属内查 object_id+version→核验引用对象类型/内容版本→项目可用性或公共准入→返回内部引用。未知归属 legacy_incomplete 保持受限，不能猜测当前租户。同一科学哈希可存在多个归属记录，查找必须先限定归属。幂等作用域含 tenant、project、根任务/调用主体、operation，不跨租户复用返回。

A0 选择：A（推荐，以上）；B（准备文档已有备选）：payload 显式 scope 作为不可信查询条件，仍逐项核验。A 减少伪造入口，但需显式公共引用以及跨项目资源准入映射；B 便于显式跨项目申请但输入校验和错误泄漏面更大。两者都不能接受角色自报身份。请批准具体字段、租户/项目级映射及允许的引用方向，不能只批准原则。

变更影响：所有 ref/id 调用点、fixture 可信包装、DTO→只读解析端口、上下文/缓存/索引/恢复；不改九个旧 JSON。T02 identity/references、T04–T09 跨对象验证依赖此决定。测试计划：同 ID/hash/幂等键双租户拒绝互读；错版本/错类型/错项目拒绝；失效委派拒绝；公共未准入拒绝；错误不得泄漏异租户对象存在性。

## 2. Q-01：逐字段科学投影

A §5.2 已确定严格解析→Schema 缺省/投影→NFC/CRLF→领域十进制→JCS→UTF-8→完整 SHA-256。台账每一字段的 S/X/R/A/M 是待审分类，不是实现白名单。科研新增字段必须重新分类；未定 object 不能整体按“元数据”排除。

推荐 A：科学定义与授权/执行事实分层。最优先审定下表及台账全部 S/R/M 行：

| 对象/路径（提案） | 科学投影 | 外置而仍强制核验 | 未决细节/影响 |
|---|---|---|---|
| CandidateHypothesis | background、sources 的科学版本、new_inference、prediction、draft 的科研内容、original_source、source_kind、scope_ref | candidate_id、身份、时间、状态/显示；version 为派生/定位 | sources 顺序/集合、draft 子字段 Q-01；来源权利/归属 Q-03 |
| Protocol | 数据/切分精确版本、metric、baseline_refs、tuning_space、sanity_suite 规范版本、applicability_template、design_type、evaluation_unit、required_items、duplicate_policy | 协议记录 ID、批准签署元数据 | 套件是否全部或只科学适用部分进入须逐字段审定；duplicate_policy Q-07，不能临时选策略 |
| Prereg | 候选/协议版本、family/question/声明/历史语义、RandomnessPlan、DiscriminationPlan、arms、estimand、test、analysis_ref、effect_threshold、inference、missing_policy、selection_feedback_policy、stop_rule、family_alpha 及科学理由 | 记录 ID、选择/批准 ID、签署身份/时间、当前批准状态 | selection/threshold 科学条款投影见 Q-02；null/缺省和列表分类不能先猜 |
| RunRequest | mode、code/image/data 精确版本、seed、arm、prereg 科学版本、deterministic、replicate_index、configuration 中科学方法、resource_limits 中科学停止条件 | 纯额度授权、凭证引用、排队/租约；sanity 结果记录外置核验 | sanity 依赖的协议/代码/环境/配置版本仍须固定；结果不直接进入 run 定义以免自循环 |
| Scope | 目标总体/样本框/选择机制、任务/数据/模型版本、规模/硬件/精度、estimand | 私有归属、展示 | 范围结构和可比映射不能由字符串等价代替 |
| ClaimSubmission | statement_template、scope、run_ids 的定义版本、protocol/prereg/前提版本 | submission_id、处理状态、服务测量字段 | run_refs 旧名仅 fixture/迁移适配，双方并存拒绝 |
| ClaimNode / EvidenceEvent | 不可变陈述/范围必保留；六维/来源细化 Q-04 | strength/status_flags 当前投影；事件 actor/时间进独立审计 | 不在 Q-01 下提前代替 Q-04 审批 |
| 预算/用量/批准/发布及其余对象 | 按台账区分科学内容、授权、配置及事实；不是每个对象都发科研内容 ID | 记录仍需摘要/审计/签名 | 不因“排除科学 hash”删除字段；审计 Q-04，签名 Q-05 |

### 2.1 运行方法、停止条件与纯预算逐字段区分

以下英文子路径是提案，尚未产品化。同名 limit 不能仅凭名称决定是否进科学哈希：

| 字段路径 | 推荐分类及规则 | 改值后果 |
|---|---|---|
| execution.method_version | S/R；具体方法代码/配置版本 | 新运行定义，重新核对批准 |
| execution.max_steps | S；训练/搜索步数属于方法或停止条件 | 新 ID；不得只改预算冒充原方法 |
| execution.max_output_tokens | S；改变模型生成截断/输出分布 | 新 ID；与总计费 token 上限分开 |
| execution.stopping_rule | S；规则、阈值、窗口、适用单位全部明列 | 新定义/预注册；不能测试后调规则 |
| execution.required_items / sample_count | S；评价/样本计划 | 新定义；耗尽预算不能缩分母 |
| execution.seed / replicate_index | S；按 A §5.2 区分随机性与基础设施重试 | 新 run，不能伪装同 attempt 恢复 |
| execution.precision / hardware_semantics | S；若影响数值/适用范围必须锁定 | 新科学定义/范围 |
| authorization.max_cost_minor / currency | X；纯付款额度，金额单位/精度另审 | 额度变更仍须新授权；科学 hash 可不变 |
| authorization.budget_approval_ref / payer_ref / credential_ref | X；权限凭证不属于方法 | 每次实时验证，不能凭 hash 复用撤销授权 |
| scheduling.queue_priority / host_locator | X，仅纯排队/位置，无方法影响 | 仍记录审计；若硬件影响科学则另入 execution |
| safety.wall_time_limit / lease_deadline | 条件分类：若它定义方法的截断/选择结果则 S；若只是基础设施硬停止则 X | X 情况中止后不得当完整结果；valid/invalid/incomplete 按协议守卫，不自动宣布无效或科学否定 |
| resource_limits.memory_limit | 条件分类：影响算法/批量/样本选择则 S；纯隔离防护 X | OOM 不准少算样本后成功，也不准自动改方法重试 |

建议消除含混单字段 timeout/max_tokens：分 execution 与 authorization/safety，拒绝无法归类的配置；同一个限额同时影响方法和费用时科学分支优先，授权仍另验。科学停止条件并不授予超预算权，预算耗尽也不允许偷偷改变停止条件。上述中止后的具体状态边依 Q-06，工程不擅自新增边。

### 2.2 缺省、列表与规范化待审细节

建议无设计缺省的科研字段显式必填，不能以 null 等价缺失；具体字段由台账审批。C.2 的 family_alpha=null 仅有限枚举且有原因；C.3 deterministic seed=null 不外推随机任务。required_items/候选集合拟集合型，arms/计划执行序列/选择历史的顺序是否有科学意义逐项审定，不能全局排序。stop_rule 在 C.2 为字符串，拟结构化时需要显式 fixture 适配和版本迁移，不直接修改样例。

规范化之前重复 JSON 键拒绝已经实施；NFC 后键碰撞、非 Unicode 标量、JCS 向量及哈希输出是 T03 后续，未声称通过。本轮 Decimal 精确解析不是完整规范化。验收需独立预期字节/摘要及 Windows/Linux 比对，不用被测算法给自己生成答案。

A0 选择：A（推荐，按上表分层）；B：所有资源限额均进入运行定义（仍排除身份/执行状态），更保守但单纯额度变动也生成新版本。请逐字段批准含混限制的分界、默认/null、集合顺序及引用科学投影；台账 object 内部结构没有确定前不得冻结完整 Schema。

## 3. Q-02：批准绑定精确版本且避免循环摘要

设计已定：A §5.1–5.3、C.2/C.5，candidate 的稳定工作 ID 不代替内容版本；科研核心改动须新检查/批准，出现 approval_ref 不等于批准。

推荐 A 的两个分层示例：

```json
{
  "science_payload_proposal": {
    "candidate_version": "<exact-candidate-science-version>",
    "protocol_version": "<exact-protocol-science-version>",
    "question_version": "<exact-question-version>",
    "meaningful_delta": "0.1",
    "threshold_terms": {"comparison_direction": "<direction>", "unit": "<unit>", "scope_version": "<scope-version>"},
    "selection_history_version": "<science-history-version>",
    "family_declaration_version": "<family-version>"
  },
  "approval_binding_server_only": {
    "approval_id": "<approval-record-id>",
    "purpose": "<approved-operation>",
    "target_ref": {"object_id": "<target-id>", "version": "<exact-target-version>"},
    "science_digest": "<full-digest>",
    "tenant_id": "<tenant>", "project_id": "<project>",
    "signer": "<authenticated-A0>", "approved_at": "<server-time>",
    "authorization_scope": {"budget_ref": "<budget-authorization>"},
    "status": "<current-approval-status>"
  }
}
```

这是字段投影示意，不是完整 Prereg；不得将示例直接当有效批准。scientific payload 的 threshold_terms 必须来自选题/阈值决定的已批准版本，不能由 A4 新填后自认批准。原 selection_ref/threshold_decision_ref/approval_ref 作为权威溯源定位保留，但投影的是不可变科研条款/版本而非签署人/时间。科学历史只投影候选/规则/暴露的科研事实，不把身份和记录时间混入；具体历史字段按 Q-01、事实链按 Q-04。

建议验证顺序：
1. 按 Q-03 解析同归属具体版本及当前有效批准，核验批准用途/范围。
2. 比对候选、协议、阈值、问题、族与历史的精确版本，拒绝旧版或错对象批准。
3. 科学条款构建/规范化后得到版本；权威信封绑定该版本及归属。批准信封摘要/签名不能递归进入它所批准的科学载荷。
4. 每次锁定/运行重新核验撤销、过期、权限及预算；即使科学 hash 相同，也不能复用已撤销批准。过去事实不删除，当前使用资格另判。

不同批准目的可能分别绑定 Candidate/Protocol/Prereg；不要求候选批准绑定尚不存在的 Prereg hash。Prereg 的审批/锁定动作目标与所需上游批准列表由具体合同登记，不能拿一个通用 approval_ref 代替全部守卫。

A0 选择：A（推荐，直接科学投影）；B：定义独立不可变“批准科学条款摘要”并纳入 Prereg，授权仍外置。B 增加条款对象/版本/迁移工作，仍不允许循环引用。请明确 selection/threshold/history 各字段的科学投影、不同批准目的/目标以及变更后的重新批准动作。身份/权限/科研语义决定由 A0 审定，工程只建议结构。

验收（尚未执行）：改变 prediction、方法停止规则、阈值、scope 或协议版本→新科学版本，旧批准拒绝；仅换签署时间/批准记录元数据→科学版本不变但授权仍验；相同科学 hash 的另一租户不能借用批准；撤销/过期/错目的/错版本/不一致 terms 均拒绝。纯预算调整不暗改科学定义，也必须通过授权。

## 4. Q-04～Q-07 与本轮依赖

| 待决 | 本轮是否依赖 | 受阻部分/关闭点 |
|---|---|---|
| Q-04 论断六维/来源投影、记录 ID/摘要/链 hash | strict 基础类不依赖；台账保留 A/未定 | ClaimNode/EvidenceReport/Event/GateExecution、审计链字段与哈希定稿前 |
| Q-05 签名载荷/域分离/外层回执 | 不依赖；没有签名代码 | Approval/ReleaseManifest 签名 Schema 冻结前；不把 science_digest 当签名规范 |
| Q-06 全状态边集/守卫及工程三维记录 | 不依赖；没有状态转换实现 | paused 恢复、reconciling、终态修订、资源中止有效性；状态机验收前 |
| Q-07 相同/冲突观测行处理 | 不依赖；JSON 重复键与重复样本是两回事 | duplicate_policy、观测单位/冲突/合法重复测试，协议和 G0/R10a 观测合同前 |

原九个金样例保持字节不变，expected_derivation 手算不被本提案替换。未完成项均未标通过。A0 审阅时请绑定本次提交和台账版本，并指定上述责任人；没有要求在本轮先批准才保存/提交工程交付。
