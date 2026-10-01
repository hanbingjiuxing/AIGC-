#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把系统里的「关于这个系统」页面复制成一份单文件 HTML（不需要框架、不需要服务器）。

用法：
    python scripts/build_about_fallback.py            # 生成 fallback/about.html
    python scripts/build_about_fallback.py --check    # 只检查磁盘上的那份是不是最新的（不写盘）

为什么需要这一页：
    「关于这个系统」页（frontend/src/pages/About.jsx）正好在讲"遇到解决不了的 bug 找谁"，
    可它本身是系统的一部分 —— 系统起不来，就看不到它。所以把它复制一份出来：
    样式从 frontend/src/index.css 原样摘取，社徽以 base64 内嵌，没有 React、
    没有 Vite、没有后端、没有任何外部请求，双击就能打开（file:// 也可以）。
    run_system.bat 启动失败时会自动打开这一页。

生成时会拿 About.jsx 逐条对文案：
    * CONTACTS / PROTOCOLS 两处数据直接从源码解析出来（不是手抄）；
    * 源码里每一段中文文案都会被拆成短句，逐句确认离线页里也有。
    对不上就直接报错退出 —— 改了 About.jsx 却忘了重新生成，这里会拦住。

所以：改完 About.jsx / index.css 之后，重新跑一次本脚本。
"""

from __future__ import annotations

import argparse
import base64
import html as html_mod
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ABOUT_JSX = ROOT / "frontend" / "src" / "pages" / "About.jsx"
INDEX_CSS = ROOT / "frontend" / "src" / "index.css"
LOGO_PNG = ROOT / "frontend" / "public" / "logo.png"
FAVICON_PNG = ROOT / "frontend" / "public" / "favicon-32.png"
OUT_HTML = ROOT / "fallback" / "about.html"

CJK = re.compile(r"[\u4e00-\u9fff]")

#: 系统内这一页有、离线版故意不照搬的文案 —— 键是源码里的句子，值是原因
INTENTIONAL_DIFFERENCES = {
    "返回": "离线版没有系统可返回，左上角按钮换成了浅色/深色切换（见 fallback/README.md）",
}


# --------------------------------------------------------------------------- #
# 从 index.css 里摘样式
# --------------------------------------------------------------------------- #
def css_block(css: str, needle: str) -> str:
    """取出以 needle 开头、大括号配平的那一段 CSS（含 needle 与收尾大括号）。"""
    i = css.find(needle)
    if i < 0:
        raise SystemExit(f"[FAIL] index.css 里找不到 {needle!r} —— 样式结构变了，请更新本脚本")
    j = css.index("{", i)
    depth = 0
    for k in range(j, len(css)):
        if css[k] == "{":
            depth += 1
        elif css[k] == "}":
            depth -= 1
            if depth == 0:
                return css[i : k + 1]
    raise SystemExit(f"[FAIL] {needle!r} 的大括号没有闭合")


def collect_css(css: str) -> str:
    """主题变量 + 基础重置 + 关于页整节，全部原样取自 index.css。"""
    parts = [
        "/* 以下样式原样取自 frontend/src/index.css，请勿在此手工修改 */",
        css_block(css, ":root {"),
        "",
        css_block(css, "[data-theme='dark'] {"),
        "",
        css_block(css, "\n* {").lstrip("\n"),
        "",
        css_block(css, "\nbody {").lstrip("\n"),
        "",
        css_block(css, "@keyframes fadeIn {"),
        "",
        # App.jsx 里 About 页外面那层容器用的就是这几个手写工具类
        # （项目没有真正启用 Tailwind，min-h-screen / p-4 之类其实没有定义）
        css_block(css, "\n.flex {").lstrip("\n"),
        "",
        css_block(css, "\n.items-center {").lstrip("\n"),
        "",
        css_block(css, "\n.justify-center {").lstrip("\n"),
        "",
    ]
    marker = "关于这个系统 (/about)"
    i = css.find(marker)
    if i < 0:
        raise SystemExit("[FAIL] index.css 里找不到「关于这个系统 (/about)」那一节")
    start = css.rindex("/*", 0, i)
    parts.append(css[start:].rstrip())
    parts.append("")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# 从 About.jsx 里取数据与文案
# --------------------------------------------------------------------------- #
def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^[ \t]*//.*$", " ", src, flags=re.M)
    return src


def strip_braces(src: str) -> str:
    """去掉 JSX 的 {...} 表达式（含嵌套；跳过字符串字面量里的括号）。"""
    out = []
    depth = 0
    quote = ""
    i = 0
    while i < len(src):
        ch = src[i]
        if quote:
            if depth == 0:
                out.append(ch)
            if ch == "\\":
                if depth == 0:
                    out.append(src[i + 1 : i + 2])
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "`\"'":
            quote = ch
            if depth == 0 and ch != "`":
                out.append(ch)
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
        i += 1
    return "".join(out)


def strip_tags(src: str) -> str:
    return re.sub(r"<[^>]*>", " ", src)


#: 句子切分：空白 + 中英文标点都算边界（这样插进新板块也不会误报，改动字句则会被抓到）
SPLIT = re.compile(r"[\s\u3000\u3001\u3002\uff01\uff08\uff09\uff0c\uff1a\uff1b\uff1f\u2014\u2018\u2019\u201c\u201d\u300a\u300b\u3010\u3011\u00b7\[\]\(\)\{\}'\"=;,./!?:+\-|]+")


def jsx_body(src: str) -> str:
    """只取组件 return (...) 里的那段 JSX。

    注意：不能对整份 About.jsx 去大括号 —— return 本身就在函数体的大括号里，
    整块 JSX 会被一起吃掉。JSX 里"看得见的文字"必须单独取出来比对。
    """
    i = src.find("return (")
    if i < 0:
        raise SystemExit("[FAIL] About.jsx 里找不到 return (...)，无法比对页面文案")
    return strip_comments(src[i:])


def jsx_pieces(src: str) -> list:
    """About.jsx 里所有"看得见的中文"被拆成短句，用来逐句核对离线页。"""
    text = strip_tags(strip_braces(jsx_body(src)))
    pieces = []
    for raw in SPLIT.split(text):
        piece = raw.strip()
        if len(piece) >= 2 and CJK.search(piece):
            pieces.append(piece)
    seen = set()
    unique = []
    for p in pieces:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def between(src: str, start: str, end: str) -> str:
    i = src.find(start)
    if i < 0:
        raise SystemExit(f"[FAIL] About.jsx 里找不到 {start!r}")
    j = src.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"[FAIL] About.jsx 里 {start!r} 没有收尾 {end!r}")
    return src[i + len(start) : j]


def parse_contacts(src: str) -> list:
    """解析 About.jsx 里的 CONTACTS（顺序即显示顺序）。"""
    block = between(src, "const CONTACTS = [", "];")
    pairs = re.findall(r"\{\s*label:\s*'([^']*)'\s*,\s*value:\s*'([^']*)'\s*\}", block)
    return [(label.strip(), value.strip()) for label, value in pairs]


def parse_protocols(src: str) -> list:
    """解析 About.jsx 里的 PROTOCOLS（顺序即显示顺序）。"""
    block = between(src, "const PROTOCOLS = [", "];")
    pairs = re.findall(r"\[\s*'([^']*)'\s*,\s*'([^']*)'\s*\]", block)
    return [(name.strip(), usage.strip()) for name, usage in pairs]


def html_text(src: str) -> str:
    """HTML 的可见文字（去掉 script/style/注释/标签，解码实体，去掉所有空白）。"""
    src = re.sub(r"<script\b.*?</script>", " ", src, flags=re.S | re.I)
    src = re.sub(r"<style\b.*?</style>", " ", src, flags=re.S | re.I)
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    src = re.sub(r"<[^>]*>", " ", src)
    src = html_mod.unescape(src)
    return re.sub(r"\s+", "", src)


def check_fidelity(about_src: str, page: str) -> None:
    """生成物必须与 About.jsx 对得上，否则直接失败。"""
    problems = []
    text = html_text(page)

    contacts = parse_contacts(about_src)
    protocols = parse_protocols(about_src)
    if not contacts:
        problems.append("没有从 About.jsx 解析到 CONTACTS")
    if not protocols:
        problems.append("没有从 About.jsx 解析到 PROTOCOLS")
    for label, value in contacts:
        for item in (label, value):
            if item not in text:
                problems.append(f"联系方式对不上：{item}")
    for name, usage in protocols:
        for item in (name, usage):
            if re.sub(r"\s+", "", item) not in text:
                problems.append(f"协议表对不上：{item}")

    for piece in jsx_pieces(about_src):
        if piece in INTENTIONAL_DIFFERENCES:
            continue
        if piece not in text:
            problems.append(f"文案对不上：{piece}")

    if problems:
        lines = "\n".join("      - " + p for p in problems)
        raise SystemExit(
            "[FAIL] 离线页与 About.jsx 对不上，已中止：\n"
            f"{lines}\n"
            "      改完 frontend/src/pages/About.jsx 后，把对应文案同步到本脚本的模板里"
            "（或确认上面的差异是有意的）。"
        )


# --------------------------------------------------------------------------- #
# 页面模板
# --------------------------------------------------------------------------- #
PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>关于这个系统 · 离线版 | AIGC探索社</title>
<link rel="icon" type="image/png" sizes="32x32" href="@@FAVICON@@">
<!--
  这一页是系统内「关于这个系统」页面（frontend/src/pages/About.jsx）的离线副本，
  由 scripts/build_about_fallback.py 生成，请勿手工编辑 —— 改完源码重新跑那个脚本。

  它被有意做成"单文件"：样式、社徽、脚本全部内嵌，没有 React、没有后端、
  没有任何外部请求，双击即可打开。run_system.bat 启动失败时会自动打开它。
-->
<style>
@@CSS@@

/* ============================================================
   离线版补充样式（系统内的 About 页没有这些）
   ============================================================ */

/* 顶栏右侧的「离线版」标记 */
.offline-pill {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  padding: 0.42em 0.9em;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: clamp(0.72rem, 0.69rem + 0.12vw, 0.82rem);
  white-space: nowrap;
}

/* 说明条：进页面第一眼要看到的东西 */
.offline-strip {
  padding: clamp(12px, 1.3vw, 18px) clamp(14px, 1.6vw, 22px);
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--primary-color);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}

.offline-strip .about-text strong {
  color: var(--text-primary);
}

/* 头像拿不到时用内嵌社徽顶上。社徽是长条形的（左侧是圆形校徽），
   这里按头像的尺寸裁成方块、只露左边圆形徽标 —— 否则整条社徽会把
   联系方式那一行撑得很宽，窄屏直接横向溢出。 */
.contact-avatar--emblem {
  width: var(--contact-h);
  object-fit: cover;
  object-position: left center;
}

/* 页脚 */
.offline-footer {
  border-top: 1px solid var(--border-color);
  padding-top: clamp(10px, 1.2vw, 16px);
}

.offline-footer .about-text {
  font-size: clamp(0.76rem, 0.73rem + 0.14vw, 0.85rem);
  color: var(--text-secondary);
}

/* 顶栏按钮上的两个图标：跟着当前主题显示一个 */
html[data-theme='dark'] .icon-sun { display: none; }
html:not([data-theme='dark']) .icon-moon { display: none; }
</style>
</head>
<body>
<!-- 与 App.jsx 里包着 About 页的那层容器一致：flex items-center justify-center -->
<div class="flex items-center justify-center">
  <div class="about-page">
    <header class="about-header">
      <button type="button" class="about-back" id="theme-toggle" title="切换浅色 / 深色">
        <svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
        <svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
        <span id="theme-label">深色</span>
      </button>
      <span class="offline-pill">离线版 · 不需要启动系统</span>
    </header>

    <main class="about-body">
      <section class="about-section offline-strip">
        <p class="about-text"><strong>这一页不需要启动系统。</strong>它是从系统里的「关于这个系统」页面复制出来的单文件版本：没有 React、没有后端、没有任何外部请求，双击就能打开。<code>run_system.bat</code> 启动失败时，会自动打开这一页。</p>
      </section>

      <div class="about-hero">
        <div class="about-emblem">
          <img src="@@LOGO@@" alt="社徽">
        </div>
        <h1 class="about-title">关于这个系统</h1>
        <p class="about-subtitle">厦门大学附属科技中学翔安校区 AIGC 探索社</p>
      </div>

      <div class="about-content">
        <!-- ---------------- 来源 ---------------- -->
        <section class="about-section">
          <h2 class="about-section-title">这套系统从哪来</h2>
          <p class="about-text">它由 <strong>27 届的学长</strong>受 <strong>纪丽丽老师</strong>委托， 用 AI 一手做出来的。从第一行代码到你此刻看到的界面，全程都由 AI 辅助编写 —— 前后用过 <strong>Claude、Gemini、DeepSeek、Mimo</strong> 等多种模型， 哪家擅长什么就用哪家，反复试、反复改，最后拼成了一个真正能跑起来的系统。</p>
          <p class="about-text">它同时也是一个<strong>开源项目</strong>：代码全部公开，改得动、看得见， 想自己部署一份也完全可以。</p>
        </section>

        <!-- ---------------- 实现与协议 ---------------- -->
        <section class="about-section">
          <h2 class="about-section-title">它是怎么做出来的</h2>
          <p class="about-text">系统采用<strong>前后端分离</strong>的结构，三块各管一摊：</p>
          <ul class="about-list">
            <li><strong>前端</strong>：React + Vite。你看到的每个页面、每次点击， 都由它在浏览器里渲染出来。</li>
            <li><strong>后端</strong>：Python + Flask。业务逻辑、权限判断、数据读写都在这里完成。</li>
            <li><strong>数据库</strong>：SQLite。整个社团的数据就是一个文件，统一放在<code>data/</code> 目录下 —— 备份和迁移只需要拷这一个文件夹。</li>
          </ul>
          <p class="about-text">两者之间用 HTTP 传 JSON（REST 风格的接口）。登录成功后，服务器会签发一张<strong>JWT 令牌</strong>，之后每个请求都带着它， 服务器据此判断你是谁、能做哪些事。</p>
          <p class="about-text">部署也不麻烦：老师在服务器上双击一次 <code>run_system.bat</code>，前后端一起启动， 同一个局域网里的电脑、手机、平板打开浏览器就能用，不需要每台机器都装环境。</p>
          <p class="about-text">系统还内置了<strong>自动更新</strong>：优先用 Git 拉取最新代码， 不行就回退到 GitHub Release 下载更新包。更新包是 ZIP，会校验 CRC32 与 SHA-256， 写入前自动备份、失败自动回滚 —— 无论更新成功与否， 数据库和同学们上传的作品都不会被动到。</p>

          <h3 class="about-subheading">用到的协议与格式</h3>
          <div class="about-table-wrap">
            <table class="about-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>用在哪</th>
                </tr>
              </thead>
              <tbody>
@@PROTOCOL_ROWS@@
              </tbody>
            </table>
          </div>
        </section>

        <!-- ---------------- 联系 ---------------- -->
        <section class="about-section">
          <h2 class="about-section-title">遇到实在解决不了的 bug</h2>
          <p class="about-text">先重启一次 <code>run_system.bat</code> —— 九成的问题到这一步就没了。</p>
          <p class="about-text">要是还不行，可以通过下面的方式，联系<strong>古希腊掌管 AIGC 社信息系统的神</strong>：</p>

          <div class="contact-row">
            <ul class="contact-list">
@@CONTACT_ITEMS@@
            </ul>
            <img
              id="contact-avatar"
              class="contact-avatar contact-avatar--emblem"
              src="@@LOGO@@"
              alt="古希腊掌管 AIGC 社信息系统的神"
            >
          </div>
        </section>
      </div>

      <footer class="offline-footer">
        <p class="about-text">离线副本 · 内容与系统内「关于这个系统」页面一致 · 由 <code>scripts/build_about_fallback.py</code> 生成</p>
      </footer>
    </main>
  </div>
</div>

<script>
(function () {
  var KEY = 'theme';
  var root = document.documentElement;
  var label = document.getElementById('theme-label');

  function read() {
    try { return window.localStorage.getItem(KEY); } catch (err) { return null; }
  }
  function write(value) {
    // file:// 下有些浏览器会禁用 localStorage，写不进去也不影响使用
    try { window.localStorage.setItem(KEY, value); } catch (err) {}
  }
  function apply(dark) {
    if (dark) { root.setAttribute('data-theme', 'dark'); }
    else { root.removeAttribute('data-theme'); }
    if (label) { label.textContent = dark ? '浅色' : '深色'; }
  }
  function initial() {
    // 与系统里的 theme.js 一致，额外支持 ?theme=dark / ?theme=light 临时指定
    var forced = /[?&]theme=(dark|light)/.exec(window.location.search);
    if (forced) { return forced[1] === 'dark'; }
    var saved = read();
    if (saved === 'dark') { return true; }
    if (saved === 'light') { return false; }
    return typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  var dark = initial();
  apply(dark);

  var button = document.getElementById('theme-toggle');
  if (button) {
    button.addEventListener('click', function () {
      dark = !dark;
      apply(dark);
      write(dark ? 'dark' : 'light');
    });
  }

  // 头像存在保险箱里（assets/encrypted/），只有后端解密才拿得到：
  // 接口在就换成真头像，离线（file:// 或后端没起来）就保持内嵌社徽，绝不裂图。
  var emblem = document.querySelector('.about-emblem img');
  var logo = emblem ? emblem.getAttribute('src') : '';
  var avatar = document.getElementById('contact-avatar');
  if (avatar && logo) {
    var useEmblem = function () {
      avatar.classList.add('contact-avatar--emblem');
      avatar.setAttribute('src', logo);
    };
    avatar.addEventListener('error', function () {
      if (avatar.getAttribute('src') === logo) { return; }
      console.warn('[About] /api/assets/avatar 取不到，已退回社徽。');
      useEmblem();
    });
    if (window.location.protocol !== 'file:') {
      avatar.classList.remove('contact-avatar--emblem');
      avatar.setAttribute('src', '/api/assets/avatar');
    }
  }
})();
</script>
</body>
</html>
"""


def data_uri(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def render(about_src: str, css: str) -> str:
    protocols = parse_protocols(about_src)
    contacts = parse_contacts(about_src)

    rows = "\n".join(
        "                <tr>\n"
        f"                  <td>{html_mod.escape(name)}</td>\n"
        f"                  <td>{html_mod.escape(usage)}</td>\n"
        "                </tr>"
        for name, usage in protocols
    )
    items = "\n".join(
        '              <li class="contact-item">\n'
        f'                <span class="contact-label">{html_mod.escape(label)}</span>\n'
        f'                <span class="contact-value">{html_mod.escape(value)}</span>\n'
        "              </li>"
        for label, value in contacts
    )
    logo = data_uri(LOGO_PNG)

    page = PAGE
    page = page.replace("@@CSS@@", collect_css(css))
    page = page.replace("@@FAVICON@@", data_uri(FAVICON_PNG))
    page = page.replace("@@LOGO@@", logo)
    page = page.replace("@@PROTOCOL_ROWS@@", rows)
    page = page.replace("@@CONTACT_ITEMS@@", items)
    check_fidelity(about_src, page)
    return page


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="生成「关于这个系统」离线页（单文件 HTML）")
    ap.add_argument("--check", action="store_true", help="只检查磁盘上的那一份是不是最新的，不写盘")
    ap.add_argument("--about", default=str(ABOUT_JSX), help="About.jsx 路径（一般不用改）")
    ap.add_argument("--css", default=str(INDEX_CSS), help="index.css 路径（一般不用改）")
    ap.add_argument("--out", default=str(OUT_HTML), help="输出 HTML 路径（一般不用改）")
    args = ap.parse_args()

    about_path = Path(args.about)
    out_path = Path(args.out)
    about_src = about_path.read_text(encoding="utf-8")
    css = Path(args.css).read_text(encoding="utf-8")

    page = render(about_src, css)
    size = len(page.encode("utf-8"))

    if args.check:
        if not out_path.is_file():
            print(f"[FAIL] {out_path} 不存在，请先运行：python scripts/build_about_fallback.py")
            return 1
        if out_path.read_text(encoding="utf-8") != page:
            print(f"[FAIL] {out_path} 已过期：与 About.jsx / index.css 重新生成的结果不一致。")
            print("       请运行：python scripts/build_about_fallback.py")
            return 1
        print(f"[OK] {out_path} 是最新的（{size:,} 字节）")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8", newline="\n")
    print("[OK] 已生成离线页")
    print(f"     文件 : {out_path}")
    print(f"     体积 : {size:,} 字节（单文件，无外部请求）")
    print(f"     来源 : {about_path.name} + frontend/src/index.css")
    print("     自查 : CONTACTS %d 条 / PROTOCOLS %d 条 / 文案逐句核对通过"
          % (len(parse_contacts(about_src)), len(parse_protocols(about_src))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
