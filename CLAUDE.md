# CLAUDE.md（项目规则，给未来的 Claude 读）

## 项目目标（当前阶段）

构建"PDF/DOCX → 统一文档模型 → 基础结构分块 → Schema 校验 → JSON 输出"的最小闭环原型。

## 范围（本阶段明确不做）

- Web UI / 前端
- 真实 KVFS 接入（仅设计 `source_locator` 字段以便未来对齐）
- 向量化、Sentence-BERT、任何 embedding
- cpp-chunker / Rust 加速
- 多 OCR 引擎
- 内核代码 / FUSE / Docker / 数据库
- 流式处理 / 异步（多进程已于 Stage 8 批次 16 纳入，见"并行化"节）

## 并行化（Stage 8 批次 16）

- **批量处理**：`app.cli batch-parse` 支持多进程并行（默认 `min(cpu_count, 8)` workers）
- **Evaluation 并行化**：`evaluation.cli run --workers N` 文档级并行（默认 1=顺序行为不变）
- **已知限制**：pdfplumber C 库 segfault 可能破坏进程池（docs/BACKLOG.md）
- 小批次（<3 文件）或 workers=1 自动走顺序路径；tqdm 为可选依赖（未装降级为逐行进度）

## 结构化日志（Stage 8 批次 17）

- `app/jsonlog.py`：`JSONFormatter`（record.msg → event，extra= 字段顶层展开）+ `setup_logger`
- `batch-parse` 与 `evaluation.cli run` 均支持 `--log-file`（JSONL，append）与 `--verbose`（stderr）；默认零输出变化（NullHandler，防 lastResort 泄漏）
- 事件：batch_start / file_complete / file_warning / file_error（含 traceback）/ batch_complete；eval_start / doc_complete / doc_error / eval_complete
- 错误事件的文本字段名是 `error_message`（`message` 是 LogRecord 保留属性，extra 不可用）
- 已知限制：日志 append 不轮转（需手动清理）；traceback 首版不截断；timestamp 为 epoch 秒

## Parser 注册表（Stage 8 批次 18）

- `app/parser_registry.py`：`register`（装饰器兼容）/ `get_parser` / `discover_parser`（扩展名 → priority 最小者名称）/ `list_parsers`
- `pipeline.get_parser` 委托注册表，调用方接口不变；`--parser` 默认仍 fallback（零变化），显式 `--parser auto` 走扩展名发现
- Parser 元数据：`supported_extensions`（空 = 不参与发现，仅显式指定）与 `priority`（小者优先；平局先注册者胜 + UserWarning）；重名注册 import 时 ValueError
- 参考插件 `app/parsers/plugins/markdown_enhanced.py`（priority 5）：frontmatter 受限解析（仅扁平 key: scalar，嵌套/列表 warning 跳过）+ GFM 任务列表；外部插件 = 自定义模块 import + `@register`（无 entry_points 扫描）
- `app.cli list-parsers` 列出全部已注册 parser；evaluation 的 AUTO_PARSER_BY_SOURCE_TYPE 是 source_type 语义，与扩展名发现并存，评测不改

## 外部插件加载（Stage 8 批次 19）

- `app/plugin_loader.py`：`load_plugins(modules)`（dotted 模块名、按 CLI 出现顺序、fail-fast）+ `PluginLoadError`（code/plugin/error_type/error_message；标准 JSON 不含 traceback）
- `--plugin MODULE`（append 可重复）挂在 parse / batch-parse / list-parsers；validate 与 evaluation.cli 不参与；模块查找走 PYTHONPATH（不做文件路径加载）
- 错误契约：`ParserRegistrationError`（register 专用 ValueError 子类，重名/缺名）→ `plugin_register_failed`；其他导入期异常 → `plugin_import_failed`；重名冲突（含与内置同名）绝不静默覆盖
- `--parser` 去掉 argparse 静态 choices，插件加载后按注册表动态校验（`auto` 唯一保留名）；未知名 → 结构化 `unknown_parser` rc 1（此前 argparse rc 2，有意变更）
- 批量：父进程在池创建前加载（失败不启动批）；并行 worker initializer 重放加载 + multiprocessing.Queue 恰一次初始化回报，文件任务派发前校验，失败受控终止池（code 同上，回报超时 `plugin_init_report_timeout`，固定上限 120 秒，事件带 expected/received worker 数）；parse_one_file 有防御背板；`plugin_loaded.parsers_added` 为本进程首次加载真实增量（重复 --plugin 同模块只发一次事件，空表仅限预导入/未注册 parser 的真实幂等情形）
- JSONL：`plugin_loaded`（含 parsers_added，CLI 已预加载时为空表）/ `plugin_load_failed` + `batch_start.plugins`
- 已知边界：batch 目录递归扫描后缀固定三类，插件格式走单文件/glob

## source_type 受控扩展契约（Stage 8 批次 20）

- `app/source_types.py`：`SOURCE_TYPE_PATTERN=^[a-z][a-z0-9_]{0,31}$`；`LOCATOR_FAMILIES` 封闭四值（page_geometry/structural_index/line_address/container_line，**不新增**——新 family 需单独批次）；`BUILTIN_SOURCE_TYPE_FAMILIES` 六类型冻结映射；`normalize_*` 全部拒绝而非静默修正
- Parser 契约声明（register 强制）：`source_types` tuple（str=单元素；多格式 parser 如 fallback 声明 `("pdf","docx")`）+ `locator_family`（新类型必填；纯内置多类型必须 None）；类型→family 全局唯一绑定（先注册者胜，冲突 ParserRegistrationError）；同绑定多 parser 并存合法；读取统一走 `declared_source_types()`（str 归一）
- schema 0.6.0：顶层 source_type 改 pattern；0.1.0–0.5.0 守卫仍限内置六类型（历史不回写）；扩展类型 locator.family 必填且 ∈ 四值，形状按 family 路由（line_address → 新 `$defs/line_address_locator`）；内置六类型 0.5.0/0.6.0 形状完全一致；`SCHEMA_VERSION_CURRENT="0.6.0"`（models.py，唯一权威常量），writer 一律输出 0.6.0
- 运行时契约检查：`process_single` 在 schema 校验后、写盘前核对 source_type ∈ 声明集合 且 每个 locator.family == 全局绑定；违规 → `parser_contract_mismatch`（details 带 declared/actual/expected_family/element_ids）+ rc 1 + 不写盘；所有 parser 统一检查（内置同规）
- `validate` 子命令纯 schema 校验，不含注册表/契约检查（无 parser 上下文）
- `.myx` 全链测试插件在 `tests/test_plugin_myx_fullchain.py`（subprocess 走真实 CLI；测试专用，永不内置、不进 evaluation AUTO 映射）；评测 AUTO_PARSER_BY_SOURCE_TYPE 语义不变

## Parser 能力快照与发现解释（Stage 8 批次 21）

- `ParserCapability` frozen dataclass 六字段（name / source_types / locator_family / extensions / priority / version）：register() 校验通过即冻结快照存 `_capabilities`；registry 核心路径（discover / list / pipeline 契约检查）**只读快照**，注册后改写类属性不生效（行为收紧修复）；能力唯一来源 `_capabilities`，不建第三份缓存
- register 校验：`supported_extensions` 元素小写含点长度≥2（str=单元素，list 归一 tuple）；`priority` 正整数（拒 bool/0/负数）；`version` 非空 str；非法 → ParserRegistrationError（经插件通道仍 `plugin_register_failed`，错误码零新增）
- 发现确定性：全序 `(priority, 注册顺序)`，小者优先、平局先注册者胜 + UserWarning、无候选即失败不静默降级；`discover_parser_details(path)` 返回冻结 `DiscoveryResult`（候选+胜者+原因+平局，含 registration_order），`discover_parser()` 委托之（单一决策实现）；诊断不发告警
- extensions=输入能力，source_types+locator_family=输出契约，两轴独立不映射；`list-parsers` 表格含六列（None 显示 "-"），`list-parsers --json` 输出 `list_parsers()` 行原样（(priority, name) 稳定序）
- 本批不做：extension→胜出 parser 展示与 resolution report CLI（留批次 22）、schema 变更（schema_version 不升）、插件目录扫描/pip entry points/网络市场/动态安装/GUI

## 选择解释 CLI（Stage 8 批次 22）

- `app.cli explain-parser <input> [--plugin MODULE ...] [--json]`：解释 `--parser auto` 的选择——extension、候选表（name/priority/registration_order，胜者标记）、winner、reason、平局信息；registry 零改动（唯一实现文件 `app/cli.py`）
- 关键边界（裁决 D2）：只取 `path.suffix`，**不读文件内容、不实例化 parser、不 parse**；文件不存在也可解释；输出含免责说明（"仅按扩展名解释，未读取文件内容"）
- warning 边界（裁决 D3）：解释通道**不重放** `discover_parser()` 的平局 UserWarning（执行时告警、解释时陈述，语义不同）；平局信息入报告（tied_names + reason"平局：先注册者胜"）
- `--json`（裁决 D4）：**显式构造**五字段 {extension, candidates[{name, priority, registration_order}], winner, reason, tied_names}——不用 `dataclasses.asdict` 直接序列化（CLI JSON 是稳定外部契约，防未来内部字段泄漏）
- 错误契约零新增：无候选 → `unsupported_type`（rc 1 结构化 JSON）；`--plugin` 失败 → `plugin_import_failed` / `plugin_register_failed`（批次 19 通道，加载序先于解释，与 parse 一致）
- discover 算法 / 选择规则 / warning / schema / parse 默认行为全部零变化；不做 `--all` 全量矩阵（会滑向 registry analysis）、不做批量解释、不做 dry-run parse

## 解析竞争审计（Stage 8 批次 23）

- `app.cli audit-parsers [--plugin MODULE ...] [--json]`：注册表级观察——extension universe = 已注册 capability snapshot 的 extensions 并集（经 `list_parsers()` 读快照，字典序稳定输出）；每扩展构造伪路径 `Path("x"+ext)` 委托 `discover_parser_details()`（单一决策实现，不复制排序）；registry/discovery 零改动（实现文件仅 `app/cli.py`）
- `status` 是 CLI 派生展示字段（derived presentation field），**禁止**反向进入 DiscoveryResult：单候选 `uncontested` / 平局 `tie` / 否则 `priority_competition`；`summary` 仅四项计数（extension_count / uncontested / priority_competition / tie），禁止健康/风险/推荐评分与"最佳 parser"排名（audit 是观察不是治理）
- tie human 行显式含决胜三要素：winner name + winner registration_order + "先注册者胜"说明（Phase A 修正裁决，格式如 `<- 平局：先注册者 X 胜（registration_order=N）`）；audit 通道零 UserWarning（执行时告警、解释/审计时陈述）
- `--json` 显式构造（D4 原则沿用）：`{"extensions": [{extension, candidates[{name,priority,registration_order}], winner, reason, tied_names, status}], "summary": {...}}`
- 空注册表 → 空报告 rc 0（只读诊断语义，不制造错误）；不实例化 parser、不读文件、不 parse；`--plugin` 复用批次 19 契约（加载先行，`plugin_*` 错误码零新增）
- 不做：explain-parser --all（单输入职责）、插件目录扫描 / entry points / 动态安装 / 网络（沿用）、audit 结果持久化/缓存、schema/source_type/family 改动

## Parser 身份与来源追溯（Stage 8 批次 24）

- 能力快照追加 identity/provenance 四字段：`module` / `qualname`（cls.__module__ / cls.__qualname__ 注册瞬间冻结）+ `loaded_via` / `plugin_spec`（registration context 调用瞬间消费）；值域封闭 `builtin|plugin`；无上下文注册（内置/预 import，含随项目分发的 markdown_enhanced）→ `builtin` + `plugin_spec=null`
- registration context（registry 私有 ContextVar，默认栈式可嵌套、异常安全，最内层生效、退出恢复外层）：loader（`load_plugins`）对每个 spec 独立进入 `_plugin_registration_context(spec)`，import 与其触发的注册 hook（顶层 @register / 副模块 / helper 转注册）全程在上下文内；plugin_spec 存规范化前原始字符串、拒绝路径形态；**禁止任何事后推断**（cls.__module__ / sys.modules / 已加载模块集合 / import graph 均不作加载来源依据——插件模块被普通 import 预导入即 builtin）；同一 class 不同时刻经不同 spec 注册各 snapshot 各归各（不按 class identity 合并）；装饰器与直接调用不构成不同 loaded_via
- `app.cli inspect-parser <name> [--plugin MODULE ...] [--json]`：只读 `_capabilities` 快照查询 identity/provenance，不实例化 parser、不做选择解释/竞争审计；`--json` 显式六键 {name, version, module, qualname, loaded_via, plugin_spec}（builtin 时 plugin_spec 为 null **不省略**；version 用注册表冻结值；无 `__file__`/绝对路径/cwd/环境变量/import search path）；human 恰六项（None 显示 "-"，与 list-parsers 同规）
- `--plugin` 加载先于名字查询：初始未知、加载后出现 → 可查询；插件失败 → `plugin_import_failed` / `plugin_register_failed`（不落成 unknown_parser）；插件成功但名字不存在 → `unknown_parser` rc 1；provenance 纯只读，不参与 duplicate/priority/discovery/resolution/audit/错误分支
- list-parsers 六键 / explain 五键 / audit 键集零变化（键集锁测试守护）；不做：给既有三个 JSON 加字段、文件系统信息、运行时活读、哈希/签名/源码比对、依赖图/传递 import、网络查询、inspect --all、schema/source_type/family/priority/discovery 改动

## 环境

- 工作目录：`C:\Users\zzhn2\Desktop\dachuang-code`（已是 git 仓库，远程 `zzh18012/dachaung`）
- Python 解释器：`C:\Users\zzhn2\AppData\Local\Programs\Python\Python312\python.exe`（**官方 CPython 3.12.10**）
- 严禁使用 PATH 里的 mingw Python 3.14（uv 会拒绝，wheel 兼容性差）
- 虚拟环境：`.venv/Scripts/python.exe`
- 包管理：uv（已有 0.11.11）
- Shell：Git Bash（msys2 ucrt64），用 Unix 语法（`/c/...`、`/dev/null`）

## 常用命令

```bash
# 创建/同步虚拟环境
uv sync --python "C:/Users/zzhn2/AppData/Local/Programs/Python/Python312/python.exe"

# 运行测试
.venv/Scripts/python.exe -m pytest

# 解析（PDF/DOCX 输入）—— 注意子命令 parse
.venv/Scripts/python.exe -m app.cli parse <input.pdf|input.docx> -o <output.json>

# 切换 parser（默认 fallback，因 kreuzberg 实测给不出 elements 结构）
.venv/Scripts/python.exe -m app.cli parse <input.docx> -o out.json --parser kreuzberg

# 仅校验已生成的 JSON（独立子命令，不要把 JSON 当成 PDF 输入）
.venv/Scripts/python.exe -m app.cli validate <output.json>

# Stage 2：跑评测（清单驱动）
.venv/Scripts/python.exe -m evaluation.cli run \
  --manifest samples/private/devset/manifest.json \
  --output outputs/evaluation-pilot-baseline.json \
  --parser fallback --max-chars 800

# Stage 2：校验评测报告
.venv/Scripts/python.exe -m evaluation.cli validate-report outputs/evaluation-pilot-baseline.json

# Stage 8 批次 16：批量解析（目录 / glob / 单文件 → 多进程并行 + summary.json）
.venv/Scripts/python.exe -m app.cli batch-parse samples/private/docs -o outputs/batch --workers 8

# Stage 8 批次 16：评测并行（--workers >1 文档级并行，默认 1 顺序行为不变）
.venv/Scripts/python.exe -m evaluation.cli run \
  --manifest samples/private/devset/manifest.json \
  --output outputs/evaluation-parallel.json --workers 8

# Stage 8 批次 17：结构化日志（--log-file 建议写 outputs/ 下，gitignored；append 模式需定期清理）
.venv/Scripts/python.exe -m app.cli batch-parse samples/private/docs \
  -o outputs/batch --log-file outputs/batch.jsonl --verbose

# Stage 8 批次 18：parser 注册表（列出已注册 parser / 扩展名自动发现）
.venv/Scripts/python.exe -m app.cli list-parsers
.venv/Scripts/python.exe -m app.cli parse <input.md> -o out.json --parser auto

# Stage 8 批次 21：能力清单（机器可读 JSON，六字段/行）
.venv/Scripts/python.exe -m app.cli list-parsers --json

# Stage 8 批次 22：解释 --parser auto 的选择（不读文件内容）
.venv/Scripts/python.exe -m app.cli explain-parser doc.md
.venv/Scripts/python.exe -m app.cli explain-parser doc.pdf --json

# Stage 8 批次 23：审计注册表全局解析竞争
.venv/Scripts/python.exe -m app.cli audit-parsers
.venv/Scripts/python.exe -m app.cli audit-parsers --json

# Stage 8 批次 24：查询单个 parser 的 identity 与 provenance（只读快照）
.venv/Scripts/python.exe -m app.cli inspect-parser fallback
PYTHONPATH=path/to/plugins .venv/Scripts/python.exe -m app.cli inspect-parser my_parser \
  --plugin my_pkg.my_plugin --json

# Stage 8 批次 19：显式外部插件加载（dotted 模块名，PYTHONPATH 提供模块）
PYTHONPATH=path/to/plugins .venv/Scripts/python.exe -m app.cli parse doc.smk \
  -o out.json --plugin my_pkg.my_plugin --parser my_parser
.venv/Scripts/python.exe -m app.cli list-parsers --plugin my_pkg.my_plugin
```

## Stage 2 评测规则（当前阶段）

完整方法见 `docs/evaluation.md`。关键不变量：

- 不修改 `app/parsers/*`、`app/chunkers/*`、`app/pipeline.py`（评测只调用，不改算法）
- 计时只记 total；parse/chunk 未插桩，固定 null + reason=`not_instrumented`，不重复 total
- 比例指标分母为 0 时返回 null + reason，**不返回 1.0**
- 聚合按类型分开：counts 求和、success_rates 算 rate、ratio 各项 macro average、silent_drop 求和；**不混合出"综合分数"**
- `figure_caption_*` 消费 document.relations 的 `has_caption`（docs/relation-consumption-contract.md）；降级 null + reason（pipeline_failed/no_annotation/no_annotation_pairs/no_predicted_relations），不引入"最近图片"启发式
- `chunk_boundary_*` 一对一匹配，容差 `tolerance_chars`（默认 30）必须在报告中记录
- manifest 中 `path` 必须相对项目根 + 正斜杠；拒绝绝对路径与反斜杠；解析后必须位于项目根内
- `silent_drop_count` 必须基于 manifest 的 `expectations.element_count_by_type`；无 expectations → null
- 报告里写 `devset_status`、`file_count`、`content_group_count`、`pdf_count`、`docx_count`、`categories_covered`；不单看文件数判定完整性
- 当前 devset 固定 `incomplete`，所有数字称为 "pilot baseline / incomplete devset"，**不代表项目总体准确率**
- 原始评测报告 JSON 只写到 `outputs/`（gitignored），不提交 git；脱敏汇总需用户单独审阅

## Parser 选择策略

**默认走 `fallback`**（pdfplumber + python-docx）。

Kreuzberg 4.10.2 实测：
- 对 DOCX 调用 `extract_file_sync`，`elements` 字段始终为空（即使开 `include_document_structure=True`）
- 对手写最小 PDF，elements/pages/tables 全空
- 给不出 PDF 的 page/bbox，给不出 DOCX 的 paragraph_index

因此默认走 fallback，kreuzberg 适配器保留为可选路径（未来升级后可能启用）。
切换不会改业务代码，只改 CLI `--parser` 参数。

## 关键不变量

- Pipeline 在写盘前**必须**通过 JSON Schema 校验（schema.py validate）
- 单文件失败 → 结构化 errors JSON + 非零退出码，不崩溃
- 每个 chunk 必须有非空 source_element_ids
- PDF 与 DOCX 的 source_locator 结构不同（schema 用 if/then 区分）
- content 和 resource_path 至少有一个非 null（schema 用 anyOf 保证）
- "分块不丢不重"测试用 `normalize_text` 统一规则：所有空白压成单空格、strip 两端



## 禁止事项

- 不读取或复制 `C:\Users\zzhn2\Desktop\大创` 中的私人申请书
- 不在源码/测试/输出中硬编码私人文件绝对路径
- 不执行 `git commit` / `git push` 除非用户明确要求
- 不修改全局 Git 配置（`http.sslbackend=schannel` 已在 `.git/config` local 设置）
- 不使用 `sudo`（Windows 上无意义，Linux 上需用户确认）
- 不执行 `reset --hard` / `clean -fd` / `push --force` 等破坏性 Git 操作
- 不全局安装依赖（只用 `.venv`）
- 不安装系统级组件
- 不增加计划外的主要依赖（如需增加必须先询问用户）
- 不伪造测试结果

## 隐私约束

- 测试样例放在 `samples/private/`，已被 `.gitignore` 忽略
- 用户将手动放入：1 个无隐私 PDF + 1 个无隐私 DOCX
- 真实样例不存在时，相关测试应明确显示 SKIPPED 而非伪造通过

## SSL 配置来源

`http.sslbackend=schannel` 仅写在 `.git/config` 的 local 配置中，未污染 global。
原因：Git Bash 默认 OpenSSL 在该机器上访问 GitHub HTTPS 时会失败，切到 Schannel（用 Windows 系统证书）解决。
