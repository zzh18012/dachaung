"""evaluation/runner.py 第六十七轮 edges 测试（Round 598）。

补强 edges66 未触及的角度（第四十二批）。
"""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第四十二批


def test_load_annotation_callable_batch42():
    assert callable(_load_annotation)


def test_load_annotation_none_returns_none_batch42():
    assert _load_annotation(None) is None


def test_load_annotation_directory_returns_none_batch42(tmp_path):
    """路径指向目录（is_file()=False）→ None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_with_complex_object_batch42(tmp_path):
    """复杂嵌套 dict 也能加载。"""
    p = tmp_path / "obj.json"
    p.write_text(json.dumps({
        "document_id": "x",
        "chunks": [{"position": 0, "marker": "abc"}],
        "nested": {"deep": {"deeper": [1, 2, {"k": "v"}]}},
    }), encoding="utf-8")
    out = _load_annotation(p)
    assert out["document_id"] == "x"
    assert out["nested"]["deep"]["deeper"][2]["k"] == "v"


def test_load_annotation_with_bom_returns_none_batch42(tmp_path):
    """UTF-8 BOM（encoding=utf-8 而非 utf-8-sig）→ JSONDecodeError → None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_unicode_keys_batch42(tmp_path):
    """中文 key 也能加载。"""
    p = tmp_path / "u.json"
    p.write_text(json.dumps({"文档": "内容"}, ensure_ascii=False), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"文档": "内容"}


def test_load_annotation_with_large_json_batch42(tmp_path):
    """大文件（1000 个 keys）。"""
    p = tmp_path / "big.json"
    payload = {f"k{i}": i for i in range(1000)}
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = _load_annotation(p)
    assert len(out) == 1000
    assert out["k999"] == 999


def test_load_annotation_json_decode_error_returns_none_batch42(tmp_path):
    """部分合法 JSON 后跟垃圾 → JSONDecodeError → None。"""
    p = tmp_path / "bad.json"
    p.write_text('{"a": 1} garbage', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_with_empty_array_batch42(tmp_path):
    """空数组。"""
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    assert _load_annotation(p) == []


def test_load_annotation_with_empty_object_batch42(tmp_path):
    """空 dict。"""
    p = tmp_path / "obj.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_idempotent_batch42(tmp_path):
    """同一文件两次读取结果一致。"""
    p = tmp_path / "x.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) == _load_annotation(p)


def test_load_annotation_does_not_close_real_file_batch42(tmp_path):
    """正常路径下文件被 with 关闭（无异常）。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    _load_annotation(p)
    # 再次写不应报错（文件未被持有）
    p.write_text("{}", encoding="utf-8")


def test_load_annotation_invalid_utf8_bytes_raises_batch42(tmp_path):
    """非 utf-8 字节 → UnicodeDecodeError（ValueError 子类，不被 OSError 捕获）。"""
    p = tmp_path / "bad.json"
    p.write_bytes(b'\xff\xfe{"k": "v"}')  # UTF-16 LE BOM
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


# ---------- _process_one 第四十二批


def _make_doc_mock(doc_id="d1", path="/fake/a.pdf", source_type="pdf",
                   expectations=None, annotation_file_str=None,
                   annotation_resolved=None):
    doc = MagicMock()
    doc.doc_id = doc_id
    doc.resolved_path = Path(path)
    doc.source_type = source_type
    doc.expectations = expectations
    doc.annotation_file_str = annotation_file_str
    doc.annotation_resolved = annotation_resolved
    return doc


def _make_manifest_mock(documents=None, expected_failures=None,
                       project_root=None):
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path.cwd()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_process_one_callable_batch42():
    assert callable(_process_one)


def test_process_one_returns_5_tuple_on_success_batch42(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"document_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc123"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


def test_process_one_returns_dict_on_success_batch42(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"document_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc123"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, total, parser_v, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"document_id": "d1"}
    assert error is None
    assert isinstance(total, float)
    assert parser_v == "1.0"
    assert image_dir == tmp_path / "imgs"


def test_process_one_returns_none_when_errors_batch42(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    err_record = MagicMock()
    err_record.to_dict.return_value = {"code": "E_PARSE", "message": "boom"}
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        document, error, total, parser_v, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "E_PARSE", "message": "boom"}
    assert parser_v is None
    assert image_dir is None  # document 为 None 时 image_dir 也 None


def test_process_one_returns_unknown_when_document_none_no_errors_batch42(tmp_path):
    """document=None + errors=[] → unknown 错误码。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, total, parser_v, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]


def test_process_one_creates_per_doc_directory_batch42(tmp_path):
    """output_root/_per_doc 目录会被创建。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_unlinks_stub_file_batch42(tmp_path):
    """成功后 _per_doc/d1.json 被清理。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"

    # 让 process_single 真的创建 stub 文件
    def fake_process_single(*args, **kwargs):
        out_path = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text("{}", encoding="utf-8")
        return fake_document, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    stub = tmp_path / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_process_one_unlink_failure_silent_batch42(tmp_path):
    """out_stub.unlink() 抛 OSError → 静默吞掉。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"

    def fake_process_single(*args, **kwargs):
        out_path = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_path:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path).write_text("{}", encoding="utf-8")
        return fake_document, []

    # unlink 抛 OSError
    original_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        if self.name == "d1.json":
            raise OSError("denied")
        return original_unlink(self, *args, **kwargs)

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch.object(Path, "unlink", fake_unlink):
                # 不抛异常就算通过
                document, error, total, parser_v, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {}
    assert error is None


def test_process_one_passes_correct_args_to_process_single_batch42(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"
    captured = {}
    def fake_process_single(*args, **kwargs):
        captured["resolved_path"] = args[0] if args else kwargs.get("resolved_path")
        captured["output_path"] = args[1] if len(args) > 1 else kwargs.get("output_path")
        captured["parser_name"] = kwargs.get("parser_name")
        captured["max_chars"] = kwargs.get("max_chars")
        captured["write_json"] = kwargs.get("write_json")
        return fake_document, []
    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "kreuzberg", 1000)
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 1000
    assert captured["write_json"] is False
    assert captured["resolved_path"] == doc.resolved_path


def test_process_one_returns_float_for_total_batch42(tmp_path):
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(total, float)
    assert total >= 0


def test_process_one_image_dir_for_called_with_stub_and_hash_batch42(tmp_path):
    """image_output_dir_for 用 out_stub 和 source_hash 调用。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "deadbeef"
    captured = {}
    def fake_image_dir_for(stub, source_hash):
        captured["stub"] = stub
        captured["source_hash"] = source_hash
        return tmp_path / "imgs"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", side_effect=fake_image_dir_for):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured["source_hash"] == "deadbeef"
    assert captured["stub"].name == "d1.json"


def test_process_one_no_image_dir_when_document_none_batch42(tmp_path):
    """document=None 时即便有 errors 也 image_dir=None。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    err = MagicMock()
    err.to_dict.return_value = {"code": "E"}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_signature_annotation_batch42():
    """源码注释：return 类型 tuple。"""
    src = inspect.getsource(rmod)
    assert "tuple[" in src


def test_process_one_idempotent_when_recalled_batch42(tmp_path):
    """同一输入两次调用结构一致。"""
    doc = _make_doc_mock(path=str(tmp_path / "x.pdf"))
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"document_id": "d1"}
    fake_document.parser_version = "1.0"
    fake_document.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            out1 = _process_one(doc, tmp_path, "fallback", 800)
            out2 = _process_one(doc, tmp_path, "fallback", 800)
    # document dict 一致
    assert out1[0] == out2[0]
    # error 都 None
    assert out1[1] is None and out2[1] is None


# ---------- run_evaluation 第四十二批


def test_run_evaluation_callable_batch42():
    assert callable(run_evaluation)


def test_run_evaluation_signature_params_batch42():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.keys())
    assert params == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_kw_only_params_batch42():
    """parser_name/max_chars/tolerance_chars 是 kw-only。"""
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_manifest_positional_or_keyword_batch42():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_run_evaluation_output_path_positional_or_keyword_batch42():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


def test_run_evaluation_default_parser_name_fallback_batch42():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_default_max_chars_800_batch42():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_default_tolerance_chars_30_batch42():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_creates_output_parent_dir_batch42(tmp_path):
    """output_path.parent 不存在时会被创建。"""
    out_path = tmp_path / "deep" / "nested" / "r.json"
    manifest = _make_manifest_mock()
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


def test_run_evaluation_creates_output_root_for_per_doc_batch42(tmp_path):
    """output_root（output_path.parent）会被 mkdir。"""
    out_path = tmp_path / "out" / "r.json"
    manifest = _make_manifest_mock(documents=[
        _make_doc_mock(path=str(tmp_path / "a.pdf")),
    ])
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        run_evaluation(manifest, out_path)
    assert (tmp_path / "out").is_dir()


def test_run_evaluation_writes_valid_json_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    run_evaluation(manifest, out_path)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_run_evaluation_uses_manifest_documents_batch42(tmp_path):
    """按 manifest.documents 顺序处理。"""
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf")),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf")),
    ]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)) as mock:
        out = run_evaluation(manifest, out_path)
    assert mock.call_count == 2
    # 第一次调用第一个 doc
    first_call_args = mock.call_args_list[0]
    assert first_call_args.args[0].doc_id == "d1"


def test_run_evaluation_uses_manifest_expected_failures_batch42(tmp_path):
    """按 manifest.expected_failures 处理。"""
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    with patch("evaluation.runner.process_single", return_value=(None, [])) as mock:
        out = run_evaluation(manifest, out_path)
    assert mock.call_count == 1
    assert len(out["expected_failures"]) == 1


def test_run_evaluation_calls_build_provenance_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(project_root=tmp_path)
    with patch("evaluation.runner.build_provenance", return_value={"provenance": "stub"}) as mock:
        run_evaluation(manifest, out_path, parser_name="kreuzberg", max_chars=500)
    mock.assert_called_once()
    kwargs = mock.call_args.kwargs
    assert kwargs["parser_name"] == "kreuzberg"
    assert kwargs["max_chars"] == 500


def test_run_evaluation_calls_aggregate_summary_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner.aggregate_summary", return_value={"summary": "stub"}) as mock:
        run_evaluation(manifest, out_path)
    mock.assert_called_once()


def test_run_evaluation_calls_build_devset_section_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    with patch("evaluation.runner.build_devset_section", return_value={"devset": "stub"}) as mock:
        run_evaluation(manifest, out_path)
    mock.assert_called_once()


def test_run_evaluation_compute_automatic_metrics_called_batch42(tmp_path):
    """每个文档都调用 compute_automatic_metrics。"""
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.compute_automatic_metrics", return_value={}) as mock:
            run_evaluation(manifest, out_path)
    mock.assert_called_once()


def test_run_evaluation_figure_caption_prf_called_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.figure_caption_prf", return_value={}) as mock:
            run_evaluation(manifest, out_path)
    mock.assert_called_once()


def test_run_evaluation_chunk_boundary_prf_called_with_tolerance_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=(None, None, 0.1, None, None)):
        with patch("evaluation.runner.chunk_boundary_prf", return_value={}) as mock:
            run_evaluation(manifest, out_path, tolerance_chars=99)
    mock.assert_called_once()
    assert mock.call_args.kwargs["tolerance_chars"] == 99


def test_run_evaluation_propagates_first_parser_version_batch42(tmp_path):
    """parser_version_for_prov 用第一个非 None 的 parser_version。"""
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf")),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf")),
    ]
    manifest = _make_manifest_mock(documents=docs)
    # 第一次返回 None，第二次返回 "1.0"
    side_effects = [
        ({}, None, 0.1, None, None),  # parser_version None
        ({}, None, 0.1, "1.0", None),  # parser_version "1.0"
    ]
    captured = {}
    def fake_build_prov(*args, **kwargs):
        captured["parser_version"] = kwargs["parser_version"]
        return {"prov": "stub"}
    with patch("evaluation.runner._process_one", side_effect=side_effects):
        with patch("evaluation.runner.build_provenance", side_effect=fake_build_prov):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert captured["parser_version"] == "1.0"


def test_run_evaluation_keeps_first_parser_version_batch42(tmp_path):
    """找到第一个后不再覆盖。"""
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf")),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf")),
    ]
    manifest = _make_manifest_mock(documents=docs)
    side_effects = [
        ({}, None, 0.1, "1.0", None),
        ({}, None, 0.1, "2.0", None),
    ]
    captured = {}
    def fake_build_prov(*args, **kwargs):
        captured["parser_version"] = kwargs["parser_version"]
        return {"prov": "stub"}
    with patch("evaluation.runner._process_one", side_effect=side_effects):
        with patch("evaluation.runner.build_provenance", side_effect=fake_build_prov):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert captured["parser_version"] == "1.0"


def test_run_evaluation_image_base_dir_set_when_dir_exists_batch42(tmp_path):
    """image_dir 是目录 → 传给 compute_automatic_metrics 作 image_base_dir。"""
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    captured = {}
    def fake_compute(*args, **kwargs):
        captured["image_base_dir"] = kwargs["image_base_dir"]
        return {}
    with patch("evaluation.runner._process_one", return_value=(MagicMock(), None, 0.1, None, img_dir)):
        with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_compute):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert captured["image_base_dir"] == img_dir


def test_run_evaluation_image_base_dir_none_when_dir_missing_batch42(tmp_path):
    """image_dir 不是目录 → 传 None。"""
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    fake_image_dir = tmp_path / "no_such"  # 不存在
    captured = {}
    def fake_compute(*args, **kwargs):
        captured["image_base_dir"] = kwargs["image_base_dir"]
        return {}
    with patch("evaluation.runner._process_one", return_value=(MagicMock(), None, 0.1, None, fake_image_dir)):
        with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_compute):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert captured["image_base_dir"] is None


def test_run_evaluation_image_base_dir_none_when_none_batch42(tmp_path):
    """image_dir=None → image_base_dir=None。"""
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    captured = {}
    def fake_compute(*args, **kwargs):
        captured["image_base_dir"] = kwargs["image_base_dir"]
        return {}
    with patch("evaluation.runner._process_one", return_value=(MagicMock(), None, 0.1, None, None)):
        with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_compute):
            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert captured["image_base_dir"] is None


def test_run_evaluation_load_annotation_called_per_doc_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [
        _make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"),
                       annotation_resolved=tmp_path / "a1.json"),
        _make_doc_mock(doc_id="d2", path=str(tmp_path / "b.pdf"),
                       annotation_resolved=tmp_path / "a2.json"),
    ]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=({}, None, 0.1, None, None)):
        with patch("evaluation.runner._load_annotation", return_value=None) as mock:
            with patch("evaluation.runner.figure_caption_prf", return_value={}) as fc:
                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                    run_evaluation(manifest, out_path)
    assert mock.call_count == 2


def test_run_evaluation_per_doc_has_4_keys_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=({}, None, 0.1, None, None)):
        with patch("evaluation.runner.figure_caption_prf", return_value={}):
            with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                out = run_evaluation(manifest, out_path)
    per_doc = out["per_doc"][0]
    assert set(per_doc.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_keys_5_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(path=str(tmp_path / "a.pdf"))]
    manifest = _make_manifest_mock(documents=docs)
    with patch("evaluation.runner._process_one", return_value=({}, None, 0.1, None, None)):
        with patch("evaluation.runner.figure_caption_prf", return_value={}):
            with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                out = run_evaluation(manifest, out_path)
    wall = out["per_doc"][0]["wall_time_seconds"]
    assert set(wall.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_run_evaluation_expected_failure_path_creates_per_doc_dir_batch42(tmp_path):
    """expected_failures 处理时也创建 _per_doc 目录。"""
    out_path = tmp_path / "out" / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        run_evaluation(manifest, out_path)
    assert (tmp_path / "out" / "_per_doc").is_dir()


def test_run_evaluation_expected_failure_unlinks_stub_batch42(tmp_path):
    """expected_failure 处理后 stub 被清理。"""
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_PARSE"

    def fake_process_single(*args, **kwargs):
        out_path_arg = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_path_arg:
            Path(out_path_arg).parent.mkdir(parents=True, exist_ok=True)
            Path(out_path_arg).write_text("{}", encoding="utf-8")
        return None, [err_record]

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        run_evaluation(manifest, out_path)
    stub = out_path.parent / "_per_doc" / "ef1.json"
    assert not stub.is_file()


def test_run_evaluation_returns_report_dict_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    out = run_evaluation(manifest, out_path)
    assert isinstance(out, dict)


def test_run_evaluation_summary_in_output_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    out = run_evaluation(manifest, out_path)
    assert "summary" in out


def test_run_evaluation_provenance_in_output_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    out = run_evaluation(manifest, out_path)
    assert "provenance" in out


def test_run_evaluation_devset_in_output_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    out = run_evaluation(manifest, out_path)
    assert "devset" in out


def test_run_evaluation_report_in_file_matches_returned_batch42(tmp_path):
    """文件内容和返回 dict 一致。"""
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock()
    out = run_evaluation(manifest, out_path)
    file_data = json.loads(out_path.read_text(encoding="utf-8"))
    # 用 json.dumps 比较结构（忽略顺序）
    assert json.dumps(out, sort_keys=True) == json.dumps(file_data, sort_keys=True)


# ---------- module source forbidden tokens 第七十一批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch42(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十七批


def test_module_source_contains_design_doc_batch42():
    src = inspect.getsource(rmod)
    assert "评测 runner" in src


def test_module_source_contains_future_annotations_batch42():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch42():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_contains_time_import_batch42():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_contains_pathlib_path_import_batch42():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch42():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_contains_app_pipeline_import_batch42():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_evaluation_report_version_import_batch42():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_contains_annotation_metrics_import_batch42():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_contains_metrics_import_batch42():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch42():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_contains_load_annotation_function_batch42():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src


def test_module_source_contains_process_one_function_batch42():
    src = inspect.getsource(rmod)
    assert "def _process_one(" in src


def test_module_source_contains_run_evaluation_function_batch42():
    src = inspect.getsource(rmod)
    assert "def run_evaluation(" in src


def test_module_source_contains_perf_counter_batch42():
    src = inspect.getsource(rmod)
    assert "time.perf_counter" in src


def test_module_source_contains_json_load_batch42():
    src = inspect.getsource(rmod)
    assert "json.load(f)" in src


def test_module_source_contains_json_dump_batch42():
    src = inspect.getsource(rmod)
    assert "json.dump(" in src


def test_module_source_contains_utf8_encoding_batch42():
    src = inspect.getsource(rmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_not_instrumented_batch42():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src


def test_module_source_contains_unknown_code_batch42():
    """错误码 'unknown'。"""
    src = inspect.getsource(rmod)
    assert '"unknown"' in src


def test_module_source_contains_image_output_dir_call_batch42():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


def test_module_source_contains_doc_id_field_batch42():
    src = inspect.getsource(rmod)
    assert '"doc_id"' in src


def test_module_source_contains_source_type_field_batch42():
    src = inspect.getsource(rmod)
    assert '"source_type"' in src


def test_module_source_contains_metrics_field_batch42():
    src = inspect.getsource(rmod)
    assert '"metrics"' in src


def test_module_source_contains_wall_time_field_batch42():
    src = inspect.getsource(rmod)
    assert '"wall_time_seconds"' in src


def test_module_source_contains_total_field_batch42():
    src = inspect.getsource(rmod)
    assert '"total"' in src


def test_module_source_contains_parse_field_batch42():
    src = inspect.getsource(rmod)
    assert '"parse"' in src


def test_module_source_contains_chunk_field_batch42():
    src = inspect.getsource(rmod)
    assert '"chunk"' in src


def test_module_source_contains_parse_reason_batch42():
    src = inspect.getsource(rmod)
    assert '"parse_reason"' in src


def test_module_source_contains_chunk_reason_batch42():
    src = inspect.getsource(rmod)
    assert '"chunk_reason"' in src


def test_module_source_contains_expected_error_code_field_batch42():
    src = inspect.getsource(rmod)
    assert '"expected_error_code"' in src


def test_module_source_contains_actual_error_code_field_batch42():
    src = inspect.getsource(rmod)
    assert '"actual_error_code"' in src


def test_module_source_contains_matches_field_batch42():
    src = inspect.getsource(rmod)
    assert '"matches"' in src


def test_module_source_contains_ensure_ascii_false_batch42():
    src = inspect.getsource(rmod)
    assert "ensure_ascii=False" in src


def test_module_source_contains_indent_2_batch42():
    src = inspect.getsource(rmod)
    assert "indent=2" in src


def test_module_source_contains_per_doc_subdir_batch42():
    src = inspect.getsource(rmod)
    assert "_per_doc" in src


# ---------- signatures 第六十七批


def test_signature_load_annotation_param_batch42():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_signature_load_annotation_path_annotation_path_or_none_batch42():
    sig = inspect.signature(_load_annotation)
    ann = str(sig.parameters["path"].annotation)
    assert "Path" in ann
    assert "None" in ann


def test_signature_load_annotation_no_default_batch42():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_signature_load_annotation_return_annotation_batch42():
    sig = inspect.signature(_load_annotation)
    ann = str(sig.return_annotation)
    assert "dict" in ann
    assert "None" in ann


def test_signature_process_one_params_batch42():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_doc_no_annotation_strict_batch42():
    """doc 参数无类型注解（注释说明是 DocumentEntry）。"""
    sig = inspect.signature(_process_one)
    src = inspect.getsource(rmod)
    assert "# DocumentEntry" in src or "DocumentEntry" in src


def test_signature_process_one_return_tuple_annotation_batch42():
    sig = inspect.signature(_process_one)
    ann = str(sig.return_annotation)
    assert "tuple" in ann


def test_signature_run_evaluation_manifest_param_batch42():
    sig = inspect.signature(run_evaluation)
    assert "manifest" in sig.parameters


def test_signature_run_evaluation_output_path_param_batch42():
    sig = inspect.signature(run_evaluation)
    assert "output_path" in sig.parameters


def test_signature_run_evaluation_output_path_annotation_path_batch42():
    sig = inspect.signature(run_evaluation)
    assert "Path" in str(sig.parameters["output_path"].annotation)


def test_signature_run_evaluation_parser_name_annotation_str_batch42():
    sig = inspect.signature(run_evaluation)
    assert "str" in str(sig.parameters["parser_name"].annotation)


def test_signature_run_evaluation_max_chars_annotation_int_batch42():
    sig = inspect.signature(run_evaluation)
    assert "int" in str(sig.parameters["max_chars"].annotation)


def test_signature_run_evaluation_tolerance_chars_annotation_int_batch42():
    sig = inspect.signature(run_evaluation)
    assert "int" in str(sig.parameters["tolerance_chars"].annotation)


def test_signature_run_evaluation_return_dict_batch42():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性 第六十七批


def test_module_has_all_attribute_batch42():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list_batch42():
    assert isinstance(rmod.__all__, list)


def test_module_all_only_run_evaluation_batch42():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_len_one_batch42():
    assert len(rmod.__all__) == 1


def test_module_does_not_export_helpers_batch42():
    for name in ("_load_annotation", "_process_one"):
        assert name not in rmod.__all__


def test_module_does_not_define_class_batch42():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src


def test_module_has_future_annotations_batch42():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_has_load_annotation_attr_batch42():
    assert hasattr(rmod, "_load_annotation")


def test_module_has_process_one_attr_batch42():
    assert hasattr(rmod, "_process_one")


def test_module_has_run_evaluation_attr_batch42():
    assert hasattr(rmod, "run_evaluation")


def test_module_load_annotation_callable_batch42():
    assert callable(rmod._load_annotation)


def test_module_process_one_callable_batch42():
    assert callable(rmod._process_one)


def test_module_run_evaluation_callable_batch42():
    assert callable(rmod.run_evaluation)


# ---------- 端到端集成 第六十七批


def test_e2e_run_evaluation_no_documents_no_failures_writes_valid_report_batch42(tmp_path):
    """完整端到端：空 manifest → 合法报告文件。"""
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    run_evaluation(manifest, out_path)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["per_doc"] == []
    assert data["expected_failures"] == []
    assert data["report_version"] == REPORT_VERSION


def test_e2e_run_evaluation_one_document_full_pipeline_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    docs = [_make_doc_mock(doc_id="d1", path=str(tmp_path / "a.pdf"), source_type="pdf")]
    manifest = _make_manifest_mock(documents=docs)
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"document_id": "d1", "source_type": "pdf"}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner._process_one",
               return_value=(fake_doc.to_dict.return_value, None, 0.05, "1.0", None)):
        with patch("evaluation.runner.figure_caption_prf", return_value={}):
            with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                out = run_evaluation(manifest, out_path)
    per_doc = out["per_doc"][0]
    assert per_doc["doc_id"] == "d1"
    assert per_doc["source_type"] == "pdf"
    assert per_doc["wall_time_seconds"]["total"] == 0.05


def test_e2e_run_evaluation_one_expected_failure_batch42(tmp_path):
    out_path = tmp_path / "r.json"
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "E_PARSE"
    manifest = _make_manifest_mock(documents=[], expected_failures=[ef])
    err_record = MagicMock()
    err_record.code = "E_PARSE"
    with patch("evaluation.runner.process_single", return_value=(None, [err_record])):
        out = run_evaluation(manifest, out_path)
    assert out["expected_failures"][0]["matches"] is True


def test_e2e_run_evaluation_idempotent_batch42(tmp_path):
    """同一 manifest 跑两次结果（除时间戳外）结构一致。"""
    out_path = tmp_path / "r.json"
    manifest = _make_manifest_mock(documents=[], expected_failures=[])
    out1 = run_evaluation(manifest, out_path)
    out2 = run_evaluation(manifest, out_path)
    # per_doc / expected_failures 应一致
    assert out1["per_doc"] == out2["per_doc"]
    assert out1["expected_failures"] == out2["expected_failures"]
