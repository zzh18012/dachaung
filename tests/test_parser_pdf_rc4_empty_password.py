r"""PDF 空用户密码 V1/R2 RC4 加密透明解密（Round 1980，a 优先级）。

权限受限（无用户密码）加密 PDF 是现实常见形态（禁止打印/
复制）；edges91 只锁了密码校验失败 → ParserError，**可解密
形态零覆盖**。探针 R1980 手搓 R2/V1 标准安全处理器（纯
hashlib+RC4，无写入库依赖）实证 pdfminer 空密码透明解密：

- O = RC4(MD5(PAD)[:5], PAD)（owner=user=""）
- file_key = MD5(PAD + O + P_le32 + ID0)[:5]；U =
  RC4(file_key, PAD)
- 对象密钥 = MD5(file_key + objid_le24 + gen_le16)[:10]
- 流先 Flate 后 RC4（解码序：解密再解压）

- **E1 单页加密内容流**（无压缩）→ 'ENCTEXT' 照提、满宽
  bbox、零告警
- **E2 两页各自加密**（不同对象密钥）→ PAGEA/PAGEB 都提
- **E3 加密 + Flate 链**→ 'ZLIBENC' 照提——Filter 与解密
  顺序正确

判别式：若 U 校验/解密路径变化则 E1–E3 变 ParserError 翻
红；若对象密钥不再含 objid 则 E2 第二页乱码/失败翻红；若
先解压后解密则 E3 翻红。
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


_ID0 = bytes(range(16))
_P_NEG1 = (-1 & 0xFFFFFFFF).to_bytes(4, "little")
_O = _rc4(hashlib.md5(PAD).digest()[:5], PAD)
_FILE_KEY = hashlib.md5(PAD + _O + _P_NEG1 + _ID0).digest()[:5]
_U = _rc4(_FILE_KEY, PAD)


def _obj_key(objid: int, gen: int = 0) -> bytes:
    return hashlib.md5(
        _FILE_KEY + objid.to_bytes(3, "little")
        + gen.to_bytes(2, "little")).digest()[:10]


def _parse(pages: list[tuple[str, bool]]):
    n = len(pages)
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (b"<< /Type /Pages /Count " + str(n).encode()
            + b" /Kids [" + b" ".join(f"{3 + i} 0 R".encode()
                                      for i in range(n)) + b"] >>"),
    }
    font_oid = 3 + 2 * n
    for i, (text, flate) in enumerate(pages):
        body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
        payload = zlib.compress(body) if flate else body
        filt = b" /Filter /FlateDecode" if flate else b""
        page_oid = 3 + i
        cs_oid = 3 + n + i
        cipher = _rc4(_obj_key(cs_oid), payload)
        objs[page_oid] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
                          b" /Resources << /Font << /F1 "
                          + f"{font_oid} 0 R".encode()
                          + b" >> >> /Contents " + f"{cs_oid} 0 R".encode() + b" >>")
        objs[cs_oid] = (b"<< " + filt + b" /Length " + str(len(cipher)).encode()
                        + b" >>\nstream\n" + cipher + b"\nendstream")
    objs[font_oid] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    enc_oid = font_oid + 1
    objs[enc_oid] = (b"<< /Filter /Standard /V 1 /R 2 /O <" + _O.hex().encode()
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
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R /Encrypt " + f"{enc_oid} 0 R".encode()
            + b" /ID [<" + _ID0.hex().encode() + b"> <" + _ID0.hex().encode()
            + b">] >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "e.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_plain_encrypted_stream_decrypts():
    """E1：无压缩加密内容流 → 'ENCTEXT' 照提满宽、零告警。"""
    d = _parse([("ENCTEXT", False)])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ENCTEXT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 156.004, 94.484], abs=0.01)
    assert d.warnings == []


def test_two_pages_per_object_keys():
    """E2：两页各自加密（对象密钥含 objid）→ 都提零告警。"""
    d = _parse([("PAGEA", False), ("PAGEB", False)])
    assert [e.content for e in d.elements] == ["PAGEA", "PAGEB"]
    for e in d.elements:
        assert e.source_locator["bbox"] == pytest.approx(
            [100.0, 82.484, 141.352, 94.484], abs=0.01)
    assert d.warnings == []


def test_flate_then_encrypt_chain():
    """E3：先 Flate 后 RC4 → 解码序（解密再解压）正确照提。"""
    d = _parse([("ZLIBENC", True)])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ZLIBENC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 150.676, 94.484], abs=0.01)
    assert d.warnings == []
