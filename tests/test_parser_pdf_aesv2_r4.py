r"""PDF 空用户密码 V4/R4 AESV2（AES-128-CBC）加密透明解密
（Round 1982，a 优先级）。

R1980/R1981 锁了 RC4（V1/V2）；V4 起流改 AESV2：密钥派生
与 R3 完全同源（算法 3.2/3.3/3.5，O/U 仍是 RC4 链），但对象
密钥多拼 4 字节盐（MD5(file_key+objid_le24+gen_le16+"sAlT")
[:16]），流密文 = IV(16) 前置 + AES-128-CBC(PKCS#7 pad)，
经 /CF /StdCF /CFM /AESV2 + /StmF /StrF 声明。探针 R1982 用
venv 已装的 cryptography 加密（pdfminer AES 同依赖），解密
走 FallbackParser。实证全通：

- **E1 单页 AES 内容流** → 'AESENC' 照提满宽、零告警
- **E2 两页各自加密**（对象密钥含 objid+盐）→ PAGEA/
  PAGEB 都提
- **E3 先 Flate 后 AES**（解码序解密再解压）→ 'ZAESNC'
  照提

判别式：对象密钥若漏 "sAlT" 盐（RC4 形状直接套 AES）则全
部静默翻红——认证仍过（O/U 与流加密无关）但 AES 解密成乱
码 → 零元素 + pdf_no_text_extracted；IV 若不前置则首块解
错、文本头部乱码；PKCS#7 若不垫则解密后尾巴多控制字节。
cryptography 缺席时 importorskip（pdfminer AES 同依赖，缺席
即整条路径不可用，非本夹具缺陷）。
"""

from __future__ import annotations

import hashlib
import tempfile
import zlib
from pathlib import Path

import pytest

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.ciphers import (  # noqa: E402
    Cipher, algorithms, modes)

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


def _pad_pw(pw: str) -> bytes:
    b = pw.encode()
    return b + PAD[:32 - len(b)]


def _xor_key(key: bytes, i: int) -> bytes:
    return bytes(b ^ i for b in key)


def _r4_keys() -> tuple[bytes, bytes, bytes]:
    """算法 3.3/3.2/3.5（R4 的 O/U/file_key 与 R3 同源）。"""
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


def _aes_obj_key(objid: int, gen: int = 0) -> bytes:
    return hashlib.md5(
        FILE_KEY + objid.to_bytes(3, "little")
        + gen.to_bytes(2, "little") + b"sAlT").digest()[:16]


def _aes_enc(key: bytes, data: bytes, iv: bytes) -> bytes:
    n = 16 - len(data) % 16
    data = data + bytes([n]) * n
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return iv + enc.update(data) + enc.finalize()


def _parse(pages: list[tuple[str, bool]]):
    n = len(pages)
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (b"<< /Type /Pages /Count " + str(n).encode()
            + b" /Kids [" + b" ".join(f"{3 + i} 0 R".encode()
                                      for i in range(n)) + b"] >>"),
    }
    for i, (text, flate) in enumerate(pages):
        body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
        payload = zlib.compress(body) if flate else body
        filt = b" /Filter /FlateDecode" if flate else b""
        page_oid = 3 + i
        cs_oid = 3 + n + i
        font_oid = 3 + 2 * n
        cipher = _aes_enc(_aes_obj_key(cs_oid), payload,
                          bytes([0xA0 + i]) + bytes(15))
        objs[page_oid] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
                          b" /Resources << /Font << /F1 "
                          + f"{font_oid} 0 R".encode()
                          + b" >> >> /Contents " + f"{cs_oid} 0 R".encode() + b" >>")
        objs[cs_oid] = (b"<<" + filt + b" /Length " + str(len(cipher)).encode()
                        + b" >>\nstream\n" + cipher + b"\nendstream")
    font_oid = 3 + 2 * n
    objs[font_oid] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    enc_oid = font_oid + 1
    objs[enc_oid] = (b"<< /Filter /Standard /V 4 /R 4 /Length 128"
                     b" /CF << /StdCF << /CFM /AESV2 /Length 16 >> >>"
                     b" /StmF /StdCF /StrF /StdCF"
                     b" /O <" + O.hex().encode() + b"> /U <" + U.hex().encode()
                     + b"> /P -1 >>")

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
            + b" /Root 1 0 R /Encrypt " + f"{enc_oid} 0 R".encode()
            + b" /ID [<" + ID0.hex().encode() + b"> <" + ID0.hex().encode()
            + b">] >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_aes_plain_stream_decrypts():
    """E1：无压缩 AESV2 内容流 → 'AESENC' 照提满宽、零告警。"""
    d = _parse([("AESENC", False)])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AESENC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 149.344, 94.484], abs=0.01)
    assert d.warnings == []


def test_two_pages_per_object_keys():
    """E2：两页各自 AES 加密（对象密钥含 objid+盐）→ 都提。"""
    d = _parse([("PAGEA", False), ("PAGEB", False)])
    assert [e.content for e in d.elements] == ["PAGEA", "PAGEB"]
    for e in d.elements:
        assert e.source_locator["bbox"] == pytest.approx(
            [100.0, 82.484, 141.352, 94.484], abs=0.01)
    assert d.warnings == []


def test_flate_then_aes_chain():
    """E3：先 Flate 后 AES → 解码序（解密再解压）正确照提。"""
    d = _parse([("ZAESNC", True)])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ZAESNC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 148.672, 94.484], abs=0.01)
    assert d.warnings == []
