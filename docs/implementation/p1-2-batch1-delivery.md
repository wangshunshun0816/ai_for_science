# P1-2 第一批交付记录：T01 与 T02 已定基础

日期：2026-11-12。起点：`87c18534d1cc4ef587ad25e6c791801f3596afe1`；Ubuntu 仓库根目录核对为 `/home/wangshunshun/danus-ai`。起始工作区干净，main 比本地 origin/main 超前 1；本轮 ls-remote 确认远端仍为人工验收提交 `0aa4703ee810c93b46b6981587e51bd4a7466c23`。本地祖先包含该验收，P1-1 已签收状态保留。

## 1. 交付与边界

- T01：[全对象字段台账](r02-field-matrix.md)，83 类对象/消息/提案结构，581 个专属字段行与 8 行条件公共字段；登记类型、可空/缺省、写入方、锁定点、哈希分类、归属/引用及来源。文中明确区分原文明确内容、英文字段/类型建议和未展开结构；缺项关联 Q，不生成生产业务 Schema。建立台账完成不意味着字段决定全部关闭。
- [具体决策草案](r02-decisions.md)：Q-03 受信归属/引用四种结构、Q-01 字段投影及运行方法/停止/纯预算表、Q-02 精确版本批准与去循环示例；均待 A0 审定。Q-04～07 仍待决，本轮基础类不依赖其决定。
- T02 部分实现：`danus_ai/contracts/parsing.py`、`base.py`、`__init__.py`；测试 `tests/contracts/test_foundations.py`。唯一模型编辑源是 Python 基础类；尚未输出业务 JSON Schema/OpenAPI。
- `pyproject.toml`/`uv.lock` 增加 D-03 已批准的 Pydantic 2 及必要传递依赖；`scripts/verify.sh` 强制重装本项目非 editable wheel，防止新增子包后继续测旧安装包。

本次实现基于 G §3.4/P1-2、A §5.1/5.2/6.4、附录 C.2 及 R §3.5；不复用上游代码。基础库是形状校验，不是身份认证/科研批准。没有授予正式科研内容 ID，没有定稿引用、批准或签名结构，没有业务状态机、数据库或付费调用。

## 2. 已实现规则与实际入口

| 已实现 | 入口/证据 | 明确限制 |
|---|---|---|
| 未知字段拒绝、严格类型、缺省与赋值验证 | StrictContract.model_validate / model_validate_json；正反例 Probe | Probe 是测试专用合同，不是业务对象 |
| 重复 JSON 键拒绝 | parse_json 的 object_pairs_hook；根/嵌套/相同值/转义后同键反例 | 不等于 Q-07 观测重复策略；NFC 后键碰撞留 T03 |
| NaN/Infinity/-Infinity 拒绝 | JSON 常量及 Python 嵌套 float/Decimal；非法默认值测试 | 精确有限 1e999 解析为 Decimal，未做规范化或 hash |
| 草稿/权威基础类分离 | DraftContract 禁止服务身份/批准/时间/摘要及 measured/supported/paid 根字段；AuthoritativeRecord 单独构造 | 不能把构造成功当认证；实际 numeric nature/source 交叉校验未实现 |
| 两种服务身份拼写拒绝 | principal/principal_id、on_behalf_of_account/on_behalf_of_account_id | 适配统一命名仍按 Q-03；不禁合法 PlanNode.role 一类科研/计划字段 |
| 禁止入口放宽策略 | strict=False、extra=allow/ignore、from_attributes=True 被拒绝 | 支持的外部输入入口限 model_validate/model_validate_json/parse_json；model_construct、model_copy(update)、原生 TypeAdapter 等不是受信输入入口 |
| 合法嵌套基础类继续严格 | ContainerProbe 包含 DraftProbe | 不靠递归扫描任意键名判权限；后续嵌套业务字段必须声明具体类型，禁止以 Any 放行 |

本轮没有发布 validate_object 分派器和 identity/references/numbers 业务合同；完整 T02 及 P1-2 未验收。跨归属引用、正式数值来源、legacy_incomplete 迁移、状态转换、规范化/内容 ID、签名和完整角色合同均未冒称完成。基类是库级开发约束，不是针对恶意 Python 子类/可执行代码的沙箱。

## 3. 依赖及可复现安装

[D-03 原批准](decisions/A0-P0-6-D01-D03.md) 明确允许 pydantic 2。本轮执行 `uv add "pydantic>=2,<3"`；CPython **3.12.16**、uv **0.13.7**，不切换解释器基线。

uv.lock 实际锁定：pydantic **2.14.3**、pydantic-core **2.50.4**、annotated-types **0.8.0**、typing-inspection **0.4.5**；安装包元数据许可均 MIT。typing-extensions 等原有依赖沿用锁定图。锁文件记录 registry/source 与下载文件哈希；不是上游源码路径依赖。此次依赖是 R02 必需最小集，未安装 fastapi 等未用包，未改仓库 Git 身份配置。

## 4. 本轮 WSL 实测

执行入口：`bash scripts/verify.sh`，退出码 0；末次结果 **55 passed in 0.79s**（原有 11 项及新增基础合同 44 项）。

入口实际运行：
1. `uv lock --check`
2. `uv sync --locked --no-install-project`
3. `uv sync --locked --no-build-isolation --no-editable --reinstall-package danus-ai`
4. `uv run --no-sync python --version` → 3.12.16
5. `uv run --no-sync ruff check danus_ai scripts/check_import_boundaries.py tests` → passed
6. `uv run --no-sync ruff format --check danus_ai scripts/check_import_boundaries.py tests` → passed
7. `uv run --no-sync mypy` → no issues in 7 source files
8. `uv run --no-sync python scripts/check_import_boundaries.py` → PASS（原违规导入夹具仍被拒绝，正常测试通过）
9. `uv run --no-sync pytest -q` → 55 passed
10. `uv build --no-build-isolation` → sdist/wheel 成功，包含 contracts 子包

安装/验证中可恢复失败：初次测试因 uv 复用旧非 editable 项目安装包而找不到新子包。修复 verify.sh 强制重装项目包后，完整入口重跑通过；不是靠源码路径注入绕过安装。日志本地暂存 `/tmp/danus-p1-2-final.log`，本记录保留结论及命令，不要求该临时文件永久存在。

九个原 JSON 用 Git 起点 blob 与工作区原始 bytes 逐个比较，全部相同；原数值与 expected_derivation 保留。三份设计基线未修改。本轮没有执行九题业务解释/证据门，因此这项字节检查不是金样例业务验收。

现有 CI 仍调用同一 verify.sh，但仅 workflow_dispatch；本轮未触发远端 CI，也不引用旧 P1-1 成功作为新代码 CI 证据。未执行 Windows 纯契约/跨平台 hash 验证（本轮没有 hash 实现）；R01 待验事项和 P0 整体验收状态不变。

## 5. 待审与下一批条件

A0 优先审阅 [决策草案 §1](r02-decisions.md#1-q-03不可信引用与受信归属分离)、§2/§2.1 及 §3，并绑定本次提交版本：引用结构/租户项目映射；科学投影、null/缺省及列表规则；运行限额具体分类；选择/阈值科学条款及不同批准目的的精确绑定。责任人和独立方法/权限复核者仍待 A0 指定。台账 object/list[object] 内部字段须补齐后才能冻结相应 Schema。

T02 的完整身份/引用与 T03/T04 的正式投影/批准校验依赖 Q-03/01/02；Q-04 审计、Q-05 签名、Q-06 状态边、Q-07 重复观测保持待决。后续可按授权继续无争议的枚举/规范化基础，但本轮没有把它们加入已实现范围。人工验收由 A0 另行记录，审核状态不由自动测试升级为通过。
