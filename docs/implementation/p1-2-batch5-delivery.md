# P1-2 第五批交付

## 依据与范围

开工时本地 HEAD、origin/main 与 GitHub main 均为第四批签收提交 `14162515f2a4ac5c55cd122e06e18a843291dff1`，工作区干净。依据 AGENTS.md、开发指南 §3.4／§5.3、大方案 §5.1／§5.5／§6.4 和附录 A.1，以及 [首组批准](decisions/A0-R02-first-contracts-checklist.md)、[Q-04～Q-07 批准](decisions/A0-P1-2-Q04-Q07-checklist.md)及本批授权。第四批为限定范围通过，第五批人工验收待 A0。

| 项目 | 已实现与验证 | 仍受阻 |
| --- | --- | --- |
| Scope | `contracts/scope.py`。显式 known、unknown、not_applicable，正整数闭区间、集合和精确引用分别比较。三值结果禁止隐式布尔转换。采样比较跳过观察集相交要求，仍核对同设计、总体、方法、基线、估计目标、单位、测量语义和其他范围条件。不同总体／抽样框／选择规则未映射时返回 unknown，测试覆盖真／假／未知和不同样本可比 | 尚无已批准的跨对象科研映射，当前入口不解析映射。Scope 结构及比较并不启用采样、描述型研究或生成 Scope 正式内容 ID |
| 身份与消息 | `contracts/messages.py`。限定项目级受信上下文、委派定位、租约、用途、期限、撤销核验，转接既有 RequestContext。请求和响应共享类型。测试伪造身份、跨租户同哈希、错版本、过期委派和租约。legacy_incomplete 可按已知归属和精确定位读取缺项元数据，科学引用及内容 ID 守卫拒绝 | 认证、当前租约的来源、真实读端口、幂等存储与未知归属记录的管理认领仍属后续阶段 |
| I-SCHEMA | `contracts/api.py` 及包入口提供七函数。首批注册按调用方、服务持有和仅输出区分。现有候选／论断版本进入 content_id，任务／尝试／结算／重试／更正／工程状态已有守卫可经统一入口验证。未知类型、外部自报权威合同及未支持操作拒绝。两侧示例使用同一 ReferenceRequest。 `scripts/export_r02_schema.py` 从注册类型生成 JSON Schema 与 OpenAPI 3.1 组件，verify.sh 检查漂移 | 组件包无 HTTP 路由。ResearchTask 完整记录、TaskPlan、SanityReport、ContextManifest、角色输出及其他未实现对象未注册，不能宣称全量契约完成。签名和发布回执仍使用专用纯契约入口 |
| 固定枚举 Protocol | `contracts/protocol_targets.py`。补 UnitSpec、MissingPolicy、SelectionRule 的固定枚举子集、版本引用配对，以及已批准的去重策略。预览投影按首组字段表输出规范字节，校验缺失策略、单位与规则配对。独立向量覆盖集合去重、顺序、精确小数及 CRLF | 正式 ID 继续阻塞。须补齐真实数据／切分与四题总体、单位键与缺失规则版本、选择规则全文和独立参考、指标实现、基线、适用模板、套件，以及可信只读解析和审核资格。Prereg、RunRequest、ExecutionBinding 仍缺完整投影 |
| 保留阻断 | 历史标记清除仍待 A0 决定。其他批准用途缺少已审定条款结构时继续阻断 | 真实身份服务、生产密钥、运行恢复、发布和科研评测按既有节点验收 |

## 可复现证据

Ubuntu 在 CPython 3.12.16 下执行 `bash scripts/verify.sh`，**200 项测试通过**。锁定安装、Ruff、mypy、导入边界、Schema 漂移检查、源码包与 wheel 构建通过。用 `uv run --no-sync python -B tests/contracts/test_batch5.py` 导出该侧向量结果。原九个金样例、手算 README 与三份设计基线逐字节一致。

Windows 原生验证环境位于 `%TEMP%\danus-r02-batch5`，使用现有 uv 0.12.7，`UV_PYTHON_INSTALL_DIR`、`UV_CACHE_DIR` 和 `UV_PROJECT_ENVIRONMENT` 分别指向其中的 `python`、`uv-cache` 和 `venv`。该 uv 发行索引对 `uv python install 3.12.16 --no-bin` 返回无 Windows x64 下载。按授权改用 `uv python install 3.12.14 --no-bin` 安装实际可用的 CPython **3.12.14**。再用 `uv sync --project <WSL-UNC checkout> --locked --no-install-project --python <native python.exe>` 安装同一锁内依赖。Windows Python 从 UNC 读同一代码和输入，`PYTHONPATH=<WSL-UNC checkout>`，工作目录及输出在 Windows 临时目录。

- `<venv>\Scripts\python.exe -B <WSL-UNC checkout>\tests\contracts\test_batch5.py` 输出向量。
- `<venv>\Scripts\python.exe -B -m pytest -q -p no:cacheprovider <...>\test_canonicalization.py <...>\test_batch5.py`，**75 项通过**，范围为规范化和第五批纯契约。
- 逐项比较两侧实际规范 UTF-8 十六进制及完整 SHA-256：**28 项一致**，**2 项非法输入均拒绝**。两个导出 Schema 的 SHA-256 一致。输入为既有 RFC 8785 附录 B 向量和新增手工固定的规范化、候选、论断、Protocol 预览向量。此证据适用于所测 3.12.14／3.12.16 组合。
- 两侧 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4 一致。新增运行环境为 PSF 许可下的 CPython 3.12.14，用于原生 Windows 对照。项目依赖及锁文件未增加条目，Windows 安装仅取锁中适用的平台项。D 盘项目归档未用作验证环境。

[Ubuntu 验证日志](evidence/p1-2-batch5-verify.log) · [Windows/Linux 向量实测](evidence/p1-2-batch5-cross-platform.json) · [保留文件字节核对](evidence/p1-2-batch5-preservation.txt)

第五批远端 CI [运行 43261216047](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43261216047) 由 `workflow_dispatch` 触发，已完成，结果为 **Success**，总用时 25 秒。GitHub 运行页指向 `4cbc58651fc88489d510201263b2538611ee0e76`，与第五批交付提交一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43261216047/job/131332722045) 的 `Locked local checks and build` 步骤成功。`actions/checkout` 仍有 Node.js 20 弃用警告，runner 使用 Node.js 24 执行，Checkout 成功。

## 第五批验收整改

整改基线 `7fac273dfc82bb83040beff5f0f6fa84caed8474`。先保留五个用例，在整改前分别复现 Scope 全不适用、采样维度跳过、无范围委派入口、候选错版和导出能力缺失。[整改前复现日志](evidence/p1-2-batch5-remediation-before.log)

| 项目 | 修复及复验 |
| --- | --- |
| Scope | 大方案 §5.5 的实际观察、任务、估计目标、目标总体、单位、方法与测量语义只接受 known 或 unknown。比较型需要基线，采样型需要抽样框及选择机制；这些维度填 N/A 拒绝。显式未知传播为 unknown，已知冲突仍为 false。非比较型可明确说明基线不适用，已确认同一目标及其他条件的不同样本仍可比 |
| 委派 | 经验证的授权保留原任务、用途、委派及租约定位、有效期、一个明确操作和精确目标列表。实际引用查询重新从受信端口读取委派及当前租约，核对操作、目标、用途、当前时刻及撤销。过期、撤销、无当前租约或同项目越范围请求在读取目标前拒绝；随后复用既有精确版本、归属和旧缺项守卫 |
| 内容 ID | 候选草稿计算版本。权威候选调用 validate_candidate_version 核对存储版本，错版返回 VERSION_MISMATCH。独立规范字节导出的版本用于权威正例，保留错存储版本反例 |
| Schema | JSON Schema 和 OpenAPI 共享 x-r02-capabilities，声明调用方、服务持有、仅输出及支持的操作／内容 ID 模式，未列能力视为不支持。标准 Schema 编码响应状态的 error／result_ref 条件及 Scope 的研究类型适用性。重复键、跨字段区间顺序、可信来源、实际权限和版本守卫仍由运行时执行，生成物显式说明。测试逐合同核对入口边界并检查生成可重复 |

Ubuntu CPython 3.12.16 执行 `bash scripts/verify.sh`，**208 项通过**，锁检查、静态检查、导入边界、Schema 漂移、源码包和 wheel 均成功。Windows 沿用 `%TEMP%\danus-r02-batch5` 的原生 3.12.14 及原锁，运行 `python -B -m pytest -q -p no:cacheprovider <...>\test_canonicalization.py <...>\test_batch5.py`，**83 项通过**。两侧继续用 `python -B tests/contracts/test_batch5.py` 输出向量，Ubuntu 经 `uv run --no-sync`，Windows 经隔离环境解释器及 UNC 源码路径。

**32 项规范 UTF-8 字节和完整 SHA-256 逐项一致**，包括既有 28 项和新增 Scope、委派读取、权威候选版本、Schema 能力四项独立预期。原两项 RFC 非法向量均被拒绝。整改守卫反例也在两侧报告过程中执行，单独登记。两个 Schema 摘要一致。原九个金样例与手算逐字节一致，依赖锁无新增条目。[整改工程日志](evidence/p1-2-batch5-remediation-verify.log) · [整改跨平台证据](evidence/p1-2-batch5-remediation-cross-platform.json)

正式 Protocol ID、未经批准的科研映射、历史标记清除及缺已审定条款的批准用途继续阻断。真实委派和租约来源仍属后续服务验收。

整改 CI [运行 43308363032](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43308363032) 已完成，结果为 **Success**，总用时 20 秒。实际运行 SHA 为 `cd70f2091d16d1f31f83dad268d323176dc9e88c`，与整改提交一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43308363032/job/131497540836) 的 `Locked local checks and build` 步骤成功。`actions/checkout` 有 Node.js 20 弃用警告，由 runner 使用 Node.js 24 执行，Checkout 成功。
