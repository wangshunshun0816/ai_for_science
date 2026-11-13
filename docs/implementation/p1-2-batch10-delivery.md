# P1-2 第十批协议工件与 I-SANITY

起点为第九批限定签收 `beb7742a0df19dfb6ced62a8c6423be1977ecf31`。依据大方案 §5.1、§6.16、附录 A，开发指南 §3.4／§5.3、字段台账及首组 P1/P2 精确引用和固定枚举边界。人工验收另行登记。

| 字段 | 来源与写入方 | 约束 |
| --- | --- | --- |
| ProtocolBundle、CheckSuite 的 locator、tenant_id、project_id | §5.1 与首组 P1；R04b 权威端 | 记录类型、ID、修订、归属均为必填；包和详细套件为项目视图 |
| ProtocolBundle.protocol_ref、suite_version_ref、binding_snapshot_ref | §5.1／§6.16；R04b | 必填精确 Protocol、CheckSuite 和 ExecutionBinding 引用，必须与解析绑定一致；租户级协议沿用项目使用授权 |
| ProtocolBundle.component_refs、independent_reference_refs | §5.1；R04b | 非空列表；每条原始引用核对归属、正文摘要及材料来源，保留顺序，不先去重 |
| ProtocolBundle.approval_ref | §5.1；A0 批准，由 R04b 引用 | 可空；有值须为 protocol_use 定位。该用途未审定，要求已批准的操作明确阻断 |
| CheckSuite.suite_version_ref、checks | §6.16；R04b | 必填，详细项与既有固定四题套件检查名完全一致 |
| CheckDefinition.applicability_ref、expectation_ref、tolerance_basis_ref、uncovered_scope_ref | §6.16；R04b | 精确材料引用，前三项非空，最后一项可空；各材料的通用内容规范仍待定 |
| SanityJobRef.job_id | §6.16；R10a/R08 | 非空，作业受理引用，仅输出 |
| SanityReportView.report_ref、expected_binding_ref | §6.16；R10a 授权视图 | 精确报告定位及当前绑定，缺权威报告或错归属／修订阻断 |
| SanityReportView.check_results、eligibility、stale | §6.16；R10a 纯视图 | 复用五类检查状态，仅在固定四题当前确认绑定、审批及必需项核验成功后输出；失败走明确错误，待定的通用视图枚举不补造 |

复用已有 Sanity 请求、报告、固定套件及 ExecutionBinding。报告视图复用必需项校验；探索 profile、过期报告和未获批准的不适用均不能产生确认资格。视图不提供运行权限。I-SCHEMA 标注服务持有、仅输出以及运行时守卫。材料仅按权威来源和精确摘要核验，通用组件分类、科学投影和正式内容 ID 保持待定。真实执行、调度、仓储及批准服务按后续阶段验收。

## 证据

Ubuntu CPython 3.12.16 完整工程检查及构建通过，296 项测试通过。[日志](evidence/p1-2-batch10-verify.log) 原九个金样例、手算、设计基线和依赖锁无字节差异。远端 CI 待核验本批交付 SHA。

Windows CPython 3.12.14 使用临时隔离环境，通过现有依赖锁同步项目所需依赖。8 项专项测试及 Schema 检查通过。四种新增合同各有一组手列预期，由独立标准库 JSON 编码并计算 SHA-256。两侧规范 UTF-8 和完整摘要逐项一致；两份生成物在两侧分别与仓库文件逐字节一致。[Ubuntu 向量](evidence/p1-2-batch10-ubuntu.json) · [Windows 向量](evidence/p1-2-batch10-windows.json)

专项覆盖有项目授权的租户级协议、撤去授权、错套件必需项、错报告定位、绑定与 profile、过期、缺项、缺陷、服务错误、未覆盖及缺依据的不适用。探索 profile 无法用于确认，包的组件不能反向引用绑定或报告。普通统一入口拒绝服务持有协议包及仅输出报告视图的载荷。合成端口证据限于上述纯契约行为。
