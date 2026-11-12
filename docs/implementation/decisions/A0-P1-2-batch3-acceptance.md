# P1-2 第三批人工验收记录

状态：A0 已于 2026-11-12 完成整改复验，结论为通过，范围仅限 P1-2 第三批已交付及整改内容。

## 批准依据与提交核对

依据 [A0 首组契约决策清单](A0-R02-first-contracts-checklist.md) §5 本人签收及 §6 实施范围，批准提交为 `1f34e0d611066acd7273a9c0843e5c93514ecd14`，绑定提案提交为 `48bd0dcc0afa78c2b6447fdfe789465b0d3a8068`。签收栏记录 Jack\_Wang 于 2026-11-12 采纳 P1、P3、P4、P5 推荐方案，P2 限定固定枚举首包。批准记录部分标题和说明仍使用签收前措辞，实施授权以 §5 实际签收内容为依据。参见 [绑定提案](../r02-first-contracts-proposal.md) 和 [第三批交付记录](../p1-2-batch3-delivery.md)。

|核对对象|结果|
|-|-|
|整改前证据基线|均为 `938f7dcaf953be57e99cafc79cd3fc725c4ddd38`。通过本地 Git 和 `git ls-remote origin refs/heads/main` 核实|
|第三批原始代码|`a4d0553233c62613afb90cb0202618d01f5e5dd9`|
|整改前 CI 实际提交|`86aeac09bfe9e36ef3dac272ff9f09ea8e6ac8a2`，GitHub 运行页直接链接此 SHA，Git 祖先关系确认包含第三批代码提交|
|代码提交至 CI 提交的实际差异|仅修改 `docs/implementation/commit\\\_log.md` 和 `docs/implementation/p1-2-batch3-delivery.md`，共 9 行新增、4 行删除。两次提交的代码、测试、依赖锁和工作流一致|

## 实现与批准范围逐项核对

|决定|已交付且有证据的范围|缺项或偏差|
|-|-|-|
|P1 归属与引用|候选、预注册、运行采用项目级形状。协议允许租户级形状。只读端口校验私有引用的租户、项目使用权限和精确版本。PublicRef 要求独立准入定位|租户级协议的真实授权、撤销联动与公共准入解析仍缺服务和目标规范。现有证据为形状校验及只读替身|
|P2 固定枚举首包|四对象严格区分草稿和权威字段，校验类型、必填与显式 null。RunRequest 实现八模式字段形状，独立 ExecutionBinding 无反向引用。候选有科学投影与版本复算，方法配置有科学限额投影和一致性校验。纯预算单独核验用途、币种、额度和有效性|Protocol、Prereg、RunRequest 尚无完整内容投影和版本计算，ExecutionBinding 尚无正式内容 ID。停止规则的跨对象一致性及真实预算准入仍缺。固定枚举 Prereg 的 randomness/discrimination 只支持明确不适用分支，预算估价只支持带依据引用的 planning\_estimate。四对象公共字段 approval\_bindings 已按提案 §1.1 的目的、记录、修订三元组精确去重。批量冲突处理仍待决定，见下文|
|P3 历史、来源与集合|科学引用投影保留类型及内容版本，历史引用同时保留实体 ID。候选来源位置参与投影，去重前逐个核验原始引用。arms 保留原序，规范集合工具提供规范化后按 JCS 字节排序和去重|历史完整投影与审计链受 Q-04 阻塞。未完成的对象投影尚无完整集合规范化。arms 现保留完全相同的条目和原序，拒绝同键异值。外部 synthetic\_design 的原始来源可独立于 sources 提供，仍须有精确位置且单独核验访问权限。方法参数及调参名称唯一性按提案保留|
|P4 科研条款与批准定位|Prereg 把 selection\_terms、threshold\_terms 与批准定位分开。只读校验对照有效批准的精确目标、版本和条款，可拒绝错版、过期、撤销及条款自改|条款进入完整 Prereg 科学投影仍待实现。Q-05 签名核验、正式锁定与运行授权未交付|
|P5 dev/val 前置|受信 task\_kind 合同绑定租户、项目和主体，决定是否需要 Prereg，缺合同则阻塞。要求计划时核对计划版本及 arm，另校验角色和引用。运行就绪入口返回 SPEC\_UNRESOLVED|A5 正式任务所需的实际合同、锁定事实、数据切分授权、sanity 有效性与完整委派尚需真实服务证据|

实现入口见 `danus\\\_ai/contracts/` 下的 `first\\\_objects.py`、`references.py`、`runs.py`、`projections.py` 和 `guards.py`。候选版本计算以引用可访问且目标规范就绪为前提，本批证据来自合成测试。Q-07 未关闭时，Protocol 的 duplicate\_policy 保留输入建议，无默认策略，完整版本计算仍受阻。

## 本地验证与远端 CI

本地交付日志记录在 Ubuntu CPython 3.12.16、uv 0.13.7 下运行 `bash scripts/verify.sh`。锁检查、锁定安装、Ruff、mypy、导入边界及受控反例、源码包与 wheel 构建均通过。pytest 共 160 项通过，耗时 0.90 秒。这是整改前的交付验证。整改验证见下文。原九个 JSON、手算 README 和三份设计基线的字节比对记录均为 MATCH。参见 [本地检查日志](../evidence/p1-2-batch3-verify.log) 和 [保留文件比对记录](../evidence/p1-2-batch3-preservation.txt)。

[CI 运行 43184083094](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43184083094) 于 2026-11-12 在 main 手动触发，结果为 **Success**，总用时 21 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43184083094/job/131066858494) 及 `Locked local checks and build` 步骤成功。GitHub 注释显示，固定版本 `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` 目标为已弃用的 Node.js 20，由 runner 强制使用 Node.js 24 执行。任务结果仍为成功。

## 保留事项与验收边界

* **Q-04 待决**。历史科研与审计字段划分、记录 ID、摘要及审计链。
* **Q-05 待决**。签名载荷、域分离、核验和回执。
* **Q-06 待决**。完整状态转换、暂停恢复、对账及保护性中止分类。
* **Q-07 待决**。重复或冲突观测策略，及依赖该策略的版本计算。
* **目标规范待补**。包括真实 Scope 和来源快照、TestSpec、MissingPolicy、FeedbackPolicy、UnitSpec、SelectionRule、StopRule、FailurePolicy/RetryPolicy、任务合同和批准／准入规范。按功能核验适用内容、精确版本及独立参考。
* **采样／描述型分支未启用**。需独立方法参考、适用材料和单独启用决定。
* **跨平台验证待办**。Windows CPython 3.12 环境和 Windows/Linux 纯契约一致性证据仍缺。

本次人工审阅范围为第三批实际实现的固定枚举纯契约、只读替身验证和工程检查。真实服务准入、完整科研链路、跨平台一致性及 P1-2／R02 整体验收各有独立证据要求。

## 整改复验

整改代码及本地证据提交 `56847f4ac38e16c80da608cad194b1aea5d6013a` 已推送 main。批准规则、整改前约束及影响逐项记录于 [交付记录 §6](../p1-2-batch3-delivery.md#6-第三批人工验收整改)。

* **本批整改已具备本地证据**。精确去重保留首次出现，不同版本保留。同记录同修订不同用途的绑定仍逐次对照权威记录，错误用途被拒绝。外部合成来源可独立提供，arms 接受相同条目并保持顺序，同键异值仍被拒绝。名称唯一、保留参数名、外部报告来源必须列入 sources 等已批准规则保留。
* **已批准延期**。Protocol、Prereg、RunRequest 等完整投影、正式 ID、真实服务准入和跨平台验证继续按原范围跟踪。固定枚举 Prereg 仅交付明确不适用的 randomness/discrimination 形状，适用分支受目标规范约束。预算估价仍限 planning\_estimate，其他 NumericValue 形状和依据结构待补。
* **仍待决定或补齐**。Q-04～Q-07、目标规范、采样／描述型启用，以及多个不同绑定的记录级冲突处置、修订优先级和对外排序合同。逐次批准核验依据精确目标、用途和当前有效性。

整改本地 `bash scripts/verify.sh` 通过，pytest **165 passed in 1.18s**，静态检查、导入边界和打包通过。[整改验证日志](../evidence/p1-2-batch3-remediation-verify.log)

整改 CI [运行 43187790171](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43187790171) 已完成，结果为 **Success**，用时 26 秒。GitHub 运行页指向实际提交 `56847f4ac38e16c80da608cad194b1aea5d6013a`，与整改代码提交完全一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43187790171/job/131079233482) 的 `Locked local checks and build` 步骤成功。`actions/checkout` 仍有 Node.js 20 弃用警告，runner 使用 Node.js 24 执行，Checkout 步骤成功。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.12

意见：已审阅第三批交付及整改记录。approval\_bindings 精确去重、外部 synthetic\_design 来源约束和 arms 条目处理已整改，本地 165 项测试及工程检查通过。整改 CI 对应提交 56847f4ac38e16c80da608cad194b1aea5d6013a，运行成功，同意本批限定范围验收通过。多个批准绑定的记录级冲突、修订优先级及对外排序继续待决；Q-04～Q-07、缺失目标规范、完整投影、真实服务准入、采样／描述型启用及跨平台验证按既有边界跟踪。checkout 运行时警告列为维护项。P1-2 整体完成状态仍以全部验收要求为准。

验收结论：通过（仅限 P1-2 第三批已交付及整改范围）

