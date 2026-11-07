# 开发前基线记录

日期：2026-11-07。依据 A0 决定 D-01 至 D-03，见 [决定记录](decisions/A0-P0-6-D01-D03.md)。本记录覆盖环境切换及验证。

## WSL 恢复与可行性

上轮 Ubuntu 启动时因发行版的 `ext4.vhdx` 缺失，挂载返回 `CreateInstance/MountDisk/HCS/ERROR_FILE_NOT_FOUND`。故障发生在 Linux 命令执行前，与项目配置无关。用户已重建 Ubuntu，新磁盘位于 `D:\wsl\ubuntu\ext4.vhdx`。

Ubuntu 以 WSL2 运行。Linux 用户为 `wangshunshun`，家目录为 `/home/wangshunshun`，`findmnt` 核实为 ext4。Git 为 2.53.0。使用 [uv 官方安装器](https://docs.astral.sh/uv/getting-started/installation/)将 uv 0.13.7 安装到 `~/.local/bin`，再通过 `uv python install 3.12` 安装并实际运行 CPython 3.12.16。项目的 `.python-version` 仍为 3.12。

| 访问路径 | 测试结果 |
| --- | --- |
| `wsl.exe -d Ubuntu -- bash -lc '…'` | 在 `~/danus-ai-probe` 写入并读回 `wsl-exe.txt`。Linux Git 在临时仓库返回 `true`。 |
| `\\wsl.localhost\Ubuntu\home\wangshunshun\danus-ai-probe` | Windows 读回 Linux 标记文件，写入并读回 `unc.txt`。Windows Git 经 UNC 对临时仓库返回 `true`。 |

从 Linux 读回 UNC 写入的标记后，已删除并确认探测目录不存在。

## 权威开发 checkout

权威 checkout 为 Ubuntu ext4 上的 `/home/wangshunshun/danus-ai`（`~/danus-ai`）。Windows 编辑入口为 `\\wsl.localhost\Ubuntu\home\wangshunshun\danus-ai`。项目的 Git、uv 及 Python 命令在 WSL 内运行。`D:\AI_for_science` 作为只读归档副本，后续开发提交在 WSL checkout 进行。

WSL 副本从 [GitHub](https://github.com/wangshunshun0816/ai_for_science) 克隆。迁移记录提交前，`main` 指向 `0659c72e10991473edd4019606b372048a534252`，10 笔可达提交的完整哈希与 D 盘一致。`git fsck --full` 通过，工作区干净。三份设计文档与 `licenses/Danus-LICENSE.txt` 的 SHA-256 均与既有登记值一致。

D-02 确认本地 SQLite/WAL 为唯一生产后端。数据库尚未创建。建库时须在 WSL 中验证数据库及 WAL/SHM 的实际路径和文件系统，并明确运行目录、制品、备份与权限。

## 上游审计复算

使用 Ubuntu 上的 Python 3.12，从 WSL checkout 运行原脚本，并传入 `--upstream /mnt/d/Danus_Coding/reference/Danus`。输出与已提交 manifest 未达到逐字节一致。Windows Git 使用 `core.autocrlf=true`，Linux Git 默认检查时将 Windows checkout 中 213 个 CRLF 路径报告为修改，因此输出的工作树匹配标记和状态列表发生变化。对同一 checkout 仅在单次诊断命令中传入 `-c core.autocrlf=true` 后，Git 状态报告恢复为空。原脚本、manifest 内的 Windows 路径和上游 checkout 均保留原状。
