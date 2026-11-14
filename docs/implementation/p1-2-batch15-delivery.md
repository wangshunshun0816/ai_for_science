# P1-2 第十五批数据边界只读核验

基线为第十四批限定签收 24c5c0635db7aa34df4edf41fdebb02a540a46f5。依据大方案 §5.1／§6.13、开发指南 §3.4／§3.13／§5.3、R02 字段台账、已签收的归属委派与批准定位规则。验收另行进行。

| 字段 | 来源、写入方与约束 |
|---|---|
| DataConstraintQuery.scope | 调用方，§6.13。必填 Dataset 不可变精确 data_ref、用途、接收方、存储和处理地域。此结构只表达请求范围。 |
| 查询 policy_ref、permit_ref | 调用方，§5.1／§6.13。必填 DataPolicy／SendPermit 记录定位及精确修订；非法类型拒绝。 |
| DataPolicy／SendPermit locator、data_ref、tenant_id、project_id、principal_id | R08c，§6.13。必填精确修订、不可变数据版本及受信租户／项目／主体。 |
| allowed_purposes、recipients | R08c，§5.1／§6.13。所含字符串仅作精确成员检查。保留源列表顺序，不静默去重、扩展映射或用空列表通配。通用集合及词表语义待决。 |
| storage_region、processing_region、expires_at | R08c，§5.1／§6.13。必填精确地域和 UTC 失效时点。无隐式地域转换。 |
| DataPolicy.sensitivity、SendPermit.policy_ref | R08c，§5.1／§6.13。必填分类代码及所引用政策的精确修订。分类仅在受信适用性端口找到对应范围证据时可参与核验。 |
| ethics.status、approval_ref、basis_ref、reason | R08c，§6.13。状态必填；其余显式可空。已批准状态要求精确批准定位，不适用要求理由与依据定位，未决阻断。通过适用性端口查证精确请求下的对应伦理事实。 |
| DataConstraintResult.status、authorization、query | 校验器仅输出。固定 constraints_checked_only 与 data_use_terms_unresolved，回显查询范围。 |

委派复验用途、操作、目标、当前租约及签发归属修订。独立 R08c 访问事实须确认当前可读取且未撤销；其后比较独立版本与完整正文。政策与许可同时满足，仅精确匹配。适用性端口须提供与同一请求及版本匹配的分类、伦理依据，单有定位、说明或非空代码不足以通过。真实端口如何验证来源、精确依据、版本不可变、撤销及不预读正文留服务验收。未设置自定义签名或内容 ID。

## 数据侧待决

| 待决 | 依据与建议 | 影响 |
|---|---|---|
| data_use 权威批准条款 | §5.1／§6.13 已定用途和精确归属。建议 A0 审定条款所绑定的数据、政策、许可、主体、用途、地域、接收方及期限。 | 真正发送授权仍阻断。 |
| 分类和个人信息范围 | §6.13 要求登记敏感级别及个人信息范围。建议冻结分类与用途、接收方、地域映射及缺项语义，避免以自由文本推断。 | 无适用事实的路径阻断。 |
| 伦理适用依据 | §6.13 固定三种状态并要求不适用理由。建议明确依据类型、适用范围及现行性验证，避免仅凭引用形状通过。 | 无精确适用依据的路径阻断。 |
| 列表与版本 | 字段台账保留集合、null 及通用目标规范空缺。建议保持只读精确子集，逐项批准扩展。 | 不发布通用政策兼容默认值，也不生成科研内容 ID。 |

预算操作提案仍待审。只读结果不提供发送授权、回执、挂载或暴露事实。DataExposure、实际扫描、发送、签发和原子消耗留后续。

## 验证

Ubuntu CPython 3.12.16 完整检查及构建通过，430 项测试。[日志](evidence/p1-2-batch15-verify.log)。Windows CPython 3.12.14 以 uv sync --offline --locked 重建隔离环境，第十五批专项 21 项及两份生成物检查通过。四组手列规范 UTF-8 与完整 SHA-256 两侧一致；两份 Schema 各侧与仓库字节一致。[Ubuntu](evidence/p1-2-batch15-ubuntu.json) · [Windows](evidence/p1-2-batch15-windows.json) · [专项](../../tests/contracts/test_batch15.py)。

[CI 43591714267](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43591714267) 最终 Success，实际 SHA 为 5535e91883c6e18cfdf2f7c62b1871f153121694。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43591714267/job/132437658164) 的 Checkout、固定工具、固定 Python、Locked local checks and build 均显示 success。构建步骤运行该提交的 scripts/verify.sh。步骤日志端点返回 404，核验限于运行摘要、任务步骤结论和提交脚本，未独立核验远端子命令输出、测试数量或制品。任务页有 Checkout 的 Node.js 20 弃用警告。原九个金样例、手算、设计基线及锁文件保留原字节。

## 伦理与分类整改

独立端口解析当前分类规范、映射及各政策／许可的伦理依据。分类代码须属于规范，映射须对应精确规范和映射修订、主体／归属、不可变数据版本和用途／地域／接收方。伦理依据核验定位与修订、精确目标、请求范围、理由及当前期限和撤销。无关 budget_use 直接拒绝；即使 data_use 定位与独立事实匹配，伦理批准用途与条款尚未审定的路径仍阻断。已有不适用依据的只读合成案例通过。独立事实必须由真实服务认证，接口本身不定义生产分类词表、审批结构或发送授权。

回归覆盖共用未知分类字符串、缺映射／规范依据、错规范或映射修订、错范围，以及伦理批准错用途／目标／修订／范围、过期、撤销、缺依据或条款未审定。拒绝路径均不调用受限正文端口。政策和许可交集、委派及撤销复验和正文绑定保留。

Ubuntu 3.12.16 完整工程检查 443 项及构建通过，Windows 3.12.14 同锁第十五批专项 34 项及生成物检查通过。四组独立规范 UTF-8 与完整 SHA-256、两份生成物在两侧与原交付一致。[Ubuntu](evidence/p1-2-batch15-remediation-ubuntu.json) · [Windows](evidence/p1-2-batch15-remediation-windows.json) · [日志](evidence/p1-2-batch15-remediation-verify.log)。

保留原 CI 证据提交 6af7fab357f6d1609a9330b0dccfa017dff47e71，原运行详细日志未取得。整改 CI 待核验。预算提案继续待审。
