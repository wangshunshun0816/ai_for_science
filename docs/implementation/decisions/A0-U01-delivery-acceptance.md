# A0 U-01 交付人工验收记录（草稿）

A0 已于 2026-11-11 完成验收，结论为通过，范围仅限 U-01 上游基线交付。

## 批准与交付依据

* 批准记录：[A0 决定：U-01](A0-U01-upstream-wsl-clone.md)。批准提交：a918001f88f6ad06157ddb79483f289a5bca95e0，作者 Danus\_Wang。
* 交付提交：00dd3de1e90d58756e50e9db1975d742a4246b70，作者 Codex，主题「U-01 切换到 WSL 原生只读上游基线」。
* [交付说明](../upstream-differences.md)记载执行依据为当时 A0 的聊天批准。批准文件提交晚于交付提交，本草稿保留该实际顺序。

## 已核实的交付证据

以下为 2026-11-11 在 Ubuntu 内完成的只读核对结果，由 Codex 整理供人工验收使用。

|核对项|证据与结果|
|-|-|
|固定 HEAD|/home/wangshunshun/upstream/Danus 的 HEAD 为 6d92e8d415933ca2ef52fd1a4da73fdfcd418f1c；.git/HEAD 直接记录该提交，处于分离 HEAD。|
|工作树及权限|Git status --porcelain 输出为空；递归 find 的 -perm /222 检查无输出，未发现带写权限位的路径。权限位可由所有者或特权用户更改，此证据不代表不可变存储。|
|两侧 tree|WSL 基线及 /mnt/d/Danus\_Coding/reference/Danus 历史副本的 HEAD 均为固定提交；HEAD^{tree} 均为 68116644a623580efb7a7510b84ed37465bce525。提交树一致不表示检出字节完全一致。|
|原始许可证|WSL LICENSE、固定提交中的 LICENSE 对象及项目 licenses/Danus-LICENSE.txt 的 SHA-256 均为 d51dbb6676bff13e23abd800608ec96bd6e637fd5b5194ef9ea8d848416d8ef3。|
|历史许可证|D 盘历史副本 SHA-256 为 61bd88cc691cd7683d203a92c8b8b2934bab9fd5f102fdd115ae3d5f261717a8；逐字节确认等于原始 LF 字节转换为 CRLF 后的结果，许可证文本相同。|
|manifest 更新|reuse\_manifest.json 已登记 WSL 路径及原始许可证哈希；91 个 Python 文件、17,073 行，逐文件路径及行数与交付提交之前一致。|
|审计复算|Ubuntu CPython 3.12.16 以 -B 执行项目 scripts/p0\_audit\_upstream.py，参数 --upstream /home/wangshunshun/upstream/Danus；标准输出与 manifest 在内存中逐字节比较，manifest\_byte\_equal: True。两者 SHA-256 均为 cc17837d2ec156f8a47dded6b94a3ba2dfd42ac8f1cb5ca0c78a6e4aaa98036c。未执行上游代码或测试。|

## 范围与限制

仅覆盖 U-01 只读基线切换、许可证字节登记及盘点复算。manifest 状态为 inventory\_only\_not\_stage\_acceptance，源码逐文件内容哈希为 not\_collected。本草稿不证明源码迁移、运行能力、模型资格或 P0 整体验收通过，不授予付费调用、发布或 P1 开工权限。核对未修改 D 盘副本或上游基线。

## A0 人工填写

|栏位|填写内容|
|-|-|
|确认人|Jack\_Wang|
|日期|2026.11.11|
|意见|已核对固定提交、只读权限、两侧 Git tree、许可证原始字节 SHA-256 及 manifest 复算结果。U-01 交付验收通过，验收范围限于本次上游基线交付。|
|验收结论|通过|



