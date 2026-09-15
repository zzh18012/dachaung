r"""PDF 空用户密码 V5/R6 AESV3（AES-256-CBC）加密透明解密
（Round 1983，a 优先级）。

R1980–R1982 锁了 RC4 V1/V2 + AESV2 V4；V5/R6 是最后一个
标准安全家族，与前代完全异构：无 MD5/RC4；密码哈希 = 算法
2.B（SHA-256/384/512 由密文首 16 字节 mod 3 动态选择 +
AES-128-CBC 内层扰动、≥64 轮、owner 路径拼整个 48 字节 U
作 vector）；U/O 各 48 字节 = hash(32)+验证盐(8)+密钥盐(8)；
file_key(32) 藏在 UE/OE（AES-256-CBC、零 IV、无填充）；流
= IV 前置 + AES-256-CBC(file_key 直接用，**无 objid 盐**)
+ PKCS#7；/CFM /AESV3；密钥派生不依赖 /ID。探针 R1983 严
格镜像 pdfminer _r6_password/authenticate（pdfdocument.py
548–670 行）手搓加密方向，实证全通：

- **T1 单页 AESV3 流** → 'AES256X' 照提
- **T2 Flate+AESV3 链**（解码序解密再解压）→ 'ZAES256'
- **T3 objstm 加密 + xref 流明文**（交叉引用流格式）→
  'STMAES' 照提
- **T4 owner 密码非空**（user 空）→ 'OWNER256' 照提——
  pdfminer authenticate 先试 owner 路径，file_key 从 OE 出

判别式：2.B 内层若用错 IV（非 k[16:32]）或哈希选择函数算
错 mod 3 则认证失败翻 ParserError（密码错误）；流若误加
objid 盐（AESV2 形状套 AESV3）则全部静默翻红——认证仍过
但解密乱码 → 零元素 + pdf_no_text_extracted；UE/OE 若带
PKCS#7 填充则 file_key 尾部错、流解密乱码。cryptography
缺席时 importorskip（pdfminer AES 同依赖）。
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

U_VAL = bytes([0x11]) * 8
U_KEY = bytes([0x22]) * 8
O_VAL = bytes([0x33]) * 8
O_KEY = bytes([0x44]) * 8
FILE_KEY = bytes(range(32))
HASHES = (hashlib.sha256, hashlib.sha384, hashlib.sha512)


def _r6_hash(password: bytes, salt: bytes, vector: bytes = b"") -> bytes:
    """算法 2.B（镜像 pdfminer _r6_password）。"""
    k = hashlib.sha256(password + salt + vector).digest()
    round_no = last_byte = 0
    while round_no < 64 or last_byte > round_no - 32:
        k1 = (password + k + vector) * 64
        enc = Cipher(algorithms.AES(k[:16]), modes.CBC(k[16:32])).encryptor()
        e = enc.update(k1) + enc.finalize()
        k = HASHES[sum(b % 3 for b in e[:16]) % 3](e).digest()
        last_byte = e[-1]
        round_no += 1
    return k[:32]


def _aes_raw(key: bytes, data: bytes) -> bytes:
    enc = Cipher(algorithms.AES(key), modes.CBC(b"\0" * 16)).encryptor()
    return enc.update(data) + enc.finalize()


def _aes256_stream(data: bytes, iv: bytes) -> bytes:
    n = 16 - len(data) % 16
    data = data + bytes([n]) * n
    enc = Cipher(algorithms.AES(FILE_KEY), modes.CBC(iv)).encryptor()
    return iv + enc.update(data) + enc.finalize()


def _make_keys(owner_pw: str, user_pw: str):
    uo = owner_pw.encode()[:127]
    uu = user_pw.encode()[:127]
    U = _r6_hash(uu, U_VAL) + U_VAL + U_KEY
    UE = _aes_raw(_r6_hash(uu, U_KEY), FILE_KEY)
    O = _r6_hash(uo, O_VAL, U) + O_VAL + O_KEY
    OE = _aes_raw(_r6_hash(uo, O_KEY, U), FILE_KEY)
    return U, UE, O, OE


def _enc_dict(U: bytes, UE: bytes, O: bytes, OE: bytes) -> bytes:
    return (b"<< /Filter /Standard /V 5 /R 6 /Length 256"
            b" /CF << /StdCF << /CFM /AESV3 /Length 32 >> >>"
            b" /StmF /StdCF /StrF /StdCF"
            b" /O <" + O.hex().encode() + b"> /OE <" + OE.hex().encode()
            + b"> /U <" + U.hex().encode() + b"> /UE <" + UE.hex().encode()
            + b"> /P -1 >>")


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "v5.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _classic(text: str, flate: bool, owner_pw: str):
    U, UE, O, OE = _make_keys(owner_pw, "")
    body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    payload = zlib.compress(body) if flate else body
    filt = b" /Filter /FlateDecode" if flate else b""
    cipher = _aes256_stream(payload, bytes([0xB0]) + bytes(15))
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<<" + filt + b" /Length " + str(len(cipher)).encode()
            + b" >>\nstream\n" + cipher + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: _enc_dict(U, UE, O, OE),
    }
    out = bytearray(b"%PDF-2.0\n")
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
            + b" /Root 1 0 R /Encrypt 6 0 R"
            + b" >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    return _parse_pdf(bytes(out))


def _objstm():
    U, UE, O, OE = _make_keys("", "")
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>"),
        6: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    order = sorted(objs)
    header = b""
    payload = b""
    for oid in order:
        header += f"{oid} ".encode() + str(len(payload)).encode() + b" "
        payload += objs[oid] + b" "
    cipher = _aes256_stream(zlib.compress(header + payload),
                            bytes([0xC0]) + bytes(15))
    body = b"BT /F1 12 Tf 100 700 Td (STMAES) Tj ET"
    cs_cipher = _aes256_stream(body, bytes([0xC1]) + bytes(15))

    out = bytearray(b"%PDF-2.0\n")
    out += (b"4 0 obj\n<< /Length " + str(len(cs_cipher)).encode()
            + b" >>\nstream\n" + cs_cipher + b"\nendstream\nendobj\n")
    out += (b"5 0 obj\n<< /Type /ObjStm /N " + str(len(order)).encode()
            + b" /First " + str(len(header)).encode()
            + b" /Filter /FlateDecode /Length " + str(len(cipher)).encode()
            + b" >>\nstream\n" + cipher + b"\nendstream\nendobj\n")

    xref_off = len(out)
    free = bytes([0]) + (0).to_bytes(4, "big") + (65535).to_bytes(2, "big")

    def e1(off: int) -> bytes:
        return bytes([1]) + off.to_bytes(4, "big") + (0).to_bytes(2, "big")

    def e2(idx: int) -> bytes:
        return bytes([2]) + (5).to_bytes(4, "big") + idx.to_bytes(2, "big")

    off4 = len(b"%PDF-2.0\n")
    len4 = len(b"4 0 obj\n") + len(
        b"<< /Length " + str(len(cs_cipher)).encode()
        + b" >>\nstream\n" + cs_cipher + b"\nendstream\nendobj\n")
    off5 = off4 + len4
    # 8 号偏移依赖 7 号块长：条目定长 6 字节，先占位再回填
    entries = [free, e2(order.index(1)), e2(order.index(2)), e2(order.index(3)),
               e1(off4), e1(off5), e2(order.index(6)), e1(xref_off), e1(0)]

    def block7(xraw: bytes) -> bytes:
        return (b"7 0 obj\n<< /Type /XRef /Size 9 /W [1 4 2] /Root 1 0 R"
                + b" /Encrypt 8 0 R /Length " + str(len(xraw)).encode()
                + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")

    xraw = b"".join(entries)
    entries[-1] = e1(xref_off + len(block7(xraw)))
    out += block7(b"".join(entries))
    out += b"8 0 obj\n" + _enc_dict(U, UE, O, OE) + b"\nendobj\n"
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_aes256_plain_stream_decrypts():
    """T1：无压缩 AESV3 流（file_key 直接用）→ 'AES256X' 照提。"""
    d = _classic("AES256X", False, "")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AES256X"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 152.032, 94.484], abs=0.01)
    assert d.warnings == []


def test_flate_then_aes256_chain():
    """T2：先 Flate 后 AESV3 → 解码序（解密再解压）正确照提。"""
    d = _classic("ZAES256", True, "")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "ZAES256"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 151.36, 94.484], abs=0.01)
    assert d.warnings == []


def test_objstm_encrypted_xref_stream_plain():
    """T3：objstm 加密 + xref 流规范豁免 → 'STMAES' 照提。"""
    d = _objstm()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "STMAES"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 149.344, 94.484], abs=0.01)
    assert d.warnings == []


def test_owner_password_user_empty():
    """T4：owner 密码非空（user 空）→ file_key 从 OE 出照样解。"""
    d = _classic("OWNER256", False, "own123")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OWNER256"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 166.012, 94.484], abs=0.01)
    assert d.warnings == []
