# P1-2 B 组：R08c 历史实际接触事实

## 设计依据与已定字段

大方案 §5.1、§6.4、§6.13 定义 R08c 暴露台账、首次实际接触和租户／项目／主体／用途／不可变数据版本的绑定。开发指南 §3.4、§3.13（R08c 模块卡）、§5.3 规定 R02 统一合同出口和 I-DATA 接口。沿用已签收的精确引用、同项目权限、当前委派及独立权威快照规则。见[字段台账](r02-field-matrix.md#dataexposure)、[第九批归属验收](decisions/A0-P1-2-batch9-acceptance.md)、[第十五批数据边界验收](decisions/A0-P1-2-batch15-acceptance.md)。

所有下列合同字段为必填单值，无列表或默认值。公共、跨项目可见性及通用暴露报告集合未在本批定义。

| 字段 | 写入方、版本与语义 |
| --- | --- |
| 查询 subject | 调用方填写历史定位及核对值。当前读者、当前读取用途、权限和租户／项目由服务侧受信上下文和委派核验。 |
| subject.event_ref | R08c 事实定位，使用 DataExposure 记录类型、ID 和精确修订。查询回显该定位仅作选择条件。§6.13 与既有 RecordLocator。 |
| subject.data_ref | R08c 记录实际接触的 Dataset 精确科学版本。必须校验当前委派内的同项目引用。§6.13。 |
| subject.principal_id | R08c 记录实际接触主体。与当前查询者分开；不推定为发送接收方。§6.13。 |
| subject.purpose | R08c 精确历史用途标签，仅作相等比较；用途映射和通用枚举待明确。当前查询用途由可信入口独立提供并经委派核验。§6.13。 |
| tenant_id、project_id | R08c 事实归属，查询端不能填写。与当前受信归属和独立权威快照逐项一致。§6.13。 |
| exposed_at | R08c 已记账的实际接触时间，使用现有 UTC 时间格式，不晚于核验时点。§6.13。 |
| status、event_ref | 仅输出核验结果及精确事件定位，取值仅为 historical_contact_verified。该结果不具备批准、许可、当前数据访问或再次发送的载荷结构。 |
| 独立权威版本快照 | 受信只读端口在授权后读取 R08c 台账的精确绑定及快照。受限事实缺失时阻断；无实际接触的独立事实允许 contact 为空，以拒绝排队状态。事实正文在另一条读取路径核验。 |

## 正式入口与证据

[语义入口](../../danus_ai/contracts/data_exposure.py)复核当前委派、租约、精确所有权和 Dataset 读取范围，再由元数据端口匹配当前读者、读取用途、精确历史事件及归属。失败时受限快照和正文均不读取。获准后逐项校验独立台账快照，再读取正文并按同修订全字段比较。真实适配器仍须证明独立台账来源、版本不可变和实际读取顺序；两个端口回显相同正文无法提供该证明。

[I-SCHEMA 注册](../../danus_ai/contracts/api.py)区分 DataExposureQuery（调用方）、DataExposure（服务持有）、DataExposureResult（仅输出）。JSON Schema 和 OpenAPI 导出结构；跨端授权与权威事实核验由上述语义入口处理。[专项](../../tests/contracts/test_data_exposure.py)覆盖这三种入口、合法历史接触、错事件或数据版本、错主体／用途／归属、过期或撤销委派、缺权威依据、排队无接触、同修订换正文及发送撤销后历史仍可核验。发送撤销用已有约束核验端口验证，历史事实不会恢复发送资格；本用例不建立许可与暴露记录的通用映射。

[独立向量](../../tests/fixtures/data_exposure/actual-contact.json)的三段规范 JSON 字符串按字段顺序手列，完整 SHA-256 由标准库直接对这些字面量计算。测试比较实际 UTF-8 和完整摘要。[Ubuntu 对照](evidence/p1-2-data-exposure-ubuntu.json)、[Windows 对照](evidence/p1-2-data-exposure-windows.json)同时记录两份生成物，每端各自重生成并逐字节比对仓库样本。[Ubuntu 完整工程检查](evidence/p1-2-data-exposure-verify.log)留存原始输出。远端 CI 结论和证据范围见下节。

Ubuntu CPython 3.12.16 执行 env -u DANUS_P13_TEST bash scripts/verify.sh，锁定安装、Ruff、mypy、导入边界、生成物、518 项测试和 sdist／wheel 构建通过；18 项 SQLite 专项按开关跳过。Windows CPython 3.12.14 在既有隔离环境执行 uv sync --offline --locked --python 3.12.14 --no-install-project，再以 python -m pytest -q -p no:cacheprovider 运行 test_data_exposure.py 与 test_batch15.py，63 项通过。比较两端 JSON 的 lock_sha256、vectors、schemas 全部相等，覆盖三组合同的实际 UTF-8、完整摘要和两份生成物；运行环境的 Python 补丁版本如上。

## 剩余出口

| 缺项 | 受阻能力 |
| --- | --- |
| recipient_ref 的目标类型、精确定位及列表语义 | 无法从历史主体推定接收方，或出具按接收方归类的暴露事实。 |
| permit_ref 的目标、可空性及与科研访问授权／SendPermit 的关系 | 无法把历史记录自动归因于某许可修订，或据此反推耗用次数和撤销影响。 |
| 通用用途及事件映射 | 仅验证 R08c 独立版本已记账的实际数据接触。反馈释放、人工读取、导出、记忆检索等规则由 §6.13 规定覆盖范围，具体来源事件、记录映射和去重粒度尚未审定，本批不读取这些分支。 |
| data_use、分类和伦理等既有待决 | 保持[第十五批边界](p1-2-batch15-delivery.md)，历史核验不为其提供批准。 |
| 独立 R08c 来源和调度时原子核验 | 真实发送、挂载、消耗计数、撤销执行、恢复回放与适配器预读保证均由服务阶段验收。 |

本批关闭同项目、精确修订、独立权威快照支持的历史实际接触只读核验子集，对应远端工程 CI 已核验，A0 已[限定签收](decisions/A0-P1-2-data-exposure-acceptance.md)（b1d17152b0bb6857eff08b4442b18e61a1ed4cd6）。签收仅覆盖上述已交付子集。C 组已接入同项目已定事件和数据映射的纯契约核验，通用暴露映射及生产历史完整性继续待定，见[C 组交付记录](p1-2-c-selection-lock-delivery.md)。


## 远端 CI 与独立复核

[运行 43808973217](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43808973217) 为 main 手动运行，实际 SHA 为 a9a56e7d23e3be7beb5479dcaf66fa5eb411a119，状态 completed，结论 success。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43808973217/job/133106137383) 的 Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build 均为 success。该提交的工作流调用 scripts/verify.sh，覆盖锁检查与安装、Ruff、mypy、导入边界、生成物、默认 pytest 和构建。运行和任务的详细日志接口均返回 HTTP 403，证据限运行与任务步骤结论及实际 SHA 的脚本。远端单项结果、计数及构建输出未取得。

在交付 SHA 的 WSL 工作区使用 env -u DANUS_P13_TEST uv run --no-sync pytest --collect-only -q，默认收集 536 项，其中 B 组 29 项、SQLite 专项 18 项。以相同环境运行 pytest -q -rs tests/contracts/test_data_exposure.py tests/storage/test_candidate_slice.py，29 项通过、18 项按开关跳过。工作流未设置该开关，SQLite 专项按测试条件跳过，本轮无新增存储验收证据。前述 518 项通过及双端向量均属原交付本地证据。

### 独立复核发现与复验条件

读取计数按受限快照、受限正文排列。以下用现有合成 R08c 和发送端口替身，在调用正式核验入口前只替换列出的输入。

| 复现依据 | 观察结果与复验要求 |
| --- | --- |
| 保持查询和独立快照不变，分别替换正文事件修订、Dataset 科学版本、主体、用途。原专项另覆盖替换正文租户、项目及接触时间。 | 同修订正文全字段比较拒绝，DATA_EXPOSURE_BODY_MISMATCH，读取次数 (1,1)。把同样的四种变异放入独立快照内的接触记录时，DATA_EXPOSURE_VERSION_MISMATCH，(1,0)。真实 R08c 适配器仍需证明快照从独立台账取得，并证明精确修订不可变。 |
| 快照仍匹配事件及归属，但接触记录为空，正文端仍准备返回已接触正文。 | DATA_EXPOSURE_CONTACT_NOT_ESTABLISHED，(1,0)。排队不能由正文补成实际接触。反馈释放等事件的可信映射继续待定。 |
| 撤销相同数据／主体／用途的合成发送许可后保留合法历史委派，再分别移除当前事件读取授权、撤销当前委派、把查询时间移到委派恰到期。专项另测错归属和越权。 | 撤销后，发送约束入口拒绝且不读发送正文。有独立当前权限时历史查询仍通过；撤销当前委派、恰到期、越权或缺读取授权时均拒绝，(0,0)。真实服务须复验预授权顺序，特别是元数据端口不预读受限内容。 |
| 把仅含 status 和 event_ref 的结果分别送给 DataConstraintQuery、SendPermit、DataExposureQuery 及 ReferenceRequest 解析器，再直接送入发送约束守卫。 | 均拒绝。当前工程中该结果只在历史入口生成并由 I-SCHEMA 作为仅输出合同注册。未来消费者须继续单独核验访问与发送权限。 |
| 在查询根或 subject 添加 recipient_ref、permit_ref、event_kind，包括显式 null。 | 严格解析均拒绝。缺这些字段仅能查询已定的实际接触事实；用途按已有精确事实逐值比较，本批不给接收方、许可或其他事件推定映射。 |

在已定子集内未发现需先修改产品代码的偏差。上述复验只证明入口能发现单侧替换和拒绝无权读取；权威来源认证、不可变性及适配器 I/O 次序属于服务验收。
