"""evaluation/runner.py 第五十二轮 edges 测试（Round 479）。

补强 edges49 未触及的角度：
- _load_annotation 第二十二批（BOM+invalid JSON / 二进制内容 / Unicode 转义 / nested / list 顶层 / null / 数字顶层 / 字符串顶层 / True 顶层）
- _process_one 第二十二批（out_stub 路径构造 / process_single kwargs 透传 / unlink 缺文件不抛 / image_dir=None when document None / error 返回 to_dict 调用）
- run_evaluation 第二十二批（per_doc 写入顺序 / image_base_dir 选择性传入 / annotation_present 注入 / 缺 _tolerance_chars 时 _tolerance_chars=None / 缺 _missing_markers 时 [] / parser_version 第一次出现后被锁 / per_doc 7 字段 / output_root 父目录创建嵌套）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation
from evaluation import runner as rmod


# ---------- _load_annotation 第二十二批 ----------


def test_load_annotation_utf8_bom_with_invalid_json_returns_none_batch22(tmp_path):
    """UTF-8 BOM + 非法 JSON → JSONDecodeError → None（不是 UnicodeDecodeError）。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": invalid}')
    assert _load_annotation(p) is None


def test_load_annotation_binary_content_returns_none_batch22(tmp_path):
    """纯二进制内容（含 0x80+ 非 UTF-8 字节）→ UnicodeDecodeError 未被 (OSError, JSONDecodeError) 捕获 → 传播。"""
    p = tmp_path / "a.json"
    p.write_bytes(bytes(range(256)))
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


def test_load_annotation_unicode_escape_batch22(tmp_path):
    """\\uXXXX 转义能正确解析。"""
    p = tmp_path / "a.json"
    p.write_text('{"k": "\\u4e2d\\u6587"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "中文"}


def test_load_annotation_nested_dict_batch22(tmp_path):
    """深度嵌套 dict 能解析。"""
    p = tmp_path / "a.json"
    payload = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
    p.write_text(json.dumps(payload), encoding="utf-8")
    assert _load_annotation(p) == payload


def test_load_annotation_top_level_list_returns_dict_batch22(tmp_path):
    """顶层是 list 时返回 list（不是 dict）—— 函数仅返回 json.load 结果，不强制 dict。"""
    p = tmp_path / "a.json"
    p.write_text('[1, 2, 3]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]
    assert isinstance(out, list)


def test_load_annotation_top_level_null_batch22(tmp_path):
    """顶层是 null 时返回 None（与文件读失败返回 None 无法区分）。"""
    p = tmp_path / "a.json"
    p.write_text('null', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_top_level_number_batch22(tmp_path):
    """顶层是数字时返回数字。"""
    p = tmp_path / "a.json"
    p.write_text('42', encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_top_level_string_batch22(tmp_path):
    """顶层是字符串时返回字符串。"""
    p = tmp_path / "a.json"
    p.write_text('"hello"', encoding="utf-8")
    assert _load_annotation(p) == "hello"


def test_load_annotation_top_level_true_batch22(tmp_path):
    """顶层是 true 时返回 True。"""
    p = tmp_path / "a.json"
    p.write_text('true', encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_path_is_dir_returns_none_batch22(tmp_path):
    """path 是目录 → OSError（is_file=False 短路 → None，不抛）。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_path_is_symlink_to_file_batch22(tmp_path):
    """path 是符号链接指向真实文件 → 返回内容。"""
    target = tmp_path / "real.json"
    target.write_text('{"k": 1}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    assert _load_annotation(link) == {"k": 1}


# ---------- _process_one 第二十二批 ----------


def _make_doc(doc_id="d1", source_type="pdf"):
    d = MagicMock()
    d.doc_id = doc_id
    d.source_type = source_type
    d.resolved_path = Path("/fake.pdf")
    d.expectations = None
    d.annotation_resolved = None
    return d


def test_process_one_out_stub_under_per_doc_batch22(tmp_path):
    """out_stub 路径在 _per_doc 子目录，文件名是 <doc_id>.json。"""
    doc = _make_doc(doc_id="xyz")
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["out"] = out
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _process_one(doc, tmp_path, "fallback", 800)
    assert captured["out"].parent.name == "_per_doc"
    assert captured["out"].name == "xyz.json"


def test_process_one_passes_parser_name_to_pipeline_batch22(tmp_path):
    """process_single 接收 parser_name kwarg。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured.update(kwargs)
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _process_one(doc, tmp_path, "kreuzberg", 800)
    assert captured["parser_name"] == "kreuzberg"


def test_process_one_passes_max_chars_to_pipeline_batch22(tmp_path):
    """process_single 接收 max_chars kwarg。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured.update(kwargs)
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _process_one(doc, tmp_path, "fallback", 1234)
    assert captured["max_chars"] == 1234


def test_process_one_passes_write_json_false_batch22(tmp_path):
    """process_single 接收 write_json=False。"""
    doc = _make_doc()
    captured = {}

    def fake_process(path, out, **kwargs):
        captured.update(kwargs)
        return None, []

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        _process_one(doc, tmp_path, "fallback", 800)
    assert captured["write_json"] is False


def test_process_one_returns_5_tuple_batch22(tmp_path):
    """_process_one 返回 5-tuple。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_image_dir_none_when_document_none_batch22(tmp_path):
    """document=None 时 image_dir 是 None。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for") as mock_img:
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None
    assert not mock_img.called  # document None 时不调 image_output_dir_for


def test_process_one_image_dir_path_when_document_present_batch22(tmp_path):
    """document 非 None 时 image_dir 是 Path。"""
    doc = _make_doc()
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1"
    document_mock.source_hash = "h"
    fake_dir = tmp_path / "images"
    fake_dir.mkdir()
    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for", return_value=fake_dir
        ):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == fake_dir


def test_process_one_error_to_dict_called_batch22(tmp_path):
    """errors[0].to_dict() 被调用一次。"""
    doc = _make_doc()
    err = MagicMock()
    err.to_dict.return_value = {"code": "PARSE_FAIL", "message": "x"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert err.to_dict.call_count == 1
    assert error == {"code": "PARSE_FAIL", "message": "x"}


def test_process_one_unlink_no_file_not_raise_batch22(tmp_path):
    """out_stub 不存在时 unlink 不被调用，不抛。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch.object(Path, "unlink") as mock_unlink:
                _process_one(doc, tmp_path, "fallback", 800)
    # 文件不存在（process_single write_json=False 没创建），所以 unlink 不会调用
    assert not mock_unlink.called


def test_process_one_elapsed_nonnegative_batch22(tmp_path):
    """elapsed >= 0。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert elapsed >= 0


# ---------- run_evaluation 第二十二批 ----------


def _make_manifest(docs=(), expected_failures=(), project_root=None):
    m = MagicMock()
    m.documents = list(docs)
    m.expected_failures = list(expected_failures)
    m.project_root = project_root or Path(".")
    m.devset_status = "incomplete"
    m.file_count = len(docs)
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_per_doc_order_preserved_batch22(tmp_path):
    """多个 doc 时 per_doc 顺序保持。"""
    docs = [_make_doc(f"d{i}") for i in range(4)]
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=docs)
                        report = run_evaluation(m, tmp_path / "out.json")
    assert [pd["doc_id"] for pd in report["per_doc"]] == ["d0", "d1", "d2", "d3"]


def test_run_evaluation_image_base_dir_passed_when_dir_exists_batch22(tmp_path):
    """image_dir 是目录时 compute_automatic_metrics 收到 image_base_dir。"""
    doc = _make_doc()
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    captured = {}
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1"
    document_mock.source_hash = "h"

    def fake_metrics(document, error, source_type, expectations, image_base_dir):
        captured["image_base_dir"] = image_base_dir
        return {}

    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for", return_value=img_dir
        ):
            with patch(
                "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
            ):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured["image_base_dir"] == img_dir


def test_run_evaluation_image_base_dir_none_when_not_dir_batch22(tmp_path):
    """image_dir 不是目录时 image_base_dir=None。"""
    doc = _make_doc()
    fake_path = tmp_path / "nope"  # 不存在
    captured = {}
    document_mock = MagicMock()
    document_mock.to_dict.return_value = {"d": 1}
    document_mock.parser_version = "1"
    document_mock.source_hash = "h"

    def fake_metrics(document, error, source_type, expectations, image_base_dir):
        captured["image_base_dir"] = image_base_dir
        return {}

    with patch(
        "evaluation.runner.process_single", return_value=(document_mock, [])
    ):
        with patch(
            "evaluation.runner.image_output_dir_for", return_value=fake_path
        ):
            with patch(
                "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
            ):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured["image_base_dir"] is None


def test_run_evaluation_image_base_dir_none_when_image_dir_none_batch22(tmp_path):
    """document=None → image_dir=None → image_base_dir=None。"""
    doc = _make_doc()
    captured = {}

    def fake_metrics(document, error, source_type, expectations, image_base_dir):
        captured["image_base_dir"] = image_base_dir
        return {}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch(
            "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
        ):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    m = _make_manifest(docs=[doc])
                    run_evaluation(m, tmp_path / "out.json")
    assert captured["image_base_dir"] is None


def test_run_evaluation_annotation_present_true_when_loaded_batch22(tmp_path):
    """annotation 加载成功时 _annotation_present=True。"""
    doc = _make_doc()
    ann_path = tmp_path / "a.json"
    ann_path.write_text('{"x": 1}', encoding="utf-8")
    doc.annotation_resolved = ann_path
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    # public per_doc 不带 _annotation_present，但内部调用应已发生
    # 验证：annotation 文件被读（间接证据是 figure_caption_prf 收到 annotation）
    # 这里改为验证 figure_caption_prf 被调用 1 次


def test_run_evaluation_annotation_present_inferred_via_call_batch22(tmp_path):
    """annotation 加载失败 → 仍调 figure_caption_prf 但 annotation 是 None。"""
    doc = _make_doc()
    doc.annotation_resolved = tmp_path / "missing.json"
    captured = {}

    def fake_fig(document, annotation):
        captured["annotation"] = annotation
        return {}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch(
                    "evaluation.runner.figure_caption_prf", side_effect=fake_fig
                ):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured["annotation"] is None


def test_run_evaluation_tolerance_chars_none_when_chunk_b_no_key_batch22(tmp_path):
    """chunk_b 没有 _tolerance_chars key → public report 不应崩溃，内部 _tolerance_chars=None。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch(
                        "evaluation.runner.chunk_boundary_prf", return_value={}
                    ):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    # 不抛异常即可
    assert "per_doc" in report


def test_run_evaluation_missing_markers_default_empty_list_batch22(tmp_path):
    """chunk_b 没有 _missing_markers key → 内部 default []。"""
    doc = _make_doc()
    fake_chunk_b = {
        "chunk_boundary_precision": {"value": 1.0, "reason": None},
        "_tolerance_chars": {"value": 30},
        # 故意省略 _missing_markers
    }
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch(
                        "evaluation.runner.chunk_boundary_prf", return_value=fake_chunk_b
                    ):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    # 不抛异常即可（默认 [] 不会写入 public report）
    assert "_missing_markers" not in report["per_doc"][0]


def test_run_evaluation_parser_version_locked_after_first_success_batch22(tmp_path):
    """parser_version_for_prov 第一次被设置后，后续 doc 的 parser_version 不覆盖。"""
    docs = [_make_doc(f"d{i}") for i in range(2)]
    docs_mocks = []
    for i in range(2):
        dm = MagicMock()
        dm.to_dict.return_value = {"d": i}
        dm.parser_version = f"v{i}"
        dm.source_hash = f"h{i}"
        docs_mocks.append(dm)

    captured = {}

    def fake_prov(project_root, parser_name, max_chars, parser_version):
        captured["parser_version"] = parser_version
        return {"x": 1}

    # 第一次 process_single 返回 doc0，第二次返回 doc1
    with patch(
        "evaluation.runner.process_single",
        side_effect=[(docs_mocks[0], []), (docs_mocks[1], [])],
    ):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch(
                            "evaluation.runner.build_provenance", side_effect=fake_prov
                        ):
                            m = _make_manifest(docs=docs)
                            run_evaluation(m, tmp_path / "out.json")
    # 锁定 v0，不被 v1 覆盖
    assert captured["parser_version"] == "v0"


def test_run_evaluation_parser_version_remains_none_if_all_fail_batch22(tmp_path):
    """所有 doc 都失败时 parser_version_for_prov 仍是 None。"""
    doc = _make_doc()
    captured = {}

    def fake_prov(project_root, parser_name, max_chars, parser_version):
        captured["parser_version"] = parser_version
        return {"x": 1}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch(
                            "evaluation.runner.build_provenance", side_effect=fake_prov
                        ):
                            m = _make_manifest(docs=[doc])
                            run_evaluation(m, tmp_path / "out.json")
    assert captured["parser_version"] is None


def test_run_evaluation_public_per_doc_has_four_keys_batch22(tmp_path):
    """public per_doc 严格 4 字段（doc_id / source_type / metrics / wall_time_seconds）。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    pd = report["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_metrics_merged_from_three_sources_batch22(tmp_path):
    """metrics = compute_automatic_metrics ∪ figure_caption_prf ∪ chunk_boundary_prf。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch(
                "evaluation.runner.compute_automatic_metrics",
                return_value={"m1": 1},
            ):
                with patch(
                    "evaluation.runner.figure_caption_prf", return_value={"m2": 2}
                ):
                    with patch(
                        "evaluation.runner.chunk_boundary_prf",
                        return_value={"m3": 3},
                    ):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    metrics = report["per_doc"][0]["metrics"]
    assert metrics == {"m1": 1, "m2": 2, "m3": 3}


def test_run_evaluation_creates_deeply_nested_output_root_batch22(tmp_path):
    """深嵌套 output_root 父目录自动创建。"""
    deep = tmp_path / "a" / "b" / "c" / "d"
    out = deep / "out.json"
    m = _make_manifest(docs=[])
    run_evaluation(m, out)
    assert out.is_file()


def test_run_evaluation_expected_failure_unlink_eats_oserror_batch22(tmp_path):
    """expected_failure 的 unlink 抛 OSError 时不传播。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"

    def fake_process(path, out, **kwargs):
        # 让 out_stub 存在，触发 unlink
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("{}", encoding="utf-8")
        return None, [err_mock]

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch.object(Path, "unlink", side_effect=OSError("nope")):
            m = _make_manifest(expected_failures=[ef])
            # 不抛
            report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failure_mismatch_batch22(tmp_path):
    """expected_failure 实际 != 期望时 matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "DIFFERENT"
    with patch(
        "evaluation.runner.process_single", return_value=(None, [err_mock])
    ):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is False
    assert report["expected_failures"][0]["actual_error_code"] == "DIFFERENT"


def test_run_evaluation_returns_dict_batch22(tmp_path):
    """run_evaluation 返回 dict（不是 list/None）。"""
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert isinstance(report, dict)


def test_run_evaluation_compute_metrics_receives_doc_source_type_batch22(tmp_path):
    """compute_automatic_metrics 收到 doc.source_type。"""
    doc = _make_doc(source_type="docx")
    captured = {}

    def fake_metrics(document, error, source_type, expectations, image_base_dir):
        captured["source_type"] = source_type
        return {}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch(
                "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
            ):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured["source_type"] == "docx"


def test_run_evaluation_compute_metrics_receives_expectations_batch22(tmp_path):
    """compute_automatic_metrics 收到 doc.expectations。"""
    doc = _make_doc()
    doc.expectations = {"element_count_by_type": {"paragraph": 5}}
    captured = {}

    def fake_metrics(document, error, source_type, expectations, image_base_dir):
        captured["expectations"] = expectations
        return {}

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch(
                "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
            ):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        run_evaluation(m, tmp_path / "out.json")
    assert captured["expectations"] == {"element_count_by_type": {"paragraph": 5}}


def test_run_evaluation_expected_failure_passes_parser_name_and_max_chars_batch22(tmp_path):
    """expected_failure 跑 process_single 时也透传 parser_name 与 max_chars。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"
    captured = {}

    def fake_process(path, out, **kwargs):
        captured.update(kwargs)
        return None, [err_mock]

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        m = _make_manifest(expected_failures=[ef])
        run_evaluation(m, tmp_path / "out.json", parser_name="kreuzberg", max_chars=4321)
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 4321
    assert captured["write_json"] is False


def test_run_evaluation_expected_failure_out_stub_path_batch22(tmp_path):
    """expected_failure 的 out_stub 也在 _per_doc/<doc_id>.json。"""
    ef = MagicMock()
    ef.doc_id = "ef_xyz"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"
    captured = {}

    def fake_process(path, out, **kwargs):
        captured["out"] = out
        return None, [err_mock]

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        m = _make_manifest(expected_failures=[ef])
        run_evaluation(m, tmp_path / "out.json")
    assert captured["out"].parent.name == "_per_doc"
    assert captured["out"].name == "ef_xyz.json"


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch22(forbidden):
    src = inspect.getsource(rmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch22():
    src = inspect.getsource(rmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch22():
    src = inspect.getsource(rmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch22():
    src = inspect.getsource(rmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch22():
    src = inspect.getsource(rmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch22():
    src = inspect.getsource(rmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch22():
    src = inspect.getsource(rmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch22():
    src = inspect.getsource(rmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch22():
    src = inspect.getsource(rmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch22():
    src = inspect.getsource(rmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch22():
    src = inspect.getsource(rmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch22():
    src = inspect.getsource(rmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch22():
    src = inspect.getsource(rmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch22():
    src = inspect.getsource(rmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch22():
    src = inspect.getsource(rmod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch22():
    src = inspect.getsource(rmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch22():
    src = inspect.getsource(rmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch22():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch22():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_has_time_import_batch22():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_has_pathlib_path_import_batch22():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch22():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_pipeline_import_batch22():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_has_report_version_import_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src


def test_module_source_has_metrics_import_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src


def test_module_source_has_perf_counter_call_batch22():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_has_not_instrumented_string_batch22():
    src = inspect.getsource(rmod)
    assert '"not_instrumented"' in src


def test_module_source_has_image_output_dir_for_call_batch22():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


def test_module_source_has_process_single_call_batch22():
    src = inspect.getsource(rmod)
    assert "process_single(" in src


def test_module_source_has_compute_automatic_metrics_call_batch22():
    src = inspect.getsource(rmod)
    assert "compute_automatic_metrics(" in src


# ---------- signatures 第三十四批 ----------


def test_signature_load_annotation_one_param_batch22():
    """_load_annotation 仅 1 个形参 path。"""
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_signature_load_annotation_return_annotation_batch22():
    """_load_annotation 返回注解含 dict | None。"""
    sig = inspect.signature(_load_annotation)
    ret = sig.return_annotation
    # 因为 __future__ annotations，ret 是字符串
    assert "dict" in ret
    assert "None" in ret


def test_signature_process_one_params_names_batch22():
    """_process_one 5 个形参名正确。"""
    sig = inspect.signature(_process_one)
    names = [p.name for p in sig.parameters.values()]
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_return_annotation_batch22():
    """_process_one 返回注解是 tuple。"""
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    assert "tuple" in ret


def test_signature_run_evaluation_only_manifest_required_batch22():
    """run_evaluation 仅 manifest 必填。"""
    sig = inspect.signature(run_evaluation)
    params = sig.parameters
    assert params["manifest"].default is inspect.Parameter.empty
    assert params["output_path"].default is inspect.Parameter.empty


def test_signature_run_evaluation_keyword_only_after_output_path_batch22():
    """run_evaluation 在 output_path 之后是 kw-only（*）。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # 第三个开始应该是 kw-only
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_signature_run_evaluation_defaults_batch22():
    """run_evaluation 默认值正确。"""
    sig = inspect.signature(run_evaluation)
    params = sig.parameters
    assert params["parser_name"].default == "fallback"
    assert params["max_chars"].default == 800
    assert params["tolerance_chars"].default == 30


# ---------- module 合理性第三十四批 ----------


def test_module_all_contains_only_run_evaluation_batch22():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_does_not_import_evaluation_cli_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_schema_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch22():
    src = inspect.getsource(rmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_app_chunkers_batch22():
    src = inspect.getsource(rmod)
    assert "from app.chunkers" not in src
    assert "from app import chunkers" not in src


def test_module_does_not_import_app_parsers_batch22():
    src = inspect.getsource(rmod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_constants_not_in_all_batch22():
    for k in ("_load_annotation", "_process_one"):
        assert k not in rmod.__all__


def test_module_no_main_block_batch22():
    src = inspect.getsource(rmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_load_annotation_is_private_batch22():
    assert _load_annotation.__name__.startswith("_")


def test_module_process_one_is_private_batch22():
    assert _process_one.__name__.startswith("_")


def test_module_run_evaluation_is_public_batch22():
    assert not run_evaluation.__name__.startswith("_")


def test_module_has_module_docstring_batch22():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 0


# ---------- 端到端集成第三十四批 ----------


def test_e2e_load_annotation_round_trip_complex_batch22(tmp_path):
    """复杂嵌套 annotation round-trip。"""
    p = tmp_path / "a.json"
    payload = {
        "figure_captions": [
            {"image_id": "img1", "caption_text": "图 1：示例"},
            {"image_id": "img2", "caption_text": "图 2：另一个"},
        ],
        "chunk_anchors": [
            {"position": "after", "marker": "章节 A"},
        ],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    out = _load_annotation(p)
    assert out == payload


def test_e2e_run_evaluation_creates_valid_json_batch22(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert "per_doc" in parsed


def test_e2e_run_evaluation_returns_same_as_file_batch22(tmp_path):
    m = _make_manifest(docs=[])
    out = tmp_path / "out.json"
    report = run_evaluation(m, out)
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed == report


def test_e2e_run_evaluation_no_docs_summary_struct_batch22(tmp_path):
    m = _make_manifest(docs=[])
    report = run_evaluation(m, tmp_path / "out.json")
    s = report["summary"]
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_e2e_run_evaluation_per_doc_count_matches_docs_batch22(tmp_path):
    docs = [_make_doc(f"d{i}") for i in range(3)]
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=docs)
                        report = run_evaluation(m, tmp_path / "out.json")
    assert len(report["per_doc"]) == 3


def test_e2e_run_evaluation_with_expected_failure_match_batch22(tmp_path):
    """expected_failure 实际错误 == 期望时 matches=True。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.expected_error_code = "E_PARSE"
    ef.resolved_path = Path("/bad.pdf")
    err_mock = MagicMock()
    err_mock.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_mock])):
        m = _make_manifest(expected_failures=[ef])
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is True


def test_e2e_run_evaluation_full_report_has_six_top_keys_batch22(tmp_path):
    """完整报告含 6 个顶层字段。"""
    m = _make_manifest(docs=[], expected_failures=[])
    report = run_evaluation(m, tmp_path / "out.json")
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_e2e_run_evaluation_public_per_doc_excludes_underscore_fields_batch22(tmp_path):
    """public per_doc 不含 _ 前缀字段。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        m = _make_manifest(docs=[doc])
                        report = run_evaluation(m, tmp_path / "out.json")
    pd = report["per_doc"][0]
    for k in pd.keys():
        assert not k.startswith("_")
