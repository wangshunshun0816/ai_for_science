# P1-2 第三批交付：批准范围内的首组契约

日期：2026-11-12。工程结果仅限本批；不代表 P1-2、R02 或 P0 整体验收通过。

## 1. 批准与起点

仓库：`/home/wangshunshun/danus-ai`。开工前工作区干净，本地 HEAD、origin/main 及 `git ls-remote origin refs/heads/main` 均为 `1f34e0d611066acd7273a9c0843e5c93514ecd14`。
已读 AGENTS.md。依据该提交 [A0 决策清单](decisions/A0-R02-first-contracts-checklist.md) §5 本人签收（Jack_Wang，2026.11.12）及 §6 实施授权，绑定提案 **48bd0dcc0afa78c2b6447fdfe789465b0d3a8068** 的 [首组契约提案](r02-first-contracts-proposal.md)。P1/P3/P4/P5 推荐方案、P2 固定枚举首包有效；未启用采样或描述型分支。
清单顶部及末尾仍有签收前的叙述，实际授权依据 §5 已填签收；本批不代改人工签收记录或据旧叙述扩大授权。

## 2. 文件、入口与设计追溯

|文件/入口|已实现|绑定提案出处与限制|
|---|---|---|
|`danus_ai/contracts/references.py`|ScientificRef/HistoricalRef、RecordLocator/ApprovalLocator、PublicRef 分型；UTC/精确小数；来源位置、科学限制、停止字段、方法配置、规范集合工具|§1.1、2、4、6；历史实体 ID 保留，普通科学引用排除工作记录定位；公共准入只有形状，没有真实准入服务|
|`danus_ai/contracts/first_objects.py`|CandidateDraft/Record、ProtocolDraft/Record、PreregDraft/Record；严格必填/null/类型、未知字段拒绝、草稿禁权威字段、来源分支、参数范围、固定枚举适用分支、批准条款一致性|§1.1/1.2、5、6.1–6.3；模型解析成功只说明形状合法，非批准有效或状态转换合法|
|`danus_ai/contracts/runs.py`|RunRequestDraft/Record 八模式字段矩阵、独立 ExecutionBinding、科学配置与预算引用分离|§1.2、3/3.1、4；无 RunRequest.status、attempt_id、scientific_validity；绑定拒绝指回运行/报告|
|`danus_ai/contracts/projections.py`|candidate_projection、content_version、validate_candidate_version；method_projection、validate_method_consistency|§1.2 Candidate、2、4、6；候选仅在只读端口逐个确认所有目标可访问且规范就绪后计算 candidate:v1:SHA256，既有记录可另行复算比对；不自动修复旧版本|
|`danus_ai/contracts/guards.py`|只读引用/批准/任务/预算端口；require_reference/approval/budget；validate_mode_preconditions、validate_prereg_approval_bindings|§2、3、5；精确目标/版本/修订、归属、用途、撤销/失效、科研条款比对；P5 分支来自受信任务合同并绑定主体，非客户端开关|
|`tests/contracts/test_first_batch.py`|本批合成夹具与正反例；接入既有 pytest/verify.sh 入口|文件名 first_batch 指首组四对象；不替换 P0-2 原金样例|

继续复用原 StrictContract、严格 JSON 解析（重复键/非有限数值拒绝）和 canonicalization（NFC、CRLF→LF、精确小数、RFC 8785 JCS）。没有新增依赖；uv.lock 与 pyproject.toml 不变。运行依赖沿用已批准 pydantic、rfc8785 及锁定传递依赖。

集合工具按规范化后 JCS 字节排序去重。候选 sources 科学投影排除工作记录定位，但**在去重前逐个核对所有原始引用权限**；相同内容不意味着相同授权。arms 保留列表顺序；具名参数/arm ID 规范化后重复均拒绝（包括完全重复条目），避免歧义；这比一般无键集合去重更严格，符合绑定表 name/arm_id 唯一要求。其他对象尚无完整投影，不能把未排序的普通 model_dump 当正式科研序列化。

## 3. 科学、权限与受阻边界

- **候选**：明确白名单投影；科学内容及来源位置变化影响版本，身份、状态、注释、批准定位不入投影。版本计算是纯函数，不分配记录 ID、不写权威存储。本次只在合成测试中计算摘要，没有为真实科研对象发放 ID。真实 Scope/SourceSnapshot 的可用性必须由可信适配器核验，不能把测试中的 specification_ready 当实际规范材料。
- **方法与预算**：科学限额仅在 MethodConfig.science_limits，停止条件仅在 Prereg/任务计划；拒绝额外字段或保留参数名覆盖。已实现与受信锁定方法配置的精确比较。纯预算使用 R07 只读视图核验用途/币种/额度/有效性；预算绑定仅存引用。改变科学限额会改变方法规范字节，改变纯预算不会改变科学配置，但仍可能被额度检查拒绝。没有消耗或预留额度。
- **批准**：只读端口验证候选选择/阈值批准及解析后的条款，拒绝错目标/版本/撤销/过期/跨归属/自改条款。通用 require_approval 支持指定目的。它不校验 Q05 签名，不生成 lock 或 run_authorize，也不增加逐 run 人工签字。当前形状允许解析状态字段，但未实现 Q06 转换服务。
- **模式**：八模式形状和已批准角色矩阵、受信 task_kind 前置、锁定计划/arm 对照、复现索引注册及引用可见性已实现；完整委派、数据切分授权、sanity 有效性、锁定事实仍依赖真实服务。require_runtime_ready 明确抛出 SPEC_UNRESOLVED；局部检查成功不等于可运行。
- **Protocol**：duplicate_policy 仅保留明确输入的建议文本，无默认；即使解析为 Record/approved 形状，也不能据此认为 Q07 已批准。完整投影/版本计算始终拒绝，待 Q07、MissingPolicy/SelectionRule 等实际目标规范。
- **Prereg**：固定枚举形状及批准条款分离可用；历史实体规则不代替完整历史摘要。版本计算/正式锁定继续受 Q04、Q05、Q06、Q07 及 FailurePolicy/RetryPolicy/FeedbackPolicy 等目标内容阻塞。
- **RunRequest/ExecutionBinding**：依赖的真实摘要与科学/审计划分、授权回执、任务/校准/准入目标缺失；完整版本计算和正式准入继续阻塞。ExecutionBinding 只实现无环形状，未冻结其内容 ID。
- **保守子集**：固定枚举 Prereg 本批仅支持 randomness/discrimination 明确不适用分支；不对未知方法自动推定适用性。预算估价仅支持 planning_estimate + basis_ref 的明确建议形状，其他 NumericValue 性质未实现，不能假作实测值。完整目标类型注册、跨对象科学一致性（如任务停止/数据 item 全量对应）、公共授权解析及所有真实服务验收仍待目标规范和适配器。
- Q04–Q07 不关闭，采样/描述型不启用。Windows CPython 3.12 与 Windows/Linux 一致性继续待办；未安装 Windows 解释器、未宣称跨平台通过。

## 4. 实际验证与期望值来源

Ubuntu CPython **3.12.16**，uv **0.13.7**。2026-11-12 运行：
```bash
bash scripts/verify.sh > /tmp/danus-p1-2-batch3.log 2>&1
```
完整输出保存于 [本批本地检查日志](evidence/p1-2-batch3-verify.log)。

|检查|实际结果|
|---|---|
|uv lock --check；锁定同步及非 editable 重装|通过；锁文件未改|
|ruff check / format --check|通过，16 files already formatted|
|mypy|通过，15 source files|
|导入边界及受控违规导入反例|通过（既有入口）|
|pytest|**160 passed in 0.90s**；此前 122 项，本批新增 38 个测试实例|
|源码包及 wheel 构建|成功|
|原九个 JSON、手算 README 及三份设计基线字节比对|见 [保留文件核对](evidence/p1-2-batch3-preservation.txt)，对批准提交逐文件比对相等|

本批修复了开发过程中的静态类型/格式问题后完成上述最终运行。未用失败的中间结果充当证据。

期望值来自绑定提案字段/模式表、A0 §5 限定决定及既有 RFC 独立规范化向量。新增候选测试使用**手写固定规范字节**与独立 hashlib 摘要对照，不以被测投影生成期望值。其余测试依据明确规则断言：逐字段缺失/权威注入、UTC/非法类型、来源分支、集合/历史实体区别、字段改动与旧版本拒绝、非法身份/归属、错版本/撤销批准、条款自改、预算变化、方法限制冲突、八模式及循环引用。MemoryPort 是合成只读替身，其 approved/readable/specification_ready 均不是实际人员资格或规范验收证据。原九个金样例及手算不改写、不重新解释为正式 ID。

## 5. 同步与 CI

开工已用远端 refs 确认批准提交同步。提交前认证预检 `GIT_TERMINAL_PROMPT=0 git push --dry-run origin main` 失败：
```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```
本批代码提交为 a4d0553233c62613afb90cb0202618d01f5e5dd9。首次实际推送同样失败；随后发现 Windows 已有 Git Credential Manager，Ubuntu 未配置 credential.helper。通过以下命令级配置调用现有凭据后推送成功，git ls-remote 确认远端 main 为该提交。未读取/输出令牌，未更改仓库身份或凭据配置。

```bash
GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never git -c credential.helper= -c credential.helper=/mnt/d/Git/mingw64/bin/git-credential-manager.exe push origin main
```

2026-11-12，用户在 main 手动触发 `P1-1 foundation checks`（`workflow_dispatch`）。[运行 43184083094](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43184083094) 已结束，结论为 **Success**，总用时 21 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43184083094/job/131066858494) 成功，其中 `Locked local checks and build` 步骤成功。

GitHub 运行页所示实际提交为 `86aeac09bfe9e36ef3dac272ff9f09ea8e6ac8a2`。本地通过 `git merge-base --is-ancestor` 确认它包含第三批代码提交 `a4d0553233c62613afb90cb0202618d01f5e5dd9`。两者的差异仅涉及本交付记录及提交日志，运行覆盖第三批交付代码和既有工作流。

GitHub 注释记录了 Node.js 20 弃用警告。固定版本的 `actions/checkout` 由 runner 强制在 Node.js 24 上执行，任务结果为成功。

本批工程验收仅限上述已实现纯契约及本地检查；真实服务、跨平台、R02 全部验收及人工签收另行处理。

## 6. 第三批人工验收整改

依据 A0 在 `1f34e0d611066acd7273a9c0843e5c93514ecd14` 的签收和绑定提案 `48bd0dcc0afa78c2b6447fdfe789465b0d3a8068`。复验基线为 `938f7dcaf953be57e99cafc79cd3fc725c4ddd38`。

| 处置 | 字段与批准规则 | 整改前影响及当前结果 |
| --- | --- | --- |
| 已整改 | `RecordMetadata.approval_bindings`，提案 §1.1 按 purpose、record_id、revision 精确去重 | 原先保留完全相同的绑定。现由四对象共用字段校验保留每个精确三元组的首次出现，不同记录、修订和用途各自保留。测试覆盖完全相同、不同修订及同记录同修订不同用途。只读批准核验仍拒绝用途与权威记录不符的请求 |
| 已整改 | `CandidateFields.original_source` 与 `sources`，提案 §6.1 | 原先要求 external_reported 和外部 synthetic_design 均将原始来源列入 sources，导致后者无背景来源时被拒。现只对 external_reported 要求包含该源位置。外部 synthetic_design 仍须提供有位置的 original_source，且该引用独立参与投影和访问检查。回归测试验证允许空 sources 及拒绝不可访问的原始来源 |
| 已整改 | `PreregFields.arms`，提案 §1.2 和 §6.2 规定有序及同键异值冲突 | 原先同一 arm_id 一律拒绝。现保留完全相同条目及原序，拒绝规范化后同一 ID 内容不同的条目。固定比较仍需 reference 和 candidate 两类臂。回归测试覆盖这三种情况 |
| 保留限制 | `MethodConfig.parameters[].name` 与 `ProtocolFields.tuning_space[].name`，提案 §4 和 §1.2 明确名称唯一，§4 明确保留名和重复参数冲突 | 继续拒绝完全相同及内容不同的同名方法参数，继续拒绝重复的调参名称和科学限额覆盖。一般集合去重规则不取消这两处字段约束 |
| 已批准延期 | 完整投影和版本计算、目标规范依赖的跨对象停止条件、实际审批／公共准入／运行服务 | 仍按 §3 和 A0 清单 §6 跟踪。固定枚举 Prereg 的 randomness/discrimination 仅支持明确不适用形状，其他适用分支缺方法和目标规范。预算估价仅实现 planning_estimate，其他 NumericValue 性质与依据结构尚缺，本轮保留为待补缺项 |
| 仍待决定 | 多个批准版本或用途同时出现时的权威选择、列表排序合同 | 提案仅规定精确去重。首次出现顺序为本次实现的稳定保留策略。批量拒绝、修订优先级、同记录同修订跨用途的记录级处置等待领域合同。当前保留不同三元组，逐次授权仍以只读权威记录精确核对 |
| 仍待决定或验证 | Q-04～Q-07、缺失目标规范、采样／描述型启用、Windows/Linux 一致性 | 按原批准边界跟踪。尚无新增关闭证据 |

本轮在 Ubuntu CPython 3.12.16 下运行 `bash scripts/verify.sh`，165 项测试通过，锁检查与锁定安装、Ruff、mypy、导入边界、源码包和 wheel 构建通过。[整改本地验证日志](evidence/p1-2-batch3-remediation-verify.log)

整改 CI [运行 43187790171](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43187790171) 已完成，结果为 **Success**，用时 26 秒。GitHub 运行页指向实际提交 `56847f4ac38e16c80da608cad194b1aea5d6013a`，与整改代码提交完全一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43187790171/job/131079233482) 的 `Locked local checks and build` 步骤成功。`actions/checkout` 仍有 Node.js 20 弃用警告，runner 使用 Node.js 24 执行，Checkout 步骤成功。
