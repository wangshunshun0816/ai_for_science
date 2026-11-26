# 审计与复审证据合同独立复核

2026-11-23 复核交付提交 28d113e04b2d97f0006bfd8cbc2506265748f0c6。依据大方案 §5.1、§6.4、§6.16、角色规格 §4.6 及本包授权。所有端口材料为明确的合成事实。本轮未修改产品或测试代码。

## CI 和本地证据

本地 HEAD 为本包交付提交，实时查询 GitHub main 仍为 4dec2fafd18ef948995a8fb51f65189654980f41。按交付 SHA 查询公开 Actions API 返回零条运行，工作流页最新显示数字整改运行 45097230926。用户确认本包需先手动推送，再选择 main 触发。本包尚无可核验的运行，实际运行 SHA、最终结论、关键步骤与详细日志均待补。不能将原数字整改成功移用于本包。[工作流入口](https://github.com/wangshunshun0816/ai_for_science/actions/workflows/ci.yml?branch=main)

本轮 Ubuntu CPython 3.12.16 默认收集 711 项，其中 test_audit_evidence.py 45 项、test_exit_coverage.py 12 项，专项复跑 57 项通过。工作流配置调用 verify.sh 的默认 pytest，未启用 DANUS_P13_TEST。收集与 57 项通过为本地证据。交付时完整检查 693 通过／18 项 SQLite 专项跳过、构建及 Windows 57 项继续引用原记录，本轮未重复全量或 Windows 检查。未新增存储证据。

## 已复现的本包整改项

### A-R01 配置引用及模型谱系正文未闭合

位置为 audit_evidence.py 的 AuditProfile.model_profile_ref／AuditAssignment.model_profile_ref，以及 check_audit_report 的 241–245、268–277 行。已有 qualification.ModelProfile.ref 是 ScientificRef，ModelLineage.model_profile_ref 也引用同一科学配置。新审计模型使用 RecordLocator 引用 ModelProfile，却未定义如何映射到原合同的科学引用。配置和谱系目前仅校验元数据读取许可及其定位与 Assignment 相等，未读取并核对二者实际正文和独立版本。

实际反例在合法 AuditSource 上增加两个结构合法的既有对象。ModelProfile 使用 real-model，ModelLineage 的 model_profile_ref 使用 unrelated-model，provider、base_model、version 同时不匹配。新审计入口仍返回 no_blocking_issue_found／evidence_checked_only，配置及谱系正文读取为零。再保持定位及修订不变，只改配置 task_kinds 与谱系所指模型，不更新它们的独立锚点，结果仍通过。合法配套配置及谱系的对照同样通过，因此当前检查不能区分错配材料。该反例未获得科学接受或发布资格，但违反本包要求的配置精确绑定与同修订正文核验。

可复现入口如下，代码只操作内存。

    from tests.contracts.test_audit_evidence import AuditSource
    from tests.contracts.test_invalidation import NOW, sci
    from danus_ai.contracts import check_audit_report
    from danus_ai.contracts.qualification import ModelProfile, ModelLineage
    s = AuditSource()
    a = s.assignment
    profile = ModelProfile.model_validate(dict(
        ref=sci("ModelProfile", "real-model"), tenant_id="tenant", project_id="project",
        provider="p", base_model="b", model_version="v1",
        prompt_ref=sci("Prompt", "prompt"), tools=[], task_kinds=["candidate_review"]))
    lineage = ModelLineage.model_validate(dict(
        locator=a.lineage_ref.model_dump(), tenant_id="tenant", project_id="project",
        model_profile_ref=sci("ModelProfile", "unrelated-model"),
        provider="different", base_model="different", version="v2"))
    s.put(a.model_profile_ref, profile.model_dump())
    s.put(a.lineage_ref, lineage.model_dump())
    result = check_audit_report(s.audit_query, s.auth, NOW, s)
    assert result.result == "no_blocking_issue_found"
    assert not [x for x in s.body_reads if x in (a.model_profile_ref, a.lineage_ref)]
    s.bodies[s.key(a.model_profile_ref)]["task_kinds"] = []
    assert check_audit_report(s.audit_query, s.auth, NOW, s).result == result.result

最小整改建议沿用已有科学配置引用和 ModelLineage 精确定位，复用 A 组已定的独立版本依据与正文核验，检查谱系关联的配置及模型组件版本。若不能提供现有合同所需的桥接或权威正文，则明确阻断配置核验分支。补两入口、同修订替换、实际模型／谱系错配、缺依据和合法新修订，保持越权零次受限读取。无需新增质量阈值或资格签发语义。

### A-R02 覆盖清单未实际消费原变体的追加观测

位置为 tests/contracts/test_exit_coverage.py 的重复 q3 分支。执行器先从正面输入复制 q3 并自行追加十条，随后只核对原变体 append_evaluator_only_rows 的长度。它没有将该字段的逐行内容送入正式入口。原样例当前恰好是十条相同 q3，所以本例数值通过，但“该变体已逐行执行”的证据不足。

独立扰动仅在内存拦截该 JSON 的 read_bytes，将十条追加行的 sample_id 全改成 q99，保留行数，run_case 仍返回 behavior_passed。将 q99 实际送入 FixedObservationInput 时，正式入口以 item_id 枚举错误拒绝。合法原 q3 变体对照通过。这是清单执行与输入追踪缺陷，原九件和四题计分实现未因此被改动。

复现只使用 unittest.mock.patch.object(Path, "read_bytes", ...) 替换该单一文件的内存读取值，原磁盘文件保持原样。最小整改为显式适配原变体的每条追加行，并用原标签、预测和独立手算核验结果。补同长度但 q99、冲突预测及合法十条 q3 的对照。整改前该行只保留“手构重复行与错误分母拒绝”范围，不记为原变体已完整执行。

## 通过的定向对照

- 原专项 57 项通过，覆盖四类结果、接收方复算、任务和报告精确匹配、候选完整正文及科学版本、同修订候选／配置记录／报告替换和预读权限。额外独立输入验证 error 夹带草稿、error 缺诊断定位、result 与 draft.outcome 不一致、未发现阻断却包含 blocking 项、needs_evidence 没有问题项，均被拒绝。
- 已有 AuditProfile 或 AuditReportRecord 自身的同修订正文替换可拒绝。更新锚点但替换报告目标仍为 AUDIT_ASSIGNMENT_MISMATCH。此通过项与 A-R01 所述的被引用模型配置／谱系正文缺口分开。
- 单目标 ReauditTask 合法链通过。缺事件为 INVALIDATION_EVENT_REQUIRED，错目标或错触发为 INVALIDATION_REAUDIT_MISMATCH，同修订任务正文替换为 INVALIDATION_BODY_MISMATCH。委派撤销或到期时全部受限快照和正文读取为零，任务无权时任务正文读取为零。返回结构未触发队列或资格恢复。
- 发布输入换报告修订或定位时，独立清单不匹配可拒绝。证据快照无权时零次受限锚点及正文读取。原 manifest 的签名载荷和方法保持原样。

## 待补测试、语义及服务边界

- needs_evidence 配一个 severity=blocking 的问题项目前可通过。这与第七批原 AuditReport 校验行为一致。当前证据不足以把它判为本包新增缺陷。后续须核对已有报告优先级依据，避免自行创设严重度或推导科学否定。
- 发布引用守卫只核对独立清单和 manifest 完整正文。向端口放入一个指向无关提交且 result=error 的 CheckReport 正文，只要原清单定位不变，关联校验仍通过，实际正文读取只有 ReleaseManifest。交付记录已经保留了通用快照／报告语义未覆盖的边界。此处未证明“无关报告正文拒绝”或“同修订快照／报告正文替换拒绝”，不能写成已验收。必要目标合同或适用事实缺失时，对应发布资格路径继续阻断。
- 仍需补配置和谱系实际正文的独立来源、任务适用及撤销事实，而非仅核对 AuditAssignment 回显的定位。真实认证、R12／R19 事实签发、适配器读取顺序与生产执行仍属服务验收。
- 十组向量使用独立固定 JSON 与完整摘要，实际值由模型序列化比较。本轮分别以 hashlib 与 OpenSSL 对十份冻结文件复算一致。候选科学版本和论断科学版本来自先前独立预映像。此证据证明本组固定输入的字节，未证明审计判断或签发来源真实。

## 29 行清单的准确覆盖

声明分类确为 12 行 path_subset、10 行 serialization_only、7 行 not_covered。十行序列化条目在 coverage_report 中的 result 为 not_executed，其实际字节验证在 test_independent_audit_vectors_and_service_input_boundary 及跨平台文件中单独执行。不能将这些行合并为行为通过。

12 行行为条目中，重复 q3 一行受 A-R02 限制。其余正面／有限否定是结果计算和接收子路径，超时仅错误报告子路径，均未承诺完整 G0/G1/G2 或入图。七行未覆盖为过宽 Scope 原变体、收集崩溃恢复、提交幂等、抽样不确定、数值复现、Scope 变更及资格恢复，保持未关闭。原九件、手算、设计基线及产品代码无改动。

## A-R01、A-R02 整改与复验（2026-11-26）

原复现及证据提交 247b44d69687c703fe7b382574448c5b0d760372 保留。先新增回归再修复，整改前新增的配置错配／正文替换、旧定位形状及原变体内容消费共 17 项全部失败。整改后两入口保留合法配套配置和精确新修订通过的对照。

### A-R01 处置

AuditProfile 和服务端 AuditAssignment 的 model_profile_ref 改为既有 ModelProfile.ref 使用的 ScientificRef，ModelLineage 仍是精确 RecordLocator。没有从旧记录定位推定科学版本，也没有创建新的配置 ID 或投影规则。旧定位载荷显式结构拒绝。两份生成物的唯一合同形状变化为 AuditProfile.model_profile_ref 从 RecordLocator 指向 ScientificRef；尚未签收的原审计形状需由提供方重新给出既有科学引用，无静默迁移。

服务端 AuditReader 复用 A 组 QualificationReader 的 execution_validity、execution_version 和 execution_body。先逐项核验当前读权限，再对两种精确目标核验当前期限、撤销与归属。独立快照的类型、精确定位、所有权与实际正文逐项相等，核对 ModelLineage.model_profile_ref 及 provider／base_model／version 与 ModelProfile 完全对应，并确认 task_kind 在配置适用列表内。提示和工具引用按快照中的精确引用核验读取权限。本次不授予正式 A7 评测资格，也不引入新阈值、权限或服务认证。

回归覆盖计算侧审计读取与接收复算两入口：实际模型／谱系错配、组件错配、同修订配置和谱系正文替换、缺有效性事实、撤销与恰到期均拒绝。配置或谱系无权时两种配置快照／正文、聚合材料及审计记录的受限读取全部为零。缺有效性、撤销和到期先于配置快照／正文读取。精确新 ModelProfile 科学版本与新谱系修订，配套新 AuditProfile／AuditReport 修订及独立依据时，两入口通过，原配置和报告正文保留。

### A-R02 处置及其他清单行检查

正式结果入口的绑定与四题独立标签沿用已有固定正面材料；原变体的 evaluator_only_rows、append_evaluator_only_rows 逐条读取，通过显式构造 TrustedObservation 输入既有精确运行／尝试绑定、原始题号和两臂预测。原始字节文件未修改。标签从锁定的正面依据取得，未采用变体自报标签重定义真值。原报告错配仍消费原 report_override。

合法十条重复 q3 计一次，固定分母为四，错误宣称的分母按实际收到的行数送入接收入口并拒绝。在内存将原追加行替换为 q99 或冲突预测，均不再报告原行为通过，q99 触发既有枚举拒绝，冲突使独立的“valid、0.25”期望失败。不是通过清空输入、补题或重建 q3 来通过。

对其他行作相同核对：缺 q4 改为消费原变体的实际逐行内容；正面和有限否定使用原文件的观测与手算字段；数字错配使用原变体 report_override。审计超时原文件仅有自然语言观察，原执行器代用另一个合成 error 报告不能证明它贯通完整 G2，因此该行降为 not_covered。独立 error 合同正反例仍保留。候选改版、三类明确失效、审计调用接收和单目标复审复用原独立材料与正式入口，范围仍为子路径。

现清单 31 行，11 行 path_subset、12 行 serialization_only、8 行 not_covered。原 29 行中行为从 12 降为 11，未覆盖从 7 增为 8；新增两行是 ModelProfile 和 ModelLineage 独立整对象字节证据。序列化行在清单报告中仍为 not_executed，其字节验证由专项执行，不混记为行为通过。[更新后清单结果](p1-2-exit-coverage-remediation.json)

### 实测、独立预期与剩余边界

Ubuntu CPython 3.12.16 完整 scripts/verify.sh 的锁定安装、静态检查、导入边界、生成物和构建通过，715 项通过／18 项 SQLite 专项跳过。Windows CPython 3.12.14 使用相同 uv.lock 的离线隔离环境，79 项专项通过。12 组整对象规范 UTF-8 和完整 SHA-256 两端逐项一致，两份 Schema 均由同一类型源生成并逐字节检查。配置字段变化的向量预期用固定 JSON 和 Python 标准库编制，并分别以 hashlib 与 OpenSSL 核算；未用产品 canonicalize 或模型输出生成自身预期。[Ubuntu](p1-2-audit-remediation-ubuntu.json) · [Windows](p1-2-audit-remediation-windows.json) · [完整工程日志](p1-2-audit-remediation-verify.log)

原九件、手算、设计基线和 uv.lock 保留原字节。发布守卫未改，仍仅证明精确引用清单与 manifest 正文关联；报告／证据快照完整正文适用性缺项保留。复审优先级、多目标、真实执行／入队、A7 方法资格、真实快照和事实认证仍未关闭。本包旧提交 28d113e04b2d97f0006bfd8cbc2506265748f0c6 尚无已核实 CI，新整改也必须核验自身 SHA 的新运行，原数字 CI 不作为本包证据。
