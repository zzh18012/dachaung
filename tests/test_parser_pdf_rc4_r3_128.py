r"""PDF 空用户密码 R3/V2 RC4-128 加密透明解密（Round 1981，a 优先级）。

R1980 锁了 R2/V1（40 位、无密钥扩展）；现实主流是 R3/V2
/Length 128：key_o 50 轮 MD5、file_key 16 字节再 50 轮扩展、
O/U 各 19 轮 RC4 链、U 校验只认前 16 字节。探针 R1981 手搓
算法 3.3/3.2/3.5（纯 hashlib+RC4，无写入库依赖）实证
pdfminer 空密码透明解密：

- **T1 基线 R3/V2**（owner=user=""，经典 xref）→ 'RC4R3'
  照提零告警——16 字节 file_key + 19 轮 U 链完整支持
- **T2 owner 密码非空**（user 空）→ 'OWNERLOCK' 照提：
  空用户密码走 user 路径认证（file_key 只依赖存储 O，与
  owner 密码是否泄露无关）
- **T3 objstm + 内容流加密 + xref 流明文**（交叉引用流格
  式）→ 'STMENC' 照提——对象流按自身 objid 解密、xref 流
  规范豁免不加密

判别式：对象密钥若漏 gen 两字节（探针实证的初版缺陷）则
全部静默翻红——认证仍过但流解密成乱码 → 零元素 +
pdf_no_text_extracted；xref 流条目若漏 Encrypt 对象则 T3 翻
ParserError（/Encrypt 解引用为空 dict → Unknown filter
param={}）；U 链若少一轮 RC4 则认证失败翻 ParserError。
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


def _r3_keys(owner_pw: str, user_pw: str) -> tuple[bytes, bytes, bytes]:
    """算法 3.3/3.2/3.5（R3/V2，n=16）。返回 (O, U32, file_key)。"""
    h = hashlib.md5(_pad_pw(owner_pw)).digest()
    for _ in range(50):
        h = hashlib.md5(h).digest()
    key_o = h[:16]
    O = _rc4(key_o, _pad_pw(user_pw))
    for i in range(1, 20):
        O = _rc4(_xor_key(key_o, i), O)
    d = hashlib.md5(_pad_pw(user_pw) + O + P_NEG1 + ID0).digest()
    for _ in range(50):
        d = hashlib.md5(d).digest()
    fk = d[:16]
    U = _rc4(fk, hashlib.md5(PAD + ID0).digest())
    for i in range(1, 20):
        U = _rc4(_xor_key(fk, i), U)
    return O, U + b"\x00" * 16, fk


def _obj_key(fk: bytes, oid: int) -> bytes:
    return hashlib.md5(
        fk + oid.to_bytes(3, "little")
        + (0).to_bytes(2, "little")).digest()[:16]


def _parse_pdf(data: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "r3.pdf"
        p.write_bytes(data)
        return FallbackParser().parse(p, compute_file_hash(p))


def _classic(text: str, owner_pw: str):
    O, U, fk = _r3_keys(owner_pw, "")
    body = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET".encode()
    cipher = _rc4(_obj_key(fk, 4), body)
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(cipher)).encode()
            + b" >>\nstream\n" + cipher + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: (b"<< /Filter /Standard /V 2 /R 3 /Length 128 /O <"
            + O.hex().encode() + b"> /U <" + U.hex().encode()
            + b"> /P -1 >>"),
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
            + b" /Root 1 0 R /Encrypt 6 0 R /ID [<" + ID0.hex().encode()
            + b"> <" + ID0.hex().encode()
            + b">] >>\nstartxref\n" + str(xref).encode() + b"\n%%EOF")
    return _parse_pdf(bytes(out))


def _objstm():
    O, U, fk = _r3_keys("", "")
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
    cipher = _rc4(_obj_key(fk, 5), zlib.compress(header + payload))
    body = b"BT /F1 12 Tf 100 700 Td (STMENC) Tj ET"
    cs_cipher = _rc4(_obj_key(fk, 4), body)

    out = bytearray(b"%PDF-1.5\n")
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

    off4 = len(b"%PDF-1.5\n")
    len4 = len(b"4 0 obj\n") + len(
        b"<< /Length " + str(len(cs_cipher)).encode()
        + b" >>\nstream\n" + cs_cipher + b"\nendstream\nendobj\n")
    off5 = off4 + len4
    # 8 号偏移依赖 7 号块长：条目定长 6 字节，先占位再回填
    entries = [free, e2(order.index(1)), e2(order.index(2)),
               e2(order.index(3)), e1(off4), e1(off5),
               e2(order.index(6)), e1(xref_off), e1(0)]

    def block7(xraw: bytes) -> bytes:
        return (b"7 0 obj\n<< /Type /XRef /Size 9 /W [1 4 2] /Root 1 0 R"
                + b" /Encrypt 8 0 R /ID [<" + ID0.hex().encode() + b"> <"
                + ID0.hex().encode() + b">] /Length "
                + str(len(xraw)).encode()
                + b" >>\nstream\n" + xraw + b"\nendstream\nendobj\n")

    xraw = b"".join(entries)
    entries[-1] = e1(xref_off + len(block7(xraw)))
    out += block7(b"".join(entries))
    out += (b"8 0 obj\n<< /Filter /Standard /V 2 /R 3 /Length 128 /O <"
            + O.hex().encode() + b"> /U <" + U.hex().encode()
            + b"> /P -1 >>\nendobj\n")
    out += b"startxref\n" + str(xref_off).encode() + b"\n%%EOF"
    return _parse_pdf(bytes(out))


def test_r3_baseline_decrypts():
    """T1：R3/V2 空密码基线 → 'RC4R3' 照提满宽、零告警。"""
    d = _classic("RC4R3", "")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "RC4R3"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 139.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_owner_password_user_empty():
    """T2：owner 密码非空（user 空）→ 空用户密码仍透明解密。"""
    d = _classic("OWNERLOCK", "own123")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "OWNERLOCK"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 178.672, 94.484], abs=0.01)
    assert d.warnings == []


def test_objstm_encrypted_xref_stream_plain():
    """T3：objstm+内容流加密、xref 流规范豁免 → 'STMENC' 照提。"""
    d = _objstm()
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "STMENC"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 150.664, 94.484], abs=0.01)
    assert d.warnings == []
