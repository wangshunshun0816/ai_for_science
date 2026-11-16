# P1-2 候选改版使旧批准不再适用的独立金样例

对应开发指南 §3.4／§5.3、大方案 §6.4／附录 C，以及[准备文档 §5.2](p1-2-contract-readiness.md#52-尚需新增的独立参考)的独立样例缺项。样例使用原有 CandidateDraft、CandidateRecord、candidate:v1 科学投影和精确批准守卫，原有科研字段及 Schema 均沿用。

同租户、同项目、同候选 ID 的两份合成材料只改 prediction，将“三题”改为“四题”。这是版本变更夹具，无实测结果。两版规范 UTF-8 逐字手列在 [old](../../tests/fixtures/candidate_revision/old.canonical.json) 和 [new](../../tests/fixtures/candidate_revision/new.canonical.json)，无 BOM 或末尾换行。以下摘要独立用 sha256sum 对手列文件计算并固定于测试；被测实现仅生成实际值以供比较。

| 版本 | 完整 SHA-256 |
|---|---|
| 旧版 | 454d422c23bb3b8f95db5986e997de3caa8fb106c5b9ef11caa5f23f51486f7a |
| 新版 | 1b433cad6edbd0cbf5f52c2d2ea9b37698133e009abdbe5ed3034be1d9f510e7 |

[专项](../../tests/contracts/test_candidate_revision_golden.py)经 validate_object 校验草稿和权威记录，经 content_id 计算及复核科学版本，最后通过 require_approval 核验。两个精确引用均先验证可读、归属一致和规范就绪。使用同一份有效、未过期的旧批准时，旧版通过，新版返回 APPROVAL_INVALID。用途、定位、归属、有效性保持一致，唯一变化是批准目标的科学版本。另行绑定新版的合成批准通过。合成批准仅证明契约行为，真实签发服务仍待验收。

- Ubuntu 3.12.16 完整工程检查 444 项通过、18 项隔离 SQLite 测试跳过，wheel／sdist 构建通过。本包不建库。[完整日志](evidence/p1-2-candidate-revision-verify.log)
- Windows 3.12.14 既有隔离环境经 uv sync --offline --locked 核验，专项 1 项通过。双方使用相同依赖锁，两版规范 UTF-8、完整摘要及三条批准路径结果一致。[Ubuntu](evidence/p1-2-candidate-revision-ubuntu.json) · [Windows](evidence/p1-2-candidate-revision-windows.json)
- 原九件金样例、手算、设计基线、依赖锁及生成物原字节保留。对应提交的远端 CI 待核验。

本交付关闭整体台账的“候选核心改版使旧批准不适用”独立样例缺项。其余独立参考（包括抽样不确定及独立复现降级）、通用合同覆盖、待决权限和整体出口仍按[收尾计划](p1-2-closure-plan.md)跟踪。P1-2 和 P1-3 整体仍待验收。
