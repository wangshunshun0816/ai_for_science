# P1-1 首次交付记录

日期：2026-11-11。依据：A0 本轮「授权执行 P1-1 首次交付：R01 工程骨架与 CI」、开发指南 §3.3／§5.3、大方案 §6.3，以及 [首次交付范围](p0-6-closure-and-p1-1-scope.md)。本条授权允许首次工程交付，不扩大 P0 或 R01 全部验收。

## 起点与状态

起点为 058606736b2fb2b572c9cfba41485f87e874e423；Ubuntu 根目录 /home/wangshunshun/danus-ai，工作区干净。git ls-remote origin refs/heads/main 返回同一完整哈希，已确认起点同步 GitHub；未读取令牌。

设计／授权：首次交付范围已获本轮用户授权。工程：下列本地首次交付已实现。验证：本地实际验证通过，目标提交的远端 CI 已成功，人工验收待 A0 填写。P0 整体和 R01 全模块仍不声明通过。

## 交付与依赖

- pyproject.toml、danus_ai/__init__.py、README.md、MANIFEST.in：最小可安装包，无 R02 对象和业务逻辑，运行时第三方依赖为空。sdist 包含验证脚本及夹具；wheel 仅提供工程包。
- .python-version 固定实测 CPython 3.12.16，项目元数据限制 >=3.12,<3.13。uv 0.13.7；uv.lock 固定解析版本和下载制品哈希。
- 本次实际必需工具：pytest 9.2.0、Ruff 0.17.4、mypy 1.20.2；构建后端 setuptools 80.9.0 为打包所必需，build-system 与开发组同时固定，使构建使用锁定环境。许可证元数据见验证记录；不是完整 SBOM／第三方许可审计。
- D-03 的其他依赖（Hypothesis、Pydantic、FastAPI、uvicorn、HTTPX）当前无使用需求，未为将来的业务提前安装。真实事务出现时补 Hypothesis 状态机验证。
- scripts/verify.sh 先安装锁定工具，再使用 --no-build-isolation --no-editable 安装本项目；未向上游注入路径。首次失败为文件生成时的引号转义错误，已修复并重跑，不存在未处理的检查失败。

## 导入边界及出处

| 规则 | 设计出处与执行方式 | 限制／待决 |
| --- | --- | --- |
| B01 禁止跨组件具体实现导入 | 大方案 §6.3、开发指南 §3.1／§3.3；组件只能依赖自身及 contracts，bootstrap.py 负责装配。设计目录 orchestration=R16、ideation=R17，见指南 §3.25／§3.26 | 首级目录作为组件、仅 bootstrap.py 例外是本次最小工程策略；R09 未来装配入口及同模块多目录映射在接入前审查，未默认为所有 R09 文件放开 |
| B02 契约依赖准入 | 大方案 §6.3／§6.4；contracts 不导入网络、DB、模型 SDK 或业务实现。按显式纯依赖清单准入，httpx/sqlite3/os 等未准入依赖被拒绝 | 清单是保守工程实现，不是设计逐项指定；新增依赖须说明其纯契约用途并补测试 |
| B03 动态导入需审查 | 为防止绕过静态边界，检查直接 __import__ 及属性 import_module 调用 | 设计未规定动态插件机制；当前拒绝上述形式为临时工程策略。别名、反射等任意 Python 行为无法由此检查完整证明；不是运行时安全沙箱 |
| B00 无效输入拒绝 | 验证设施自身正确性：缺失／空根目录、语法及非法相对导入不能报告通过 | 工程校验规则，无新增业务语义 |

受控 fixture 只被 AST 解析，不执行或导入。合法 fixture 覆盖 R16→R02 和 bootstrap→R17；违规 fixture 为 R16→R17，检查器返回 1 并输出 B01。测试将预期拒绝视为成功；真实源码仍须全部通过。另覆盖相对导入、from danus_ai import ...、memory 实现导入、契约 I/O 依赖及动态导入拒绝。

边界检查仅限制已支持的静态导入形式，不证明角色进程没有数据库写权限；角色进程隔离和实际写权限验证留在对应模块验收。未创建角色或仓储实现。

## 实际验证

机器可读结果及锁 SHA-256：[p1-1-verification.json](p1-1-verification.json)。本地执行入口：

    bash scripts/verify.sh
    UV_PROJECT_ENVIRONMENT=/home/wangshunshun/danus-ai/.venv-repro bash scripts/verify.sh

每次均执行 uv lock --check、两步 uv sync --locked、Ruff lint／format、mypy、源码边界检查、pytest、uv build --no-build-isolation。两次均为 11 tests passed，mypy 3 files 无问题，构建 sdist/wheel 成功。两个独立虚拟环境包名／版本集合完全相同；复现证据为依赖解析及安装一致，不宣称构建产物字节可重复。

另执行 uv venv --python 3.12.16 .venv-wheel，再以 uv pip install --python .venv-wheel/bin/python --no-deps 安装本地 wheel；在 /tmp 使用该解释器 -I 导入，定位到 .venv-wheel 的 site-packages，排除源码目录遮蔽。临时环境和构建输出均被忽略，不提交。

## CI

.github/workflows/ci.yml 仅 workflow_dispatch，无 push／PR 自动触发。2026-11-11 已核实公开仓库与标准 ubuntu-24.04 runner 的免费执行条件，见下方核对记录。随后由用户手动触发运行 #1，公开页面已核实 Success，实际链接及提交见文末。自动触发认证不可用的历史记录保留。

权限仅 contents: read；checkout 固定提交、persist-credentials: false；不注入自定义密钥或生产凭证；固定 uv 和 Python，15 分钟上限，无 GPU／模型调用。uv 在独立工具 venv 安装以避免系统 Python 的 externally-managed 限制；随后执行与本地相同的 verify.sh。本地通过不能代替 GitHub 托管执行通过。

## R01 保留验收及待决

以下均未完成，拟定节点沿用范围记录，不因本次交付标为通过。

| 项目 | 当前状态／下一验收节点 |
| --- | --- |
| SBOM／差异与完整许可审计 | 待完成；工具和范围待落实，拟在 P1 依赖基线验收补初版并随变更复核 |
| 镜像 manifest／digest | 未创建镜像；基础镜像及构建方案待决，P1 首个镜像验收固定 digest 与 manifest |
| Windows/Linux 规范化哈希 | 未实现 R02 哈希业务，未做跨平台验证；拟在 P1-2 契约验收联合完成 |
| Linux 容器运行 | 未运行容器；拟在首个可运行镜像及 R01 跨模块验收前完成 |
| 签名校验 | 未建立签名载荷或密钥；责任／信任配置待决，首次正式制品及 R01 跨模块验收前完成 |
| 真实事务／隔离故障测试 | 无事务、角色或数据库；在 P1-3／P2 对应能力形成后验证，不能以 AST 替代 |
| 远端 CI | 免费条件已核实；运行 #1 已成功，见文末实际链接及对应提交。该结果仅覆盖目标代码提交 |

A0 尚需落实范围记录所列责任人、首包／独立复核及投入。工程侧后续需审查模块映射、动态导入策略及工具／镜像方案；科学资格、付费调用和正式 campaign 按原批准边界执行。本轮未修改设计基线、上游只读目录或 D 盘归档，未创建数据库或发起模型付费调用。

## 远端 CI 收尾核对（2026-11-11，触发前历史记录）

- git ls-remote origin refs/heads/main 返回 30e97ad85c5333d92ee8cac8aa7ec2f27e0e17f3，与目标提交及本地起点一致，已同步。
- 未登录访问 [仓库网页](https://github.com/wangshunshun0816/ai_for_science)，页面标记 Public 且数据字段 isPrivate=false。工作流只用标准 ubuntu-24.04 runner、15 分钟上限，没有 upload-artifact 或 cache 步骤，也没有模型／采购步骤。
- [GitHub Actions 计费规则](https://docs.github.com/en/actions/concepts/billing-and-usage)说明公开仓库的标准 GitHub-hosted runner 免费；[runner 标签表](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job)将 ubuntu-24.04 列为标准 runner。因此本次运行的免费条件已核实，无需依赖私有仓库的剩余额度。若仓库可见性、runner 或工作流改变，应重新核实。
- 触发阻塞：Ubuntu 和 Windows 未发现 gh；Ubuntu 未配置 Git credential.helper；匿名 REST API 返回限流 403；浏览器控制和 Windows 自动化均在初始化时报告 sandbox helper_unknown_error。未读取、输出或导出令牌，未尝试匿名写操作。
- 实际运行链接：无（尚未触发）。目标代码提交：30e97ad85c5333d92ee8cac8aa7ec2f27e0e17f3。运行结果：未运行／触发认证阻塞，不记为 CI 通过或 CI 失败。
- 后续：在已登录的 [工作流页面](https://github.com/wangshunshun0816/ai_for_science/actions/workflows/ci.yml)手动触发 main，核对运行的完整 head SHA；若 main 已追加仅证据文档的提交，应明确登记实际运行 SHA，不能冒充本目标提交的精确运行。跟踪到结束后补入实际 run URL 和结果；人工验收由 A0 填写。

## 远端 CI 实际完成证据（2026-11-11）

- [P1-1 foundation checks #1](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43036783370)，run ID 43036783370；用户在 main 上手动 workflow_dispatch 触发。
- 实际运行提交：30e97ad85c5333d92ee8cac8aa7ec2f27e0e17f3，与本次要求验证的目标完全一致。公开运行页的提交链接独立核实了完整 SHA，不仅依赖截图短哈希。
- 最终状态：Success；foundation job 成功；总耗时 24 秒。证据来源：用户截图及本轮直接读取的 GitHub 公开运行摘要。工作流执行 scripts/verify.sh；本轮没有取得逐步原始日志，不将本地测试计数冒充远端日志摘录。
- 一项非阻断警告：固定 actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 的目标运行时为已弃用 Node.js 20，平台强制使用 Node.js 24 执行。本次结果成功；后续应评估并固定支持当前运行时的 checkout 版本，升级后另行运行验证。本轮不为清除此警告改变已经通过的目标代码。
- 此前的触发认证阻塞已由用户手动运行解决；本地 Git 推送认证属于另一事项，不以 CI 成功推定推送成功。后续证据文档提交不宣称自身运行了该次 CI。
- P1-1 本地及目标提交远端验证均有成功证据。人工验收仍待 A0 填写；不宣称 P0 整体或 R01 全部验收通过，不启动 P1-2。
