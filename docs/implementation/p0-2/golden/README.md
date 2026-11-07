# P0-2b 五类金样例草案

唯一底本为大方案 v1.2 附录 C 的固定四题枚举。四题标签、基线预测、评价单位 `unique_item` 与锁定阈值沿用底本。有限否定仅替换方法预测，删除和重复分支仅改变收到的观测行。所有 JSON 使用 `fixture_only: true` 与 `fixture:` 别名。

**期望值由 Codex 手算，监工独立复算；正式独立复核人待定。** 本目录尚无独立复核结果登记。

## 载荷与隔离

- `positive.json` 把 C.2–C.4 原始载荷归入 `input` 和 `expected` 两部分，保留原字段和数值。各文件的 `expected.expected_derivation` 是给复核者看的逐题推导。
- 其余文件以 `input.base_fixture_ref` 引用正面样例的 **input**，逐个独立应用本文件所列变化。替换 `evaluator_only_rows` 表示以该数组作为收到的观测，`append_evaluator_only_rows` 表示在原行后追加。报告改动、故障观察及重复请求分别描述该分支的独立条件。别名在各场景内使用，继承的运行引用和原始载荷不会预先授予变体科学资格。
- 外层结构、变更描述和期望断言供 P0 评审，字段名不定义正式 R02 Schema。Evaluator 持有 `evaluator_only_rows` 中的隐藏标签及期望区。A5 只接收获准的输入视图。正式 fixture 需另行提供可信归属、授权及必要的精确绑定。

## 样例索引

| 文件 | 类别 | 附录 C 对应分支 | 期望与手算依据 |
| --- | --- | --- | --- |
| [positive.json](positive.json) | 正面 | C.2–C.4 原样例 | baseline 对 q1、q2，2/4 = 0.5。method 对 q1、q2、q3，3/4 = 0.75。q4 两臂均错。差值 0.25 大于 0.1，为 `improvement`。G2 无阻断时才可接受。 |
| [bounded-negative.json](bounded-negative.json) | 有限否定 | C.5 结果差值为 0 | 仅把 method 的 q3 预测从 1 改为 0。两臂均对 q1、q2，均错 q3、q4，各 2/4 = 0.5，差值 0。结论 `bounded_no_meaningful_gain` 仅对这四题有效。 |
| [incomplete-missing-q4.json](incomplete-missing-q4.json) | 未决 | C.5 删除 q4 | q1、q2 两臂均对，q3 仅 method 对，q4 缺失。锁定集合仍是四题，科学资格为 `incomplete`，不得用三题重算。 |
| [error-audit-timeout.json](error-audit-timeout.json) | 未决 | C.5 审计超时 | 逐题结果沿用正面样例，baseline 为 2/4，method 为 3/4。G0/G1 正常，G2 超时按角色规格记为 `error`，不产生 `accepted`。 |
| [rejected-number-mismatch.json](rejected-number-mismatch.json) | 拒绝 | C.5 数字被改成 0.50 | 原预测仍给出 3/4 − 2/4 = 0.25。报告单独改为 0.50 后发生错配，G0 拒绝。 |
| [rejected-overbroad-scope.json](rejected-overbroad-scope.json) | 拒绝 | C.5 声称泛化到所有分类任务 | 两臂正确题仍为 q1、q2 和 q1、q2、q3。差值仅覆盖已枚举四题，拒绝原过宽提交。收窄后须另建提交。 |
| [rejected-duplicate-q3.json](rejected-duplicate-q3.json) | 拒绝 | C.5 复制 q3 十次 | q1、q2、q3、q4 各计一次。十个附加行都是 q3，故 `unique_item` 仍为 4，拒绝声称有 14 个评价单位。 |
| [recovery-collector-crash.json](recovery-collector-crash.json) | 恢复 | C.5 收集进程崩溃 | 原节点已完成，仍可按 q1、q2 与 q1、q2、q3 核对两臂结果。恢复原尝试的收集与对账，不重复运行。 |
| [recovery-idempotent-submission.json](recovery-idempotent-submission.json) | 恢复 | C.5 重复提交相同幂等键 | 两次请求引用同一四题结果，原正确题数为 2 和 3。内容与幂等键相同，返回原 submission，不重复建图。 |

## P1 抽样 fixture 缺口

严格意义的 `outcome=inconclusive` 在此处指抽样推断下证据不足。本底本是有限总体的完整枚举，无法产生该类统计结论。缺题的 `incomplete` 是科学资格，审计超时的 `error` 是处理状态，均不填为 `inconclusive`。真正的 `inconclusive` 样例留给 P1 抽样 fixture。当前完整枚举的区间和 p 值为不适用，不构造新的统计量。
