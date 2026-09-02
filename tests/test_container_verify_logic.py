"""批次 25 Phase A：container_verify.py 纯逻辑单元测试。

经 importlib 直接从 scripts/ 导入（scripts 不是包）。覆盖：
- D-C 语义对照：身份字段显式相等、来源可变字段剔除、其余逐字段相等；
- 分区断言：精确划分的完整正反例；
- sha256 边车解析与哈希；
- 合成语料构造（含 stdlib zipfile 最小 docx）。
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "container_verify", ROOT / "scripts" / "container_verify.py"
)
cv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cv)


def _sample_doc(source_path="/in/sample.md", image_output_dir="/tmp/host-out/images-x",
                element_text="段落一") -> dict:
    return {
        "schema_version": "0.6.0",
        "document_id": "doc-abc123",
        "source_path": source_path,
        "source_type": "markdown",
        "source_hash": "h1" * 32,
        "parser_name": "markdown",
        "parser_version": "stdlib/0.1.0",
        "elements": [
            {"element_id": "doc-abc123::e0000", "type": "heading",
             "content": "标题", "source_locator": {"family": "line_address", "line": 1},
             "metadata": {}},
            {"element_id": "doc-abc123::e0001", "type": "paragraph",
             "content": element_text, "source_locator": {"family": "line_address", "line": 3},
             "metadata": {}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "标题\n" + element_text,
             "source_element_ids": ["doc-abc123::e0000", "doc-abc123::e0001"],
             "metadata": {}},
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {"markdown": True, "image_output_dir": image_output_dir},
    }


# ---------- strip_provenance / compare_documents ----------

def test_strip_provenance_removes_exactly_provenance_fields():
    doc = _sample_doc()
    stripped = cv.strip_provenance(doc)
    assert "source_path" not in stripped
    assert "image_output_dir" not in stripped["metadata"]
    assert stripped["metadata"]["markdown"] is True
    # 原 dict 不被修改
    assert doc["source_path"] == "/in/sample.md"
    assert doc["metadata"]["image_output_dir"] == "/tmp/host-out/images-x"


def test_compare_identical_documents_pass():
    assert cv.compare_documents(_sample_doc(), _sample_doc()) == []


def test_compare_provenance_only_difference_passes():
    host = _sample_doc(source_path="C:/host/sample.md", image_output_dir="C:/host/out/images-x")
    cont = _sample_doc(source_path="/input/sample.md", image_output_dir="/output/images-x")
    assert cv.compare_documents(host, cont) == []


@pytest.mark.parametrize("field", ["source_hash", "document_id"])
def test_compare_identity_field_must_be_equal(field):
    host = _sample_doc()
    cont = _sample_doc()
    cont[field] = "different-value"
    problems = cv.compare_documents(host, cont)
    assert any(field in p for p in problems)


def test_compare_element_content_mismatch_reported():
    problems = cv.compare_documents(_sample_doc(), _sample_doc(element_text="不同段落"))
    assert problems and any("document.elements" in p for p in problems)


def test_compare_chunk_text_and_list_length_mismatch():
    host = _sample_doc()
    cont = _sample_doc()
    cont["chunks"][0]["text"] = "不同文本"
    assert cv.compare_documents(host, cont)
    cont2 = _sample_doc()
    cont2["elements"].append(dict(cont2["elements"][0], element_id="doc-abc123::e0002"))
    problems = cv.compare_documents(host, cont2)
    assert any("长度" in p for p in problems)


def test_compare_missing_key_on_one_side():
    host = _sample_doc()
    cont = _sample_doc()
    del cont["parser_version"]
    problems = cv.compare_documents(host, cont)
    assert any("parser_version" in p for p in problems)


def test_compare_excluded_field_cannot_mask_identity_difference():
    """剔除可变字段不等于放松身份断言：source_hash 不同必须报。"""
    host = _sample_doc()
    cont = _sample_doc(source_path="/input/sample.md")
    cont["source_hash"] = "ff" * 32
    assert cv.compare_documents(host, cont)


# ---------- check_partition ----------

def test_partition_valid_exact_cover():
    assert cv.check_partition(_sample_doc()) == []


def test_partition_empty_elements_or_chunks():
    doc = _sample_doc()
    doc["elements"] = []
    assert doc and cv.check_partition(doc)
    doc2 = _sample_doc()
    doc2["chunks"] = []
    assert cv.check_partition(doc2)


def test_partition_unknown_reference_rejected():
    doc = _sample_doc()
    doc["chunks"][0]["source_element_ids"] = ["doc-abc123::e9999"]
    problems = cv.check_partition(doc)
    assert any("不存在" in p for p in problems)


def test_partition_overlap_rejected():
    doc = _sample_doc()
    doc["chunks"].append({
        "chunk_id": "c2", "text": "重复引用",
        "source_element_ids": ["doc-abc123::e0001"], "metadata": {},
    })
    problems = cv.check_partition(doc)
    assert any("重叠" in p for p in problems)


def test_partition_uncovered_element_rejected():
    doc = _sample_doc()
    doc["chunks"][0]["source_element_ids"] = ["doc-abc123::e0000"]
    problems = cv.check_partition(doc)
    assert any("未覆盖" in p for p in problems)


def test_partition_within_chunk_duplicate_rejected():
    doc = _sample_doc()
    doc["chunks"][0]["source_element_ids"] = ["doc-abc123::e0000", "doc-abc123::e0000"]
    problems = cv.check_partition(doc)
    assert any("内部" in p for p in problems)


# ---------- sha256 / 边车 ----------

def test_sha256_of_matches_hashlib():
    p = Path(__file__).parent / "_b25_sha_tmp.bin"
    payload = b"batch25"
    p.write_bytes(payload)
    try:
        assert cv.sha256_of(p) == hashlib.sha256(payload).hexdigest()
    finally:
        p.unlink()


def test_read_sha256_sidecar_accepts_both_forms(tmp_path):
    art = tmp_path / "img.tar.gz"
    art.write_bytes(b"x")
    digest = hashlib.sha256(b"x").hexdigest()
    (tmp_path / "img.tar.gz.sha256").write_text(f"{digest}  img.tar.gz\n", encoding="utf-8")
    assert cv.read_sha256_sidecar(art) == digest
    (tmp_path / "img.tar.gz.sha256").write_text(digest, encoding="utf-8")
    assert cv.read_sha256_sidecar(art) == digest
    (tmp_path / "img.tar.gz.sha256").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        cv.read_sha256_sidecar(art)


def test_load_artifact_checksum_mismatch(tmp_path):
    art = tmp_path / "img.tar.gz"
    art.write_bytes(b"payload")
    (tmp_path / "img.tar.gz.sha256").write_text("0" * 64, encoding="utf-8")
    tag, err = cv.load_artifact(art)
    assert tag is None
    assert "校验和不符" in err


# ---------- 卷挂载规范 ----------

def test_vol_normalizes_backslashes_with_suffix(tmp_path):
    import re
    d = tmp_path / "out dir"
    d.mkdir()
    spec = cv._vol(d, ":/output")
    assert "\\" not in spec
    assert spec.endswith(":/output")
    # 绝对路径（POSIX 以 / 开头；Windows 为盘符形式 C:/…）
    host_part = spec[: -len(":/output")]
    assert re.match(r"^([A-Za-z]:/|/)", host_part), spec
    assert Path(host_part).is_absolute()


# ---------- 合成语料 ----------

def test_synthetic_inputs_writable_and_docx_is_valid_zip(tmp_path):
    for name, writer in cv.SYNTHETIC_INPUTS.items():
        target = tmp_path / name
        writer(target)
        assert target.is_file() and target.stat().st_size > 0
    with zipfile.ZipFile(tmp_path / "sample.docx") as z:
        names = set(z.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "word/styles.xml",
                "word/document.xml"} <= names
        doc_xml = z.read("word/document.xml").decode("utf-8")
        assert "合成文档标题" in doc_xml


def test_synthetic_docx_parseable_by_project_stack(tmp_path):
    """合成 docx 必须能被 fallback parser 真实解析（python-docx 可开）。"""
    cv._write_synthetic_docx(tmp_path / "sample.docx")
    sys.path.insert(0, str(ROOT))
    try:
        from app.parsers.fallback_parser import _parse_docx
        from app.hash import compute_file_hash
        from app.parsers.base import make_document_id
        from pathlib import Path as P
        elements, warnings = _parse_docx(
            P(tmp_path / "sample.docx"),
            compute_file_hash(P(tmp_path / "sample.docx")),
            make_document_id(compute_file_hash(P(tmp_path / "sample.docx"))),
            None,
        )
        assert elements, "合成 docx 应产出至少一个 element"
        assert any(e.type == "heading" for e in elements)
        assert not warnings
    finally:
        sys.path.remove(str(ROOT))


def test_gzip_roundtrip_of_verify_fixture(tmp_path):
    """（探针性质）gzip 模块可解出 docker save|gzip 形态——CI 归档路径自洽。"""
    raw = b"pretend-tarball" * 100
    gz = tmp_path / "x.tar.gz"
    with gzip.open(gz, "wb") as f:
        f.write(raw)
    with gzip.open(gz, "rb") as f:
        assert f.read() == raw
    payload = json.dumps({"ok": True})
    assert json.loads(payload)["ok"] is True
