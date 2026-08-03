"""一次性生成合成样例 + 跑 CLI + 校验，用于演示完整流程。

这个脚本只用于演示/手动验证，不参与测试套件。
合成样例是临时文件，跑完就删。
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "outputs" / "_demo"
TMP.mkdir(parents=True, exist_ok=True)


def make_docx(path: Path) -> None:
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第一章 项目概述</w:t></w:r></w:p>
    <w:p><w:r><w:t>本项目目标：构建一个最小可用的文档解析原型。它支持 PDF 和 DOCX 两种格式。</w:t></w:r></w:p>
    <w:p><w:r><w:t>本阶段不实现 OCR、向量化和 KVFS 接入。这些会在后续阶段处理。</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1 范围</w:t></w:r></w:p>
    <w:p><w:r><w:t>当前最小闭环包含提取、统一模型、分块和校验四个步骤。</w:t></w:r></w:p>
    <w:tbl>
      <w:tr><w:tc><w:p><w:r><w:t>阶段</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>交付</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>骨架</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>2</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>解析器</w:t></w:r></w:p></w:tc></w:tr>
    </w:tbl>
  </w:body>
</w:document>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    ct = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)


def main() -> int:
    src = TMP / "demo.docx"
    out = TMP / "demo.json"
    make_docx(src)
    print(f"[setup] 已生成合成样例: {src}")

    # 调用 CLI
    import subprocess
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [
            str(ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m", "app.cli",
            str(src), "-o", str(out),
            "--parser", "fallback",
            "--max-chars", "200",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    print(f"[cli] returncode={proc.returncode}")
    print(f"[cli] stdout={proc.stdout!r}")
    if proc.stderr:
        print(f"[cli] stderr={proc.stderr!r}")
    if proc.returncode != 0:
        return proc.returncode

    # 展示简化 JSON（只显示前几个 element/chunk + 关键字段）
    data = json.loads(out.read_text(encoding="utf-8"))
    print()
    print("=== 简化 JSON 示例（仅展示关键字段，省略 confidence/metadata 等）===")
    slim = {
        "schema_version": data["schema_version"],
        "document_id": data["document_id"],
        "source_type": data["source_type"],
        "source_hash": data["source_hash"][:16] + "...(64位 SHA-256)",
        "parser_name": data["parser_name"],
        "elements_total": len(data["elements"]),
        "elements[0:2]": [
            {
                "element_id": e["element_id"],
                "type": e["type"],
                "content": e["content"][:60] + ("..." if len(e["content"]) > 60 else ""),
                "source_locator": e["source_locator"],
            }
            for e in data["elements"][:2]
        ],
        "chunks_total": len(data["chunks"]),
        "chunks[0:1]": [
            {
                "chunk_id": c["chunk_id"],
                "text": c["text"][:80] + ("..." if len(c["text"]) > 80 else ""),
                "source_element_ids": c["source_element_ids"],
            }
            for c in data["chunks"][:1]
        ],
        "warnings": data["warnings"],
        "errors": data["errors"],
    }
    print(json.dumps(slim, ensure_ascii=False, indent=2))

    # 验证
    proc2 = subprocess.run(
        [
            str(ROOT / ".venv" / "Scripts" / "python.exe"),
            "-m", "app.cli",
            str(out), "--validate",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
    )
    print()
    print(f"[validate] returncode={proc2.returncode}")
    print(f"[validate] stdout={proc2.stdout!r}")

    # 清理
    src.unlink()
    out.unlink()
    try:
        TMP.rmdir()
    except OSError:
        pass
    print("[cleanup] 合成样例已删除（outputs/_demo 是临时目录）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
