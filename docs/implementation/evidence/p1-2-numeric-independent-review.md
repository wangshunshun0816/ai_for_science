# 数字性质与固定枚举结果独立复核

交付提交 〈835263bdae9a7d42962fd42f8d9faa0f41885104〉。2026-11-18 从 Ubuntu 本地 HEAD 和远端 main 独立核对。复核依据为大方案 §5.1、§6.4、§6.16、附录 C.2–C.5、Q-07 A 与原固定四题手算。受信端口均为合成事实。

## CI 与本地证据

该提交已在 GitHub main。公开工作流列表最新显示 44127201891，运行摘要为成功，实际 SHA 为 775ca649d3b003c32d5b3751f8252bc2ecf1862f，属于此前失效证据整改。按数字交付 SHA 查询 Checks API 返回 HTTP 403（公开访问限流）。本次尚未核实对应运行、实际运行 SHA、最终结果、关键步骤结果或详细日志。旧运行仅用于排除误认。[工作流列表](https://github.com/wangshunshun0816/ai_for_science/actions/workflows/ci.yml?branch=main) · [旧运行](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44127201891)

提交内的配置仅有手动触发。配置步骤包括 checkout、安装固定 uv、安装 CPython 3.12.16，以及运行 verify.sh。脚本配置了锁定安装、Ruff、mypy、导入边界、Schema、默认 pytest 和发行构建。工作流未设置 DANUS_P13_TEST。这些是配置证据。[工作流](../../../.github/workflows/ci.yml) · [脚本](../../../scripts/verify.sh)

Ubuntu 在既有锁定环境中使用 .venv/bin/python -m pytest --collect-only -q -p no:cacheprovider 默认收集 626 项，其中数字专项 15 项。指定 tests/contracts/test_numeric_results.py 的复跑为 15 项通过；无路径参数的默认复跑为 608 通过、18 跳过，跳过项为 SQLite 专项。本轮没有新增存储证据。此前 Windows 3.12.14 和 Ubuntu 3.12.16 的字节、摘要与 Schema 证据继续引用原文件，本轮在 Ubuntu 复跑 23 组，Windows 证据未重跑。[专项](../../../tests/contracts/test_numeric_results.py) · [跨平台证据](p1-2-numeric-cross-platform.json)

## 已复现缺陷

| 编号 | 入口与依据 | 独立反例及结果 | 整改与复验 |
| --- | --- | --- | --- |
| N-R01 | [固定结果读取顺序](../../../danus_ai/contracts/numeric_results.py#L305)。受限证据须先授权。 | 用 Reader 与 fixed("positive", r) 构造合法比较，保留聚合分析授权，只将 r.denied 置为 r.lock.method.attempt_ref。入口最终拒绝 NUMERIC_REFERENCE_UNAVAILABLE，但 r.reads 为 ["version", "body"]，已读取聚合中该尝试的四条观测。拒绝整个分析引用的对照为零次读取；授权齐备时原结果通过。 | 在读取包含受限观测的聚合快照或正文前，依据独立锁定元数据核验两臂所需读取权。复验基线／方法的运行或尝试授权撤销、越权时零次受限读取；保留合法计算、接收复算及锁定和正文一致性守卫。 |
| N-R02 | [外部报告来源结构](../../../danus_ai/contracts/numeric_results.py#L55)、[来源解引用](../../../danus_ai/contracts/numeric_results.py#L214)。大方案 §5.1、§6.16 要求绑定实际原文位置。 | 用 numeric("external_reported", "R03", fields, Reader()) 将 fields.source.snapshot_ref 从 sci("SourceSnapshot") 换成 sci("RunRequest")，位置保留 section / Table 2，合成版本锚点与来源事实分别匹配这一输入。结果为 source_verified。合法 SourceSnapshot 对照通过；只改位置并保留原来源事实会被拒绝。 | 核验精确引用确为适用原文及位置。若缺已定来源类型或适用映射，明确阻断该路径。用依然具备正确摘要和当前授权的非原文对象重验，保留合法来源对照。本反例证明入口接受错误类型，真实端口的来源认证留待服务验收。 |

## 通过的对照与待补证据

- 需求和设计默认值各核对独立决定投影，意义阈值另走已定精确批准。估价经既有报价入口，并有其不能作为效应的反例。实测要求 R11 权威写入及精确 RunRequest／Analysis。外部报告定位及参考推导的输入列表纳入独立来源事实对比。四类非实测投影被修改为 measured 且同步替换来源事实时，旧锚点使其返回 NUMERIC_BODY_MISMATCH。将合成锚点改成匹配新正文、保留原写入方后，返回 NUMERIC_SOURCE_WRITER_MISMATCH。合法实测与四类原性质对照通过。错单位、错版本、模型自报实测、估价作为效应及推导输入不一致的现有反例随专项通过。通用决定分类、原文类型及原文位置的证据、通用推导依据的真实性仍需对应目标规范及可信来源；合成端口无法验证真实供应方是否以回显生成事实。
- 原手算四题的合格比较在 Decimal 全局精度局部设为 1 时仍得基线 0.5、方法 0.75、效应 0.25；有限否定仍得 0.5、0.5、0。接收方篡改 effect 为 0.2 返回 FIXED_REPORTED_RESULT_MISMATCH。另用独立标准库重算批准条款及签名主体摘要，锁定阈值分别取 0.24999999999999999999999、0.25、0.25000000000000000000001。第一例通过为 improvement，等于和高于效应的非零分支均明确拒绝 FIXED_OUTCOME_SPEC_UNRESOLVED。重复行按原策略计一次，冲突为 invalid，缺题为 incomplete 且无分数。分母恒为四，区间和 p 值均为空且有不适用理由。结果有效及来源核验不授予科研接受资格。
- 23 组预期包含五类性质各三组、固定四题两类各三组、既有报价两组。输入与输出预期由固定输入、原手算字段和第十四批已固定报价文本组成。受测规范化输出与标准库排序 JSON 对照，摘要以标准库对预期 UTF-8 计算。固定结果预期的 analysis_ref 取自已解析查询定位，其他比较覆盖固定原始输入及输出数值。此引用字段可在后续把期望取自手列定位，增强该字段的独立性。两份 Schema 的摘要是生成物对照证据，未作为 23 组手算向量计数。
- 待补的覆盖包括逐类错权威依据的综合反例、外部原文类型／位置策略和完整推导契约。当前结果只覆盖固定四题已有两个结论及拒绝分支。通用统计、抽样、负效应、非零阈值未达到分支的结论规则、真实适配器及 G0/G1/G2 保持原边界。

## 远端 CI 补充核验

收到本次运行链接后，公开运行摘要确认手动触发的 44236133594 绑定 `835263bdae9a7d42962fd42f8d9faa0f41885104`，最终为 Success。公开作业 134572594081 的七个步骤都显示成功，包括 Set up job、Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build、Post Checkout 与 Complete job。摘要有 checkout 目标 Node.js 20 已弃用、实际强制在 Node.js 24 运行的警告。[运行摘要](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44236133594) · [作业及步骤](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44236133594/job/134572594081)

未取得详细日志。作业页面给出的检查构建步骤日志返回 HTTP 404，公开日志 API 返回 HTTP 403（限流）。由对应 SHA 的 verify.sh 可验证该成功步骤配置运行默认 pytest 及构建；远端未逐项核验数字专项名称、测试数量、SQLite 跳过数或构建输出。SQLite 专项未启用，本轮无新增存储证据。本地收集 15 项数字专项以及 608 通过、18 跳过的实测证据见上文。N-R01、N-R02 仍待整改。

## N-R01、N-R02 整改与复验

整改前在 Ubuntu 定向运行首批 25 个回归参数，22 个失败、3 个通过。18 个失败显示拒绝前仍发生 version 与 body 读取，4 个显示错误外部来源或缺适用证据时未阻断。聚合整体拒绝的两个入口与原文错版的对照原先即通过。原复现记录保留于上文。

- N-R01：先核验精确聚合分析引用，再核验独立 R06 锁定元数据的当前读取权限。仅取得允许读取且精确定位、归属匹配的锁定事实后，按该事实逐一核验两臂运行与尝试、预注册、策略和阈值批准。随后才读取聚合锚点与正文，并比较正文两臂绑定与锁定事实。计算和接收复算均验证聚合或锁定元数据被拒绝、两臂的运行及尝试被拒绝、委派撤销或恰到期、锁定错修订或错归属、锁定缺失。每条拒绝均断言零次聚合锚点和正文读取；聚合或锁定元数据授权拒绝也断言零次锁定事实读取。独立锁定与已授权正文不一致的旧反例继续拒绝。
- N-R02：仅在 external_reported 分支要求已有 SourceSnapshot 目标及其精确科学版本。源引用授权与精确解析通过后，独立原文端口按该快照返回适用位置，再精确核对整条 SourceRef。摘要、权威投影和读取权限可匹配的 RunRequest 仍拒绝。合法原文通过，错版、越权、位置不适用、缺位置事实及另一版本的位置事实拒绝。越权及错版不会调用位置事实读取端口。

Ubuntu CPython 3.12.16 的 scripts/verify.sh 完整通过，包含锁定安装、静态检查、导入边界、两份生成物、默认测试 636 通过和 18 项 SQLite 专项跳过，以及源码包和 wheel 构建。Windows CPython 3.12.14 使用同一 uv.lock 离线同步的隔离环境，数字专项 43 项通过，Schema 检查通过。两边均运行 independent_vectors，并对 23 组结果逐项核验独立 UTF-8 预期和完整 SHA-256，与既有跨平台记录逐项比对长度及摘要。两端完整输出（含两份 Schema 摘要）排序 JSON 的 SHA-256 同为 c2f86f18023c6d24b48dc83291281101fe3cb175b4533345f12eb6ec67765a8a。两份 Schema 分别通过本地逐字节生成物检查，文件及 uv.lock 无差异。原九个金样例、手算和设计基线字节无差异。

兼容边界：请求或输出结构与 Schema 字节沿用现有版本；数字读取端口新增锁定元数据授权和独立原文位置查验，接入方需要提供对应的受信事实。缺事实的分支显式拒绝。真实适配器的认证、当前权限与原文事实来源仍属服务验收。CI 44236133594 仅覆盖原交付 SHA 835263bdae9a7d42962fd42f8d9faa0f41885104，整改 CI 待新运行核验。本轮没有新增存储验证。
