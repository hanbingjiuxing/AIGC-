# 资源保险箱（assets/encrypted/）

站点要用的图片以**密文**形式存放在这里：仓库、发布包和硬盘上都没有对应的明文。

> 防护等级（先说清楚）：这是**防"有人直接翻项目文件夹就看到图片"**，挡的是没有
> 计算机知识的普通用户，不是强保密。密钥材料默认内置在程序里（见下），
> 所以能看到源码或仓库的人依然可以解出明文。要更强的保护，见「安全边界」一节。

## 运行期怎么用（About 页头像）

`frontend/public/` 里**不再放** `tx.png`。About 页的 `<img src="/api/assets/avatar">` 由后端在收到请求时解密到**内存**再返回：

```
浏览器 ── GET /api/assets/avatar ──► Flask（backend/routes/assets.py）
                                      └─ 解密 assets/encrypted/tx.web.png.enc 到内存
                                         每个进程只解密一次，之后走内存缓存 + ETag / 304
```

* 明文只活在进程内存里：请求结束不落地，进程退出即消失。**没有"关闭后要清理的临时文件"——因为压根没产生过**；服务被强杀也一样，磁盘上不会留下半份。
* 密钥默认**内置在程序里**（`backend/utils/asset_vault.py` 的 `EMBEDDED_KEY_HEX`），所以换机器、从 GitHub 拉取更新之后都不必再手工拷密钥，头像直接可用。
* 万一密文或密钥对不上（例如你换过自己的密钥却没重新加密密文），接口返回 404 而不是 500，About 页的 `<img onError>` 会退回社徽 `logo.png`，不会出现裂图。
* 接口是公开的：**能打开网站的人就能拿到这张图**，这与加密无关（浏览器能显示 = 明文已经发出去）。加密解决的是"磁盘上、仓库里不留明文"，不是"谁都看不到"。

## 目录内容

| 文件 | 内容 | 用途 |
|------|------|------|
| `encrypted/tx.web.png.enc` | 网页版头像 174,855 B | 运行期由 `/api/assets/avatar` 解密返回 |
| `encrypted/tx.png.enc` | 母版原图 981,353 B（1118×1094） | 只归档，站点不用；需要时手动解密 |

密文头部记录了原文的 sha256、大小与加密时间，**不需要密钥**就能查看：

```bash
python scripts/asset_vault.py info assets/encrypted/tx.web.png.enc
```

## 密钥在哪里

默认**在程序里**（随仓库一起分发）：

```
backend/utils/asset_vault.py      # EMBEDDED_KEY_HEX = "<64 位十六进制>"
```

这样设计是为了省事：换机器、从 GitHub 拉取更新、重装发布包之后，头像开箱即用，
不会因为"忘了拷密钥"而退回社徽。

想提高防护等级的话，生成一把自己的密钥放到这里，**它的优先级高于内置密钥**：

```
data/secrets/asset-vault.key      # 32 字节随机数的十六进制文本
```

`data/` 已被 `.gitignore` 忽略，并且被更新模块整体保护（升级不覆盖、不删除）。
换成私有密钥后要记住两件事：

1. **重新加密密文**：`python scripts/asset_vault.py encrypt <明文> --out assets/encrypted/tx.web.png.enc`，
   否则旧密文只认内置密钥，头像会退回社徽；
2. **备份并随身携带**：它丢了，`encrypted/` 里的密文就再也解不开。

## 取回明文（临时用）

```bash
# 1) 校验密文完好（解密到内存校验，不写文件）
python scripts/asset_vault.py verify assets/encrypted/tx.png.enc

# 2) 还原到某个临时位置
python scripts/asset_vault.py decrypt assets/encrypted/tx.png.enc --out tx.png
```

用完记得删掉——这正是保险箱想避免的东西。

## 新增一个站点资源

```bash
# 1) 收进保险箱
python scripts/asset_vault.py encrypt <明文图片> --out assets/encrypted/<名字>.enc
```

2) 在 `backend/routes/assets.py` 的 `SITE_ASSETS` 里加一条：`'<资源名>': ('assets/encrypted/<名字>.enc', 'image/png')`，然后前端用 `/api/assets/<资源名>` 引用。

## 换一台机器还原（口令模式）

密钥文件默认不随仓库分发。若要在没有该密钥文件的机器上还原，可以用口令模式归档一份：

```bash
python scripts/asset_vault.py encrypt <明文文件> --passphrase   # 交互输入口令
python scripts/asset_vault.py decrypt <密文> --passphrase        # 换机器后还原
```

## 安全边界（说明白，免得误解）

* 管用的：仓库 / 发布包 / 备份里只有密文；硬盘上、`public/` 里、构建产物里都没有明文图片；网站运行期间明文只在内存。
* **管不了的（默认配置下）**：密钥内置在程序里，而程序在公开仓库里 —— 任何能看到源码的人都能解出这张图。它挡的是"翻文件夹"级别的围观，不是有意破解的人。
* 要真正拦住：换成自己的密钥文件（`data/secrets/asset-vault.key`，优先级更高）并**不要**提交它，同时用新密钥重新加密密文；更强的做法是把密钥挪到本机之外（U 盘、密码管理器），或给接口加鉴权（图片得改成 fetch + blob，`<img>` 带不了 Token）。
* 算法是 AES-256-GCM（认证加密）：密文或文件头被改动一个字节都会解密失败，不会解出"看起来正常"的坏文件。
* 脚本依赖 `cryptography`（`pip install cryptography`）；系统本身运行不需要它，只有加解密与接口解密用到。

## 命令速查

| 命令 | 作用 |
|------|------|
| `asset_vault.py keygen` | 生成随机密钥文件 |
| `asset_vault.py encrypt <明文> [--out <密文>]` | 加密（加 `--passphrase` 改口令模式） |
| `asset_vault.py decrypt <密文> [--out <明文>]` | 解密还原 |
| `asset_vault.py verify <密文> [--expect <明文>]` | 解密校验，不落地 |
| `asset_vault.py info <密文>` | 只读文件头（无需密钥） |

实现位于 `backend/utils/asset_vault.py`（后端运行期也用它），`scripts/asset_vault.py` 只是一层入口。
