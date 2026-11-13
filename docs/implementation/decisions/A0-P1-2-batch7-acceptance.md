# P1-2 第七批人工验收记录

状态：A0 于 2026-11-13 整改复验通过，范围仅限 P1-2 第七批已交付及整改内容。

## 1\. 依据与实际交付

已核对第七批授权、AGENTS.md、开发指南 §3.4／§5.3、大方案 §5.1–5.3、§6.4、§6.21、§6.25 及附录 A，角色规格 §3.2–3.4、§4、§5.1／§5.3。沿用首组批准 §5–6 及其绑定提案 `48bd0dcc0afa78c2b6447fdfe789465b0d3a8068` 的归属和版本边界，以及 [Q-06 等签收决定](A0-P1-2-Q04-Q07-checklist.md)。基线为[第六批限定签收](A0-P1-2-batch6-acceptance.md) `8e4116041114c1954c2209cbf689f6eb6d66eb84`。

|路径|实际交付|
|-|-|
|任务与计划|初始草稿不接受权威字段；执行状态要求活动快照。计划校验 NFC 节点唯一性、重复／悬空依赖和环，按受信根任务、活动版本、精确任务合同、资格引用及根预算校验可行性。|
|上下文|清单绑定任务、计划、授权视图和构建策略。对已纳入项及其直接来源核对可见性和精确版本，核对输入估计及预留，要求关键引用保留；恢复要求 prior\_context\_ref，新审计顶层禁止该字段。|
|输出与接收|七角色判别联合、既有业务草稿、严格拒绝额外权威字段。接收检查角色、任务种类、租约定位、当前交接记录、活动计划定位、收发合同、嵌套引用及工件／反馈白名单。|
|I-SCHEMA|同一注册表生成 JSON Schema 与 OpenAPI，区分调用方和服务记录，列出独立运行时守卫；第七批没有新增科研内容 ID。|

## 2\. 同步、CI 与本地证据

* Ubuntu HEAD、GitHub main 均为 `ec8fb7b7956617d29cdbc9d9c758f649748c20d9`。该证据提交直接接续 `e5188d22d0c47e5845d1b5ea853dba98535134ba`，仅更新 `commit\_log.md` 和[交付记录](../p1-2-batch7-delivery.md)，3 行新增、2 行删除。
* [CI 43351115237](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43351115237)经 GitHub API 复核为 main 手动触发、completed / success，实际 SHA `e5188d22d0c47e5845d1b5ea853dba98535134ba`，开始至完成更新 28 秒。[foundation](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43351115237/job/131642134859) 锁定安装、检查及构建均成功。Checkout 成功，唯一警告为固定 actions/checkout 所用 Node.js 20 弃用，runner 改用 Node.js 24。
* 原交付 Ubuntu CPython 3.12.16 完整工程检查 253 项通过，Windows 原生 CPython 3.12.14 本批 24 项通过。本轮 Ubuntu 以 `PYTHONPATH=. .venv/bin/python -B -m pytest -q -p no:cacheprovider` 复跑 **253 passed**，生成 Schema 检查通过。Windows 使用既有交付证据。
* 比对 [Ubuntu](../evidence/p1-2-batch7-ubuntu.json) 和 [Windows](../evidence/p1-2-batch7-windows.json) 结果，3 份规范 UTF-8 字节及完整 SHA-256 一致，计划 8 项、上下文 7 项拒绝一致，2 份 Schema 摘要与当前生成物一致。本轮从原始字节复算摘要。预期由测试手列计划及探索输出字段、显式 NFC／换行字面量，以标准库独立编码。原九个金样例和手算目录相对 `412e67e` 无差异。

## 3\. 本批整改及复验要求

以下复现均可从 `tests/contracts/test\_batch7.py` 的独立 `Chain()` 和 `NOW` 开始。更改的事实由现有合成端口返回；涉及错误事实的用例验证纯守卫是否具备独立交叉检查，不表示真实服务已经部署或发生越权。

|发现与位置|可复现输入与结果|依据与整改要求|
|-|-|-|
|草稿可携带活动快照，修订可缺授权定位。[planning.py](../../../danus_ai/contracts/planning.py#L42)、[PlanRevision](../../../danus_ai/contracts/planning.py#L127)|用合法任务和计划定位构造 status=draft 的 TaskSnapshot，将其放入同为 draft 的 ResearchTask，解析成功。以原计划为父版本构造修订 2，authorization\_refs=\[] 也成功。DAG 本身能拒绝环、重复和悬空依赖。|大方案 §5.1／§5.3／§6.25、附录 A、Q-06。分清未激活草稿、已激活快照与取消记录。将纯提案／未授权版本与受信有效修订区分；声明有效的修订应核对所需授权定位和活动父版本。补对应的运行时及导出测试。|
|计划校验缺显式服务主体检查。[planning.py](../../../danus_ai/contracts/planning.py#L206)、[validate\_plan](../../../danus_ai/contracts/planning.py#L266)|原合成 reader 对请求操作返回匹配 AccessFact。调用 validate\_plan(c.plan, c.a2, c.reader, now=NOW) 成功，尽管调用者是 A2 且上下文任务为 sender。|大方案 §6.25 与附录 A 将 validate/activate 交可信服务，角色可提交提案。现有 operation、租约和引用检查可保留，另用可独立核验的服务操作主体／用途与根任务绑定区分提案者和校验者。补角色持有同名操作授权但无服务资格时拒绝的反例。|
|交接没有检查当前根预算事实，授权定位可与当次授权不同。[role\_outputs.py](../../../danus_ai/contracts/role_outputs.py#L263)、[planning.py](../../../danus_ai/contracts/planning.py#L206)|设 c.reader.current\_budget=None，accept\_handoff 仍成功。让 reader.access 返回可用、目标相同但 delegation\_ref 为 different-grant 的 AccessFact，保留 Handoff.authorization\_ref 为 grant，仍成功。|角色规格 §5.1、§5.3 TC-PLAN-03，大方案 §6.25。按当前接收操作核对授权绑定，以及同根任务、同项目的预算与继承记录。区分历史归档可读和授权接收；缺预算、错根、错授权应阻断接收。预占、实际额度支出与对账由对应服务负责。|
|交接根任务、计划节点与路由仍由合并布尔值背书。[role\_outputs.py](../../../danus_ai/contracts/role_outputs.py#L216)、[accept\_handoff](../../../danus_ai/contracts/role_outputs.py#L280)|将 root\_task\_ref 换成同项目已授权的 sender、target\_node\_ref 换成 source\_node\_ref，并将 current 设为此记录；活动 plan\_ref 和 route\_and\_approvals\_current=True 保持。接收成功。|角色规格 §5.1 明确绑定根、活动计划／节点版本及 A8 重授权。用受信的当前任务／节点映射核对收发任务归属、节点身份和精确版本、输出与接收合同以及必需批准；缺映射或错根、错节点时阻断。|
|A7 冷启动可通过来源重新带入旧上下文。[context.py](../../../danus_ai/contracts/context.py#L59)、[validate\_context](../../../danus_ai/contracts/context.py#L100)|用 new\_audit 且 prior\_context\_ref=None，把一个允许读取的旧 ContextManifest 放进 authority 输入的 sources，并将 verified\_inputs 同步为该列表。A7 校验通过。普通恢复已有授权、到期、容量和关键约束守卫。|角色规格 §3.3、§4.6、TC-MEM-02/03。新审计需要独立审计任务与冷启动包依据，逐条检查来源及摘要谱系，拒绝混入旧会话或旧审计上下文；恢复仅允许匹配同一次任务／审计的前序材料，失效后从权威重新构建。|
|引用白名单不能约束交接中的任意自由文本。[role\_outputs.py](../../../danus_ai/contracts/role_outputs.py#L159)、[接收守卫](../../../danus_ai/contracts/role_outputs.py#L317)|在原交接的 completed 中加入 `same-family confirmation labels: q1=1`，allowed\_feedback\_refs 保持空，端口返回该当前记录，接收成功。结构化自报 approved 会被拒绝。|角色规格 §5.1、TC-A4-06、TC-MEM-03。接收应消费绑定接收方、用途和版本的受信过滤视图，任意模型文本需经视图审核或隔离后才可转交。补文本及嵌套输出夹带与允许中性摘要反例；实际敏感内容识别及语义注入评测留待下游。|
|A7 输出能同时声明未发现阻断及列出阻断项。[role\_outputs.py](../../../danus_ai/contracts/role_outputs.py#L101)|用 A7 output，outcome=no\_blocking\_issue\_found，issues 含 code=G0、severity=blocking 和有效材料引用。RoleOutputEnvelope 解析成功。|角色规格 §4.6、TC-A7-03。把可判定的严重度与结论关系编码到合同，矛盾输入退回；缺结构化严重度映射时保持待定且阻断推导“通过”。补合法非阻断发现、有效补证、阻断及服务错误。|
|Schema 和跨平台证据缺关键反例的端到端对照。[api.py](../../../danus_ai/contracts/api.py#L295)、[tests](../../../tests/contracts/test_batch7.py#L503)|导出 ResearchTask 仅有字段与类型，status=executing 加 active\_snapshot=null 的结构能通过字段规则，运行时返回 TASK\_SNAPSHOT\_REQUIRED。现有七角色测试主要做形状和禁止字段，完整发送／接收链只覆盖 A2→A4。三份独立向量为计划、A2 输出和草稿 NFC／换行，未覆盖 ContextManifest 或 Handoff 的预期字节。|R02 §3.4、P1-2 §5.3、大方案 §6.4。导出可表达的任务状态条件，明确活动版本、DAG 和接收权限仍需运行时守卫。让调用端与接收端使用同一生成合同并执行上述反例；补独立 ContextManifest 和 Handoff 字节向量、错合同版本、根预算与冷启动来源等两侧对照。|

## 4\. 后续待办与验收边界

本批纯契约整改可验证权威事实缺失时阻断、定位和版本一致及角色隔离。生产 task\_kind 启用和实际角色资格、派生上限与上下文容量配置、实际租约／权限和预算来源、文本过滤、仓储、调度、原子 CAS、恢复执行及模型调用按对应工作包验收。完整 ClaimSubmission、EvidenceSnapshot、数值宏、Sanity 请求／报告与其余 R02 对象仍需对应合同及权威提供方。未审定的科研／权限规则继续按既有决定处理。

## 5\. 整改与复验

整改前固定八个失败回归。整改后，草稿和快照、计划主体与授权、接收根预算和当前委派、计划节点与用途、A7 来源冷启动、反馈谱系、精确审阅视图和审计结论已按合成端口复验。具体设计依据和处置见[交付记录](../p1-2-batch7-delivery.md#验收整改)。原审查发现保留供复核。真实权限及内容审核服务、仓储、调度与原子 CAS 按原边界验收。

Ubuntu 267 项通过，Windows 第七批 38 项通过。两侧 5 份独立规范字节和完整摘要、15 个原计划／上下文拒绝、两份 Schema 摘要一致；包含新增 ContextManifest 和 Handoff 向量。原九个金样例和手算记录无字节差异。

GitHub Actions [整改运行 43354232528](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43354232528) 在 `main` 手动触发，结果为 **Success**。实际运行 SHA 为 `89c25da8cd9efe50e0509912ce3b06efd6ac26bf`，与第七批整改提交一致。从运行开始到完成更新用时 24 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43354232528/job/131652295785)的锁定检查和构建通过。Checkout 成功，唯一警告是固定的 `actions/checkout` 使用已弃用的 Node.js 20，runner 改用 Node.js 24 执行。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.13

意见：已审阅第七批交付及整改记录。任务与计划、交接授权、A7 冷启动、角色输出一致性及 Schema／验证覆盖问题已有回归复验。Ubuntu 267 项、Windows 38 项测试通过，两侧已执行的独立规范字节、摘要和拒绝结果一致。整改 CI 对应提交 89c25da8cd9efe50e0509912ce3b06efd6ac26bf，运行成功，同意本批限定范围验收通过。

本次签收限于 R02 纯契约及合成端口验证。真实权限、预算和内容审核服务、调度、仓储、原子 CAS、模型调用及其余契约缺项继续按对应阶段验收。跨平台结论限于实际测试版本与向量，Checkout 运行时警告保留为维护项。

验收结论：通过（仅限 P1-2 第七批已交付及整改范围）

