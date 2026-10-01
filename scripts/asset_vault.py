#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资源保险箱命令行入口。

实现放在 `backend/utils/asset_vault.py`：后端运行期也要用它（按需解密、
明文不落盘），所以模块归到 backend/utils/ 下；这里只保留一层入口，
让文档里的命令照旧可用：

    python scripts/asset_vault.py keygen
    python scripts/asset_vault.py encrypt <明文> --out assets/encrypted/<名字>.enc
    python scripts/asset_vault.py decrypt <密文> --out <明文>
    python scripts/asset_vault.py verify  <密文> [--expect <明文>]
    python scripts/asset_vault.py info    <密文>

直接运行 `python backend/utils/asset_vault.py ...` 效果相同。
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.asset_vault import main  # noqa: E402  —— 必须在 sys.path 调整之后再导入

if __name__ == "__main__":
    raise SystemExit(main())
