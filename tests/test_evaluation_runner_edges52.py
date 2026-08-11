"""evaluation/runner.py 第五十四轮 edges 测试（Round 493）。

补强 edges51 未触及的角度（第二十四批）：
- _load_annotation 第二十四批：null/true/false/string/scientific/int/大整数/嵌套 10 层/emoji/unicode escape/前导空白/前导 BOM+有效 JSON/CRLF/打开括号/关闭括号/JSON 后跟内容/空字符串
- _process_one 第二十四批：out_stub 命名约定（_per_doc/<doc_id>.json）/mkdir 先于 process_single/elapsed 非负/parser_name 关键字传入/max_chars 关键字传入/process_single 仅调用一次/返回 5-tuple 元素类型/parser_version None 时 image_dir 仍可计算
- run_evaluation 第二十四批：build_provenance 调用参数精确/build_devset_section 接收 manifest/compute_automatic_metrics 每文档调用一次/figure_caption_prf 每文档调用一次/chunk_boundary_prf 每文档调用一次/multiple expected_failures/expected_failure 成功解析/输出文件 utf-8 编码/output_root.mkdir parents+exist_ok/parser_name 透传到 _process_one/max_chars 透传/_annotation_present True/False/_tolerance_chars 透传到 per_doc（私有字段被剥除）
- module source forbidden tokens 第四十一批
- module source 字符串精确补强第三十七批
- signatures 第三十七批
- module 合理性第三十七批
- 端到端集成第三十七批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十四批 ----------


def test_load_annotation_null_literal_batch24(tmp_path):
    """JSON `null` 顶层 → 解析为 None → 返回 None（与 error case 同型，无法区分）。"""
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_true_literal_batch24(tmp_path):
    """JSON `true` 顶层 → 解析为 True。"""
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_false_literal_batch24(tmp_path):
    """JSON `false` 顶层 → 解析为 False。"""
    p = tmp_path / "a.json"
    p.write_text("false", encoding="utf-8")
    assert _load_annotation(p) is False


def test_load_annotation_string_top_level_batch24(tmp_path):
    """JSON 字符串顶层（合法）。"""
    p = tmp_path / "a.json"
    p.write_text('"hello world"', encoding="utf-8")
    assert _load_annotation(p) == "hello world"


def test_load_annotation_scientific_notation_batch24(tmp_path):
    """JSON 科学记数法 → 解析为 float。"""
    p = tmp_path / "a.json"
    p.write_text("1.5e3", encoding="utf-8")
    assert _load_annotation(p) == 1500.0


def test_load_annotation_large_integer_batch24(tmp_path):
    """JSON 大整数（超出 int32）。"""
    p = tmp_path / "a.json"
    p.write_text("9007199254740993", encoding="utf-8")  # > 2^53
    out = _load_annotation(p)
    assert isinstance(out, int)
    assert out == 9007199254740993


def test_load_annotation_nested_10_levels_batch24(tmp_path):
    """嵌套 10 层 dict（每层一个 key 'n' 指向下一层）仍可解析。"""
    p = tmp_path / "a.json"
    # 构造 {"n": {"n": {"n": ... {"n": 1}...}}}（10 层）
    payload = 1
    for _ in range(10):
        payload = {"n": payload}
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)
    # 深入 9 层后应仍是 dict
    inner = out
    for _ in range(9):
        inner = inner["n"]
    assert isinstance(inner, dict)
    # 第 10 层的 "n" 是 1
    assert inner["n"] == 1


def test_load_annotation_emoji_batch24(tmp_path):
    """JSON 含 emoji 字符串。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": "\\ud83d\\ude00"}', encoding="utf-8")  # \u escape 形式
    out = _load_annotation(p)
    assert out["k"] == "\U0001F600"


def test_load_annotation_unicode_escape_batch24(tmp_path):
    """JSON \\u00e9 → 'é'。"""
    p = tmp_path / "a.json"
    p.write_text('"\\u00e9"', encoding="utf-8")
    assert _load_annotation(p) == "é"


def test_load_annotation_leading_whitespace_valid_batch24(tmp_path):
    """JSON 前导空白 → 合法（json 允许）。"""
    p = tmp_path / "a.json"
    p.write_text('   \n  {"a": 1}  \n', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_bom_plus_valid_batch24(tmp_path):
    """BOM + 合法 JSON → Python utf-8 可解码（BOM 被去）→ json.load 成功。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    out = _load_annotation(p)
    # 注意：Python utf-8 解码 BOM 为 ﻿，json 应失败；但 utf-8-sig 才会 strip BOM
    # 这里 encoding="utf-8"（非 sig），所以 BOM 字符 ﻿ 留在前面
    # 实际：json 会在第一字符位置见到 ﻿ → JSONDecodeError → None
    assert out is None


def test_load_annotation_crlf_line_endings_batch24(tmp_path):
    """JSON 含 CRLF 行尾 → 仍合法。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'{\r\n  "a": 1\r\n}')
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_only_opening_brace_batch24(tmp_path):
    """只一个 `{` → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_only_closing_brace_batch24(tmp_path):
    """只一个 `}` → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_extra_after_json_batch24(tmp_path):
    """JSON 后跟额外内容 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1} extra', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_string_batch24(tmp_path):
    """空字符串 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_array_with_nested_batch24(tmp_path):
    """JSON 数组嵌套。"""
    p = tmp_path / "a.json"
    p.write_text('[[1, 2], [3, 4], {"k": [5, 6]}]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [[1, 2], [3, 4], {"k": [5, 6]}]


def test_load_annotation_mixed_types_batch24(tmp_path):
    """JSON 含所有基本类型。"""
    p = tmp_path / "a.json"
    payload = {
        "str": "text",
        "int": 42,
        "float": 3.14,
        "bool_t": True,
        "bool_f": False,
        "null": None,
        "arr": [1, "two", None, False],
        "nested": {"deep": {"deeper": "value"}},
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = _load_annotation(p)
    assert out == payload


# ---------- _process_one 第二十四批 ----------


@pytest.fixture
def fake_doc_v2():
    """构造一个最小 DocumentEntry mock（用 v2 后缀避免与 edges51 fixture 冲突）。"""
    doc = MagicMock()
    doc.doc_id = "test_doc_001"
    doc.resolved_path = Path("/fake/path.pdf")
    return doc


def test_process_one_out_stub_naming_batch24(fake_doc_v2, tmp_path):
    """out_stub 必须遵循 output_root/_per_doc/<doc_id>.json 命名约定。"""
    captured = {}

    def fake_ps(path, output_path, **kwargs):
        captured["output_path"] = str(output_path)
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_ps):
        _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    # output_path 必须形如 tmp_path/_per_doc/test_doc_001.json
    assert captured["output_path"].replace("\\", "/").endswith("_per_doc/test_doc_001.json")


def test_process_one_mkdir_before_process_single_batch24(fake_doc_v2, tmp_path):
    """mkdir 必须先于 process_single 调用（顺序检查）。"""
    call_order = []
    real_mkdir = Path.mkdir

    def tracking_mkdir(self, *args, **kwargs):
        call_order.append(("mkdir", str(self)))
        return real_mkdir(self, *args, **kwargs)

    def tracking_ps(*args, **kwargs):
        call_order.append(("process_single", ""))
        return None, []

    with patch("evaluation.runner.process_single", side_effect=tracking_ps), patch(
        "pathlib.Path.mkdir", tracking_mkdir
    ):
        _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    # 第一个应该是 mkdir
    assert call_order[0][0] == "mkdir"


def test_process_one_elapsed_non_negative_batch24(fake_doc_v2, tmp_path):
    """elapsed 必须 >= 0.0。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _, _, elapsed, _, _ = _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    assert elapsed >= 0.0


def test_process_one_process_single_called_once_batch24(fake_doc_v2, tmp_path):
    """process_single 只被调用一次。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    assert ps_mock.call_count == 1


def test_process_one_parser_name_kwarg_used_batch24(fake_doc_v2, tmp_path):
    """parser_name 通过关键字传入 process_single。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc_v2, tmp_path, "kreuzberg", 1200)
    kwargs = ps_mock.call_args.kwargs
    assert kwargs.get("parser_name") == "kreuzberg"


def test_process_one_max_chars_kwarg_used_batch24(fake_doc_v2, tmp_path):
    """max_chars 通过关键字传入 process_single。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc_v2, tmp_path, "fallback", 999)
    kwargs = ps_mock.call_args.kwargs
    assert kwargs.get("max_chars") == 999


def test_process_one_returns_5_tuple_element_types_batch24(fake_doc_v2, tmp_path):
    """返回 tuple 元素类型：dict|None, dict|None, float, str|None, Path|None。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        result = _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    document, error, elapsed, parser_version, image_dir = result
    assert document is None or isinstance(document, dict)
    assert error is None or isinstance(error, dict)
    assert isinstance(elapsed, float)
    assert parser_version is None or isinstance(parser_version, str)
    assert image_dir is None or isinstance(image_dir, Path)


def test_process_one_write_json_always_false_batch24(fake_doc_v2, tmp_path):
    """write_json 必须始终为 False（runner 不写中间文件）。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    assert ps_mock.call_args.kwargs.get("write_json") is False


def test_process_one_image_dir_independent_of_parser_version_batch24(
    fake_doc_v2, tmp_path
):
    """parser_version=None 但 document 存在 → image_dir 仍计算。"""
    document = MagicMock()
    document.to_dict.return_value = {"id": "x"}
    document.parser_version = None  # 显式 None
    document.source_hash = "h1"
    expected = tmp_path / "_per_doc" / "img"
    with patch(
        "evaluation.runner.process_single", return_value=(document, [])
    ), patch(
        "evaluation.runner.image_output_dir_for", return_value=expected
    ):
        _, _, _, parser_version, image_dir = _process_one(
            fake_doc_v2, tmp_path, "fallback", 800
        )
    assert parser_version is None
    assert image_dir == expected


def test_process_one_first_positional_arg_is_resolved_path_batch24(
    fake_doc_v2, tmp_path
):
    """process_single 第一个位置参数必须是 doc.resolved_path。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc_v2, tmp_path, "fallback", 800)
    args = ps_mock.call_args.args
    assert args[0] == fake_doc_v2.resolved_path


# ---------- run_evaluation 第二十四批 ----------


def _build_document_dict_v2(doc_id="d1", source_type="pdf"):
    """构造一个最小合法 document dict（v2 后缀避免冲突）。"""
    return {
        "doc_id": doc_id,
        "source_type": source_type,
        "source_locator": (
            {"page": 1, "bbox": [0, 0, 100, 100]} if source_type == "pdf" else {}
        ),
        "elements": [],
        "chunks": [],
        "source_hash": "abc",
        "parser_version": "fallback/test",
    }


def _make_empty_manifest(tmp_path):
    """构造一个空 manifest MagicMock。"""
    m = MagicMock()
    m.documents = []
    m.expected_failures = []
    m.project_root = tmp_path
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_build_provenance_called_with_correct_args_batch24(tmp_path):
    """build_provenance 必须用 (project_root, parser_name, max_chars, parser_version) 调用。"""
    manifest = _make_empty_manifest(tmp_path)
    with patch("evaluation.runner.build_provenance", return_value={}) as bp_mock:
        run_evaluation(manifest, tmp_path / "out.json", parser_name="kreuzberg", max_chars=500)
    bp_mock.assert_called_once()
    kwargs = bp_mock.call_args.kwargs
    assert kwargs.get("project_root") == tmp_path
    assert kwargs.get("parser_name") == "kreuzberg"
    assert kwargs.get("max_chars") == 500


def test_run_evaluation_build_devset_section_called_with_manifest_batch24(tmp_path):
    """build_devset_section 接收 manifest 对象。"""
    manifest = _make_empty_manifest(tmp_path)
    with patch("evaluation.runner.build_devset_section", return_value={}) as bds_mock:
        run_evaluation(manifest, tmp_path / "out.json")
    bds_mock.assert_called_once_with(manifest)


def test_run_evaluation_aggregate_summary_called_with_per_doc_results_batch24(tmp_path):
    """aggregate_summary 必须接收 per_doc_results list。"""
    manifest = _make_empty_manifest(tmp_path)
    with patch("evaluation.runner.aggregate_summary", return_value={}) as as_mock:
        run_evaluation(manifest, tmp_path / "out.json")
    as_mock.assert_called_once()
    args = as_mock.call_args.args
    assert isinstance(args[0], list)


def test_run_evaluation_compute_metrics_called_per_doc_batch24(tmp_path):
    """manifest 有 N 个 documents → compute_automatic_metrics 调用 N 次。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    doc2 = MagicMock()
    doc2.doc_id = "d2"
    doc2.source_type = "pdf"
    doc2.resolved_path = tmp_path / "d2.pdf"
    doc2.expectations = None
    doc2.annotation_resolved = None

    doc3 = MagicMock()
    doc3.doc_id = "d3"
    doc3.source_type = "pdf"
    doc3.resolved_path = tmp_path / "d3.pdf"
    doc3.expectations = None
    doc3.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1, doc2, doc3]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.compute_automatic_metrics", return_value={"pipeline_success": {"value": True}}
    ) as cam_mock:
        run_evaluation(manifest, tmp_path / "out.json")
    assert cam_mock.call_count == 3


def test_run_evaluation_figure_caption_prf_called_per_doc_batch24(tmp_path):
    """manifest 有 2 个 documents → figure_caption_prf 调用 2 次。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    doc2 = MagicMock()
    doc2.doc_id = "d2"
    doc2.source_type = "pdf"
    doc2.resolved_path = tmp_path / "d2.pdf"
    doc2.expectations = None
    doc2.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1, doc2]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.figure_caption_prf", return_value={}
    ) as fcp_mock:
        run_evaluation(manifest, tmp_path / "out.json")
    assert fcp_mock.call_count == 2


def test_run_evaluation_chunk_boundary_prf_called_per_doc_batch24(tmp_path):
    """manifest 有 2 个 documents → chunk_boundary_prf 调用 2 次。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    doc2 = MagicMock()
    doc2.doc_id = "d2"
    doc2.source_type = "pdf"
    doc2.resolved_path = tmp_path / "d2.pdf"
    doc2.expectations = None
    doc2.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1, doc2]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.chunk_boundary_prf", return_value={}
    ) as cbp_mock:
        run_evaluation(manifest, tmp_path / "out.json")
    assert cbp_mock.call_count == 2


def test_run_evaluation_multiple_expected_failures_batch24(tmp_path):
    """manifest 有 3 个 expected_failures → expected_failure_results 含 3 条。"""
    efs = []
    for i in range(3):
        ef = MagicMock()
        ef.doc_id = f"ef{i}"
        ef.expected_error_code = "unsupported_format"
        ef.resolved_path = tmp_path / f"ef{i}.txt"
        efs.append(ef)

    manifest = _make_empty_manifest(tmp_path)
    manifest.expected_failures = efs

    err = MagicMock()
    err.code = "unsupported_format"

    with patch(
        "evaluation.runner.process_single", return_value=(None, [err])
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert len(report["expected_failures"]) == 3
    for i, efr in enumerate(report["expected_failures"]):
        assert efr["doc_id"] == f"ef{i}"
        assert efr["matches"] is True


def test_run_evaluation_expected_failure_succeeds_batch24(tmp_path):
    """expected_failure 但 process_single 返回成功 → matches=False（实际无错）。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = tmp_path / "ef1.txt"

    manifest = _make_empty_manifest(tmp_path)
    manifest.expected_failures = [ef]

    document = MagicMock()
    document.to_dict.return_value = {"id": "ok"}

    with patch(
        "evaluation.runner.process_single", return_value=(document, [])
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    efr = report["expected_failures"][0]
    assert efr["actual_error_code"] is None
    assert efr["matches"] is False


def test_run_evaluation_output_file_utf8_encoded_batch24(tmp_path):
    """输出文件必须是 UTF-8 编码（中文 categories 不乱码）。"""
    manifest = _make_empty_manifest(tmp_path)
    manifest.categories_covered = ["技术", "金融"]

    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    raw_bytes = out.read_bytes()
    # 中文字符 UTF-8 编码（"技" = E6 8A 80）
    assert "技术".encode("utf-8") in raw_bytes


def test_run_evaluation_output_root_mkdir_called_batch24(tmp_path):
    """output_root.mkdir 必须用 parents=True, exist_ok=True（用 wraps 让真实 mkdir 仍执行）。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "deep" / "nested" / "report.json"
    real_mkdir = Path.mkdir
    mkdir_calls = []

    def tracking_mkdir(self, *args, **kwargs):
        mkdir_calls.append((self, kwargs))
        return real_mkdir(self, *args, **kwargs)

    with patch("pathlib.Path.mkdir", tracking_mkdir):
        run_evaluation(manifest, out)
    # 至少一次调用含 parents=True exist_ok=True
    assert any(
        c[1].get("parents") is True and c[1].get("exist_ok") is True
        for c in mkdir_calls
    )
    # 文件应被实际创建
    assert out.is_file()


def test_run_evaluation_parser_name_passed_to_process_one_batch24(tmp_path):
    """parser_name 必须从 run_evaluation 透传到 _process_one。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ) as po_mock:
        run_evaluation(manifest, tmp_path / "out.json", parser_name="kreuzberg")
    args = po_mock.call_args.args
    # 第三个位置参数是 parser_name
    assert args[2] == "kreuzberg"


def test_run_evaluation_max_chars_passed_to_process_one_batch24(tmp_path):
    """max_chars 必须从 run_evaluation 透传到 _process_one。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ) as po_mock:
        run_evaluation(manifest, tmp_path / "out.json", max_chars=2000)
    args = po_mock.call_args.args
    # 第四个位置参数是 max_chars
    assert args[3] == 2000


def test_run_evaluation_public_per_doc_excludes_private_fields_batch24(tmp_path):
    """public_per_doc 必须剥除 _annotation_present / _tolerance_chars / _missing_markers。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)
    pd = report["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "_tolerance_chars" not in pd
    assert "_missing_markers" not in pd


def test_run_evaluation_annotation_present_when_file_exists_batch24(tmp_path):
    """annotation_resolved 指向存在的文件 → _annotation_present 内部 = True（通过 figure_caption_prf 被调用确认）。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    ann_path = tmp_path / "ann.json"
    ann_path.write_text("{}", encoding="utf-8")
    doc1.annotation_resolved = ann_path

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    captured = {}

    def fake_fcp(document, annotation):
        captured["annotation"] = annotation
        return {}

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.figure_caption_prf", side_effect=fake_fcp
    ):
        run_evaluation(manifest, tmp_path / "out.json")

    # annotation 应是非 None（因为文件存在）
    assert captured["annotation"] == {}


def test_run_evaluation_annotation_absent_when_file_missing_batch24(tmp_path):
    """annotation_resolved 指向不存在的文件 → _annotation_present=False（annotation=None）。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = tmp_path / "nope.json"  # 不存在

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    captured = {}

    def fake_fcp(document, annotation):
        captured["annotation"] = annotation
        return {}

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.figure_caption_prf", side_effect=fake_fcp
    ):
        run_evaluation(manifest, tmp_path / "out.json")

    assert captured["annotation"] is None


def test_run_evaluation_annotation_none_path_batch24(tmp_path):
    """annotation_resolved = None → annotation=None → figure_caption_prf(None, None)。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = [doc1]

    captured = {}

    def fake_fcp(document, annotation):
        captured["annotation"] = annotation
        return {}

    with patch(
        "evaluation.runner._process_one",
        return_value=(_build_document_dict_v2(), None, 0.1, "v", None),
    ), patch(
        "evaluation.runner.figure_caption_prf", side_effect=fake_fcp
    ):
        run_evaluation(manifest, tmp_path / "out.json")

    assert captured["annotation"] is None


def test_run_evaluation_write_json_overwrite_existing_batch24(tmp_path):
    """已存在的输出文件应被覆盖（不是追加）。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    out.write_text('{"old": "content that should be overwritten"}', encoding="utf-8")

    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert "old" not in data
    assert "report_version" in data


def test_run_evaluation_returns_dict_batch24(tmp_path):
    """run_evaluation 返回 dict。"""
    manifest = _make_empty_manifest(tmp_path)
    out = run_evaluation(manifest, tmp_path / "report.json")
    assert isinstance(out, dict)


def test_run_evaluation_per_doc_order_preserved_batch24(tmp_path):
    """manifest.documents 顺序必须保留到 per_doc。"""
    docs = []
    for i in range(5):
        d = MagicMock()
        d.doc_id = f"d{i}"
        d.source_type = "pdf"
        d.resolved_path = tmp_path / f"d{i}.pdf"
        d.expectations = None
        d.annotation_resolved = None
        docs.append(d)

    manifest = _make_empty_manifest(tmp_path)
    manifest.documents = docs

    # 每个 doc 用不同 parser_version 区分
    sides = [
        (_build_document_dict_v2(f"d{i}"), None, 0.1, f"v{i}", None)
        for i in range(5)
    ]
    with patch(
        "evaluation.runner._process_one",
        side_effect=sides,
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)
    pd_ids = [p["doc_id"] for p in report["per_doc"]]
    assert pd_ids == ["d0", "d1", "d2", "d3", "d4"]


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import datetime",
    "import subprocess",
    "import csv",
    "import xml",
    "import logging.handlers",
]


def test_module_source_forbidden_tokens_batch24():
    """runner.py 不应直接 import 这些副作用大的模块。"""
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch24():
    """runner.py 不应使用 class（functional 风格）。"""
    source = inspect.getsource(rmod)
    import re as _re
    matches = _re.findall(r"\bclass\s+\w+", source)
    assert matches == [], f"unexpected class definitions: {matches}"


def test_module_source_no_yield_batch24():
    """runner.py 不应使用 yield。"""
    source = inspect.getsource(rmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch24():
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch24():
    source = inspect.getsource(rmod)
    assert "global " not in source


def test_module_source_no_walrus_batch24():
    source = inspect.getsource(rmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch24():
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_subprocess_batch24():
    """runner.py 不应使用 subprocess（仅 report.py 需要）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_module_source_no_pickle_batch24():
    source = inspect.getsource(rmod)
    assert "pickle" not in source


def test_module_source_no_shutil_batch24():
    source = inspect.getsource(rmod)
    assert "shutil" not in source


def test_module_source_no_tempfile_batch24():
    source = inspect.getsource(rmod)
    assert "tempfile" not in source


def test_module_source_no_environ_batch24():
    source = inspect.getsource(rmod)
    assert "os.environ" not in source


def test_module_source_no_argparse_batch24():
    source = inspect.getsource(rmod)
    assert "argparse" not in source


def test_module_source_no_dataclass_batch24():
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source


def test_module_source_no_network_io_batch24():
    source = inspect.getsource(rmod)
    assert "import socket" not in source
    assert "import http" not in source
    assert "import requests" not in source


def test_module_source_no_relative_imports_batch24():
    """runner.py 不应使用相对导入（from .）。"""
    source = inspect.getsource(rmod)
    lines = [l for l in source.split("\n") if "from " in l and "from __future__" not in l]
    for line in lines:
        assert not line.strip().startswith("from ."), f"relative import: {line}"


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_image_output_dir_for_batch24():
    """source 必须从 app.pipeline 导入 image_output_dir_for。"""
    source = inspect.getsource(rmod)
    assert "image_output_dir_for" in source
    assert "from app.pipeline import" in source


def test_module_source_contains_process_single_batch24():
    """source 必须从 app.pipeline 导入 process_single。"""
    source = inspect.getsource(rmod)
    assert "process_single" in source


def test_module_source_contains_report_version_import_batch24():
    """source 必须含 from evaluation import REPORT_VERSION。"""
    source = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in source


def test_module_source_contains_chunk_boundary_prf_import_batch24():
    """source 必须从 evaluation.annotation_metrics 导入 chunk_boundary_prf。"""
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source


def test_module_source_contains_figure_caption_prf_import_batch24():
    """source 必须从 evaluation.annotation_metrics 导入 figure_caption_prf。"""
    source = inspect.getsource(rmod)
    assert "figure_caption_prf" in source


def test_module_source_contains_compute_automatic_metrics_import_batch24():
    """source 必须从 evaluation.metrics 导入 compute_automatic_metrics。"""
    source = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in source


def test_module_source_contains_aggregate_summary_import_batch24():
    """source 必须从 evaluation.report 导入 aggregate_summary。"""
    source = inspect.getsource(rmod)
    assert "aggregate_summary" in source


def test_module_source_contains_build_devset_section_import_batch24():
    """source 必须从 evaluation.report 导入 build_devset_section。"""
    source = inspect.getsource(rmod)
    assert "build_devset_section" in source


def test_module_source_contains_build_provenance_import_batch24():
    """source 必须从 evaluation.report 导入 build_provenance。"""
    source = inspect.getsource(rmod)
    assert "build_provenance" in source


def test_module_source_contains_time_perf_counter_batch24():
    """source 必须使用 time.perf_counter（计时）。"""
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_contains_not_instrumented_batch24():
    """source 必须含 reason='not_instrumented' 字符串字面量。"""
    source = inspect.getsource(rmod)
    assert '"not_instrumented"' in source


def test_module_source_contains_write_json_false_batch24():
    """source 必须含 write_json=False。"""
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_contains_per_doc_subdir_batch24():
    """source 必须含 _per_doc 子目录命名约定。"""
    source = inspect.getsource(rmod)
    assert "_per_doc" in source


def test_module_source_contains_ensure_ascii_false_batch24():
    """source 必须含 ensure_ascii=False。"""
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


def test_module_source_contains_indent_2_batch24():
    """source 必须含 indent=2。"""
    source = inspect.getsource(rmod)
    assert "indent=2" in source


# ---------- signatures 第三十七批 ----------


def test_signature_load_annotation_param_count_batch24():
    """_load_annotation 仅 1 个参数。"""
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_signature_process_one_param_count_batch24():
    """_process_one 4 个参数。"""
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_signature_run_evaluation_param_count_batch24():
    """run_evaluation 5 个参数。"""
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_signature_run_evaluation_keyword_only_params_batch24():
    """parser_name, max_chars, tolerance_chars 是 KEYWORD_ONLY。"""
    sig = inspect.signature(run_evaluation)
    for name in ["parser_name", "max_chars", "tolerance_chars"]:
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_positional_only_manifest_output_batch24():
    """manifest 与 output_path 是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_process_one_no_defaults_batch24():
    """_process_one 所有参数都必填（无默认值）。"""
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_load_annotation_no_varargs_batch24():
    """_load_annotation 不接受 *args / **kwargs。"""
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_run_evaluation_no_varargs_batch24():
    """run_evaluation 不接受 *args / **kwargs。"""
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- module 合理性第三十七批 ----------


def test_module_all_only_run_evaluation_batch24():
    """__all__ 仅暴露 run_evaluation。"""
    assert hasattr(rmod, "__all__")
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_three_callables_batch24():
    """runner.py 定义 3 个函数：_load_annotation, _process_one, run_evaluation。"""
    funcs = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isfunction)
        if val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_classes_batch24():
    """runner.py 不定义任何 class。"""
    classes = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isclass)
        if val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch24():
    """module 有 docstring。"""
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 0


def test_module_docstring_mentions_evaluation_batch24():
    """module docstring 应提及 evaluation 或 评测。"""
    src = rmod.__doc__
    assert "评测" in src or "evaluation" in src.lower() or "runner" in src.lower()


def test_module_process_one_docstring_present_batch24():
    """_process_one 有 docstring。"""
    assert _process_one.__doc__ is not None
    assert len(_process_one.__doc__) > 0


def test_module_run_evaluation_docstring_present_batch24():
    """run_evaluation 有 docstring。"""
    assert run_evaluation.__doc__ is not None


def test_module_uses_from_future_annotations_batch24():
    """runner.py 必须有 from __future__ import annotations。"""
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


def test_module_constants_no_module_level_mutables_batch24():
    """runner.py 顶层无私有常量（除 __all__）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(rmod))
    top_level_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    for node in top_level_assigns:
        for target in node.targets:
            assert isinstance(target, _ast.Name)
            assert target.id == "__all__", f"unexpected top-level assignment: {target.id}"


def test_module_imports_use_absolute_form_batch24():
    """import 必须用绝对形式（from evaluation.X / from app.X），不用相对。"""
    source = inspect.getsource(rmod)
    lines = [
        l.strip() for l in source.split("\n")
        if l.strip().startswith("from ") and "from __future__" not in l
    ]
    for l in lines:
        assert not l.startswith("from ."), f"relative import: {l}"


# ---------- 端到端集成第三十七批 ----------


def test_e2e_full_flow_no_documents_writes_valid_json_batch24(tmp_path):
    """空 manifest → JSON 文件可被 json.load。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["report_version"] == REPORT_VERSION
    assert data["per_doc"] == []


def test_e2e_summary_has_four_top_keys_batch24(tmp_path):
    """summary 顶层 4 keys。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert set(report["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_e2e_report_has_six_top_keys_batch24(tmp_path):
    """report 顶层 6 keys。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_e2e_devset_section_six_keys_batch24(tmp_path):
    """devset 含 6 keys。"""
    manifest = _make_empty_manifest(tmp_path)
    manifest.devset_status = "complete"
    manifest.file_count = 10
    manifest.content_group_count = 5
    manifest.pdf_count = 4
    manifest.docx_count = 6
    manifest.categories_covered = ["cat1", "cat2", "cat3"]

    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert set(report["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }
    assert report["devset"]["status"] == "complete"
    assert report["devset"]["file_count"] == 10


def test_e2e_provenance_nine_keys_batch24(tmp_path):
    """provenance 含 9 keys。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert set(report["provenance"].keys()) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_e2e_str_path_output_accepted_batch24(tmp_path):
    """output_path 接受 str。"""
    manifest = _make_empty_manifest(tmp_path)
    out = str(tmp_path / "report.json")
    report = run_evaluation(manifest, out)
    assert Path(out).is_file()
    assert report["report_version"] == REPORT_VERSION


def test_e2e_return_value_matches_file_batch24(tmp_path):
    """返回值 = 文件读回 dict。"""
    manifest = _make_empty_manifest(tmp_path)
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        file_report = json.load(f)
    assert report == file_report
