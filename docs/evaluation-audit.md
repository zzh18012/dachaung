# 评测管线审计报告（Round 8）

> 范围：`evaluation/*.py` + `tests/test_evaluation_*.py` + `tests/test_annotation_metrics.py`
> 基线 commit：`5f783fc`（272 pass / 9 skip）；审计后：`<本 commit>`（277 pass / 9 skip）
> 不变量：未触动 `evaluator_version`（仍为 `"1.1"`）与 `report_version`（仍为 `"1.1"`）

## 1. 已修复的真实 bug

### 1.1 `chunk_boundary_prf` 重复 marker 全部命中第 1 次出现

**文件**：`evaluation/annotation_metrics.py:117-130`（修复前）

**症状**：当标注里两个 anchor 用了相同的 `marker` 文本（例如两处都想标记 "the"），
两个 anchor 都调 `stream.find(marker)` —— 没有起点参数 —— 都返回 stream 中
**第 1 次出现**的位置。结果：

- 两个 anchor 的 `gt_position` 完全相同
- 一对一匹配约束下，至多命中 1 个
- 召回率被低估、且语义错误（标注者明确指了两个不同位置）

**修复**：维护 `search_from` 游标，每找到一个 marker 后推进到其末尾。
下一个 anchor 在剩余 stream 里找下一次出现。允许同一 marker 文本对应
不同 stream 位置；找不到时进 `missing_markers`。

```python
search_from = 0
for a in anchors:
    marker = a.get("marker", "")
    find_pos = stream.find(marker, search_from) if marker else -1
    if find_pos < 0:
        missing_markers.append(marker)
        continue
    ...
    search_from = find_pos + len(marker)
```

**回归测试**：
- `tests/test_annotation_metrics.py::test_chunk_boundary_repeated_marker_finds_distinct_positions`
- `tests/test_annotation_metrics.py::test_chunk_boundary_repeated_marker_after_position`
- `tests/test_annotation_metrics.py::test_chunk_boundary_repeated_marker_not_found_after_exhausted`

### 1.2 `_process_one` 失败时返回 `Path()` 而非 `None`

**文件**：`evaluation/runner.py:88, 96, 97`（修复前）

**症状**：函数返回类型签名是 `Path`，于是失败分支写 `image_dir or Path()`。
当 `image_dir` 为 `None`（document 为 None 时确实为 None），返回 `Path('.')`
即**当前工作目录**。下游 `run_evaluation` 调用：

```python
image_base_dir = image_dir if image_dir.is_dir() else None
```

`Path('.').is_dir()` 在评测进程的 cwd 里几乎总为 `True`，于是
`image_base_dir` 被设成 cwd。失败文档无图片所以 `_image_resource_ratio`
会先 short-circuit 在 `no_image_elements`，bug 在实践中无害，但：

- 类型契约错误（声称 `Path` 实际可能任何东西）
- 任何后续把 `image_base_dir` 当作真实图片根目录使用的代码路径都会
  误把 cwd 里的随机文件当图片
- 静默语义漂移，未来重构时容易爆雷

**修复**：把返回类型改成 `Path | None`，三个 return 都直接 `return image_dir`
（None 时不做 fallback）。`run_evaluation` 的调用点改成
`image_dir if (image_dir is not None and image_dir.is_dir()) else None`。

**回归测试**：
- `tests/test_evaluation_runner.py::test_process_one_returns_none_image_dir_on_failure`
- `tests/test_evaluation_runner.py::test_process_one_returns_path_image_dir_on_success`

## 2. 审计了但**不是 bug**的设计选择

### 2.1 `aggregate_summary` 不混合类型出"综合分数"

`report.py` 显式分四类聚合：counts（求和）、success_rates（rate）、
ratio_macro_averages（macro avg）、silent_drop_total（求和）。
`test_no_mixed_overall_score` 显式断言不存在混合分数。这是有意设计，
对齐 CLAUDE.md "不混合出'综合分数'"。

### 2.2 比例指标分母为 0 返回 null + reason，不返回 1.0

`metrics.py:_ratio()`/`_null()` 的用法贯穿所有比例指标。
如 `_chunk_reference_ratio` 在 `not chunks` 时返回 `("no_chunks")`，
`_pdf_locator_ratio` 在 `not elements` 时返回 `("no_elements")`。
对齐 CLAUDE.md "比例指标分母为 0 时返回 null + reason，**不返回 1.0**"。

### 2.3 `figure_caption_*` 始终 null

`annotation_metrics.py:figure_caption_prf` 固定返回 `parser_does_not_emit_relations`。
对齐 CLAUDE.md "本期不引入'最近图片'启发式"。

### 2.4 计时只记 total

`runner.py:_process_one` 用 `time.perf_counter()` 包住 `process_single`，
parse/chunk 字段固定 `null + reason="not_instrumented"`。对齐 CLAUDE.md
"parse/chunk 未插桩" 与 "不重复 total"。

### 2.5 manifest 路径必须是相对 + 正斜杠 + 位于项目根内

`manifest.py:_resolve_relative_path` 三道闸：拒绝 `_is_absolute_like`、
拒绝 `\`、`resolve()` 后必须 `relative_to(project_root)`。对齐 CLAUDE.md
"manifest 中 `path` 必须相对项目根 + 正斜杠；拒绝绝对路径与反斜杠"。

### 2.6 `silent_drop_count` 必须基于 manifest expectations

`metrics.py:_silent_drop_count` 在 `not expectations` 时返回 null。
对齐 CLAUDE.md "无 expectations → null"。

### 2.7 chunk_boundary 用一对一贪心匹配

`annotation_metrics.py` 的匹配算法：所有 (pred, gt) 距离 ≤ tolerance 的对
按距离升序排序，贪心选互不冲突的对。`test_chunk_boundary_one_to_one_matching`
覆盖了一对一约束。这是设计选择（不是 bug）。

## 3. 已识别但**未修**的小问题（建议后续 round 处理）

### 3.1 `evaluation/cli.py` 的 `--parser` choices 仍是 `("fallback", "kreuzberg")`

新增的 markdown / html / text / ipynb parser 没暴露给评测 CLI。但**不修**的理由：
- 当前评测指标 `pdf_locator_valid_ratio` / `docx_locator_valid_ratio` 都是按 PDF/DOCX 设计的；
  新格式加进来需要扩展指标体系
- 扩展可能要 bump `evaluator_version`，与"不动版本号"约束冲突
- 留给候选 I（evaluation devset 加入新格式）专门处理

### 3.2 `evaluation/cli.py:run` 子命令生成报告后又从磁盘重读校验

`run_evaluation` 已经返回 report dict，但 CLI 紧跟着又 `validate_file(output_path, ...)`
重新打开 JSON 文件。改成 `validate(report, ...)` 可省一次磁盘 IO。**不修**的理由：
- 只是低效，没有正确性问题
- 重读能验证磁盘上的 JSON 确实可解析（防写入损坏），有价值

### 3.3 `runner.py:_process_one` 的 image_dir 推导硬编码 document_id 格式

```python
did = document.document_id
sha16 = did.replace("doc-", "") if did.startswith("doc-") else did
image_dir = out_stub.parent / f"images-{sha16}"
```

依赖 `document_id = "doc-" + source_hash[:16]` 与 `image_output_dir = out_root / images-{source_hash[:16]}`
这两个约定。任一约定改了，这里就会静默错位。**不修**的理由：
- 当前两处约定一致，没有 bug
- 根治需要 pipeline 暴露 `image_output_dir` 字段或返回它；改动面较大，
  应在专门的重构 round 里做（候选：source_spans / pipeline refactor）

### 3.4 `metrics.py:_chunk_reference_ratio` 的 `elem_ids` 集合可能含 None

```python
elem_ids = {e.get("element_id") for e in elements}
```

如果某 element 没有 `element_id`，`None` 进集合；chunk 引用 None 时会
"匹配"。Schema 要求 element_id 非空，所以实践不会触发。**不修**的理由：
- 防御性边界，但 schema 已保证；加 `if e.get("element_id") is not None`
  会让代码变啰嗦且不解决真实问题

### 3.5 `metrics.py:_text_preservation` 当 expected 非空、actual 为空时 recall=0.0

这是合理语义（"应该有的东西一个都没出来" = 0 召回），不是 bug。
对称地 expected 为空、actual 非空时 precision=0.0。注释里说明即可。

## 4. 测试基线变化

| 维度 | Round 7 末 | Round 8 末 | Δ |
|---|---|---|---|
| 总测试 | 272 | 277 | +5 |
| 通过 | 272 | 277 | +5 |
| 跳过 | 9 | 9 | 0 |
| 失败 | 0 | 0 | 0 |

新增测试：
- `tests/test_annotation_metrics.py`：3 个（重复 marker × 3 场景）
- `tests/test_evaluation_runner.py`：2 个（_process_one 返回值契约）

## 5. 不变量复核

- ✅ `evaluator_version` 仍是 `"1.1"`（未触动 `evaluation/__init__.py`）
- ✅ `report_version` 仍是 `"1.1"`（同上）
- ✅ 没有改 `app/parsers/*`、`app/chunkers/*`、`app/pipeline.py`
- ✅ 没有改 manifest schema / annotation schema / evaluation-report schema
- ✅ 比例分母为 0 → null + reason（保留）
- ✅ 计时只记 total（保留）
- ✅ 不混合综合分数（保留）
- ✅ manifest 路径校验三道闸（保留）

## 6. 给后续 round 的建议

- **候选 I（evaluation devset 加入新格式）**：会需要扩展指标体系（如
  `markdown_section_path_valid_ratio`），届时必须 bump `evaluator_version`
  到 `"1.2"` 并在 `evaluation/__init__.py` 注释里加 v1.2 的语义变化说明
- **source_spans 重构**：参见 `metrics.py:_text_preservation` 的 docstring，
  里面已写明"若需要空白级精确验证，必须为每个 chunk 增加 source_spans"
- **pipeline 暴露 image_output_dir**：参见上文 3.3
