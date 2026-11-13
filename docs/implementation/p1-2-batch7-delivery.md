# P1-2 第七批交付记录

起点 `8e4116041114c1954c2209cbf689f6eb6d66eb84`，第六批固定四题限定签收。依据开发指南 §3.4、§5.3，大方案 §5.1、§6.4、§6.21、§6.25 与附录 A，以及角色规格 §3.3、§4、§5.1。沿用首组已批准的精确引用与归属，以及 Q-06 状态与权威边界。

| 交付 | 纯契约验收范围 |
| --- | --- |
| planning | ResearchTask 草稿与激活后快照分离；计划和修订、节点及合同形状；NFC 节点标识、重复与悬空依赖、无环图、精确活动修订、委派、项目归属、资格及根预算；节点资格事实绑定已核对的计划正文。估价用于可行性检查。 |
| context | R14 权威清单与版本、授权视图和构建策略绑定；核对可信输入清单、估算、容量和输出预留、必需约束保留、摘要来源及失效；合法恢复与 A7 新审计冷启动分开。 |
| role_outputs | A1 策略、A2 探索、A3 协议、A4 分析、A5 实现、A7 审计、A12 文稿最小输出；使用严格角色分派和现有业务草稿。拒绝自报权威字段。交接绑定根任务、活动计划、收发合同、租约、原任务计数、已有运行及待结费用；接收者重新核验当前授权、工件、嵌套输出引用及反馈白名单。 |
| I-SCHEMA | 注册调用草稿及服务记录，从同一模型导出 JSON Schema/OpenAPI。声明纯守卫、运行时条件及对象覆盖。本批的规范字节和完整 SHA-256 用于序列化验证。 |

受信读端口的装配由下游权威服务负责。测试使用明确标记的合成端口，无生产 task_kind 或角色资格。未知任务种类、缺资格／启用、未验证目标合同、数据可见性与授权证据均阻断；完整角色工件（包括 ClaimSubmission、EvidenceSnapshot、数值宏和完整 Sanity 契约）依赖权威来源。语义性提示注入、实际敏感信息过滤和文本事实质量属 R14/R09 与角色评测，本批检查清单污染、归属及越权引用。任务阶段、角色互斥、预算／数据／权限政策与实际可见性由受信事实提供，实际启用范围及派生配置沿用待办。调度、原子 CAS、仓储及模型调用按后续阶段验收。

## 实测证据

Ubuntu CPython 3.12.16 运行 `bash scripts/verify.sh`，253 项通过，锁定安装、Ruff、mypy、导入边界、Schema 漂移及源码包、wheel 构建通过。Windows 原生 CPython 3.12.14 在 `%TEMP%\danus-r02-batch7` 以原锁创建隔离环境，运行 `python -B -m pytest -q -p no:cacheprovider <repo>\tests\contracts\test_batch7.py`，24 项通过。原环境缺少可用 venv，按原锁重建；pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4。无项目依赖变更。

两侧用 `python -B tests/contracts/test_batch7.py` 生成向量。3 份规范字节及完整 SHA-256、15 个计划及上下文拒绝场景、两份 Schema 摘要相同，并执行交接、七角色形状和权限检查。计划及探索输出的期望字段独立手列，NFC／换行以显式字面量定义，再使用 Python 标准库按受限向量编码。原九个金样例及手算相对 `412e67e` 无字节差异。[Ubuntu 输出](evidence/p1-2-batch7-ubuntu.json) · [Windows 输出](evidence/p1-2-batch7-windows.json)

GitHub Actions [运行 43351115237](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43351115237) 在 `main` 手动触发，已完成，结果为 **Success**。实际运行 SHA 为 `e5188d22d0c47e5845d1b5ea853dba98535134ba`，与第七批交付提交一致。从运行开始到完成更新用时 28 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43351115237/job/131642134859)的锁定工具和 Python 安装、完整工程检查及构建均成功。Checkout 成功，唯一警告是固定的 `actions/checkout` 使用已弃用的 Node.js 20，runner 改用 Node.js 24 执行。A0 人工验收待签收。


## 验收整改

先在交付基线固定八个失败回归，运行 `pytest -q -p no:cacheprovider tests/contracts/test_batch7.py -k remediation`，八项均失败。整改证据见[复现日志](evidence/p1-2-batch7-remediation-before.log)。

| 事项与依据 | 复现与复验结果 |
| --- | --- |
| 任务／计划，大方案 §5.1／§5.3／§6.25、附录 A | 草稿带活动快照、空修订授权及 A2 调用服务校验均已阻断。纯形状仍可由角色提交；服务预检绑定 R16、实际主体、根任务和操作委派，激活预检还要求与权威一致的授权定位。生成 Schema 同步快照有无的条件，定位相等与实际权限继续运行时核验。 |
| 接收授权，角色规格 §5.1、TC-PLAN-03 | 无当前预算、错根或节点、委派替换均拒绝。接收核对同根预算与生效状态、双方任务节点与精确合同、当前计划、接收用途、委派与授权目标。测试覆盖 A2→A4、A4→A5、A7→A4／A5 和错版／错角色。 |
| A7 冷启动，角色规格 §3.3／§4.6 | 原输入来源可挂旧 ContextManifest。现在检查输入、直接来源与受信谱系，阻断旧上下文、缺谱系与循环，允许合法原始证据。恢复另要求前序上下文归于同一任务。 |
| 角色输出，角色规格 §4.6／§5.1 | 未审阅自由文本替换、嵌套的同族确认反馈和矛盾审计结论均拒绝。自由文本与已审核接收视图逐字段匹配，结构化来源检查可见性和反馈族。严重度的最小判别是阻断／非阻断，具体细分量表随审计规范决定。 |
| Schema 和向量，开发指南 §3.4／§5.3 | 两份生成物声明激活预检无写操作及接收视图要求。ContextManifest 与 Handoff 新增手列字段预期，标准库独立编码，接收正反例和既有向量在两侧执行。 |

生产审阅／过滤服务的权威来源、敏感文本和语义注入识别、工件完整谱系及预算／权限来源仍由对应服务验收。授权定位类型细分、审计严重度细分以及合法恢复的业务同一性粒度如需扩展，按后续具体合同定稿。仓储、调度和原子 CAS 属后续工作。A0 待签收。

Ubuntu 3.12.16 执行 `bash scripts/verify.sh`，267 项测试通过，锁定安装、静态检查、导入边界、Schema 检查和构建成功。Windows 3.12.14 使用 `%TEMP%/danus-r02-batch7-remediation` 原锁隔离环境，第七批 38 项通过。两侧执行 `python -B tests/contracts/test_batch7.py`，5 份规范 UTF-8 字节和完整 SHA-256、15 个原计划／上下文拒绝及两份 Schema 摘要相同，新增路径在两侧复验。原九个金样例和手算记录相对 `412e67e` 无字节差异。[Ubuntu 检查](evidence/p1-2-batch7-remediation-verify.log) · [Ubuntu 向量](evidence/p1-2-batch7-remediation-ubuntu.json) · [Windows 向量](evidence/p1-2-batch7-remediation-windows.json)

GitHub Actions [整改运行 43354232528](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43354232528) 在 `main` 手动触发，结果为 **Success**。实际运行 SHA 为 `89c25da8cd9efe50e0509912ce3b06efd6ac26bf`，与第七批整改提交一致。从运行开始到完成更新用时 24 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43354232528/job/131652295785)的锁定检查和构建通过。Checkout 成功，唯一警告是固定的 `actions/checkout` 使用已弃用的 Node.js 20，runner 改用 Node.js 24 执行。
