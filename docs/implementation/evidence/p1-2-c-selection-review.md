# C 组限定纯契约独立复核证据

复核提交 1e90d61fe560eebf8fb612953603425b9c0c0973。C-01～C-05 依据签收 164ed9ce41b70f06c7afe5ff5dceee2da4031763 及其绑定方案 a837a549b61cfc177756a6560e19d9fbf9d9f98c。C-S01～C-S07 依据签收 4ae073622a360949d84e651b9b17d31f821f6f1b 及其绑定字段表和向量 1c23327a2e95fd18ef308aa4958c21706fa03094。[签收决定](../decisions/A0-P1-2-consolidated-decisions.md) · [字段表及补充签收](../p1-2-c-selection-lock-fields.md) · [交付和 CI](../p1-2-c-selection-lock-delivery.md#远端-ci)

在 Ubuntu CPython 3.12.16 用该提交的原专项及临时内存夹具复验，默认收集 16 项，定向运行 16 项通过。下面的反例使用独立构造的权威快照、完整正文、租户及项目权限，除各项列出的替换外保留原始夹具。它们在验收提交上运行时未改产品文件。[测试夹具](../../../tests/contracts/test_selection_review.py)

|编号与签收项|可复现输入及实际结果|关闭条件|
|---|---|---|
|C-R01 · C-05／C-S05|用 history_fixture 装配受权 A4 视图，保持精确定位和状态，只将 family_summary.blocking_reason_codes 换为含空格、分隔符的主体私有文本和许可定位。调用 history_view，整段文字原样回到 blocking_reason_codes。字段白名单存在，但允许受限信息借短码字段输出。[返回路径](../../../danus_ai/contracts/selection_review.py#L745) · [字段形状](../../../danus_ai/contracts/selection_records.py#L280)|在返回边界只接收受控短码，拒绝正文、可识别主体或许可定位。用同一反例断言敏感值不出现在响应，合法短码去重、A4 零受限正文读、A7 原有正例继续通过。|
|C-R02 · C-04／C-05／C-S04～C-S06|用 history_fixture 装配同项目 R05/R08c 覆盖。第一步给 FilterEvent 的配套正文和独立快照写入另一问题的 question_ref，保持精确定位可读、来源清单仍引用原事件定位，A7 仍报 complete。第二步把同一 FilterEvent 定位放入 intervention_event_refs，独立重算 SelectionSet 与 v2 历史版本，R05 清单仍只含一次事件。两份列表同时返回该事件，仍报 complete。通用正文比较未核事件语义，覆盖按定位去重掩盖了角色错配。[集合读取](../../../danus_ai/contracts/selection_review.py#L586) · [来源归类](../../../danus_ai/contracts/selection_review.py#L613)|以获准的事件契约或受信事实核验问题、归属、类别与列表角色，范围不明就阻断。补跨问题、错类、同事件冒充另一角色、来源证明错配及合法有序多事件正反例。|
|C-R03 · C-03／C-S03|从 threshold_fixture 取得已有真实合成签名事实的当前 approved 事件。增加独立快照及正文匹配的 superseded 前驱，把它的 approval_ref 指向不存在的 meaningful_threshold 批准。当前事件指向此前驱，问题、阈值及时间保持一致。check_threshold 返回 approved，前驱批准无版本依据或正文读计数，且端口根本没有该批准事实。[生效检查](../../../danus_ai/contracts/selection_review.py#L489) · [前驱遍历](../../../danus_ai/contracts/selection_review.py#L527)|对链内 approved／superseded 节点按其精确问题、条款、事件和当时的权威批准事实核验，缺历史事实阻断。补不存在、错目标、错条款与跳接反例，以及当前不可用但历史时点有适用签名的合法链，避免用当前状态代替历史证据。|
|C-R04 · C-01／C-S01|用 report_fixture 构造六项检查均通过的当前报告。第一项 evidence_refs 加入完全相同的第二条定位，报告正文与独立版本保持一致，权限和独立证据均有效。check_report 返回 ready 且原样返回两条引用。集合比较会折叠重复，输出仍带重复项。[结果处理](../../../danus_ai/contracts/selection_review.py#L350) · [字段形状](../../../danus_ai/contracts/selection_records.py#L78)|按已签收集合语义处理输出，在去重前逐条授权和验证。补重复输入、次序差异、不同精确修订与越权副本用例。|

签名复验直接使用 OpenSSL Ed25519 对公开夹具的 v2 选择及两个 v1 选题／阈值签名前载荷验签。用 OpenSSL 回调走现有 check_selection_fixture 得到 fixture 标记。只改签名首个十六进制字符，并使替换后的信封与模拟独立快照一致，仍得到 SIGNATURE_INVALID。正式入口在合法签名之后以 C_SELECTION_BUDGET_AUTHORITY_SPEC_UNRESOLVED 拒绝。此证据覆盖签名内容及运行时调用，真实签发主体、密钥治理、撤销及预算合同留服务和权威决定验收。[签名核验](../../../danus_ai/contracts/selection_review.py#L392) · [签名测试材料](../../../tests/fixtures/c-selection/ed25519.json)

另以独立标准库 JSON 和 SHA-256 重算引用 v2 历史的新 Prereg v1 版本，为它单独登记配套权威完整正文，并提供现行旧格式选题及阈值批准。fixed_lock_preimage 明确以 TARGET_VERSION_MISMATCH: SelectionHistory 拒绝，复现到历史版本域门槛。原固定四题测试继续对照现有 Prereg 独立预映像、空暴露、test=null 和 family_alpha=null。完整锁定前通过仍需协议及族签名、适用完整历史、校准及预算事实。[现有预注册路径](../../../danus_ai/contracts/selection_review.py#L778)

七组签收向量逐字节、长度和完整 SHA-256 均相符。其中固定问题、族、历史、选择条款、阈值条款、旧批准主题、DataExposure 是各自的字面预映像，材料公开标明 Scope、Dataset、候选及 Rationale 占位引用，仅作为逐对象对照使用。贯通夹具另行提供这类目标正文，使用标准库 JSON 与 SHA-256 装配引用、独立版本、当前授权、源覆盖与适用签名。重算得到 v2 选择签名前载荷 SHA-256 8eab64e5fab638c986ebf90abd4a346f13d27adced4d2091695ac68b309c2984，新版历史投影 SHA-256 a3a6aba602962168f400d82c910e80b3a12b42d6d9ed19e882c44856205bede6，与交付记录一致。历史族关联的夹具使用原 FixedFamily 投影作权威锚点，关联正文另行提供，完整新族签名和正式确认仍需单独证明。[签收向量](../p1-2-c-selection-lock-vectors.md) · [独立装配和比较](../../../tests/contracts/test_selection_review.py#L1067)

仍待补测的纯契约场景包括六项检查中有权且适用的 not_applicable 正例与缺试点依据反例，逐字段置换报告及清单修订、预算币种、用途、预算及根任务定位，签名到期和撤销；阈值跳接与历史时点证据；双事件同数据定位的正确集合去重与冲突，及多事件、不同来源游标、截断和次序、多项目拒绝。已有历史截断、签名变更、旧批准失效、错事件或数据版本、越权零次受限读取和 v1/v2 拒绝证据继续保留。生产 R05/R08c 的游标、冻结截面、真实来源与不可变性以及适配器读取顺序需分别验收。

[CI 44015452505](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44015452505) 在交付 SHA 上成功，foundation 的检出、固定工具和 Python、锁定检查与构建步骤均成功。详细日志 HTTP 403，远端单项 pytest 输出及计数未核验。本地收集 16 项。该工作流和本轮复核均未执行 SQLite 专项。

## C-R01～C-R04 整改

原四项复现保留在上文，对应交付 SHA 1e90d61fe560eebf8fb612953603425b9c0c0973。先转为回归，在旧代码上新增定向筛选为 6 项失败、1 项合法对照通过。整改后的正反例结果如下，工程复验与人工签收分别记录。

|复核项|整改及复验|
|---|---|
|C-R01 A4 阻断码|仅返回 C 组已有覆盖守卫的五个稳定短码。未知 token 和私有文本均以现有 C_FAMILY_SUMMARY_UNRESOLVED 拒绝，响应无原值，零次受限详情读取。已知短码保留并去重，合法 A4 摘要及原 A7 白名单通过。详细诊断由授权审计边界处理。[输出守卫](../../../danus_ai/contracts/selection_review.py#L893)|
|C-R02 筛选与干预|在受限读取前核对精确事件许可及独立 R05 事实，要求类别、稳定问题与版本、精确选择集合、上游覆盖截面、归属均匹配。再核对权威快照与事件正文中的问题和集合关系。跨问题、同事件冒充双角色、类别／修订／集合／截面错配和无权威事实均拒绝。独立覆盖的合法筛选和干预各绑定其角色，A7 返回 complete。[事件及覆盖守卫](../../../danus_ai/contracts/selection_review.py#L704)|
|C-R03 阈值历史|逐个核验已批准或已替代的前驱，消费独立的 R09 历史有效时点证据，核对精确事件、批准目标、条款摘要和已归档的签名证据。替代必须是 R09 审批历史中获授权的实际决定，绑定被替代证据和链内后继精确批准。不存在或未归档的批准、缺替代、错误后继、错误条款、错误历史时点及未授权或未归档替代均拒绝。是否合法以历史事实判断，合成正例中旧批准已不在当前有效视图，历史链仍通过。[前驱与替代核验](../../../danus_ai/contracts/selection_review.py#L564)|
|C-R04 报告证据集合|报告快照原样核验，逐条原始引用执行当前权限、精确版本和正文核验，随后按完整引用去重并保留首次顺序。重复出现的第二次读取被撤权时整项拒绝。不同修订与定位均保留，旧报告的权威快照和科学预映像不重写。[报告读取](../../../danus_ai/contracts/selection_review.py#L372)|

Ubuntu CPython 3.12.16 的完整工程检查为 558 项通过、18 项 SQLite 专项跳过，含依赖锁、Ruff、mypy、导入边界、Schema 检查和发行构建。Windows CPython 3.12.14 同锁 C 组纯契约 40 项通过。原七组手列向量和两组贯通预映像的规范 UTF-8 与完整 SHA-256 都在两端一致，且与整改前一致。两份更新后的生成物通过双端逐字节校验。

|生成物|整改后的完整 SHA-256|
|---|---|
|JSON Schema|7df7f77ca46cb92288fc422601ce3c28a4fdaa3d7f992e0fbbb7057a073b0880|
|OpenAPI|2a8b79af164f230e9fc521e47cb136d9932a792a3748dad916c0057a0459bcac|

Schema 只收窄 A4／A7 公共阻断码的元素类型为现有覆盖代码枚举。报告输出折叠完全相同的引用，字段形状不变。历史批准和事件绑定是受信读取端口的证据要求，旧适配器缺必要事实时须拒绝。原批准、设计基线、九个金样例及手算未变，固定四题 v1 与新历史 v2 确认边界不变。

正式 ready 仍须逐项权威检查证据，正式选择签发仍缺权威预算合同，完整锁定前通过仍缺适用签名和权威事实。合法历史及覆盖正例是合成端口复验。真实 R09 历史有效性、替代权威与不可变性、R05／R08c 真实来源及读取顺序留服务验收。CI 44015452505 只覆盖原交付 SHA，整改提交的独立 CI 见下节。人工验收待 A0 填写。

## 整改 CI 与定向复验

[整改 CI 44027827660](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44027827660) 的公开运行页显示最终 Success，提交链接为 a3008c5c7dece9c3dc0bfac52244cf29d55e5232。[foundation 作业](https://github.com/wangshunshun0816/ai_for_science/actions/runs/44027827660/job/133852331964)的公开步骤元数据确认 Checkout、Install pinned tooling、Install pinned Python、Locked local checks and build 均成功。REST 运行、作业和详细日志接口返回 HTTP 403，公开单步日志链接返回 HTTP 404。未取得明细日志，远端逐项 pytest 输出、计数及构建明细未单独核验。

本地在同一提交用默认 pytest 入口确认收集 C 组 40 项，定向复跑 40 项通过。该工作流按默认入口执行，未启用 DANUS_P13_TEST。SQLite 专项跳过，本轮无新增存储验收证据。

|定向复验|同一 SHA 的本地观察|
|---|---|
|C-R04 报告|原始重复逐条核验后才去重。第二次读取失权时拒绝。合法不同修订及不同证据定位均保留。|
|C-R03 阈值历史|旧批准不在当前有效视图时，已归档且匹配历史时点、前驱和合法替代的链通过。批准缺失或未归档、条款／目标错配、替代未授权或未归档、错误后继均拒绝。|
|C-R02 筛选／干预|同一事件充当双角色、错问题、错类别、错修订、错集合／截面或缺权威依据均拒绝。合法双类事件通过，A7 仅按各自类别列出并报告 complete。|
|C-R01 A4|合法覆盖码去重后返回，响应白名单不含受限字段。私有文本、许可定位及未知 token 以固定错误拒绝且不回显，错误路径零次受限历史快照或正文读取。|

真实服务及权威依赖维持原边界。人工验收待 A0 填写。

历史状态更新。A0 已于 2026.11.17 限定签收 C 组已交付纯契约及四项整改（a3ab1ec77746055fb7199145b228db4fb5a155ea）。原发现、两次 CI 证据与未关闭依赖按原记录保留。[签收](../decisions/A0-P1-2-c-selection-lock-acceptance.md)
