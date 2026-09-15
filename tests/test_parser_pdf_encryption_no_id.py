r"""PDF 无 /ID trailer 下的标准加密（Round 1987，a 优先级）。

pdfdocument.py 对无 /ID 文件显式降级：docid=(b"",b"")，算
法 2（compute_encryption_key）与 R3 的 U 链（compute_u）都
update(self.docid[0])——无 /ID 时即 b""。此前 R1980/R1981
全部加密夹具 trailer 均带 /ID，此分支零覆盖。探针 R1987 实
证（密钥全按 id=b"" 手搓）：

- **T1 V1/R2 无 /ID**：fk=MD5(PAD+O+P_le32+b"")[:5]、
  U=RC4(fk,PAD)、obj 密钥 10 字节 → 'NOIDV1' 照提零告警
- **T2 V2/R3 无 /ID**：d 50 轮扩展、U 链内 MD5(PAD+b"")、
  obj 密钥 16 字节 → 'NOIDR3' 照提零告警
- **T3 V2/R3 + objstm + xref 流无 /ID**：objstm 按自身
  oid=7 解密、xref 流规范豁免、Encrypt 条目在 xref 流内
  → 'NOIDSTM' 照提零告警

判别式：若 pdfminer 对缺 /ID 崩溃或拒绝则 T1–T3 翻
ParserError；若密钥派生偷偷用其他 id 值（如伪造 16 字节）
则认证过但流乱码 → 零元素 + pdf_no_text_extracted；另实证
V2 缺 /Length 时 pdfminer 按 40 位默认 → 认证失败翻
ParserError（探针初版教训，/Length 128 必须显式写）。
"""

from __future__ import annotations

import hashlib
import tempfile
import zlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

PAD = bytes([
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00,
    0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08, 0x2E, 0x2E, 0x00, 0xB6,
    0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53,
    0x69, 0x7A])

NOID = b""
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


def _xor_key(key: bytes, i: int) -> bytes:
    return bytes(b ^ i for b in key)


def _r2_keys():
    O = _rc4(hashlib.md5(PAD).digest()[:5], PAD)
    fk = hashlib.md5(PAD + O + P_NEG1 + NOID).digest()[:5]
    U = _rc4(fk, PAD)
    return O, U, fk


def _r3_keys():
    h = hashlib.md5(PAD).digest()
    for _ in range(50):
        h = hashlib.md5(h).digest()
    key_o = h[:16]
    O = _rc4(key_o, PAD)
    for i in range(1, 20):
        O = _rc4(_xor_key(key_o, i), O)
    d = hashlib.md5(PAD + O + P_NEG1 + NOID).digest()
    for _ in range(50):
        d = hashlib.md5(d).digest()
    fk = d[:16]
    U = _rc4(fk, hashlib.md5(PAD + NOID).digest())
    for i in range(1, 20):
        U = _rc4(_xor_key(fk, i), U)
    return O, U + b"\x00" * 16, fk


def _obj_key(fk: bytes, oid: int, n: int) -> bytes:
    return hashlib.md5(
        fk + oid.to_bytes(3, "little")
        + (0).to_bytes(2, "little")).digest()[:n]


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "n.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _classic(cs_body: bytes, O: bytes, U: bytes, V: int, R: int) -> bytes:
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(cs_body)).encode()
            + b" >>\nstream\n" + cs_body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Filter /Standard /V " + str(V).encode() + b" /R "
            + str(R).encode()
            + (b" /Length 128" if V == 2 else b"")
            + b" /O <" + O.hex().encode()
            + b"> /U <" + U.hex().encode() + b"> /P -1 >>"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R /Encrypt 6 0 R >>\nstartxref\n"
            + str(xref).encode() + b"\n%%EOF")
    return _parse_pdf(bytes(out))


def _objstm_xref():
    O, U, fk = _r3_keys()
    inner: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    order = sorted(inner)
    header = b""
    payload = b""
    for oid in order:
        header += f"{oid} ".encode() + str(len(payload)).encode() + b" "
        payload += inner[oid] + b" "
    stm_cipher = _rc4(_obj_key(fk, 7, 16),
                      zlib.compress(header + payload))
    n, first = len(order), len(header)

    body = b"BT /F1 12 Tf 100 700 Td (NOIDSTM) Tj ET"
    cs_cipher = _rc4(_obj_key(fk, 4, 16), body)

    out = bytearray(b"%PDF-1.5\n")
    block4 = (b"4 0 obj\n<< /Length " + str(len(cs_cipher)).encode()
              + b" >>\nstream\n" + cs_cipher + b"\nendstream\nendobj\n")
    out += block4
    block7 = (b"7 0 obj\n<< /Type /ObjStm /N " + str(n).encode()
              + b" /First " + str(first).encode()
              + b" /Filter /FlateDecode /Length "
              + str(len(stm_cipher)).encode()
              + b" >>\nstream\n" + stm_cipher + b"\nendstream\nendobj\n")
    out += block7
    off4 = len(b"%PDF-1.5\n")
    off7 = off4 + len(block4)
    enc_obj = (b"6 0 obj\n<< /Filter /Standard /V 2 /R 3 /Length 128 /O <"
               + O.hex().encode() + b"> /U <" + U.hex().encode()
               + b"> /P -1 >>\nendobj\n")
    out += enc_obj
    off6 = len(out) - len(enc_obj)
    xref_off = len(out)

    free = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")

    def e1(off: int) -> bytes:
        return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")

    def e2(idx: int) -> bytes:
        return bytes([2]) + (7).to_bytes(4, "big") + idx.to_bytes(2, "big")

    rows = {0: free, 1: e2(order.index(1)), 2: e2(order.index(2)),
            3: e2(order.index(3)), 4: e1(off4), 5: e2(order.index(5)),
            6: e1(off6), 7: e1(off7), 8: e1(xref_off)}
    xraw = b"".join(rows[oid] for oid in range(9))
    out += (b"8 0 obj\n<< /Type /XRef /Size 9 /W [1 4 2] /Root 1 0 R"
            + b" /Encrypt 6 0 R /Length " + str(len(xraw)).encode()
            + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_r2_no_id_transparent():
    """T1：V1/R2 无 /ID → 'NOIDV1' 照提零告警。"""
    O, U, fk = _r2_keys()
    body = b"BT /F1 12 Tf 100 700 Td (NOIDV1) Tj ET"
    d = _classic(_rc4(_obj_key(fk, 4, 10), body), O, U, 1, 2)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NOIDV1"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 144.676, 94.484], abs=0.01)
    assert d.warnings == []


def test_r3_no_id_transparent():
    """T2：V2/R3 无 /ID → 'NOIDR3' 照提零告警。"""
    O, U, fk = _r3_keys()
    body = b"BT /F1 12 Tf 100 700 Td (NOIDR3) Tj ET"
    d = _classic(_rc4(_obj_key(fk, 4, 16), body), O, U, 2, 3)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NOIDR3"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 145.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_r3_objstm_xref_no_id_transparent():
    """T3：V2/R3 + objstm + xref 流无 /ID → 'NOIDSTM' 照提零告警。"""
    d = _objstm_xref()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "NOIDSTM"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 155.332, 94.484], abs=0.01)
    assert d.warnings == []
