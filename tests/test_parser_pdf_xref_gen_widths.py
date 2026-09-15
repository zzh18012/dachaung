r"""PDF xref 条目编码变体：/W 窄字段 + 非零代数 gen（Round
1985，a 优先级）。

真实文件并非都是 /W [1 4 2] + gen 0：小文件常用窄字段编
码；被增量更新过的对象带非零代数（经典表 00001 n）。覆盖
grep 确认 /W 变体与 gen 语义零覆盖（既有 xref 流夹具全为
[W 1 4 2] + gen 0）。探针 R1985 实证：

- **T1 /W [1 2 1]**：偏移 2 字节、代数 1 字节的 xref 流 →
  'NARROWW' 照提
- **T2 经典表 gen=1（明文）**：内容流对象 4 更新过 →
  'GENONE' 照提（pdfminer 检索按 objid，gen 被容忍）
- **T3 R2/V1 加密 + gen=1**：对象密钥 =
  MD5(fk+oid_le24+gen_le16) 取真实 gen=1 → 'GENENC' 照提

判别式（T3 为核心）：若 pdfminer 在对象密钥派生里硬编码
gen=0（或忽略 xref 条目里的 gen 列），解密必乱码 → 零元
素 + pdf_no_text_extracted 静默翻红（认证不受影响——
file_key/U 与对象密钥无关）；若 /W 窄字段被按 [1 4 2] 解
读则 T1 条目错位 → PDFXRef 解析错或对象缺失翻红。T2 与
T3 合看把 gen 的两重身份（检索容忍 vs 派生必用）同时锁
住。
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

PAD = bytes([
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00,
    0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08, 0x2E, 0x2E, 0x00, 0xB6,
    0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53,
    0x69, 0x7A])

ID0 = bytes(range(16))
P_NEG1 = (-1 & 0xFFFFFFFF).to_bytes(4, "little")


def _rc4(key: bytes, data: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 255
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for b in data:
        i = (i + 1) & 255
        j = (j + S[i]) & 255
        S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i] + S[j]) & 255])
    return bytes(out)


_O = _rc4(hashlib.md5(PAD).digest()[:5], PAD)
_FK = hashlib.md5(PAD + _O + P_NEG1 + ID0).digest()[:5]
_U = _rc4(_FK, PAD)


def _obj_key(objid: int, gen: int) -> bytes:
    return hashlib.md5(
        _FK + objid.to_bytes(3, "little")
        + gen.to_bytes(2, "little")).digest()[:10]


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "w.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def test_narrow_w_fields():
    """T1：/W [1 2 1] 窄字段 xref 流 → 'NARROWW' 照提零告警。"""
    body = b"BT /F1 12 Tf 100 700 Td (NARROWW) Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(body)).encode()
            + b" >>\nstream\n" + body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_off = len(out)

    def row(t: int, off: int) -> bytes:
        return bytes([t]) + off.to_bytes(2, "big") + bytes([0])

    entries = [row(0, 0)]
    for oid in range(1, 6):
        entries.append(row(1, offsets[oid]))
    entries.append(row(1, xref_off))
    xraw = b"".join(entries)
    out += (b"6 0 obj\n<< /Type /XRef /Size 7 /W [1 2 1] /Root 1 0 R"
            + b" /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"

    d = _parse_pdf(bytes(out))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NARROWW"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 165.988, 94.484], abs=0.01)
    assert d.warnings == []


def _classic(cs_body: bytes, gen4: int, encrypt: bool):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(cs_body)).encode()
            + b" >>\nstream\n" + cs_body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    if encrypt:
        objs[6] = (b"<< /Filter /Standard /V 1 /R 2 /O <" + _O.hex().encode()
                   + b"> /U <" + _U.hex().encode() + b"> /P -1 >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        gen = gen4 if oid == 4 else 0
        out += ("%010d %05d n \n" % (offsets[oid], gen)).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R" + (b" /Encrypt 6 0 R" if encrypt else b"")
            + b" /ID [<" + ID0.hex().encode() + b"> <" + ID0.hex().encode()
            + b">] >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    return _parse_pdf(bytes(out))


def test_gen1_plain_object():
    """T2：经典表 gen=1 明文 → 'GENONE' 照提零告警。"""
    d = _classic(b"BT /F1 12 Tf 100 700 Td (GENONE) Tj ET", 1, False)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "GENONE"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 152.008, 94.484], abs=0.01)
    assert d.warnings == []


def test_gen1_encrypted_object_key():
    """T3：R2/V1 加密 + gen=1 → 对象密钥取真实 gen → 'GENENC' 照提。"""
    cipher = _rc4(_obj_key(4, 1),
                  b"BT /F1 12 Tf 100 700 Td (GENENC) Tj ET")
    d = _classic(cipher, 1, True)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "GENENC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 151.336, 94.484], abs=0.01)
    assert d.warnings == []
