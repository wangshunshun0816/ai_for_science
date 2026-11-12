# P1-2 第五批人工验收记录

状态：A0 已于 2026-11-13 完成整改复验，结论为通过，范围仅限 P1-2 第五批已交付及整改内容。

## 批准依据与提交核对

已读取 AGENTS.md。本批授权覆盖 Scope 三值比较、身份与消息基础、I-SCHEMA 首批注册与导出、固定枚举 Protocol 准备及原生 Windows/Linux 纯契约对照。依据开发指南 §3.4／§5.3、大方案 §5.1／§5.5／§6.4 与附录 A.1，沿用 [首组批准](A0-R02-first-contracts-checklist.md) 与 [Q-04～Q-07 批准](A0-P1-2-Q04-Q07-checklist.md)。开工基线为第四批限定签收提交 `14162515f2a4ac5c55cd122e06e18a843291dff1`。实施和测试范围见 [第五批交付记录](../p1-2-batch5-delivery.md)。

|核对对象|结果|
|-|-|
|本地 HEAD、origin/main 和实际远端 main|均为 `7fac273dfc82bb83040beff5f0f6fa84caed8474`，起始工作区干净|
|第五批代码和 CI 实际运行 SHA|`4cbc58651fc88489d510201263b2538611ee0e76`|
|证据提交的差异|`7fac273dfc82bb83040beff5f0f6fa84caed8474` 的直接父提交为上述代码提交。仅修改 `docs/implementation/commit\\\\\\\_log.md` 与 `docs/implementation/p1-2-batch5-delivery.md`，3 行新增、2 行删除|

## 逐项交付与审查结果

|项目|已交付及可复查边界|
|-|-|
|Scope|`scope.py` 提供 known、unknown 和 not\_applicable，区间按包含／交集，硬件按集合，精确引用按相等比较。已有测试验证区间、硬件冲突、缺字段、未知及拒绝隐式布尔转换。不同总体／观察数据等需要映射时不能直接推出相等。采样比较在其他维度相同、两边观察数据已知时无需观察集相交。比较结果本身不证明样本统计独立性，也不启用采样研究。核心维度的不适用约束见整改项|
|受信上下文和旧记录|`messages.py` 逐项比较受信上下文和委派，检查委派及租约精确定位、撤销、用途、到期时间。请求形状拒绝自报身份。现有只读端口测试同哈希跨租户拒绝、错版本拒绝。`read\\\\\\\_legacy` 仅返回精确定位且同归属的缺项视图，`content\\\\\\\_id(LegacyIncomplete)` 和显式带 legacy 标记的引用解析拒绝。未知归属读入继续受限。用途和目标约束向后续查询传递的缺口见整改项|
|I-SCHEMA 注册和导出|`api.py` 提供七入口。validate\_object 注册 47 个顶层合同，6 个调用方合同为 CandidateDraft、ProtocolDraft、PreregDraft、RunRequestDraft、ReferenceRequest、Scope。40 个服务持有合同涵盖相应权威记录、论断／审计、批准／签名、执行与状态快照、委派／响应／旧记录及固定枚举目标等。EvaluationView 仅输出。未知名字、未受信调用及输出型入参被拒绝。validate\_transition 支持 task、attempt、settlement、retry、correction、engineering，首次分派测试覆盖 task 正反例，其余分支的底层规则由第四批测试覆盖。content\_id 只处理候选和论断，未完对象不发 ID。另有 canonicalize 和三个 scope\_\* 入口。两个 Schema 从同一注册表生成，调用和提供方示例均使用 ReferenceRequest，OpenAPI 仅提供组件。运行时校验与导出表达的差异见整改项|
|Protocol 预览与发号|`protocol\\\\\\\_targets.py` 提供 FixedUnitSpec、FixedMissingPolicy、SelectionRule 及其引用配对，复用已批准的重复策略。预览检查缺失策略引用、单位／总体链接和调参引用覆盖，产生规范字节。实验探针将 required\_items 改为 q99 后仍可预览，说明入口只检查合同结构和定位配对，未核验实际总体或规则内容。ProtocolDraft／Record 的正式 content\_id 均明确阻塞。未来启用前需取得真实数据、切分、总体、规则全文及独立依据、指标、基线、适用模板、套件，并由可信端口验证归属和精确目标|
|跨平台|Windows 原生 **3.12.14**、Ubuntu **3.12.16**，两侧项目锁相同，核心包版本均为 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4。Windows 现有 uv 下载源未提供 3.12.16，证据限于实际补丁组合及选定测试|

## 测试及跨平台证据

Ubuntu 原交付 `bash scripts/verify.sh` 通过 **200 项测试**，包括锁、静态检查、类型、导入边界、Schema 漂移、源码包和 wheel。Windows 执行 `test\\\\\\\_canonicalization.py` 和 `test\\\\\\\_batch5.py`，**75 项通过**。本轮核对已有测试日志与向量证据，并执行了只读契约探针，未重跑完整套件。原九个金样例与手算记录保留核对见 [保留文件比对](../evidence/p1-2-batch5-preservation.txt)。

跨平台报告中的 **28 项一致**为 RFC 8785 附录 B 的 24 项可编码 binary64 向量，加上规范化、候选投影、论断投影、Protocol 预览各一项。逐项保存 UTF-8 十六进制和完整 SHA-256，两侧一致。**2 项拒绝**为该附录向量的非法浮点输入，两侧均拒绝。独立期望来自附录原始输出和提交中的固定 `expected\\\\\\\_utf8`，测试过程未用待测投影生成期望。本轮独立核对了输入文件、依赖锁、记录字节与摘要，以及两个 Schema 摘要同现有产物一致。Schema 项比较的是两个组件包 SHA-256。Windows 75 项另覆盖本批 Scope、委派、旧记录和统一入口回归，签名适配器与完整运行服务未纳入 Windows 证据。[向量结果](../evidence/p1-2-batch5-cross-platform.json) · [Ubuntu 验证日志](../evidence/p1-2-batch5-verify.log)

[GitHub Actions 运行 43261216047](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43261216047) 由 workflow\_dispatch 触发，**Success**，用时 25 秒。运行 SHA 为 `4cbc58651fc88489d510201263b2538611ee0e76`。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43261216047/job/131332722045) 的锁定检查与构建成功。固定版本 `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` 有 Node.js 20 弃用警告，由 runner 用 Node.js 24 执行，Checkout 成功。

## 建议本批整改与复验

|发现|整改与复验要求|
|-|-|
|Scope 核心维度可被成对 not\_applicable 跳过|`scope.py` 的 \_dimension 将两个 not\_applicable 视为相容。探针将所有维度设为 not\_applicable，contains 和 overlaps 均返回 true。另一探针的采样 Scope 把抽样框和选择机制设为 not\_applicable，其他核心条件已知时，两份不同观察数据仍可比。按大方案 §5.5 定义各研究类型的必适用维度，拒绝不合法的 N/A 或返回 unknown；无法确定的适用性保持 unknown。补全 N/A、采样缺抽样依据、已知冲突与不同真实样本的组合反例|
|委派用途及目标范围未约束到请求解析|`authorize\\\\\\\_delegated\\\\\\\_request` 验证委派时核对用途、租约和时限，返回的 RequestContext 只保留租户、项目、主体、角色、任务种类。随后 `resolve\\\\\\\_reference\\\\\\\_query` 只校验引用可读及精确版本，未核对操作是否属于原委派用途及目标范围。探针使用用途 other-operation 的已验证委派，通过同项目的 references.resolve 查询另一目标。应在纯入口贯通预期操作、任务及精确目标范围，并明确每次调用的时效与租约事实。补同项目越范围、错用途及到期后重用已验证上下文的反例。真实身份和租约来源继续由下游服务验收|
|权威候选版本统一入口可静默返回重算值|`api.py` 对 CandidateRecord 直接调用 content\_version，探针输入错误的 stored content\_version 时返回不同的新摘要。ClaimRecord 分支会验证存储版本。应对 CandidateRecord 复用现有 `validate\\\\\\\_candidate\\\\\\\_version`，拒绝错版；草稿计算行为保留。补草稿计算、权威正确版本和旧版失败的分派测试|
|导出只列形状，无法识别运行时限制|`export\\\\\\\_schema.py` 的 x-r02-contracts 只列引用。调用方可见组件中也含服务持有和仅输出模型，缺少注册可用性、支持操作及运行时校验说明。ResponseEnvelope 的 status=ok、result\_ref=null 可通过结构 Schema，运行时拒绝。应在生成物标注调用方／服务／仅输出、首批支持与受阻能力，表达可导出的跨字段约束，其余明确要求调用运行时。补 JSON Schema/OpenAPI 元数据一致、禁止把权威模型当调用方入参、响应条件及未支持操作测试|

## 后续待办与验收边界

* Protocol 预览保留为准备入口，签发正式 ID 继续等待目标规范和可信解析。启用前补实际总体与 required\_items、观测单位、独立规则依据及引用就绪的正反例。Prereg、RunRequest、ExecutionBinding 完整投影继续跟踪。
* 历史标记清除权限待 A0，当前仍阻断。其他批准用途缺少已审定条款结构时继续阻断。旧缺项标记的可靠持久化和来源核验由实际读端口及迁移验收。
* TaskPlan、完整 ResearchTask、SanityReport、ContextManifest、角色输出等尚未注册。全量契约、服务端与调用端联验、完整投影和更多独立金样例仍属 P1-2 后续。真实身份、生产密钥、运行恢复、发布和科研评测按各阶段验收。
* Checkout 警告列为维护项。后续投影与 Schema 变更须重做跨平台向量对照。

本次审阅范围为第五批 R02 纯契约和所列验证证据。人工验收意见和结论由 A0 填写。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.13

意见：已审阅第五批交付及四项整改记录。Scope、委派查询守卫、权威候选版本一致性和 Schema 合同边界问题已整改。Ubuntu 208 项、Windows 83 项测试通过；Ubuntu 3.12.16 与 Windows 3.12.14 的 32 项规范字节及完整 SHA-256 一致，两个 Schema 摘要一致。整改 CI 对应提交 cd70f2091d16d1f31f83dad268d323176dc9e88c，运行成功，同意本批限定范围验收通过。

跨平台结论限于已验证的版本与测试范围。正式 Protocol ID、未经批准的科研映射、历史标记清除及缺少已审定条款的批准用途继续阻断；真实委派和租约来源留待服务验收。Checkout 运行时警告作为维护项跟踪，P1-2 整体验收仍按全部要求完成。

验收结论：通过（仅限 P1-2 第五批已交付及整改范围）

