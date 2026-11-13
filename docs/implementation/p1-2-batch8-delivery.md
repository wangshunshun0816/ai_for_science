# P1-2 第八批固定四题纯契约

基线为第七批签收提交 `e3b899b27842e1af7662252c2d0ed71781bbd6b8`。依据开发指南 §3.4、§5.3，大方案 §3.9、§5.1、§5.3、§6.16–6.20、§6.29 与附录 C，沿用首组批准及 Q-04～Q-07（含 Q05-C）。人工验收另行登记。

## 字段来源、写入方与约束

| 字段 | 写入方 | 出处与约束 |
| --- | --- | --- |
| 草稿 statement、scope_ref | A5 经 R09 | §5.1；非空陈述，精确 Scope |
| 草稿 run_refs、protocol_ref、prereg_ref、premise_refs | A5 经 R09 | §5.1、附录 C；沿用 run_refs 命名，至少一条运行，每条先核授权与版本；固定四题运行须匹配协议、预注册、Scope |
| 服务记录 locator、tenant_id、project_id | 记录权威服务 | §5.1、首组归属决定；精确修订与当前项目 |
| ClaimSubmission draft、status、report_ref、claim_ref | R13 | §5.3、§6.20；修改正文另建版本，终态有报告，仅 accepted 可关联论断 |
| SanityRequest binding_ref | 授权调用方 | §6.16；沿用 ExecutionBinding，解析准确协议、套件、数据及切分、代码、镜像、依赖、配置及 profile；无报告反向依赖 |
| SanityReport locator、tenant_id、project_id、binding_ref、suite_ref、profile_ref | R10a | §5.1、§6.16；当前项目的精确报告与当前绑定、套件和 profile |
| SanityReport checks、stale、approval_bindings、not_applicable_bases | R10a 保存受信事实 | §6.16；五类状态，当前批准与不适用依据，失效报告不得用于确认 |
| SanityReport evidence 的 basis_refs、output_refs、coverage、residual_limits | R10a | §6.16；每项证据和状态一一对应，解析依据与输出 |
| EvidenceReport submission_ref、decision、gate_refs | R10–R13 | §5.1、§5.3、§6.20；绑定提交精确修订、报告结论和关口记录 |
| EvidenceReport basis_refs、observation_bindings、audit_refs、repair_scope | R10–R13 | §5.1、§6.20、Q-04/Q-07；引用依据、固定四题观测绑定、审计定位和可空修复范围；评价从受信行重算 |
| GateExecution subject_ref、gate、attempt、policy_ref、trace_ref、result | R12/R13 | §5.1、§6.20、§6.29；精确提交修订，G0/G1/G2，正整数尝试编号，保留错误与缺证 |
| GateExecution invocation_refs、usage_refs | R12/R13 记录引用，R08/R07 提供事实 | §5.1、§6.29；精确可读调用和用量记录，费用来源仅 R07 |
| GateExecution started_at、ended_at、wait_reason、rework_parent_ref | R12/R13 | §6.29；UTC，结束不早于开始，原因和父项可空，禁止自身为父项 |

I-SCHEMA 及两份生成物区分调用草稿、服务持有和仅输出报告；显式登记运行时守卫。测试端口是合成夹具。服务组装负责认证记录正文和来源，纯守卫不写记录或执行关口。未定义的多尝试终态选择保留待决；报告无法靠混合错误和失败推导科学结论。Q05-C 的歧义阻断和显式撤销／替代已经批准。其余边界见[现行剩余工作](p1-2-contract-readiness.md)。

## 验证

Ubuntu CPython 3.12.16 完整检查通过，271 项测试通过。执行 `bash scripts/verify.sh`。证据见[完整日志](evidence/p1-2-batch8-verify.log)。Windows CPython 3.12.14 使用第七批隔离环境及原锁，4 项通过。独立字节预期写在测试中，SanityRequest 的 1 组独立规范字节与完整 SHA-256 一致，见 [Ubuntu](evidence/p1-2-batch8-ubuntu.json) 和 [Windows](evidence/p1-2-batch8-windows.json)。原九个金样例及手算分母记录对比 `412e67e` 无字节差异。

GitHub Actions [运行 43373228351](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43373228351) 在 `main` 手动触发。GitHub API 确认 `completed / success`，实际运行 SHA 为 `6f0f92575b3a374e2ddcf348081c6938952ed6c6`。UTC 05:37:23 开始，05:37:46 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43373228351/job/131713642231) 的 Checkout、固定工具与 Python 安装、锁定检查及构建均成功。

验收复核发现两项缺口。当前调用模型和生成物使用 `run_refs`，与大方案 §5.1 的正式字段 `run_ids` 及 E-02 的旧样例显式适配约定不一致。跨平台逐字节证据仅覆盖 SanityRequest，未覆盖 ClaimSubmissionDraft、ClaimSubmission、SanityReport、EvidenceReport、GateExecution 或生成的两份 Schema。Windows 4 项行为测试另计。


## 验收整改与复验

- 正式 ClaimSubmissionDraft、权威记录的嵌套草稿及生成物统一使用 `run_ids`。每项保留现行 ScientificRef 的运行定义类型、对象 ID 及精确内容版本；原有逐条权限、归属和版本守卫继续生效。旧 `run_refs` 只由测试适配器经显式目录映射。复验正式字段通过，正式入口拒绝旧字段、双字段及 Attempt 引用；旧正例的两个别名保持原顺序并映射到对应运行定义。
- [Ubuntu 完整日志](evidence/p1-2-batch8-remediation-verify.log)记录 CPython 3.12.16、272 项测试及构建通过。Windows CPython 3.12.14 在既有原锁隔离环境运行第八批 5 项测试及生成物检查，全部通过。两侧 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4、pytest 9.2.0，项目锁无变化。
- 六种合同各有一组手列投影，用独立标准库 JSON 编码得出预期 UTF-8 及完整 SHA-256，两侧逐项一致。两侧各自生成的 JSON Schema 和 OpenAPI 均逐字节等于仓库对应生成物，两侧摘要一致。[Ubuntu 输出](evidence/p1-2-batch8-remediation-ubuntu.json) · [Windows 输出](evidence/p1-2-batch8-remediation-windows.json)
- 两侧行为复验覆盖运行字段与旧样例适配、伪造权威字段、错版／归属及未授权引用、Sanity 自依赖与 profile 跳过、提交状态与报告不匹配、错误来源用量和缺题不能接受。字节对照覆盖指定六种合同各一个输入。原九个金样例、手算记录及设计基线无字节差异。

[整改 CI 运行 43375110700](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43375110700) 由 `workflow_dispatch` 在 `main` 手动触发。GitHub API 核实实际 SHA 为 `16df8ec216ceae4e8ccc7edf7e1ab425284183b2`，最终状态为 `completed / success`。运行自 2026-11-13 05:54:54 UTC 开始，05:55:12 UTC 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43375110700/job/131719664882)的 Checkout、固定工具和 Python 安装、锁定检查及构建均通过。

## 后续签收

Jack_Wang 于 2026-11-13 签收通过，限第八批固定四题纯契约的已交付及整改内容。提交 `126095ae4e8fc806559cbfc209e66aa8ef9b8501`，见[验收记录](decisions/A0-P1-2-batch8-acceptance.md)。
