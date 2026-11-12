# P1-2 后续实施方案：Q-04～Q-07

状态：供 A0 审定。本文中的推荐字段、未定状态边和策略选择尚待批准。已签收基线为 `4d1b3219e651723663906890655ee132a53224de`。开工时本地 HEAD、origin/main 和 GitHub main 均为该提交，工作区干净。A0 于 2026-11-12 通过第三批已交付及整改范围，含整改提交 `56847f4ac38e16c80da608cad194b1aea5d6013a` 的 165 项本地测试与对应 CI。签收范围以 [第三批验收记录](decisions/A0-P1-2-batch3-acceptance.md) 为准。

出处代号：[大方案 A](<../Danus-AI 科研智能体产品架构与落地执行方案 v1.2 最终确认稿.md>)、[开发指南 G](<../Danus-AI 落地开发指南：模块顺序、接口衔接与验收.md>)、[角色规格 R](<../Danus-AI Agent 角色实现与验收规格.md>)。首组仍按 [A0 已签收决定](decisions/A0-R02-first-contracts-checklist.md) §5–6 和绑定提交 `48bd0dcc0afa78c2b6447fdfe789465b0d3a8068` 的提案执行。当前 `references.py` 已分型科学引用、历史引用和权威定位，`projections.py` 仅对条件具备的候选计算对象版本，`guards.py` 对精确批准做只读核验。以下字段名和错误码示例用于 R02 设计，后续由类型源导出。

## Q-04 论断投影、事件和链

**既定**。A §5.1–5.5、§8.6–8.8、§12.2。R13 是论断入图唯一提交入口。陈述、范围不可变。六维独立，负面结果可有高强度。外部报告、数学引用保持来源和边界。科学身份与租户权限分开，保留旧 `danus_fact:<id>`。规范化沿 A §5.2，关键事件链按 §12.2 每日及每次发布独立导出签名链头。

| 论断字段 | 推荐投影与变更规则 |
| --- | --- |
| `statement, scope_ref` | 科学内容。Scope 按精确版本引用，陈述或范围改变时创建新科学版本并重新过门 |
| `kind, outcome, origin, logical_level` | 科学内容。按 §5.4 枚举和适用性约束，层次无默认映射为强度。数学引用保留明确引用，不能代填经验结果 |
| `strength, status_flags` | 由已接受的证据事件推导当前值。首个接纳事件保存初值和依据，后续升降级、撤销、污染标记追加事件，科学版本稳定 |
| `origin_binding` | 带 origin 判别符。内部实验绑定形成该陈述所用的锁定运行定义、协议／预注册科学版本，确切前提用精确版本。外部报告绑定来源快照科学版本及位置。数学绑定原样 `danus_fact:<id>` 与受权来源快照／版本，状态另作使用资格核验 |
| 证据与审计引用 | 报告、尝试、原始制品摘要、审计记录定位留在证据事件，供回查形成结果的实际证据。后续复现若只改变支持强度，追加证据，若改变陈述、范围、结果或定义性来源则走新版本 |

**A0 选择 Q04-A（推荐）**。冻结上述形成时的定义性来源于科学投影，复现追加不改版本。Q04-B 将内部形成时的运行／协议／预注册绑定仅存于首个证据事件，科学版本只区分陈述、范围、科学分类及外部／数学出处。B 能聚合更多等价表述，必须从事件分辨不同内部形成路径。两案都保存完整出处并核验访问权。A0 决定哪些差异构成新科学论断，摘要封装与索引由实施者负责。

| 标识或摘要 | 预定字段及计算边界 |
| --- | --- |
| 科学内容版本 | `claim:v1:<完整 SHA-256>`，白名单科学字段规范化。归属、当前资格、证据事件和签名外置 |
| 记录 ID 与修订 | 服务分配稳定 ID，在受信 tenant/project 内定位。EvidenceReport、GateExecution、EvidenceEvent 有独立定位与记录修订，报告与关口事实摘要使用记录域，无需发科研内容 ID |
| 事件摘要 | 不可变事件载荷含 `schema_version,event_id,event_kind,claim_ref,report_refs,artifact_digests,change,reason`。关键对象事实使用带类型与版本的摘要，保存可回查的确切记录引用 |
| 链摘要 | 对独立域内 `chain_id,sequence,previous_chain_digest,event_digest,object_digest,schema_version,timestamp,tenant_id,project_id,on_behalf_of_account,actor,task_ref,plan_revision,operation,object_ref,result,cost_ref` 的规范字节计算。链条和事件本身可独立复算。按租户归属串行编号，项目为记录字段，分链及创世规则显式版本化。检查点绑定链 ID、序号、链头及快照范围，签名保存于应用写权限之外 |

例：追加有效复现令 supported→replicated，事件摘要和链头变化，科学版本不变。扩到新总体产生新版本。移动外部报告所引页码按 A 产生新版本。改 actor、删中间事件、重排或截尾与独立检查点不符时验收失败。仅凭匹配科学 hash 越租户查找拒绝。T03/T06 独立字节向量和链篡改测试先行，R13/R19 与 G P6-3 验证真实事件和恢复检查点。

## Q-05 签名前载荷、域、信封与回执

**既定**。A §2.4、§5.1–5.2、§6.30、§12.2，G §4 发布与恢复流程及 P6-2/P6-5。A0 对准确 manifest 签字，操作者本地持 Ed25519 私钥，控制服务只验证公钥。完整发布清单绑定代码、依赖、镜像、结果和证据快照，改稿重检重签，实际发布回执才允许 released。已有批准用途沿首组提案 §5。R06 锁定及 R08/R09 运行授权是服务动作。

| 结构 | 拟定字段与绑定 |
| --- | --- |
| `ReleaseManifestBody` | `schema_version,release_ref,scope,evidence_snapshot_ref,artifact_manifest,code_ref,dependency_lock_digest,image_digest,sbom_refs,data_license_refs,public_mapping_ref,reproduction_steps,result_tolerances,disclosures,check_report_refs`。每个制品含规范逻辑路径、大小和完整摘要，锁定许可及公开边界。完整签前 body 计算 `release_manifest_hash` |
| `SigningInput` | `schema_version,domain,purpose,key_id,algorithm,issuer_id,subject_ref,subject_digest,authorization_scope,issued_at,expires_at`。批准域含归属、精确记录修订、目标版本和条款摘要。发布域含发布定位和 manifest hash。可公开签署信息采用公开标识，私有归属映射留授权视图。检查点域绑定 Q-04 链头及快照范围 |
| `SignatureEnvelope` | `signing_input,signature`。签名覆盖规范化输入字节，验证方用配置的域、用途、可信 key_id 及算法校验，重算 subject_digest。信封签字摘要可由 ReleaseManifest 读视图展示，位于签前 body 外 |
| `ReleaseReceipt` | `record_id,revision,release_ref,manifest_hash,envelope_digest,action,channel,external_locator,artifact_digest,occurred_at,verified_by,result`。R21 经实际交付证据记录，发布、撤回分别追加。下载包可交付给用户，外部公开发布须有对应渠道回执。未知结果先核对渠道，避免重复发布 |

**A0 选择 Q05-A（推荐）**。批准、发布、独立检查点采用独立用途域和相应信任用途。发布离线验证包包含签前 manifest、签名信封和公开验证所需的可信公钥定位。允许公开范围内展示回执证据，受限字段留控制服务。Q05-B 保持相同密码学绑定，公开包只含 manifest 与签名信封，回执只在受权查询中提供。区别在回执公开粒度及离线可证明的发布事实。两案均禁止在签名输入中循环嵌入签名／回执，允许已批准的具体渠道，钥匙轮换和撤销时间规则仍需管理合同。工程建议使用带版本的规范 JSON 表达不同域，验证按预期用途查公钥，拒绝未知域和不受信密钥。

例：内容未改且签名用途正确时离线验签通过，添加回执不改变 manifest hash。换任一结果、镜像、许可或制品字节，验签／摘要复算失败。有效的预算签名不能签发发布。重放同一回执返回原事实，签过但未取得实际回执仅是 signed。T07 先做固定密钥测试向量、错域、错版本、撤销及改稿测试，P2-1 和 P6-2/P6-5 再验证真实钥匙和制品。

## Q-06 异常边、权威写入与工程三维

**既定**。A §5.3、§6.10–6.11、§6.25、§12.2、C.5，G §4 状态、事务及恢复条款。Task、Attempt、科学资格、提交和发布各有原枚举。RunRequest 是锁定定义，RunRecord 是尝试聚合。恢复不得跳过当前计划、权限和租约，不以进程退出码或技术失败作科学结论。R08 基础设施故障最多自动重试 2 次，仍须服从预注册更严限制。默认采用第一个有效完整尝试，意外多个按预注册处理。

| 对象／状态边 | 守卫、权威写入方与后果 |
| --- | --- |
| ResearchTask 的活跃阶段 → paused / blocked | 保留 `prior_phase, reason_ref, active_plan_revision, pending_reconciliation_refs`。R09 管理入口或 R16 经控制服务登记。R08b 停新领取，运行中任务按授权决定继续或请求取消，保留历史 |
| paused / blocked → 合法原阶段，或 → cancelled | 恢复需现行计划、输入、权限、额度、租约及外部事实完成核对。先解除原阻塞，不能跳过科学阶段。控制服务按 `expected_revision` 原子转换。取消阻止新负债，不自动宣布资源已停或费用已清 |
| Attempt reserved / running / collecting → reconciling | R08 协调器登记未知状态及查询依据，R24a 提供节点／平台事实，R07 独立记录费用。过期 fencing token 禁止直接写状态。保持同一 attempt，封住未知外部副作用下的自动重试 |
| reconciling → running / collecting / succeeded / failed / cancelled | R08 可信收集器按匹配的外部身份、租约、制品和状态证据恢复。仍运行回 running，已执行待核制品回 collecting。成功只接受经校验的制品。证据缺失则留 reconciling。账务未清另标待对账并限制新增负债 |
| 保护性中止 | R08b/R24a 执行租约、纯基础设施安全和预算止损，R08 按可信事实写取消或失败原因，外部未知转 reconciling。R07 保留已花和未结费用，释放可确认未花部分。R08 可信收集供科学资格评定，缺必需输出为 incomplete，污染／违协议证据可判 invalid。不得缩分母或自动判科学否定 |
| 旧 Attempt 终态 → 新 Attempt queued | 仅同一锁定 run、已确认基础设施失败、RetryPolicy 允许、预算及权限重验、无未知重复副作用且未按结果选择。旧尝试原样留存。换方法、代码、数据、种子或预声明 API 复现索引走新 run |
| 终态事实修正或科研修订 | 追加带 `supersedes_ref,reason,evidence_refs,expected_revision` 的有权更正，保留原事件。R08/R07 分别更正执行事实和账务，R13 处理证据接受和资格变更，R21 处理发布修订／撤回。改候选核心、批准协议、锁定 Prereg 或发布内容创建新版本，重走适用守卫。已拒提交改稿另建 submission，已发布包撤回另记，科研任务完成不被反向改写 |

**A0 选择 Q06-A（推荐）**。暂停采用分级策略：停止新任务，已经启动的工作只有在现有授权有效且处置记录明确允许时才能继续到可安全收集点。授权撤销、租约失效或保护条件触发则按设计止损。Q06-B 对普通暂停也统一请求取消运行中任务，降低继续消耗的可能，但更易损失已投入的工作。两案均保留强制中止、对账、审计和预算边界。具体恢复截止、可继续范围和额度由版本化 TaskContract／SafetyLimits／RetryPolicy 确定，缺配置阻塞。上表异常边是 R02 推荐收敛形状，明确的设计约束先落实。

工程三维保存在绑定工作项、范围与版本的独立工程验收记录，字段为 `work_item_ref,scope_ref,revision,decision_status,implementation_status,evidence_status,decision_refs,delivery_refs,evidence_refs`。沿 A §5.3 原枚举。A0 决定人写决策，工程维护者凭提交登记实施，指定复核者凭实际测试／评测登记证据，A0 或已授权验收者登记验收。三类写入有独立来源、时间和记录历史。R02 导出结构，项目实施记录先用同一口径，未来控制服务采用单一权威记录。论断及任务的科研状态各自投影，不由三维工程字段推导。

例：收集器崩溃后重新接管原 attempt 和制品，计费不重复。旧实例迟到回传只交受信收集器。保护性中止缺 q4 为 incomplete，进程退出 0 但无可信制品不能 succeeded。对账未完成即购买第二份资源、结果不好才重试、签收设计即写工程验收均失败。T05/T08 用故障注入状态轨迹验纯契约，P2 R07/R08/R08b/R24a/R14 再验真实收集、费用、取消和恢复，P4 验证计划替换。

## Q-07 观测行、冲突和合法重复

**既定**。A §5.2–5.3、§6.11、§8.4、C.2–C.5，R §4.4 TC-A4-02/05。评价单位由锁定协议先声明，R08 harness 计算可信指标和有效样本量。固定枚举的分母为每臂 q1–q4 各一次，缺任一题为 incomplete。确定性再跑是 repeatability。基础设施尝试不能作为独立样本，预声明 API 复现另有 run_id。

| 分类及判据 | 推荐处理 |
| --- | --- |
| 可信输入及单位键 | 锁定协议引用 `unit_spec_ref,missing_policy_ref,duplicate_policy`，按受信 `run_ref,attempt_ref,arm_id` 限定来源后，从固定总体提取 `item_id` 为每臂单位键。原始行、制品摘要、输入位置不可变。行等价按严格校验后的科学观测字段比较，传输重放标记独立留存，未知字段不得忽略为等价 |
| 完全相同行，同单位同预测及适用观测字段 | 原始行留存，评价视图去重，登记 `unit_key,source_row_refs,duplicate_count,policy_version`。伪称额外有效单位的提交按原样例拒绝 |
| 同单位冲突行 | 保存全部位置和内容，当前 attempt 的冲突单位不可用于评分，拒绝当前观测包的科学资格并记录冲突。缺证或冲突走既有守卫，不择首、择末、平均或择优，也不能删掉冲突题后使用缩小分母 |
| 合法重复试验 | 独立重复仅在 RandomnessPlan/UnitSpec 已锁定并验证样本、配对、聚类、种子／复现索引时可按声明分析。每次四题重跑仍各自为四题，独立采样是否成立须经适用方案证明 |
| 校验输出 | 建议 `expected_unit_keys,observed_unit_keys,missing_unit_keys,duplicate_groups,conflict_groups,attempt_ref,policy_ref`。供 T09/G0 及可信 harness 消费。方法进程不提供权威标签或计数 |

**A0 选择 Q07-A（推荐）**。完全相同的行保留原始证据并对评价视图去重，同单位冲突拒绝该观测包。Q07-B 连完全相同的重复行也拒绝原包，需按协议处理重传或重收集。B 更严，增加纯传输重放引发的拒绝。两案都拒绝伪样本量、保持分母，当前固定枚举之外的采样轨道按既有边界。具体观测字段与单位注册由 T04/T09 固化，未知策略显式阻塞。

正反例见 [四题手算及九个金样例](p0-2/golden/README.md)。正例 2/4、3/4，差 0.25 > 0.1。有限否定两臂均 2/4，差 0。复制 q3 十次仍为四单位，宣称 14 拒绝。q3 同臂出现相反预测走冲突分支，缺 q4 不得算 2/3 和 3/3。G2 超时仍按原样例未接受，技术错误不改变原始差值。T09 新增行顺序、精确重复、冲突、跨尝试和合法重复的独立例子，保留原九个 JSON 与手算原字节。

## 批准绑定的遗留行为

现有 `RecordMetadata.approval_bindings` 按 `purpose,record_id,revision` 精确去重，保留首次出现顺序。不同三元组均保留。现有 `require_approval` 逐条核对目标、用途、归属、当前有效性，拒绝错绑定。

| 问题 | 归属及推荐 |
| --- | --- |
| 同 record_id + revision 在同归属权威库声称不同用途、目标或条款 | Q-05 签名主体一致性，Q-04 留证。保留所有冲突输入并阻断相关授权，由有权人核查，不能因某签名可验就自动选它。请求中不同用途 locator 的存在仍不授予权威事实 |
| 同记录的多个 revision 或多个同时有效批准 | 现有精确版本原则继续执行。请求或领域合同指定精确修订并核验有效性。签名撤销、替代与重签属 Q-05，正式审批生效及冲突处置合同待 A0。歧义阻断并保留冲突，不能按数字最大、时间最新或数组末尾选择 |
| 对外展示排序 | 独立工程规则。授权过滤后，导出可按 `purpose,record_id,revision` 稳定排序并在导出合同声明，保留来源记录及冲突。当前 DTO 的首次出现顺序保留，排序与授权优先级无关 |

A0 在 Q05 下另审 **Q05-C**：歧义时由有权人发布明确的撤销／替代记录（推荐），或仅撤销冲突批准后重新批准。两案在处置完成前均阻断。前者保留更明确的版本关系，后者规则较窄但增加重签成本。不同修订正常并存且用途、有效性和目标明确时，继续使用精确定位。

后续任务、目标规范和验收节点见 [剩余工作清单](p1-2-contract-readiness.md#7-第三批签收后的剩余工作)。A0 逐项选择见 [精简决策清单](decisions/A0-P1-2-Q04-Q07-checklist.md)。
