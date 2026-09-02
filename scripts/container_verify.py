#!/usr/bin/env python3
"""批次 25 容器交付验证脚本（Stage 8 可复现交付，裁决 D-C/D4 修订版）。

用法（解释器必须是项目 venv 的 python——宿主侧 parse/validate 依赖项目环境）：
    python scripts/container_verify.py --image kvfs-doc-parser:ci
    python scripts/container_verify.py --artifact dist/kvfs-doc-parser_<sha>-img.tar.gz

验证步骤：
  1. Docker daemon 预检（不可用 → exit 3）；
  2. --artifact 模式：先校验 .sha256 边车文件（不匹配 → exit 4），再 docker load，
     随后与 --image 模式走同一套显式镜像检查；
  3. 镜像契约检查：USER=app、ENTRYPOINT=[venv python -m app.cli]、CMD=[--help]、
     4 个 OCI 标签非空（不符 → exit 5）；
  4. 合成语料（md/txt/docx，docx 为 stdlib zipfile 手工构造的最小 OOXML）；
  5. 容器侧 parse/validate：加固 flags（--read-only --tmpfs /tmp:rw,noexec,nosuid
     --network none，/input 只读挂载，/output 唯一可写挂载）；
  6. 宿主侧 parse/validate（同一语料、同一 --parser auto、同一 --max-chars）；
  7. D-C 深度语义对照：双端输出先过 schema（validate），再剔除实证可变的来源
     字段（顶层 source_path、document.metadata.image_output_dir），其余字段
     逐一相等；source_hash 与 document_id 必须显式相等；
  8. 分区断言：chunk.source_element_ids 必须构成 element id 的精确划分
     （非空、⊆ 全集、chunk 内无重复、两两不相交、并集=全集）；
  9. 非 root 探针（os.getuid()==1000）与输入只读探针（EROFS/EACCES/EPERM）；
  10. inspect-parser / list-parsers 宿主↔容器输出一致。

退出码：0=全部通过；2=用法错误；3=daemon 不可用；4=制品校验和不符；
4/5=镜像检查失败；6=容器/宿主执行失败；7=语义对照或分区断言失败。
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_ENTRYPOINT = ["/app/.venv/bin/python", "-m", "app.cli"]
EXPECTED_CMD = ["--help"]
EXPECTED_USER = "app"
REQUIRED_LABELS = (
    "org.opencontainers.image.title",
    "org.opencontainers.image.version",
    "org.opencontainers.image.revision",
    "org.opencontainers.image.created",
)

# D-C：宿主↔容器唯一可变的来源字段（实证登记于 ADOPTION 批次 25）。
# 顶层 source_path = 输入挂载路径；metadata.image_output_dir = 输出根目录派生。
EXCLUDED_TOP_FIELDS = ("source_path",)
EXCLUDED_METADATA_KEYS = ("image_output_dir",)
# 身份字段必须显式相等（不是"剔除后不管"）。
IDENTITY_FIELDS = ("source_hash", "document_id")

ACCEPTED_RO_ERRNOS = (errno.EROFS, errno.EACCES, errno.EPERM)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DAEMON = 3
EXIT_CHECKSUM = 4
EXIT_IMAGE = 5
EXIT_RUN = 6
EXIT_COMPARE = 7

SAMPLE_MD = """# 容器验证标题

批次 25 合成 markdown 语料：固定内容，宿主与容器双端解析对照。

## 二级标题

- 列表项一
- 列表项二

收尾段落。
"""

SAMPLE_TXT = """批次 25 合成纯文本语料
第二行：固定内容
第三行：用于 line_address locator 对照
"""

_DOC_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

_DOC_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

_DOC_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>
"""

_DOC_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>合成文档标题</w:t></w:r></w:p>
<w:p><w:r><w:t>批次 25 容器验证用合成段落，内容固定。</w:t></w:r></w:p>
<w:p><w:r><w:t>第二段落：用于宿主与容器输出对照。</w:t></w:r></w:p>
</w:body></w:document>
"""

SYNTHETIC_INPUTS = {
    "sample.md": lambda p: p.write_text(SAMPLE_MD, encoding="utf-8"),
    "sample.txt": lambda p: p.write_text(SAMPLE_TXT, encoding="utf-8"),
    "sample.docx": lambda p: _write_synthetic_docx(p),
}


# ---------- 纯函数（tests/test_container_verify_logic.py 直接导入测试） ----------

def _write_synthetic_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _DOC_CONTENT_TYPES)
        z.writestr("_rels/.rels", _DOC_RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_DOC_RELS)
        z.writestr("word/styles.xml", _DOC_STYLES)
        z.writestr("word/document.xml", _DOC_DOCUMENT)


def strip_provenance(doc: dict) -> dict:
    """剔除实证可变的来源字段（浅拷贝顶层 + metadata，不动原 dict）。"""
    d = dict(doc)
    for k in EXCLUDED_TOP_FIELDS:
        d.pop(k, None)
    md = dict(d.get("metadata") or {})
    for k in EXCLUDED_METADATA_KEYS:
        md.pop(k, None)
    d["metadata"] = md
    return d


def _deep_diff(path: str, a, b) -> list[str]:
    if a == b:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: 仅容器侧存在 = {b[k]!r}")
            elif k not in b:
                out.append(f"{path}.{k}: 仅宿主侧存在 = {a[k]!r}")
            else:
                out.extend(_deep_diff(f"{path}.{k}", a[k], b[k]))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{path}: 长度 host={len(a)} container={len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(_deep_diff(f"{path}[{i}]", x, y))
        return out
    return [f"{path}: host={a!r} container={b!r}"]


def compare_documents(host: dict, container: dict) -> list[str]:
    """D-C 深度语义对照：身份字段显式相等 + 剔除来源字段后逐字段相等。"""
    problems: list[str] = []
    for f in IDENTITY_FIELDS:
        if host.get(f) != container.get(f):
            problems.append(
                f"身份字段 {f} 不一致: host={host.get(f)!r} container={container.get(f)!r}"
            )
    h, c = strip_provenance(host), strip_provenance(container)
    problems.extend(_deep_diff("document", h, c))
    return problems


def check_partition(doc: dict) -> list[str]:
    """chunk.source_element_ids 必须构成 element id 的精确划分。"""
    problems: list[str] = []
    elements = doc.get("elements") or []
    if not elements:
        return ["elements 为空"]
    ids = [e.get("element_id", "") for e in elements]
    if any(not i for i in ids):
        problems.append("存在空 element_id")
    id_set = set(ids)
    if len(id_set) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        problems.append(f"element_id 重复: {dupes[:5]}")
    chunks = doc.get("chunks") or []
    if not chunks:
        problems.append("chunks 为空")
        return problems
    used: list[str] = []
    for ch in chunks:
        cid = ch.get("chunk_id", "?")
        srcs = ch.get("source_element_ids") or []
        if not srcs:
            problems.append(f"chunk {cid}: source_element_ids 为空")
            continue
        if len(set(srcs)) != len(srcs):
            problems.append(f"chunk {cid}: 内部 source_element_ids 重复 {srcs}")
        unknown = sorted(set(srcs) - id_set)
        if unknown:
            problems.append(f"chunk {cid}: 引用不存在的 element {unknown[:5]}")
        used.extend(srcs)
    if len(set(used)) != len(used):
        problems.append("chunk 间 source_element_ids 有重叠（违反两两不相交）")
    uncovered = sorted(id_set - set(used))
    if uncovered:
        problems.append(f"并集≠全集，未覆盖 element: {uncovered[:5]}（共 {len(uncovered)} 个）")
    return problems


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_sha256_sidecar(artifact: Path) -> str:
    """读取 `<artifact>.sha256` 边车（接受 `hash  filename` 或纯 hash 行）。"""
    sidecar = Path(str(artifact) + ".sha256")
    text = sidecar.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"sha256 边车为空: {sidecar}")
    return text.split()[0].lower()


# ---------- 子进程与 docker 辅助 ----------

def _run(cmd: list[str], timeout: int = 300, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, cwd=cwd,
    )


def _vol(p: Path, suffix: str) -> str:
    """卷挂载规范形式：正斜杠（Windows 盘符路径 Docker Desktop 亦接受）。"""
    return f"{str(p.resolve()).replace(chr(92), '/')}{suffix}"


def _docker_hardened(image: str, extra: list[str], *, entrypoint_python: bool = False,
                     inputs: Path | None = None, outputs: Path | None = None) -> list[str]:
    cmd = ["docker", "run", "--rm", "--read-only",
           "--tmpfs", "/tmp:rw,noexec,nosuid", "--network", "none"]
    if inputs is not None:
        cmd += ["-v", _vol(inputs, ":/input:ro")]
    if outputs is not None:
        cmd += ["-v", _vol(outputs, ":/output")]
    if entrypoint_python:
        cmd += ["--entrypoint", "/app/.venv/bin/python"]
    cmd.append(image)
    cmd.extend(extra)
    return cmd


def _host_cli(args: list[str]) -> subprocess.CompletedProcess:
    return _run([sys.executable, "-m", "app.cli", *args], timeout=300,
                cwd=str(REPO_ROOT))


# ---------- 主流程 ----------

def preflight_daemon() -> tuple[bool, str]:
    r = _run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=60)
    if r.returncode != 0:
        return False, (r.stderr or r.stdout).strip()[:500]
    return True, r.stdout.strip()


def check_image_contract(tag: str) -> list[str]:
    r = _run(["docker", "image", "inspect", tag], timeout=120)
    if r.returncode != 0:
        return [f"docker image inspect 失败: {(r.stderr or r.stdout).strip()[:300]}"]
    info = json.loads(r.stdout)[0]
    cfg = info.get("Config") or {}
    problems: list[str] = []
    if cfg.get("User") != EXPECTED_USER:
        problems.append(f"User={cfg.get('User')!r}，预期 {EXPECTED_USER!r}")
    if cfg.get("Entrypoint") != EXPECTED_ENTRYPOINT:
        problems.append(f"Entrypoint={cfg.get('Entrypoint')!r}，预期 {EXPECTED_ENTRYPOINT!r}")
    if cfg.get("Cmd") != EXPECTED_CMD:
        problems.append(f"Cmd={cfg.get('Cmd')!r}，预期 {EXPECTED_CMD!r}")
    labels = cfg.get("Labels") or {}
    for key in REQUIRED_LABELS:
        val = labels.get(key)
        if not isinstance(val, str) or not val.strip():
            problems.append(f"OCI 标签 {key} 缺失或为空: {val!r}")
    return problems


def load_artifact(artifact: Path) -> tuple[str | None, str]:
    """校验和先行 → docker load → 返回加载出的 tag。"""
    try:
        expected = read_sha256_sidecar(artifact)
    except (OSError, ValueError) as e:
        return None, f"读取 sha256 边车失败: {e}"
    actual = sha256_of(artifact)
    if expected != actual:
        return None, f"校验和不符: sidecar={expected} actual={actual}"
    r = _run(["docker", "load", "-i", str(artifact)], timeout=900)
    if r.returncode != 0:
        return None, f"docker load 失败: {(r.stderr or r.stdout).strip()[:300]}"
    tag = None
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("Loaded image:"):
            tag = line.split(":", 1)[1].strip()
            break
    if tag is None:
        return None, f"docker load 输出未包含 Loaded image 行: {r.stdout[:300]!r}"
    return tag, ""


def run_semantic_suite(tag: str) -> tuple[list[str], dict]:
    """合成语料 → 双端 parse/validate → D-C 对照 + 分区断言 + 探针 + smoke。"""
    problems: list[str] = []
    detail: dict = {"files": {}}
    with tempfile.TemporaryDirectory(prefix="b25-verify-") as td:
        tdp = Path(td)
        inputs = tdp / "inputs"
        host_out = tdp / "host-out"
        cont_out = tdp / "cont-out"
        inputs.mkdir()
        host_out.mkdir()
        cont_out.mkdir()
        # Linux CI：容器以 uid 1000 写 /output，宿主运行用户可能不同 → 放开目录权限
        os.chmod(host_out, 0o777)
        os.chmod(cont_out, 0o777)
        for name, writer in SYNTHETIC_INPUTS.items():
            writer(inputs / name)

        for name in sorted(SYNTHETIC_INPUTS):
            fprobs: list[str] = []
            in_path = inputs / name
            host_json = host_out / f"{name}.json"
            cont_json = cont_out / f"{name}.json"

            hr = _host_cli(["parse", str(in_path), "-o", str(host_json),
                            "--parser", "auto", "--max-chars", "800"])
            if hr.returncode != 0 or not host_json.exists():
                problems.append(f"{name}: 宿主 parse 失败 rc={hr.returncode}: "
                                f"{(hr.stderr or hr.stdout).strip()[:300]}")
                detail["files"][name] = {"status": "host_parse_failed"}
                continue
            hv = _host_cli(["validate", str(host_json)])
            if hv.returncode != 0:
                problems.append(f"{name}: 宿主 validate 失败: {(hv.stdout or hv.stderr).strip()[:300]}")
                detail["files"][name] = {"status": "host_validate_failed"}
                continue

            cr = _run(_docker_hardened(
                tag, ["parse", f"/input/{name}", "-o", f"/output/{name}.json",
                      "--parser", "auto", "--max-chars", "800"],
                inputs=inputs, outputs=cont_out))
            if cr.returncode != 0 or not cont_json.exists():
                problems.append(f"{name}: 容器 parse 失败 rc={cr.returncode}: "
                                f"{(cr.stderr or cr.stdout).strip()[:300]}")
                detail["files"][name] = {"status": "container_parse_failed"}
                continue
            cv = _run(_docker_hardened(
                tag, ["validate", f"/output/{name}.json"],
                inputs=inputs, outputs=cont_out))
            if cv.returncode != 0:
                problems.append(f"{name}: 容器 validate 失败: {(cv.stdout or cv.stderr).strip()[:300]}")
                detail["files"][name] = {"status": "container_validate_failed"}
                continue

            host_doc = json.loads(host_json.read_text(encoding="utf-8"))
            cont_doc = json.loads(cont_json.read_text(encoding="utf-8"))
            diff = compare_documents(host_doc, cont_doc)
            part_h = check_partition(host_doc)
            part_c = check_partition(cont_doc)
            if diff or part_h or part_c:
                problems.extend(f"{name}: {m}" for m in diff + part_h + part_c)
                detail["files"][name] = {"status": "mismatch",
                                         "diff": diff, "partition_host": part_h,
                                         "partition_container": part_c}
            else:
                detail["files"][name] = {
                    "status": "match",
                    "source_hash": host_doc.get("source_hash"),
                    "element_count": len(host_doc.get("elements") or []),
                    "chunk_count": len(host_doc.get("chunks") or []),
                }

        # 非 root 探针
        ur = _run(_docker_hardened(tag, ["-c", "import os; print(os.getuid())"],
                                   entrypoint_python=True))
        uid = (ur.stdout or "").strip()
        if ur.returncode != 0 or uid != "1000":
            problems.append(f"非 root 探针失败: rc={ur.returncode} uid={uid!r}")
        detail["container_uid"] = uid

        # 输入只读探针：向 /input 追加写必须失败且 errno ∈ {EROFS, EACCES, EPERM}
        probe = (
            "import errno,sys\n"
            "try:\n"
            "    open('/input/sample.md','a').close()\n"
            "    sys.exit(10)\n"
            "except OSError as e:\n"
            "    sys.exit(0 if e.errno in (errno.EROFS, errno.EACCES, errno.EPERM) else 20)\n"
        )
        rr = _run(_docker_hardened(tag, ["-c", probe], entrypoint_python=True,
                                   inputs=inputs, outputs=cont_out))
        if rr.returncode == 10:
            problems.append("输入只读探针失败：/input 竟然可写")
        elif rr.returncode == 20:
            problems.append(f"输入只读探针失败：意外 errno: {(rr.stdout or rr.stderr).strip()[:200]}")
        elif rr.returncode != 0:
            problems.append(f"输入只读探针异常 rc={rr.returncode}: {(rr.stderr or '')[ :200]}")
        detail["input_ro_probe_rc"] = rr.returncode

        # inspect-parser / list-parsers 宿主↔容器一致
        hi = _host_cli(["inspect-parser", "markdown", "--json"])
        ci = _run(_docker_hardened(tag, ["inspect-parser", "markdown", "--json"]))
        if hi.returncode != 0 or ci.returncode != 0:
            problems.append(f"inspect-parser smoke 失败: host rc={hi.returncode} container rc={ci.returncode}")
        else:
            try:
                if json.loads(hi.stdout) != json.loads(ci.stdout):
                    problems.append("inspect-parser markdown --json 宿主≠容器")
            except json.JSONDecodeError as e:
                problems.append(f"inspect-parser 输出非 JSON: {e}")
        hl = _host_cli(["list-parsers", "--json"])
        cl = _run(_docker_hardened(tag, ["list-parsers", "--json"]))
        if hl.returncode != 0 or cl.returncode != 0:
            problems.append(f"list-parsers smoke 失败: host rc={hl.returncode} container rc={cl.returncode}")
        else:
            try:
                if json.loads(hl.stdout) != json.loads(cl.stdout):
                    problems.append("list-parsers --json 宿主≠容器")
            except json.JSONDecodeError as e:
                problems.append(f"list-parsers 输出非 JSON: {e}")

    return problems, detail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="批次 25 容器交付验证")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--image", help="已构建镜像 tag（如 kvfs-doc-parser:ci）")
    g.add_argument("--artifact", help="docker save|gzip 制品路径（须有同名 .sha256 边车）")
    args = ap.parse_args(argv)

    ok, info = preflight_daemon()
    if not ok:
        print(json.dumps({"result": "FAIL", "stage": "daemon_preflight",
                          "error": info}, ensure_ascii=False, indent=2))
        return EXIT_DAEMON

    mode = "image" if args.image else "artifact"
    tag = args.image
    if args.artifact:
        artifact = Path(args.artifact)
        if not artifact.is_file():
            print(json.dumps({"result": "FAIL", "stage": "artifact_missing",
                              "error": str(artifact)}, ensure_ascii=False, indent=2))
            return EXIT_CHECKSUM
        tag, err = load_artifact(artifact)
        if tag is None:
            print(json.dumps({"result": "FAIL", "stage": "artifact_load",
                              "error": err}, ensure_ascii=False, indent=2))
            return EXIT_CHECKSUM if err.startswith(("读取", "校验和")) else EXIT_IMAGE

    image_problems = check_image_contract(tag)
    if image_problems:
        print(json.dumps({"result": "FAIL", "stage": "image_contract", "mode": mode,
                          "image": tag, "problems": image_problems},
                         ensure_ascii=False, indent=2))
        return EXIT_IMAGE

    problems, detail = run_semantic_suite(tag)
    summary = {
        "result": "PASS" if not problems else "FAIL",
        "mode": mode,
        "image": tag,
        "daemon": info,
        "checks": {
            "image_contract": "PASS",
            "semantic_compare_and_partition": "PASS" if not problems else "FAIL",
        },
        "problems": problems,
        "detail": detail,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return EXIT_OK if not problems else EXIT_COMPARE


if __name__ == "__main__":
    sys.exit(main())
