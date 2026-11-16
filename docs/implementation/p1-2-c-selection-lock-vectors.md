# C 组既有合同独立规范字节与摘要

状态为独立预期材料，尚未接入 C 组实现或测试。本材料只采用已有合同形状和摘要域。以下 JSON 行是逐字段独立手列的规范预映像；编码为 UTF-8，无 BOM、无末尾换行。复用上游预映像摘要的引用仅作字面量替换。完整 SHA-256 由 Python 标准库计算，并用 OpenSSL 对同一字节交叉核对；未导入产品代码或由被测实现生成预期。

示例中的 Scope、Dataset、CandidateHypothesis 和 Rationale 版本采用重复十六进制占位值，只用于序列化和引用形状对照。这些目标没有配套正文或权威事实，因此不得用于验证整条跨对象读链。下面三个目标版本仅为本合成材料的预期标识。DataExposure 的 SHA-256 只用于核对序列化，不能生成事件科学版本或充当权威证据。

| 预映像 | 规范 UTF-8 字节数 | 完整 SHA-256 |
| --- | --- | --- |
| FixedQuestion 正文 | 380 | `7f079b1f872d8e790990d3c9bd4ab8a7008cca501b5db7ce782efecc8d6eaa98` |
| FixedFamily 正文 | 363 | `d57b38f88fcdc16e97f0ae053a67603c174d01f2a15d3314148952922ffe6b3d` |
| FixedSelectionHistory 正文 | 569 | `92122aa8065c813a483fe304b0e859f69b51e82e2ea60b7359f7f8403f7a98cd` |
| SelectionTerms 批准条款预映像 | 394 | `408a186507d1f9850c860e790885939cee0f95ab617f0b7fcd247f5b6b88e0be` |
| ThresholdTerms 批准条款预映像 | 597 | `b62a07758614111f4570a75dbe6ca251eff293f287b946eb249e11e5c459302e` |
| 现有选题 ApprovalSubject 摘要预映像 | 425 | `b4e47a0c2440988961b448e159221fa6ffb98cc2eee6f1e11b36e8a2f9eaaf50` |
| DataExposure 规范序列化 | 370 | `226d0da80cc2bd34e51580ad99afb24604882a44792ea2f256a71596b07e600a` |

## FixedQuestion 正文

```json
{"direction":"greater","estimand":"准确率差","population_ref":{"content_version":"dataset:v1:2222222222222222222222222222222222222222222222222222222222222222","object_id":"four","object_type":"Dataset"},"scope_ref":{"content_version":"scope:v1:1111111111111111111111111111111111111111111111111111111111111111","object_id":"scope-c","object_type":"Scope"},"unit":"unique_item"}
```

合成预期版本为 `research_question:v1:7f079b1f872d8e790990d3c9bd4ab8a7008cca501b5db7ce782efecc8d6eaa98`。

## FixedFamily 正文

```json
{"candidate_refs":[{"content_version":"candidate:v1:3333333333333333333333333333333333333333333333333333333333333333","object_id":"candidate-c","object_type":"CandidateHypothesis"}],"question_ref":{"content_version":"research_question:v1:7f079b1f872d8e790990d3c9bd4ab8a7008cca501b5db7ce782efecc8d6eaa98","entity_id":"question-c","object_type":"ResearchQuestion"}}
```

合成预期版本为 `family_declaration:v1:d57b38f88fcdc16e97f0ae053a67603c174d01f2a15d3314148952922ffe6b3d`。

## FixedSelectionHistory 正文

```json
{"considered_candidates":[{"content_version":"candidate:v1:3333333333333333333333333333333333333333333333333333333333333333","object_id":"candidate-c","object_type":"CandidateHypothesis"}],"family_ref":{"content_version":"family_declaration:v1:d57b38f88fcdc16e97f0ae053a67603c174d01f2a15d3314148952922ffe6b3d","entity_id":"family-c","object_type":"FamilyDeclaration"},"question_ref":{"content_version":"research_question:v1:7f079b1f872d8e790990d3c9bd4ab8a7008cca501b5db7ce782efecc8d6eaa98","entity_id":"question-c","object_type":"ResearchQuestion"},"test_exposures":[]}
```

合成预期版本为 `selection_history:v1:92122aa8065c813a483fe304b0e859f69b51e82e2ea60b7359f7f8403f7a98cd`。

## SelectionTerms 批准条款预映像

```json
{"body":{"candidate_ref":{"content_version":"candidate:v1:3333333333333333333333333333333333333333333333333333333333333333","object_id":"candidate-c","object_type":"CandidateHypothesis"},"meaningful_delta":"0.1","scope_ref":{"content_version":"scope:v1:1111111111111111111111111111111111111111111111111111111111111111","object_id":"scope-c","object_type":"Scope"}},"domain":"approval-terms:v1"}
```

## ThresholdTerms 批准条款预映像

```json
{"body":{"direction":"greater","question_ref":{"content_version":"research_question:v1:7f079b1f872d8e790990d3c9bd4ab8a7008cca501b5db7ce782efecc8d6eaa98","entity_id":"question-c","object_type":"ResearchQuestion"},"rationale_ref":{"content_version":"rationale:v1:4444444444444444444444444444444444444444444444444444444444444444","object_id":"rationale-c","object_type":"Rationale"},"scope_ref":{"content_version":"scope:v1:1111111111111111111111111111111111111111111111111111111111111111","object_id":"scope-c","object_type":"Scope"},"unit":"unique_item","value":"0.1"},"domain":"approval-terms:v1"}
```

## 现有选题 ApprovalSubject 摘要预映像

```json
{"body":{"locator":{"purpose":"candidate_selection","record_id":"selection-c","revision":1},"project_id":"project-c","target":{"content_version":"candidate:v1:3333333333333333333333333333333333333333333333333333333333333333","object_id":"candidate-c","object_type":"CandidateHypothesis"},"tenant_id":"tenant-c","terms_digest":"408a186507d1f9850c860e790885939cee0f95ab617f0b7fcd247f5b6b88e0be"},"domain":"approval-subject:v1"}
```

## DataExposure 规范序列化

```json
{"exposed_at":"2026-11-12T00:00:00Z","project_id":"project-c","subject":{"data_ref":{"content_version":"dataset:v1:2222222222222222222222222222222222222222222222222222222222222222","object_id":"four","object_type":"Dataset"},"event_ref":{"record_id":"event-c","record_type":"DataExposure","revision":2},"principal_id":"reader-c","purpose":"read"},"tenant_id":"tenant-c"}
```

## 接入及边界

- 固定四题目标正文按本页比较规范字节和版本。历史保留问题与族的精确定位、原候选列表和空暴露列表。
- 条款摘要按既有批准域核对，选题主题绑定完整 SelectionTerms、精确批准定位、归属与候选版本。现有载荷覆盖范围不包含新增报告和预算绑定。本页未生成签名或签发事实。
- 历史暴露仅对比已定结构的序列化。事件精确修订与 Dataset 科学版本分别比较，现有测试引入授权前后读取计数和独立快照替换用例。
- 完整候选改版正反例继续使用[已验收向量](p1-2-candidate-revision-golden.md)。整体 Prereg 预映像沿用[第六批独立对照](p1-2-batch6-delivery.md)及[手列固定四题期望](../../tests/contracts/test_batch6.py)。原九个金样例和手算保持原字节。
- 七组向量纳入[同一纯契约实施包与验收](p1-2-c-selection-lock-fields.md#同一纯契约实施包与验收)。占位引用只用于本页逐对象对照；贯通夹具须改用可核验的独立目标正文及对应重算版本，补齐受信事实并另列受影响的独立预映像。新增合同的验收场景见[待审七项补充决定](p1-2-c-selection-lock-fields.md#c-组补充决定七项待-a0-签收)，尚无实测或跨平台证据。
