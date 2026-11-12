# Third-party notices

本文件记录第三方来源及实际采纳状态，不声明 Danus-AI 自有代码的项目许可证。

## Danus（P0 只读参考，尚未迁移源码）

- 上游项目：https://github.com/frenzymath/Danus
- 固定提交：`6d92e8d415933ca2ef52fd1a4da73fdfcd418f1c`
- 本地只读基线：`~/upstream/Danus`（WSL 原生克隆）。项目许可证副本取自固定提交的 LICENSE 原始字节。
- 上游 LICENSE 中的版权声明：Copyright 2026 FrenzyMath
- 许可证：Apache License, Version 2.0，SPDX `Apache-2.0`。
- 上游 LICENSE 原文副本：[licenses/Danus-LICENSE.txt](licenses/Danus-LICENSE.txt)。
- 当前采纳状态：仅路径/行数/许可证/HEAD 核对；尚未复制或修改第三方源码，未作为可编辑依赖安装，未运行独立数学服务。
- 修改记录：[docs/implementation/upstream-differences.md](docs/implementation/upstream-differences.md)。

P1 按文件或组件登记受控迁移、隔离保留或关闭。受控迁移保留相关版权和许可声明，并在修改文件中显著标明已修改；本汇总文件不能替代文件内的修改标识。

分发包含上游作品或其衍生部分时，携带适用许可证及声明；如果所采用版本含 NOTICE，保留与采纳部分有关的归属声明。当前文件路径盘点未发现名为 NOTICE 的文件，不代表嵌套组件或未来依赖无需进一步核查。

依据：[Apache-2.0 第 4 节](https://www.apache.org/licenses/LICENSE-2.0)。后续新增依赖逐项登记，不把上游根目录许可证自动套给所有嵌套组件。

## rfc8785 0.1.4（P1-2 通用规范化依赖）

- 来源：https://github.com/trailofbits/rfc8785.py ，通过 PyPI 安装，版本及下载哈希固定于 uv.lock。
- 用途：RFC 8785 UTF-8 字节序列化；不含 Danus-AI 的业务投影或授权规则。
- 许可证：Apache-2.0。原始许可副本：[rfc8785-0.1.4-LICENSE](docs/implementation/licenses/rfc8785-0.1.4-LICENSE)。
- 原始 LICENSE SHA-256：0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594。
- 本轮用户于 2026-11-12 明确批准新增该依赖；无传递依赖。未修改/复制其源码，分发时保留原包许可证及归属声明。
- RFC 独立测试数值及来源说明：[canonicalization vectors](tests/fixtures/canonicalization/README.md)。
