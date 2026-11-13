# P1-2 第六批人工验收记录

状态：A0 已于 2026-11-13 签收，验收通过，范围仅限 P1-2 第六批固定四题纯契约的已交付及整改内容。以下复现记录保留供复核。第 6 节登记本轮整改、复验及远端 CI 结果。

## 1\. 批准依据与提交

* 第六批授权限定固定四题 Protocol、Prereg、独立 ExecutionBinding 与确定性 confirmation，要求核验实际内容、逐条解析引用、跨对象守卫与跨平台独立预期。
* [第五批签收](A0-P1-2-batch5-acceptance.md)为 `c378993cbbf19ff54452dc9165ed2cdfc59104d6`，范围是第五批交付和整改。[首组签收](A0-R02-first-contracts-checklist.md) §5–6 绑定提案 `48bd0dcc0afa78c2b6447fdfe789465b0d3a8068`，本批沿用其中 §1–6 的固定枚举、归属、科学字段与批准边界。[Q-04～Q-07 签收](A0-P1-2-Q04-Q07-checklist.md)在 `412e67e0586fe21837916111eefb89c9223f01fa`，绑定 `2ff34729510f02750f3d1ea7799adfbb55819db2`，本批沿用其批准冲突、历史证据分界及固定四题规则。设计参照大方案 §5.1、§5.2、§5.5、§6.9、§6.16、附录 C。
* 实际代码提交 `df85e6c00928ffdfdfc5463eb322c564c281009e`。检查时 Ubuntu HEAD 与 GitHub `main` 均为 `b8020d13574a09d8ff2ac0777061774d92693348`。该证据提交直接接续代码提交，仅更新 `docs/implementation/commit\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_log.md` 与 [第六批交付记录](../p1-2-batch6-delivery.md)，无产品代码、测试或 Schema 差异。

## 2\. 实际支持范围

|审查对象|已有支持及边界|
|-|-|
|解析与权限|`FixedFour.\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_read` 检查精确 locator、租户、项目、可读性、旧缺项、解析结果的归属；有类型目标重算摘要，工件另外调用受信端口。布尔就绪与无内容不能单独通过。类型域、夹具来源和嵌套记录仍见下节。|
|Protocol|数据与切分指向同一总体，固定四题集合与 required\_items 对齐，检查缺项策略及基线和 Scope 部分维度。投影保留批准表科学字段并排除批准定位及状态。UnitSpec 通过 MissingPolicy 间接绑定，四题单位键尚未与评价器核对。|
|Prereg|问题、族、选择历史保留实体 ID 与版本。匹配候选、历史、总体、阈值、Scope 及停止集合，投影包含选择／阈值科学条款并排除批准定位。历史与规则内容的覆盖有限。|
|ExecutionBinding / RunRequest|Binding 单向引用协议、工件和方法，报告及请求引用 Binding，无对象回指循环。确认投影包含锁定计划引用、Arm、模式、种子／确定性、工件及 Binding 的科学引用。直接工件字段与 Binding 两条路径均入哈希，正常路径先比对精确引用。预算、保护限制、sanity 定位、授权回执和签署元数据排除。|
|阶段入口|科学预映像可先于批准和锁定计算。锁定核验选择及阈值签署记录、修订歧义、撤销和摘要；运行守卫检查角色、任务、sanity 和锁定状态。协议和族签名条款缺失时，两条授权路径都明确阻断。尚无成功锁定、发放运行授权或实际启动的证据。|

## 3\. 本批整改及复验要求

以下复现以 `tests/contracts/test\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_batch6.py` 的 `Chain()` / `SyntheticReader` 为起点，每条使用新实例。行号对应代码提交。

### 1\. 受信端口、目标类型及正式版本域

* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L194) 允许构造时注入任意符合形状的端口。已复现 `FixedFour(CTX, c.reader).protocol(c.protocol, c.unit, basis\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_ref=c.basis)` 在默认模式返回版本，和夹具模式使用同样的 `SciencePreimage`。现有测试本身用该路径模拟生产合同。调用方 JSON 当前不能直接传入 Python 端口，这个复现表明现有服务接口没有隔离夹具与权威来源。整改时把夹具入口与受信服务装配分开，明确预览结果类型及使用边界，确保夹具端口或客户端就绪声明不能通过正式路径。补拒绝夹具和缺真实适用依据的反例。
* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L226) 的通用目标解析只按调用指定的形状校验，`\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_match` 只比较末段 SHA-256。以 UnitSpec 内容构造 `object\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_type=Unrelated`，`target(ref, FixedUnitSpec)` 成功。把当前 Binding 精确引用的版本前缀改成 `other:v9:`，保持摘要和正文并同步端口 locator，`confirmation` 仍产生新版本。整改时在目标注册中绑定类型、完整版本域和投影算法；保留未知规范明确阻断，补错类型和错算法版本测试。

### 2\. 权威记录校验及归属

* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L277) 公开 Protocol 入口先截取草稿字段，后续仅检查权威记录的归属和版本。已复现将合法草稿记录用 `model\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_copy` 更新为 `status=approved, approval\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_ref=None` 后，仍得到正确摘要。应在拆分前重新校验完整记录。预览仍可核算有效但尚未批准的科学内容。
* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L370) 统一要求记录项目等于当前项目。已复现同租户 `ownership\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_scope=tenant, project\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id=None` 的 Protocol，在 reader 的 `allowed\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_projects` 包含当前项目且提供现有适用依据时，Binding 被误拒。P1 已批准租户级复用并要求项目使用授权。整改时区分记录归属和项目使用资格；补已授权项目通过、未授权项目和跨租户拒绝，实际批准条款仍待审定。
* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L397) 主候选核验正文 ID、版本、归属和来源，族／历史中的其他候选只核算科学摘要。已复现给历史加入另一个同摘要候选 locator，其正文 `object\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id`、`tenant\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id`、`project\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id` 均不匹配，Prereg 仍生成预映像。整改时对每个原 locator 复用完整候选校验，覆盖正文错归属、错对象和不可读来源，再做任何合并。

### 3\. 固定四题的单位、历史、规则和方法

* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L287) 只检查总体及题集合、UnitSpec 与 MissingPolicy 的引用关系。已复现新 UnitSpec 的 `unit\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_key\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_fields=\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\["unrelated\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id"]`，把 MissingPolicy 指向该版本后 Protocol 仍生成摘要。按 Q-07 把受信数据中实际行的 `item\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_id`、UnitSpec、锁定总体和评价视图接通；补错键、数据 manifest 所声明总体与实际题集合不一致的反例。
* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L414) 的族和历史视图仅核对问题／族定位、主候选是否存在、测试暴露是否为空；分析、失败／重试、反馈规则在第 468 行仅走通用材料核验。用 `FailurePolicy` 正文 `{"opaque":"choose best attempt"}` 及匹配摘要，夹具端口仍使 Prereg 通过。整改时核验固定四题已明确的单次锁定评价、完整历史与候选／族匹配、尝试选择和反馈限制。缺尚未审定的完整目标结构、独立校准或适用依据时分对象明确阻断，不把可读内容或夹具描述当作批准规则。
* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L547) 和 [确认入口](../../../danus_ai/contracts/fixed_four.py#L587) 核对工件和方法版本，但确定性仅由请求布尔值和空种子声明。当前 CodeEvidence／MethodConfig 目标无独立确定性证明。整改时由受信方法／工件合同证明方法适用、确定性和锁定配置，未知明确阻断。对精确 Scope 补复验，确认其方法、基线、度量和数据与实际 Arm／Protocol 对应，缺映射仍阻断。

### 4\. Sanity 必需项与当前 Binding

* [fixed\_four.py](../../../danus_ai/contracts/fixed_four.py#L565) 只要求 profile 非空且 suite locator 相等，协议套件正文的必需项未参与比较。已复现套件仍含 `no-leak`，另建 profile 只要求 `unrelated` 时 Binding 仍生成版本。另在 [check\_sanity](../../../danus_ai/contracts/fixed_four.py#L649) 直接传入该新 Binding，保持请求和报告的旧 Binding locator，将报告 profile 改为新 profile，给 `unrelated=pass, no-leak=defect`，守卫返回成功。完整 admission 路径会先核对请求 Binding 的摘要，独立 sanity 守卫未复用这一步。整改时从协议与套件的受信版本确定必需检查集合，并从请求精确解析和重算 Binding，校验报告快照与适用例外。补漏必需项、套件必需项 defect、错 Binding 正文及批准过期反例。

### 5\. 规范化与逐条引用校验

* [Prereg 投影](../../../danus_ai/contracts/fixed_four.py#L475) 在投影前按带 locator 的原 Arm 字节去重，[Prereg 字段校验](../../../danus_ai/contracts/first_objects.py#L250) 也先以原 locator 比较同名 Arm。首组 §6.2 要求逐项验证，再按批准的科学投影判定同键冲突，并保留 Arm 顺序。补同名同科学内容但使用不同可读 locator、不可读第二 locator、同名不同科学版本三个测试，禁止用内容相等跳过权限。Run 的 [Arm 查找](../../../danus_ai/contracts/fixed_four.py#L618) 使用原始字符串。已复现将锁定 Arm 名改成 NFC `café`，用该值运行计算成功，换成等价 NFD `cafe + U+0301` 则报 `ARM\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_METHOD\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\_MISMATCH`。应对计划、授权任务和运行的局部 Arm ID 使用相同规范化策略，拒绝真正冲突并复验两种拼写。

### 6\. 补充证据覆盖

* 现有跨平台主链的预期可追溯至附录 C 和绑定字段表，测试独立列出四份预期对象并用标准库序列化 ASCII 预期字节。覆盖非空真实内容的模拟解析及七个拒绝案例，不能覆盖上述新复现。整改后在两侧增加错版本域、夹具隔离、租户级 Protocol、次要候选、单位／策略、方法和 sanity 必需项，补至少一组 NFC 等价输入及科学字段变更与预算隔离的独立字节预期。有效切分、非空调参和历史引用的组合也应有正反例。完整工程检查和对应代码提交 CI 随整改重跑。

## 4\. 验证证据

* [第六批交付记录](../p1-2-batch6-delivery.md)记录 Ubuntu CPython 3.12.16 完整工程检查，包括锁、Ruff、mypy、导入边界、Schema 和构建，220 项测试通过。本轮只读复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -B -m pytest -q -p no:cacheprovider`，实测 **220 passed**。另运行上节所列独立探针，既有测试通过与新增复现并存。
* 已有 Windows 原生 CPython 3.12.14 第六批测试 **12 passed**。本轮读取两侧保存的原始 JSON，对照[版本化跨平台证据](../evidence/p1-2-batch6-cross-platform.json)，逐项核实四份完整 UTF-8 字节与 SHA-256、七项拒绝标签、两份 Schema SHA-256 一致，并从保存的字节重算四份摘要。Windows 测试本轮沿用交付证据。相同锁内 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4；Python 补丁版本不同，结论限于已执行向量。原九个金样例及手算目录由 `git diff --exit-code 412e67e HEAD -- docs/implementation/p0-2/golden` 核实无字节差异。
* [GitHub Actions 运行 43318093230](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43318093230)经 API 核实为 `main` 手动触发，`completed / success`，实际完整 SHA 为 `df85e6c00928ffdfdfc5463eb322c564c281009e`。开始至完成更新 23 秒，[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43318093230/job/131531276420)的 Checkout、锁定工具与 Python 安装、工程检查和构建均成功。注解中唯一警告为固定 `actions/checkout` 使用的 Node.js 20 已弃用，runner 改用 Node.js 24 执行。Checkout 维护另行跟踪。

## 5\. 后续阶段与验收边界

* 未审定的协议使用、族确认、预算及数据等批准用途条款保持阻断。历史标记清除权限、跨 Scope 科研映射及采样／描述型启用按既有决定保留待决。本批整改可在既有批准的四题约束内完成；确实缺失的科学结构需列出受阻项。
* 真实签名来源、数据／Git／镜像和依赖材料、账户与委派、租约、预算、实际 sanity 执行、运行与恢复由对应权威服务阶段验收。第六批独立预映像不产生上述运行资格。
* 其余对象、模式、I-SCHEMA 全量调用两侧验证及其他金样例仍按 P1-2 跟踪。Linux 正式部署验收独立执行。本草稿仅覆盖第六批固定四题纯契约及其证据。

## 6\. 整改与复验证据

五组问题先以六个失败回归固化。修复后，目标类型／版本域与受信来源、权威 Protocol 和逐候选归属、单位键／尝试／独立确定性、Sanity 必需项和 Binding、Arm 逐条解析及 NFC 均已按测试复验。逐项依据、前后结果和保留边界见[交付记录第 5 节](../p1-2-batch6-delivery.md#5-第六批验收整改)。

Ubuntu 3.12.16 完整工程检查 229 项通过，Windows 3.12.14 第六批测试 21 项通过。两侧原始结果复算 7 个完整 SHA-256 和规范字节一致，原 7 项拒绝、9 组整改检查及 2 份 Schema 摘要一致。原九个金样例和手算记录字节一致。

未审定用途条款及科研映射等原边界保留。真实权威服务接入、完整历史、分析校准及正式运行仍待对应阶段。

GitHub Actions [运行 43323478957](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43323478957) 在 `main` 手动触发，结果为 **Success**。实际运行 SHA 为 `b2e2fb93eb9a5823d9ba313ff64c163071133daf`，与第六批整改提交一致。从运行开始到完成更新为 26 秒。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43323478957/job/131549915158)的锁定检查与构建通过。Checkout 成功，唯一警告为固定的 `actions/checkout` 使用已弃用的 Node.js 20，runner 改用 Node.js 24 执行。

## A0 本人填写

确认人：Jack\_Wang

日期：2026.11.13

意见：已审阅第六批交付及五组整改记录。Ubuntu 229 项、Windows 21 项测试通过，已执行的跨平台规范字节、摘要及拒绝结果一致。整改 CI 对应提交 b2e2fb93eb9a5823d9ba313ff64c163071133daf，运行成功，同意本批固定四题纯契约已交付及整改范围验收通过。跨平台结论限于实际测试版本与向量。未审定批准条款、科研映射、完整历史、分析校准及其他契约缺项继续跟踪；真实权威服务和正式运行按对应阶段验收。Checkout 运行时警告保留为维护项。

收结论：通过（仅限 P1-2 第六批已交付及整改范围）

