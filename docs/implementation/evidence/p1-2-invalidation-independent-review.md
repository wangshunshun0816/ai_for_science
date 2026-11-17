# 明确失效证据独立复核

复核对象为 24e99a51e6078c306328f6facbdce7a04e8e24eb。Ubuntu 在该 SHA 以默认 pytest 路径收集失效专项 27 项，定向复跑 27 项通过。下面另用同一合成权威夹具独立变更输入，不修改测试或产品代码。SQLite 专项未执行，无新增存储证据。

|编号及结果|复现与实际观察|关闭条件|
|---|---|---|
|I-R01，已复现审计接纳缺陷|从 Source 合法对照出发，分别把最后一个 AuditEntry 的 result 改为 error，把 timestamp 改为 2099-01-01T00:00:00Z，及同时修改两项。每次用标准库重算该条锚点和检查点链头，保留事件、精确报告及其余权威事实。合法对照和三个变体均返回 needs_reaudit。守卫检查 operation、报告绑定、事件摘要及链头，但没有检查操作结果或查询时点。见 [history](../../../danus_ai/contracts/invalidation.py#L251)。|对登记有效的 R13 追加结果和评价时点作明确校验。失败、未来及二者并存均拒绝，不产生失效结论，也不授予确认资格。合法当前事件继续通过。|
|I-R02，混合及反向疑点未复现|原两跳 requires 图增加正反比较边仍判 needs_reaudit。另将失效源换成 comparison，独立绑定报告、事件及链头，目标的两跳 requires 图只通过一条 contradicts 边接到该源，返回 no_dependency_on_source。反向纯比较仍无传播；把反向边作为 requires 作无覆盖注入，返回 INVALIDATION_GRAPH_SCOPE_MISMATCH。用比较边替代权威论断定义中的真实前提，返回 INVALIDATION_GRAPH_PREMISES_MISMATCH。见 [depends_on_source](../../../danus_ai/contracts/invalidation.py#L294)。|保留独立回归。范围仅为单一事件与依赖对的检查，不证明目标总体有效，也不证明生产 R19 图完整。|
|I-R03，同科学版本的异修订行为已复现，适用语义待明确|增加同 ID、同科学版本、独立锚定的论断记录 rev 2。事件仍绑定 rev 1，仅将一条 requires 的单个前提指到 rev 2。返回 no_dependency_on_source，require_unaffected_confirmation 正常返回。两修订同时出现的原专项拒绝仍通过。单条引用是否构成换修订绕过取决于科学前提到权威精确修订的独立映射。当前内部前提只保存 ID＋科学版本，图检查据此比对，传播采用三元组。见 [前提核对](../../../danus_ai/contracts/invalidation.py#L320) 和 [消费入口](../../../danus_ai/contracts/invalidation.py#L420)。|明确该关联的权威映射及失效跨记录修订范围。分别固定合法独立修订和不可通过换修订脱离同一失效证据的反例。映射不足时安全阻断。|
|I-R04，权限与原证据链|拒绝上例 rev 2 的读取授权，得到 INVALIDATION_REFERENCE_UNAVAILABLE，该修订的快照、正文读次数均为零。原专项也确认整条根权限拒绝为零读取，以及错对象、项目、运行、正文替换与破坏审计链拒绝；缺事件或权威诊断、服务错误、证据不足、复现未完成均无结论。三类合法对照保留原科学版本、正文和历史，复审计仅返回定位，无定位时受影响依赖仍被拒绝用于新确认。|真实授权、审计适配器的预读保证、R18／R13 来源认证与 R19 队列仍需服务验收。|

## CI 证据范围

GitHub Actions 以交付完整 SHA 查询返回 0 次运行。核验时远端 main 为 a3ab1ec77746055fb7199145b228db4fb5a155ea，交付 SHA 在本地。最近可见的 [CI 44027827660](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44027827660) 实际为 a3008c5c7dece9c3dc0bfac52244cf29d55e5232，运行、foundation、Checkout、Install pinned tooling、Install pinned Python 以及 Locked local checks and build 均成功，详细日志端点 HTTP 403。该旧运行只作为 C 组证据。本包 27 项的默认收集及定向结果均为本地证据。对应 CI 待同步后单独核验。
