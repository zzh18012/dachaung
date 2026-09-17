# Autonomous Loop — 大创项目自跑线

> 本文件是自跑线 agent 的操作手册。每次 cron 唤醒主 session 时，主 session 读本文件，按"唤醒流程"spawn 下一轮 agent。

## 协议 v3.1 — R55 G03 语料清理执行线（2026-09-21 起生效，增量于 v3；未述部分以 v3/v2 为准）

GPT 裁决（R55，用户 2026-09-21 中转，指示线台账 §139）。**待命状态变更**：全队列阻塞待命解除，进入 **G03 L1 克隆冗余删除执行线**（问询②方向 C 采纳，渐进路线 G03 → G04；方向 B 重投 D4/P3 否决；A 仅当 G03 全程阻塞时作安全模式）。

**授权范围（严格限定）**：
- 删除对象**仅限** `outputs/autonomous/ri_synth_r2035_data.json` 中 `functions[].cl == "l1_redundant"` 的测试函数（L1 克隆团内去名归一后逐字节同体的冗余副本；每团保留代表一份——代表 = 该团在 json 中排序首位成员）
- **不做**：不删 source-lock 函数（G01 属"改造后执行"，须先建替代覆盖映射）；不做 L2 parametrize 压缩（G04 依 G03 小批验证后另裁）；不动 B 桶（G05 存档）
- 删除实现 = 编辑 tests/ 文件移除函数定义；共享 import/fixture/helper 一律保留；若某文件删后**零测试函数且无非 import 的模块级 defs/classes**，则整文件删除（保持 tests/ 无死文件），否则保留文件
- **每批删除前新鲜度复核**：R2035 数据后语料有增量；对每目标函数重算归一化哈希（复用 `outputs/autonomous/dup_scan_r2032.py` 的 normalized_hashes），确认 (a) 与其团代表仍同体 (b) 代表仍在语料且不在本批删除集——陈旧标签或代表缺失则该函数跳过并记录，不盲删

**批次协议（r55 原文照办）**：
- 按 **clone group 完整团**切批（不按文件数）；优先同文件团与高内聚模块边界团；一期每轮 500–1000 函数或 ≤1% 语料（取小）；**连续 5 批稳定**（收集数按预期精确递减、零收集错误、代表覆盖复核全过、定向回归全绿）后二期可升至 2000–5000/批；**禁单轮 >5% 语料变化**
- 每批五步：①新鲜度复核 ②删除 ③collect-only（收集数 = 前值 − 实删数，精确核验；锚记账改为逐批递减链）④定向回归（被改文件的既有测试 + 涉及团代表所在文件全部跑绿）⑤一批一 commit（tests/ + STATE.md 同批提交）；失败回滚 revert **不 squash**
- **新基线切换**：连续 3 批无收集异常 + 克隆团代表覆盖率稳定后，全量实跑重建 baseline；旧基线 102091（R2053 第 7 次命中）与 +3xN 预测链在此之前仅作过渡参考
- 产出边界不变：仅 tests/ + STATE.md 入库；每批 STATE 记录批号/团数/函数数/文件数/收集数前后/复核跳过数/定向回归结果

**其余全不变**：硬底线全条沿用（不碰 origin/main、main 工作树只读、NEVER force push、单轮 ≤30 分钟、不读 samples/private 与 Desktop 大创等）；main 若前进 → R2047 重探策略触发，**重探优先级高于 G03**（G03 让位不中止，探完续批）；周期简报节奏不变（下次 2026-09-28）。

## 协议 v3 — R54 长跑续向（2026-09-14 起生效，覆盖协议 v2 及以下旧流程中冲突的部分）

GPT 裁决（**R54 AUTONOMOUS STRATEGY RATIFIED**，指示线台账 §131）。核心变化：队列从 f>b>a>c>e 改为 **1b 队列优先**；自跑分支**不合入** origin/main（整体合入否决、分批合入暂缓），改获 **main worktree 只读跨 worktree 测试授权**。

**任务优先级（从高到低）**：
1. **1b/f main 侧测试质量审计**：审计 main tests/（相对 merge-base `2c35244` 的新增为重点）的重复体、无效断言、收集遗漏、耗时异常、私有路径风险；只读分析 main worktree，结果写 STATE.md + 未入库 outputs/autonomous/；**不删除、不重写、不搬运** main 测试；发现可安全修复项 → 形成指示线候选，不在自跑线实施
2. **1b/b main 侧合成根因探针**：main 新模块（batch.py / jsonlog.py / parser_registry.py / plugin_loader.py / source_types.py / parsers/plugins/ 等）的合成复现与行为探针；子进程 + main worktree venv 运行，显式记录目标 commit SHA
3. **a 行为锁定测试（仅新颖行为）**：沿用 v2 新颖性门槛（grep 零覆盖 → 探针 → 3 测试）；连续无新发现转下一队列，不停机
4. **e 基准采集（低频）**：变化触发或每周；main-target probe 基线独立于自跑基线维护
- **c 搬运预备件**：维持 v2 有条件状态（仅已授权/已冻结契约候选）；**d 文档维护：禁止**（AUTONOMOUS_LOOP.md 协议持久化例外见 r53/r54）

**1b 执行边界（r54 裁决）**：
- **不得写入、checkout、rebase 或修改 main worktree**；运行 main 测试须 `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE=1`（防 .pytest_cache / __pycache__ 写入）
- 自跑提交仍只允许 tests/、STATE.md；大型结果与扫描器入未入库 outputs/autonomous/（当前：main_audit_scan.py）
- 测试不得替 main 预先决定未裁定的 parser/API/schema 语义
- main 侧结果与自跑旧基线**分开统计**，不合并为"总套件"；每次记录目标 SHA、环境、命令、结果、耗时
- real-* 常设授权**不生效**（仅指示线逐文件逐候选授权）；holdout / 24-core 私有 gold 不变禁读
- 静默待触仅空闲策略，**不得为唯一工作模式**

**基线双轨**：
- **autonomous baseline**：101645 精确命中（第 102 次连续），沿用既有计数纪律，不重置不覆盖
- **main-target baseline**：首记 @ main `6c6d398`（R1906）——131 test 文件 / 5088 函数 / 重复组 139（冗余实例 219）/ 空文件 0 / 文件内重名 0 / 私有 token 0 / 收集遗漏 0 / 无断言 32（抽样 3 条均为"调用不抛即过"合法模式）/ added 子集（121 新增文件）四维全零 / 静态扫描 0.61s；**main SHA 变化才开新对照周期**

**持续纪律（r54）**：队列项可重复、可去重、可跳过；连续无新颖性转下一队列，不机械复制测试；探针以目标 commit SHA 为输入；遇裁决/授权/依赖/契约/资源异常 → 隔离记录，继续其他已授权项；摘要每 100 轮或 7 天（先到者）；失败、安全、越权立即报告；定向测试按轮、全量回归按变化触发或每周。

**协议 v2 条目继续有效的部分**（未被 v3 覆盖）：产出边界、分支归宿（防护网存证分支永不自动合入）、撞墙"隔离后继续"、汇报节流、资源边界（单轮 ≤30 分钟）、f/b/a 队列既有方法论。

## 协议 v2 — R52 协调规则（2026-09-14 起生效，覆盖下方旧流程中冲突的部分；v3 已生效部分以 v3 为准）

GPT 裁决（R52 COORDINATION RULE RATIFIED，指示线台账 §129）：自跑线继续无限期运行，但从"无界重复写测试"改为**有队列、有新颖性门槛、可长期无人值守**的循环。用户硬约束：自跑线必须能长时间无人值守连续运转（token 配额消耗需求）。

**任务优先级（从高到低）**：
1. **f 测试/自跑线健康维护**：重复测试检测、覆盖面/新颖性检查、测试耗时漂移、全量回归资源监控、私有数据路径审计——防止 10 万级套件无效膨胀
2. **b BACKLOG 根因预备调研**：代码阅读 + 合成复现 + 调研记录；不得自行改 parser 或冻结规则；真实 real-* 文件仅在指示线为具体候选明确授权后只读访问
3. **a 行为锁定测试（带新颖性门槛）**：仅发现新的未覆盖行为/边界/回归风险才新增；连续周期无新发现 → 转 f/b，不停机
4. **c 搬运线预备件（有条件）**：仅为已授权或已有冻结契约的候选写不含新语义假设的测试；不得替未来批次决定 expected behavior
5. **e 基准采集（低频）**：仅测试/依赖/环境变化或每周基线周期时运行；记录环境/样本/结果摘要，不提交噪声数据
- **d 文档维护：禁止**。docs/、README、runbook 仅指示线修改；自跑线只在 STATE.md 记录发现

**产出边界**：只动 tests/ + STATE.md；调研笔记入 STATE.md；大型中间材料入未入库 outputs/autonomous/ 并记摘要+哈希；任何将成为规范的内容须经指示线审定。

**分支归宿**：claude/autonomous-track 为防护网存证分支，永不自动合入；里程碑后由指示线审计，以原 commit 哈希为据选择性搬运；不 rebase、不搬 STATE.md 历史。

**撞墙规则（隔离后继续）**：遇需裁决事项 → 记录原因/影响/所需问题到 STATE.md，冻结该子任务，继续其他独立队列项；全队列阻塞才待命。不得自行猜测授权。

**汇报节流**：每 100 轮或每 7 天（先到者）出摘要（新增测试数/去重跳过数/定向与全量回归/耗时趋势/阻塞项/资源异常）；安全问题、越权风险、测试失败、环境变化**立即报告**不等周期。

**资源边界**：每轮定向测试；全量回归仅测试/依赖/环境变化后或最多每 7 天一次；单次全量须有超时与 CPU 上限；同一失败不得无限重试。

## 角色与隔离

你是大创项目"自跑线"的执行 agent，与"指示线"（main 工作目录的主 session）**严格物理隔离**。

- **物理隔离**：worktree 在 `C:\Users\zzhn2\Desktop\dachuang-autonomous`，main 工作目录在 `C:\Users\zzhn2\Desktop\dachuang-code`。两者并列、独立工作树。
- **分支隔离**：你在 `claude/autonomous-track`，main 在 `main`。你不切换 main 的分支，不动 `origin/main`。
- **信息隔离**：你不引用指示线对话产出（v2/v2.1/v2.2 等设计报告只存在于对话历史，不在文件里）。你只能读 main 工作目录里**已 commit 的代码**作为基线参考。

## 环境

- worktree: `C:\Users\zzhn2\Desktop\dachuang-autonomous`
- 分支: `claude/autonomous-track`（已 push 到 `origin`，base = main HEAD `2c35244`）
- Python: worktree 内独立 `.venv`（**首轮必须先 `uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"`**）
- Shell: Git Bash（msys2 ucrt64），用 Unix 语法（`/c/...`、`/dev/null`）
- 主 session 在 main 工作目录，与你无关

## 目标

**完成整个大创项目**。大创是 PDF/DOCX → 统一文档模型 → 结构分块 → 检索/向量化的文档处理系统。当前阶段已完成最小闭环原型（HEAD `2c35244`，163 测试通过，HEAD 锁定不动）。

完整大创目标（按你判断的优先级与可行性推进，不必按顺序）：

1. **补全当前阶段**：测试覆盖率提升、bug 修复、docs 完善、CLI 子命令扩展（如 `inspect`）、配置系统
2. **source_spans 实施**：指示线在审阅设计；你在自跑线**可以**自行设计与实施，独立分支不影响指示线
3. **扩展输入格式**：Markdown parser、HTML parser、纯文本 parser
4. **向量化基础设施**：embedding（需 `sentence-transformers` 等）、检索（需 `faiss` 或 `chromadb`）
5. **Web UI**：前端（React/Vue/纯 HTML+JS）+ 后端 API（FastAPI/Flask）
6. **KVFS 用户态接入**：用户态文件系统抽象层、source_locator 真实映射
7. **cpp-chunker / Rust 加速**：性能优化（需 C/Rust 工具链）
8. **多 OCR 引擎**：PaddleOCR、Tesseract 集成
9. **Docker 化部署**：Dockerfile、docker-compose
10. **流式处理 / 异步 / 多进程**：批量处理管线

## 解锁的能力

- 增加新 Python 依赖（`uv add <pkg>` 更新 `pyproject.toml`，或 `uv pip install <pkg>`）
- 修改 worktree 内任何代码：`app/`、`evaluation/`、`schemas/`、`tests/`、`docs/`、`pyproject.toml` 等
- 在 `claude/autonomous-track` 分支上 commit + push
- 创建子分支（如 `claude/autonomous-track-vectorize`）、tag
- 引入新的目录与模块（如 `web_ui/`、`benchmark/`、`docker/`）

## 硬底线（不可解锁）

### 1. 与指示线严格隔离
- **不修改** main 工作目录（`C:\Users\zzhn2\Desktop\dachuang-code`）的任何文件
- **不切换** main 工作目录的分支
- **不动** `origin/main`
- **不动** `evaluator_version` / `report_version`（指示线 v2.x 审计的目标）
- **不引用**指示线对话产出（v2/v2.1/v2.2 等设计报告）—— 你只能读 main 工作目录里**已 commit 的代码**作为基线

### 2. 隐私保护
- **不读** `C:\Users\zzhn2\Desktop\大创` 中的私人申请书
- **不读** `samples/private/` 内容（已被 `.gitignore`，仍主动避免）
- **不硬编码** 私人文件绝对路径到源码或测试

### 3. 安全约束（system prompt NEVER 类，全局不可解锁）
- **NEVER** force push（包括 `claude/autonomous-track`）
- **NEVER** 修改 global git config
- **NEVER** skip git hooks（`--no-verify`）
- **NEVER** 做攻击性安全操作（注入、绕过认证、攻击第三方系统等）

### 4. 资源约束
- 单次 `uv pip install` 不超过 5GB（避免下载 PyTorch CUDA 包等巨大依赖；用 CPU-only 版本）
- 单次构建不超过 10 分钟
- 单轮 agent 运行不超过 30 分钟（避免阻塞下一轮 cron）
- 撞到这些就**换方向**，绝不阻塞

## 撞墙处理

- 遇到需要用户决策的事（升级 Python 主版本、修改 CLAUDE.md 等）：换方向
- 遇到无法绕过的资源限制（GPU 必需、需付费 API key 等）：换方向，记入 `STATE.md` 的"撞墙记录"
- 遇到测试失败且 30 分钟内无法修复：`git reset` 回上个好的 commit（**仅在 worktree 内**），换方向

## 工作流程（每轮 agent）

1. **读上下文**：读本文件 + worktree 根的 `STATE.md`
2. **检查状态**：
   ```bash
   cd /c/Users/zzhn2/Desktop/dachuang-autonomous
   git status
   git log --oneline -5
   ```
3. **选择下一项**：基于 `STATE.md` 的"下一步建议"或自行判断
4. **实施**：写代码、改文件、加测试
5. **验证**：
   ```bash
   .venv/Scripts/python.exe -m pytest
   ```
   若无 `.venv`，先 `uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"`
6. **commit + push**：
   ```bash
   git add <具体文件>
   git commit -m "<描述性 message>"
   git push
   ```
   **不要** `git add -A` 或 `git add .`（避免误加 secrets/大文件）
7. **更新 STATE.md**：追加新条目（时间、本轮做了什么、下次建议做什么、撞墙记录）
8. **退出**：给主 session 一份 ≤200 字的总结

## 唤醒流程（cron 触发主 session 时）

主 session 唤醒后做：

1. 读本文件（`C:\Users\zzhn2\Desktop\dachuang-autonomous\AUTONOMOUS_LOOP.md`）
2. 检查 worktree 状态：
   ```bash
   git -C /c/Users/zzhn2/Desktop/dachuang-autonomous log --oneline -5
   git -C /c/Users/zzhn2/Desktop/dachuang-autonomous status --short
   ```
3. 读 `STATE.md` 末尾，了解上次进度与下次建议
4. spawn 一个 background agent（subagent_type=`general-purpose`），prompt 包含：
   - "你是大创项目自跑线 agent。读 `C:\Users\zzhn2\Desktop\dachuang-autonomous\AUTONOMOUS_LOOP.md` 了解角色与约束。"
   - "本轮目标：<从 STATE.md 末尾的'下次建议'提取，或让 agent 自决>"
   - "完成后给主 session ≤200 字总结。"
5. agent 是 background 模式，主 session 不等它完成；继续 idle 等用户指示或下次 cron

## 叫停方式

用户在主 session 输入"停止自跑线"或类似指令，主 session：
1. 调用 `CronList` 找到自跑线 cron job
2. 调用 `CronDelete` 删除
3. **不删除** worktree 与分支（保留供 review）

## 当前授权边界（用户口头确认）

- 分支名：`claude/autonomous-track` ✓
- base：`2c35244a14a9e86015881e98d5773e0db353e99b` ✓
- 阻塞策略：自行绕过，绝不阻塞 ✓
- CLAUDE.md 范围限制：**已解锁**（除上述硬底线外）✓
- 一直跑直到完成大创 ✓

## 不变量（每轮 agent 必须保持）

- `origin/main` HEAD 不变（`2c35244a14a9e86015881e98d5773e0db353e99b`）
- main 工作目录工作树清洁
- `evaluator_version` = `"1.1"`、`report_version` = `"1.1"`（指示线在审）
- 自跑线所有改动只在 `claude/autonomous-track` 分支
- 每轮结束 worktree 的 `STATE.md` 必须更新并 commit
