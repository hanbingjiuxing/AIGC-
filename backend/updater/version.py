"""版本号解析、比较与本地版本记录读写。"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from .paths import VERSION_FILE

_NUM_RE = re.compile(r"\d+")


def normalize(text: Any) -> str:
    """去掉首尾空白与可选的 v / V 前缀。"""
    s = str(text or "").strip()
    if s[:1] in ("v", "V"):
        s = s[1:]
    return s


def parse(text: Any) -> Tuple[Tuple[int, ...], str]:
    """解析版本号，返回 (数字元组, 预发布后缀)。

    预发布后缀为空字符串表示正式版。支持 1.2.0 / v1.2 / 1.2.0-beta.1 / 1.2.0rc2。
    """
    s = normalize(text)
    main, sep, pre = s.partition("-")
    if not sep:
        m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", s)
        if m and m.group(2):
            main, pre = m.group(1), m.group(2)
    nums = tuple(int(x) for x in _NUM_RE.findall(main)) or (0,)
    return nums, pre.strip()


def compare(a: Any, b: Any) -> int:
    """比较版本号：a < b 返回 -1，a == b 返回 0，a > b 返回 1。"""
    na, prea = parse(a)
    nb, preb = parse(b)

    width = max(len(na), len(nb))
    na = na + (0,) * (width - len(na))
    nb = nb + (0,) * (width - len(nb))
    if na != nb:
        return -1 if na < nb else 1

    # 数字部分相同：正式版优先于预发布版；两者都是预发布版时按字典序比较
    if not prea and not preb:
        return 0
    if not prea:
        return 1
    if not preb:
        return -1
    if prea == preb:
        return 0
    return -1 if prea < preb else 1


def is_newer(remote: Any, local: Any) -> bool:
    return compare(remote, local) > 0


def read_local_version() -> Dict[str, Any]:
    """读取本地版本记录。

    使用 utf-8-sig 以兼容带 BOM 的历史文件（旧版用 utf-8 读取会直接解析失败，
    从而静默把本地版本退化成 0.0.0）。
    """
    if not VERSION_FILE.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            with VERSION_FILE.open("r", encoding=encoding) as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
    return {}


def local_version_string() -> str:
    return normalize(read_local_version().get("version") or "0.0.0")


def write_local_version(payload: Dict[str, Any]) -> None:
    """写入版本记录（不带 BOM）。"""
    VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = VERSION_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    tmp.replace(VERSION_FILE)
