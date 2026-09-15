"""PDF V4 加密 crypt filter 矩阵（Round 2010，a 优先级）。

pdfdocument.py PDFStandardSecurityHandlerV4.init_params 实读：
StmF≠StrF → PDFEncryptionError；CF 每项 CFM 仅认
{V2, AESV2}；Identity→decrypt_identity 免 CF 直名注册；
get_cfm V2→decrypt_rc4（**无 sAlT 盐**，算法 3.1 形状）。
R1982 只锁 AESV2+StdCF 全加密；Identity / CFM-V2 / 两条
拒绝分支零覆盖（grep 实证 tests/ 无 StmF 非 StdCF 形态）。
探针 R2010 实证：

- **T1 /StmF /Identity** + 明文内容流 → decrypt_identity
  no-op → 'STMPLAIN' 照提满宽、零告警（有 /Encrypt 但流
  不加密）
- **T2 /CFM /V2** + RC4 加密流（对象密钥 md5(fk+objid_le24
  +gen_le16)[:16] 无盐）→ 照提；与 AESV2 含盐形状对照
- **T3 /CFM /None** → ParserError code=pdfplumber_open_failed
  且 message 含 "Unknown crypt filter method"
- **T4 /StmF /Identity /StrF /StdCF 不匹配** → 同 code 但
  message 含 "Unsupported crypt filter"

判别式：T1 若被强行解密 → 乱码零元素翻；T2 若错用 AES
盐形状 → 解密乱码零元素翻；T3/T4 若 code 或 message 甄别
串不同翻。
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import FallbackParser

PAD = bytes([
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00,
    0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08, 0x2E, 0x2E, 0x00, 0xB6,
    0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53,
    0x69, 0x7A])
ID0 = bytes(range(16))
P_NEG1 = (-1 & 0xFFFFFFFF).to_bytes(4, "little")

TEXT = b"BT /F1 12 Tf 100 700 Td (STMPLAIN) Tj ET"


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


def _pad_pw(pw: str) -> bytes:
    b = pw.encode()
    return b + PAD[:32 - len(b)]


def _xor_key(key: bytes, i: int) -> bytes:
    return bytes(b ^ i for b in key)


def _r4_keys() -> tuple[bytes, bytes, bytes]:
    h = hashlib.md5(_pad_pw("")).digest()
    for _ in range(50):
        h = hashlib.md5(h).digest()
    key_o = h[:16]
    O = _rc4(key_o, _pad_pw(""))
    for i in range(1, 20):
        O = _rc4(_xor_key(key_o, i), O)
    d = hashlib.md5(_pad_pw("") + O + P_NEG1 + ID0).digest()
    for _ in range(50):
        d = hashlib.md5(d).digest()
    fk = d[:16]
    U = _rc4(fk, hashlib.md5(PAD + ID0).digest())
    for i in range(1, 20):
        U = _rc4(_xor_key(fk, i), U)
    return O, U + b"\x00" * 16, fk


O, U, FILE_KEY = _r4_keys()


def _rc4_obj_key(objid: int, gen: int = 0) -> bytes:
    key = FILE_KEY + objid.to_bytes(3, "little") + gen.to_bytes(2, "little")
    return hashlib.md5(key).digest()[:min(len(key), 16)]


def _parse(enc_dict: bytes, cs_body: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + str(len(cs_body)).encode()
            + b" >>\nstream\n" + cs_body + b"\nendstream"),
        6: (b"<< /Filter /Standard /V 4 /R 4 /Length 128" + enc_dict
            + b" /O <" + O.hex().encode() + b"> /U <" + U.hex().encode()
            + b"> /P -1 >>"),
    }
    out = bytearray(b"%PDF-1.6\n")
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
            + b" /Root 1 0 R /Encrypt 6 0 R /ID [<" + ID0.hex().encode()
            + b"> <" + ID0.hex().encode()
            + b">] >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


IDENT = (b" /CF << /StdCF << /CFM /AESV2 /Length 16 >> >>"
         b" /StmF /Identity /StrF /Identity")
V2 = (b" /CF << /StdCF << /CFM /V2 /Length 16 >> >>"
      b" /StmF /StdCF /StrF /StdCF")


def test_stmf_identity_plain_stream():
    """T1：/StmF /Identity + 明文流 → 照提满宽、零告警。"""
    d = _parse(IDENT, TEXT)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "STMPLAIN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 160.012, 94.484], abs=0.01)
    assert d.warnings == []


def test_cfm_v2_rc4_no_salt():
    """T2：/CFM /V2 RC4 对象密钥无盐 → 解密正确照提。"""
    d = _parse(V2, _rc4(_rc4_obj_key(4), TEXT))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "STMPLAIN"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 160.012, 94.484], abs=0.01)
    assert d.warnings == []


def test_cfm_none_rejected():
    """T3：/CFM /None → ParserError pdfplumber_open_failed + Unknown crypt filter。"""
    with pytest.raises(ParserError) as ei:
        _parse(b" /CF << /StdCF << /CFM /None >> >> /StmF /StdCF /StrF /StdCF",
               TEXT)
    assert ei.value.code == "pdfplumber_open_failed"
    assert "Unknown crypt filter method" in ei.value.message


def test_stmf_strf_mismatch_rejected():
    """T4：StmF≠StrF → 同 code + Unsupported crypt filter 甄别串。"""
    with pytest.raises(ParserError) as ei:
        _parse(b" /CF << /StdCF << /CFM /AESV2 /Length 16 >> >>"
               b" /StmF /Identity /StrF /StdCF", TEXT)
    assert ei.value.code == "pdfplumber_open_failed"
    assert "Unsupported crypt filter" in ei.value.message
