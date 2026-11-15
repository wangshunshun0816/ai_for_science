# P1-2 第十五批人工验收记录

状态：A0（Jack_Wang）于 2026.11.15 签收通过，范围仅限 P1-2 第十五批已交付及整改内容。

## 范围与证据

第十四批签收基线为 24c5c0635db7aa34df4edf41fdebb02a540a46f5。依据第十五批授权、大方案 §5.1／§6.13、开发指南 §3.4／§3.13／§5.3 和已签收的归属、委派及精确引用规则。交付限于 DataPolicy、SendPermit、查询及只读核验结果和 Schema。

- [交付证据](../p1-2-batch15-delivery.md)记录 Ubuntu CPython 3.12.16 完整检查及构建、430 项测试，Windows CPython 3.12.14 同锁专项 21 项及生成物检查。四组独立规范 UTF-8 与完整 SHA-256 一致，两份 Schema 逐字节一致。原九个金样例、手算、设计基线与锁文件原字节保留。本轮复核使用既有日志并定向复现，未重跑全套。
- [CI 43591714267](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43591714267) 最终 Success，实际 SHA 为 5535e91883c6e18cfdf2f7c62b1871f153121694。[foundation](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43591714267/job/132437658164) 的 Checkout、固定工具、固定 Python、Locked local checks and build 均显示 success。该步骤调用对应提交的 scripts/verify.sh，覆盖锁定安装、静态检查、导入边界、Schema、pytest 和构建。详细日志端点返回 404，未独立核验远端各子命令输出、数量或制品。任务页显示 Checkout 的 Node.js 20 弃用警告。证据提交为 6af7fab357f6d1609a9330b0dccfa017dff47e71。

## 逐项复核

| 要求 | 实现及证据 | 发现及复验要求 |
|---|---|---|
| 政策与许可同时满足 | [交集守卫](../../../danus_ai/contracts/data_policy.py#L170)核对许可绑定的政策修订，再分别对两套记录检查精确数据、主体／归属、用途、接收方、地域及期限。[专项](../../../tests/contracts/test_batch15.py#L152)覆盖其中一侧不满足；本轮复现空用途或接收方列表拒绝，敏感分类及地域为 null 拒绝。 | 建议对政策和许可各补空列表与错政策修订断言，保持无默认或通配。仅伦理依据槽位按状态允许 null。 |
| 独立版本与正文 | [端口](../../../danus_ai/contracts/data_policy.py#L112)分别提供版本事实和正文；[守卫](../../../danus_ai/contracts/data_policy.py#L164)缺版本阻断，完整比较两份正文。[专项](../../../tests/contracts/test_batch15.py#L190)覆盖同修订替换接收方、有效期和伦理状态。 | 补缺版本及互换两类正文测试。真实端口的版本不可变和独立性留服务验收。 |
| 当前撤销、委派与读取顺序 | [读取前核验](../../../danus_ai/contracts/data_policy.py#L144)重查当前委派、租约、签发归属版本、操作、目的、数据目标，再核对两记录的当前访问事实。[专项](../../../tests/contracts/test_batch15.py#L160)验证撤销、错租户、数据版本及主体均未调用正文读取。 | 当前撤销由端口是否返回访问事实表达。补进入守卫后委派撤销／过期、旧归属修订、错操作或目标，以及分别撤销政策和许可的反例，核对版本与正文端口调用次数。真实适配器不预读仍留服务验收。 |
| 伦理状态及适用范围 | [结构](../../../danus_ai/contracts/data_policy.py#L39)限制各状态的依据槽位，未决阻断。[适用性守卫](../../../danus_ai/contracts/data_policy.py#L191)比较精确请求、分类和两个 EthicsRequirement。 | **本批整改。** 把许可伦理改为 required_and_approved，令 approval_ref 为其他用途的 budget_use、ID unrelated、修订 1，同时保持许可正文一致并令适用性返回相同 EthicsRequirement，仍得到 constraints_checked_only。当前返回值只回显定位和声明，缺权威批准用途、目标、适用范围及现行性证据。应单独核验适用依据绑定；缺批准规则或事实则阻断。not_applicable 同样须证明依据与当前范围适用，非空理由和定位不足。 |
| 未知敏感分类 | [分类字段](../../../danus_ai/contracts/data_policy.py#L78)接受文本，预期由适用性端口证明。[守卫](../../../danus_ai/contracts/data_policy.py#L191)会拒绝未匹配返回。 | **本批整改。** 将政策和正文 sensitivity 改为 unmapped，再让 DataApplicability 回显 unmapped，仍返回 constraints_checked_only。需核验有独立出处和精确适用范围的分类映射；缺已批准词表或适用事实时阻断，不以文本回显证明映射有效。 |
| 输出与批准隔离 | [结果](../../../danus_ai/contracts/data_policy.py#L86)固定 constraints_checked_only 和 data_use_terms_unresolved。[入口专项](../../../tests/contracts/test_batch15.py#L211)确认普通调用方不能提交权威记录或夹带批准，仅输出结果不能由调用方提交。 | 合同未输出发送资格、回执、挂载或暴露。补消费端拒绝将结果、预算、报价及 Usage 当作数据许可的定向反例。 |

## 验收边界与后续

data_use 条款、敏感分类与个人信息范围映射、伦理适用依据类型及验证规则仍待明确。纯契约合成事实仅证明已定守卫行为。真实来源认证、适配器不预读、扫描、发送、挂载、许可签发、原子消耗和 DataExposure 留后续。预算操作提案继续待审，第十六批未启动。

## 整改复验

原发现及原 CI 证据保留。现由独立版本化分类规范与映射核验代码和适用范围，并按精确定位、目标、范围及有效性核验伦理依据。未审定伦理批准路径仍阻断。已验证不适用依据的只读案例通过。真实端口认证和发送留服务验收。原 CI 详细日志未取得。

Ubuntu 443 项及构建、Windows 34 项和生成物检查通过，四组独立向量与两份 Schema 原字节无漂移。见[整改交付与对照](../p1-2-batch15-delivery.md#伦理与分类整改)。整改 CI 已核验，见下节，预算提案继续待审。

## 整改远端 CI 核验

[整改 CI 43592470752](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43592470752) 已 completed / success，实际 head_sha 为 `1b7e44f7088bd72828dbce592e79956248a3c77b`，与整改提交完全一致。2026-11-14 通过 GitHub REST 运行接口及 jobs 接口直接核验。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43592470752/job/132439936969) 的 Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build 均为 completed / success。

核对该提交的工作流与 scripts/verify.sh：构建步骤调用锁检查、锁定安装、Ruff、mypy、导入边界、Schema 检查、pytest 和发行包构建。详细日志接口 `/actions/jobs/132439936969/logs` 本次返回 HTTP 403，提示需要仓库管理权限，未取得详细日志。证据仅限运行及步骤 API 结论和对应提交脚本，未独立核验远端子命令输出、测试数量或制品；此前原交付日志端点返回 404 的历史记录保留，不视为本次结果。本次未独立核验警告详情，不沿用旧运行警告作为本次证据。本轮仅更新证据文档，未重跑本地测试。

通过的合成案例不代表伦理批准条款或通用分类规则已获审定。真实事实认证仍待服务验收，data_use 未审定路径继续阻断。预算操作提案保持待审，第十六批未启动，人工验收待 A0 签收。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.15

意见：已审阅第十五批交付及整改证据，认可 DataPolicy、SendPermit 及只读约束核验的限定实现。Ubuntu 443 项、Windows 34 项检查通过，四组独立向量及两份 Schema 跨平台一致。整改 CI 对应提交 1b7e44f7088bd72828dbce592e79956248a3c77b，通过；详细日志未取得，证据范围按交付记录保留。伦理批准条款、通用分类规则和真实事实认证未因此获准或完成，不授权真实发送、挂载或许可签发，不代表 P1-2 整体完成。

验收结论：通过，仅限 P1-2 第十五批已交付及整改内容，不含明确保留的待决与服务能力。
