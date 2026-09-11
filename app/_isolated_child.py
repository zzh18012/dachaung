"""隔离子进程入口（app.process_isolation 专用，经 subprocess 直接执行）。

stdin 读两段 pickle：父进程 sys.path 列表 + (fn, args)。先恢复 sys.path
再 unpickle 函数引用（函数按模块名引用 pickle，路径不对则 import 失败）；
结果单段 pickle 写 stdout。退出码语义：0=正常回传；4=任务装卸失败；
5=结果不可 pickle——后两者父侧按 ``parser_process_crashed`` 防御处理。
"""

from __future__ import annotations

import io
import pickle
import sys
import traceback
from pathlib import Path


def main() -> int:
    # 本脚本位于 app/ 内，其父目录即项目根——保证 fn 所属模块可导入
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        stream = io.BytesIO(sys.stdin.buffer.read())
        extra_path = pickle.load(stream)
        sys.path.extend(p for p in extra_path if p not in sys.path)
        fn, args = pickle.load(stream)
    except BaseException:  # noqa: BLE001 — 装卸失败让 exitcode 说话
        return 4
    try:
        payload = ("ok", fn(*args))
    except BaseException as e:  # noqa: BLE001 — 子进程边界：任何异常都结构化回传
        payload = ("exc", type(e).__name__, str(e), traceback.format_exc())
    try:
        pickle.dump(payload, sys.stdout.buffer)
        sys.stdout.buffer.flush()
        return 0
    except BaseException:  # noqa: BLE001 — 结果不可 pickle：exitcode≠0 交父侧判崩溃
        return 5


if __name__ == "__main__":
    sys.exit(main())
