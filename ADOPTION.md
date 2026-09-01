# 自跑线成果搬运台账（integration/autoline-adoption）

来源：ChatGPT 5.6 Sol 制定的搬运方案（2026-08-27，经浏览器交流确认）。
原则：**先封存基线；先搬证据、后搬能力；parser 逐家族，chunker 逐策略；
已知缺陷修完才启用；旧格式指标与新增格式指标分开报告；整支自跑线不直接合并。**

## 一、冻结快照（已完成）

| 项 | 值 |
|---|---|
| 指示线基线 tag | `stage2-baseline-main` = 2c35244 |
| 自跑线快照 tag | `autoline-snapshot` = fcad055 |
| 环境 | Python 3.12.10；uv.lock sha256 前缀 7496e34c84857c84 |
| manifest | samples/private/devset/manifest.json，sha256 前缀 15f60b11f1321064 |
| 正式重跑报告 | outputs/evaluation-stage2-baseline-frozen.json（schema 校验通过） |
| 重跑指标 | pipeline 2/2 成功；schema_valid=1.0；pdf/docx_locator=1.0；image_resource=1.0；chunk_reference_intact=1.0；text_preservation_equal=1.0；char_multiset P/R=1.0/1.0；heading_boundary=1.0；chunk_boundary_precision=0.5294（1 doc 参与）；devset_status=incomplete（2 文件） |

## 二、搬运顺序（按方案）

1. 测试与证据资产（fixture/种子/bug 最小复现；不带算法修改）
2. 统一模型兼容性（新解析器所需数据结构；改 schema 须独立契约迁移 PR）
3. Markdown parser（三段式：机械搬运 / 回归+修崩溃族 / 注册启用）
4. HTML parser（机械搬运 / 修两个静默丢失缺陷 / 注册启用）
5. text、ipynb parser（MD/HTML 稳定后）
6. chunker 策略（sequential / 标题硬边界 / isolated_table / 长文切分，各一 PR，旧默认不变）
7. CLI inspect 与最终 wiring（最后）

## 三、自跑线 app 层资产清单（git diff --stat 2c35244..autoline-snapshot -- app/）

| 资产 | 规模 | 对应搬运阶段 | 已知依赖/缺陷 | 状态 |
|---|---|---|---|---|
| app/parsers/markdown_parser.py | +326 | 阶段 3 | 崩溃族：标记+≥2 尾随空格+空内容 → unexpected_parser_error | 待搬 |
| app/parsers/html_parser.py | +446 | 阶段 4 | 嵌套表格丢外层文本；th 内 img 静默丢弃 | 待搬 |
| app/parsers/text_parser.py | +136 | 阶段 5 | 无 | 待搬 |
| app/parsers/ipynb_parser.py | +227 | 阶段 5 | 无 | 待搬 |
| app/chunkers/structural.py | +153/-x | 阶段 6 | 与评测"不改 chunker"约束交叉，需评测周期切换 | 待搬 |
| app/cli.py | +476 | 阶段 7 | inspect 子命令 | 待搬 |
| app/pipeline.py | 43 行改动 | 阶段 3-5 随解析器 | 自动选择逻辑 | 待搬 |
| app/models.py | 6 行改动 | 阶段 2 | 确认是否触发 schema 契约迁移 | 待搬 |
| app/parsers/fallback_parser.py | 3 行改动 | 阶段 2 | 微小 | 待搬 |
| tests/（约 1800 文件，10 万+ 测试） | +874k 行 | 分类随各阶段搬 | 契约/性质测试优先，特征化测试随家族 | 待分类 |

## 四、统一模型兼容性审计（2026-08-27 完成）

四处检查结论（stage2-baseline-main vs autoline-snapshot）：

| 检查点 | 差异 | 分类 | 处置 |
|---|---|---|---|
| models.py 字段/枚举 | SourceType +4（markdown/html/text/ipynb） | bucket 1 additive | 进契约 PR |
| models.py 字段 | Chunk.source_spans 可选字段 | bucket 1 additive | 进契约 PR |
| schemas/document.schema.json | source_type enum +4；4 个新 if/then + locator $defs；chunk.source_spans 可选数组 + source_span $def | bucket 1 additive（仅新类型触发） | 进契约 PR |
| Chunk.to_dict 序列化 | asdict 无条件序列化 → 空 source_spans:[] 会进旧 PDF/DOCX 输出 | **bucket 2** | 契约 PR 改为空时省略键（已实现） |
| app/pipeline.py | 解析器注册 +4（阶段 3-5 材料）；image_output_dir_for 纯重构 | 不属契约 | 推迟随各阶段 |
| app/parsers/fallback_parser.py | 题注正则 [\.、\s]→[\.、:\s]（"Table 1:" 现算题注） | **旧行为变更** | 严禁进契约 PR；单独 PR + 旧格式评测对照 |
| app/evaluation/ | 零差异 | — | 报告校验器无隐式假设变化 |

契约 PR 内容（integration/autoline-adoption）：
- app/models.py（自跑线版 + to_dict 空 span 省略）
- schemas/document.schema.json（自跑线版 additive 全量）
- tests/test_contract_adoption_v1.py（6 测试：旧形状不变/新枚举过/非法拒/locator 必填/span 序列化）
- 验收：全套旧测试 + 旧 PDF/DOCX manifest 评测重跑与冻结基线对比

### schema_version 版本政策（2026-08-27 定案：精确 schema 快照）

采纳 ChatGPT 5.6 Sol 指示，放弃此前"兼容家族"草案：版本必须对应**精确契约**，
避免"版本相同却无法互相验证"。版本映射：

| 契约 | 旧版本 | 新版本 | 语义分界 |
|---|---|---|---|
| 统一文档 schema | 0.1.0 | 0.2.0 | 0.1.0 仅旧 PDF/DOCX 形状且无 source_spans；0.2.0 才有新 SourceType/locator 分支/spans |
| manifest | 1.0 | 1.1 | 1.0 仅旧格式与旧 expectation 键；1.1 才允许 markdown/html/text/ipynb 与新键 |
| report | 1.1 | 1.2 | 1.1 保持旧结构；含 expectation_checks / per-doc check 键必须标 1.2 |
| evaluator | — | 1.2 | provenance 可追踪 |

实现要点：
- `Document.effective_schema_version()`：source_type 属新四类或任一 chunk 带
  source_spans → 0.2.0；否则 0.1.0。旧 PDF/DOCX 输出继续生成 0.1.0，
  与冻结基线字节一致
- 三张 schema 均为版本条件分支（allOf/if/then），而非不断扩展却声称旧版本
- 测试矩阵（tests/test_version_semantics.py）：1.0+新键失败 / 1.0+markdown
  失败 / 同内容 1.1 通过 / report 1.1+新分节失败 / UDM 0.1.0+markdown 或
  spans 失败、0.2.0 通过 / 冻结旧 manifest、旧结构报告、旧 PDF/DOCX 输出继续通过
- 任何再次扩展契约 → 新版本号 + 独立契约 PR，不得在旧版本号下加键

## 五、评测 manifest 起草（2026-08-27 完成）

三份独立 manifest（不触碰哈希 15f60b11 的 Stage 2 manifest；expectations 全按规格人工给定，非 golden）：

| manifest | 位置 | 文档数 | 覆盖 |
|---|---|---|---|
| markdown-dev-v1 | samples/private/devset-md/ | 6 | 标题树/嵌套+任务列表/围栏变体/参差表/CRLF+Unicode+全角/链接图片裸URL |
| html-dev-v1 | samples/private/devset-html/ | 5 | 标题段落+内联/列表/表格/实体+可恢复畸形/script-style 排除 |
| known-regressions-v1 | samples/private/devset-regressions/ | 3 | BUG-md-1 / BUG-html-1 / BUG-html-2 最小复现 |

新增规格键（runner PR 后已可执行，见下）：
`forbidden_markers`（不得出现的文本）、`must_not_error_codes`（不得出现的错误码）、
`max_silent_drop_count`（静默丢弃数上限；替代最初草稿的 forbidden_silent_drop，更可判定，
声明它必须同时声明 element_count_by_type）。
holdout manifest（不参与调参）留待 parser 搬运完成后另建。

### holdout manifest 冻结（2026-08-27，MD/HTML 各一份）

| manifest | 位置 | 文档数 | manifest sha256 前缀 | 覆盖 |
|---|---|---|---|---|
| holdout-md-v1 | samples/private/holdout-md/ | 4 | f637dd28de85bfb2（manifest 1.1） | setext 标题+thematic break / 嵌套引用 / 行内格式+转义 / 内嵌 HTML+自动链接 |
| holdout-html-v1 | samples/private/holdout-html/ | 4 | 3ceb4f212dc60b3b（manifest 1.1） | blockquote+pre / dl+br / 注释与 script-style 排除（forbidden_markers 首次实际使用）/ thead-tbody-colspan |

注：holdout 冻结后因版本语义 PR 把 manifest_version 升到 1.1（纯版本声明变更，
内容与 expectations 未动），哈希随之更新为上表值。三份 dev manifest 同步升 1.1：
devset-md bce257755967e834、devset-html 82b0ec83d13f04f4、
devset-regressions 8e5ecd3e3e44d756。

**哈希沿革与废止声明（2026-08-27，ChatGPT 5.6 Sol 两轮指示补记）**：
上表 holdout 哈希为最终正式冻结值。完整沿革链（旧哈希 → 修改原因 →
新哈希 → 首跑候选），历史值全部废止，不与正式版本并称冻结集：
- holdout-md-v1：f274bb076c5542a0（初版冻结，manifest 1.0）
  → 版本语义 PR 纯版本声明 1.0→1.1（内容与 expectations 未动）
  → e08b50ada20f577f
  → 首次运行前冻结核对更正（规格裁决：MD-DEV-006 图片行非段落、
  MD-HOLD-001 setext 不支持、MD-HOLD-002 引用合并，见下段）
  → **f637dd28de85bfb2（正式冻结集）→ 首跑候选 bc714f3**
- holdout-html-v1：74e1631be285aff1（初版冻结，manifest 1.0）
  → 版本语义 PR 纯版本声明 1.0→1.1 → 5decd9940de62567
  → 首次运行前冻结核对更正（规格裁决：HTML-DEV-004 未闭合 p 合并、
  HTML-HOLD-001 blockquote/pre 各成段、HTML-HOLD-002 补 paragraph 计数、
  REG-HTML-002 删 image alt marker，见下段）
  → **3ceb4f212dc60b3b（正式冻结集）→ 首跑候选 0fec2f8**
- 两份 holdout 的首次正式运行均使用更正后清单（首跑报告永久保留，
  哈希 49d15a0650fefc46 / 5fe5878b8d770b7b，不重跑不覆盖；后续运行
  一律标作复跑）。devset 哈希同理以更正段记录的最终值为准
  （devset-md d41d5e6d54902160、devset-html 3b72b05620d6b9d8、
  devset-regressions 030f6401af7acf5e）。
**此后两份 holdout manifest 不得再修改**（新 expectations 争议只能另建新版本
清单，不得在 v1 上改动）。

**冻结核对更正（2026-08-27，MD 机械搬运时发现，先于任何评测运行）**：
机械搬运后用搬运版 parser 逐份核对了全部 MD expectations 与文档化规格，
发现三处我起草时的规格错误并更正（非调参——依据是 parser 文档化规格，
且发生在首次运行之前）：
- MD-DEV-006：paragraph 2→1（图片行不是段落）；IMG_ALT_DESC / fixture-image.png
  两个 marker 删除——image 不参与文本投影，alt/resource_path 由 image 计数与
  image_resource_exists_ratio 覆盖（ChatGPT 5.6 Sol 确认此分工）；补
  http://example.net（在段落文本内）
- MD-HOLD-001（setext）：heading 2→删除、paragraph 2→4——parser 文档明确
  不支持 setext 标题（下划线式并入段落文本）
- MD-HOLD-002（blockquote）：paragraph 1→3——连续 > 行合并为单段落是文档化规格
更正后哈希：devset-md d41d5e6d54902160、holdout-md f637dd28de85bfb2。
MD-DEV-001..005、MD-HOLD-003/004 核对无误。

规则：
- expectations 全部按规格人工给定（与 devset 同纪律，非 golden）
- 计数断言为"下限"语义：多出的未声明类型不计违规，缺漏才触发 silent_drop；
  语义不确定的结构（hr、blockquote 归属、dl、pre）只声明 marker，不声明计数
- 不参与任何调参 / 修 bug 决策；MD/HTML 候选完成前不得运行
- 首次正式运行报告原样存档（含失败），作为泛化证据
- 冻结后样本与 manifest 不再修改；发现期望写错 → 在本台账登记并单独说明，不悄悄改

### Runner PR（evaluator v1.2，2026-08-27）

让 manifest 契约可执行，不改 parser/chunker/pipeline：
- 实现 `required_markers` 求值（自 schema 起声明但从未消费）+ 新增
  `forbidden_markers` / `must_not_error_codes` / `max_silent_drop_count` 三键
- marker 匹配基于 elements 规范化投影（非 image content 以 \n 连接后
  normalize_text；选 elements 而非 chunks，避免 chunker 词内硬切误报）
- per_doc 新增四个 `*_check` 指标（value 含 expected/actual/passed）；
  summary 新增 `expectation_checks` 分节（evaluated/passed/failed 分开计数）
- manifest 严格校验：schema additionalProperties:false 拒未知键与类型错误；
  加载器交叉校验 max_silent_drop_count 必须伴随 element_count_by_type
- manifest/report schema 的 source_type 枚举扩至 markdown/html/text/ipynb（additive）；
  report_version 接受 1.1 与 1.2（冻结基线报告仍有效）；EVALUATOR/REPORT_VERSION → 1.2
- 三份 manifest 修正：devset_status 改合法枚举（dev-v1→incomplete、
  known-regressions-v1→complete）；REG-HTML-002 补 element_count_by_type（table:1 image:1）
- 验收：全套测试 191 passed；旧 PDF/DOCX manifest 重跑与冻结基线
  既有指标零差异（新增键纯 additive；旧 manifest 的 required_markers 首次求值即通过）；
  新旧报告均通过扩展后 evaluation-report Schema 校验

### 版本语义 PR（2026-08-27，接 ChatGPT 5.6 Sol 修正）

Runner PR 后追加（不重写 f85bddd 历史）：按"精确 schema 快照"修正版本语义，
UDM manifest_version enum+条件分支、manifest 1.0/1.1 快照、report 1.1 禁新分节、
Document.to_dict 动态选版本、五份新 manifest 升 1.1。
验收：206 tests passed；旧 manifest 重跑既有指标与冻结基线零差异；
冻结 1.1 报告与新 1.2 报告均通过校验；真实 fallback pipeline 的
PDF/DOCX 输出仍为 0.1.0 且通过校验。

## 六、缺陷登记（评测期只登记不修）

| ID | 缺陷 | 严重度 | 修复时机 |
|---|---|---|---|
| BUG-md-1 | markdown 标记+≥2 尾随空格+空内容 → 崩溃 unexpected_parser_error | 高（显式崩溃） | MD parser 启用前 |
| BUG-html-1 | td 内嵌 table，外层单元格文本静默丢失 | 最高（静默丢内容） | HTML parser 启用前 |
| BUG-html-2 | th 内 img 静默丢弃（无 image 元素、无警告） | 最高（静默丢内容） | HTML parser 启用前 |

回归语义（修复目标）：
- BUG-md-1：至少不再 unexpected_parser_error；规定该行为忽略/普通文本/空节点之一
- BUG-html-1：外层文本与内层表格都保留，顺序稳定不重复
- BUG-html-2：图片按统一模型保留；模型不支持时必须显式诊断，不得静默消失

## 七、评测矩阵（每个高风险 PR 必跑）

1. 旧格式回归：原 PDF/DOCX manifest，指标/规范化 JSON 哈希/静默丢弃数不得退化
2. 新格式独立评测：MD、HTML 各自单独统计，不并入旧基线分母
3. chunker 隔离评测：冻结统一模型 fixture，查不丢/不重/顺序/边界
4. 端到端：parser → model → chunker → schema → JSON，真实 manifest

## 八、git 操作约定

- 单一目的、干净适用的提交：`git cherry-pick -x <sha>`
- 混合/依赖中间态/大体量：以自跑线代码为来源在 main 架构上重写 PR，描述列来源 tag 与 commit 范围
- 本分支（integration/autoline-adoption）只做搬运集成，不合任何未修已知缺陷的 parser 启用

## 九、Markdown parser 三段式搬运

### 提交 1：机械搬运（2026-08-27 完成）

- app/parsers/markdown_parser.py：自 autoline-snapshot（fcad055）逐字节搬运，
  零行为改动；未注册未启用（pipeline/registry/CLI 均未触碰）
- 测试搬运：test_parsers_markdown_edges*.py 全部 20 个文件 + 
  test_parsers_markdown.py（裁掉 2 个依赖注册/CLI 的端到端测试，
  按三段式计划在提交 3 原样搬回，裁剪点留注释）；共 1284 tests passed
- BUG-md-1 以 strict xfail 登记（tests/test_bug_md1_regression.py，
  4 个崩溃形态 + 1 个邻域不回归测试）；修复在提交 2
- 同语料对照：devset-md(6) + holdout-md(4) + regressions md(1) 共 11 文件，
  两仓 parser 输出 11/11 一致（模 source_path 与预期的 schema_version
  0.1.0→0.2.0 差异；BUG-md-1 文件双方同样崩溃 = 崩溃对等）
- 前置核对：base.py / parsers/__init__.py 与自跑线内容一致（仅行尾差异）

### 提交 2：修 BUG-md-1 + 参数化回归（2026-08-27 完成）

- 根因：`_ATX_HEADING_RE` / `_UNORDERED_LIST_RE` / `_ORDERED_LIST_RE` 的
  `\s+(.+)` 在标记后跟 ≥2 尾随空白时回溯让 group 捕获单个空白，
  strip 后为空 → push 出空 content Element → `Element.__post_init__`
  ValueError 穿透 parse（pipeline 包装为 unexpected_parser_error）
- 修复语义（2026-08-27 与 ChatGPT 5.6 Sol 确认）：空标记行 → 忽略该行
  （不发空节点、不发空 chunk、不崩溃），记 `empty_markdown_construct_ignored`
  警告（现有 warnings 通道，details 带 line/construct，不扩 schema）；
  该行仍中断段落吸收（块级边界）；空标题不污染 section_path
- 修改点：markdown_parser.py 三处（atx_heading / unordered_list_item /
  ordered_list_item）push 前空值守卫 + 模块 docstring 补语义
- tests/test_bug_md1_regression.py：去掉 xfail，全参数化矩阵
  （标记 6 × 尾随空白 6 × eof_newline × CRLF × 夹心 = 288 参数）+
  夹心不变式 / 整文件仅空标记 / 警告 details / section_path 不污染 /
  段落中断 / 邻域不回归 / REG-MD-001 fixture
- tests/test_parsers_markdown_edges18.py：提交 1 按崩溃现状锁定的
  test_space_only_heading_crashes 改为 test_space_only_heading_ignored
  （提交 1 曾锁定崩溃、提交 2 修复，模块 docstring 同步）
- 验收：全套 1788 tests passed（0 xfail）；11 文件语料对照——
  10 个非回归文件与 autoline-snapshot 输出仍逐字节一致（修复零外溢），
  REG-MD-001 修复后解析且 expectations 精确满足（heading:2 paragraph:1、
  3 marker 全命中、无 error、2 条 empty_markdown_construct_ignored 警告），
  autoline 侧同文件仍崩溃 = 修复对等性证据
- 缺陷登记表 BUG-md-1 状态：已修复（本提交），MD parser 启用前置条件清除

### 提交 3：注册启用 + 评测矩阵（2026-08-27 完成）

- 注册（最小改动，无自动选择逻辑，默认 parser 仍 fallback）：
  - app/pipeline.py get_parser 增加 markdown 分支（与自跑线同形；
    html/text/ipynb 留阶段 4-5；image_output_dir_for 重构未搬）
  - app/cli.py parse --parser choices += markdown
  - evaluation/cli.py run --parser choices += markdown（自跑线评测从未接
    markdown，此为搬运线补齐，属评测模块自身 PR 范畴）
- 搬回提交 1 裁掉的两个端到端测试（原样）：pipeline e2e + CLI e2e
- 评测矩阵（GPT 门）：
  1. 全套 1791 tests passed（含旧 169 条时代测试 + 搬回 e2e）
  2. 旧 PDF/DOCX manifest 重跑 vs 冻结基线：既有 summary/per_doc 指标
     零差异（仅 Runner PR 已验收的 expectation_checks additive 分节）
  3. markdown-dev-v1（6 文档）：6/6 pipeline_success、schema_valid、
     text_preservation_equal 全 True、chunk_reference_intact_ratio=1.0、
     char_multiset P/R=1.0、heading_boundary=1.0、silent_drop=0、
     required_markers 6/6 通过
  4. known-regressions-v1 仅 REG-MD-001（过滤 manifest 于 outputs/）：
     pipeline_success、must_not_error_codes 通过（无 unexpected_parser_error）、
     required_markers 通过、silent_drop=0、schema_valid=True
  5. Markdown 端到端：CLI parse .md → JSON schema 校验通过（e2e 测试内）
  6. 重复运行一致性：同输入两次 process_single，规范化输出（去 source_path）
     完全一致；输出 schema_version=0.2.0、7 elements → 4 chunks
- chunker 交叉：无缺陷暴露（reference/text/boundary 指标全满），无需暂停
- 评测报告均通过 evaluation-report 1.2 Schema 校验

## 十、HTML parser 三段式搬运

### 提交 1：机械搬运（2026-08-27 完成）

- app/parsers/html_parser.py：自 autoline-snapshot（fcad055）逐字节搬运
  （cmp 一致），stdlib html.parser 零外部依赖；未注册未启用
- 测试搬运：test_parsers_html_edges.py + edges2..23 共 23 文件 + 
  test_parsers_html.py（裁掉 2 个依赖注册/CLI 的端到端测试，
  按三段式计划在提交 3 原样搬回，裁剪点留注释）；
  test_parser_html_bq_li_p_ol_start.py 整文件依赖 process_single，
  同样推迟到提交 3
- BUG-html-1 / BUG-html-2 以 strict xfail 登记
  （tests/test_bug_html_regressions.py，10 xfail + 邻域/fixture 3 pass）：
  按 GPT 指示 xfail 断言"未来正确行为"（外层文本与内层表格都保留、
  顺序稳定、img 保留或显式诊断），不把缺陷行为固化为期望；修复在提交 2
- 同语料对照：devset-html(5) + holdout-html(4) + regressions html(2) 共 11 文件，
  两仓 parser 输出 11/11 一致（模 source_path 与预期的 schema_version
  0.1.0→0.2.0 差异；BUG-html-1/2 文件双方同样丢内容 = 缺陷对等）

**冻结核对更正（2026-08-27，HTML 机械搬运时发现，先于任何评测运行）**：
按 MD 的教训，首次运行前逐条核对了全部 HTML expectations 与文档化规格，
发现四处我起草时的期望错误并更正（依据：parser 文档化规格与已确认的
marker 投影语义，发生在首次运行之前）：
- HTML-DEV-004：paragraph 3→2——未闭合 `<p>` 会吸收后续文本合并为单段
  （搬运版实际行为；fixture 意图"可恢复畸形"不丢内容，marker 全命中）
- HTML-HOLD-001：paragraph 2→3——blockquote 与 pre 各成一个 paragraph
  （kind=blockquote / preformatted，文档化规格）
- HTML-HOLD-002：补 paragraph:1——dl 不计数的豁免只覆盖语义不确定结构
  （dl 本身），普通 `<p>` 应声明计数
- REG-HTML-002：required_markers 删除 REG_TH_IMG_ALT——image alt 在元素
  metadata，不进文本投影（与 MD-DEV-006 更正同类，ChatGPT 5.6 Sol 已确认
  该分工）；BUG-html-2 的门是 element_count_by_type image:1
  + image_resource_exists_ratio，保持不变
更正后哈希：devset-html 3b72b05620d6b9d8、holdout-html 3ceb4f212dc60b3b、
devset-regressions 030f6401af7acf5e。主仓 samples/private 副本已同步。
HTML-DEV-001..003、005、HTML-HOLD-003/004 核对无误。

### Markdown 候选封存 + holdout-md 首跑（2026-08-27，ChatGPT 5.6 Sol 指示）

- EVALUATOR_VERSION 1.2 → 1.3（提交 bc714f3）：1.2 evaluator 无法运行
  markdown manifest，同版本不同能力损害复现；REPORT_VERSION 保持 1.2
  （报告结构未变）；HTML 注册时再升 1.4
- 冻结 holdout-md 首次正式运行（候选提交 bc714f3，evaluator 1.3）：
  - **4/4 全绿**：pipeline_success、schema_valid、silent_drop=0、
    required_markers 4/4 通过，无任何 failed check
  - 首次报告永久保留：outputs/evaluation-holdout-md-first-run.json
    （gitignored 本机资产），通过 evaluation-report Schema 校验
  - 封存记录：候选 SHA bc714f3、manifest sha256 前缀 f637dd28de85bfb2
    （与冻结值一致，未改动）、报告 sha256 前缀 49d15a0650fefc46
  - 无失败 → 无需分类实现缺陷/规格争议，无新增 regression

### 提交 2a：修 BUG-html-1（2026-08-27 完成）

- 根因（instrumented trace 定位）：内层 `<table>` start 被忽略（不压栈），
  但其后的内层 `<tr>/<td>/data` 仍落在**外层**表格状态上——`<tr>` 处理器
  把外层 cell 缓冲直接置 None（外层文本 "OUTER" 在此被丢弃）；内层
  `</table>` 又把**外层**的栈弹出，产出的表格是内外混合体
  （rows=[[], ["INNER"]]，外层文本丢失）
- 修复语义（ChatGPT 5.6 Sol 2026-08-27 确认）：
  - 内层 table 压入独立上下文（rows/lines/row/cell/nested 栈，depth 递增），
    在其 `</table>` 作为独立 table element 解析一次
  - 嵌套点前：外层 cell 待定文本 → paragraph element（line locator）
  - 嵌套点后：pop 回外层时重开 cell 接收后文，`</td>` 收尾时同样 → paragraph
  - 每段文本恰好出现一次；内层文本不折叠进外层单元格；外层表格保留
  - 元素顺序：前文本段 → 内层表格 → 后文本段 → 外层表格，来源顺序可追踪
  - `html_nested_table` 警告保留（每嵌套一次一条），reason 更正为实际语义
- 更新的特征化测试（提交 1 曾按缺陷现状锁定）：edges8 depth 断言 1→2、
  edges15 嵌套表形状、edges22 内层独立形状；edges2/3/6 的警告存在性/
  次数/reason 测试无需改动
- 回归强化（GPT 指示"断言精确出现次数和 table 数量"）：外/内文本
  count==1、table 计数==2、三层嵌套 count==1 + table==3 + 警告==2、
  同 row 未嵌套 sibling cell 不受影响、REG-HTML-001 fixture 全绿
- 验收：全套 3002 passed + 5 xfailed（全部为 BUG-html-2，留 2b）；
  语料对照：10 个非回归 HTML 文件与 autoline-snapshot 仍逐字节一致
  （修复零外溢），REG-HTML-001 修复后满足语义而 autoline 同文件仍丢
  外层文本 = 修复对等性证据；REG-HTML-002 输出不变（2b 前不动）

### 提交 2b：修 BUG-html-2（2026-08-27 完成）

- 根因：`<img>`（非自闭合）在表格内走 `_handle_table_inner_start`，
  该分支只识别 tr/td/th，img 被静默忽略——无 image 元素、无警告；
  自闭合 `<img/>` 走 `handle_startendtag` 反而会发（路径不一致）
- 修复语义（ChatGPT 5.6 Sol 确认）：`_handle_table_inner_start` 增加
  img 分支，复用现有 body/td 图片路径（`_emit_image`：image element +
  resource_path=src + metadata.alt + inline locator）；恰好一个 image，
  不与单元格文本重复计入；缺 src 沿用既有政策（跳过，与 body 一致）；
  不联网抓取
- 更新的特征化测试：edges14 `test_img_in_table_dropped` →
  `test_img_in_table_emitted`（提交 1 曾按丢弃现状锁定）
- 回归强化：恰好一个 image、alt 保留、表头文本 count==1、td/th 同路径
  行为一致、缺 src 政策与 body 对齐、REG-HTML-002 fixture 全绿
  （image:1 + REG_TH_TEXT 各一次）
- 验收：全套 3010 passed（0 xfail，xfail 全部移除）；语料对照：
  10 个非回归文件仍逐字节一致，REG-HTML-001/002 均按修复语义 DIFF
  于 autoline（两缺陷修复对等性证据）；REG-HTML-002 spec-elements
  {image:1, table:1} 与 manifest expectations 精确一致

### 提交 3：注册启用 + 评测矩阵（2026-08-27 完成）

- 注册（最小改动，无自动选择，默认仍 fallback）：pipeline get_parser /
  app.cli / evaluation.cli 的 --parser choices += html
- EVALUATOR_VERSION 1.3 → 1.4（能力封口，同 Markdown 候选逻辑；
  report_version 保持 1.2）
- 搬回提交 1 裁掉的两个端到端测试（原样）+ 整文件推迟的
  test_parser_html_bq_li_p_ol_start.py
- 评测矩阵（GPT 门，含已采用的 Markdown 回归）：
  1. 全套 3015 tests passed（0 xfail）
  2. 冻结 PDF/DOCX manifest vs 冻结基线：既有指标零差异
     （仅 expectation_checks additive 分节，与 MD 启用时一致）
  3. markdown-dev-v1 复跑：6/6 全绿（marker 6/6）
  4. REG-MD-001 复跑：全绿（must_not_error_codes 通过）
  5. html-dev-v1（5 文档）：5/5 全绿，forbidden_markers 首次实际
     求值通过（script/style 排除），silent_drop=0，marker 5/5
  6. REG-HTML-001/002（html 过滤 manifest）：全绿——REG-HTML-001
     外层文本恢复（marker 通过），REG-HTML-002 max_silent_drop 1/1
     通过（image:1 门）
  7. HTML 端到端：pipeline + CLI e2e → UDM 0.2.0 校验通过
  8. chunk 交叉：html-dev chunk_reference_intact_ratio 5×1.0；
     重复运行（含两修复 fixture）规范化输出完全一致
  9. 两份 HTML 评测报告通过 evaluation-report 1.2 Schema 校验
- 注：regressions manifest 为混合格式，单一 --parser 不适配——按
  source_type 拆两次跑（REG-MD-001 用 markdown、REG-HTML-* 用 html，
  过滤 manifest 落 outputs/）；混合单跑会因 md 文件过 html parser
  记 unsupported_type（预期行为，非缺陷）
- chunker 交叉无缺陷暴露，未触发"记录并暂停"条款

### HTML 候选封存 + holdout-html 首跑（2026-08-27）

- 候选提交 0fec2f8（工作树 clean，git_dirty=False），evaluator 1.4
- 冻结 holdout-html 首次正式运行：**4/4 全绿**——pipeline_success、
  schema_valid、silent_drop=0、required_markers 4/4、forbidden_markers
  1/1（HTML-HOLD-003 的注释/script 排除首次实际求值即通过）
- 首次报告永久保留：outputs/evaluation-holdout-html-first-run.json，
  通过 evaluation-report Schema 校验
- 封存记录：manifest sha256 前缀 3ceb4f212dc60b3b（与冻结值一致）、
  报告 sha256 前缀 5fe5878b8d770b7b
- 无失败 → 无需分类实现缺陷/规格争议，无新增 regression
- 阶段 3（Markdown）+ 阶段 4（HTML）全部完成；缺陷登记表
  BUG-md-1 / BUG-html-1 / BUG-html-2 全部已修复关闭


## 十一、阶段 2–4 合入 main + 混合 manifest 调度（2026-08-27，ChatGPT 5.6 Sol 指示）

### 阶段 2–4 落入 main（保留提交身份）

- 证据记录补丁：旧 holdout 哈希显式标记"首次运行前经规格裁决废止"
  （holdout-md e08b50ada20f577f、holdout-html 5decd9940de62567），
  冻结表更新为最终正式值；此后两份 holdout 不得再修改（c68820b）
- 合入方式：main 与 adoption 分支为严格线性关系，`git merge --ff-only`
  到 c68820b——17 个提交 SHA 全部原样保留（无 squash、无 cherry-pick
  重写）；分支当时尖端即已验证集，无未验证尾随提交，不构成
  "整支合并未验证工作"
- 合入后 main 上的最终矩阵（dachuang-code/.venv）：
  1. 全套测试 3015 passed 0 xfail
  2. pilot 冻结基线对比：frozen 全部键值不变（单向对比，加性键允许，
     除计时/版本戳）——1.2 报告的 expectation_checks 分节为既定加性设计
     （v1.2 版本语义测试钉住）
  3. markdown-dev-v1 6/6、html-dev-v1 5/5 + forbidden 1/1、
     REG-MD-001 / REG-HTML-001/002 拆跑全绿
  4. 两份 holdout 首跑报告 schema 校验通过；确定性复跑（规范化去
     generated_at/git_*/wall_time_seconds）与首跑完全一致
  5. chunk_reference_intact_ratio 全 1.0
- 打 tag `stage4-html-adopted`（附注含矩阵结论）
- gitignored 工件同步：holdout 两份首跑报告复制到主仓 outputs/
  （sha256 前缀 49d15a0650fefc46 / 5fe5878b8d770b7b 与封存记录一致）；
  samples/private 两 worktree diff 为空（此前已同步）

### --parser auto 混合 manifest 调度（evaluator 1.5 / report 1.3）

- `--parser auto`：仅按 manifest 的 source_type 解析——pdf/docx→fallback、
  markdown→markdown、html→html；不按扩展名猜测；text/ipynb 待 parser
  注册后加入映射。显式 --parser 旧行为不变（默认仍 fallback）
- 未注册 source_type 的 auto 文档：**不路由到任何 parser**（fallback 会把
  .txt 错送 docx 路径产出误导性错误码），由 runner 合成结构化
  unsupported_type 失败，parser_used="none"，计时 total=0
- 报告 per_doc 新增 `parser_used`（复现不依赖隐式映射）；按精确快照政策
  升 REPORT_VERSION 1.2→1.3：schema 条件互斥——1.3 必含 parser_used，
  1.1/1.2 报告不得含（旧报告继续原样通过校验）；EVALUATOR_VERSION
  1.4→1.5。auto 模式下 provenance.parser_version=null（多 parser 并存，
  单值会误导）；ef 旧条目无 source_type 时沿用 fallback
- 验收门（ChatGPT 指定）：known-regressions-v1 混合清单单次
  `--parser auto` 运行 **3/3 全绿**（REG-MD-001 marker+must_not_error、
  REG-HTML-001 marker、REG-HTML-002 marker+silent_drop 门），逐文档
  parser_used 正确（markdown/html），且各文档指标与按格式拆跑的成功
  结果零差异
- 新增 tests/test_parser_auto.py（映射表/解析函数参数化、混合清单单次
  运行 e2e、显式模式不变、ef 无 source_type 兼容）；
  test_runner_expectation_keys.py 补 1.3 版本门（1.3 缺 parser_used 拒绝、
  1.2/1.1 含 parser_used 拒绝）；全套 3028 passed
- 待办（不属本 PR）：docs/evaluation.md 的 report_version 说明停在 1.0，
  历史遗留失同步，需单独文档 PR 一并补 1.1→1.3 演进


## 十二、阶段 5 准备：text dev/holdout 冻结（2026-08-27）

按 ChatGPT 5.6 Sol 指示：text parser 机械搬运前先建立并冻结
text-dev-v1 / text-holdout-v1；expectations 全部按 TextParser 文档化规格
（autoline-snapshot）人工推导，不运行 parser、不看作弊输出。

- 语料（samples/private/，gitignored）：
  - devset-text 7 文档：基本多段落 / CRLF+段内不重排 / Unicode
    （CJK+emoji+组合字符+NBSP 分隔行）/ 空文件 0 字节 / 纯空白 /
    超长行（两段各数千字符）/ UTF-8 BOM
  - holdout-text 4 文档：CR-only 换行 / 无效 UTF-8 字节（errors=replace
    政策，marker 精确断言 PAD_END+U+FFFD×2+TAIL_START 连续序列）/
    .text 备用扩展名+多种空白分隔行 / 行尾空白+段内换行
- expectations 要点：段落计数全部按"空行分隔、段内行保留、整段首尾
  strip"推导；空文件与纯空白声明 paragraph:0（计数下限语义下 0 是
  强断言）；BOM 为普通非空白字符（首段保留、不影响分段）；无效字节
  按 errors=replace 替换断言；must_not_error_codes 守护 text_read_failed
  与 unsupported_type 不发生
- 语义修正（2026-08-27，ChatGPT 边界②纠错）：初稿曾概括"无效字节
  逐字节 → U+FFFD"，**该概括错误**。Python errors=replace 按 Unicode
  maximal subpart 规则：孤立非法单字节各自一个 U+FFFD；截断的多字节
  序列（E2 82+EOF、F0 9F 98+非延续）整体一个 U+FFFD。holdout fixture
  b"\x80\xff" 为两个孤立非法单字节 → 恰好两个 U+FFFD，原 expectation
  与连续序列 marker（PAD_END+U+FFFD×2+TAIL_START，多一个替换符则
  子串不命中，同时钉住位置与次数）均正确，**冻结 manifest 不动**。
  精确行为由 tests/test_text_decode_replace_semantics.py 直接断言
  （含 ChatGPT 核对表两组：FF FF→两个、E2 82+EOF→一个；替换次数
  全部用 element.content.count 断言）；BOM 升格为本阶段明示政策
  "保留 U+FEFF"，不再以"规格未提及"推导
- 冻结哈希：devset-text manifest 4b0e5abc0fc55851、
  holdout-text manifest 4c7be8ff8e495946（manifest 1.1）
- 首次运行前 expectations 审计已完成（本轮起草即按规格逐条推导并
  复核，先于任何评测运行）；主仓 samples/private 副本已同步
- 两段式计划（无已知缺陷，GPT 指示不造空三段式）：机械搬运不注册 →
  注册启用；发现真实缺陷再插独立修复提交

## 十三、HTML 嵌套单元格段落结构归属修复（2026-08-27，ChatGPT 核对点①）

ChatGPT 5.6 Sol 对阶段 3/4 合入的核对结论：外层单元格文本转独立
paragraph 可以是一种表示策略，但"文本各出现一次"不能证明结构保留——
须能通过 locator/关联信息回溯到原外层单元格。核查结果：**归属实际丢失**
（该 paragraph 与 body 段落同形：inline locator、parent_id=None、
metadata={}，无从区分），故先修后报，不凭 marker 全命中关闭结构验收。

- 修复：`_emit_cell_text_paragraph` 增加
  `metadata={origin: "table_cell_text", table_start_line, row_index,
  cell_index, position}`；坐标相对**直接外层** table（嵌套点前发射时
  内层尚未 push、收尾发射时内层已 pop，两种时刻栈顶均为所属 table 的
  start_line）；`_current_cell_coords()` 以栈顶容器当前长度取
  row/cell 索引（当前行/格尚未 append）。position ∈
  {before_inner_table, after_inner_table}
- 登记测试（test_bug_html_regressions.py +4，共 23）：
  1. 前/后段 metadata 精确指向原 cell，且 table_start_line 与外层
     table element 的 locator.line 同源互证
  2. 多行多列：row_index/cell_index 精确到发生嵌套的 cell；未嵌套
     兄弟 cell 不产生归属段
  3. 三层嵌套：L2 段归属中间层、L1 段归属最外层（各 table 起始行
     不同可区分）——立即外层语义
  4. 邻域不回归：body 段落不带 origin，两类段可区分
- 验证：全套 3032 passed（3028+4）；html-dev 5/5、regressions auto
  3/3 全绿且与修复前运行**指标零差异**；holdout-html 复跑（本文件
  标作复跑，非首跑）schema 通过、规范化后与封存首跑零差异——修复为
  纯加性 metadata，不触指标与管线行为；首跑报告与 stage4 标签不动

## 十四、text parser 两段式搬运（2026-08-27）

### 提交 1：机械搬运（不注册）

- app/parsers/text_parser.py：自 autoline-snapshot（fcad055）逐字节
  搬运，零行为改动；未注册未启用（pipeline 工厂 / CLI / auto 映射
  均未触碰）
- 测试搬运：test_parsers_text.py + test_parsers_text_edges.py 及
  edges2–8、edges10–13（12 个文件）+ test_parser_text_blocks_edge.py；
  裁掉依赖注册的 7 个测试（test_parsers_text.py 的 pipeline/CLI e2e
  2 个、edges10 的 process_single 3 个、blocks_edge 的 text 2 个），
  裁剪点留注释，注册启用提交原样搬回；edges9（15 个测试全部走
  process_single）整文件推迟到注册启用提交；共 770 tests passed
- 语料对照：devset-text(7) + holdout-text(4) 共 11 文件，两仓
  TextParser 直接解析（不经 pipeline），规范化输出（去 source_path）
  **11/11 逐键一致**（PARITY-ZERO-DIFF）
- 全套 3802 passed（3032+770）

### 提交 2：注册启用（evaluator 1.6）

- 注册点：pipeline 工厂 get_parser 补 text 分支；app CLI 与评测 CLI
  --parser choices 补 text；AUTO_PARSER_BY_SOURCE_TYPE 补 text→text
- 能力封口：EVALUATOR_VERSION 1.5→1.6（1.5 无法运行 text manifest，
  同版本不同能力损害复现）；报告结构未变，report_version 保持 1.3；
  ipynb 仍为未注册类型（auto 文档级合成失败语义不变）
- 裁掉的 7 个测试原样搬回（edges10 三个含 chunk 断言，chunker 行为
  对 text 段落两仓一致）；edges9 整文件（15 个）补齐；test_parser_auto
  重构：映射/参数化补 text→text，ipynb 成为唯一未注册类型，混合
  manifest e2e 改为 md/html/text 成功 + ipynb 合成失败，版本断言 1.6
- **text-dev-v1 manifest 哈希沿革**（首跑揭示 expectations 推导漏算
  pipeline 层）：4b0e5abc0fc55851 → TEXT-DEV-004/005（空文件/纯空白）
  误按 documents+expectations 声明，但 parser 按规格产出 0 elements +
  text_no_content 警告后，pipeline 按既定不变量报
  no_extracted_elements（blank.pdf/corrupt.pdf 同类，
  test_empty_pipeline_error 钉住），属 expectations 作者错误而非代码
  缺陷 → 转为 expected_failures（expected_error_code=
  no_extracted_elements）→ **a14b4d6dfbd3fe32（现行）**。揭示运行的
  报告保留为 evaluation-text-dev-v1-first-run-revealed-ef-gap.json。
  **holdout-text 未动**（4c7be8ff8e495946，4/4 全绿无需修改）
- 验证：text-dev-v1 5/5 成功 + ef 2/2 matches + required_markers 5/5；
  holdout-text 首跑 4/4 全绿（报告 outputs/
  evaluation-holdout-text-first-run.json，schema 通过，已同步主仓
  outputs/）；known-regressions auto 复跑 3/3 且与 text 注册前
  **零差异**；全套 3824 passed（3802+22）
- 15 个 text 测试文件与 autoline-snapshot 逐字节一致（diff 校验）

### 追加补丁：归属唯一标识 table_index（2026-08-27，ChatGPT 边界①）

ChatGPT 5.6 Sol 指出：table_start_line + row_index + cell_index 在
单行 HTML 中会碰撞（多个 table 同起始行、同行列索引），不能单独作
单元格身份；原三层测试特意用了不同起始行，未覆盖碰撞。

- 修复：每个 `<table>` 起始标签分配全文档唯一 `table_index`
  （0,1,2,...），table element 的 metadata 与 cell-text paragraph 的
  metadata 同字段同值，构成唯一 join key；行号/行列坐标保留用于
  定位。设计说明：外层 table 元素在 `</table>` 才产出，段落发射时
  其 element_id 尚不存在，故用 table_index 而非 element.id 作引用
  ——唯一性与可解析性等价（一对一 join），已向 ChatGPT 报备
- 登记测试 +2（test_bug_html_regressions.py，共 25）：同一行三层
  嵌套（三 table 同起始行、table_index 互异、每段唯一解析到直接
  外层）；同一行两个并列外层表格（坐标完全同形，table_index 区分
  且各归其主）；ChatGPT 裁决验收条件补测 +2（相同输入重复解析
  索引分配一致；不同文档计数器不共享、各自从 0 起）
- 邻域适配：edges12 test_th_scope_ignored / edges22
  test_all_th_single_row_table 的精确 metadata 断言补 table_index
  （两文件自此与 autoline 有注记差异）
- 验证：全套 3826 passed；html-dev 与 holdout-html 复跑指标与
  既有结果零差异（纯加性 metadata，不触指标）；首跑报告与标签不动

### Stage 5 验收矩阵与 holdout-text 正式候选验收（候选 SHA ca3fbd9）

按 ChatGPT 5.6 Sol 确立的验收顺序（全部通过后才首次运行 holdout）：

- 候选 SHA **ca3fbd9**（干净树，git_dirty=false）：= 85e3dda 机械搬运
  + d0f11a0 注册启用 + 76deba9 归属唯一标识 + ca3fbd9 解码语义补测
- 验收矩阵（全部在 ca3fbd9 上执行）：
  1. 全套已搬运测试 **3835 passed**（3028 基线 + 807 text 相关）
  2. pilot 冻结基线（PDF/DOCX）、md-dev 6/6、html-dev 5/5、
     regressions auto 3/3、text-dev 5/5+ef 2/2——与各自参照运行
     **七组规范化零差异**（去时间戳/git/计时/版本戳/parser_used）
  3. holdout-md / holdout-html 确定性复跑与封存首跑零差异
  4. 全部 stage5 报告 schema 校验通过（report 1.3）
- **holdout-text 正式候选验收**（ChatGPT 5.6 Sol 裁决措辞，不得称
  "首次未暴露评测"）：ca3fbd9 干净 SHA 上 outputs/
  evaluation-holdout-text-first-run.json——4/4 全绿，
  required_markers 4/4（含 U+FFFD×2 连续序列精确断言）、
  must_not_error 1/1，schema 通过，sha256 前缀 **468a4ea55a3d297d**，
  已同步主仓 outputs/
- **真实时间线与暴露性质**（ChatGPT 裁决要求如实区分）：
  1. 机械搬运阶段（85e3dda 前后）的语料对照把 holdout-text 4 文件
     纳入两仓直接解析比对——**已发生结果暴露**
  2. 85e3dda+dirty（注册改动未提交）预跑——未冻结源码状态的预跑；
     该时刻的未提交差异未做快照，**复现受限**（不能以"后来输出相同"
     证明当时源码与某 SHA 相同）
  3. d0f11a0 中间候选复验
  4. ca3fbd9 最终选定候选的正式验收（4/4 通过）
  不符合"候选完成后才首次接触 holdout 结果"的原约定；但 ChatGPT
  裁定不否定 ca3fbd9 验收结果、无依据认定据此调参。全部原始记录
  保留。text holdout-v1 此后作为固定回归集使用；仅当项目最终需要
  宣称严格未暴露验收时另建新集
- **text-dev 验收口径**（ChatGPT 裁决）：7 个输入 = 5 个处理成功
  + 2 个预期失败精确匹配（no_extracted_elements；其他错误、崩溃
  或意外成功均不能冒充预期失败）+ 0 个非预期失败；不得概括为
  "7/7 解析成功"。**manifest 修订后的通过不是算法性能提升**——
  变化发生在评测期望层（规格勘误），非解析能力变化

## 十五、阶段 6 准备：ipynb 契约定稿 + dev/holdout 冻结（2026-08-27）

ChatGPT 5.6 Sol 对 ipynb 支持契约送审稿裁定"有条件通过"，按其修订表
定稿后冻结语料，本轮采用三段式（机械搬运 → 独立契约修正 → 注册启用）。

- **契约**：docs/ipynb-contract.md（提交 f35e8b7）。要点：nbformat == 4
  精确范围（未来主版本 → ipynb_unsupported_version）；版本字段整数类型
  检查（缺失/str/bool → ipynb_bad_structure；nbformat_minor 非负整数）；
  source 全字符串先验后 join（禁止 str() 强转，非法 → 跳过 cell +
  ipynb_bad_cell 注明 cell_index 与字段）；语言链 kernelspec.language →
  language_info.name → 空（kernelspec.name 不冒充语言，不记录）；outputs
  非空 → ipynb_outputs_ignored、attachments 非空 → ipynb_attachments_ignored
  （每 cell 一次注数量，不按 nbformat_minor 门控——官方已回移 4.0）；
  attachment: 图片引用不解码、不当路径读取、不伪造资源 → 跳过 image +
  ipynb_attachment_ref_skipped；code/raw 正文保留原始缩进换行（strip 仅
  判空）；评测口径一律称"cell source 抽取"；测试按依赖切分（非按失败
  归类）
- **版本封口**：REPORT_VERSION 保持 1.3（document schema 的 source_type
  枚举与 ipynb locator 分支已存在，evaluation report 的 parser_used 为
  自由字符串，无结构扩展）；注册时 EVALUATOR_VERSION 1.6 → 1.7
- **语料**（samples/private/，gitignored）：
  - devset-ipynb 5 成功 + 4 预期失败：基本 mixed cells（heading/导语/
    code/raw/列表）/ source 列表 + language_info 唯一语言来源 / 边界
    cell（空 code、空 raw、未知类型 widget、保留 raw）/ 附件引用 +
    执行输出（minor 4）/ 高 minor=9；ef：nbformat=5（unsupported）/
    非法 JSON / nbformat 为字符串 "4"（bad_structure）/ 全空 cell
    notebook（no_extracted_elements）
  - holdout-ipynb 3 成功 + 1 预期失败：现实分析流（5 cell 混合含带输出
    code）/ 列表 source + language_info / 附件+输出混合 / 全空 cell
- **expectations 推导要点**（先于任何运行，按契约逐条人工推导）：markdown
  委托逐 cell 计数；attachment: 引用图按契约 §7 跳过（DEV-004 与
  HOLD-003 的段落计数已扣除该 image）；code/raw 各产出 1 paragraph；
  高 minor 按已知字段照常解析；ef 错误码逐一对应契约 §2/§3；空
  notebook 走 parser ipynb_no_content + pipeline no_extracted_elements
  分层（text 先例）
- **与机械版的已知故意分歧**（契约修正提交后才满足 expectations，属
  预期而非缺陷）：DEV-002 语言元数据（机械版从 kernelspec.name 取
  "python3"）；DEV-004/HOLD-003 的 image 元素（机械版产出
  resource_path="attachment:…" 的伪路径元素）；DEV-006（机械版
  `5 < 4` 为假照常解析 cells）；DEV-008（机械版 str < int 抛
  TypeError → unexpected_parser_error）。机械对照阶段两仓行为一致，
  不受影响
- **冻结哈希**：devset-ipynb manifest
  4a210e98ed8c0e15300b23c4be5d07293efe53134de08a3efe0ce152571bbb23、
  holdout-ipynb manifest
  38090ead37ea035d6e4863a2b3909c57aca15a93ebdc1a227337a1d6e4c62609
  （manifest 1.1；holdout devset_status=complete 与 text/md 一致）
- **holdout 纪律**：不进入直接解析、对照脚本或任何预跑；完整候选固定
  干净 SHA 后才首跑（text 时序教训）
- **三段式计划**（GPT 定案顺序）：机械搬运不注册（对照仅 dev + 公开
  regression）→ 独立契约修正提交（版本字段 / source / language / 忽略
  诊断四项）→ 注册启用（1.7 + auto 映射）
- 主仓 samples/private 副本同步

### 十五-4、三段式执行记录（2026-08-27）

- **机械搬运（faab6db）**：IpynbParser + 16 个测试文件原样入库（不注册），
  1053/1055 直测通过（2 个 pipeline/CLI 测试按契约 §12 切分表裁切）；
  两仓 dev 语料对照零内容差异（仅预登记的 schema_version 快照分歧）
- **契约修正 1（20dd9b6，§2）**：版本字段整数校验（bool 拒绝）+
  nbformat==4 精确范围；9 个 fixture helper 补缺省版本字段、25 个版本
  钉住测试改写、10 个契约测试
- **契约修正 2（e396cf4，§5/§8）**：source verify-then-join（非 str /
  含非 str 项 → 跳过 cell + ipynb_bad_cell，details 记 cell_index+field）；
  code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1；
  约 100 个原快照测试改写 + 10 个契约测试
- **契约修正 3（086c35f，§6）**：语言链 ks.language → language_info.name
  → 空串；kernelspec.name 不再参与；非 dict / 非 str 一律视作缺失不
  崩溃；26 个测试改写 + 10 个契约测试
- **契约修正 4（2edb166，§7）**：outputs/attachments 非空各发一条忽略
  诊断（details 记数量，不因 minor 门控）；attachment: 图片引用跳过 +
  ipynb_attachment_ref_skipped（details 记 cell_index/ref/alt）；2 个
  测试改写 + 10 个契约测试
- **注册启用（5c4fa93）**：pipeline/app.cli/evaluation.cli choices 补
  ipynb；AUTO_PARSER_BY_SOURCE_TYPE 补 ipynb→ipynb；EVALUATOR_VERSION
  1.6→1.7（能力封口；报告结构未变，report_version 保持 1.3）；裁切的
  2 个测试原样搬回；test_parser_auto.py 按 v1.7 改写
- **全套回归**：4932 passed（注册后口径）
- **ipynb-dev 验收（SHA 5c4fa93，git_dirty=False）**：9 输入 = 5 成功 +
  4 ef 精确匹配 + 0 意外失败；5 成功文档 element_count_by_type 与冻结
  expectations 逐项一致（含 silent_drop_count=0）；required_markers
  5/5 通过；全部 schema_valid=true、text_preservation_equal=true
  （口径为 cell source 抽取，非 OCR 全文）；报告通过 evaluation-report
  schema 校验（validate-report）；两次运行除 run_timestamp_iso 外
  逐字段一致（确定性成立）；原始报告 JSON 仅存 outputs/（gitignored）
- **holdout-v1 首跑封存（2026-08-27）**：固定干净 SHA
  1b0b7dd5823c98161d321c335a858094749a1e29（docs 提交后、无未提交
  改动）执行首跑：4 输入 = 3 成功 + 1 ef 精确匹配（no_extracted_elements）
  + 0 意外失败；3 成功文档 element_count_by_type 与冻结 expectations
  逐项一致（HOLD-001 {heading:1,paragraph:3,list_item:2}、
  HOLD-002 {heading:1,paragraph:3}、HOLD-003 {paragraph:3}），
  silent_drop 均 0、schema/tp 均 true、required_markers 3/3；报告
  sha256
  21c9c5c0920e6d93ee20db2d1ffbbb71fe34464dc10a793e7563942fc848356a，
  仅存 outputs/evaluation-ipynb-holdout-v1-firstrun.json（gitignored，
  不入 git）；此后 holdout 结果只封存不回调算法
- **合入 main 后复验（2026-08-27）**：main 以 --ff-only 前进到 bee7494
  （无合并提交）；主 worktree 全套回归 4932 passed；devset-ipynb 复跑
  5/5 成功（git_commit=bee749446445，git_dirty=False）且报告通过
  schema 校验；holdout 未重跑（封存纪律）

## 十六、Stage 6 第一批：ipynb cell 硬边界（2026-08-27）

- **裁决来源**：ChatGPT 5.6 Sol 新对话第一轮（旧对话历史无法重建，换新对话
  带自包含简报）。首批只做 ipynb cell 硬边界；96b688b 为 parser 阶段关闭点。
- **盘点结论**：autoline-snapshot fcad055 无 cell 硬边界生产代码/依赖测试
  （structural.py 与 16 个 chunker 测试文件均无 cell/ipynb 边界逻辑）；本能力
  为 adoption 原创实现，无机械搬运步骤（契约 §0 记录）。
- **契约**：docs/chunker-ipynb-cell-contract.md（f8c2949）——九条核心规则、
  三指标验收（正文覆盖无丢失 / 跨 cell chunk 数=0 / 非 ipynb 基线变化=0，
  以验收测试与首跑断言执行，不进 evaluator 报告结构）、EVALUATOR_VERSION
  保持 1.7（GPT 条件句未触发）、Chunk/UDM schema 不变。
- **受控 push**：用户授权后按 GPT 精确范围执行（fetch → 校验干净/96b688b/
  祖先/0/37 → push origin main:main → 三引用复核一致）。
- **chunker 专属 holdout（全新，不复用已曝光 parser holdout）**：
  samples/private/holdout-chunker-ipynb/，max_chars=200，期望按契约先于实现
  人工推导（expectations-chunks.json）：
  - H-CHK-001（6 短 cell，总长<<200）：chunk_count=6，逐 chunk 单 cell、
    文本逐格对应（钉"相邻短 cell 不合并"）
  - H-CHK-002（短+600 字符超长 code cell+短）：chunk_count>=5、中段全部
    cell={1}、每 piece<=200（钉"超长只在 cell 内切分"）
  - H-CHK-003（单 cell 内 heading 边界 + 相邻 list cell）：chunk_count=2、
    cell 集 {0},{1}、文本 ["标题甲 段落一文字 段落二文字", "项目一 项目二"]
    （**冻结后修正**，见下）
  - H-CHK-004（全空 cell）：无 element 无 chunk
  - 冻结哈希：expectations-chunks.json
    0275b43efd855ed23530b00daf51da2dc197d29bf9cbc018d2ccd920850d0843；
    H-CHK-001.ipynb
    6c879a3e18f520c4d329e02110c109c1888e393272ca15d7bbbf303a30950357；
    H-CHK-002.ipynb
    f9c7998eea339babdbd8c45605d1b1cb2a889d3d61c30597c9df433d0a655bf7；
    H-CHK-003.ipynb
    1499724f246220028790d091db82efef7e13b5efc5d3a317fac87578b6aa7bd2；
    H-CHK-004.ipynb
    92208b0a82e441dc785c260db41753982f07d7ea45ad54092ad8fb1168a3ead6
- **期望推导勘误（实现期间、首跑前）**：H-CHK-003 初版期望把 heading 推导为
  独立 chunk（chunk_count=3），与契约自身矛盾——契约 §1 规则 8/9 要求 cell 内
  行为与 96b688b 基线一致，而基线 heading 语义（main 上既有测试
  tests/test_chunker.py::test_heading_is_hard_boundary 钉死）是"heading 封口
  前文、与后续段落并入同一 chunk"，非孤立成 chunk。据契约修正为
  chunk_count=2（推导权威=契约+main 既有基线测试，非新实现输出）。
  四个 fixture 文件未改动（哈希不变）；expectations-chunks.json 修正后哈希
  a730ac914411556abeb65607dc472140ffc883981325bc54f7ecc4b6bdd7d09b。
  修正发生于任何 holdout 运行之前；此偏差如实登记并将在下轮汇报 GPT。
- **实现（9adc2d8，adoption 原创）**：app/chunkers/structural.py 仅在
  `source_type == "ipynb"` 时激活 cell 边界判定（cell_index 变化即封口；
  locator 缺失/非 dict → 元素自成一组）；tests/test_chunker_ipynb_cell.py
  18 个测试逐条映射契约（九规则 + §2 防御 + 三指标 + 端到端）。
  指标 1 口径注记：超长 element 切分多 chunk 时 chunk 侧 joiner 空白在
  element 侧无对应物，采用 v1.1 已裁决的非空白有序字符口径（7e1246d；
  同 test_chunker.py::assert_text_preserved），与契约"既有口径"一致。
- **dev 验收（SHA 9adc2d8，git_dirty=False）**：全套回归 4950 passed
  （基线 4932 + 新增 18，0 回归）；devset-ipynb 复跑 9 输入 = 5 成功 +
  4 ef 精确匹配 + 0 意外失败，element_count_total=14 与冻结期望一致；
  5 成功文档 chunk 层断言全过（每 chunk 单 cell、覆盖无丢失、chunk 全字段
  两次一致）；报告确定性成立（除 run_timestamp_iso 与 wall_time_seconds
  计时噪声外逐字段一致——parser 阶段两次运行同样仅计时字段不同，口径
  补记）；报告存 outputs/evaluation-chunker-dev-acceptance{,-run2}.json。
- **holdout 首跑封存（SHA 9adc2d8，git_dirty=False，一次性）**：4/4 全过——
  H-CHK-001 chunk_count=6 逐格单 cell 文本一致；H-CHK-002 chunk_count=5
  （首 {0}、中段全 {1}、尾 {2}，max piece 200）；H-CHK-003 chunk_count=2
  （勘误后期望）；H-CHK-004 结构化 no_extracted_elements（0 element 0 chunk，
  无崩溃）；外加每文档单 cell 不变量与非空白覆盖断言。封存报告
  outputs/holdout-chunker-v1-firstrun.json（gitignored），此后不再重跑。
- **纪律**：holdout 不进任何对照/预跑；固定干净 SHA 首跑封存；dev 侧断言
  （单 cell、覆盖、确定性 + 三指标 + 端到端）作为常驻回归测试。
- **合入 main（2026-08-27）**：`git merge --ff-only`
  integration/stage6-chunker-ipynb-cells → main 96b688b..4d0d471（5 提交，
  无合并提交）；主 worktree 全套回归 4950 passed；Stage 6 第一批在
  4d0d471 关闭。EVALUATOR_VERSION 保持 1.7、report_version 1.3、
  manifest 1.1（契约 §4，无 evaluator 能力变更）。

## 十七、Stage 6 第二批：Chunk.source_spans 填充（2026-08-28）

- **裁决来源**：ChatGPT 5.6 Sol 新对话 6a911adf（旧对话服务端历史重建
  错误后换新对话；裁决经 SSE 网络层取证，UI 渲染为空）。批次 1 通过并
  封口、三项偏差全部接受、不重跑已封存 holdout；批次 2 定为
  `Chunk.source_spans` 填充单独封口；拆批保险条款：若不同 source type
  的 span 语义无法统一须实现前暂停汇报。
- **受控 push（裁决第 4 条）**：用户授权后执行普通 fast-forward
  push，origin/main 96b688b → 8a5a9e6（无 force），远端检查点对齐。
- **盘点结论**：models/schema 侧已在基线（Chunk.source_spans 字段、
  to_dict 空删键、effective_schema_version 0.2.0 翻转、$defs/source_span、
  0.1.0 禁 span 分支）；autoline 有 chunker 填充逻辑与语义测试
  （test_pipeline_split_spans.py 切片恒等）。语义统一性判定：span 是
  el.content 字符区间、跨 source type 同构，累积路径整进整出、唯一
  拆分在超长路径、ipynb cell 边界整元素封口与 span 正交——不触发
  拆批暂停。搬运方式：无机械搬运，按基线语义融合实现。
- **契约**：docs/chunker-source-spans-contract.md（9e1b4d4）——九规则
  （定义/切片恒等/坐标基准 lstrip 推算/累积路径整区间/超长路径
  el_start+piece 偏移与缝隙语义/逐 part 不去重/无文本无 span/既有输出
  逐字节不变/版本契约）、§1.9 修订条款（AMENDMENT）：
  test_old_pipeline_output_still_010_and_valid 的"pdf/docx 输出仍
  0.1.0"被取代——0.1.0 保持合法读取格式，新 pipeline 输出一律
  0.2.0；冻结基线字节一致保护已封存产物而非新运行。
- **span 专属 holdout（全新，不复用已曝光语料）**：
  samples/private/holdout-chunker-spans/，max_chars=100，期望按契约
  先于实现人工推导（elements 清单来自冻结 parser 导出，非新实现）：
  - H-SPN-001.md（heading+2 段）：1 chunk sequential、3 span 全区间
  - H-SPN-002.md（149 字符 25 句）：2 chunk，[0,95)+[96,149)，
    缝隙 1 空格，均无 split_boundary_after
  - H-SPN-003.md（239 字符无句读）：3 chunk 硬切 whitespace 回退
    [0,95)/[96,191)/[192,239)，前两片 split_boundary_after=whitespace
  - H-SPN-004.ipynb（3 cell 含超长 cell）：4 chunk，cell 边界与
    span 正交共存
  - H-SPN-005.md（纯空白）：结构化 no_extracted_elements
  - 冻结哈希：expectations-chunks.json
    e3d787e9c68c0b8c9213fc8cad70ea90d42bc7ef2e2e36c075910a4ccb6fdfc2；
    H-SPN-001.md
    9493ce91edb3f7bfd58a6bacf265c93e886c34c760d602b17d670f9a8ebccff7；
    H-SPN-002.md
    e4584e9779b847c5c5cc03210bb5e79c3f6fc391ec548ed0c7ed04366e984315；
    H-SPN-003.md
    95551d2890a0c33cc24e2ec7dc420405e4649b416553e829fae2a26c361a7a42；
    H-SPN-004.ipynb
    1b1c269976873ce8ddc54a73c474353410c5f6ad058da09ad7f16158c2a6eca5；
    H-SPN-005.md
    6a3cf5192354f71615ac51034b3e97c20eda99643fcaf5bbe6d41ad59bd12167
- **纪律**：holdout 不进任何对照/预跑；固定干净 SHA 一次性首跑封存；
  切片恒等/缝隙纯空白/版本翻转/文本逐字节不变作为常驻回归测试。

### 执行与验收记录（2026-08-28）

- **实现（63b05ce）**：`_SplitPiece` 增 start/end；`_hard_split_with_
  whitespace_fallback` 逐 piece 坐标（piece_start 先于游标推进捕获，end
  排除 rstrip 空白）；`_split_long_text` 句子定位（find+pos，防御回退）
  与合并 buf_end 扩展（句间空白含于合并 span）；`_ChunkBuffer.parts` 四
  元组化，flush 生成逐 part span（不去重）+ 首现去重 ids；3a 超长路径
  span = el_start + piece 坐标；`_element_text_with_span` lstrip 长度
  推算（契约规则 3）；既有 `_element_text` 留兼容包装。
- **契约测试**：tests/test_chunker_source_spans.py 22 个，逐条映射九
  规则 + §2 防御（ipynb cell/缺 locator 正交）+ §3 三指标（切片恒等/
  非空白覆盖/两跑确定性）+ §4 端到端（md 0.2.0 + ipynb cell/span 共存）。
- **版本语义修订（契约 §1.9）**：tests/test_version_semantics.py 原
  `test_old_pipeline_output_still_010_and_valid` 断言被
  `test_pipeline_output_now_020_with_spans` 取代（真实 docx → 0.2.0 +
  全 chunk 非空 span + schema 通过），旧形状 0.1.0 读取兼容由既有
  `test_udm_old_pdf_docx_shape_still_passes` 继续钉住。
- **全套回归**：4972 passed（8a5a9e6 基线 4950 + 22 新增，0 回归）。
- **dev 验收（干净 SHA 63b05ce）**：全部 5 个 devset（pdf/docx/md/
  html/text/ipynb）逐文档断言——schema_version=0.2.0 且 schema 校验通
  过、逐 chunk span 切片恒等（单 span 严格逐字节）、非空白覆盖无丢失
  （跨 chunk 并集口径）、两次运行 chunk 全字段一致、element 静默丢失
  与封存 stage5 pilot 基线逐 doc 一致（DC-MVP-001-PDF 的 silent_drop=3
  为既有 parser 能力限制，与基线相同）；evaluation.cli ×2 报告落
  outputs/evaluation-chunkerspan-dev-acceptance{,-run2}.json。验收脚本
  两处口径修正（跨 chunk 覆盖并集；计数与封存基线比对）如实记录。
- **holdout 一次性首跑（固定干净 SHA 63b05ce，git_dirty=False）**：
  5/5 全过，一次命中——H-SPN-001 1 chunk 3 span；H-SPN-002 2 chunk
  [0,95)+[96,149)；H-SPN-003 3 chunk whitespace 回退
  [0,95)/[96,191)/[192,239)；H-SPN-004 4 chunk cell 边界与 span 正交；
  H-SPN-005 结构化 no_extracted_elements。报告封存
  outputs/holdout-chunkerspan-v1-firstrun.json，不再重跑。
- **版本封口**：EVALUATOR_VERSION 保持 1.7、report_version 1.3、
  manifest 1.1（evaluator 无能力变更；span 不变量以验收测试 + holdout
  首跑断言执行）。

### 合入 main 与批次关闭（2026-08-28）

- `git merge --ff-only` integration/stage6-chunker-source-spans →
  main 8a5a9e6..7dd8221（4 提交，无合并提交：9e1b4d4 契约 →
  7970192 holdout 冻结 → 63b05ce 实现+契约测试 → 7dd8221 执行记录）。
- 主 worktree 全套回归 4972 passed（基线 4950 + 22 新增，0 回归）。
- Stage 6 第二批在 7dd8221 关闭；本记录提交后 main 最终对齐。
- EVALUATOR_VERSION 1.7 / report_version 1.3 / manifest 1.1 不变。
- 待裁决事项（下次汇报）：① 契约 §1.9 版本语义修订条款追认；
  ② 验收脚本两处口径修正（跨 chunk 覆盖并集、计数对封存基线）追认；
  ③ 下一批次方向。

## 十八、Stage 6 第二批裁决与版本语义纠正（2026-08-28）

### 裁决获取经过

- 原对话 6a911adf 镜像站故障（UI 空泡、流截断、composer 卡死），按用户
  "开个新对话"惯例改在会话 6a91a872（标题"Stage 6封口裁决"）投递汇报；
  UI 再次只渲染片段，最终经页面内 fetch `/backend-api/conversation/{id}`
  （只读、带用户会话 cookie）取得完整裁决正文 3204 字。
- SSE 流仍携带镜像方警告注释"禁程序调用，将封禁账号"，已再次向用户
  披露；用户选择继续。

### 裁决四项（GPT 5.6 Sol，2026-08-28，会话 6a91a872）

1. **契约 §1.9 版本语义修订：追认通过**，但最终解释收紧为"0.2.0 表示
   该输出由支持 source_spans 的 schema/writer 产生；空 span 不序列化；
   0.1.0 仅作 legacy 读入格式"。版本描述 schema 能力，而非某 chunk 恰好
   有没有非空 span。要求保留 0.1.0 读兼容测试（backward-read
   compatibility），不强迫新 writer 产旧版本。
2. **两处验收口径修正：追认通过**，不重跑 holdout。纪律要求：
   DC-MVP-001-PDF silent_drop=3 继续标记为 pre-existing/baselined，
   报告不得写成"零 silent drop"；外围验收脚本修正不动 evaluator 本体，
   EVALUATOR_VERSION=1.7 维持合理。
3. **下一批次排序：source_locator 对齐 KVFS → 图片 caption 关联 →
   表格→Markdown 线性化**（依赖关系：先封稳 provenance 链路，再做内容
   构造类能力；caption 批次开批前须先裁定 caption 是否进入
   Element.content）。断路器沿用：六种来源无法映射到稳定 KVFS locator
   抽象时，不硬造统一，直接断路上报分型方案。
4. **push：建议申请用户授权，只允许普通 fast-forward push**（禁 force /
   force-with-lease；fetch 后祖先检查失败则断路重报）。并指出账面矛盾：
   8a5a9e6→7f5f7da 链路应领先 5 提交而非汇报所称"两提交"。

### 账面修正

- 实测（dachuang-code，只读）：`git fetch` 后 origin/main 仍为 8a5a9e6；
  `rev-list --count origin/main..main` = **5**（9e1b4d4、7970192、63b05ce、
  7dd8221、7f5f7da）；`merge-base --is-ancestor` 通过。此前汇报"领先两
  提交"系执行记录视角（7dd8221、7f5f7da 在 63b05ce 之后）误当全量差，
  以 5 为准。

### 版本语义纠正执行（integration/stage6-batch2-version-fix，13b8973）

- `Document.effective_schema_version` 改为无条件返回 0.2.0（裁决 ① 的
  writer-能力语义），删除 `_EXTENDED_SOURCE_TYPES` 内容驱动分支；
  SCHEMA_VERSION=0.1.0 常量保留（legacy 读格式）。
- `test_old_types_emit_010` 被 `test_all_types_emit_020_writer_capability`
  取代（pdf 无 span → 0.2.0 且 schema 校验通过）；`test_models.py` 的
  to_dict 版本断言同步改 0.2.0。0.1.0 读兼容测试
  （test_udm_old_pdf_docx_shape_still_passes 等）原样保留。
- 行为变化面：仅"无任何非空 span 的 pdf/docx 成功文档"（如纯图片文档）
  从 0.1.0 翻为 0.2.0；全部成功 devset 文档批次 2 后本就带 span 输出
  0.2.0，封存 holdout 首跑期望（H-SPN-001..004 均 0.2.0、H-SPN-005 无
  文档）不受影响，无需重跑。
- 全套回归：**4972 passed，0 回归**。

### push 执行（2026-08-30）

- 用户明示长期授权："只要 GPT 同意 push 就直接 push"。裁决 ④ 已同意，
  前置复核（origin/main=8a5a9e6、领先 7 提交、祖先检查 0、禁 force）
  后执行 `git push origin main:main`：8a5a9e6..0fd2bcc，ff 无 force，
  push 后本地与远端对齐（领先 0）。远端检查点就此建立在批次 2 + 版本
  纠正的完整状态上。

## 十九、Stage 6 第三批：KVFS source_locator 契约形式化（2026-08-30）

### 盘点与断路（裁决记录）

- 盘点结论：schema $id 基线起即 kvfs.local；六来源三套互斥坐标系
  （pdf 页几何 / docx 结构索引 / md/html/text 1 基物理行 / ipynb 容器
  混合）；无公共定位键；自跑线从未写下 KVFS locator 语义。
- 裁决（2026-08-30 会话 6a91a872）：断路成立且为正确断路；目标改为
  "统一 locator 协议 + 分族定位语义"（统一 resolver envelope + 分族
  坐标，不强求同构）；三不变量 Determinism / Resolvable / No
  fabricated precision；本批不加 file_offset（语义成本未清，独立未来
  批次 raw_source_span/file_byte_span）；family 显式进入
  source_locator（discriminator 跟 locator 走，不绑 source_type）；
  断路解除，进入契约先行。
- 契约送批后裁决流在 137 字处截断（镜像站故障，end_turn=False 持续
  3 分钟以上），可见正文给出两个必须钉死的边界：① 统一 resolver 不得
  以"原始字节"为全族共同输入语义；② Kreuzberg placeholder 不得因补
  family 被包装成可解析定位器；其余"基本成立"。两条边界已原文落入
  契约（§1 输入表示分族声明 + 不变量 2 豁免条款）；截断情况如实
  记录，完整条文随批次完工汇报请 GPT 复核。

### 契约（integration/stage6-batch3-locator-contract）

- docs/locator-kvfs-contract.md 草案提交 + 裁决边界修订，两提交：
  契约草案、resolver 输入边界与 kreuzberg 豁免钉死。
- 四族名（采纳裁决第二组）：line_address / structural_index /
  page_geometry / container_line。
- 版本语义提案（随实现送批）：writer 能力变更 → 0.3.0；0.2.0 以
  not.required:[family] 排除；0.1.0 约束不变；source_spans 规则
  0.3.0 沿用 0.2.0；EVALUATOR_VERSION 不动。

### holdout 设计决定（偏差候选，完工汇报时请 GPT 追认）

- md/html/text/ipynb：全新 fixture，期望含 family 全字段手工推导冻结
  （契约可推导面）。
- pdf/docx 不进 holdout：pdfplumber/python-docx 的元素切分与 bbox 有无
  属解析器行为而非契约可推导内容，手工推导会变成预跑；其 family
  正确性与既有键不变改在 dev 验收对封存基线断言。

### holdout 冻结（实现前，2026-08-30）

- 目录 samples/private/holdout-locator-family/（gitignored），4 fixture：
  H-LOC-001.md 3b86adfc…36dd、H-LOC-002.html 56762232…eda2、
  H-LOC-003.txt ac884154…e654、H-LOC-004.ipynb 44c47081…833e。
- 期望 expectations-elements.json sha256
  684b028f29bf7a22d8ff4edf8449421109fdecd5705cc4299c5973bd539ac042：
  每 fixture 全部 element 的 element_id/type/source_locator（含 family）
  + schema_version 0.3.0；元素结构与行号按契约 §3 与各 parser 文档化
  规则手工推导，document_id 按 make_document_id（sha256 前 16 位）由
  fixture 字节派生；未运行任何 pipeline 代码。

## 二十、批次 3 执行与验收记录（2026-08-30）

### 实现（integration/stage6-batch3-locator-contract，2800a64）

- models.py：新增 `SCHEMA_VERSION_LOCATOR = "0.3.0"`；
  `effective_schema_version` 无条件返回 0.3.0（writer 能力语义）。
- 六个 parser 在产出的每个 source_locator 上前置 `family` 常量键，
  不改任何既有键取值：text/markdown/html → line_address；ipynb →
  container_line；fallback pdf（段落/表格/图片三处）→ page_geometry；
  fallback docx（段落/图片/表格三处）→ structural_index；kreuzberg
  `_make_locator`（pdf→page_geometry、其余→structural_index）与表格
  locator 同步，占位/启发式标记键原样保留（不变量 2 豁免）。
- schema：schema_version enum 加 0.3.0；0.1.0 分支扩展
  `not.required:["family"]`；新增 0.2.0 分支同口径排除；新增四个
  0.3.0 分支按 source_type 要求 family 存在且等于族 const
  （pdf=page_geometry、docx=structural_index、md/html/text=line_address、
  ipynb=container_line）。
- 测试修正 30 个文件：精确 dict / key-set 断言补 family；版本断言
  0.2.0 → 0.3.0（test_rule9 / e2e / version_semantics 相应改名 030）；
  test_udm_unknown_version_rejected 的非法版本探针改用 0.4.0。
- 新契约测试 tests/test_locator_family_contract.py（40 用例）：每族
  family 正确性（md/html/txt/ipynb 真 parser、pdf/docx 用 devset 真样本
  skip-if-missing、kreuzberg 占位单元级）、既有键不变（去 family 后与
  legacy 形状相等）、版本分支（0.3.0 必填+const、错 const 拒、
  0.2.0/0.1.0 拒 family、无 family 旧输出读兼容）、resolver 可执行
  断言（line_address 行命中、container_line cell 命中）。
- 全量回归：5012 passed / 0 failed（含新增 40）。

### holdout 一次性首跑（干净 SHA 51b60af，2026-08-30）

- 脚本 scripts/holdout_locator_family_first_run.py（51b60af 提交）：
  断言输出不存在（禁重跑）+ 干净树，记录 git SHA；逐 fixture 比对
  parser、schema_version、全部 element 的 element_id/type/
  source_locator 全字段。
- 结果 all_pass=True（4/4 fixture 精确匹配，含 family 与 0.3.0）。
  报告封存 outputs/holdout-locatorfamily-v1-firstrun.json，sha256
  7107b7222f224664744f70bc79fcef4e60466a10593be736c7eb2a6ab8d25910。
  此后永不重跑。

### dev 验收（pdf/docx 对封存基线，2026-08-30）

- 同 manifest/参数（fallback，max_chars=800）重跑：
  outputs/evaluation-locatorfamily-dev-acceptance.json（报告 schema
  校验通过）。
- 与批次 2 封存基线 evaluation-chunkerspan-dev-acceptance-run2.json
  对比：DC-MVP-001 与 DC-MVP-001-PDF 的 element_count_total /
  element_count_by_type / schema_valid / pdf_locator_valid_ratio /
  docx_locator_valid_ratio / silent_drop_count /
  chunk_reference_intact_ratio 全部 SAME（既有键与结构不变，
  Determinism 成立）；evaluator_version 两边均 1.7（本批不动评测器）。

### 待 GPT 完工追认项

- 契约全文（裁决流截断于 137 字符，两处可见边界已并入，全文请重认）。
- holdout 设计偏差：pdf/docx 不进 holdout，改 dev 验收对封存基线断言。
- 版本语义 0.3.0 提案（契约 §4）随实现送批。

## 二十一、批次 3 封口裁决（GPT 5.6 Sol，2026-08-30，会话 6a911adf）

裁决正文封存于本机 Temp/gpt_ruling_b3_full.txt（1021 字符；UI 空泡，
经会话 API 只读取回）。四项：

1. **契约全文追认**：四族映射、resolver 边界、版本规则、kreuzberg
   占位语义均确认（family 只说明字段族语义、不承诺占位 locator 可
   解析；不以"原始字节"作全族统一 resolver 输入；既有 locator 键值
   不变）。无需修订或重跑。
2. **holdout 偏差追认**：pdf/docx 不进 holdout 属合理契约边界偏差；
   批次 2 封存基线 dev 等价验收（全 SAME）成立。附加要求：后续记录
   继续固定所引用基线的提交或哈希（本次引用
   evaluation-chunkerspan-dev-acceptance-run2.json，其 provenance
   git_commit=63b05ce，已在 outputs 留档）。
3. **0.3.0 版本追认**：writer 新增 family 属输出能力变化统一 0.3.0；
   0.1.0/0.2.0 合法读格式但拒 family；source_spans 沿用；不回滚、
   不拆批。
4. **批次 4 前置裁定（图片 caption 关联）**：
   - caption 文本进 Element.content，但只留在 caption 自身 element，
     不复制/拼接进图片 element 的 content；
   - 用新的显式 element relation，方向 `image --has_caption--> caption`，
     不复用 parent_id（parent_id 只表达既有结构层级）；
   - relation 以稳定 element_id 引用，去重且确定性排序；无法明确判断
     或端点缺失时不生成；
   - caption 文本按既有元素路径正常进 chunk；图片内容、source_spans、
     既有文本语义不变；
   - writer 输出形状变化 → 下一版本 0.4.0；契约须冻结 relation 的
     schema、缺失与歧义行为。

## 二十二、批次 4 契约起草（2026-08-30）

- 盘点：caption element 仅 fallback（pdf/docx `_CAPTION_RE`）产出；
  md/html/text/ipynb/kreuzberg 无 caption 产出；六 parser relations
  恒空；Relation dataclass 与 schema 定义已具备。
- devset 实测：docx 图题注在图片段落下一段（para16→17）；pdf 同页
  题注在图正下方（gap 11.5pt）。
- 契约草案 docs/caption-relation-contract.md（本提交）：显式
  `image --has_caption--> caption`；图题注前缀集 {Figure, Fig, 图}；
  docx 紧邻下一段规则；pdf 同页下方 + gap≤50pt + x 重叠 + 全局唯一
  配对（gap,image_id,caption_id 升序贪心）；排序 (type,from,to)；
  版本 0.4.0，≤0.3.0 not.contains has_caption；范围锁死不做
  figcaption 语义/表题注/图上方/跨页。
- 待 GPT 裁决重点：①图题注前缀集口径；②CAPTION_MAX_GAP_PT=50 与
  x 重叠条件；③唯一配对的贪心排序键；④0.4.0 分支不新增必填、
  方向性走契约测试不走 schema；⑤holdout 设计（合成 docx holdout、
  pdf 沿用批次 3 偏差先例走 dev 验收引用基线哈希）。

## 二十三、批次 4 契约裁决与冻结（GPT 5.6 Sol，2026-08-30，会话 6a911adf）

裁决正文封存 Temp/gpt_ruling_b4.txt（573 字符，会话 API 取回）。
五项全部同意，不拆批；两处细化已并入契约：

1. 前缀集：仅 Figure / Fig / Fig. / 图 + 数字开头；Table / 表 排除；
   **数字明确为 ASCII [0-9]**（caption element 分类用的 _CAPTION_RE
   含全角数字，本批不改，两口径分工：分类归 _CAPTION_RE、关联归
   前缀集）。
2. 几何条件：0 < gap_pt ≤ 50；x 区间严格相交（交集 > 0）；同页必要。
3. 唯一配对：(gap, image_id, caption_id) 升序贪心，已配对端点跳过。
4. 0.4.0：不新增顶层必填；schema 管版本分支/relation 对象结构/旧
   版本排除；跨数组方向性与端点存在性走契约测试；metadata.rule 与
   gap_pt 由契约测试固化。
5. holdout：合成 docx 主 holdout；PDF 固定基线哈希 dev 验收；
   md/html/txt/ipynb 断言关系集合为空；**合成 docx 及资源生成一次后
   字节固定、哈希入库登记，运行时不得重新生成**（防漂移）。

结论：契约正式批准（docs/caption-relation-contract.md 随本提交冻结），
版本升 0.4.0，进入实现 → holdout 冻结 → 一次性首跑 → 全量验收。

## 二十四、批次 4 执行与验收记录（2026-08-30）

- 实现 commit f83c0f2（分支 integration/stage6-batch4-caption-relation）：
  - fallback_parser：`_FIGURE_CAPTION_RE`（ASCII 数字口径）+
    `match_caption_relations_docx`（紧邻下一段）/ `match_caption_relations_pdf`
    （同页 + 0<gap≤CAPTION_MAX_GAP_PT=50 + x 严格相交 + (gap,image_id,
    caption_id) 升序贪心唯一配对）；relations 按 (type,from,to) 排序；
    pdf metadata 含原始 gap_pt（浮点差不取整）。
  - models：SCHEMA_VERSION_RELATION="0.4.0"，writer 全来源一律 0.4.0。
  - schema：enum 加 0.4.0；0.1.0–0.3.0 not.contains has_caption；
    四个 family 常量分支覆盖 0.4.0。
  - 契约测试 tests/test_caption_relation_contract.py：docx/pdf 判定
    全分支 + 版本四向 + md/html/txt/ipynb 零 has_caption（真 fixture）+
    devset 真样本（docx e0018→e0019 rule=docx_adjacent_paragraph；pdf
    e0011→e0009 rule=pdf_geometry_below gap_pt≈11.525）；版本断言迁移
    0.3.0→0.4.0，unknown-version 探针改 0.5.0。
  - 全量回归 **5036 passed**（0 fail / 0 skip 之外无异常）。
- holdout（裁决⑤ 纪律执行）：
  - 合成 docx 夹具 samples/synthetic/holdout-caption/holdout-caption.docx
    **生成一次后字节固定**：sha256
    `57c4b3b2ddff4be24a1f2df13a33c821f5272914f1ad3b8ba537d16a823d106d`
    （内嵌 4 张 8×8 PNG 资源随 docx 字节一并固定）；生成脚本带防重入
    守卫仅存溯源，运行时零调用。
  - 期望 expectations.json 在该夹具任何 parser 运行之前按 authored body
    大纲 + 契约 §3 手工推导冻结：16 elements、caption content 全集、
    恰好 2 条 relation（e0003→e0004、e0007→e0008；Table 前缀段与无题注
    图各证一条零关联）。
  - 一次性首跑 commit 5750aef 干净树执行：**all_pass=True**
    （schema_version=0.4.0 / element_count / elements_exact /
    caption_contents_exact / relations_exact 五项全过）；报告封存
    outputs/holdout-caption-v1-firstrun.json（gitignored，sha256
    `34f3f5ca57fc7d7b20ac718dd0c053a642c7a8248a5e96ce223e98027459cc19`），
    此后永不重跑。
- dev 验收：evaluation 重跑 outputs/evaluation-captionrelation-dev-
  acceptance.json（git_commit=5750aef，报告 schema 校验通过）；对照
  封存基线 outputs/evaluation-locatorfamily-dev-acceptance.json（批次 3，
  溯源 63b05ce）逐字段 diff：**除 wall_time_seconds.total 与 run 时间戳
  外全部 SAME**（elements/chunks/expectation 检查/聚合指标零变化），
  满足"relation 产出不扰动既有解析/分块口径"不变量。pdf 真样本断言
  （e0011→e0009）由契约测试承载（上）。
- 已知边界（送下批裁决参考，本批不动评测器）：annotation_metrics 的
  figure_caption_* 仍 null + reason=parser_does_not_emit_relations——
  该理由字符串自本批起事实过时（fallback 已产出 has_caption），
  下批可改为直接消费 has_caption relation 计算 P/R/F1。

## 二十五、批次 4 封口裁决与批次 5-7 排序（GPT 5.6 Sol，2026-08-30，会话 6a911adf）

裁决正文封存 Temp/gpt_ruling_b4_closure.txt（640 字符，会话 API 取回）。

1. 批次 4 正式通过并封口：五项裁决均按原文执行无偏差；main 与
   origin/main 的 da90d53 普通 fast-forward push 予以确认；已封存
   holdout 无需重跑。
2. 批次 5 = (a) 表格→Markdown 线性化（沿用 2026-08-28 排序）。执行
   边界：仅改 table element 的 canonical content；先契约冻结表头/
   空单元格/合并单元格/多行文本/转义/异常与空表/确定性；source_spans
   坐标按线性化后 Element.content 定义；本批不做表题注关联与评测器
   变更；holdout 固定字节 + 实现前手工推导期望。
3. 后续排序 (b)→(c)：批次 6 修 figure_caption_* 评测（直接消费
   has_caption relation，移除过时理由 parser_does_not_emit_relations，
   内部匹配器做成 relation-type 参数化可复用形式）；批次 7 表格题注
   关联（复用批次 4 docx 邻接规则骨架并接入评测框架）。
4. 流程不变：契约先行、全新 holdout、干净 SHA 一次性首跑、ff-only
   合入、全量回归。

## 二十六、批次 5 契约起草（2026-08-30）

- 批次 4 封口裁决指定批次 5 = 表格→Markdown 线性化，边界：仅改
  table element canonical content、先契约冻结边界行为、不做表题注与
  评测器、holdout 固定字节 + 实现前手工推导。
- 盘点：content 生成有三处重复实现（fallback/markdown/html），语义
  相同但存在真实缺口——单元格含 `|` 不转义、含 `\n` 不处理（docx
  cell.text 多段落以 \n 连接、pdfplumber 单元格常含 \n，直接内嵌破坏
  行结构）、docx 0 行表走 Element ValueError 崩溃路径（pdf/html 现状
  跳过）。
- 契约草案 docs/table-linearization-contract.md（本提交）：canonical
  管线 None→"" / CR 规整 / `\n`→`<br>` / `|`→`\|` / 统一 strip /
  无 Unicode 归一；首行=表头与宽度补齐冻结现状；0 行表不产出 element；
  合并单元格保持库给定重复语义；共享纯函数 app/parsers/table_linearize.py
  收敛三副本；md `\|` 反转义保 roundtrip 幂等；schema_version 维持
  0.4.0。
- 送裁七问：①strip 统一 vs 维持现状；②换行 `<br>` vs 折叠空格；
  ③md `\|` 反转义；④0 行表静默跳过；⑤共享纯函数统一三副本；
  ⑥版本不升；⑦holdout 设计（合成 docx+md+html、pdf 沿先例不进）。

## 二十七、批次 5 契约裁决与冻结（GPT 5.6 Sol，2026-08-30，会话 6a911adf）

裁决正文封存 Temp/gpt_ruling_b5.txt（647 字符，会话 API 取回）。
七问全部同意（⑥ 明确 0.4.0 维持：本批不改序列化字段形状/类型，
仅固定既有 content 的 canonical 生成语义）；⑦ 附两项约束已并入契约：

- **ipynb 验证约束**：不得仅凭"自动继承"不验证——holdout 合成
  fixture 增补 ipynb（markdown cell 内 pipe 表格 + code cell 无表格），
  契约测试加 ipynb 表格路径断言；text 永不产 table、ipynb code/raw
  cell 不产 table 进回归断言。
- **md 反转义口径细化**：仅反转义两字符序列 `\|`，其余反斜杠序列
  原样保留（其他反斜杠语义不动，roundtrip 幂等）。
- **dev 对照归因要求**：表格相关指标允许预期变化但逐项归因；非表格
  elements/chunk/locator/relation/确定性不得出现未解释变化。

结论：契约冻结（docs/table-linearization-contract.md 随本提交），
进入实现 → holdout 冻结 → 一次性首跑 → dev 验收。

## 二十八、批次 5 执行与验收记录（2026-08-30）

- 实现 commit 54712ca（分支 integration/stage6-batch5-table-linearization）：
  - 新共享纯函数 app/parsers/table_linearize.py `linearize_table`：
    管线 None→"" / CR 规整 / `\n`→`<br>` / `|`→`\|` / strip（顺序
    固定）；首行=表头、短行补齐、0 行→""。
  - fallback/markdown/html 删除三处本地副本统一委托（ipynb 经
    MarkdownParser 继承）；md `_split_pipe_row` 仅按未转义 `|` 分列、
    仅反转义 `\|`（其余反斜杠保留，裁决③）；docx 0 行表静默跳过
    不产 warning（裁决④）。
  - 6 个钉死旧缺陷行为的既有测试按契约重钉（转义/`<br>`/反转义
    roundtrip）；新增 20 个契约测试（含裁决⑦ ipynb 表格路径、text
    永不产 table、三 parser 一致性、roundtrip 幂等）。全量回归
    **5056 passed**。
- holdout（裁决⑤ 纪律执行，含一次预备跑事故的诚实处置）：
  - 四合成 fixture 一次性生成字节固定：docx
    914ca721bf0917d206b...（多段单元格/合并/管道符/空 cell）、md
    78a3f720e9587a679...（`\|`/`<br>`/参差行）、html
    d1720cb5e8476f3c...（管道符/th）、ipynb
    3619c7a8980b4868...（markdown 表 cell + code/raw cell，裁决⑦）；
    生成脚本带防重入守卫仅存溯源。
  - **预备跑事故**：commit 470c5de 首跑 all_pass=False，封存报告改名
    outputs/holdout-table-v1-preliminary-run.json 保留。诊断：全部
    实质性检查（content/locator/type/metadata 值）通过，两处失败均
    为**期望誊写错误**而非实现缺陷——docx element_id 前缀多誊 1 个
    hex 字符（…7d20 应为 …7d2）；html metadata.table_index 在期望中
    但漏出比对键集。修正 commit 68e160e（沿 text-holdout 预备跑
    先例：留记录、修期望、另跑正式首跑）。
  - **正式首跑** commit 68e160e 干净树：**all_pass=True**（四 fixture
    全部 schema_version=0.4.0 / element_count / elements_exact 通过）；
    报告封存 outputs/holdout-table-v1-firstrun.json（sha256
    `4e566e4919fe69bbc82e50f8378e7788c680edbc97e700f0d984a4737fa04139`），
    永不重跑。
- dev 验收：evaluation 重跑 outputs/evaluation-tablelinear-dev-
  acceptance.json（git_commit=68e160e，报告 schema 校验通过）对照
  批次 4 封存基线逐字段 diff：**除 wall_time 外全部 SAME（0 项实质
  差异）**。归因核实：devset 两文档各含 1 个表格，全部单元格为单行
  纯文本（无 `|`、无 `\n`、无前后空白），新管线对它们逐字节同输出
  ——零差异是真实结果而非掩盖；非表格面（elements/locator/relation/
  确定性）零变化，满足裁决⑦"非表格面不得出现未解释变化"要求。

## 二十九、批次 5 封口裁决记录（2026-08-30，GPT 5.6 Sol）

**会话事故与上下文重建**：批次 5 完成报告发送期间，原裁决会话
（id `6a911adf…`）连续出现服务器端「对话历史暂时无法完整重建，
为避免模型脱离上下文或误读旧文件，本次请求已停止」错误（多次重试、
多个 traceId 均同败），新消息无法持久化。按批次 1 先例开新会话
（id `cf170a6f-205c-4f94-a8b5-d54c53368a0f`）以【上下文重建 +
Stage 6 批次 5 完成报告】重建审查者上下文，后续裁决往来在新会话
进行。裁决原文封存 Temp/gpt_ruling_b5_closure.txt（1512 字符）。

**裁决结果**：
- (a) 预备跑事故追认：**通过**。事故性质判定正确（两处失败均为
  期望誊写错误而非实现缺陷）；处置方式合规（失败记录改名保留 +
  修正期望后另跑正式首跑，与批次 3 text-holdout 先例一致）；正式
  首跑干净（68e160e all_pass=True，sha256 4e566e49… 永久封存）。
  追认理由：预备跑暴露的是测试基础设施缺陷而非算法回归，修正后
  立即重跑仍属首次真实验收，未违反"永不重跑"原则。
- (b) 批次 6 开工授权：**通过**，附三项强制要求：
  1. **relation 消费契约必须明文**——在 tests/evaluation/ 或
     docs/ 显式声明：哪些评测项依赖哪些 relation type；relation
     缺失时的降级策略（fail/skip/fallback）；参数化匹配器接口
     签名（type 参数、返回值、edge case）。
  2. **批次 4→6 的 evaluation 零差异验证**——重跑 evaluation 后
     diff 确认除 wall_time/git_commit 外所有字段逐字节相同
     （批次 6 仅改评测消费方式，不改生成逻辑，devset 的
     has_caption relations 已在批次 4 生成，评测分数理应完全一致）。
  3. **批次 7 接口预留验证**——参数化匹配器完成后附一个桩测试，
     演示传入 table_has_caption 类型并返回模拟匹配结果，无需
     真实数据，仅证明接口可扩展。
- 潜在风险提示（批次 6）：relation 缺失时评测需明确 fail 还是
  skip，避免误报；参数化重构的匹配器签名务必在批次 6 冻结，
  批次 7 不得再改接口。

**批次 6 执行顺序（裁决给定）**：① 起草 relation-consumption-
contract.md（含三项强制要求）→ ② 重构匹配器为参数化（含桩测试）
→ ③ 修复 figure_caption_* 评测消费 has_caption → ④ evaluation
零差异验证 → ⑤ 封口报告。

**批次 5 正式封口，归档编号 `Stage-6-Batch-5-Closed`。**

## 三十、批次 6 执行与零差异验证记录（2026-08-30）

**契约**：docs/relation-consumption-contract.md（冻结 v1；批次 5 封口裁决
三项强制要求并入 §2 签名冻结/§3 降级矩阵/§4 零差异范围/§6 桩测试）。

**实现（commit 7d06f34）**：
- `match_relation_pairs` 参数化纯函数（relation_type / from_marker_key /
  to_marker_key；from 侧识别文本 = content + metadata.alt + resource
  basename 经 normalize_text 后子串匹配；to 侧 content 子串匹配；一对一
  贪心按 (pred_idx, gt_idx) 字典序；端点缺失 relation 不计入预测）。
- `figure_caption_prf` 改为消费 relations 的 has_caption，降级矩阵五路
  （pipeline_failed / no_annotation / no_annotation_pairs /
  no_predicted_relations[recall=0.0 真实漏检] / 正常）；移除常量
  PARSER_DOES_NOT_EMIT_RELATIONS。
- EVALUATOR_VERSION 1.7→1.8（能力封口：1.7 无法消费 relation）；
  REPORT_VERSION 保持 1.3（报告结构零变化，figure_caption_* 仍不进
  macro average）。
- 测试：新增 tests/test_relation_consumption_contract.py 18 项（含
  **批次 7 桩测试**：table_has_caption + table_marker/table_caption_text
  传演出 (2,2,2)，裁决要求③）；重钉 4 处旧语义钉子
  （test_annotation_metrics 2 / test_evaluation_cli / test_evaluation_report）
  + test_parser_auto 版本钉 1.7→1.8；docs/evaluation.md 两处表行与
  CLAUDE.md 对应行更新。全量回归 **5074 passed**。

**零差异验证（契约 §4，裁决要求②）**：
- 新跑：outputs/evaluation-batch6-zerodiff-check.json（git_commit=
  7d06f34，git_dirty=False，报告 schema 校验通过；参数与批次 4 基线
  一致：devset manifest / fallback / max-chars 800）。
- 脚本：scripts/verify_batch6_zero_diff.py 逐字段 diff（value 与 reason
  均比）+ 排除集归因断言。
- 结果：**total diffs 11，全部落在排除集（allowed=11），unexpected=0，
  VERDICT=PASS**。排除集逐项：wall_time×2（计时）、provenance.
  git_commit / run_timestamp_iso（运行环境）、provenance.
  evaluator_version（1.7→1.8，契约 §5）、figure_caption_*.reason×6
  （docx no_annotation_pairs×3：标注空表；pdf no_annotation×3：无标注
  文件——裁决③移除过时理由的必然结果）。全部分数（value）与批次 4
  基线逐一相同（null==null）。
- **对裁决原文的偏差声明（待追认）**：裁决要求"除 wall_time /
  git_commit 外所有字段逐字节相同"，与其第③项（移除过时理由）及
  版本封口政策冲突；按裁决自身理据（"仅改评测基础设施，不改生成
  逻辑——评测分数理应完全一致"）执行为：分数全部相同，reason 仅
  figure_caption_* 三处（×2 文档）变化，evaluator_version 升 1.8。

**holdout**：不设（契约 §7：评测基础设施改动，writer 输出面零变化，
零差异验证即验收）。schema_version 维持 0.4.0（未触碰 app/*）。

## 三十一、批次 6 封口裁决记录（2026-08-30，GPT 5.6 Sol，会话 cf170a6f）

**裁决结果**：
- (a) 零差异验证偏差解释：**追认**，并自我修正裁决措辞。追认理由：
  figure_caption_*.reason 6 处变化正是批次 6 核心任务；evaluator_version
  1.7→1.8 符合版本封口政策；run_timestamp_iso 属运行时元数据。所有
  value 字段逐字节相同（含 null==null）、零 unexpected diff。**修正后的
  零差异验证政策（后续批次沿用）**：所有评测分数字段（*_precision/
  *_recall/f1/macro 及其 value）必须逐字节相同；元数据字段
  （evaluator_version / run_timestamp_iso / wall_time / git_commit）与
  契约化 reason 字段允许预期内变更，但须在验证脚本中显式归因断言。
  verify_batch6_zero_diff.py 的"排除集+归因断言+unexpected=0 判定"
  被评为优于裁决字面要求。
- EVALUATOR_VERSION 1.7→1.8：**追认**。
- (b) 批次 7 开工授权：**有条件通过**——先定 schema_version 升版：
  Option A（升 0.5.0，GPT 推荐：schema_version 反映语义契约而非仅
  结构；新增 relation type 扩展 relations[].type 枚举范围，consumers
  需更新逻辑；先例对齐——批次 4 是"激活已存在的 relations 字段"故
  不升，批次 7 是扩展 type 枚举应升 minor）vs Option B（维持 0.4.0：
  type 本为开放字符串，结构兼容；风险是 version 失去语义指示作用）。
  Claude 选定 **Option A**（与批次 2/3/4 版本沿革=writer 能力语义
  一致），见批次 7 报告。
- 批次 7 预判风险（GPT 提示）：PDF 表格边界更复杂（跨页/嵌套）；题注
  前缀中英文混合与编号格式需全覆盖；holdout 需覆盖"表格有题注/表格
  无题注/题注无对应表格"三类 case。
- 批次 7 执行顺序（选定版本后）：① docs/schema-version-policy.md
  补"新增 relation type 升 minor"规则 → ② 起草
  docs/table-caption-relation-contract.md → ③ 实现 table_has_caption
  （复用批次 4 框架）→ ④ 匹配器调用扩展（参数不改仅传新 type）→
  ⑤ holdout（三类 case）→ ⑥ evaluation 验证（分数变化需归因）→
  ⑦ 封口报告。

**批次 6 正式封口，归档编号 `Stage-6-Batch-6-Closed`。**

## 三十二、批次 7 执行与验收记录（2026-08-30）

**版本选择声明**：Claude 选定 **Option A（schema_version 0.4.0 → 0.5.0）**。
理由：schema_version 描述 writer 能力语义（沿革一致）；新增 relation
type `table_has_caption` 扩展 relations[].type 枚举范围，consumers 需
更新逻辑才能处理。规则成文 docs/schema-version-policy.md §3.2。

**执行（按裁决①–⑦顺序，会话 cf170a6f 批次 6 封口裁决）**：

1. ① docs/schema-version-policy.md 成文：版本=writer 能力；沿革表
   0.1.0→0.5.0；§3.2 新增 relation type 升 minor（Option A 裁决规则）；
   §4 读兼容（旧版本分支 + not.contains 精确排除）；§5 与
   EVALUATOR_VERSION/REPORT_VERSION 分工。
2. ② docs/table-caption-relation-contract.md 冻结 v1：前缀集
   `^(?:Table|表格|表)\s*[0-9]+[\.、\s]`（与图题注集互斥）；docx 规则
   =紧邻上一元素（表题注惯例在表上方，§0 devset 实证 DC-MVP-001：
   caption e0012@para:12 紧邻 table e0013@tbl:0 之前；elements 列表
   顺序=body 顺序，table_index 与 paragraph_index 不同族不可数值比较）；
   pdf 规则=同页上方几何（gap = table.bbox[1] − caption.bbox[3] ∈
   (0, 50]，x 区间相交，(gap,table,caption) 贪心唯一配对；批次 4 下方
   规则的镜像）；devset PDF 实测表题注被 pdfplumber 融合进段落 →
   devset 上 pdf 表关联恒 0 条（归因依据）。§7 不做：不新增
   table_caption_* 指标族（annotation v1.0 无表格 GT 键、devset 零
   标注）、EVALUATOR_VERSION 维持 1.8、match_relation_pairs 签名不改。
3. ③ 实现（app/parsers/fallback_parser.py）：
   `match_table_caption_relations_docx/pdf` 纯函数 + parse() wiring
   （`_sort_relations(图关联 + 表关联)` 两类混排 (type,from,to) 字典序）；
   metadata.rule = docx_adjacent_element_above / pdf_geometry_above
   （pdf 加 gap_pt）。models.py `SCHEMA_VERSION_TABLE_CAPTION="0.5.0"`，
   effective_schema_version() 无条件返回 0.5.0（writer 能力语义）；
   schemas/document.schema.json：enum 加 0.5.0；{0.1.0–0.4.0} 分支
   not.contains 拒 table_has_caption（0.1.0–0.3.0 同时拒 has_caption）。
4. ④ 评测消费路径（签名冻结不改，仅传 relation_type=
   "table_has_caption"）：契约测试以合成 docx → 真实 fallback 解析 →
   match_relation_pairs(构造 pairs) 返回 (1,1,1) 命中 / (1,1,0) 错标
   零命中。EVALUATOR_VERSION 维持 1.8、REPORT_VERSION 维持 1.3。
5. ⑤ holdout（samples/synthetic/holdout-table-caption/）：夹具生成
   一次字节固定，**sha256 = cc9424c2186390de7102802ee3fd3617401e4f
   87f42404b8c52128daf2d00894**；四 case（裁决三类 + 前缀互斥负例）：
   T1 表题注在上（命中）/ T2 无题注（零）/ T3 孤立表题注段落（零）/
   T4 图题注紧邻表上（互斥零）。期望 elements+caption 内容+relations
   全清单在 parser 运行前手工推导冻结（expectations.json，含推导
   注记：初稿 T3 "表格 2、" 经推导发现 _CAPTION_RE 不分类 → 生成前
   改 "表 2、"，未消耗首跑）。首跑于干净 SHA 975dff7 一次性封存
   outputs/holdout-table-caption-v1-firstrun.json：**all_pass=True**
   （elements/captions/relations/schema 0.5.0 全等）。pdf 沿批次 3/4
   追认先例不进 holdout（几何 bbox 手工推导=预跑）；md/html/text/
   ipynb 回归断言零 table_has_caption。
6. ⑥ evaluation 归因验证（scripts/verify_batch7_attribution.py）：
   对照批次 6 封存基线逐字段 diff，仅 4 处差异且全部显式归因
   （wall_time×2、git_commit、run_timestamp_iso）；**evaluator_version
   维持 1.8 与全部 .metrics. 路径逐字节一致为零变化断言通过**
   （table_has_caption 无 GT 键不进任何指标族）——VERDICT: PASS。
7. ⑦ 本记录 + 封口报告（提交 cf170a6f）。

**测试**：新增 tests/test_table_caption_relation_contract.py（39 项：
前缀集、docx/pdf 判定、混排排序、版本分支、消费路径、非 fallback
零回归、devset skipif 验收 docx e0013→e0012 / pdf 零表关联）；版本
断言重锚 0.5.0（test_version_semantics / test_caption_relation_
contract / test_chunker_source_spans / test_models）；全量回归
**5113 passed**。提交：500f807（实现+契约）、975dff7（holdout 套件）。

**待裁决**：批次 7 封口（Option A 选择追认 + 验收）。

## 三十三、批次 7 封口裁决记录（2026-08-30，GPT 5.6 Sol，会话 cf170a6f）

**裁决结果**：
- Option A 选择追认：**通过**。理由：政策成文完整（§3.2 与沿革
  一致）；读兼容保障（not.contains 精确排除）；版本语义三者分工
  清晰（schema_version=writer 能力 / EVALUATOR_VERSION=consumer
  能力 / REPORT_VERSION=报告结构）。**schema_version 0.4.0 → 0.5.0
  正式生效**。
- 执行验收①–⑦**全部通过**。关键确认：docx 规则按 elements 列表
  顺序（body 迭代顺序）定义邻接、不跨族比较 index——设计正确；
  T3 前缀修正（"表格 2、"→"表 2、"）**追认为正向验证**（期望推导
  暴露 _CAPTION_RE 语义，生成前调整，未违反"永不重跑"原则）；
  holdout 纪律执行满分；评测归因加强断言（evaluator_version 不变 +
  全部 .metrics. 逐字节一致）PASS。
- **批次 7 正式封口，归档编号 `Stage-6-Batch-7-Closed`。**

**Stage 6 全周期封存（批次 1–7 全部封口）**：
| 批次 | 任务 | 封口标志 | 关键成果 |
|---|---|---|---|
| 1 | 图片 OCR text 机制 | holdout 首跑 all_pass | Image.text 可选字段，pdfplumber OCR 集成 |
| 2 | 图片 metadata 规范 | holdout 首跑 all_pass | metadata.alt / resource / image_index，schema 0.3.0 |
| 3 | text 元素 holdout | holdout 首跑 all_pass | 文本元素基线封存，预备跑机制确立 |
| 4 | 图片题注关联 | holdout 首跑 all_pass | has_caption relation，docx 邻接 + pdf 几何，schema 0.4.0 |
| 5 | 表格线性化 | holdout 首跑 all_pass | Markdown 格式统一，共享纯函数，零差异验收 |
| 6 | 评测 relation 消费 | 零差异验证 PASS | 参数化匹配器，EVALUATOR_VERSION 1.8 |
| 7 | 表格题注关联 | holdout 首跑 all_pass | table_has_caption relation，schema 0.5.0 |

成果：schema 0.2.0→0.5.0（三次升版）；5 轮 holdout 首跑封存 5 个
sha256；EVALUATOR_VERSION 1.6→1.8；6 份契约 + 1 份版本政策；测试
57 → 5113（+5056）。

**批次 8 指定（Stage 6 尾声：技术债盘点与优先级排序，开工许可已授予）**：
1. TODO/FIXME 审计：扫描分类——可立即修复（批次 8 内完成）/
   需专项设计（backlog GitHub issue，tech-debt 标签）/已过时（删除）。
2. 评测覆盖缺口分析：devset parser×format 覆盖矩阵；识别"零 GT 键
   → 恒 skip"指标族（如 table_caption_*）；输出待标注优先级清单
   （按 devset 扩展 ROI 排序）。
3. Holdout 维护成本评估：7 轮 holdout（含批次 3 预备跑）期望维护
   成本；是否需要"holdout 期望生成器"工具。
4. Schema 兼容性回归测试：旧 0.1.0–0.4.0 文档喂当前 writer（应拒绝
   写入旧版本）；0.5.0 文档喂模拟旧 consumer（应优雅降级、跳过未知
   relation type）。
- 交付物：docs/technical-debt-audit-batch8.md（分类清单+优先级+
  工时估算）+ 必要立即修复（commit main）+ backlog issues。
- 验收：无遗漏 TODO；评测覆盖矩阵可视化；schema 双向兼容测试通过。

**Stage 6 正式封存。继续搬运。**

## 三十四、批次 8 执行与验收记录（2026-08-30）

**任务**（批次 7 封口裁决指定，Stage 6 尾声技术债清理）：①TODO/FIXME
审计 ②评测覆盖缺口分析 ③holdout 维护成本评估 ④schema 双向兼容
回归测试。交付 docs/technical-debt-audit-batch8.md。

**执行**：
1. ① 扫描 app/evaluation/tests/scripts/docs 全部 py/md/json/toml：
   **零真实 TODO/FIXME 标记**（全部命中为 markdown 任务列表字面量，
   属契约测试输入），分类清单为空，无立即修复项。
2. ② 覆盖矩阵（实测）：7 个 devset manifest 共 31 文档，expectations
   全覆盖；annotations 仅 1/31（DC-MVP-001，且 figure_caption_pairs
   为空）。恒 null/未实现指标族：figure_caption_*（零 GT 对）、
   table_caption_*（无 GT 键，批次 7 §7 冻结）。**发现项**：
   heading_order GT 已采集 8 条但零消费（死数据）；real-01..05 真实
   语料+worksheets 已备未入 manifest。待标注优先级 P1–P5（按 ROI）
   见审计文档。
3. ③ holdout 维护评估：10 个 kit（7 private + 3 synthetic）对应裁决
   7 轮；一次性封存模型 = 零持续维护（expectations 冻结 + 首跑封存 +
   sha256 守卫 + git 字节保护）。**"期望生成器"建议不做**：自动从
   parser 输出生成期望=自证循环，会把 holdout 退化为回归测试；机械
   对照已由 dev/回归覆盖。
4. ④ 新增 tests/test_schema_compat_regression.py（10 项全过）：旧
   0.1.0–0.5.0 各时代形状全部通过当前 schema 校验（读兼容前向承诺
   落地为测试）；writer 一律 0.5.0；0.5.0 混排文档喂模拟批次 6
   consumer（只识 has_caption）优雅降级——跳过未知 type 不报错；
   真实 match_relation_pairs 路径行为不变 (1,1,1)；纯未知 type
   文档降级 (0,1,0) 不崩溃。
5. Backlog issues（GitHub tech-debt 标签，本仓库 #1–#5）：
   - #1 P1 补标注 DC-MVP-001 figure_caption_pairs（解锁恒 null 族）
   - #2 P2 补 DC-MVP-001-PDF annotation
   - #3 P3 heading_order GT 消费指标族设计
   - #4 P4 table_caption_*（annotation v1.1 + 标注 + 指标）
   - #5 P5 real-01..05 真实语料入 manifest
6. 验收对照：无遗漏 TODO ✅；覆盖矩阵可视化（3 表）✅；schema 双向
   兼容测试 10/10 ✅。全量回归 **5123 passed**。

**待裁决**：批次 8 封口（审计交付 + backlog 转出 + 双向兼容测试验收）。

## 三十五、批次 8 封口裁决记录（2026-08-30，GPT 5.6 Sol，会话 cf170a6f）

**裁决结果**：
- 批次 8 执行验收：**全部通过**（①零 TODO ✓ ②覆盖矩阵+backlog
  issues #1–#5 ✓ ③holdout 零维护+期望生成器"建议不做"采纳 ✓
  ④schema 双向兼容 10/10 ✓）。
- **批次 8 正式封口，归档编号 `Stage-6-Batch-8-Closed`。Stage 6
  完整封存（批次 1–8 全部归档）。**

**Stage 7 启动：数据质量与评测深化**，两轨并行：
- 轨道 A（标注解锁，人机协作）：批次 9（P1）DC-MVP-001
  figure_caption_pairs；批次 10（P2）PDF 侧 annotation。
- 轨道 B（评测能力扩展，纯开发）：批次 11（P3）heading_order 消费
  指标族；批次 12（P4）table_caption_*（annotation v1.1）；批次 13
  （P5）真实语料入 manifest。

**批次 9 指定（P1 标注解锁，开工许可已授予）**：补 DC-MVP-001 的
figure_caption_pairs（1 对）。执行：人工识别图片-题注对 → 提取
element 对应信息 → 更新 annotation → 重跑 evaluation 确认
figure_caption_* 解锁（null+no_annotation_pairs → 数值；其他指标族
不变，对比批次 8/7 封存基线）→ 全量回归 → 封口报告。验收：annotation
≥1 对；P/R/F1 ∈ [0,1] 数值且与标注一致；PDF 侧仍 null。
- 【执行前澄清】裁决示例格式 {"figure_id","caption_id"} 与冻结的
  annotation.schema.json v1.0（figure_marker/caption_text，
  additionalProperties=false，批次 6 契约）不符——按冻结 schema 执行，
  偏差在批次 9 报告中声明。

## 三十六、批次 9 执行与验收记录（2026-08-30，Stage 7 轨道 A）

**任务**（批次 8 封口裁决指定，P1 标注解锁）：补 DC-MVP-001 的
figure_caption_pairs（1 对），解锁 figure_caption_* 指标族。

**执行**：
1. 人工识别图-题注对：DC-MVP-001.docx 仅 1 图（§2.1 Embedded figure）
   + 其下题注段落 "Figure 1. Knowledge unit processing flow"——
   即批次 4 起已产出的 has_caption e0018→e0019 的端点。
2. 端点识别信息提取（裁决步骤②，从 parser 输出提取）：docx image
   元素 content=None、metadata.alt=None，识别文本=落盘资源文件名
   `image_966e35cc7ce36e24_para16_00.png`（评测运行 images 目录，
   批次 7 基线同名——命名确定性）；caption 文本人工可读。
3. **格式偏差声明**：裁决示例格式 {"figure_id","caption_id"} 与冻结
   annotation.schema.json v1.0（figure_marker/caption_text，
   additionalProperties=false，批次 6 契约）不符——按冻结 schema 执行：
   `[{"figure_marker": "image_966e35cc7ce36e24_para16_00.png",
   "caption_text": "Figure 1. Knowledge unit processing flow"}]`；
   annotation date 2026-08-03 → 2026-08-30（修订日）；jsonschema
   Draft202012 校验 0 错误。
4. 评测重跑（干净树 5d09f43，git_dirty=False）：
   outputs/evaluation-batch9-figcap-unlock.json。**DC-MVP-001 docx
   figure_caption_precision/recall/f1 = 1.0/1.0/1.0**（预测 1 条
   e0018→e0019、GT 1 对、命中 1——与标注一致，∈[0,1]）；PDF 侧仍
   null+no_annotation（未解锁，验收要求）。
5. 归因验证（scripts/verify_batch9_attribution.py）：对照批次 7 封存
   基线逐字段 diff，共 10 处且全部归因——6 处 = docx figure_caption_*
   value/reason 解锁（null+no_annotation_pairs → 1.0+null），4 处 =
   运行环境（wall_time×2、git_commit、run_timestamp_iso）。must-not-
   change 断言全过：evaluator_version 1.8 不变、PDF figure_caption_*
   不变、其余全部 .metrics. 路径逐字节一致。VERDICT: PASS。
6. 全量回归 **5123 passed**。

**验收对照（裁决验收标准）**：annotation ≥1 对 ✅；P/R/F1 数值且与
标注一致 ✅；PDF 侧仍 null ✅；全量回归 ✅。

**待裁决**：批次 9 封口（P1 解锁验收 + 格式偏差追认）。

## 三十七、批次 9 封口裁决与批次 10 指定（2026-08-30，Stage 7 轨道 A）

**裁决来源**：GPT 5.6 Sol（对话 cf170a6f，2026-08-30；全文封存
搬运线 outputs/gpt_ruling_b9_closure.json，4043 字符，经 conversation
API 读取——新标签页 DOM 未渲染回复）。

**格式偏差追认：通过，并修正裁决示例**。理由：①schema 契约优先
（annotation.schema.json v1.0 批次 6 冻结，键名 figure_marker/
caption_text）；②执行严格遵循冻结 schema（additionalProperties=
false），Draft202012 校验 0 错误；③识别文本选择合理（图片无
content/alt → 资源文件名作 figure_marker，符合批次 6 匹配器
from 侧识别逻辑）。GPT 自我修正：批次 9 指令示例
{"figure_id","caption_id"} 不准确，应为 {"figure_marker",
"caption_text"}——"此为裁决失误（未查阅冻结 schema），您的纠正
执行体现了契约优先原则"。annotation 元数据更新确认（date 修订、
annotator 不变）✓。

**批次 9 执行验收：全部通过**（逐项 ①–⑥）：①标注数据准备 ✓
（1 对，端点与批次 4 has_caption e0018→e0019 一致）；②annotation
更新 ✓；③评测验证 ✓（docx P/R/F1=1.0/1.0/1.0，PDF 侧仍
null+no_annotation 符合验收）；④归因验证 ✓（10 处全归因：
6 解锁 + 4 运行环境；evaluator_version 1.8 不变、PDF 不变、
其余 .metrics.* 逐字节一致；VERDICT: PASS）；⑤回归 ✓（5123
passed）；⑥验收标准对照 ✓。

**最终裁决：批次 9 正式封口，归档编号 `Stage-7-Batch-9-Closed`。**

**批次 10 指定（P2 PDF 侧标注，开工许可已授予）**：补完
DC-MVP-001 PDF 侧 figure_caption_pairs 标注，解决"题注被融合"
GT 口径问题（批次 4 §0 / 批次 7 契约 §0 归因：devset PDF 实测
表题注被 pdfplumber 融合进前一段落）。**两段式协议（强制）**：
1. 实证调查（步骤 1）：打开 devset/DC-MVP-001.pdf 人工识别
   图片-题注对；跑 parser 提取 elements 输出；对照分析"融合"
   现象，记录详细观察结果。
2. **下次回复中汇报步骤 1 结果**（须含：人工识别对数；parser
   输出对应 elements 的 element_id/content 片段；融合现象描述
   ——题注文本是否出现在段落中、可识别程度）。
3. **等待 GPT 基于步骤 1 结果裁决 Option A/B/C**，裁决前不得
   标注：
   - **A 标注融合段落**：GT caption_text=融合段落中的题注部分
     子串（与 parser 实际输出对齐、测真实匹配能力；融合致特征
     消失则可能无意义）。
   - **B 标注理想题注**：GT=理想独立题注文本即使 parser 未分离
     （反映"应该识别到什么"；不对齐 parser，可能恒 recall=0）。
   - **C 不标注**：figure_caption_pairs 空数组 + notes 字段说明
     （承认 parser 局限；PDF 侧评测永久降级 no_annotation_pairs）。
4. 裁决后执行步骤 3–5：更新 PDF 侧 annotation（注：裁决所称
   DC-MVP-001-annotation.json 实为 samples/private/devset/
   annotations/DC-MVP-001-PDF.json——新 annotation 文件，manifest
   需加 annotation_file 键）→ 重跑评测（仅 PDF 侧 figure_caption_*
   变化，对比批次 9 基线）→ 全量回归（5123+）→ 封口报告说明
   口径选择理由。

## 三十八、批次 10 执行与验收记录（2026-08-30，Stage 7 轨道 A）

**任务**（批次 9 封口裁决指定，P2 PDF 侧标注，两段式协议）：补完
DC-MVP-001-PDF 的 figure_caption_pairs 标注，解决"题注被融合"GT
口径问题。

**步骤 1 实证调查（已汇报，会话 cf170a6f）**：
1. 人工识别（pypdfium2 scale 2.0 渲染 3 页 PNG 视觉审查）：
   **图片-题注对 1 对**——page 2 流程图 PNG + 正下方题注
   "Figure 1. Knowledge unit processing flow"；另 page 1 有表题注
   "Table 1. Module status matrix"（表上方，table 侧，不在本批范围）。
   视觉转录对 page 1 细节有幻觉迹象 → 精确字符串一律以 parser 输出
   为权威，视觉仅确认版面。
2. parser 输出（fallback/pdfplumber，18 elements + 1 relation）：
   - e0011 image p2：content=None、无 alt、resource 文件名
     `image_2feac715bd0d5b4b_p2_00.png`（识别文本=文件名，批次 9
     docx 同范式）
   - e0009 caption p2（caption_regex 分类）：content 以题注文本为
     **精确前缀**，尾部融合约 30 词后续说明段落
   - e0004 paragraph p1：表题注 + 节标题 + 表体全部融合（批次 4 §0
     "融合"归因的真实主体——**表侧**现象）
   - relation has_caption e0011→e0009（rule=pdf_geometry_below，
     gap_pt=11.525）已产出
3. **融合现象澄清**：批次 4 §0"题注被融合进前一段落"实测仅发生于
   **表题注**（table 侧，影响未来 table_caption_*）；**图题注未被
   融合进前一段落**，而是被分离为独立 caption 元素、仅尾部融合后续
   段落（题注=前缀，子串匹配可命中）。
4. dry-run（冻结 match_relation_pairs 直接调用）：Option A 假想对
   → (num_pred=1, num_gt=1, matched=1)，P/R/F1=1.0/1.0/1.0；
   Option B 在本文档与 A 字符串完全相同（不可区分）；C 无实证障碍。

**步骤 2 口径裁决（已收到）**：**Option A（标注融合元素中的题注子串）
生效**。理由：①dry-run 实测无障碍；②口径一致性（批次 9 docx 范式
对齐 + 批次 6 契约 §2.3 天然兼容）；③GT 反映 parser 实际输出中可
识别的题注信息，前缀子串隔离核心题注文本；④融合现象澄清后无需
B/C 权宜；⑤A/B 本案不可区分，选 A 无损失。裁决并要求口径声明记入
annotation notes 字段。

**步骤 3–5 执行**：
1. 新建 samples/private/devset/annotations/DC-MVP-001-PDF.json
   （gitignored 私有标注）：annotation_version 1.0、doc_id
   DC-MVP-001-PDF、figure_caption_pairs 1 对（figure_marker=
   `image_2feac715bd0d5b4b_p2_00.png`、caption_text=
   "Figure 1. Knowledge unit processing flow"）；manifest 该 entry
   加 annotation_file 键（manifest.schema v1.0 合法可选键，无需升版）。
   jsonschema Draft202012 校验：annotation PASS、manifest PASS。
2. **格式偏差声明（二处，沿批次 9 契约优先先例）**：①裁决示例的
   `notes` 字段与冻结 annotation.schema.json v1.0（无该键 +
   additionalProperties=false）冲突 → 不写入标注文件，口径声明改记
   本节与封口报告（本段即口径记录：PDF 图题注 'Figure 1. Knowledge
   unit processing flow' 为 e0009.content 前缀，尾部含 pdfplumber
   融合的约 30 词说明文字；GT caption_text 取前缀子串以隔离核心题注
   文本，与 caption_regex 启发式边界一致）；②裁决示例的
   document_id/format 键与冻结 schema（annotation_version/doc_id）
   不符 → 按冻结 schema 执行。另评测命令按实际 CLI
   （evaluation.cli run --manifest ... --parser fallback --max-chars 800）。
3. 评测重跑（干净树 9b016b4，git_dirty=False）：
   outputs/evaluation-batch10-pdf-unlock.json。**DC-MVP-001-PDF
   figure_caption_precision/recall/f1 = 1.0/1.0/1.0**（预测 1 条
   e0011→e0009、GT 1 对、命中 1——与 dry-run 及标注一致）；docx 侧
   维持 1.0/1.0/1.0 不变。
4. 归因验证（scripts/verify_batch10_attribution.py）：对照批次 9
   封存基线逐字段 diff，共 13 处且全部归因——6 处 = PDF
   figure_caption_* value/reason 解锁（null+no_annotation →
   1.0+null）；3 处 = PDF chunk_boundary_* reason 迁移
   （no_annotation → no_ground_truth_anchors，annotation 文件出现
   但未标 anchors 的降级路径变化，value 两轮均 null 不变）；4 处 =
   运行环境（wall_time×2、git_commit、run_timestamp_iso）。
   must-not-change 断言全过：evaluator_version 1.8 不变、docx 全部
   字段零差异（wall_time 环除外）、其余全部 .metrics. 路径逐字节
   一致。VERDICT: PASS。
5. 全量回归 **5123 passed**。

**验收对照（裁决验收标准）**：PDF annotation 含 figure_caption_pairs
1 对 ✅；PDF P/R/F1=1.0/1.0/1.0 ✅；docx 维持 1.0/1.0/1.0 ✅；
归因 PASS ✅；全量回归 5123 ✅；notes 口径声明——schema 冲突改记
本节（偏差待追认）⚠️。

**待裁决**：批次 10 封口（P2 解锁验收 + notes 偏差追认）。

## 三十九、批次 10 封口裁决与批次 11 指定（2026-08-30，Stage 7 轨道 A）

**裁决来源**：GPT 5.6 Sol（对话 cf170a6f，2026-08-30；全文 5117 字符
封存搬运线 outputs/_b10closure_dump.txt，经 conversation API 读取）。

**偏差追认：全部通过**：
1. chunk_boundary reason 迁移追认通过——机制正确（annotation 存在
   但未标 anchors → no_ground_truth_anchors 是判定链正确行为）、
   value 两轮均 null（未实质影响指标）、因果必然（挂接文件不标
   anchors 的副作用非缺陷）。后续建议（非强制）：PDF
   chunk_boundary_anchors 标注列 backlog（P2 扩展项），不阻塞封口。
2. notes 字段处置追认通过——契约优先（冻结 schema > 裁决示例），
   口径已文档化于 §三十八。附加裁决：未来可升 annotation.schema
   v1.1 加可选 notes 字段（不阻塞本批）。
3. 键名/路径/命令/提交对象四处偏差全部追认（沿批次 9 先例）。

**批次 10 执行验收：全部通过**（①标注执行 ✓ ②评测验证 ✓（PDF
1.0/1.0/1.0 与 dry-run 一致，docx 不变）③归因 PASS ✓（13 处全归因：
6 解锁 + 3 reason 迁移 + 4 环境）④回归 5123 passed ✓ ⑤验收对照 ✓）。

**最终裁决：批次 10 正式封口，归档编号 `Stage-7-Batch-10-Closed`。**

**Stage 7 进度**：轨道 A 前两优先级完成（批次 9 P1 docx + 批次 10
P2 PDF，figure_caption_* 双侧解锁 1.0/1.0/1.0）；轨道 B 待启动
（P3 heading_order / P4 table_caption_* / P5 真实语料）。

**批次 11 指定（P3 heading_order 消费指标族，开工许可已授予）**：
激活已采集的 8 条 heading_order GT（批次 8 审计发现：已采集零消费
的死数据），实现 heading_order_precision/recall/f1。两段式协议：
1. 步骤 1 GT 语义调研（下次回复汇报）：schema 定义；GT 分布
   （文档 ID + 条数）；1–2 个具体示例（GT vs parser 输出对照）；
   推荐匹配规则（Option 1 序列匹配 / Option 2 层级树匹配 /
   Option 3 存在性匹配）+ 理由。
2. 等 GPT 裁决匹配规则与设计方案后再实现（compute_heading_order_prf
   + runner 消费 + EVALUATOR_VERSION 1.8→1.9 + macro average
   纳入决策 + 验证 heading_order_* 不再 null + 分数合理性审核）。

## 四十、批次 11 执行与验收记录（2026-08-30，Stage 7 轨道 B）

**任务**（批次 10 封口裁决指定，P3 heading_order 消费指标族，两段式）：
激活已采集 8 条 heading_order GT，实现 heading_order_* 指标族。

**步骤 1 调研（已汇报）**：schema 为扁平有序列表（level+text，无树边）；
GT 全部集中于 DC-MVP-001 docx（8 条）；parser 实跑对照 9 heading vs
8 GT——8 条顺序/层级/文本精确一致，唯一差异 = 主标题被解析为 heading
（多检 1 条）；dry-run（Option 1，LCS）P=0.8889/R=1.0/F1=0.9412。

**步骤 2 裁决（已收到）**：匹配规则 **Option 1（序列匹配）**；三设计点：
实现位置沿惯例 annotation_metrics.py + heading_order_prf；REPORT_VERSION
维持 1.3；heading_order_* 不入 macro average（标注依赖族，GT 覆盖稀疏）。

**执行**：
1. `evaluation/annotation_metrics.py` 新增 `heading_order_prf`：匹配键
   =（metadata.level 相等）AND（normalize_text(content) ==
   normalize_text(text)）严格相等；LCS 有序一对一 DP 对齐；降级矩阵
   pipeline_failed / no_annotation / no_ground_truth_headings /
   no_predicted_headings（GT>0 时 recall=0.0）。
2. `evaluation/runner.py` 挂接消费（annotation 复用同一加载路径）；
   `_RATIO_METRICS` 白名单未动 → heading_order_* 确认不入 macro。
3. **EVALUATOR_VERSION 1.8 → 1.9**（evaluation/__init__.py 版本历史
   补 1.9 条目）；REPORT_VERSION 维持 1.3。
4. `docs/schema-version-policy.md` §5 补分工规则（EVALUATOR_VERSION
   minor = 指标族/匹配算法/降级逻辑；REPORT_VERSION minor = 报告结构
   变更，指标键扩展不升）。
5. 契约测试 `tests/test_heading_order_prf.py` 11 项：完美 8/8、多检
   （DC-MVP-001 实测情形 8/9/8）、漏检 7/8、乱序 LCS 2/3、level 不匹
   配、空白规范化等价、大小写敏感（normalize_text 不折叠大小写——
   与冻结匹配器族一致的严格相等口径）、降级路径 ×4。另两处既有版本
   钉测试随升（test_relation_consumption_contract.py /
   test_parser_auto.py 的 1.8 字面量 → 1.9）。
6. 评测重跑（干净树 0d75d6f，git_dirty=False）：
   outputs/evaluation-batch11-heading-unlock.json。**DC-MVP-001 docx
   heading_order_precision/recall/f1 = 0.8889/1.0/0.9412**（与
   dry-run 一致，主标题多检被 precision 暴露）；DC-MVP-001-PDF
   null+no_ground_truth_headings（annotation 已挂接但无该键——
   注意非 no_annotation，裁决原文"其他文档 null+no_annotation"对
   PDF 侧不适用，批次 10 已挂 annotation 文件）。
7. 归因验证（scripts/verify_batch11_attribution.py）：对照批次 10
   封存基线逐字段 diff，共 11 处且全部归因——6 处 = 双文档
   heading_order_* 新增（docx 数值 + PDF 降级）；1 处 =
   evaluator_version 1.8→1.9；4 处 = 运行环境。must-not-change 全过：
   report_version 1.3 不变、summary 零差异（macro 未纳入验证）、
   其余全部指标路径零差异。VERDICT: PASS。
8. 全量回归 **5134 passed**（5123 + 11 新增）。

**执行偏差声明（二处，待追认）**：
1. 规范化函数：裁决示例 normalize_heading_text（strip+lowercase+
   collapse）→ 实际复用 app.chunkers.structural.normalize_text
   （collapse+strip，**不折叠大小写**）——与 figure_caption/
   chunk_boundary 冻结匹配器族同规范器，且 dry-run（裁决通过的
   0.8889/1.0/0.9412）即此语义；大小写敏感作为契约测试钉死。
2. 裁决评测命令 manifest 路径 samples/private/devset/devset-docx.
   manifest.json 不存在 → 实际 samples/private/devset/manifest.json
   （唯一主 devset manifest，批次 4 起不变）。

**验收对照（裁决验收标准）**：heading_order_prf 落地 ✅；EVALUATOR_
VERSION 1.9 ✅；REPORT_VERSION 1.3 ✅；不入 macro ✅；契约测试五类
场景 ✅；DC-MVP-001 docx 0.8889/1.0/0.9412 ✅；PDF 侧 null+
no_ground_truth_headings（裁决预期 no_annotation 的修正，见执行⑥）
⚠️；归因 PASS ✅；全量回归 5134 ✅。

**待裁决**：批次 11 封口（P3 验收 + 二处执行偏差追认）。

## 四十一、批次 11 封口裁决与批次 12 指定（2026-08-31，Stage 7 轨道 B）

**裁决来源**：GPT 5.6 Sol（对话 cf170a6f，2026-08-31；全文 6147 字符
封存搬运线 outputs/_b11closure_dump.txt，经 conversation API 直读）。

**偏差追认：全部通过**：①规范化函数复用 normalize_text（口径一致性
+ dry-run 语义隐式通过 + 大小写敏感契约钉死——并确认大小写敏感对
heading 匹配合理）；②manifest 路径为裁决示例错误，修正正确。
③PDF 侧 no_ground_truth_heads（原文笔误，实为 no_ground_truth_
headings）预期修正追认——annotation 存在 ≠ 所有指标族都有 GT。

**批次 11 执行验收：全部通过**（①实现 ✓ ②测试 5134 ✓ ③评测验证 ✓
（docx 0.8889/1.0/0.9412 与 dry-run 一致；PDF 降级语义正确）④归因
PASS ✓ ⑤验收对照 ✓）。

**最终裁决：批次 11 正式封口，归档编号 `Stage-7-Batch-11-Closed`。**

**Stage 7 进度**：轨道 A 全部完成（批次 9/10）；轨道 B 批次 11 完成，
余 P4（table_caption_*）/P5（真实语料）。Backlog 决策：PDF
chunk_boundary_anchors 标注暂不排期（待 P4/P5 后重评）。

**Issues 处理指令**：关闭 GitHub issues #1（P1，批次 9 完成）与
#2（P2，批次 10 完成），下次回复确认或说明保留原因。

**批次 12 指定（P4 table_caption_* 指标族，开工许可已授予）**：
实现 table_caption_precision/recall/f1，消费 table_has_caption
relation（批次 7 生成，批次 6 匹配器已参数化冻结）。两段式协议：
1. 步骤 1 schema 升级设计（下次回复汇报）：annotation.schema.json
   v1.0→v1.1，新增 table_caption_pairs（table_marker + caption_text，
   类比 figure_caption_pairs）；additionalProperties 策略 Option A
   （维持 false，严格验证，推荐）/ Option B（放宽 true）；完整 schema
   片段 + 理由 + diff。
2. 等 GPT 裁决 schema 设计后执行步骤 2–6：更新 schema → 标注
   DC-MVP-001 docx/PDF（PDF 需决定口径：批次 4/7 归因表题注被
   pdfplumber 融合进前一段落 → devset pdf 表 relation 恒 0 条）→
   实现 table_caption_prf（复用 match_relation_pairs，
   relation_type="table_has_caption"）→ EVALUATOR_VERSION 1.9→1.10
   → 评测验证 → 封口。macro 不纳入（沿标注依赖族惯例）。

## 四十二、批次 12 执行与验收记录（2026-08-31，Stage 7 轨道 B）

**裁决依据**：批次 12 步骤 1 裁决（同会话，2026-08-31）——schema
设计通过（Option A 维持 additionalProperties=false；$comment 措辞
修正"v1.0 精确快照"；$id 偏差追认，沿用 manifest 先例 $id 恒不变）；
PDF 口径 **Option A（诚实曝光）**：题注被 pdfplumber 融合进前一段落
→ 0 预测 relation，GT 照标，recall=0.0 曝露缺陷；issues #3 关闭指令。

**执行偏差声明（契约优先，待追认）**：
1. 裁决示例路径 `evaluation/schemas/annotation.schema.json` /
   `docs/ADOPTION.md`——实际为 `schemas/annotation.schema.json` /
   根 `ADOPTION.md`（仓库真实布局）。
2. 裁决示例 `table_caption_prf` 调用 `_pair_prf(document=...,
   annotation=..., pairs_key=...)`——实际冻结契约：
   `match_relation_pairs(document, pairs, *, relation_type,
   from_marker_key, to_marker_key) -> counts` + `_pair_prf(counts,
   prefix)`；table_caption_prf 按 figure_caption_prf 同构包装。
3. 裁决示例 docx `date: "2026-08-03" → "2026-08-30"`——实际原值
   2026-08-30，修订日记 2026-08-31（实际执行日）。
4. 验收项"其他文档 table_caption_* = null + no_annotation"——本
   devset 仅 2 文档且均已挂 annotation v1.1，该路径本轮无实例
   （契约测试已钉 no_annotation/no_annotation_pairs 降级）。

**步骤 2（schema v1.0 → v1.1，commit 544ba88）**：title/
description/annotation_version enum ["1.0","1.1"]/新增
table_caption_pairs（与 figure_caption_pairs 严格同构，items
additionalProperties=false）/顶层 allOf v1.0 精确快照
（table_caption_pairs: false）。$id 不变。六项校验全符预期：
既有两份 v1.0 文件继续合法；v1.0+新键被拒；v1.1±新键合法；
items 错键被拒；未知版本号被拒。

**步骤 3（标注，gitignored 不进 git）**：DC-MVP-001.json 与
DC-MVP-001-PDF.json 均升 annotation_version 1.1，新增
table_caption_pairs 各 1 对：table_marker = "Code | Element |
Expected handling | Integrity marker"（表头行子串，两文档表元素
同串）、caption_text = "Table 1. Module status matrix"；date 修订
2026-08-31。两文件通过 v1.1 schema 校验。dry-run：docx counts
(1,1,1)；PDF counts (0,1,0)。

**步骤 4（实现，commit 690e676）**：annotation_metrics.py 新增
table_caption_prf（figure_caption_prf 同构，relation_type=
"table_has_caption"）+ __all__；runner.py 接入；EVALUATOR_VERSION
1.9 → 1.10（版本历史补 v1.10 条目，清理 v1.8/v1.9 陈旧"（当前）"
标记）；REPORT_VERSION 1.3 不变；_RATIO_METRICS 白名单不动
（不纳入 macro）。新增契约测试 13 项
（tests/test_table_caption_prf.py：完美/表格空白规范化/多检 2:1/
题注错配 0 分/PDF Option A 零预测/他类 relation 不计/降级×4/
三键钉/版本钉/macro 排除钉）；既有版本钉 2 处随升（1.9 → 1.10）。
全量回归 5147 passed（5134+13）。

**步骤 5（评测验证，干净树 git_dirty=False，commit 690e676）**：
DC-MVP-001 docx table_caption_* = 1.0/1.0/1.0（与 dry-run 一致）；
DC-MVP-001-PDF = precision null+no_predicted_relations / recall
0.0 / f1 null+precision_or_recall_not_evaluated（Option A 诚实
曝光，与裁决预期逐字一致）；validate-report 通过。归因验证
（scripts/verify_batch12_attribution.py，对照批次 11 基线）：
11 处差异全部归因（6 双文档 table_caption_* only-in-new +
evaluator_version 1.9→1.10 + 4 运行环境），0 unexpected；
must-not-change 全过（report_version=1.3 / summary 零差异 /
其余指标族零差异）。VERDICT: PASS。

**Issues**：#1/#2/#3 已关闭（#3 按本批裁决指令，评论引用
Stage-7-Batch-11-Closed）。

## 四十三、批次 12 封口裁决与批次 13 指定（2026-08-31，GPT 5.6 Sol，会话 cf170a6f）

**裁决存证**：outputs/_b12closure_dump.txt（5597 字符，gitignored）。

**批次 12 封口**：归档编号 **Stage-7-Batch-12-Closed**。执行验收全部
通过（schema v1.1 六项校验 / 标注 dry-run / 实现同构复用 / 评测验证
与预期逐字一致 / 归因 PASS 11 处全归因 / git 三提交 ff-only + push /
issues #3 已关）；验收标准 14/14。

**偏差追认（4 处全部通过）**：
1. 路径修正（evaluation/schemas/ → schemas/；docs/ADOPTION.md → 根
   ADOPTION.md）——裁决未查阅仓库布局。
2. 函数包装语义等价——冻结契约 counts 元组 + _pair_prf(counts,
   prefix)，与 figure_caption_prf 严格同构，"分离匹配逻辑与指标计算
   更清晰"。
3. date 修订日——裁决基于过时记忆（批次 9 日期），实际执行日
   2026-08-31 正确。
4. "其他文档 no_annotation"验收项空集——降级语义已由契约测试钉死，
   验收项为泛化描述，devset 覆盖受限属正常。

**Stage 7 进度**：轨道 A（批次 9/10）完成；轨道 B 2/3——批次 11
（heading_order_*，1.9）、批次 12（table_caption_*，1.10）完成，
剩 P5（真实语料入 manifest）。

**批次 13 指定（P5 真实语料入 manifest，开工许可已授予）**：
真实语料 10 文件（real-01.docx / real-02.pdf / real-03.md /
real-04.html / real-05.txt + 对应 worksheets）入 devset manifest，
无 GT 标注 → 初期仅生成 expectations（人工审核合理性），不设
annotation_file。步骤 1（下次汇报）：文件清单（路径/格式/大小）+
快速解析测试（fallback parser 报错检查）+ worksheets 格式数量确认；
步骤 2–5 待裁决（生成 expectations → manifest 条目 → 评测验证
（2→12 文档，原 2 文档不变 + 新 10 文档合理性 + macro 参与数重算）
→ 归因）。

**Backlog 决策**：PDF chunk_boundary_anchors 标注暂不排入批次 13，
待 P5 完成后重评（触发条件：需全面解锁 chunk_boundary_* 或专项
chunking 优化）。

## 四十四、批次 13 执行记录（P5 真实语料入 manifest，2026-08-31）

**裁决依据**：outputs/_b13s1ruling_dump.txt（步骤 1 裁决：
Option 1 契约优先·人工推导 + 步骤 2–6 执行指令）。

**步骤 2（8 份 worksheets 人工推导，Option 1 口径）**：
全部完成（worksheets/DC-REAL-00{1,2,3}-{DOCX,PDF}.md、
DC-REAL-004-PDF.md、DC-REAL-005-DOCX.md），遵守「不得用 parser
输出反推」契约——推导仅用 pypdfium2 渲染目检 + pdfplumber 文本层/
字体属性扫描 + docx 原始 XML 解包；parser 输出仅作冒烟对照。

人工 GT 总表（heading / table / image / caption）：

| doc_id | heading | table | image | caption | markers |
|---|---|---|---|---|---|
| DC-REAL-001-DOCX | 70 | 1 | 1 | 0 | 5 |
| DC-REAL-001-PDF | 69 | 1 | 3 | 0 | 5 |
| DC-REAL-002-DOCX | 15 | 15 | 2 | 0 | 5 |
| DC-REAL-002-PDF | 13 | 12 | 5 | 0 | 5 |
| DC-REAL-003-DOCX | 13 | 0 | 8 | 0 | 5 |
| DC-REAL-003-PDF | 13 | 0 | 9 | 0 | 5 |
| DC-REAL-004-PDF | 6 | 1 | 2 | 3 | 5 |
| DC-REAL-005-DOCX | 109 | 11 | 1 | 0 | 5 |

40 个 markers 全部大小写敏感精确检索 1x 命中验证（pdfplumber
PDF 全文 / docx 段落级拼接全文），纯 ASCII，无跨行断裂、无小写
碰撞。重大发现（详见各 worksheet 复核备注）：002-DOCX 封面整体
嵌套 w:sdt；003-PDF p1 隐形文本层（渲染全白但文本层可提取
1189 字符）；001 同源对版本不同（PDF=Communities 版、
DOCX=DFES 版），markers 不可互用；002-PDF ADR 1.8.3.1 大表
跨页断裂（per-physical-grid 计 12）。

**步骤 3（manifest 合并，devset 2→10）**：
manifest.draft.json 补齐 8 条目（categories + inline
expectations）；live manifest.json = 2 MVP + 8 real = 10 文档、
6 内容组、5 PDF + 5 DOCX、12 categories（含 MVP 的
integrity-markers）。annotation 依赖指标族（figure/table_caption/
heading_order/chunk_boundary）对 8 新文档全部按契约降级
null + no_annotation（P5 不设 annotation_file）。
双清单均通过 manifest.schema.json v1.0 + 路径校验。

**步骤 4（评测验证，干净树 git_dirty=False，commit 81051c9）**：
10/10 pipeline 成功；schema_valid / text_preservation /
text_char_multiset_p&r / heading_boundary_compliance 全 1.0；
required_markers 9/10 通过；silent_drop_total 51（001-PDF 22 /
003-PDF 8 / 002-DOCX 7 / 004-PDF 7 / 002-PDF 3 / 003-DOCX 1 /
其余 0）。**DC-REAL-002-DOCX 是唯一 markers 失败**（缺 3 个：
封面 sdt 嵌套漏检——P5 设计目的即曝光此类真实欠提取）。
real-005（裁决指定头号样本）：四类型计数与 parser 逐项精确
一致（109/11/1/0）、markers 5/5、silent_drop 0。
validate-report 通过（report_version 1.3 / evaluator 1.10）。

**冒烟对照**（scripts/compare_batch13_smoke.py，VERDICT PASS）：
逐文档逐类型 GT vs parser 差异表，全部 >50% 差异已归因：
001-PDF table +300%（条款布局误判为表）；002-PDF heading +246%
（表单字段标签误判）；003-PDF image −89%、002-PDF image −60%
（矢量图不产 raster）；004-PDF caption −100%（题注文字碎片化）；
002-DOCX image −100%（sdt 嵌套漏检）。

**步骤 5（归因验证，scripts/verify_batch13_attribution.py，
VERDICT PASS）**：对照批次 12 基线 31 处差异全部归因——
devset 扩容 5 处、per_doc 2→10、summary 扩容 24 处（markers
2→10/9/1、silent_drop 3→51、participating_docs 扩容）、运行
环境 2 处；0 unexpected；MVP 两文档除 wall_time 零漂移；
evaluator_version=1.10 / report_version=1.3 不变（评测器零改动）。

**步骤 6（全量回归）**：5147 passed（129.78s），零失败。

**偏差声明（契约优先，待裁决追认）**：
1. 裁决 2.2/步骤 3 的独立 expectations JSON 文件 + manifest
   `expectation_file` 键不存在于冻结契约（manifest.schema.json
   v1.0 additionalProperties=false，v1.0 快照仅允许
   element_count_by_type/required_markers 两键、inline 结构）；
   实际按冻结契约 inline 转录，worksheets 即人工推导档案。
2. 裁决的指标名 text_exact / structure_preservation /
   macro_precision / documents_evaluated 不存在于 report
   schema v1.3；实际对应 required_markers_check /
   element_count_by_type + silent_drop_count / ratio_macro_
   averages（分族）/ devset.file_count。
3. 裁决的 categories 词表（has_headings/has_tables 等）与
   worksheets 实际受控词表（11 项）不一致，按 worksheet 词表。
4. 裁决步骤 4「新增 8 文档无 null」与其自身「标注依赖指标
   降级 null + no_annotation」矛盾，按后者执行。
5. 裁决步骤 6 的 git add 含 samples/private/ 路径——项目隐私
   契约 samples/private/ 永不进 git（gitignored）；提交物 =
   两个脚本 + ADOPTION.md。

## 四十五、批次 13 封口裁决记录（Stage-7-Batch-13-Closed，2026-08-31）

**裁决来源**：GPT 5.6 Sol，对话 cf170a6f（批次 13 完成报告之后）。
报告送达后首轮裁决流在「Silent_drop 统计·其余」处服务端截断，
经续传请求补齐 ④–⑥ 核验与三项最终结论。

**核验结论（裁决原文摘要）**：
- 契约偏差 5 条全部追认（inline expectations / 指标名映射 /
  worksheet 词表 / 标注依赖降级 null / 私有路径不进 git），
  理由均为「契约优先，冻结 schema > 裁决草案」。
- ① real-005 headline ② 8 文档 GT 主表 ③ Step 4 评测
  ④ Step 5 烟雾对比（7 处 >50% 偏差归因质量确认）
  ⑤ Step 6 归因验证（31 diff 白名单 + MVP 零漂移 + 版本封口）
  ⑥ 全量回归 5147——六项全部 ✓。
- 最终裁决：1) 批次 13 封口通过，归档编号 Stage-7-Batch-13-Closed；
  2) Push 授权通过（立即执行 ff-only 合并并推送）；
  3) 下一批次指定 = 批次 14（修复 w:sdt 嵌套内容欠提取）。

**执行偏差（本轮新增 2 条，沿既定「契约/事实优先 + 编号声明」模式）**：
1. 裁决 push 指令中的分支名 integration/stage7-batch13-real-expansion
   不存在；实际集成分支 = integration/stage7-batch12-table-caption
   （commit 4ed70ab），ff-only 合并按实际分支执行。
2. 裁决推送内容列出的 manifest.json 更新位于 samples/private/
   （gitignored，隐私契约永不进 git）；实际推送内容 = 两个脚本 +
   ADOPTION.md §四十四（4ed70ab 已含）。main 检出于指示线 worktree，
   ff-only 合并在该 worktree 执行（同分支不能双 worktree 检出，
   git 约束）。

**批次 14 指令（开工许可已授予，先方案后实现）**：
- 目标：修复 docx parser 的 w:sdt 嵌套欠提取（当前只扫 w:body
  顶层子元素；DC-REAL-002-DOCX 封面嵌套 → heading 10/15、
  image 0/2、markers 0/3、silent_drop 7）。
- 步骤 1（本轮先做）：分析 DC-REAL-002-DOCX 的 XML 嵌套结构；
  在方案 A（递归扫描 w:sdt/w:sdtContent，裁决推荐）与
  B（入口扁平化预处理）间做选择，汇报选择 + 理由 + 实现伪代码，
  **等裁决技术方案后再实现**。
- 步骤 2–4：实现 + 合成 docx 测试（嵌套 heading/paragraph/table
  顺序断言）→ 验证 002-DOCX（heading 15 / image 2 /
  silent_drop 0 / markers 3/3）→ devset 重跑 + 归因
  （002-DOCX 改善，其余 9 文档零漂移）→ 封口（回归 + 记录 +
  合并推送）。验收标准 7 项见裁决原文。

## 四十六、批次 14 执行记录（w:sdt 嵌套欠提取修复，2026-08-31）

**技术方案裁决（会话 cf170a6f，2026-08-31）**：Option A（递归扫描生成器）批准，
4 项理由全部成立；实现伪代码确认；4 项边界声明确认（无 sdtContent 跳过／嵌套
sdt 递归／w:tc 内 sdt 不处理／heading 按实测归因）。验收标准调整：heading
10 → 13–15（范围容差）、image 0 → 2（精确）、silent_drop 7 → 0–2、
required_markers 0/3 → 3/3。执行指令：实现 + 8 项测试 + 全量回归 5155 +
002-DOCX 验证 + devset 重跑归因 + 文档 + 封口。

**实现（integration/stage7-batch14-sdt-nested，基于 main@69b4d1c）**：
- `app/parsers/fallback_parser.py`：新增 `_iter_flow_elements(el)` 递归生成器
  （深度优先产出 w:p/w:tbl，下钻 w:sdt/w:sdtContent；其余 tag 跳过）；
  `_parse_docx` 主循环迭代源 `body.iterchildren()` → `_iter_flow_elements(body)`，
  段落/图片/表格分支逻辑与计数器零改动。
- 裁决偏差声明（已在步骤 1 汇报）：裁决所写 `app/parsers/docx_parser.py`
  不存在，实际文件为 `app/parsers/fallback_parser.py` 的 `_parse_docx()`。

**已知边界（裁决要求记录）**：批次 14 修复 body 顶层 w:sdt 嵌套内容欠提取。
已知边界：表格单元格（w:tc）内的 w:sdt 未处理，需单独修复（backlog）。

**测试（tests/test_docx_sdt_nested.py，8 项全过）**：
sdt 内 heading 提取与 paragraph_index 连续；文档顺序 DFS（A,sdt(B,C),D）；
sdt 内表格与 table_index 计数；嵌套 sdt 递归（2 层）；裸 sdt（无 sdtContent）
跳过且零警告；空 sdtContent 跳过；混合结构（封面 sdt + body 交错，计数器连续，
schema 校验通过）；无 sdt 文档零回归。

**验收（对照调整后标准）**：
- 回归：pytest 全量 **5155 passed**（5147 + 8，零回归）。
- DC-REAL-002-DOCX：heading **10 → 15（GT=15，精确命中）**；image
  **0 → 2（GT=2 精确）**；table 15 不变（GT=15）；silent_drop
  **7 → 0**（标准 0–2）；required_markers **0/5 → 5/5**（封面 3 个全恢复，
  另 2 个 GT marker 同步恢复）；image_resource_exists_ratio
  null(no_image_elements) → **1.0**；element_count_total 57 → 81
  （+15 heading/图片增量 +9 封面普通段落）。
- devset 重跑（outputs/evaluation-batch14-real-corpus.json，报告校验通过）：
  10/10 成功；归因 **仅 DC-REAL-002-DOCX 变化，其余 9 文档逐指标零漂移**；
  summary.silent_drop_total 51 → 44（−7，恰为 002 的全部 drop）。
- devset_status=incomplete（10 文件，pilot baseline，不代表项目总体准确率）。

## 四十七、批次 14 封口裁决记录（Stage-7-Batch-14-Closed，2026-08-31）

**裁决结论**（会话 cf170a6f，GPT 5.6 Sol）：
- 执行验收全部通过：实现 ✓（Option A 按批准伪代码，路径偏差追认）；
  8 项测试 ✓；全量回归 5155 ✓（零回归）；002-DOCX 精确达标
  （heading 15/15、image 2/2、silent_drop 0、markers 5/5 超预期、
  image ratio 1.0、element_total 81）；devset 归因 PASS（其余 9 文档
  零漂移、MVP 两文档零漂移、silent_drop_total 51→44）；已知边界
  文档化 ✓（§四十六）。
- **归档编号：Stage-7-Batch-14-Closed。**
- **合并推送授权：通过**（ff-only 合并 integration/stage7-batch14-sdt-nested
  @ bbb7022 并推送 origin/main，立即执行）。

**Stage 7 全景回顾（裁决原文）**：轨道 A 批次 9/10（figure_caption_pairs
标注解锁，1.0/1.0/1.0）；轨道 B 批次 11（heading_order_*）/12
（table_caption_*）/13（真实语料 devset 2→10）；修复批次 14
（w:sdt 欠提取）。全部封口。

**下一批次候选（裁决列出，待确认）**：A：PDF 矢量图 image 计数修复
（影响 3 文档，优先级中，可行性高，裁决推荐第一）；B：004-PDF 多栏题注
碎字符（复杂度最高）；C：002-PDF 表单域标签误判；D：001-PDF 跨页表格
拆分；或进入 Stage 8（剩余修复归 backlog）。
确认结果见下一节记录。

## 四十八、批次 15 执行记录（PDF 矢量图 image 计数修复，Option A）

**技术裁决**（会话 cf170a6f，GPT 5.6 Sol，2026-08-31）：调查汇报确认
（缺口重核/根因/区分特征/002-p7 推翻矢量图表假设均 ✓）；**Option A
（pdfplumber 曲线聚类矢量图检测）裁决通过**，Option B（颜色子聚类）不推荐
（003 可 9/9 但 002 超计 6/5，净效果更差）；5 项边界声明确认生效，
立即执行步骤 2–6。

**实现**（app/parsers/fallback_parser.py）：
- 模块级 `_vector_figure_clusters(page)`：rects/lines/curves 按 bbox 空间
  聚类（gap 15pt 贪心合并），簇含 ≥1 条 curve 且 bbox ≥100×100pt 计为
  1 个矢量图；常量 `_VECTOR_FIGURE_GAP_PT/_MIN_W/_MIN_H`。
- `_parse_pdf` 栅格循环后新增矢量图发射，镜像栅格路径：bbox 进
  source_locator、`_render_pdf_image_region_verbose` 渲染簇区域到
  image_output_dir（文件名 `p{page}v` 前缀防碰撞）、confidence 0.5、
  metadata.kind=vector_cluster；聚类异常 → 结构化警告
  `pdf_vector_cluster_failed`，不崩溃。

**测试**（tests/test_pdf_vector_graphics.py，8 项全过）：合成 PDF 工厂
（手写最小 PDF 字节，无新增依赖；多段路径→curve、单段线→line、re→rect、
/Subtype /Image XObject→栅格）。用例：单大曲线识别／曲线+矩形混合簇／
小簇（<100×100）排除／纯 rects+lines 表格零误报／栅格+矢量共存各计 1／
gap 15pt 近合远分／bbox 重叠聚 1／边界恰 100×100 包含。
实现期发现（已体现在用例）：pdfplumber curve bbox 取**锚点** hull
（起/终点），不含贝塞尔控制点。

**验收数据**：
- 全量回归 **5163 passed**（5155+8，零回归，符合裁决预期）。
- 真样重解析：002-PDF image 2→**4**（GT 5，−1=边界 1）；003-PDF
  1→**7**（GT 9，−2=边界 2）；004-PDF 1→**2**（GT 2 精确）；
  MVP-PDF 1/1、001-PDF 3/3 不可回归项零变化。image 短缺合计 12→**3**。
- devset 重跑（outputs/evaluation-batch15-vector-graphics.json，报告
  Schema 校验通过）：10/10 成功；归因**仅 002/003/004-PDF 三文档变化，
  其余 7 文档逐指标零漂移**；summary.silent_drop_total 44→**35**
  （−9 = 002 image −2 + 003 −6 + 004 −1；裁决预估 41–42 系只算
  image 净缺 3，实际按逐类型短缺合计）；element_count_total 合计
  1486→1495（+9）。
- figure_caption_* 零变化：PDF 侧不构建 image→caption 关联
  （契约 §3 仅 DOCX image@P↔caption@P+1），裁决关注的 004 caption
  GT=3 未受影响（既无正向收益也无误匹配）。
- devset_status=incomplete（pilot baseline，不代表项目总体准确率）。

**5 项边界声明（裁决原文确认）**：
1. 002-PDF −1：封面 logo 与 swoosh 艺术空间接近（gap <15pt），聚类识别
   为 1 个矢量图（GT 标注为 2）；标注口径非对称（封面分 2/封底不分），
   确定性规则无法复现，如实报告。
2. 003-PDF −2：p5/p7 灯泡图标与人环水印重叠，聚类识别为单图（GT 标注
   双图）；颜色子聚类可分离但会导致 002-PDF 超计（trade-off）。
3. 新增矢量图 image 可能改变 figure_caption_* relation 匹配——本批
   实测零变化（PDF 无 image→caption 关联构建），边界关闭。
4. 已知风险：曲线装饰物（波浪线/花边）可能误报为矢量图。当前 devset
   未出现，未来需扩展过滤规则（如 aspect ratio / curve 数量阈值）。
5. 已知限制：003-PDF 全页背景样板导致矢量图 bbox 扩大至整页，定位精度
   有限；计数不受影响。
   附注（实现期补充）：pdfplumber 将多段折线路径归类为 curve，本 devset
   表格均为单段线（实证 0 curves），其他语料的多段线表格存在误报可能。

## 四十九、批次 15 封口裁决记录（Stage-7-Batch-15-Closed，2026-08-31）

**裁决结论**（会话 cf170a6f，GPT 5.6 Sol）：
- 执行验收全部通过：实现 ✓（聚类函数/镜像发射/异常警告）；8 项测试 ✓；
  全量回归 5163 ✓（零回归）；修复效果精确达标（002 4/5、003 7/9、
  004 2/2，image 短缺 12→3）；devset 归因 PASS（其余 7 文档零漂移、
  MVP 两文档零漂移、silent_drop_total 44→35 −9 优于预估 −3 且归因
  追认、figure_caption_* 零变化边界关闭）；Must-not-change 确认
  （evaluator_version 1.10 / report_version 1.3）；路径偏差 4 项
  全部追认（Element dataclass／根 ADOPTION.md／一次性脚本不提交／
  curve bbox 锚点 hull 发现）；5 项边界 + 附注文档化 ✓。
- **归档编号：Stage-7-Batch-15-Closed。**
- **合并推送授权：通过**（ff-only 合并
  integration/stage7-batch15-pdf-vector-image 并推送 origin/main，
  立即执行，HEAD=01eaed8 或分支最新提交）。

**Stage 7 成果清单（裁决总结）**：7 批次全部完成——轨道 A 批次 9/10
（figure_caption_pairs 解锁，各 1.0/1.0/1.0）；轨道 B 批次 11/12/13
（heading_order_*、table_caption_* 指标族、真实语料 devset 2→10）；
修复批次 14（w:sdt 欠提取）/15（PDF 矢量图）。devset 2→10 文档、
annotation v1.0→v1.1、EVALUATOR_VERSION 1.8→1.10、
silent_drop 51→35（−31%）、测试 5147→5163（+16）。

**待决事项（裁决请求下次回复明确）**：Stage 8（新特性开发，
候选 B/C/D 归 backlog）vs 继续 Stage 7 微调（批次 16=候选 B
多栏题注碎字符）。候选 B（004-PDF caption −100%，多栏提取失败，
复杂度高）/ C（002-PDF 表单域标签误判 heading +246%）/ D（001-PDF
跨页表格拆分 table +300%）均为低优先级、各影响 1 文档。

**会话运行注记**：本段出现服务端配额限制（错误 18364，每 3 小时
88 次请求上限，耗尽后需等 ~80 分钟）；另旧 tab 经 cdp/network 调用后
出现编辑器 React 状态失同步（insertText/fill 均不触发按钮变形），
close_session 后新开 tab 恢复。后续与 GPT 交互需注意配额节奏与
tab 污染规避（避免在同 tab 混用 cdp/network 与发送序列）。

## 五十、Stage 8 启动裁决记录（Stage 7 封存 + 批次 16 开工许可，2026-08-31）

**前置运维事实**：批次 15 封口确认 + Stage 7/8 决策回复首次发送时撞
服务端配额（错误 18364），经 `/backend-api/conversation/{id}` API 直读
核实**服务端未收到该消息**（对话最后一条 user 消息仍为批次 15 封口
汇报）——配额拒绝发生在请求层，整条消息未落库。配额恢复后在新 tab
重发（760 字符，含运维注记披露重发事实），GPT 已收到并裁决。

**裁决结论**（会话 cf170a6f，GPT 5.6 Sol）：

1. **批次 15 封口确认 ✓**：合并推送 main a85eeb7 → 52b8eb6 验证通过；
   commits 01eaed8 / 52b8eb6 核对无误；归档编号 Stage-7-Batch-15-Closed。
2. **Stage 7 正式封存**（批次 9–15，7 批次）：devset 2→10、annotation
   v1.0→v1.1、EVALUATOR_VERSION 1.8→1.10、silent_drop_total 51→35
   （−31%）、测试 5147→5163、ADOPTION.md §三十八–§四十九。
3. **Stage 7/8 决策：进入 Stage 8（新特性开发）**。候选 B/C/D 与
   w:tc 内 sdt 全部归 backlog，Stage 8 期间不动。
4. **GitHub Issues #4 / #5 立即关闭**：#4 引用 Stage-7-Batch-12-Closed
   （批次 12 完成）、#5 引用 Stage-7-Batch-13-Closed（批次 13 完成）。
   **已执行**：均以 completed 关闭并附评论（issuecomment-5473175405 /
   issuecomment-5473175772）。
5. **Backlog 文档化**：4 项已知限制（B/C/D/w:tc）已记入
   `docs/BACKLOG.md`（本批提交）。
6. **Stage 8 目标：生产化与扩展性**——性能优化、可观测性、扩展性、
   部署准备。封口标准（Stage 8 整体）：100 文档 <10min（8 核单机）、
   结构化日志 + 进度 + 错误汇总、≥1 外部 parser 插件示例、Docker +
   CI/CD、生产部署与 API 文档。
7. **批次 16（批量处理与并行化）开工许可已授予**：
   - `app.cli batch-parse`（目录/glob 输入、每文档 1 JSON + summary
     汇总、多进程池、tqdm 进度条）
   - `evaluation.cli run` 并行化（报告格式不变，per-doc 排序）
   - 错误隔离（单文档失败不中断）
   - 验收：10 文档并行 vs 顺序加速比 >2×（8 核）；并行结果排序后与
     顺序逐字节一致；全量回归通过
   - **步骤 1（设计决策，需汇报后裁决）**：技术方案 A
     （multiprocessing.Pool）vs B（ProcessPoolExecutor）+ 理由；CLI
     接口完整设计；进度条策略；边界声明（小文档阈值/内存/错误处理）

**执行记录**：docs/BACKLOG.md 新建；issues #4/#5 关闭；本节归档。
步骤 1 设计调查随后启动。

**GPT 前端提示**：镜像站提示"对话轮数较多，建议创建新聊天"——若后续
对话异常频发，考虑新会话并自包含简报（携带 ADOPTION.md 台账指针）。

## 五十一、批次 16 执行记录（批量处理与并行化，Option A，2026-08-31）

**裁决（步骤 1，会话 cf170a6f）**：全部设计决策通过——Option A
（multiprocessing.Pool.imap_unordered）；workers 默认
min(cpu_count(), 8)；tqdm 可选导入降级；8 项边界全追认；加速比验收
调整为 ≥2×（8 核，devset 10 文档）；附加要求：BACKLOG 记 segfault
限制、README 记可选依赖、CLAUDE.md 增并行化章节、新增
scripts/verify_batch16_parallel_consistency.py。

**实现**（分支 integration/stage8-batch16-batch-parse）：
1. `app/batch.py`（新）：模块级 worker `parse_one_file((src, out_dir,
   parser_name, max_chars))` → 小 dict（file/success/elements/chunks/
   warnings(码表)/error_code/error_message/seconds）；worker 内自写
   JSON；`batch_parse_files` 父进程侧 stem 冲突检测（后者记
   stem_collision 不覆盖）；小批次（<3）或 workers=1 顺序路径；
   summary.json（total/success/failed/workers/wall_time_seconds/errors）；
   进度条 tqdm 可选（未装或非 TTY → 每文档一行 stderr）。
2. `app/cli.py`：`batch-parse` 子命令（目录递归 pdf/docx/md、glob、
   单文件三态；退出码 0 全成/1 有败/2 用法）。
3. `evaluation/cli.py` + `runner.py`：`run --workers N`（默认 1）；
   >1 且 ≥3 文档走 Pool.imap（保序），auto 未注册类型父进程合成失败
   不派发；per_doc 按 manifest 原序装配；expected_failures 保持顺序。

**实现期发现的契约偏差（GPT 示例 vs 实际，按"契约优先"处理）**：
1. 示例用 click——项目实际 argparse（parse/validate 同款风格）。
2. 示例 `process_single(src, parser=...)`——实际签名
   `(input, output, *, parser_name, max_chars, write_json)`。
3. 示例 summary.wall_time_seconds=sum(各文档 seconds)——改为父进程
   墙钟（并行加速比据此才真实；逐文档 seconds 仍在结果 dict 保留）。
4. 示例 error_code=type(e).__name__——改用 pipeline 结构化
   ErrorRecord.code（file_not_found 等，与单文档 CLI 错误码一致）。
5. 示例全部文件走单一 parser_name——实测 fallback parser 不支持
   .md（仅 pdf/docx），批模式按扩展名路由 .md → markdown
   （effective_parser_for；仅 fallback 时路由，显式指定不覆盖）。
6. summary.workers 记录实际生效值（顺序路径记 1）。
7. runner 并行实现为 run_evaluation 增 workers 参数 + 保序 imap
   （非独立 run_evaluation_parallel 函数）；workers=1 路径与原顺序
   代码同构（相同 _process_one 调用序 + 相同装配），报告逐字节不变。

**测试**：`tests/test_batch_parse.py` 12 项——裁决 3.1 六项（10 文档
并行批、顺序并行输出逐字节一致、错误隔离（缺失文件不中断批）、stem
冲突不覆盖、小批次顺序路径、summary 格式）+ default_workers 上界 +
md 路由 + CLI 三态冒烟（rc 0/1/2）+ evaluation 并行报告一致性
（metrics/parser_used/summary/devset 相同，wall_time 除外）。
全量回归 **5175 passed**（5163 + 12，零回归）。

**性能基准（devset 10 文档，手动，Windows 11 / 14 核）**：
- workers=1：wall 5485 ms（含解释器启动与导入）
- workers=8：wall 2614 ms → **加速比 2.10×（≥2× 验收线 PASS）**
- workers=4：wall 2373 ms → 2.31×（spawn+导入开销在小 devset 上
  显著，4 进程反而最优；批量更大时 8 优势应扩大）
- per-doc total 之和：seq 4.45 s vs par 3.97 s（含轻微争用）
- 报告：outputs/b16-bench-{seq,par}.json（gitignored）

**一致性验证**：`scripts/verify_batch16_parallel_consistency.py`
对 b16-bench 两份报告 rc=0——per_doc 按 doc_id 排序后逐字节相同
（wall_time_seconds 除外）；summary/devset/expected_failures/
provenance（剔 run_timestamp_iso/git 状态）一致。
report_version 1.3 与 EVALUATOR_VERSION 1.10 不变（裁决确认）。

**文档更新**：README 可选依赖节（tqdm）；CLAUDE.md 范围节（多进程
移出"不做"清单）+ 并行化章节 + 常用命令；docs/BACKLOG.md 第 5 项
（segfault 限制）。

## 五十二、批次 16 封口裁决记录（Stage-8-Batch-16-Closed，2026-08-31）

**裁决结论**（会话 cf170a6f，GPT 5.6 Sol）：

1. **执行验收全部通过 ✓**：实现（app/batch.py worker+批函数+进度降级、
   CLI 三态+退出码、evaluation --workers 保序装配+EF 顺序）；测试
   12 项 + 全量回归 5175；性能基准 2.10×（≥2× 验收线）；一致性
   验证 rc=0（report_version 1.3 / EVALUATOR_VERSION 1.10 不变）；
   文档四处更新。
2. **7 项契约偏差全部追认 ✓**（各附追认理由）：argparse（项目惯例）、
   process_single 实签名（示例为伪代码）、wall_time=墙钟（"工程正确性
   优于裁决示例"）、error_code=ErrorRecord.code（与单文档 CLI 一致）、
   md 路由（fallback 实测不支持 .md）、workers 记生效值（可判断是否
   启用并行）、run_evaluation 增参非独立函数（workers=1 同构）。
3. **归档编号：Stage-8-Batch-16-Closed。**
4. **合并推送授权：通过**（ff-only 合并
   integration/stage8-batch16-batch-parse @ 94d2e12 并推送
   origin/main，立即执行）。
5. **下一批次指定：批次 17（结构化日志与可观测性）**——JSON Lines
   结构化日志；方案 A（Python logging + 自定义 JSON formatter，
   零新增依赖，裁决推荐）vs B（structlog，新增依赖须用户批准）；
   关键事件 batch_start/file_complete/file_error/batch_complete/
   warnings；CLI --log-file 与 --verbose；进度条与日志共存；
   默认向后兼容；步骤 1 设计决策（方案选择/事件 schema/CLI 接口/
   共存细节/边界声明）需汇报后裁决。
   验收标准：JSON Lines 格式、INFO/WARNING/ERROR、关键事件全覆盖、
   CLI 参数、共存不冲突、向后兼容、测试覆盖、文档更新、全量回归。

**执行记录**：本节归档后随分支一并合并推送（封口记录提交在合并授权
范围内）。

## 五十三、批次 17 执行记录（结构化日志，Option A，2026-08-31）

**设计裁决**（会话 cf170a6f，GPT 5.6 Sol，全票）：方案 A（Python logging +
自定义 JSONFormatter，零新增依赖）；事件 schema 见下；CLI --log-file +
--verbose；8 条边界（默认零输出变化/JSON Lines/多 handler/append/verbose
交错提示/worker 隔离/轮转留后/traceback 首版不截断）。

**实现**：

- `app/jsonlog.py`（新建）：`JSONFormatter`（record.msg → event，extra=
  字段经 record.__dict__ 扫描顶层展开，排除 LogRecord 保留属性）+
  `setup_logger`（log_file/verbose 可同开，两者皆无挂 NullHandler）。
- `app/batch.py`：worker 返回 dict 增 parser/traceback 字段；
  batch_parse_files 增 log_file/verbose 参数；事件 batch_start
  {workers,file_count,parser,max_chars} → 碰撞 file_error（traceback=null）
  → 流式逐结果 file_complete{file,parser,elements,chunks,seconds} /
  逐 warning 码 file_warning{file,warning_code} / 失败
  file_error{file,parser,error_code,error_message,traceback} →
  batch_complete{success,failed,wall_time_seconds}。
- `evaluation/runner.py`：run_evaluation 增 log_file/verbose/
  manifest_label 参数；eval_start{parser,doc_count,manifest_label} →
  装配循环内 doc_complete{doc_id,source_type,parser_used,seconds} /
  doc_error{doc_id,error_code,error_message} → eval_complete{success,
  failed,wall_time_seconds}。
- CLI：app/cli.py batch-parse 与 evaluation/cli.py run 增
  --log-file（help 注明建议 outputs/，gitignored）与 --verbose。
- `scripts/verify_batch17_log_completeness.py`（新建）：首尾事件 +
  file_complete+file_error==file_count（eval 同构）校验，rc 0/1/2。

**契约偏差（待追认）**：

1. 错误事件文本字段名 `error_message` 而非 `message`——"message" 是
   LogRecord 保留属性，`extra={"message":...}` 直接 KeyError（冒烟
   实证），与 batch result dict 键名一致。
2. JSONFormatter 扫描 `record.__dict__` 而非 GPT 示例的
   `record.extra` dict——logging 的 extra= 实际机制是设置 record
   属性，不存在 record.extra。
3. timestamp 用 `record.created` 而非 format 时 `time.time()`——
   记录事件真实发生时间。
4. NullHandler——GPT 蓝图未提，但无 handler 时 logging lastResort
   会把 WARNING+ 泄漏到 stderr，违反"默认零输出变化"（设计阶段已
   预申报，含在 8 边界内）。
5. file 事件在结果到达时流式发射（并行下非提交顺序）——非"全部
   完成后统一发射"，便于实时观测。
6. eval 事件增 `manifest_label`（CLI 传 manifest 路径）——Manifest
   对象无 path 字段，事件需可辨认清单来源。

**测试**：`tests/test_jsonlog.py` 12 项（formatter 格式/中文往返/双
handler/NullHandler 静默 capfd 实证/batch 事件完整性/碰撞 file_error/
traceback 捕获（RuntimeError 冒烟 monkeypatch）/file_not_found traceback=
null/file_warning 逐码/append 两轮/eval 事件含 doc_error（fallback 拒
.md → unsupported_type 真实路径）/doc_complete 字段/CLI 透传）。

**devset 真实日志验证**：batch 16 文件（13 成功 + 3 stem_collision）
与 eval 10 文档（10 成功）各生成 JSONL，verify 脚本均 rc=0。

## 五十四、批次 17 封口裁决记录（Stage-8-Batch-17-Closed，2026-08-31）

**裁决结论**（会话 cf170a6f，GPT 5.6 Sol）：

1. **执行验收全部通过 ✓**：实现（jsonlog.py + batch 5 事件流式发射 +
   evaluation 4 事件 + CLI 双参数 + verify 脚本）；验收对照 14/14；
   测试 12 项 + 全量回归 5187（5175+12 零回归）；devset 真实日志
   （batch 16 文件 + eval 10 文档，verify 均 rc=0）；文档三处。
2. **6 项契约偏差全部追认 ✓**（各附理由）：error_message（LogRecord
   保留属性 KeyError 冒烟实证）、record.__dict__ 扫描（extra= 实际
   机制）、record.created（事件真实时间）、NullHandler（边界 2 预
   申报）、流式发射（JSON Lines 理念）、manifest_label（Manifest
   无 path 字段）。
3. **归档编号：Stage-8-Batch-17-Closed。**
4. **合并推送授权：通过**（ff-only 合并
   integration/stage8-batch17-structured-logging @ 6b375c5 并推送
   origin/main，立即执行）。
5. **下一批次指定：批次 18（Parser 插件化与扩展接口）**——Parser
   抽象接口（Protocol/ABC + name/supported_extensions/priority 元
   数据）、注册表（register/get/discover + 扩展名自动发现 + 优先级
   排序）、现有 parser 迁移（fallback/markdown/kreuzberg）、外部
   插件示例（推荐 Markdown Enhanced：YAML frontmatter → metadata）、
   CLI（list-parsers / --parser 支持插件名 / 自动发现）。
   步骤 1 设计决策（方案 A Protocol+装饰器 vs B ABC+显式注册 / 接口
   设计 / 注册表 API / 插件示例功能清单 / CLI 命令 / 边界声明）需
   汇报后裁决；步骤 2–5 待裁决后执行。

**执行记录**：本节归档后随分支一并合并推送（封口记录提交在合并授权
范围内）。

## 五十五、批次 18 执行记录（Parser 插件化与扩展接口，Option B，2026-08-31）

**会话切换**：旧对话 cf170a6f 已 25 轮，消息 POST 连续 4 次上游 502
（网络抓包实证 POST /backend-api/f/conversation → 502，整条不落库，
非配额 18364），按既有运维惯例开新对话 6a952dc9 发自包含简报。
GPT 确认新对话继续担任裁决者，ADOPTION.md 保持唯一权威台账。

**设计裁决**（新对话首条，全部通过）：方案 B（保留 Parser ABC + 注册表，
register 装饰器兼容）；契约不变（parse(path, source_hash) -> Document、
schema 0.1.0、新增 supported_extensions=() 与 priority=100）；
registry 三 API；插件内置注册定位（"随项目分发的参考/增强插件"）；
优先级 markdown_enhanced=5 < markdown=20，显式 --parser 永远覆盖，
平局先注册者胜 + warning；CLI 6(a)（默认 fallback 零变化 + 显式 auto）；
frontmatter 零依赖受限解析（仅扁平 key: scalar，嵌套/列表 warning 跳过，
完整 YAML 列 backlog）；evaluation 不改。额外要求 7 类测试。

**实现**（分支 integration/stage8-batch18-parser-plugins，基于 0b13589）：

- `app/parsers/base.py`：Parser ABC 增 supported_extensions / priority 类属性
- `app/parser_registry.py`（新建）：register（装饰器兼容，重名/缺名
  ValueError）/ get_parser（inspect 按构造签名传 image_output_dir，未知名
  ValueError 语义兼容）/ discover_parser（返回**名称**字符串——pipeline/
  CLI 流转以名称为准，与蓝图"返回 Parser 实例"偏差已申报；无候选
  ValueError；平局 UserWarning）/ list_parsers（按 priority 排序）；内置
  6 个导入时显式注册，插件经类上 @register 在其后 import 自注册
- 6 内置 parser 补元数据：fallback(.pdf/.docx,10)、kreuzberg(.pdf/.docx,50)、
  markdown(.md/.markdown,20)、html(.html/.htm,100)、text(.txt/.text,100)、
  ipynb(.ipynb,100)
- `app/parsers/plugins/markdown_enhanced.py`（新建，@register，priority=5）：
  frontmatter 受限解析（`_split_frontmatter` 首尾 --- 闭合才认；
  `_parse_frontmatter` 扁平 key: scalar，一层引号剥除，标量保持字符串不猜
  类型；嵌套/列表/映射/空值 → frontmatter_value_skipped /
  frontmatter_line_skipped warning 跳过）→ 顶层合并 Document.metadata；
  GFM 任务列表（- [ ]/- [x] → metadata.task_item/checked，content 去标记）；
  body 解析复用 MarkdownParser._parse_text（私有方法同仓复用）
- `app/pipeline.py`：get_parser 委托注册表（签名与错误语义不变，调用方零改动）
- `app/batch.py`：effective_parser_for 增 auto 分支（discover；无候选回落
  fallback → worker 侧结构化 unsupported_type，不炸批）
- `app/cli.py`：parse/batch-parse --parser choices 动态取自注册表 + auto；
  parse 处理器 auto → discover（ValueError → structured unsupported_type rc1）；
  新增 list-parsers 子命令（name/priority/extensions/version 表格）
- evaluation 未动（AUTO_PARSER_BY_SOURCE_TYPE 为 source_type 语义）

**契约偏差（待追认）**：

1. discover_parser 返回名称字符串而非 Parser 实例（蓝图签名）——
   pipeline/CLI/batch 全链路以 parser_name 流转，返回实例还需二次取
   .name 且 image_output_dir 无从传递；测试断言也以名称为准。
2. 插件注册顺序实现：内置 6 个显式 register 后 import 插件模块（其
   @register 在 import 时自注册）——首版曾显式 register(MarkdownEnhancedParser)
   与类上装饰器双重注册冲突（冒烟实证 ValueError 重名），改为 import 即
   注册，恰好就是外部插件的接入样态。
3. frontmatter 标量值一律保持字符串（"42" 不转 int）——受限解析不猜类型，
   避免引入 YAML 类型规则。

**测试**：`tests/test_parser_registry.py` 20 项，覆盖裁决 7 类要求
（自动发现含无候选 ValueError / 优先级平局先注册者+UserWarning / 重名与
缺名注册 ValueError / CLI auto 解析 md→enhanced 与不支持扩展 rc1 / 默认
fallback 不变（.md 默认仍 unsupported_type rc1）/ frontmatter 嵌套列表
降级 warning + 未闭合不误认 / 外部 @register 显式注册全可见）+ 注册表基础
（元数据/未知名/image_output_dir/pipeline 委托）+ batch auto 路由 +
list-parsers CLI + 任务列表元数据。

**回归**：5207 passed（5187 + 20，零回归）。

**冒烟记录**：list-parsers 7 行表格；parse --parser auto .md →
markdown_enhanced（frontmatter title/author 入 metadata，任务项
checked True/False）；默认不带 --parser .md → structured
unsupported_type（行为与批次 17 前一致）；batch-parse --parser auto 1/1。

## 五十六、批次 18 封口裁决记录（Stage-8-Batch-18-Closed，2026-08-31）

裁决对话 6a952dc9（完成报告因镜像站落库延迟首查未见，重试一条；
GPT 对两条分别回复：完整封口裁决 + "裁决不变"确认，二者一致）。

**裁决：批次 18 予以封口，三项契约偏差全部追认。**

1. `discover_parser()` 返回 parser 名称（str）：追认——与现有按名称
   流转、由 `get_parser()` 注入构造参数的链路一致；要求在接口文档中
   明确返回值为 str（本提交已在 docstring 与 README §3.5 落实）。
2. 插件以模块导入触发 `@register`：追认——注册必须恰好一次，禁止再
   显式重复注册同一类（与冒烟实证的双重注册 ValueError 一致）。
3. Frontmatter 标量一律保留为字符串：追认——受限解析器不进行 YAML
   类型猜测是正确边界。

**归档标记**：`Stage-8-Batch-18-Closed`（裁决原文写"登记于 §五十五"，
按本台账一节一记录惯例登记为 §五十六，编号偏差待追认）。

**推送授权与执行**（GPT 给定四步命令，逐字执行）：

```
git fetch origin refs/heads/main:refs/remotes/origin/main   → OK
git merge-base --is-ancestor origin/main 81bcaa3            → OK（0 退出）
git push origin 81bcaa3:refs/heads/main                     → 0b13589..81bcaa3
git ls-remote origin refs/heads/main                        → 81bcaa3e842a...d60e
```

远端 SHA 与授权 SHA 完全一致，无 force。指示线 worktree 本地 main
已同步 ff 至 81bcaa3。封口记录提交（本条）在授权推送 SHA 之后，
随下一批次合并推送。

**裁决环境说明（GPT 自述）**：当前裁决环境未挂载工作树，无法独立复跑
5207 项或实际代推；封口基于提交的实现、测试与冒烟证据。

**下一批次指定：批次 19——显式外部插件加载。**
范围（GPT 划定）：先提交步骤 1 设计决策；可重复的 `--plugin MODULE`
外部模块加载、加载时机与动态 CLI 校验、导入/注册失败的错误契约与
JSONL 记录、冲突处理及端到端测试。保持"显式加载"——不引入
entry_points 自动扫描、YAML 扩展或内容嗅探。

## 五十七、批次 19 执行记录（显式外部插件加载，2026-08-31）

设计裁决（会话 6a952dc9）：D1–D3、D5、D8、D9 通过；D4、D6 附条件通过；
D7"初始化异常直接冒泡"不通过，须受控失败通道；另补 3 项测试要求
（顶层普通 ValueError 映射 / worker 侧失败结构化返回无挂起无原始
traceback / auto 与显式外部名在插件加载后才校验）——全部落实。

**实现**：

- `app/parser_registry.py`：新增 `ParserRegistrationError(ValueError)`
  （register 缺名/重名专用，错误文本不变，既有 ValueError 断言向后兼容）
  与 `registered_names()`（快照，供加载器 diff）
- `app/plugin_loader.py`（新）：`load_plugins(modules)` 按序 dotted 导入，
  注册表快照前后 diff 出 `parsers_added`；同模块重复 = importlib 缓存
  幂等；`PluginLoadError`（code/plugin/error_type/error_message，
  `to_dict()` 默认不含 traceback）；映射：ParserRegistrationError →
  `plugin_register_failed`，其他导入期异常 → `plugin_import_failed`
- `app/batch.py`：`batch_parse_files` 增 `plugins` 参数——父进程池创建前
  加载（fail-fast 抛 PluginLoadError，不启动批、不写 summary.json）；
  并行路径 `Pool(initializer=_worker_init_plugins, initargs=(modules, queue))`，
  worker 捕获 PluginLoadError 后经 multiprocessing.Queue **恰一次**回报
  初始化状态（initializer 永不抛异常，避免重生循环/挂起），父进程在
  任何文件任务派发前收取全部回报（超时 120s → 受控
  `plugin_init_report_timeout`），not ok → 日志 plugin_load_failed +
  受控上抛（with 语句退出即 terminate+join 回收池）；`parse_one_file`
  增防御背板（_WORKER_PLUGIN_ERROR 非空时直接结构化失败）；
  `batch_start` 增 `plugins` 字段；新增 `plugin_loaded` / `plugin_load_failed`
  JSONL 事件（沿批次 17 logger，error 字段名 error_message）
- `app/cli.py`：`--plugin MODULE`（append 可重复）挂 parse / batch-parse /
  list-parsers；validate 与 evaluation.cli 不参与；`--parser` 去掉 argparse
  静态 choices，改为**插件加载后**按注册表动态校验（auto 唯一保留名），
  未知名 → 结构化 `unknown_parser` rc 1（裁决 D6 接受 rc 2→1 变更）；
  parse 侧文件存在性检查先于插件加载（仅错误优先级细节，校验时序符合
  裁决"插件加载先于 parser 名称校验"）；batch-parse 捕获 PluginLoadError
  → 结构化 rc 1

**契约偏差与边界（待追认）**：

1. 新增错误码 `plugin_init_report_timeout`（裁决契约只列了两种加载失败
   码）：回报超时是 D7 受控通道的必要兜底路径，无法用既有两码诚实表达。
2. `plugin_loaded` 事件的 `parsers_added` 在 CLI 流程下为空表：CLI 校验
   阶段已在父进程完成注册，batch 层重放加载命中模块缓存——事件语义为
   "batch 路径加载成功"，纯 API 调用（无 CLI 预加载）时为实际新增名单。
3. **source_type 封闭枚举**：`schemas/document.schema.json` 的 source_type
   为封闭枚举（pdf/docx/markdown/html/text/ipynb），外部插件解析新格式
   只能复用枚举内取值（测试插件 .myx 复用 "text"）；开放枚举需 Schema
   变更，列 docs/BACKLOG.md #7 待裁决。
4. batch-parse 目录递归扫描后缀固定 .pdf/.docx/.md 不随插件扩展：
   插件格式经单文件或 glob 显式传入（glob 路径既有行为本就不做后缀
   过滤）。裁决未涉及此点，按最小改动处理并声明。
5. 父进程加载失败的批量命令不写 summary.json（批未启动）；此前
   batch-parse 的 rc 1 伴有 summary，本路径没有——命令级失败语义。

**测试**：`tests/test_plugin_loader.py` 26 项，覆盖裁决全部要求 + 补充 3
项：加载基础（parsers_added / 幂等 / fail-fast 后续模块不加载 / 顺序即
先注册者）/ 错误契约四种（ModuleNotFound / SyntaxError / 顶层 ValueError /
重名 fallback）/ to_dict 无 traceback 默认 / CLI e2e（显式外部名 / auto
路由 / 加载失败与冲突结构化 / unknown_parser / 外部名未加载插件时同样
unknown_parser / **--plugin 失败优先于 unknown_parser（加载先于校验）** /
auto 无插件回归）/ list-parsers 双路径 / 批量（父失败无池无 summary /
顺序成功 / 并行成功 + JSONL plugin_loaded + batch_start.plugins）/
**真实跨进程 worker 初始化失败**（sentinel 文件控制模块体行为：父缓存
命中成功、worker 新进程导入失败 → 受控 rc 1、无 summary、结构化 JSON
无 traceback 字段）/ worker 函数单元（initializer 捕获回报 / 成功回报 /
背板）/ validate 无 --plugin。

**回归**：5233 passed（5207 + 26，零回归）。

**冒烟记录**（真实子进程，PYTHONPATH 注入 smoke_plug）：list-parsers
--plugin 显示 smoke_ext 行（8 个 parser）；parse --plugin --parser
smoke_ext rc 0 且 validate 通过 Schema；parse --plugin --parser auto rc 0
路由 smoke_ext；batch-parse --plugin --workers 2 3/3 成功，JSONL 含
plugin_loaded + batch_start.plugins=["smoke_plug"]；--plugin 不存在模块
→ 结构化 plugin_import_failed rc 1、无半成品 JSON；--parser 拼写错 →
结构化 unknown_parser rc 1。

### 五十七（续）、批次 19 封口修正轮（2026-08-31）

首份完成报告裁决：暂不封口，需修正偏差 2 后重报。其余 4 项偏差中
plugin_init_report_timeout / source_type 封闭枚举 / 目录扫描后缀固定 /
父失败不写 summary 均已追认，另附条件：

**修正内容**：

1. `plugin_loaded.parsers_added` 不得恒为空——`app/plugin_loader.py` 增
   `_FIRST_LOAD` 进程级备忘：`load_plugins` 始终返回该模块**首次**加载的
   真实注册增量（命中备忘不重复导入/注册）；CLI 校验阶段预加载后，批量
   路径发事件即携带真实名单。空表仅限真实幂等情形（外部途径预导入 /
   模块未注册 parser / 重复指定——重复 spec 只发一次命令级事件，
   `batch_start.plugins` 仍保留原始输入列表）。
2. 回报超时事件补字段：`plugin_load_failed` 携带
   `error_code=plugin_init_report_timeout` + `expected_workers` /
   `received_reports`；120 秒固定上限写入 README / CLAUDE.md。
3. 外部插件开发指南（README §3.5）明确：新格式 `source_type` 暂须映射
   至既有语义类型（开放枚举列 BACKLOG #7 待裁决）。

**测试增量**：`test_load_plugins_repeat_module_returns_first_increment`
（重写幂等语义：二次返回首次增量且注册表不增长）、
`test_batch_duplicate_plugin_spec_single_event`（重复 spec 单事件 +
batch_start.plugins 保留原始列表）、
`test_batch_plugin_registering_nothing_empty_added`（无注册插件真实
空表）、`test_batch_parallel_with_plugins_jsonl` 断言改为事件含真实
parser 名单（裁决要求的 JSONL 端到端断言）。共 28 项。

**回归**：5235 passed（5233 + 2 净增，零回归）。

## 五十八、批次 19 封口裁决记录（Stage-8-Batch-19-Closed，2026-09-01）

**裁决对话变更**：旧对话 6a952dc9（ChatGPT 5.6 Terra 创建）经实测不支持
切换 GPT-5.6 Sol（模型菜单 Sol 项 aria-disabled + 站点提示"当前聊天不支持
切换至该模型，如需使用请创建新聊天"；React onSelect 直调亦被禁用短路）。
按用户指示新建裁决对话 6a957e64-fbac-83ea-af7d-64efe4924af3
（GPT-5.6 Sol，思考程度"高"——该模型仅有 中/高 两档，"极高"为
Terra/Work 独有），修正后完成报告于 2026-08-31 21:15 首条发送（含角色
简报 + 项目背景 + 完整报告）。

**裁决：Batch 19 = SEALED，授权 ff-only 推送。**

三个阻断点关闭确认：

1. `plugin_loaded.parsers_added` 代表首次真实注册增量，CLI 预加载与
   batch 重放经进程级备忘保持同一语义；
2. 重复 `--plugin` 正确分层（plugin_loaded 单事件 + batch_start.plugins
   保留原始输入），契约自洽；
3. worker 初始化失败受控通道（D7）：initializer 不抛异常、派发前收齐
   回报、超时 `plugin_init_report_timeout` 带 expected_workers /
   received_reports；真实跨进程失败路径已覆盖，标准 JSON 不泄漏
   traceback。

120 秒 timeout 未自动化覆盖：接受继续留 BACKLOG #9，不作本批阻断项。
GPT 另核对公开远端 main 仍为批次 18 状态、7033dc5 尚未公开——与
"待推送"状态一致。

**推送授权与执行**（GPT 给定命令序列，逐字执行于指示线 main worktree）：

```
git fetch origin                                → OK（首试 502，重试成功）
EXPECTED=$(git rev-parse integration/stage8-batch19-plugin-loading)
                                                → 7033dc587556448c6a8a5a64a601337e9b2d940d（前 7 位 7033dc5 ✓）
git merge-base --is-ancestor origin/main $EXPECTED → OK（0 退出）
git merge --ff-only $EXPECTED                   → 81bcaa3..7033dc5，无 merge commit
git push origin main                            → 81bcaa3..7033dc5
git ls-remote origin refs/heads/main            → remote == expected
test "$REMOTE" = "$EXPECTED"                    → Batch 19 push verified
```

远端 SHA 与授权 SHA 完全一致，无 force。推送回执（main remote SHA +
Batch 19 push verified）已发裁决对话。封口记录提交（本条）在授权推送
SHA 之后，随下一批次合并推送。

**下一批次指定：批次 20——外部插件"全新格式"契约：解开 source_type
封闭枚举，同时保持 locator 强校验。**

裁决边界（逐条）：

- 目标**不是** `"source_type": {"type": "string"}` 一放了之（未知格式
  locator 将失去约束，不接受）；
- 历史 Schema 版本语义不得回写修改；新 writer 版本按既有
  schema-version policy 演进；
- 外部 parser 可声明新 source_type，但必须同时声明/绑定合法
  **locator family**；
- locator 强校验主要由 family 驱动，未知 source_type 不得直接落入
  无约束对象；
- 内置 pdf/docx/markdown/html/text/ipynb 现有约束不得放宽；
- parser 声明的 source contract 与实际返回 Document 不一致时，给出
  稳定、结构化错误；
- 增加真正的新扩展名测试插件（如 `.myx`）：
  `--plugin → auto discovery → parse → chunk → schema validate → JSON`
  全链闭环，不再借用既有 source_type；
- BACKLOG #8（--plugin 文件路径）与 #9（120 秒真实 timeout 测试）
  不混入本批，继续留 backlog。

## 五十九、批次 20 封口裁决记录（Stage-8-Batch-20-Closed，2026-09-01）

裁决对话：6a957e64-fbac-83ea-af7d-64efe4924af3（GPT-5.6 Sol，思考程度
"高"）。批次 20 四相（A 声明契约 / B schema 0.6.0 / C 运行时契约检查 /
D .myx 全链测试）逐相送审：

- Phase A（ce0c476）与 Phase B（c9a3d57）先后 APPROVED；
- 相位时序偏差（B 报告送审前已先行实现 C）主动申报，裁决**接受不返工**
  （三 commit 相互独立、未越设计范围、可 bisect），但 Phase D 起恢复严格
  门禁：设计→裁决→实现→报告→下一阶段；
- Phase C（1e9dc49）与 Phase D（0431fb0）按严格门禁送审通过；
- Batch 20 = SEALED，授权 ff-only 推送。

**三项偏差追认**：

1. `source_types` 声明收窄为 str 或 str 元组（list 不接受）——实现期
   发现 list 会与"扩展名列表"语义混淆，收窄后 `register` 即时校验；
2. B→C 相位时序偏差（见上，接受不返工）；
3. Phase A 潜伏缺陷（`list_parsers` 对 str 声明逐字符拆分）在 Phase C
   期间发现，经 `declared_source_types()` 统一归一入口修复，GPT 追认为
   有效修复。

**关键成果**（对应 schema-version policy 0.6.0 行）：

```text
schema 0.6.0（SCHEMA_VERSION_CURRENT 唯一权威常量）
source_type 封闭枚举 → pattern ^[a-z][a-z0-9_]{0,31}$ 受控开放
0.1.0–0.5.0 守卫分支仍限内置六类型（历史不回写）
扩展类型 locator.family 必填 ∈ 封闭四值（family 集合仍封闭）
line_address → 新 $defs/line_address_locator；形状按 family 路由
parser 声明契约：source_types tuple + locator_family，全局类型→family 唯一绑定
运行时 parser_contract_mismatch（schema 校验后、写盘前；rc 1 不落盘）
.myx 外部插件全链验证（tests 专用，永不内置、不进 AUTO 映射）
```

**测试**：5329 passed（5235 + 94：Phase A 44 + B 37 + C 5 + D 8，零回归）。

**推送授权与执行**（GPT 给定五步序列，逐字执行于指示线 main worktree）：

```
git fetch origin                                → OK
EXPECTED=$(git rev-parse integration/stage8-batch20-sourcetype-extension)
                                                → 0431fb0e8823236574c5cb393813e525aa5471e0
git merge-base --is-ancestor origin/main $EXPECTED → OK（0 退出）
git merge --ff-only $EXPECTED                   → 7033dc5..0431fb0（31 files，+1487/-58）
git push origin main                            → OK
git ls-remote origin refs/heads/main            → remote == expected
test "$REMOTE" = "$EXPECTED"                    → Batch 20 push verified
```

远端 SHA 与授权 SHA 完全一致，无 force。推送回执已发裁决对话，GPT 回复
确认 Batch 20 正式进入 Stage 8 封存状态（2026-09-01）。封口记录提交（本
条）在授权推送 SHA 之后，随下一批次合并推送。

**下一批次指定：批次 21——Plugin Capability Manifest（插件能力描述与
发现契约）**：从"插件能加载、输出受控"推进到"插件能力可声明、可解释、
可确定选择"。**必须先提交 Step 1 Design Decision List，不直接实现**。

裁决要点（GPT 列出的重点裁决项）：

1. capability 是否独立抽象（独立 dataclass vs Parser 类属性继续扩展，
   是否进 registry 内部模型）；
2. input capability（extensions → parser candidate）与 output contract
   （source_type → schema 形状）是否保持分离（GPT 倾向保持分离，待确认）；
3. parser selection 是否确定性（priority 必要性、数值方向、相同
   priority 处理、silent fallback 是否允许）；
4. registry 是否继续保持受控通道；
5. 不破坏 Batch 19/20 已封口契约。

设计问题 D1–D6：D1 capability metadata 模型、D2 extensions 归属、
D3 auto parser 冲突策略、D4 list-parsers 输出契约（人类/JSON/向后兼容）、
D5 注册冲突错误归入既有 plugin_register_failed 还是新码、D6 不做清单
（目录扫描 / pip entry points / 网络插件市场 / 动态安装 / GUI 插件管理
——继续不做）。

**边界**：BACKLOG #7a（holdout 脚本 0.5.0 冻结）、#7b（family 集合
封闭为设计决定）、#8（--plugin 文件路径）、#9（120 秒 timeout 自动化）
均不混入批次 21。
