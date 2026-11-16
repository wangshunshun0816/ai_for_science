# P1-2 A 组执行资格与准入子集验收记录

状态：A0（Jack_Wang）于 2026.11.16 签收通过，范围仅限 P1-2 A 组同项目、精确版本核验子集的已交付及整改内容。

## 交付与证据边界

交付提交 5b1f7f9ff8355c79796b260ac22561a79ea84c76。依据大方案 §5.1、§6.4、§9.1、§12.3，角色规格 §6.3–6.5，开发指南 §3.4／§5.3，以及已签收的同归属精确引用和委派规则。[字段依据与交付](../p1-2-execution-qualification.md)

[运行 43797949960](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43797949960) 最终为 Success，实际 SHA 为 4d20e183dcbc476d9bf2d90d440fd6362bb3c5e0，早于 A 组交付 5b1f7f9ff8355c79796b260ac22561a79ea84c76。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43797949960/job/133070987675) 的 Checkout、固定工具和 Python 安装、Locked local checks and build 均显示 success。任务页显示 Checkout 的 Node.js 20 弃用警告。详细步骤日志端点返回 HTTP 404，未取得单项输出、远端测试计数或制品。运行 SHA 的 Git 树不包含 A 组测试，本运行不计为 A 组 CI。A 组交付 SHA 在 WSL 按默认 pytest 配置收集到 30 项，本轮定向复跑 30 项通过。工作流未启用 DANUS\_P13\_TEST，SQLite 专项按开关跳过，本轮无新增存储验收证据。

原交付本地证据为 Ubuntu 474 项通过、18 项跳过和构建成功，Windows 同锁专项 30 项通过，四组规范字节与完整 SHA-256、两份 Schema 两侧一致。本轮重新执行 WSL 专项，未重跑全套或跨平台检查。

## 逐项复核及复验要求

|项目|现有覆盖与复现|待整改或验收边界|
|-|-|-|
|ModelProfile 与 ModelLineage|[姿态与精确版本匹配](../../../danus_ai/contracts/qualification.py#L194)比对配置定位、提示／工具和谱系。使用现有合成 Application，保留所有定位和有效事实，将 ModelProfile.task\_kinds 扩为 explore、unrelated，或同时把 ModelProfile.model\_version 与 ModelLineage.version 改成 v-unbound，计划和调用均接受。|**待整改。** 在现有精确定位之外提供独立权威版本正文依据，再逐个验证四类受限正文。复验范围扩写、成对改写、单侧不一致、缺独立版本依据和已知合法证据。完整谱系、回退、未知权重及凭证继续待决或服务验收。|
|RoleQualification|[版本比较](../../../danus_ai/contracts/qualification.py#L210)绑定角色、任务及模型、提示、工具、合同、上下文、代码和环境等精确版本。保持同修订，将 RoleQualification.report\_ref 替换为另一个已授权 EvaluationReport，两入口仍接受。|**待整改。** 可读性不能证明报告是该资格修订的权威正文内容。补同修订报告／评测集替换与受测目标错版回归。完整评测结果、阈值、限制、状态和启用批准继续待审或待服务验收。|
|ResourceAdmission|[资源匹配](../../../danus_ai/contracts/qualification.py#L216)核对资源版本、用途与许可定位。将同修订许可定位改为另一个已授权 License，两个入口仍接受。|**待整改。** 独立版本依据应绑定许可定位。现有函数只有只读核验结果，无资源授权副作用。许可条款、参与项目、权限、费用及计划需求到资源选择的映射仍受阻。|
|当前有效性和读取顺序|[授权与有效性检查](../../../danus_ai/contracts/qualification.py#L160)在正文端口前核对委派、可见性、精确引用、归属及当前 expires\_at／revoked。将资格设为撤销、谱系恰到期或移除准入目标，两个入口均拒绝且正文打开为零。|保持这些路径，补独立版本依据的读取顺序测试。真实端口如何获得现行事实、认证来源和确保不预读仍待服务验收。|
|入口适用范围|[计划](../../../danus_ai/contracts/planning.py#L383)将选择绑定到节点合同与当前资格。[调用](../../../danus_ai/contracts/execution_records.py#L335)绑定 R08 受信上下文及委派。声明版本化证据但缺读取端口会拒绝。|保留历史记录校验。待真实服务装配时，明确哪些操作必须提供 A 组证据，避免凭旧校验取得新能力。不能把四种类型的 I-SCHEMA 注册计为四行完成。|

## 同修订正文绑定整改复验

原复核发现及原运行证据保留。

授权、归属、精确引用以及当前期限和撤销先于版本快照及正文读取。独立受信端口 execution\_version 按精确定位提供四种完整版本快照，逐个核对类型、定位、修订及归属后，才通过 execution\_body 读取正文并比较全字段。版本快照须来自独立权威版本事实，端口不得从待检正文回填。缺快照、错版本或错归属阻断并保持正文读取为零。现有组件版本、用途及其他业务匹配继续单独复核。未新增科研投影、批准或授权条款。

整改前保留的四种替换在计划和调用共八个用例均未被拒绝，导致新增回归失败。整改后，同修订扩写任务范围、替换为其他已授权评测报告或许可依据，以及成对改写配置与谱系版本均在两条入口收到 EXECUTION\_QUALIFICATION\_VERSION\_BODY\_MISMATCH。精确新准入修订匹配独立快照且许可定位合法时，两个入口均通过只读检查。撤销、恰到期及委派范围外仍零次读取版本快照和正文。真实快照来源认证、权限适用性、资格签发及资源使用授权留服务验收。

Ubuntu CPython 3.12.16 专项 45 项、完整工程检查 489 项及 wheel／sdist 构建通过，18 项 SQLite 专项按开关跳过。Windows CPython 3.12.14 同锁专项 45 项通过。四组规范 UTF-8、完整 SHA-256、两份 Schema 与原交付一致；两端均逐字节核对现行生成物。[Ubuntu](../evidence/p1-2-execution-qualification-remediation-ubuntu.json) · [Windows](../evidence/p1-2-execution-qualification-remediation-windows.json) · [完整检查](../evidence/p1-2-execution-qualification-remediation-verify.log)。原九个金样例、手算及设计基线保留原字节，本轮无新增存储验收证据。

保留原发现及其证据提交 0789883f95a715c4e58940e20853bc8ab82609f9。CI 43797949960 只覆盖旧提交 4d20e183dcbc476d9bf2d90d440fd6362bb3c5e0，详细步骤日志返回 HTTP 404。整改 CI 与定向复核见下节。人工验收另行进行。

## 整改 CI 与本轮定向复核

[整改 CI 43800243706](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43800243706) 最终为 Success，实际 SHA 为 e72b082853a4fad109ce1b762447a3e3f73c9f9b。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43800243706/job/133078494624) 的 Checkout、固定工具安装、固定 Python 安装及 Locked local checks and build 均显示 success。任务页有 Checkout 的 Node.js 20 弃用警告。详细步骤日志端点返回 HTTP 404，未取得各子命令输出、远端测试数量或构建产物。证据限运行摘要、任务步骤结论及相应提交的工作流和验证脚本。

该提交默认执行 pytest -q，本轮用相同默认配置在 WSL 确认收集执行资格专项 45 项。CI 未启用 DANUS\_P13\_TEST，SQLite 专项按开关跳过，本轮无新增存储验收证据。远端单项用例结果未独立核验。原 WSL 完整检查 489 项通过、18 项 SQLite 跳过及两端各 45 项专项通过仍属既有本地证据。

本轮在 WSL 定向复跑 22 项通过、23 项未选中。八个同修订正文替换用例在计划与调用两个入口均拒绝，独立绑定的合法新修订在两入口通过，撤销、恰到期及委派范围外均断言快照／正文读取次数为零。缺、错修订或错归属的独立快照使正文读取次数为零。真实权威快照来源认证、资格签发和资源使用授权继续留服务验收。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.16

意见：同意 P1-2 A 组同项目、精确版本核验子集的已交付及整改内容通过验收。范围包括四类合同的已定子集、计划与调用入口的精确绑定、独立权威版本快照与正文一致性核验，以及撤销、到期和越权时的读取前拒绝。认可记录中限定的本地及跨平台证据；远端 CI 成功，但详细日志、单项远端结果和计数未取得，SQLite 专项未执行。真实快照来源认证、资格签发、任务启用、资源使用授权及未交付的完整合同继续待验收。本次签收不代表 A 组全部要求或 P1-2／P1-3 整体通过。

验收结论：通过，仅限 P1-2 A 组同项目、精确版本核验子集的已交付及整改内容，明确保留的缺项和待决能力除外。

