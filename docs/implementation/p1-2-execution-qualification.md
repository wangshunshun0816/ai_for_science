# P1-2 A 组版本化执行证据核验

依据大方案 §5.1、§6.4、§9.1、§12.3，角色规格 §6.3–6.5，开发指南 §3.4／§5.3，以及已经签收的同归属精确引用与委派规则。该子集只核验受信服务已提供的事实，真实配置批准、资格签发、能力启用和资源授权仍另行验收。字段台账的提案行没有被提升为批准。

## 字段依据与限制

下表字段均为本子集必填且非空值，无业务缺省。列表保留顺序，本子集的工具列表做全列表精确比较，允许显式无工具；空用途或任务范围列表不匹配任何申请。归属字段由服务写入，只接受当前租户下同项目证据。精确科学定位使用类型、对象 ID 和内容版本，受信业务记录定位使用类型、记录 ID 和修订。未引入科学投影、内容 ID 规则或授权用途。现有引用目标规范无法确认时，由引用守卫拒绝。

| 出口行 | 本次使用的字段、依据与权威写入方 | 仍受阻范围与原因 |
|---|---|---|
| ModelProfile | A §5.1／§9.1，A0 批准的模型配置管理。ref 为既有 ModelProfile 精确科学定位，tenant_id／project_id 由服务写入，provider／base_model／model_version 对照谱系事实，prompt_ref 和 tools 精确绑定版本，task_kinds 只消费服务已有适用范围。 | 评测／回退配置完整结构，凭证、数据约束、参数和上下文限额的目标规范仍待补。回退启用、授权及跨项目使用仍待审。版本文本仅用于对照来源给定的版本，API 权重未知的披露和真实可复现性另行验收。 |
| ModelLineage | A §6.4／§9.1、角色规格 §4.6，模型配置管理。locator 为记录精确修订，tenant_id／project_id 由服务写入，model_profile_ref 为精确配置定位，provider／base_model／version 复核与配置一致。 | 作者／评审模型谱系全集、独立性判断及未知权重的通用合同未覆盖。 |
| RoleQualification | A §5.1／§9.1、角色规格 §6.4–6.5。R22 写入 locator、tenant_id／project_id、role、task_kind、evaluation_set_ref、report_ref 及受测版本集合。集合包括精确 model_profile_ref、prompt_ref、tools、contract_ref、context_ref、code_ref 和 environment_ref。角色与任务类型同计划节点和受信调用上下文匹配。 | 通用费用、限制、状态转换、质量阈值、能力启用与回滚批准条款未定。本次仅查评测集和报告的精确可读定位，尚未重算评测结果，未签发资格。 |
| ResourceAdmission | A §6.4／§12.3，R00 资源准入事实的只读投影，生产写入责任待落实。locator、tenant_id／project_id 为受信定位及归属，resource_ref 固定资源精确版本，source 记录来源，license_ref 绑定可查的精确许可依据，allowed_uses 与当前用途匹配。 | 许可条款、目的地和权限、费用和撤销的完整持久化、资源需求文本到权威资源选择的映射及真实可用性未定。用途匹配无法提供资源用权，缺已审定授权时保持阻断。 |
| 实际契约入口 | 服务从 PlanFacts.node_execution 为节点提供证据组合，在 validate_plan 校验节点合同、现行资格和申请；调用由 R08 ExecutionFact 带同样组合、精确上下文和委派定位，在 check_invocation_record 复核。组合中的定位为模型／提示／工具／合同／上下文／代码／环境、谱系、资格、准入和资源。生命周期由受信端口按精确定位提供 expires_at、revoked 和归属事实。 | 既有结构／历史调用记录校验仍可独立使用。服务声明有版本化证据时，缺读取端口或缺节点选择则拒绝。两条入口检查均无启用或执行副作用。 |

先用既有访问守卫匹配委派、当前租约、用途、可见性及精确引用，再访问证据正文。四个新根合同仅在受信服务入口解析。评测集、报告与许可依据会核验精确定位和访问，其正文由后续服务负责。证据事实的来源认证和持久化版本不可变保证仍由适配器验收。对工具和模型定位相同摘要的替换继续做精确身份校验。

## 验证

同一个合成申请通过计划与调用入口。反例覆盖错角色／任务、模型或工具版本、归属、资源／用途、过期、撤销、缺证据、摘要相同但定位替换，以及委派越权。权限、过期、撤销和定位等元数据拒绝路径断言正文读取次数为零。合成端口不代表真实审批资格或授权。

四种根合同的独立 [UTF-8 和 SHA-256 向量](../../tests/fixtures/qualification/approved-subset.json)由手列 wire 字段经标准库紧凑排序编码及摘要工具计算，测试只比较实测字节与固定预期。[专项测试](../../tests/contracts/test_execution_qualification.py)还核对两份 Schema 生成物。两端均使用仓库依赖锁。

已有原九个金样例、手算与设计基线保留原字节。该工作包只关闭出口台账同行的上述已定核验子集，资格阈值、审批、跨项目权限和真实资源接入继续待审或待服务验收。P1-2 和 P1-3 整体尚待验收。

- Ubuntu CPython 3.12.16 完整工程检查 474 项通过、18 项隔离 SQLite 测试跳过，Ruff、mypy、导入边界、Schema 及 sdist/wheel 构建通过。未建库。[完整日志](evidence/p1-2-execution-qualification-verify.log)
- Windows CPython 3.12.14 同锁专项 30 项通过。双方四组规范 UTF-8 字节及完整 SHA-256 一致，两份 Schema 各自与仓库生成物逐字节一致。[Ubuntu](evidence/p1-2-execution-qualification-ubuntu.json) · [Windows](evidence/p1-2-execution-qualification-windows.json)
- 对应工程 CI 待核验，本轮复核见下节。

## 远端运行核对与独立复核

[运行 43797949960](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43797949960) 最终为 Success，实际 SHA 为 4d20e183dcbc476d9bf2d90d440fd6362bb3c5e0，早于 A 组交付 5b1f7f9ff8355c79796b260ac22561a79ea84c76。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43797949960/job/133070987675) 的 Checkout、固定工具和 Python 安装、Locked local checks and build 均显示 success。任务页显示 Checkout 的 Node.js 20 弃用警告。详细步骤日志端点返回 HTTP 404，未取得单项输出、远端测试计数或制品。运行 SHA 的 Git 树不包含 A 组测试，本运行不计为 A 组 CI。A 组交付 SHA 在 WSL 按默认 pytest 配置收集到 30 项，本轮定向复跑 30 项通过。工作流未启用 DANUS_P13_TEST，SQLite 专项按开关跳过，本轮无新增存储验收证据。

两入口合成复核在保持证据定位、归属、期限与可见性不变时，均接受了同版本扩写模型配置的任务范围、将资格报告或许可依据换成另一个可读精确引用、以及配置与谱系同时把版本值改为 v-unbound。当前元数据没有独立的正文绑定。撤销、恰到期及不在委派目标内三项反例在计划和调用入口均拒绝，正文打开次数为零。详见未跟踪验收草稿，A 组对应 SHA 的远端 CI 仍待核验。

## 同修订正文绑定整改

授权、归属、精确引用以及当前期限和撤销先于版本快照及正文读取。独立受信端口 execution_version 按精确定位提供四种完整版本快照，逐个核对类型、定位、修订及归属后，才通过 execution_body 读取正文并比较全字段。版本快照须来自独立权威版本事实，端口不得从待检正文回填。缺快照、错版本或错归属阻断并保持正文读取为零。现有组件版本、用途及其他业务匹配继续单独复核。未新增科研投影、批准或授权条款。

整改前保留的四种替换在计划和调用共八个用例均未被拒绝，导致新增回归失败。整改后，同修订扩写任务范围、替换为其他已授权评测报告或许可依据，以及成对改写配置与谱系版本均在两条入口收到 EXECUTION_QUALIFICATION_VERSION_BODY_MISMATCH。精确新准入修订匹配独立快照且许可定位合法时，两个入口均通过只读检查。撤销、恰到期及委派范围外仍零次读取版本快照和正文。真实快照来源认证、权限适用性、资格签发及资源使用授权留服务验收。

Ubuntu CPython 3.12.16 专项 45 项、完整工程检查 489 项及 wheel／sdist 构建通过，18 项 SQLite 专项按开关跳过。Windows CPython 3.12.14 同锁专项 45 项通过。四组规范 UTF-8、完整 SHA-256、两份 Schema 与原交付一致；两端均逐字节核对现行生成物。[Ubuntu](evidence/p1-2-execution-qualification-remediation-ubuntu.json) · [Windows](evidence/p1-2-execution-qualification-remediation-windows.json) · [完整检查](evidence/p1-2-execution-qualification-remediation-verify.log)。原九个金样例、手算及设计基线保留原字节，本轮无新增存储验收证据。

保留原发现及其证据提交 0789883f95a715c4e58940e20853bc8ab82609f9。CI 43797949960 只覆盖旧提交 4d20e183dcbc476d9bf2d90d440fd6362bb3c5e0，详细步骤日志返回 HTTP 404。整改 CI 及本轮复核见下节。人工验收另行进行。

## 整改 CI 与本轮定向复核

[整改 CI 43800243706](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43800243706) 最终为 Success，实际 SHA 为 e72b082853a4fad109ce1b762447a3e3f73c9f9b。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43800243706/job/133078494624) 的 Checkout、固定工具安装、固定 Python 安装及 Locked local checks and build 均显示 success。任务页有 Checkout 的 Node.js 20 弃用警告。详细步骤日志端点返回 HTTP 404，未取得各子命令输出、远端测试数量或构建产物。证据限运行摘要、任务步骤结论及相应提交的工作流和验证脚本。

该提交默认执行 pytest -q，本轮用相同默认配置在 WSL 确认收集执行资格专项 45 项。CI 未启用 DANUS_P13_TEST，SQLite 专项按开关跳过，本轮无新增存储验收证据。远端单项用例结果未独立核验。原 WSL 完整检查 489 项通过、18 项 SQLite 跳过及两端各 45 项专项通过仍属既有本地证据。

本轮在 WSL 定向复跑 22 项通过、23 项未选中。八个同修订正文替换用例在计划与调用两个入口均拒绝，独立绑定的合法新修订在两入口通过，撤销、恰到期及委派范围外均断言快照／正文读取次数为零。缺、错修订或错归属的独立快照使正文读取次数为零。真实权威快照来源认证、资格签发和资源使用授权继续留服务验收。
