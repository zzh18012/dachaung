# Autonomous Loop — 大创项目自跑线

> 本文件是自跑线 agent 的操作手册。每次 cron 唤醒主 session 时，主 session 读本文件，按"唤醒流程"spawn 下一轮 agent。

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
