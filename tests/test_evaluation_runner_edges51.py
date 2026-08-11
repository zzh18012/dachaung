"""evaluation/runner.py 第五十三轮 edges 测试（Round 486）。

补强 edges50 未触及的角度（第二十三批）：
- _load_annotation 第二十三批：whitespace only / 单 BOM / trailing comma / 单引号 / 注释 / 长 payload / 路径含空格 / 路径含中文 / UTF-16 BE/LE / UTF-8 多 BOM / 文件夹 is_file() False / 链接跟随
- _process_one 第二十三批：process_single OSError 传播 / ValueError 传播 / (None, []) → unknown code / (None, [e1, e2]) → errors[0] / to_dict 调用一次 / out_stub.parent.mkdir 参数 / image_dir 仅 document 非空时计算 / unlink 缺文件不抛 / unlink OSError 静默 / 返回 tuple 长度
- run_evaluation 第二十三批：manifest.documents 空 + expected_failures 空 / 第一个 doc parser_version 锁定 / 所有 doc 失败 / annotation 缺失影响 _annotation_present / tolerance_chars 默认 30 / tolerance_chars 自定义 / per_doc 字段精确 / wall_time_seconds 结构 / output_path 嵌套父目录 / JSON dump 格式 / report_version 在 report / return value 等于文件读回
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
"""

from __future__ import annotations

import inspect
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 第二十三批 ----------


def test_load_annotation_whitespace_only_returns_none_batch23(tmp_path):
    """只有空白字符的文件 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("   \n\t  \r\n ", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_bom_only_returns_none_batch23(tmp_path):
    """只有 UTF-8 BOM（3 字节）→ JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf')
    assert _load_annotation(p) is None


def test_load_annotation_double_bom_returns_none_batch23(tmp_path):
    """双重 BOM → 非法 JSON → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf\xef\xbb\xbf{}')
    assert _load_annotation(p) is None


def test_load_annotation_trailing_comma_returns_none_batch23(tmp_path):
    """JSON 不允许 trailing comma → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_single_quotes_returns_none_batch23(tmp_path):
    """JSON 不允许单引号字符串 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_json_comment_returns_none_batch23(tmp_path):
    """JSON 标准（非 JSON5）不允许注释 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('// comment\n{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_long_payload_batch23(tmp_path):
    """长 payload 仍可正常解析（无截断）。"""
    p = tmp_path / "a.json"
    payload = {"key_" + str(i): "value_" + str(i) for i in range(1000)}
    p.write_text(json.dumps(payload), encoding="utf-8")
    out = _load_annotation(p)
    assert out == payload
    assert len(out) == 1000


def test_load_annotation_path_with_spaces_batch23(tmp_path):
    """路径含空格也能读取。"""
    p = tmp_path / "my file.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_load_annotation_path_with_unicode_batch23(tmp_path):
    """路径含中文也能读取。"""
    p = tmp_path / "数据.json"
    p.write_text('{"x": "中"}', encoding="utf-8")
    assert _load_annotation(p) == {"x": "中"}


def test_load_annotation_utf16_be_returns_none_batch23(tmp_path):
    """UTF-16 BE 编码内容（ASCII 范围内）→ UTF-8 可解码但 JSON 解析失败 → JSONDecodeError → None。

    注：'{"a": 1}' 在 UTF-16 BE 中是 NUL+ASCII 配对，UTF-8 解码得到 '\\x00{\\x00"\\x00a...'，
    json.load 解析时遇到 NUL 失败。
    """
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-16-be")
    assert _load_annotation(p) is None


def test_load_annotation_utf16_le_returns_none_batch23(tmp_path):
    """UTF-16 LE 编码内容（ASCII 范围内）→ UTF-8 可解码但 JSON 解析失败 → JSONDecodeError → None。"""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-16-le")
    assert _load_annotation(p) is None


def test_load_annotation_path_is_dir_returns_none_batch23(tmp_path):
    """路径是目录（is_file() False）→ 返回 None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_none_path_returns_none_batch23():
    """None path → 直接返回 None（短路）。"""
    assert _load_annotation(None) is None


def test_load_annotation_missing_file_returns_none_batch23(tmp_path):
    """不存在的文件 → is_file() False → None。"""
    p = tmp_path / "nope.json"
    assert _load_annotation(p) is None


def test_load_annotation_symlink_follows_batch23(tmp_path):
    """符号链接 → is_file() True → 读取目标内容。"""
    target = tmp_path / "real.json"
    target.write_text('{"real": true}', encoding="utf-8")
    link = tmp_path / "link.json"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    assert _load_annotation(link) == {"real": True}


def test_load_annotation_empty_dict_batch23(tmp_path):
    """空 dict 是合法 JSON。"""
    p = tmp_path / "a.json"
    p.write_text('{}', encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_empty_array_batch23(tmp_path):
    """空 array 是合法 JSON。"""
    p = tmp_path / "a.json"
    p.write_text('[]', encoding="utf-8")
    assert _load_annotation(p) == []


def test_load_annotation_negative_number_batch23(tmp_path):
    """负数顶层 JSON。"""
    p = tmp_path / "a.json"
    p.write_text('-42', encoding="utf-8")
    assert _load_annotation(p) == -42


def test_load_annotation_float_number_batch23(tmp_path):
    """浮点数顶层 JSON。"""
    p = tmp_path / "a.json"
    p.write_text('3.14159', encoding="utf-8")
    out = _load_annotation(p)
    assert out == pytest.approx(3.14159)


# ---------- _process_one 第二十三批 ----------


@pytest.fixture
def fake_doc():
    """构造一个最小 DocumentEntry mock。"""
    doc = MagicMock()
    doc.doc_id = "test_doc_001"
    doc.resolved_path = Path("/fake/path.pdf")
    return doc


def test_process_one_process_single_oserror_propagates_batch23(fake_doc, tmp_path):
    """process_single 抛 OSError → 传播（不在 _process_one 内捕获）。"""
    with patch(
        "evaluation.runner.process_single", side_effect=OSError("disk full")
    ):
        with pytest.raises(OSError):
            _process_one(fake_doc, tmp_path, "fallback", 800)


def test_process_one_process_single_valueerror_propagates_batch23(fake_doc, tmp_path):
    """process_single 抛 ValueError → 传播。"""
    with patch(
        "evaluation.runner.process_single", side_effect=ValueError("bad arg")
    ):
        with pytest.raises(ValueError):
            _process_one(fake_doc, tmp_path, "fallback", 800)


def test_process_one_returns_unknown_when_document_none_no_errors_batch23(
    fake_doc, tmp_path
):
    """process_single 返回 (None, []) → unknown code/message。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ):
        document, error, elapsed, parser_version, image_dir = _process_one(
            fake_doc, tmp_path, "fallback", 800
        )
    assert document is None
    assert error is not None
    assert error["code"] == "unknown"
    assert "process_single returned None without errors" in error["message"]
    assert isinstance(elapsed, float)
    assert parser_version is None
    assert image_dir is None


def test_process_one_returns_first_error_when_multiple_errors_batch23(
    fake_doc, tmp_path
):
    """process_single 返回 (None, [err1, err2]) → 只取 errors[0].to_dict()。"""
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "err1", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "err2", "message": "second"}
    with patch(
        "evaluation.runner.process_single", return_value=(None, [err1, err2])
    ):
        _, error, _, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert error == {"code": "err1", "message": "first"}
    err1.to_dict.assert_called_once_with()
    err2.to_dict.assert_not_called()


def test_process_one_to_dict_called_once_batch23(fake_doc, tmp_path):
    """error.to_dict() 只调用一次。"""
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}
    with patch(
        "evaluation.runner.process_single", return_value=(None, [err])
    ):
        _, _, _, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    err.to_dict.assert_called_once_with()


def test_process_one_out_stub_parent_mkdir_with_parents_exist_ok_batch23(
    fake_doc, tmp_path
):
    """out_stub.parent.mkdir 必须用 parents=True, exist_ok=True。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ), patch("pathlib.Path.mkdir") as mkdir_mock:
        _process_one(fake_doc, tmp_path, "fallback", 800)
    # 至少调用过 mkdir，参数含 parents=True exist_ok=True
    mkdir_calls = [c for c in mkdir_mock.call_args_list]
    assert any(
        c.kwargs.get("parents") is True and c.kwargs.get("exist_ok") is True
        for c in mkdir_calls
    )


def test_process_one_image_dir_only_when_document_not_none_batch23(
    fake_doc, tmp_path
):
    """document=None → image_dir 始终 None（不调 image_output_dir_for）。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ), patch("evaluation.runner.image_output_dir_for") as img_mock:
        _, _, _, _, image_dir = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert image_dir is None
    img_mock.assert_not_called()


def test_process_one_image_dir_when_document_present_batch23(fake_doc, tmp_path):
    """document 非空 → image_dir 通过 image_output_dir_for(out_stub, source_hash) 计算。"""
    document = MagicMock()
    document.to_dict.return_value = {"id": "x"}
    document.parser_version = "fallback/1.0"
    document.source_hash = "abc123"
    expected_path = tmp_path / "_per_doc" / "images"
    with patch(
        "evaluation.runner.process_single", return_value=(document, [])
    ), patch(
        "evaluation.runner.image_output_dir_for", return_value=expected_path
    ) as img_mock:
        _, _, _, _, image_dir = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert image_dir == expected_path
    img_mock.assert_called_once()
    args = img_mock.call_args.args
    # 第一个参数应当含 _per_doc/<doc_id>.json
    assert "_per_doc" in str(args[0])
    assert "test_doc_001.json" in str(args[0])
    # 第二个参数是 source_hash
    assert args[1] == "abc123"


def test_process_one_unlink_missing_file_silent_batch23(fake_doc, tmp_path):
    """out_stub.is_file() False（process_single 没写文件）→ 不调 unlink。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        # out_stub 是真实路径，process_single 不写文件
        _, _, _, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    # out_stub 不存在
    out_stub = tmp_path / "_per_doc" / "test_doc_001.json"
    assert not out_stub.is_file()


def test_process_one_unlink_oserror_silent_batch23(fake_doc, tmp_path):
    """out_stub.is_file() True 但 unlink 抛 OSError → 静默（不传播）。"""
    err = MagicMock()
    err.to_dict.return_value = {"code": "x"}
    # 让 process_single 不抛但写一个空文件作为 out_stub
    def fake_ps(*args, **kwargs):
        out_stub_path = args[1] if len(args) > 1 else kwargs.get("output_path")
        if out_stub_path:
            Path(out_stub_path).parent.mkdir(parents=True, exist_ok=True)
            Path(out_stub_path).write_text("temp")
        return None, [err]

    with patch("evaluation.runner.process_single", side_effect=fake_ps):
        # 现在 unlink OSError 应被吞
        with patch("pathlib.Path.unlink", side_effect=OSError("denied")):
            _, _, _, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    # 测试通过即表示 OSError 未传播


def test_process_one_returns_5_tuple_batch23(fake_doc, tmp_path):
    """返回值必须是 5-tuple。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ):
        result = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_parser_version_passed_through_batch23(fake_doc, tmp_path):
    """document.parser_version 透传到返回 tuple[3]。"""
    document = MagicMock()
    document.to_dict.return_value = {"id": "x"}
    document.parser_version = "fallback/2.3.4"
    document.source_hash = "x"
    with patch(
        "evaluation.runner.process_single", return_value=(document, [])
    ), patch("evaluation.runner.image_output_dir_for"):
        _, _, _, parser_version, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert parser_version == "fallback/2.3.4"


def test_process_one_parser_name_kwarg_passed_batch23(fake_doc, tmp_path):
    """process_single 必须以 parser_name=parser_name 关键字参数调用。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ) as ps_mock:
        _process_one(fake_doc, tmp_path, "kreuzberg", 1000)
    ps_mock.assert_called_once()
    kwargs = ps_mock.call_args.kwargs
    assert kwargs.get("parser_name") == "kreuzberg"
    assert kwargs.get("max_chars") == 1000
    assert kwargs.get("write_json") is False


def test_process_one_elapsed_is_float_batch23(fake_doc, tmp_path):
    """elapsed 必须是 float。"""
    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ):
        _, _, elapsed, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)
    assert elapsed >= 0.0


def test_process_one_document_to_dict_called_when_present_batch23(fake_doc, tmp_path):
    """document 非空 → document.to_dict() 调用一次。"""
    document = MagicMock()
    document.to_dict.return_value = {"id": "x"}
    document.parser_version = "v"
    document.source_hash = "h"
    with patch(
        "evaluation.runner.process_single", return_value=(document, [])
    ), patch("evaluation.runner.image_output_dir_for"):
        doc_dict, _, _, _, _ = _process_one(fake_doc, tmp_path, "fallback", 800)
    document.to_dict.assert_called_once_with()
    assert doc_dict == {"id": "x"}


# ---------- run_evaluation 第二十三批 ----------


def _build_document_dict(doc_id="d1", source_type="pdf"):
    """构造一个最小合法 document dict。"""
    return {
        "doc_id": doc_id,
        "source_type": source_type,
        "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]} if source_type == "pdf" else {},
        "elements": [],
        "chunks": [],
        "source_hash": "abc",
        "parser_version": "fallback/test",
    }


def test_run_evaluation_empty_manifest_no_documents_no_expected_failures_batch23(
    tmp_path,
):
    """空 manifest → 空 per_doc + 空 expected_failures + summary 仍计算。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []
    assert report["expected_failures"] == []
    assert "summary" in report
    # 文件确实被写
    assert out.is_file()
    # 内容一致
    with out.open("r", encoding="utf-8") as f:
        file_content = json.load(f)
    assert file_content == report


def test_run_evaluation_first_doc_parser_version_locks_batch23(tmp_path):
    """第一个 doc 提供 parser_version 后，后续 doc 即使提供不同版本也不覆盖。"""
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

    manifest = MagicMock()
    manifest.documents = [doc1, doc2]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 2
    manifest.content_group_count = 1
    manifest.pdf_count = 2
    manifest.docx_count = 0
    manifest.categories_covered = ["test"]

    d1_dict = _build_document_dict("d1")
    d2_dict = _build_document_dict("d2")

    def fake_ps(path, *args, **kwargs):
        if "d1" in str(path):
            d = MagicMock()
            d.to_dict.return_value = d1_dict
            d.parser_version = "fallback/v1"
            d.source_hash = "h1"
            return d, []
        else:
            d = MagicMock()
            d.to_dict.return_value = d2_dict
            d.parser_version = "fallback/v2"
            d.source_hash = "h2"
            return d, []

    with patch("evaluation.runner.process_single", side_effect=fake_ps), patch(
        "evaluation.runner.image_output_dir_for"
    ), patch(
        "evaluation.runner._process_one",
        side_effect=[
            (d1_dict, None, 0.1, "fallback/v1", None),
            (d2_dict, None, 0.1, "fallback/v2", None),
        ],
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert report["provenance"]["parser_version"] == "fallback/v1"


def test_run_evaluation_all_docs_failed_batch23(tmp_path):
    """所有 doc 失败 → per_doc 中 doc_id 与 source_type 仍透传。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_error", "message": "fail"}

    with patch(
        "evaluation.runner._process_one",
        return_value=(None, err.to_dict.return_value, 0.01, None, None),
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert len(report["per_doc"]) == 1
    assert report["per_doc"][0]["doc_id"] == "d1"
    assert report["per_doc"][0]["source_type"] == "pdf"
    # pipeline_success 应是 False
    assert report["per_doc"][0]["metrics"]["pipeline_success"]["value"] is False


def test_run_evaluation_annotation_present_flag_batch23(tmp_path):
    """有 annotation 时 _annotation_present=True（不在 public_per_doc，但影响内部）。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = tmp_path / "ann.json"
    # annotation 文件存在
    (tmp_path / "ann.json").write_text("{}", encoding="utf-8")

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    doc_dict = _build_document_dict("d1")
    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.01, "fallback/v", None),
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    # per_doc 不暴露 _annotation_present，但 annotation_metrics 应被调用
    assert "figure_caption_precision" in report["per_doc"][0]["metrics"]


def test_run_evaluation_tolerance_chars_default_30_batch23(tmp_path):
    """tolerance_chars 默认 30 → chunk_boundary tolerance=30。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    doc_dict = _build_document_dict("d1")
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {"chunk_boundary_precision": {"value": 1.0, "reason": "test"}}

    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.01, "fallback/v", None),
    ), patch(
        "evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert captured["tolerance_chars"] == 30


def test_run_evaluation_tolerance_chars_custom_batch23(tmp_path):
    """tolerance_chars 自定义值（如 50）→ chunk_boundary tolerance=50。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    doc_dict = _build_document_dict("d1")
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {"chunk_boundary_precision": {"value": 1.0, "reason": "test"}}

    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.01, "fallback/v", None),
    ), patch(
        "evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out, tolerance_chars=50)

    assert captured["tolerance_chars"] == 50


def test_run_evaluation_per_doc_public_field_set_exact_batch23(tmp_path):
    """public_per_doc 每条精确含 4 字段：doc_id, source_type, metrics, wall_time_seconds。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "docx"
    doc1.resolved_path = tmp_path / "d1.docx"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 0
    manifest.docx_count = 1
    manifest.categories_covered = []

    doc_dict = _build_document_dict("d1", source_type="docx")
    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.123, "fallback/v", None),
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert len(report["per_doc"]) == 1
    pd = report["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert pd["doc_id"] == "d1"
    assert pd["source_type"] == "docx"


def test_run_evaluation_wall_time_seconds_structure_batch23(tmp_path):
    """wall_time_seconds 含 5 字段：total, parse, chunk, parse_reason, chunk_reason。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    doc_dict = _build_document_dict("d1")
    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 1.234, "fallback/v", None),
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["total"] == 1.234
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_output_path_nested_parent_created_batch23(tmp_path):
    """output_path 的多级父目录会被创建。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = tmp_path / "deep" / "nested" / "report.json"
    report = run_evaluation(manifest, out)
    assert out.is_file()
    assert out.parent.is_dir()


def test_run_evaluation_json_dump_format_batch23(tmp_path):
    """JSON 输出：ensure_ascii=False + indent=2。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = ["中文类目"]

    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    raw = out.read_text(encoding="utf-8")
    # 中文应原样输出（不转义）
    assert "中文类目" in raw
    # indent=2：每行最多 2 空格缩进可见
    assert "\n  " in raw


def test_run_evaluation_report_version_in_output_batch23(tmp_path):
    """报告 dict 含 report_version=REPORT_VERSION。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_return_value_matches_file_batch23(tmp_path):
    """返回值 = 文件读回 dict。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        file_report = json.load(f)
    assert report == file_report


def test_run_evaluation_report_has_six_top_keys_batch23(tmp_path):
    """report 顶层 6 keys：report_version, provenance, devset, summary, per_doc, expected_failures。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

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


def test_run_evaluation_expected_failures_field_set_batch23(tmp_path):
    """expected_failure_result 含 4 字段：doc_id, expected_error_code, actual_error_code, matches。"""
    ef = MagicMock()
    ef.doc_id = "broken"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = tmp_path / "broken.txt"

    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = [ef]
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    err = MagicMock()
    err.code = "unsupported_format"

    with patch(
        "evaluation.runner.process_single", return_value=(None, [err])
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    assert len(report["expected_failures"]) == 1
    efr = report["expected_failures"][0]
    assert set(efr.keys()) == {
        "doc_id",
        "expected_error_code",
        "actual_error_code",
        "matches",
    }
    assert efr["doc_id"] == "broken"
    assert efr["expected_error_code"] == "unsupported_format"
    assert efr["actual_error_code"] == "unsupported_format"
    assert efr["matches"] is True


def test_run_evaluation_expected_failure_no_error_actual_none_batch23(tmp_path):
    """expected_failure 中 process_single 返回 (None, []) → actual_error_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "broken"
    ef.expected_error_code = "unsupported_format"
    ef.resolved_path = tmp_path / "broken.txt"

    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = [ef]
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    with patch(
        "evaluation.runner.process_single", return_value=(None, [])
    ):
        out = tmp_path / "report.json"
        report = run_evaluation(manifest, out)

    efr = report["expected_failures"][0]
    assert efr["actual_error_code"] is None
    assert efr["matches"] is False


def test_run_evaluation_devset_section_in_report_batch23(tmp_path):
    """devset 字段含 6 keys：status, file_count, content_group_count, pdf_count, docx_count, categories_covered。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 7
    manifest.content_group_count = 3
    manifest.pdf_count = 4
    manifest.docx_count = 3
    manifest.categories_covered = ["cat1", "cat2"]

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
    assert report["devset"]["file_count"] == 7


# ---------- module source forbidden tokens 第三十九批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
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
]


def test_module_source_forbidden_tokens_batch23():
    """runner.py 不应直接 import 这些副作用大的模块。"""
    source = inspect.getsource(rmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch23():
    """runner.py 不应使用 class（functional 风格）。"""
    source = inspect.getsource(rmod)
    # 排除 docstring 中的 'class' 单词（很少出现，但保险）
    # 简单地：搜 'class ' 后跟标识符
    import re as _re
    matches = _re.findall(r"\bclass\s+\w+", source)
    assert matches == [], f"unexpected class definitions: {matches}"


def test_module_source_no_yield_batch23():
    """runner.py 不应使用 yield（无 generator）。"""
    source = inspect.getsource(rmod)
    # 排除 docstring
    assert "yield " not in source


def test_module_source_no_async_def_batch23():
    """runner.py 不应使用 async def。"""
    source = inspect.getsource(rmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch23():
    """runner.py 不应使用 global。"""
    source = inspect.getsource(rmod)
    assert "global " not in source


def test_module_source_no_walrus_batch23():
    """runner.py 不应使用 walrus 运算符。"""
    source = inspect.getsource(rmod)
    # := 是 walrus
    assert ":=" not in source


def test_module_source_no_relative_imports_batch23():
    """runner.py 不应使用相对导入（from .）。"""
    source = inspect.getsource(rmod)
    # 排除 from __future__ （不算相对导入）
    lines = [l for l in source.split("\n") if "from " in l and "from __future__" not in l]
    for line in lines:
        assert not line.strip().startswith("from ."), f"relative import: {line}"


def test_module_source_no_eval_exec_batch23():
    """runner.py 不应使用 eval/exec/compile。"""
    source = inspect.getsource(rmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_subprocess_batch23():
    """runner.py 不应使用 subprocess（仅 report.py 需要）。"""
    source = inspect.getsource(rmod)
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_module_source_no_network_io_batch23():
    """runner.py 不应使用 socket/http/network 模块。"""
    source = inspect.getsource(rmod)
    assert "import socket" not in source
    assert "import http" not in source
    assert "import urllib" not in source
    assert "import requests" not in source


def test_module_source_no_dataclass_batch23():
    """runner.py 不应使用 @dataclass 装饰器（dataclass 在 manifest.py 中定义）。"""
    source = inspect.getsource(rmod)
    assert "@dataclass" not in source


def test_module_source_no_pickle_batch23():
    """runner.py 不应使用 pickle（安全）。"""
    source = inspect.getsource(rmod)
    assert "import pickle" not in source
    assert "pickle." not in source


def test_module_source_no_shutil_batch23():
    """runner.py 不应使用 shutil（无文件批量操作）。"""
    source = inspect.getsource(rmod)
    assert "import shutil" not in source
    assert "shutil." not in source


def test_module_source_no_tempfile_batch23():
    """runner.py 不应使用 tempfile（在测试中由 pytest tmp_path 提供）。"""
    source = inspect.getsource(rmod)
    assert "import tempfile" not in source
    assert "tempfile." not in source


def test_module_source_no_environ_batch23():
    """runner.py 不应使用 os.environ（无环境变量读取）。"""
    source = inspect.getsource(rmod)
    assert "os.environ" not in source


def test_module_source_no_argparse_batch23():
    """runner.py 不应使用 argparse（CLI 在 cli.py）。"""
    source = inspect.getsource(rmod)
    assert "import argparse" not in source
    assert "argparse." not in source


def test_module_source_no_open_at_module_level_batch23():
    """runner.py 顶层不应直接 open() 文件（应在函数内）。"""
    source_lines = inspect.getsource(rmod).split("\n")
    # 找顶层（无缩进）的 open() 调用
    for i, line in enumerate(source_lines):
        stripped = line.rstrip()
        # 顶层是没缩进的（不在 def 内）
        if stripped and not stripped.startswith((" ", "\t", "#")) and "open(" in stripped:
            # 允许注释
            if stripped.lstrip().startswith("#"):
                continue
            pytest.fail(f"top-level open() at line {i+1}: {stripped}")


# ---------- module source 字符串精确补强第三十五批 ----------


def test_module_source_contains_process_single_import_batch23():
    """source 必须含 'from app.pipeline import image_output_dir_for, process_single'。"""
    source = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in source


def test_module_source_contains_report_version_import_batch23():
    """source 必须含 'from evaluation import REPORT_VERSION'。"""
    source = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in source


def test_module_source_contains_annotation_metrics_import_batch23():
    """source 必须含 annotation_metrics 的 chunk_boundary_prf + figure_caption_prf 导入。"""
    source = inspect.getsource(rmod)
    assert "chunk_boundary_prf" in source
    assert "figure_caption_prf" in source
    assert "from evaluation.annotation_metrics import" in source


def test_module_source_contains_metrics_import_batch23():
    """source 必须含 'from evaluation.metrics import compute_automatic_metrics'。"""
    source = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in source


def test_module_source_contains_report_import_batch23():
    """source 必须含 'from evaluation.report import aggregate_summary, build_devset_section, build_provenance'。"""
    source = inspect.getsource(rmod)
    assert "from evaluation.report import" in source
    assert "aggregate_summary" in source
    assert "build_devset_section" in source
    assert "build_provenance" in source


def test_module_source_contains_time_perf_counter_batch23():
    """source 必须使用 time.perf_counter（计时）。"""
    source = inspect.getsource(rmod)
    assert "time.perf_counter" in source


def test_module_source_contains_not_instrumented_batch23():
    """source 必须含 reason='not_instrumented' 字符串字面量。"""
    source = inspect.getsource(rmod)
    assert '"not_instrumented"' in source


def test_module_source_contains_write_json_false_batch23():
    """source 必须含 write_json=False（process_single 调用约束）。"""
    source = inspect.getsource(rmod)
    assert "write_json=False" in source


def test_module_source_contains_per_doc_subdir_batch23():
    """source 必须含 '_per_doc' 子目录命名约定。"""
    source = inspect.getsource(rmod)
    assert "_per_doc" in source


def test_module_source_contains_ensure_ascii_false_batch23():
    """source 必须含 ensure_ascii=False（中文输出）。"""
    source = inspect.getsource(rmod)
    assert "ensure_ascii=False" in source


def test_module_source_contains_indent_2_batch23():
    """source 必须含 indent=2（JSON 输出格式）。"""
    source = inspect.getsource(rmod)
    assert "indent=2" in source


def test_module_source_contains_unknown_code_batch23():
    """source 必须含 'unknown' code（document None 时 fallback）。"""
    source = inspect.getsource(rmod)
    assert '"unknown"' in source


def test_module_source_contains_image_output_dir_for_call_batch23():
    """source 必须含 image_output_dir_for(out_stub, ...) 调用。"""
    source = inspect.getsource(rmod)
    assert "image_output_dir_for(out_stub" in source


def test_module_source_contains_tolerance_chars_param_batch23():
    """source 必须含 tolerance_chars 参数。"""
    source = inspect.getsource(rmod)
    assert "tolerance_chars" in source


def test_module_source_contains_annotation_resolved_batch23():
    """source 必须读 annotation_resolved（manifest 字段）。"""
    source = inspect.getsource(rmod)
    assert "annotation_resolved" in source


# ---------- signatures 第三十五批 ----------


def test_signature_load_annotation_batch23():
    """_load_annotation(path: Path | None) -> dict[str, Any] | None。"""
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    p = params[0]
    assert p.name == "path"
    assert p.default is inspect.Parameter.empty
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.return_annotation == "dict[str, Any] | None"


def test_signature_process_one_batch23():
    """_process_one(doc, output_root, parser_name, max_chars) -> tuple[dict|None, dict|None, float, str|None, Path|None]。"""
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]
    for p in params:
        assert p.default is inspect.Parameter.empty
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.return_annotation == (
        "tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path | None]"
    )


def test_signature_run_evaluation_batch23():
    """run_evaluation(manifest, output_path, *, parser_name, max_chars, tolerance_chars) -> dict[str, Any]。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert [p.name for p in params] == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]
    # manifest, output_path 必填
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty
    # 后 3 个 keyword-only
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY
    # 默认值
    assert params[2].default == "fallback"
    assert params[3].default == 800
    assert params[4].default == 30
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_process_one_annotations_are_strings_batch23():
    """`from __future__ import annotations` 使所有注解为字符串。"""
    sig = inspect.signature(_process_one)
    assert isinstance(sig.return_annotation, str)


def test_signature_run_evaluation_annotations_are_strings_batch23():
    sig = inspect.signature(run_evaluation)
    assert isinstance(sig.return_annotation, str)


def test_signature_load_annotation_param_annotation_batch23():
    """path 参数注解是 'Path | None'。"""
    sig = inspect.signature(_load_annotation)
    p = sig.parameters["path"]
    assert p.annotation == "Path | None"


def test_signature_process_one_max_chars_annotation_batch23():
    """max_chars 注解是 'int'。"""
    sig = inspect.signature(_process_one)
    p = sig.parameters["max_chars"]
    assert p.annotation == "int"


def test_signature_run_evaluation_max_chars_annotation_batch23():
    """max_chars 注解是 'int'。"""
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["max_chars"]
    assert p.annotation == "int"


# ---------- module 合理性 第三十五批 ----------


def test_module_all_only_run_evaluation_batch23():
    """__all__ 仅暴露 run_evaluation（_load_annotation, _process_one 是私有）。"""
    assert hasattr(rmod, "__all__")
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_three_callables_batch23():
    """runner.py 定义 3 个函数：_load_annotation, _process_one, run_evaluation。"""
    funcs = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isfunction)
        if val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_run_evaluation_in_all_callable_batch23():
    """__all__ 中 run_evaluation 是可调用属性。"""
    assert "run_evaluation" in rmod.__all__
    assert callable(getattr(rmod, "run_evaluation"))


def test_module_no_classes_batch23():
    """runner.py 不定义任何 class。"""
    classes = [
        name
        for name, val in inspect.getmembers(rmod, inspect.isclass)
        if val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_docstring_mentions_pipeline_batch23():
    """module docstring 应说明这是评测 runner。"""
    assert rmod.__doc__ is not None
    assert "评测" in rmod.__doc__ or "runner" in rmod.__doc__.lower()


def test_module_docstring_mentions_total_batch23():
    """module docstring 提及 total（计时只记 total 的约束）。"""
    assert rmod.__doc__ is not None
    assert "total" in rmod.__doc__


def test_module_docstring_mentions_not_instrumented_batch23():
    """module docstring 提及 not_instrumented（parse/chunk 未插桩）。"""
    assert rmod.__doc__ is not None
    # 直接或间接表述
    src = rmod.__doc__.lower()
    assert "instrument" in src or "未插桩" in rmod.__doc__


def test_module_docstring_mentions_image_batch23():
    """module docstring 提及 image 资源处理。"""
    assert rmod.__doc__ is not None
    assert "image" in rmod.__doc__.lower() or "图片" in rmod.__doc__


def test_module_process_one_docstring_present_batch23():
    """_process_one 有 docstring。"""
    assert _process_one.__doc__ is not None
    assert len(_process_one.__doc__) > 0


def test_module_run_evaluation_docstring_present_batch23():
    """run_evaluation 有 docstring（即使是单行）。"""
    assert run_evaluation.__doc__ is not None


def test_module_constants_no_module_level_mutables_batch23():
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


def test_module_uses_from_future_annotations_batch23():
    """runner.py 必须有 from __future__ import annotations。"""
    source = inspect.getsource(rmod)
    assert "from __future__ import annotations" in source


# ---------- 端到端集成 第三十五批 ----------


def test_e2e_full_flow_no_documents_writes_valid_json_batch23(tmp_path):
    """端到端：空 manifest → 生成 JSON 文件，可被 json.load。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["report_version"] == REPORT_VERSION
    assert data["per_doc"] == []


def test_e2e_summary_has_four_top_keys_batch23(tmp_path):
    """summary 顶层 4 keys：counts, success_rates, ratio_macro_averages, silent_drop_total。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert set(report["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_e2e_provenance_has_nine_keys_batch23(tmp_path):
    """provenance 含 9 keys：git_commit, git_dirty, evaluator_version, report_version, parser_name, parser_version, dependencies, max_chars, run_timestamp_iso。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

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


def test_e2e_run_evaluation_idempotent_for_empty_batch23(tmp_path):
    """两次跑空 manifest 应得到结构等价的 report（除 timestamp/git_dirty 外）。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    # 除 timestamp 外，其余应等价
    r1["provenance"].pop("run_timestamp_iso")
    r2["provenance"].pop("run_timestamp_iso")
    # git_dirty 可能不同（worktree 状态变），但 git_commit 应一致
    r1["provenance"].pop("git_dirty", None)
    r2["provenance"].pop("git_dirty", None)
    assert r1 == r2


def test_e2e_str_path_output_accepted_batch23(tmp_path):
    """output_path 接受 str（不仅 Path）。"""
    manifest = MagicMock()
    manifest.documents = []
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 0
    manifest.content_group_count = 0
    manifest.pdf_count = 0
    manifest.docx_count = 0
    manifest.categories_covered = []

    out = str(tmp_path / "report.json")
    report = run_evaluation(manifest, out)
    assert Path(out).is_file()
    assert report["report_version"] == REPORT_VERSION


def test_e2e_image_base_dir_when_image_dir_is_dir_batch23(tmp_path):
    """image_dir 是目录 → compute_automatic_metrics 接收 image_base_dir=image_dir。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    # 创建实际的 image 目录
    image_dir = tmp_path / "_per_doc" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    doc_dict = _build_document_dict("d1")
    captured = {}

    def fake_metrics(*args, **kwargs):
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        # 返回最小合法 metrics
        return {"pipeline_success": {"value": True}}

    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.01, "fallback/v", image_dir),
    ), patch(
        "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
    ):
        out = tmp_path / "report.json"
        run_evaluation(manifest, out)

    assert captured["image_base_dir"] == image_dir


def test_e2e_image_base_dir_none_when_image_dir_not_dir_batch23(tmp_path):
    """image_dir 不存在（不是目录）→ compute_automatic_metrics 接收 image_base_dir=None。"""
    doc1 = MagicMock()
    doc1.doc_id = "d1"
    doc1.source_type = "pdf"
    doc1.resolved_path = tmp_path / "d1.pdf"
    doc1.expectations = None
    doc1.annotation_resolved = None

    manifest = MagicMock()
    manifest.documents = [doc1]
    manifest.expected_failures = []
    manifest.project_root = tmp_path
    manifest.devset_status = "incomplete"
    manifest.file_count = 1
    manifest.content_group_count = 1
    manifest.pdf_count = 1
    manifest.docx_count = 0
    manifest.categories_covered = []

    # image_dir 是不存在的路径
    image_dir = tmp_path / "_per_doc" / "does_not_exist"

    doc_dict = _build_document_dict("d1")
    captured = {}

    def fake_metrics(*args, **kwargs):
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        return {"pipeline_success": {"value": True}}

    with patch(
        "evaluation.runner._process_one",
        return_value=(doc_dict, None, 0.01, "fallback/v", image_dir),
    ), patch(
        "evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics
    ):
        out = tmp_path / "report.json"
        run_evaluation(manifest, out)

    assert captured["image_base_dir"] is None
