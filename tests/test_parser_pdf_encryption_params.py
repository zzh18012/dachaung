r"""PDF 标准加密密钥派生参数分支（Round 1988，a 优先级）。

此前全部加密夹具（R1980–R1987）参数空间收窄：/P 恒 -1、
/EncryptMetadata 缺省（=true）、/Length 恒 128（V2）。三
个真实世界分支零覆盖，探针 R1988 实证手搓密钥全部照提：

- **T1 /P -4 受限权限**：compute_encryption_key 第 4 步
  struct.pack("<L",p) 进哈希——权限位不是装饰字段 →
  'PERMKEY' 照提零告警
- **T2 AESV2 /EncryptMetadata false**：R≥4 且 false 时
  哈希末尾追加 b"\\xff\\xff\\xff\\xff"（pdfdocument.py:
  404-408）→ 'METAOFF' 照提零告警
- **T3 V2/R3 /Length 96（n=12）**：50 轮扩展每轮只哈希
  result[:n]、key_o/O 链/U 链全用 12 字节 → 'LEN96' 照提
  零告警

判别式：若 P 被忽略或按大端/原值进哈希则 T1 认证失败
ParserError；若 FFFFFFFF 追加缺失则 T2 认证失败；若
/Length 被硬编码 128 则 T3 认证失败；若 n 截断只作用于
返回值不作用于扩展轮次则 T3 也失败——三个参数各锁一个
独立哈希入口。
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

cryptography = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # noqa: E402

PAD = bytes([
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00,
    0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08, 0x2E, 0x2E, 0x00, 0xB6,
    0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53,
    0x69, 0x7A])

ID0 = bytes(range(16))


def _p_le(p: int) -> bytes:
    return (p & 0xFFFFFFFF).to_bytes(4, "little")


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


def _r3_keys(n: int, p: int, tail: bytes = b""):
    h = hashlib.md5(PAD).digest()
    for _ in range(50):
        h = hashlib.md5(h).digest()
    key_o = h[:n]
    O = _rc4(key_o, PAD)
    for i in range(1, 20):
        O = _rc4(_xor_key(key_o, i), O)
    d = hashlib.md5(PAD + O + _p_le(p) + ID0 + tail).digest()
    for _ in range(50):
        d = hashlib.md5(d[:n]).digest()
    fk = d[:n]
    U = _rc4(fk, hashlib.md5(PAD + ID0).digest())
    for i in range(1, 20):
        U = _rc4(_xor_key(fk, i), U)
    return O, U + b"\x00" * 16, fk


def _rc4_obj_key(fk: bytes, oid: int) -> bytes:
    return hashlib.md5(
        fk + oid.to_bytes(3, "little")
        + (0).to_bytes(2, "little")).digest()[:16]


def _aes_obj_key(fk: bytes, oid: int) -> bytes:
    return hashlib.md5(
        fk + oid.to_bytes(3, "little")
        + (0).to_bytes(2, "little") + b"sAlT").digest()[:16]


def _aes_enc(key: bytes, data: bytes) -> bytes:
    iv = bytes(range(16, 32))
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    pad = 16 - len(data) % 16
    return iv + enc.update(data + bytes([pad]) * pad) + enc.finalize()


def _parse_pdf(cs_body: bytes, enc_dict: bytes):
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(cs_body)).encode()
            + b" >>\nstream\n" + cs_body + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: enc_dict,
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
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "k.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def test_p_negative4_restricted():
    """T1：/P -4 进派生哈希 → 'PERMKEY' 照提零告警。"""
    body = b"BT /F1 12 Tf 100 700 Td (PERMKEY) Tj ET"
    O, U, fk = _r3_keys(16, -4)
    d = _parse_pdf(
        _rc4(_rc4_obj_key(fk, 4), body),
        b"<< /Filter /Standard /V 2 /R 3 /Length 128 /O <" + O.hex().encode()
        + b"> /U <" + U.hex().encode() + b"> /P -4 >>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "PERMKEY"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 158.68, 94.484], abs=0.01)
    assert d.warnings == []


def test_aesv2_encrypt_metadata_false():
    """T2：AESV2 + /EncryptMetadata false → 'METAOFF' 照提零告警。"""
    body = b"BT /F1 12 Tf 100 700 Td (METAOFF) Tj ET"
    O, U, fk = _r3_keys(16, -1, b"\xff\xff\xff\xff")
    d = _parse_pdf(
        _aes_enc(_aes_obj_key(fk, 4), body),
        b"<< /Filter /Standard /V 4 /R 4 /Length 128 /CF << /StdCF <<"
        b" /CFM /AESV2 /Length 16 >> >> /StmF /StdCF /StrF /StdCF"
        b" /EncryptMetadata false /O <" + O.hex().encode()
        + b"> /U <" + U.hex().encode() + b"> /P -1 >>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "METAOFF"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 157.336, 94.484], abs=0.01)
    assert d.warnings == []


def test_r3_length_96():
    """T3：/Length 96（n=12 截断扩展）→ 'LEN96' 照提零告警。"""
    body = b"BT /F1 12 Tf 100 700 Td (LEN96) Tj ET"
    O, U, fk = _r3_keys(12, -1)
    d = _parse_pdf(
        _rc4(_rc4_obj_key(fk, 4), body),
        b"<< /Filter /Standard /V 2 /R 3 /Length 96 /O <" + O.hex().encode()
        + b"> /U <" + U.hex().encode() + b"> /P -1 >>")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "LEN96"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 136.684, 94.484], abs=0.01)
    assert d.warnings == []
