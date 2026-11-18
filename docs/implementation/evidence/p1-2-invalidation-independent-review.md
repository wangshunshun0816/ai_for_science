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

## I-R01 整改和 I-R03 适用边界

原复现见上表。先用标准库独立更新条目锚点和审计链头，旧实现上，失败、未来、二者同时，以及单一同科学版本异修订共 4 项按预期失败。整改后的已用审计记录必须为 ok，且不得晚于受信查询时点。失败及未来分别返回 INVALIDATION_AUDIT_RESULT_INVALID 和 INVALIDATION_AUDIT_TIME_INVALID，二者同时优先返回结果错误。恰在查询时点的合法对照通过。失效读入口和确认守卫均阻断不合格输入，不生成科学否定或资格结论。[审计守卫](../../../danus_ai/contracts/invalidation.py#L251) · [自动回归](../../../tests/contracts/test_invalidation.py)

Q04-A 和大方案 §5.2、§5.5、§8.6 区分科学投影、权威记录及事件，要求精确定位，同时要求真实依赖传播。它们没有给出同科学版本的记录修订何时共同受一条事件约束，也没有把科学前提自动映射到唯一权威记录修订。原实现可以通过把单个真实 requires 指向同 ID、同科学哈希的另一修订，使本事件守卫返回无依赖。现在发现这种已授权异修订且精确来源未命中时返回 INVALIDATION_REVISION_SCOPE_UNRESOLVED；既不按哈希传播，也不放行。精确命中仍按原规则传播。异修订越权时，该修订受限快照、正文读取为零。

|待 A0 决定|规则与影响|
|---|---|
|推荐：独立权威适用映射|R13/R19 提供同归属、精确事件及前提修订对应的权威依据，说明是否沿用受损的定义性证据。已有明确关联才传播；明确独立才返回本事件不适用。无映射继续阻断。换修订本身不能清除限制。|
|备选：只按记录修订传播|事件只作用于精确修订。另一修订须有独立证据证明其前提重绑定有权且资格已重新核验，才能判断本事件不适用。若只比较定位，已实测可用换修订绕过，因此不建议省略独立重绑定。|

I-R02 混合传播疑点仍未复现。完整 requires 图通过比较边连接失效源时不传播，反向比较不影响原真实依赖路径，已纳入回归。Ubuntu CPython 3.12.16 完整工程 593 项通过，18 项 SQLite 专项跳过。Windows 3.12.14 同锁专项 35 项通过。六组规范字节及完整摘要两端一致，两份 Schema 逐字节对照通过且保持原字节。原九件金样例、手算、设计基线未变。整改 CI 与人工验收按新提交分别登记。

## 整改 CI 与定向复验

[整改 CI 44127201891](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891) 首次手动触发，实际 SHA 为 775ca649d3b003c32d5b3751f8252bc2ecf1862f，最终成功。[foundation 作业](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891/job/134194135744)显示 Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build 均成功。作业明细日志下载返回 HTTP 403，单步日志链接返回 HTTP 404，未取得详细日志或核验远端逐项输出和计数。

同一 SHA 在 Ubuntu 默认 pytest 路径收集 35 项失效专项，定向复跑 35 项通过。由工作流和测试开关确认此 CI 未启用 DANUS_P13_TEST，SQLite 专项跳过，无新增存储证据。 失败、未来时点及两者同时发生的审计均阻断。恰在查询时点的合法对照通过。获授权的同科学版本异修订路径返回 INVALIDATION_REVISION_SCOPE_UNRESOLVED，既不自动传播也不授予确认资格。比较边截断复验通过，越权异修订的受限快照及正文读取均为零次。异修订权威适用映射仍待 A0 决定。

失效证据子集及 I-R01 审计整改已由 A0 于 2026.11.18 限定签收（aad0fe493090a2840e1ce6f799b7510fbf342467）。I-R03 权威适用映射仍待决定。原发现、原始及整改 CI 的日志限制和 SQLite 跳过证据保留。 [限定签收](../decisions/A0-P1-2-invalidation-acceptance.md)
