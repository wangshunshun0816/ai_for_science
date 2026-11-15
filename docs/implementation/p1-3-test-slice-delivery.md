# P1-3 私有候选最小测试切片交付

依据 [P1-3 专节](decisions/A0-P1-2-consolidated-decisions.md#p1-3-测试切片独立签收)签收提交 a51b5b91b47770a705a3531efdabb27ef318c514、[切片计划](p1-3-minimum-slice-plan.md)、AGENTS.md 和 D-02。开工时本地 HEAD 与远端 main 同为签收 SHA，工作区干净。范围限 WSL 隔离测试切片，人工验收另行登记。

## 建库前现场证据

2026-11-16 的现场探测在 /home/wangshunshun/.cache/danus-ai/pytest/preflight-xxi9w1dm/。当时新建 danus-ai、pytest 和该隔离目录，全部 0700，文件 permissions-probe.txt 为 0600。进程及新建对象均为 UID/GID 1000/1000，umask 077。最终路径无符号链接，本地 /dev/sdd 挂载为可写 ext4。写入、fsync 和回读 28 字节一致。可用 1,022,571,024,384 字节、67,046,084 个 inode。已有父目录权限未改，现场探测目录未被用作数据库。

每个集成用例新分配独立 slice- 目录。每次打开 SQLite 前检查 WSL、UID/GID、进程 umask、逐路径解析、模式及挂载，核验数据库及存在的 WAL/SHM 文件。数据库位置为 db/control.db，制品及暂存为 artifacts/ 与 artifacts/.staging/，快照为 backups/，恢复为 restore-check/。实际路径、挂载和可用字节见[专项日志](evidence/p1-3-test-slice-recovery.log)。测试进程使用 64 MiB 和 128 个可用 inode 作为本切片合成数据及恢复的最低余量检查。该工程阈值无需推及运行库容量。用户级配额工具不可用，未核验配额。小文件探测与合成测试均无法证明未来数据量、并发或运行环境的容量。

## 实现与可复验行为

- [迁移](../../danus_ai/storage/migration.py)用版本 1 建立账户、个人租户、项目与精确候选版本。账户与租户使用延迟外键，材料通过复合租户／项目外键隔离。每连接启用外键并要求 WAL。仅有一版初始迁移，支持重开已迁移测试库。
- [仓储](../../danus_ai/storage/candidates.py)用 CandidateDraft、CandidateRecord、candidate:v1 已批准投影和逐源引用守卫。只读端口提供 Scope／来源就绪与权限事实。服务写入精确归属、创建元数据、初始状态及空批准引用。使用规范序列化的完整记录 SHA-256 校验制品字节。受信委派复验当前租约、用途、操作及签发时归属版本。查询先核目标及数据库复合键，再打开制品、校验摘要及记录版本，仅返回签收列明的候选定位和正文。
- 制品同挂载暂存、校验、原子发布后记录事务提交。失败可能保留供日后引用复核的孤立制品，客户端不会得到成功，库内无悬空有效记录。本切片未启用自动清理。
- [备份恢复](../../danus_ai/storage/recovery.py)在测试库写锁内用 SQLite backup API 获取快照并保存所引用制品与摘要清单。恢复先校验快照及全部制品，再写独立目录，复核迁移版本、完整性、外键及摘要。恢复后查询继续核验当前外部委派，撤销照常阻断。当前撤销来源由夹具提供。缺当前授权事实时查询失败。生产增量回放、清理策略、长期备份容量和运行恢复目标待后续验收。

## 验证

Ubuntu WSL 的 CPython 3.12.16、SQLite 3.53.1。使用锁定环境运行：

    umask 077
    export DANUS_P13_TEST=1
    PYTHONPATH=. uv run --no-sync python -m pytest -q -s tests/storage
    bash scripts/verify.sh

[独立专项](../../tests/storage/test_candidate_slice.py) 8 项通过。独立手列候选投影和查询返回验证科学版本与返回字段。验证空库迁移、WAL 外键及活跃侧文件权限、两个租户同候选 ID／同科研哈希、精确版本与并发同版本保存、无关归属和错版／已撤销在制品读取前拒绝、Scope 错修订阻断、数据库写入故障无有效版本。恢复验证 SQLite 完整性、外键、制品校验、跨租户及跨项目隔离、撤销与损坏快照拒绝。

恢复见 [专项日志](evidence/p1-3-test-slice-recovery.log)，本次快照在 /home/wangshunshun/.cache/danus-ai/pytest/slice-xhhxzfmx/backups/，恢复在同 run-id 的 restore-check/，已校验制品 SHA-256 为 245fd66339cac6745eaa998e51b4d206195173f51f2167a9206029788ea70b91。测试数据保留在各自隔离目录供复核。

[完整工程日志](evidence/p1-3-test-slice-verify.log)记录 Ruff、mypy、导入边界、Schema 检查、451 项测试及 wheel/sdist 构建通过。普通 CI 不设置 DANUS_P13_TEST，现场 SQLite 专项仅在签收路径显式启用。远端 CI 核验见下节。原九个金样例、手算、设计基线、Schema 及依赖锁均原字节保留。

测试身份与就绪来源为受控合成事实。实际覆盖仅为本地私有单项目候选、初始迁移、版本写入、受权精确读取及独立恢复。真实认证、运行库、预算、外发、模型及付费资源未启用。P1-2、P1-3 的整体出口及人工验收仍独立登记。

## 远端 CI 与独立复核

[运行 43777277306](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43777277306) 最终 Success，实际 SHA 为 6e01f5c3e6c2cfd34d66f051363b79df95d421b4。[foundation](https://github.com/wangshunshun0816/ai_for_science/actions/runs/43777277306/job/133006325106) 的 Checkout、固定工具与 Python 安装、Locked local checks and build 均为 success。详细步骤日志端点返回 HTTP 404，未取得子命令输出、远端测试计数或构建产物。任务页显示 Checkout 的 Node.js 20 弃用警告。

该 SHA 的工作流及验证脚本未设置 DANUS_P13_TEST，未启用 SQLite 集成测试。WSL 上以关闭开关复验得到 8 skipped。原交付的 SQLite 8 项及完整工程 451 项为 WSL 本地证据。远端成功只覆盖既有工程 CI。

另用隔离目录 slice-zldf5gpl 复验。注入延迟外键导致 COMMIT 失败，新增记录及触发器副作用回滚；未引用制品留存但未被备份纳入。禁止读取原库与原制品后，恢复和查询成功，数据库实际只打开备份与恢复库，查询只打开恢复目录制品。观察到索引 digest 被篡改为同 ID／同科学版本的外租户制品时，会先打开外租户制品再拒绝，未返回正文。该项待整改，人工验收另行登记。
