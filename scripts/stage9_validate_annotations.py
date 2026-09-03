# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注校验 CLI。

用法（项目 venv python 运行）：
  python scripts/stage9_validate_annotations.py \
      --manifest samples/private/stage9-corpus/manifest.draft.json \
      --annotations samples/private/stage9-corpus/annotations \
      [--full-set] [--report outputs/stage9-validation.json] [--json]

退出码：0 = 全部通过；1 = 存在校验失败；2 = 输入/IO 错误（文件缺失、
JSON 解析失败等）。--full-set 在单篇校验之上追加 split 分层约束
（14/4/6、三域全覆盖、全部正选已标注）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stage9.validation import (  # noqa: E402
    load_json,
    validate_annotation,
    validate_split_constraints,
)


def collect_annotation_files(paths):
    files = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 9 批次 26 标注校验（契约见 "
                    "docs/stage9-batch26-design.md §7）")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--annotations", nargs="+", required=True,
                        help="标注 JSON 文件或目录")
    parser.add_argument("--full-set", action="store_true",
                        help="追加 split 分层约束（冻结/终检用）")
    parser.add_argument("--report", help="失败报告 JSON 输出路径")
    parser.add_argument("--json", action="store_true",
                        help="stdout 输出机器可读报告")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print("manifest 不存在: %s" % manifest_path, file=sys.stderr)
        return 2
    try:
        manifest_data = load_json(manifest_path)
    except (OSError, json.JSONDecodeError) as exc:
        print("manifest 读取失败: %s" % exc, file=sys.stderr)
        return 2
    manifest_index = {d.get("doc_id"): d
                      for d in manifest_data.get("docs", [])
                      if isinstance(d, dict)}

    files = collect_annotation_files(args.annotations)
    if not files:
        print("未找到标注文件", file=sys.stderr)
        return 2

    failures = []
    annotated = set()
    io_errors = 0
    for path in files:
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            print("标注读取失败 %s: %s" % (path, exc), file=sys.stderr)
            io_errors += 1
            continue
        doc_id, fails = validate_annotation(data, manifest_index)
        if doc_id:
            annotated.add(doc_id)
        for fail in fails:
            failures.append({"file": str(path), "doc_id": doc_id,
                             **fail.to_json()})

    summary = {"checked_files": len(files), "failures": len(failures),
               "io_errors": io_errors}
    if args.full_set:
        split_fails, split_summary = validate_split_constraints(
            manifest_data, annotated)
        for fail in split_fails:
            failures.append({"file": str(manifest_path), "doc_id": None,
                             **fail.to_json()})
        summary["split"] = split_summary

    report = {"summary": summary, "failures": failures}
    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        for item in failures:
            print("[%s] %s %s: %s" % (item["code"], item["doc_id"] or "-",
                                      item["file"], item["detail"]))
        print("检查 %d 个文件：%d 项失败，%d 个 IO 错误"
              % (summary["checked_files"], summary["failures"], io_errors))
        if args.full_set:
            print("split: %s" % json.dumps(
                summary["split"], ensure_ascii=False))

    if io_errors:
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
