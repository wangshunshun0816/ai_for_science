# A0 决策清单：R02 首组四对象契约

日期：2026-11-12。状态：**全部待 A0 审定**。基于提交 `f538edddc065b98445026e5f23088a3a52162e47` 中 [首组提案 §7](../r02-first-contracts-proposal.md#7-可逐项选择的-a0-决定)。本清单只解释选择，不批准任何科研语义、权限、投影或运行。

设计代号：[A 大方案](<../../Danus-AI 科研智能体产品架构与落地执行方案 v1.2 最终确认稿.md>)；[G 开发指南](<../../Danus-AI 落地开发指南：模块顺序、接口衔接与验收.md>)；[R 角色规格](<../../Danus-AI Agent 角色实现与验收规格.md>)。G §3.4/§5.3 要求全对象契约和独立验证，但没有替 A0 决定下列字段形状。A 的既定红线继续有效：模型不填有效身份、批准绑定精确版本、同 hash 不授访问权、科学改变新版本/适用批准；这些不是重新开放的选项。

## 1. Q-03：引用指向谁、谁可以读取

| 条目/要决定什么 | 推荐选项与具体字段 | 备选与选择后果 | 设计出处 |
|---|---|---|---|
| Q03-1：协议能否在同租户多个项目复用 | A：Candidate/Prereg/RunRequest 为项目级，Protocol 可租户级；服务填写 tenant_id、project_id、ownership_scope；每次项目使用另核授权，public 独立准入 | B：首批全部项目级，暂不启用跨项目/公开协议。A 可复用但要多一层授权；B 较窄，不能宣称已实现公共/租户级能力 | A §5.1、5.2、4.2；提案 §1/2 |
| Q03-2：模型请求携带哪些定位字段 | A：私有 Ref 仅 object_id+version；公共 Ref 另有 namespace=public、admission_ref；归属由 TrustedRequestContext/ResolvedRef 提供 | B：请求也带不可信 scope，仍逐项重验。A 输入较少；B 便于显式申请但需防错归属/信息泄漏。两者都不能把 tenant=null 当公共 | A §5.1/5.2、附录 A.1；R §3.2 |
| Q03-3：引用的工作记录 ID 是否影响科学摘要 | A：科学投影为 object_type+content_version；object_id 只作定位/权限依据 | B：有历史实体意义的引用保留稳定 ID，需列具体例外。A 允许同科学内容的不同记录科学等价；B 保留历史区分但会增加版本。不得据此合并授权记录 | A §5.2、5.1 SelectionHistory/FamilyDeclaration；提案 §1/7 |

未闭合：哪些引用具有历史实体意义、公共 ResolvedRef 的完整字段、AdmissionLocator 对应记录/撤销规则、SourceLocation 如何挂到每一 sources/original_source、引用 type/version/归属错误的稳定错误码。以上需在相应引用模型冻结前明确，负责人待 A0 指定。

## 2. Q-01：哪些内容定义科研版本

科学投影是“参与科研内容摘要的字段集合”。排除摘要不代表删除字段或免检。

| 条目/要决定什么 | 推荐选项与具体字段 | 备选与选择后果 | 设计出处 |
|---|---|---|---|
| Q01-1：候选草稿和来源如何表达 | A：draft={format,body}；background/new_inference/prediction/scope_ref 等入科学投影；sources 为精确版本集合；original_source/source_kind 区分原创、外部、synthetic | B：draft 用独立版本化科学规范 Ref，sources 有序。A 阅读直接，B 便于单独管理但增加对象。改预测/来源/科研正文均产生新版本；服务 version_ref/content_version 只能一个权威值 | A §5.1/5.2、C.2；R §4.2；提案 §3/8 |
| Q01-2：协议首包覆盖哪些研究类型 | A：design_type 覆盖固定枚举、采样比较、描述型；明确 metric、split_ref、baseline_refs、tuning_space、evaluation_unit、required_items、missing_policy_ref、duplicate_policy | B：先只启用固定枚举，其余 blocked。A 更完整但需各分支独立方法参考；B 更小但不等于 R02 全部完成。duplicate_policy 仍依赖 Q07，不能随选择 A 自动批准 | A §5.1、5.5、C.2/C.5；R §4.3；提案 §4/8 |
| Q01-3：预注册用可验证结构还是窄模板 | A：arms 有序；randomness_plan/discrimination_plan 明列适用分支；stop_rule 用 StopSpec；test/missing_policy/selection_feedback_policy 精确引用；family_alpha=null 仅不做采样推断且有理由 | B：保留 C.2 文本形式但限定具名模板与版本，不接受自由文本作为执行规则。A 可扩展但要迁移；B 实现较窄。两者都不改原九题文件、不静默补科学批准 | A §5.1、6.9、C.2；R §4.4；提案 §5/8 |
| Q01-4：运行的哪些前置材料进入定义 | A：按 mode 明确 prereg_ref/arm_id/seed/replicate_index 的 null；sanity_ref 是权威实测结果，不入科学投影；binding_spec_ref 的规范依赖版本入投影 | B：将报告的独立规范绑定摘要纳入定义，报告 ID 仍外置。A 减少结果与定义循环；B 需单独绑定摘要格式。sanity 不依赖自身报告，analysis_calibration 不强求已锁定正式 Prereg | A §3.9、5.2、6.16、C.3；R §4.5；提案 §6/8 |
| Q01-5：运行限制是方法还是付款额度 | A：ScienceLimits 的 max_steps/max_output_tokens/method_wall_time_seconds/method_memory_bytes 入科学投影；BudgetLimits 的 max_cost_minor/currency/approval_ref 等外置；SafetyLimits 仅在纯基础设施保护时外置 | B：所有资源限额入科学投影，身份仍排除。A 纯额度变化不产生新科学版本，但必须更新授权；B 更保守，纯额度也会增加运行版本。混合用途必须按科学限制处理并另验预算 | A §3.9、5.1/5.2、3.8；提案 §8/9 |

逐字段例：训练步数或生成截断改变方法，必须入投影；金额上限限制付款，仍强制核验但可以外置；墙钟/内存若决定抽样、截断或输出选择就是科研限制，不能改叫 safety 后排除。保护性中止不准缩分母后宣告完整，具体中止状态待 Q06。

## 3. Q-02：谁批准了哪个版本、何时要重批

| 条目/要决定什么 | 推荐选项与具体字段 | 备选与选择后果 | 设计出处 |
|---|---|---|---|
| Q02-1：批准目的与目标怎样绑定 | 推荐 A 的精确绑定方向：selection_use→候选版本；protocol_use→协议版本；prereg_lock→预注册版本；run_authorize→运行定义及数据/预算授权。purpose、record_id、revision 和目标版本须核验 | 原提案 A/B 边界有歧义：A 列 run_authorize，B 说明不增加逐run人工签字。建议将运行授权定义为服务核验已有批准的记录，**不自行增加 A0 每run签字**；如需人工动作必须另选并说明适用模式。完整目的/动作表未定前不能宣称本项批准 | A §3.9、4.1/4.2、5.1/5.3、C.2；提案 §7 Q02-1 |
| Q02-2：选择/阈值决定的哪些内容进入 Prereg | A：selection_terms/threshold_terms 的候选/范围/问题版本、meaningful_delta/value、单位/方向直接投影；selection_ref/threshold_decision_ref 的批准 ID、签署人、时间外置 | B：单独不可变“批准科研条款”摘要进入 Prereg。A 少一层对象，B 多条款版本/迁移工作；都须核验当前有效批准，避免把签名/批准引用递归放进其自身目标摘要 | A §5.1/5.2、6.9、C.2/C.5；提案 §5/8 |
| Q02-3：哪些变化触发新批准 | A：预测、阈值、方法、协议/数据/代码/范围等科研变化产生新科学版本并重做适用批准；纯预算变化只更新预算授权并重验使用资格 | B：科研变化同 A，纯预算变化也新建运行定义及相关批准。A 配合 Q01-5 A，B 配合 Q01-5 B。撤销/过期/错租户即使科学 hash 相同也拒绝；不能统一重批全部无关对象或沿用已失效批准 | A §5.2/5.3、C.5、3.9；提案 §9 |

原设计规定“精确版本绑定”，但没有规定上述 purpose 英文枚举及新增审批界面。名字、运行授权记录、操作者动作不得因这张清单自动成为已批准功能。

## 4. 仍有结构空缺或冲突，必须显式关闭

| 缺口 | 具体字段/问题 | 建议补齐方式（仍待审） | 依赖 |
|---|---|---|---|
| 权威记录与草稿边界 | 四表继承 status 必填，但又说 RunRequest 无自有状态机；草稿如何省权威字段没有独立字段表 | 拆 draft/authoritative/执行记录三种形状；RunRequest 不强加 status；逐个标出创建前与锁定后的必填字段 | Q03-1、Q01-4、Q06 |
| 双版本名 | Candidate.version_ref 与公共 content_version 两名存在但仅说不重复存 | 选一个正式字段，另一个只在显式适配器使用；拒绝二者冲突 | Q01-1 |
| 来源与 synthetic 分支 | SourceLocation 未明确挂载位置；synthetic_design 的 original_source 能否 null 未定义 | 来源项建具体 SourceRef 结构；逐一列 original/external/synthetic 的 null/位置约束 | Q01-1、Q03-2 |
| 两类引用混用 | Protocol.approval_ref、Prereg.selection_ref/threshold_decision_ref 写 Ref；又规定批准用 record_id+revision，非科学 Version | 分 ScientificRef 与 ApprovalLocator；明确每字段类型和 service 解析结果，补 authorizing target/version | Q03-2、Q02-1/2 |
| 目标规范尚空 | test、missing_policy、feedback_policy、random_sources、minimal_design_ref、selection_rule_ref 等只有 Ref | 为每种目标提供 schema版本、完整字段、权威来源和独立参考；目标缺失则 blocked，不能靠 Ref 假装结构完成 | Q01-2/3、Q03-3 |
| 类型分支及范围 | ParameterRange 界限是否闭区间/步长、MetricSpec 单位枚举、采样/描述型协议的完整守卫不齐 | 补边界、单位、范围及分支验证矩阵；如先批准固定枚举，把其他分支禁用状态写明 | Q01-2 |
| 计划映射 | DiscriminationPlan predictions 的 explanation_ref 要求位于外部引用内容，尚无对应目标合同；重复/独立单位结构未闭合 | 补显式映射、唯一性/覆盖约束及单位规范，不用“长度相同”代替 | Q01-3 |
| 模式与绑定循环 | RunRequest 一律 binding_spec_ref 必填，BindingSpec 又一律 suite/profile/configuration_ref 必填，探索等模式不一定具备；若 configuration_ref 指整个 RunRequest 则循环 | 列八模式字段矩阵；configuration_ref 只指独立方法配置版本，不指含 binding 的父对象；无套件模式怎样表示须审定 | Q01-4 |
| 参数/停止规则重复 | MethodConfig.parameters、MethodConfig.stopping、ScienceLimits、Prereg.stop_rule 可表达同一个约束 | 指定唯一权威来源和一致性规则；冲突拒绝，不规定任一层静默覆盖 | Q01-3/5 |
| 批准动作不完整 | prereg_lock 谁实际批准、run_authorize 是否人审、过期/撤销与绑定目标字段未闭合 | 单列 purpose→actor→target/version→前置→重新批准触发表；不隐含新增人审 | Q02-1/3、Q05/06 |
| 哈希历史/集合细则 | family_id 为 S，但引用投影建议去稳定 ID；selection_history 科学/审计分界、集合排序比较键未定 | 逐字段说明历史实体意义；确定规范化后集合去重/排序、冲突处理及版本迁移 | Q03-3、Q01、Q04 |
| 观测、签名、状态 | duplicate_policy、签名域/载荷、暂停/中止/修订边 | 保留 Q04～07 待决；本轮规范化键冲突测试不能代替观测去重、签名或状态验收 | Q04～07 |

“闭合字段形状提案”不代表以上语义/交叉约束已经完整。选 A 方向也不能自动关闭这些缺口。先决定方向，再补齐对应字段/分支表并绑定具体版本；原九题手算与数据不修改。

## 5. A0 填写区与后续验收

以下留空；空白不是默认采纳推荐项，自动测试不替代签收。允许逐项选择 A、B、修改后采纳或暂缓；修改请附字段清单和适用范围。

| 决定项 | 选择/修改意见 | 负责人 | 关闭结构缺口/适用范围 |
|---|---|---|---|
| Q03-1 | | | |
| Q03-2 | | | |
| Q03-3 | | | |
| Q01-1 | | | |
| Q01-2 | | | |
| Q01-3 | | | |
| Q01-4 | | | |
| Q01-5 | | | |
| Q02-1 | | | |
| Q02-2 | | | |
| Q02-3 | | | |

确认人：
日期：
意见：
结论：

后续验收：逐字段增删/更改的预期字节和版本变化矩阵；跨租户同 hash 不互读；错版本/撤销批准拒绝；各 mode 前置与 null/缺省；科学限制与纯额度变更对照；独立金样例。Windows CPython 3.12 环境及 Windows/Linux 一致性继续待办。本轮只整理清单和 CI 证据，不实现上述业务合同。
