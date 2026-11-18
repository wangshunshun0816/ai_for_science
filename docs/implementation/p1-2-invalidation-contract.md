# R02 明确失效证据与下游使用资格

|字段或视图|权威、版本及约束|
|---|---|
|ClaimRecord 与 ClaimEvidenceRef|沿用 Q-04。R13 写论断定位、归属、科学版本；定义性运行及前提继续进入原科学投影。|
|InvalidationReport|R18 明确诊断的只读投影。精确报告定位、原论断、定义性运行、归属、实现错误／污染／协议失效及诊断定位。独立确认事实绑定完整报告。通用复现类型、独立性、容差和数值判据另案。|
|EvidenceEvent|R13 追加。报告、尝试、制品、前驱摘要、审计位置和完整状态快照沿用 Q-04。§8.6 明确失效事件不改变科学内容、结果、强度或历史标记。|
|DependencySnapshot|§5.5／§6.28。R19 提供带归属和精确修订的完整前提图。requires 单独传播；replicates／contradicts／supersedes／generalizes 仅比较。前提图不得违反已有内部科学前提。|
|ReauditTaskLink|R19 只读定位，绑定任务、触发事件、归属及受影响论断。不设分诊默认值。优先级、风险、预算、负责人及下一步与期限的通用写入、状态和分诊规则另案。|
|查询与结果|调用方只提交精确定位。受信权限先于快照和正文。结果仅是本次事件的影响，不授予总体有效性。缺事件或权威证据均阻断。无任务时，已确认的使用限制仍立即生效。|

依据为大方案 §5.1、§5.4–5.5、§6.4、§6.27–6.28、§8.6–8.7，开发指南 §3.4、§3.28 和 Q-04 A 签收。

## 交付、关闭范围与验证

正式入口为 check_invalidation_impact 和 require_unaffected_confirmation，分别核验只读结果并守卫本次事件有关的确认使用。精确调用方、服务持有对象与输出在 I-SCHEMA 分开登记，两份 Schema 已更新。[实现](../../danus_ai/contracts/invalidation.py) · [独立夹具和正反例](../../tests/contracts/test_invalidation.py)

本次关闭 §6.4 复现降级样例的明确实现错误、污染、协议失效子场景。独立预期先用标准库冻结四份论断科学预映像和两个判断结果；后续验证不由待测代码生成答案。样例单独准备完整正文、当前委派、各记录独立精确摘要、R13 审计链和检查点、R18 独立诊断、R19 前提图及任务定位。需要真实来源的证据在测试中明确用合成端口提供。

事件追加有精确归属、报告绑定、前驱摘要及审计位置。只传播真实 requires 的直接与间接影响，非依赖比较对象只产生 no_dependency_on_source，不取得总体资格。命中依赖且未取得任务定位时仍拒绝新的确认性使用。服务错误、证据不足、复现未完成、缺事件、缺权威诊断、错版本、错归属、无权访问和破坏链条均无有效性结论。科学陈述、结果、强度及历史标记继续保留。旧形状与旧预映像不变，普通事件投影入口仍拒绝未通过本包核验的失效事件。

尚缺数值复现方法与容差、抽样不确定、范围变更、资格恢复、完整 ReauditTask 队列合同和适用目标/消息。该子集的同项目审计链及 R19 当前前提图均须有独立覆盖，跨项目、数学／外部前提及来源证据缺失时阻断。真实报告认证、R13 写入与检查点认证、R19 图物化／队列、生产资格撤销、真实复现分别留后续服务验收。本次的审计使用不赋予这些写权。

- Ubuntu CPython 3.12.16 执行 env -u DANUS_P13_TEST bash scripts/verify.sh。585 项通过、18 项 SQLite 专项跳过，静态检查、Schema 和发行构建通过。
- Windows CPython 3.12.14 使用同一 uv.lock，定向运行 tests/contracts/test_invalidation.py 的 27 项并用 scripts/export_r02_schema.py --check 复核。四组科学预映像、两组判断结果的字节和完整 SHA-256 两端一致，两份 Schema 均与新生成物逐字节一致。[实际比对输出](evidence/p1-2-invalidation-cross-platform.json)
- 本轮独立金样例见 tests/fixtures/invalidation/independent.json。原九件、手算、签收设计及依赖锁保留原字节。远端 CI 与人工验收按交付 SHA 另行登记。

## 独立复核状态

27 项本地默认收集及定向复跑通过。独立复核复现审计失败／未来时点仍接纳的缺陷，同科学版本不同精确修订的行为已记录且适用语义待明确。三类子场景有正向证据，样例出口待整改及复验。对应交付 SHA 的 GitHub Actions 查询为 0 次运行，不沿用旧 C 组结果。[复现、CI 范围与关闭条件](evidence/p1-2-invalidation-independent-review.md)

审计结果及时点整改已完成本地复验。失败或未来审计记录阻断，合法对照通过。同科学版本异修订缺适用规则时阻断，推荐与备选待 A0 决定。Ubuntu 593 项通过、SQLite 专项跳过 18 项，Windows 同锁专项 35 项通过。六组规范字节及两份未改 Schema 两端一致。[整改、A0 选项及原复核证据](evidence/p1-2-invalidation-independent-review.md#i-r01-整改和-i-r03-适用边界)

## 整改 CI 与定向复验

[整改 CI 44127201891](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891) 首次手动触发，实际 SHA 为 775ca649d3b003c32d5b3751f8252bc2ecf1862f，最终成功。[foundation 作业](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891/job/134194135744)显示 Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build 均成功。作业明细日志下载返回 HTTP 403，单步日志链接返回 HTTP 404，未取得详细日志或核验远端逐项输出和计数。

同一 SHA 在 Ubuntu 默认 pytest 路径收集 35 项失效专项，定向复跑 35 项通过。由工作流和测试开关确认此 CI 未启用 DANUS_P13_TEST，SQLite 专项跳过，无新增存储证据。 失败、未来时点及两者同时发生的审计均阻断。恰在查询时点的合法对照通过。获授权的同科学版本异修订路径返回 INVALIDATION_REVISION_SCOPE_UNRESOLVED，既不自动传播也不授予确认资格。比较边截断复验通过，越权异修订的受限快照及正文读取均为零次。异修订权威适用映射仍待 A0 决定。

失效证据子集及 I-R01 审计整改已由 A0 于 2026.11.18 限定签收（aad0fe493090a2840e1ce6f799b7510fbf342467）。I-R03 权威适用映射仍待决定。原发现、原始及整改 CI 的日志限制和 SQLite 跳过证据保留。 [限定签收](decisions/A0-P1-2-invalidation-acceptance.md)
