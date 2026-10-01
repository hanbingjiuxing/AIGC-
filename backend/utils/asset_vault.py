#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资源保险箱：把不适合明文入库的源文件加密归档。

为什么需要它
------------
有些文件必须留在手边，却不适合明文进仓库。典型例子是 About 页头像
（"古希腊掌管 AIGC 社信息系统的神"）的高清母版 tx.png：线上用的是
frontend/public/tx.png 的压缩版，而放在项目根目录的母版会被 git 直接跟踪，
仓库一旦公开就等于把原图一起发出去。

本脚本把母版加密成密文归档到 assets/encrypted/，仓库里只留下无法还原的字节；
密钥保存在 data/secrets/（已被 .gitignore 忽略、升级时被更新器整体保护），
因此密文可以随仓库分发，而内容只对持有密钥的人可见。

加密设计
--------
* 算法：AES-256-GCM（认证加密）。密文或文件头被改动一个字节都会解密失败，
  不会解出"看起来正常"的坏文件。
* 容器：8 字节 magic + 4 字节头部长度 + 头部 JSON + 密文。
  整段头部（magic/length/JSON）作为 AAD 参与认证，改动同样会被检出。
* 密钥派生：scrypt（N=32768, r=8, p=1, dklen=32）。密钥材料二选一：
    - 密钥文件：32 字节随机数的十六进制文本，默认 data/secrets/asset-vault.key
    - 口令：--passphrase 交互输入，不落盘、不进命令历史，便于换机器还原
* 明文摘要：sha256 记录在文件头，解密后再校验一次。

常用命令
--------
    python scripts/asset_vault.py keygen                     # 生成密钥文件
    python scripts/asset_vault.py encrypt <明文> [--out <密文>]
    python scripts/asset_vault.py decrypt <密文> [--out <明文>]
    python scripts/asset_vault.py verify  <密文>             # 只解密校验，不落地
    python scripts/asset_vault.py info    <密文>             # 只看文件头

依赖：cryptography（pip install cryptography）。系统本身不需要它，只有本脚本用。
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import secrets
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

MAGIC = b"DSHVAULT"
FORMAT_NAME = "dsh-asset-vault"
VERSION = 1
CIPHER_NAME = "AES-256-GCM"
SCRYPT_N = 1 << 15
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32
SALT_LEN = 16
NONCE_LEN = 12
#: OpenSSL 默认 maxmem 只有 32 MiB，而 N=32768/r=8 需要 128*N*r = 32 MiB 以上
SCRYPT_MAXMEM = 128 * SCRYPT_N * SCRYPT_R * 2
HEADER_LIMIT = 64 * 1024
CHUNK = 1 << 20

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # backend/utils/ -> backend/ -> 项目根
DEFAULT_KEY_FILE = PROJECT_ROOT / "data" / "secrets" / "asset-vault.key"


class VaultError(Exception):
    """可预期的使用错误：以友好信息退出，不打印堆栈。"""


def _reconfigure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _aesgcm():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover
        raise VaultError("缺少依赖 cryptography，请先执行：pip install cryptography") from exc
    return AESGCM


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{num} B"


# --------------------------------------------------------------------------- #
# 密钥
# --------------------------------------------------------------------------- #

def decode_key_material(raw: bytes, origin: str) -> bytes:
    """密钥文件允许三种写法：64 位十六进制文本 / base64 文本 / 32 字节原始数据。"""
    text = raw.strip()
    if len(text) == KEY_LEN * 2:
        try:
            key = bytes.fromhex(text.decode("ascii"))
            if len(key) == KEY_LEN:
                return key
        except (ValueError, UnicodeDecodeError):
            pass
    if len(text) == 44:
        try:
            key = base64.b64decode(text, validate=True)
            if len(key) == KEY_LEN:
                return key
        except Exception:
            pass
    if len(raw) == KEY_LEN:
        return raw
    raise VaultError(f"密钥文件格式不正确（应为 {KEY_LEN} 字节随机数，或等值的十六进制/base64 文本）：{origin}")


def load_key_file(path: Path) -> bytes:
    if not path.is_file():
        raise VaultError(
            f"密钥文件不存在：{path}\n"
            f"先执行：python scripts/asset_vault.py keygen"
        )
    return decode_key_material(path.read_bytes(), str(path))


def create_key_file(path: Path, force: bool = False) -> bytes:
    if path.exists() and not force:
        raise VaultError(f"密钥文件已存在，未覆盖：{path}\n（确实要重建请加 --force，旧密文将再也无法解密）")
    key = secrets.token_bytes(KEY_LEN)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key.hex() + "\n", encoding="ascii")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return key


def read_passphrase(confirm: bool) -> bytes:
    passphrase = getpass.getpass("口令：" if not confirm else "设置口令：")
    if not passphrase:
        raise VaultError("口令不能为空")
    if confirm:
        again = getpass.getpass("再输一次：")
        if again != passphrase:
            raise VaultError("两次输入的口令不一致")
    return passphrase.encode("utf-8")


def derive_key(material: bytes, salt: bytes) -> bytes:
    return hashlib.scrypt(
        material, salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
        dklen=KEY_LEN, maxmem=SCRYPT_MAXMEM,
    )


def key_check(key: bytes) -> str:
    """密钥校验值：用于确认"手上这把密钥能不能开这个密文"，不泄露密钥本身。"""
    return sha256_bytes(b"dsh-asset-vault:" + key)[:16]


# --------------------------------------------------------------------------- #
# 容器读写
# --------------------------------------------------------------------------- #

def build_header(source: Path, plaintext: bytes, mode: str, salt: bytes,
                 nonce: bytes, check: str) -> bytes:
    header = {
        "format": FORMAT_NAME,
        "version": VERSION,
        "cipher": CIPHER_NAME,
        "key_mode": mode,
        "kdf": {
            "name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P,
            "dklen": KEY_LEN, "salt": b64e(salt),
        },
        "nonce": b64e(nonce),
        "source_name": source.name,
        "source_size": len(plaintext),
        "source_sha256": sha256_bytes(plaintext),
        "key_check": check,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return json.dumps(header, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def pack_container(header_bytes: bytes, ciphertext: bytes) -> bytes:
    return MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes + ciphertext


def read_container(path: Path) -> Tuple[bytes, dict, bytes]:
    """返回 (参与认证的头部前缀, 头部字典, 密文)。"""
    if not path.is_file():
        raise VaultError(f"文件不存在：{path}")
    raw = path.read_bytes()
    prefix_len = len(MAGIC) + 4
    if len(raw) < prefix_len or raw[:len(MAGIC)] != MAGIC:
        raise VaultError(f"不是本工具生成的保险箱文件（magic 不匹配）：{path}")
    (header_len,) = struct.unpack(">I", raw[len(MAGIC):prefix_len])
    if not 0 < header_len <= HEADER_LIMIT or len(raw) < prefix_len + header_len:
        raise VaultError(f"文件头损坏（长度字段异常）：{path}")
    header_bytes = raw[prefix_len:prefix_len + header_len]
    try:
        header = json.loads(header_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VaultError(f"文件头无法解析：{path}") from exc
    if not isinstance(header, dict) or header.get("format") != FORMAT_NAME:
        raise VaultError(f"文件头格式不符：{path}")
    if header.get("version") != VERSION:
        raise VaultError(f"不支持的保险箱版本：{header.get('version')!r}（本工具支持 {VERSION}）")
    if header.get("cipher") != CIPHER_NAME:
        raise VaultError(f"不支持的加密算法：{header.get('cipher')!r}")
    return raw[:prefix_len + header_len], header, raw[prefix_len + header_len:]


def unlock(header: dict, key_file: Path, use_passphrase: bool) -> bytes:
    mode = header.get("key_mode")
    if mode == "passphrase" or use_passphrase:
        material = read_passphrase(confirm=False)
    else:
        material = load_key_file(key_file)
    kdf = header.get("kdf") or {}
    salt = b64d(kdf["salt"])
    key = derive_key(material, salt)
    check = header.get("key_check")
    if check and key_check(key) != check:
        raise VaultError(
            "密钥不符：这把密钥/口令解不开该密文。\n"
            f"（密文要求的密钥校验值 {check}，当前密钥为 {key_check(key)}）"
        )
    return key


def decrypt_plaintext(vault: Path, key_file: Path, use_passphrase: bool) -> Tuple[bytes, dict]:
    aad, header, ciphertext = read_container(vault)
    key = unlock(header, key_file, use_passphrase)
    try:
        plaintext = _aesgcm()(key).decrypt(b64d(header["nonce"]), ciphertext, aad)
    except Exception as exc:
        raise VaultError("解密失败：密文或文件头已被改动，或密钥不对。") from exc
    if len(plaintext) != header.get("source_size") or sha256_bytes(plaintext) != header.get("source_sha256"):
        raise VaultError("解密成功但内容校验不一致，已放弃输出（文件可能已损坏）。")
    return plaintext, header


def guard_output(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise VaultError(f"输出文件已存在，未覆盖：{path}\n（确需覆盖请加 --force）")


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #

def cmd_keygen(args: argparse.Namespace) -> int:
    path = Path(args.key_file)
    key = create_key_file(path, force=args.force)
    print(f"已生成密钥文件：{path}")
    print(f"  密钥文件指纹：{key_check(key)}（核对备份用；与密文头里的\"解密校验值\"不是同一个值）")
    print("  注意：密钥不随仓库分发。请另存一份到密码管理器或移动介质，")
    print("        否则 data/secrets/ 一旦丢失，assets/encrypted/ 里的密文将无法还原。")
    return 0


def cmd_encrypt(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if not source.is_file():
        raise VaultError(f"待加密文件不存在：{source}")
    out = Path(args.out) if args.out else source.with_suffix(source.suffix + ".enc")
    guard_output(out, args.force)

    plaintext = source.read_bytes()
    mode = "passphrase" if args.passphrase else "keyfile"
    if args.passphrase:
        material = read_passphrase(confirm=True)
    else:
        key_file = Path(args.key_file)
        if not key_file.is_file():
            print(f"未找到密钥文件，先自动生成：{key_file}")
            create_key_file(key_file)
        material = load_key_file(key_file)

    salt = secrets.token_bytes(SALT_LEN)
    nonce = secrets.token_bytes(NONCE_LEN)
    key = derive_key(material, salt)
    header_bytes = build_header(source, plaintext, mode, salt, nonce, key_check(key))
    aad = MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes
    ciphertext = _aesgcm()(key).encrypt(nonce, plaintext, aad)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(pack_container(header_bytes, ciphertext))

    print(f"已加密：{source}  ->  {out}")
    print(f"  明文：{human_size(len(plaintext))}  密文：{human_size(out.stat().st_size)}  算法：{CIPHER_NAME}")
    print(f"  明文 sha256：{sha256_bytes(plaintext)}")
    print(f"  密钥模式：{'口令' if mode == 'passphrase' else '密钥文件'}   解密校验值：{key_check(key)}")
    if mode == "keyfile":
        print(f"  密钥文件：{args.key_file}")
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    vault = Path(args.source)
    out = Path(args.out) if args.out else (vault.with_suffix("") if vault.suffix.lower() == ".enc"
                                           else vault.with_suffix(vault.suffix + ".dec"))
    guard_output(out, args.force)

    plaintext, header = decrypt_plaintext(vault, Path(args.key_file), args.passphrase)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(plaintext)

    print(f"已解密：{vault}  ->  {out}")
    print(f"  原始文件名：{header.get('source_name')}  大小：{human_size(len(plaintext))}")
    print(f"  sha256：{sha256_bytes(plaintext)}")
    print(f"  加密时间：{header.get('created_utc')}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    vault = Path(args.source)
    plaintext, header = decrypt_plaintext(vault, Path(args.key_file), args.passphrase)
    print(f"校验通过：{vault}")
    print(f"  原始文件名：{header.get('source_name')}  大小：{human_size(len(plaintext))}")
    print(f"  sha256：{sha256_bytes(plaintext)}")
    if args.expect:
        expected = Path(args.expect)
        if not expected.is_file():
            raise VaultError(f"参照文件不存在：{expected}")
        same = sha256_file(expected) == sha256_bytes(plaintext)
        print(f"  与 {expected} 逐字节一致：{'是' if same else '否'}")
        return 0 if same else 1
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    _, header, ciphertext = read_container(Path(args.source))
    rows = [
        ("格式", f"{header.get('format')} v{header.get('version')}"),
        ("算法", header.get("cipher")),
        ("密钥模式", "口令" if header.get("key_mode") == "passphrase" else "密钥文件"),
        ("解密校验值", header.get("key_check")),
        ("原始文件名", header.get("source_name")),
        ("原始大小", human_size(int(header.get("source_size") or 0))),
        ("原始 sha256", header.get("source_sha256")),
        ("加密时间", header.get("created_utc")),
        ("密文长度", human_size(len(ciphertext))),
    ]
    kdf = header.get("kdf") or {}
    rows.append(("KDF", f"{kdf.get('name')} N={kdf.get('n')} r={kdf.get('r')} p={kdf.get('p')}"))
    width = max(len(key) for key, _ in rows) + 1
    for key, value in rows:
        print(f"{key}{' ' * (width - len(key))}：{value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asset_vault.py",
        description="资源保险箱：把不宜明文入库的源文件加密归档（AES-256-GCM）。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python scripts/asset_vault.py keygen\n"
            "  python scripts/asset_vault.py encrypt tx.png --out assets/encrypted/tx.png.enc\n"
            "  python scripts/asset_vault.py decrypt assets/encrypted/tx.png.enc --out tx.png\n"
            "  python scripts/asset_vault.py info assets/encrypted/tx.png.enc\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_key_args(target: argparse.ArgumentParser, passphrase: bool) -> None:
        target.add_argument("--key-file", default=str(DEFAULT_KEY_FILE),
                            help=f"密钥文件路径（默认 {DEFAULT_KEY_FILE}）")
        if passphrase:
            target.add_argument("--passphrase", action="store_true",
                                help="改用口令加解密（交互输入，不使用密钥文件）")

    p = sub.add_parser("keygen", help="生成随机密钥文件")
    p.add_argument("--key-file", default=str(DEFAULT_KEY_FILE), help="密钥文件路径")
    p.add_argument("--force", action="store_true", help="已存在时覆盖（旧密文将无法解密）")
    p.set_defaults(func=cmd_keygen)

    p = sub.add_parser("encrypt", help="加密文件")
    p.add_argument("source", help="待加密的明文文件")
    p.add_argument("--out", help="密文输出路径（默认 <source>.enc）")
    p.add_argument("--force", action="store_true", help="允许覆盖已存在的输出")
    add_key_args(p, passphrase=True)
    p.set_defaults(func=cmd_encrypt)

    p = sub.add_parser("decrypt", help="解密文件")
    p.add_argument("source", help="保险箱文件（*.enc）")
    p.add_argument("--out", help="明文输出路径（默认去掉 .enc）")
    p.add_argument("--force", action="store_true", help="允许覆盖已存在的输出")
    add_key_args(p, passphrase=True)
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("verify", help="解密校验但不落地")
    p.add_argument("source", help="保险箱文件（*.enc）")
    p.add_argument("--expect", help="可选：与这个明文文件比对 sha256")
    add_key_args(p, passphrase=True)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("info", help="只读文件头信息")
    p.add_argument("source", help="保险箱文件（*.enc）")
    p.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[list] = None) -> int:
    _reconfigure_stdio()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except VaultError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
