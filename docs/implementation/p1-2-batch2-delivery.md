# P1-2 第二批交付：通用规范化与首组字段定稿提案

日期：2026-11-12。起点本地 HEAD 和远端 main 经 git ls-remote 核对均为 `198a2dc6b0a4b3a0109eacc69988bd8e684798f0`，工作区干净。仓库根目录 `/home/wangshunshun/danus-ai`。已读 AGENTS、G §3.4/P1-2、A §5.2/6.4、第一批交付及 Q 草案。本轮用户另明确批准新增 rfc8785；不扩大其他依赖、付费或科研批准范围。

## 1. 已实施的 T03 通用部分

代码：`danus_ai/contracts/canonicalization.py`，由 contracts 包导出；`tests/contracts/test_canonicalization.py` 接入现有 verify.sh/pytest。

- 继承严格 JSON 解析：重复键/NaN/Infinity 拒绝。
- normalize：递归 NFC 与 CRLF→LF，裸 CR 保留；键/值均处理；规范化后重复键即使值相同也拒绝；无效 Unicode 标量拒绝；不就地修改输入。
- decimal_string：严格 JSON 数字字面语法的字符串，精确 Decimal 转无指数形式，去多余小数末尾零，负零归 "0"；不经 float 或 Decimal.normalize 的上下文精度舍入。普通字符串不自动当数字。
- canonicalize：调用方先验证和投影，再显式指定 decimal_paths（原键名/精确数组索引）；所有声明路径须存在且为字符串；未知路径/错误类型拒绝。不补业务缺省、不删除字段、不替业务对象选集合排序。
- jcs_bytes：纯 RFC 8785 序列化到 UTF-8 字节，保留输入字符串，不做 NFC；库负责 UTF-16 键排序、控制字符及 binary64 数值格式。
- jcs_json：严格解析后显式按 RFC binary64 解释小数（可能舍入），拒绝非有限输出；只适用于 JCS 数值语义。
- canonicalize_json：科学前处理便捷入口；未经过 Schema 转换的裸小数 Decimal 拒绝，避免偷偷损失精度；精确科研量须用已声明 decimal string。两条入口不能混用。

这是通用字节管线，不是完整 I-SCHEMA content_id：没有业务投影注册、Schema 缺省、批准解析、集合型字段自动排序或正式科研内容 ID。语义列表保持顺序；集合去重排序仍等待逐字段批准和领域 Schema，不能全局排序。尚未对恶意超大输入制定统一资源限制，部署入口的大小/深度/十进制指数限制需另设工程策略，不声称有网络服务抗耗尽能力。

## 2. 库选择、授权、许可与来源

选择 `rfc8785==0.1.4`（实际 uv.lock），纯 Python、无传递依赖，库源 https://github.com/trailofbits/rfc8785.py 。选择理由：普通 json.dumps 无法代替 RFC 的 binary64 格式及 UTF-16 排序；采用库而不自行编写浮点算法。用户本轮明确批准添加超出 D-03 名单的该依赖。项目声明与锁中均记录依赖；不改解释器基线 CPython 3.12.16、uv 0.13.7。

许可证从已安装 distribution 原始 LICENSE 核实为 Apache-2.0，原字节保存在 [rfc8785-0.1.4-LICENSE](licenses/rfc8785-0.1.4-LICENSE)，SHA-256 `0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594`。第三方声明同步；未复制库源码或执行 Danus 上游。导入边界白名单只增加已批准的纯序列化依赖。

独立向量：[RFC Appendix B 数据](../../tests/fixtures/canonicalization/rfc8785-appendix-b.json) 和 [来源说明](../../tests/fixtures/canonicalization/README.md)。26 条预期从 RFC 原文表格提取，来源原字节 SHA-256 `63d52294eb0e3f0014174288186d388b4ddbf2c67d1ce8af1d9726eb0c3ab240`。测试不调用被测实现生成期望；另有 RFC 数值数组、UTF-16 排序及项目手算 NFC/换行/Decimal 字节断言。规范参考：https://www.rfc-editor.org/rfc/rfc8785.txt §3.1–3.2、Appendix B/D/E。

库整数域限于 ±(2**53-1) 的 Python int；大整数领域必须显式字符串化。Appendix B 大值以 IEEE bits 解码 float 验证；不把 int 域限制误报为未测试大浮点数。

## 3. 字段及 A0 决定

[首组完整字段提案](r02-first-contracts-proposal.md)：CandidateHypothesis 10、Protocol 15、Prereg 24、RunRequest 13 个专属字段，另有公共权威字段及闭合子结构表。表中必填/null/缺省、顺序、写入方、科学投影、精确引用及变更规则均为**待 A0 审定提案**。没有把其字段表写进生产默认值。

具体选择见该文 §7：Q03-1～3 归属映射/引用结构/科学引用投影；Q01-1～5 四对象结构与科学/纯预算分界；Q02-1～3 批准目的、条款投影及重新批准。参数范围、随机性/区分设计、运行限制等子表给具体建议，不冒称设计原文已有完整 Schema；外部 Ref 的目标规范缺失仍 blocked，不以引用替代完整性检查。Q04～07 保持适用待决。

## 4. 实际验证

WSL CPython **3.12.16**，uv **0.13.7**，rfc8785 **0.1.4**。执行 `bash scripts/verify.sh` 返回 0：
- uv lock --check；两阶段 locked sync；非 editable 重装本项目；
- Ruff lint/format 全通过；
- mypy：9 source files 无问题；
- 导入边界 PASS，原受控违规导入反例仍被拦截；
- pytest：**122 passed in 0.78s**（第一批 55 + 本轮 67）；
- sdist/wheel 构建成功，wheel 包含 canonicalization 模块。

临时日志 `/tmp/danus-p1-2-batch2.log`。测试覆盖 RFC 26 行、浮点舍入示例、键排序、重复/碰撞/非法 Unicode、精确长十进制、小 Decimal context、未声明数值不误转、无输入修改、列表保序及拒绝分支。独立向量预期字节均通过。

Windows：py -0p 只列 Python 3.14，py -V 实际 **3.14.5**；没有 Windows CPython 3.12。未安装 Windows 解释器/依赖，也未以 3.14 代替验收；**Windows/Linux 一致性待完成**。具备 3.12 环境后用相同锁与测试向量执行纯契约测试，逐个比较预期字节，记录补丁版本/依赖版本/输出；Windows 不能代替 Linux 运行验收。

## 5. 远端 CI 与同步边界

本轮匿名 GitHub API 返回 repository private=false、visibility=public；工作流仍是标准 ubuntu-24.04、contents:read、15 分钟、无付费调用/上传制品/缓存。2026-11-12 复核 GitHub 官方免费规则（https://docs.github.com/en/actions/concepts/billing-and-usage）：公开仓库标准托管 runner 免费。本轮不改工作流触发规则。

API 列出的唯一运行仍为 `30e97ad85c5333d92ee8cac8aa7ec2f27e0e17f3`，success：
https://github.com/wangshunshun0816/ai_for_science/actions/runs/43036783370 。
**此运行只证明旧 P1-1，第一批和第二批均尚无远端 CI 证据。**

触发条件受阻：Ubuntu/Windows 未发现 gh，Ubuntu 无 credential.helper；浏览器自动化初始化失败，错误 `windows sandbox failed: helper_unknown_error: setup refresh had errors`。未读取/输出令牌。没有可用的已认证 Actions 写入入口，未把未触发记录为失败或通过。

完成同步后人工触发步骤：进入仓库 Actions → P1-1 foundation checks → Run workflow → main；核对实际 head SHA 为本批代码提交或包含它的后续提交；提供 run URL 后跟踪全部 jobs 到 completed，记录实际 SHA/结论/警告。本次本地成功不能代替远端证据。提交/推送实际结果在本轮最终报告中给出；提交日志按前一 HEAD 登记，当前提交下次补登。

未改三份设计基线与九个金样例，未创建数据库或运行上游代码；P0/R01 后续验收、P1-2 整体验收均不升级为通过。
