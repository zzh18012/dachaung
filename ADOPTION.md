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
| holdout-md-v1 | samples/private/holdout-md/ | 4 | e08b50ada20f577f（manifest 1.1） | setext 标题+thematic break / 嵌套引用 / 行内格式+转义 / 内嵌 HTML+自动链接 |
| holdout-html-v1 | samples/private/holdout-html/ | 4 | 5decd9940de62567（manifest 1.1） | blockquote+pre / dl+br / 注释与 script-style 排除（forbidden_markers 首次实际使用）/ thead-tbody-colspan |

注：holdout 冻结后因版本语义 PR 把 manifest_version 升到 1.1（纯版本声明变更，
内容与 expectations 未动），哈希随之更新为上表值。三份 dev manifest 同步升 1.1：
devset-md bce257755967e834、devset-html 82b0ec83d13f04f4、
devset-regressions 8e5ecd3e3e44d756。

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
