# P1-2 第九批账户、个人租户与项目归属

基线为第八批限定签收 `126095ae4e8fc806559cbfc209e66aa8ef9b8501`。依据大方案 §1.1、§5.1–5.2、附录 A.1，开发指南 §3.4／§5.3 及字段台账，沿用首组 P1 归属和精确引用决定。人工验收另行登记。

| 字段 | 来源与写入方 | 版本及可空约束 |
| --- | --- | --- |
| 三种记录的 locator | 大方案 §5.1 与台账对象 ID，控制服务 | 必填非空，含记录类型、ID 和精确修订，无科研内容 ID |
| PersonalAccount.login_subject | 台账 PersonalAccount，控制服务 | 必填非空，随账户修订。实际登录标识规范和认证映射留待服务 |
| PersonalAccount.personal_tenant_ref | 大方案 §5.1 一账户一租户，控制服务 | 必填非空，精确定位租户，与反向定位相符 |
| PersonalTenant.owner_account_ref | 大方案 §5.1，控制服务 | 必填非空，精确定位账户 |
| Project.tenant_ref | 大方案 §5.1，控制服务 | 必填非空，精确定位租户，允许同租户多个项目 |
| OwnershipUnclaimed.status、locator | 大方案 §5.2 旧记录待认领，控制服务 | 必填非空，固定状态及原记录精确定位，与科研缺项只读视图区分 |

委派和读取入口核验权威关系及当前精确修订。关系核验通过后继续检查当前委派、租约、操作及目标范围。引用端口只解析归属和可读元数据。三种记录以服务持有类型注册，可信解析仅验证结构。跨项目授权和真实认领流程保留既有边界。

## 验证

- Ubuntu CPython 3.12.16 完整工程检查与构建通过，285 项测试通过。[日志](evidence/p1-2-batch9-verify.log)
- Windows CPython 3.12.14 在既有原锁隔离环境执行第九批 13 项及 Schema 检查，均通过。两侧 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4、pytest 9.2.0。
- 三种记录各有一组手列投影，独立标准库 JSON 得出预期规范 UTF-8 与 SHA-256。两侧向量一致，两份生成物在两侧分别与仓库文件逐字节一致。[Ubuntu](evidence/p1-2-batch9-ubuntu.json) · [Windows](evidence/p1-2-batch9-windows.json)
- 专项覆盖两租户三项目、关系错配、错修订、缺关系、委派越项目及越目标、同 ID／哈希跨租户拒绝、服务与调用方解析入口、旧记录两种状态。关系和委派失败先于目标元数据解析，跨租户目标在元数据阶段拒绝。原九个金样例、手算记录、设计基线及锁文件无字节差异。
- [远端 CI 43379368621](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43379368621) 在 main 手动触发，GitHub API 核实实际 SHA 为 `8a379647cc10a2d601c8fff78d611b80397bc6fd`，最终为 completed / success。2026-11-13 06:32:07 UTC 开始，06:32:34 UTC 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43379368621/job/131733291615)的 Checkout、固定工具与 Python 安装、锁定检查及构建均通过。

## 验收整改

- 委派授权从受信端口读取对应精确委派修订的签发归属事实，核对当前账户、租户及项目修订。缺事实返回 DELEGATION_ISSUANCE_FACTS_REQUIRED，错修订阻断。旧快照和同一旧委派的重新授权均在目标元数据读取前失败。合成端口提供合法新签发事实后，授权和读取均通过。签发事实仅在内部只读端口传递，公开载荷和 Schema 无变化。真实签发、续签及如何保存不可改写的签发依据留待服务合同；缺已批准规则时保持阻断。
- 两租户三项目各验证完整授权和引用读取、跨项目拒绝、同 ID／同哈希跨租户拒绝及目标错修订。测试端口设正文读取哨兵。真实适配器必须保持元数据和正文读取分离。
- LegacyIncomplete 仍兼容空归属结构，空归属与待认领状态均不能通过业务读取，且不会按当前上下文补齐。普通入口拒绝载荷内 trusted 字段，真实适配器负责认证和受信调用边界。
- Ubuntu 3.12.16 完整检查与构建通过，288 项测试通过。Windows 3.12.14 同锁专项 16 项和生成物检查通过。三组独立向量及两份 Schema 两侧一致，且与整改前输出相同。原九个金样例、手算、设计基线与锁文件保持原字节。[Ubuntu 日志](evidence/p1-2-batch9-remediation-verify.log) · [Ubuntu 向量](evidence/p1-2-batch9-remediation-ubuntu.json) · [Windows 向量](evidence/p1-2-batch9-remediation-windows.json)
- [整改 CI 43381229894](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43381229894) 在 main 手动触发。GitHub API 核实实际 SHA 为 `c1b20305eeb8d48fda60cea88a9c6dfbff0ed9c9`，最终为 completed / success。2026-11-13 06:48:11 UTC 开始，06:48:38 UTC 更新为完成。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43381229894/job/131739210479)的 Checkout、固定工具与 Python 安装、锁定检查及构建均通过。
