# P1-2 第十一批执行记录与 R07 精确引用

基线为第十批限定签收 `a46798ed401c9d61cd91b98fb711ba1be23ca185`。依据大方案 §5.1–5.3、§6.10–6.11 和附录 C.3，开发指南 §3.4／§5.3、首组归属决定和 Q-06。人工验收另行登记。

| 字段 | 来源及写入方 | 精确版本、可空及约束 |
| --- | --- | --- |
| 两记录 locator、tenant_id、project_id | §5.1；R08 | 均非空。定位携带记录类型、ID 和修订；归属匹配当前项目 |
| RunRecord.definition_ref | §5.1–5.2、C.3；R08 | 非空，精确 RunRequest 科研版本，保留既有运行定义 |
| RunRecord.attempts | §5.3、C.3；R08 | 必填列表，可空列表；每条为精确 Attempt 修订并绑定同一运行，保留原序和失败事实 |
| RunRecord.artifacts | §5.1、C.3；R08 | 必填列表，可空列表；逐条核对精确引用、授权和所属运行 |
| RunRecord.exit_reason_ref | §5.1、C.3；R08 | 可为 null；有值须为该运行的精确退出事实 |
| RunRecord.usage_ref | §5.1、§6.10；R08 记录引用、R07 提供事实 | 可为 null；有值须为该运行的精确 Usage |
| InvocationRecord.purpose、request_digest、response_version | §5.1、§6.11；R08 | 用途及完整摘要非空；响应版本可为 null，均与同修订调用事实相符 |
| InvocationRecord.model_profile_ref | §5.1、§6.11；R08 | 非空，精确 ModelProfile，缺目标规范拒绝 |
| InvocationRecord.retry_refs | §5.1、§6.11；R08 | 必填列表，可空列表；精确关联同一调用且匹配用途、请求摘要和模型配置 |
| InvocationRecord.usage_ref、cost_ref | §5.1、§6.10；R08 记录引用、R07 提供事实 | 分别为可空 Usage、Settlement 精确引用，有值须属于该调用 |

复用 AttemptSnapshot 和 AttemptFacts 推导逐尝试科研资格，缺证据为 incomplete，账务状态仍独立保留。已结算的尝试须解析属于其上一精确修订的 R07 结算事实。空用量或费用引用不产生零金额。通用运行级资格汇总、择优规则、不同配置的重试与费用汇总、完整计量口径均未定稿。角色推理记录无科研预注册字段。第十批的当前绑定选择规则及通用材料依赖语义仍待明确。

受信读取端口须提供元数据、来源及精确归属，未授权对象不进入后续读取。I-SCHEMA 注册两种服务持有类型；可信结构验证由服务调用，实际来源认证和委派装配由服务负责。真实执行、调用、发送、预算与结算留待相应工作包。

## 证据

- Ubuntu CPython 3.12.16 完整工程检查及构建通过，308 项测试通过。[日志](evidence/p1-2-batch11-verify.log)
- Windows CPython 3.12.14 在临时隔离环境同步同一锁，8 项专项测试及 Schema 检查通过。
- 两种记录各一组独立手列投影，经标准库 JSON 编码得出规范 UTF-8、计算完整 SHA-256。两侧逐项一致，两份生成物分别与仓库文件逐字节一致。[Ubuntu](evidence/p1-2-batch11-ubuntu.json) · [Windows](evidence/p1-2-batch11-windows.json)
- 专项覆盖多尝试、有执行成功但缺科研证据、错运行／版本／归属、未授权材料、同摘要换定位、错模型版本、跨调用重试、错用量归属、非 R07 费用来源及调用方入口拒绝。原九个金样例、手算、设计基线和锁文件无字节差异。
- [远端 CI 43456418793](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43456418793) 的实际 SHA 为 `863585f2a9cfcaedf13eb7107f1a0a3cb67f25d6`，最终为 completed / success。2026-11-13 15:49:13 UTC 开始，15:49:33 UTC 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43456418793/job/131991644477)的 Checkout、固定工具及 Python 安装、锁定检查和构建均通过。

## 验收整改

- 尝试结算先核 R07 元数据来源、项目归属和上一精确尝试修订，再读取 SettlementFacts 并沿用 apply_settlement 核验运行、结算定位及 settled／no_charge。错运行、修订、归属、pending、缺事实及非法终结结果均拒绝；错归属未读取结算正文。
- 运行守卫拒绝同一尝试重复或多个修订并列，保留输入原始事实。尝试历史汇总规则仍待明确。调用重试继续核对归属、精确修订、调用主体及请求，拒绝自引用和重复关联。内部尚无已定义的通用间接重试图合同，不据此推导链路或汇总。
- 调用费用引用仅核验 R07 来源和当前调用归属；是否必须引用最终结算仍待决定。空引用保持空值。真实委派、租约、元数据端口不预读正文继续留待服务验收。
- Ubuntu 3.12.16 完整检查 318 项与构建通过，Windows 3.12.14 同锁专项 18 项及生成物检查通过。两组向量及两份 Schema 与整改前逐字节一致。原九个金样例、手算、设计基线及锁文件原字节保留。

[完整日志](evidence/p1-2-batch11-remediation-verify.log) · [Ubuntu 向量](evidence/p1-2-batch11-remediation-ubuntu.json) · [Windows 向量](evidence/p1-2-batch11-remediation-windows.json)。整改 SHA 的远端 CI 待核验。
