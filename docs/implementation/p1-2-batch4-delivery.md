# P1-2 第四批交付：Q-04～Q-07 纯契约

## 批准和起点

开工时 Ubuntu 仓库 `/home/wangshunshun/danus-ai` 工作区干净，本地 HEAD、origin/main、远端 main 均为 `412e67e0586fe21837916111eefb89c9223f01fa`。读取 AGENTS.md 和 [A0 决策清单](decisions/A0-P1-2-Q04-Q07-checklist.md)。Jack_Wang 于 2026-11-12 签收 Q-04、Q-05、Q05-C、Q-06、Q-07 的 A 方案，绑定 `2ff34729510f02750f3d1ea7799adfbb55819db2` 的 [实施方案](p1-2-q04-q07-proposal.md)。签收授权范围为 R02 契约结构及纯契约验证，第四批工程验收由 A0 签收。

## 交付范围与剩余依赖

| 项目 | 实现及验证 | 依赖或后续验收 |
| --- | --- | --- |
| Q-04 论断、事件、审计 | `contracts/claims.py`。科学版本绑定陈述、Scope、科学分类和定义性来源。内部运行／协议／预注册及前提用精确版本，外部来源保留位置，数学保留旧 fact ID。证据事件推导强度及标记，记录定位、事件摘要、审计链分域。租户链验证前链摘要、序号、对象摘要承诺和独立链头。测试独立字节向量、证据更新、科学修改、未就绪引用及篡改／截尾 | 真实 Scope、来源快照、定义性运行和前提版本、证据事件的可信写入与排序、日常外部检查点留存、恢复及真实审计 |
| Q-05 签名及回执 | `contracts/signing.py`。严格签前清单、用途域和信封，精确核对主体、范围、用途、受信密钥和签名期限。回执绑定 manifest、信封、渠道及实际分发包摘要。制品字节和清单逐件核对。回执重放不重复推进，未知结果保持 signed，发布和撤回由已确认的受信回执投影 | Ed25519 验签由受信端口注入，生产适配、信任配置、轮换、撤销时点策略待对应阶段。真实公开映射、脱敏回执导出、许可、校验报告及实际发布证据仍待 R21 |
| Q05-C 批准歧义 | `contracts/approval_conflicts.py`。在受信归属内按记录 ID 与修订审查，保留全部冲突证据。完整撤销／替代必须覆盖同一修订的证据并获有权确认。新纯入口复用 `require_approval`，并核验受信主体摘要，明确请求精确修订。多个正常修订保持独立，展示顺序无授权优先级 | R09 需提供已验签权威证据、完整歧义集合、处置权限和精确主体摘要，再将新入口接入正式授权。原第三批只读入口继续支持既有调用 |
| Q-06 状态与守卫 | `contracts/transitions.py`。暂停／阻塞保留原阶段，普通暂停只允许已启动且经明确处置的工作继续。恢复检查版本、任务合同、权限、额度、租约及待对账条目。尝试对账检查 revision、fencing、外部身份和制品事实，保护性中止与科学资格分开。重试要求同一 run、明确 RetryPolicy、费用及副作用已核实、基础设施原因及最多两次。终态更正追加引用，工程三维按写入角色独立验证 | 正常调度边及外部状态采集、额度结算、任务处置规则的真实提供方，正式尝试选择策略及意外多个完整尝试的预注册政策，费用释放和故障演练继续待办 |
| Q-07 四题观测 | `contracts/observations.py`。受信固定四题策略和 run／attempt／arm 绑定，保留全部原始行和制品行位置。相同行计一次，同单位冲突整包 invalid 且无分数，缺题 incomplete、分母维持 4。标签只来自受信评价策略。核对正例 2/4、3/4，有限否定两臂 2/4，复制 q3 十次拒绝 14 单位，拒绝混入其他尝试 | 真实 UnitSpec、MissingPolicy、DuplicatePolicy 与隐藏标签来源需由 R04b/R06/R08 验证，R10a/G0 执行联调。固定枚举之外的重复、配对、聚类和采样仍需独立批准及目标规范 |

以上纯函数由调用方提供受信事实、端口及时间。构造 DTO 本身不提供身份、服务权限或证据真实性。首组未完成对象的完整投影、真实准入、Windows/Linux 字节一致性仍按剩余工作清单跟踪。

## 本地及远端验证

Ubuntu CPython 3.12.16 执行 `bash scripts/verify.sh`。锁检查、锁定安装、Ruff、mypy、导入边界、源码包和 wheel 构建通过，pytest **181 项通过**。新增测试使用既有规范化逻辑、独立预期和固定 Ed25519 测试密钥，测试适配器调用 Ubuntu 自带 OpenSSL，无新依赖。原九个金样例、手算 README 与三份设计基线逐字节与批准提交一致。见 [本地检查日志](evidence/p1-2-batch4-verify.log) 和 [保留文件比对](evidence/p1-2-batch4-preservation.txt)。

第四批远端 CI [运行 43207738623](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43207738623) 由 `workflow_dispatch` 触发，结果为 **Success**，总用时 20 秒。GitHub 运行页指向 `f0da7c201821599a2ac40a20447e133ffe9bf55b`，与第四批代码提交一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43207738623/job/131147086969) 的 `Locked local checks and build` 步骤成功。`actions/checkout` 仍有 Node.js 20 弃用警告，runner 使用 Node.js 24 执行，Checkout 步骤成功。
