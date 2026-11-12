# P1-2 第六批交付记录

## 1. 依据与范围

起点为 A0 第五批限定验收提交 `c378993cbbf19ff54452dc9165ed2cdfc59104d6`，开工时 Ubuntu HEAD 与 GitHub main 一致，工作区干净。沿用 [首组批准清单](decisions/A0-R02-first-contracts-checklist.md) §5–6、[首组字段表](r02-first-contracts-proposal.md) §1–6 和 [Q-04～Q-07 批准清单](decisions/A0-P1-2-Q04-Q07-checklist.md)。四题路径依据大方案 §5.1、§5.5、§6.9、§6.16、附录 C。

## 2. 已交付契约

| 对象或操作 | 已验证的合同 | 生产阻断或后续 |
| --- | --- | --- |
| 只读解析 | 对实际内容做严格类型校验和摘要重算，分别报告不可读、缺目标规范、错精确版本、错归属和内容不匹配。普通材料须经受信端口核验实际来源或 manifest | 受信端口由后续服务实现。部分材料只验证内容承诺和端口确认，完整业务规范由各权威模块提供 |
| Protocol | 固定四题总体、数据及切分一致性、缺题策略、调参规则、基线、度量及精确适用 Scope。计算确定性预映像，可核对已存版本 | 生产模式须提供准确项目、Protocol 版本及真实适用证据。使用批准需另经 R04b/R09 |
| Prereg | 问题、族与选择历史版本、候选、阈值单位和方向、Scope、Arm 与基线、四题停止条件、分析及失败／重试／反馈引用。科学条款进入投影 | 科学计算与签名分开。锁定核验候选选择和阈值的精确批准记录、冲突及签名主题/条款摘要。协议与族签名条款未审定，继续阻断锁定 |
| ExecutionBinding | 独立绑定代码 commit、镜像、依赖锁、数据 manifest、切分、方法、协议、套件与检查配置，重算规范版本 | 真实 Git、镜像及数据工件由对应服务核验。无回指 RunRequest 或 SanityReport |
| RunRequest | 固定枚举确定性 confirmation 的预映像、绑定一致性、锁定计划内 Arm、方法、角色及任务。核验当前 sanity 绑定、套件、配置、必需项和批准快照 | 纯预算、保护限制、批准与回执不进入科学投影。其他批准用途缺已审定条款时阻断，真实授权、租约、预算、数据及调度在后续阶段验收 |

代码入口为 `danus_ai.contracts.fixed_four.FixedFour`。生成的 JSON Schema 与 OpenAPI 标记新增服务目标视图和专用预映像能力。通用 `content_id` 继续拒绝缺少专用输入的对象。精确引用先逐条校验，再投影或按既定集合语义去重。夹具仅用于纯契约验证，不构成可入库版本、批准或实际启动资格。

## 3. 实测

- Ubuntu CPython 3.12.16 执行 `bash scripts/verify.sh`，220 项测试通过，锁定安装、Ruff、mypy、导入边界、Schema 漂移、sdist 及 wheel 构建均通过。
- Windows 原生 CPython 3.12.14，在 `%TEMP%\danus-r02-batch6` 以既有 uv 0.12.7 重建隔离环境，`uv sync --project <WSL UNC> --locked --no-install-project --python <native python.exe>`，随后 `python -B -m pytest -q -p no:cacheprovider <WSL UNC>\tests\contracts\test_batch6.py`，12 项通过。Ubuntu 使用 uv 0.13.7。两侧 pydantic 2.14.3、pydantic-core 2.50.4、rfc8785 0.1.4，项目依赖和锁无变更。
- Ubuntu `PYTHONPATH=. uv run --no-sync python -B tests/contracts/test_batch6.py` 与 Windows 隔离环境以 UNC 源码为 `PYTHONPATH` 运行同脚本。四个预映像逐字节及完整 SHA-256 一致，七项错误路径和两份 Schema 摘要一致。独立预期在测试中按已批准字段表手列投影，用 Python 标准库排序 JSON 验证 ASCII 键值、空值和布尔量，对 RFC 8785 的广泛覆盖沿用既有向量。
- `git diff --exit-code 412e67e -- docs/implementation/p0-2/golden` 无差异，原九个样例及手算记录保持原字节。跨平台结果见 [实测向量](evidence/p1-2-batch6-cross-platform.json)。

## 4. 待办与 CI

历史标记清除权限、跨 Scope 科研映射、其他用途条款、采样及描述型分支仍按原决定处理。真实服务接入、完整 I-SCHEMA、其余金样例及 Linux 正式运行仍待对应阶段。第六批人工验收待 A0。

GitHub Actions [运行 43318093230](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43318093230) 已完成，结果为 **Success**，运行记录从开始到完成更新用时 23 秒。该运行在 `main` 手动触发，实际 SHA 为 `df85e6c00928ffdfdfc5463eb322c564c281009e`，与第六批交付提交一致。[foundation 任务](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43318093230/job/131531276420) 的锁定工具安装、Python 安装、`Locked local checks and build` 均成功。Checkout 步骤成功，运行注解记录了 `actions/checkout` 的 Node.js 20 弃用警告，runner 使用 Node.js 24 执行。
