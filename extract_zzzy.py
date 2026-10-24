#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_zzzy.py
================
从 https://www.zzzypro.com/ 的「资源接口」板块下
「影视资源」与「X站资源」两个栏目，遍历所有站点卡片，
进入每个站点的二级页面，提取形如  https://<域名>/.../provide/vod
的接口地址，取其域名并按真实前缀（/api 或 /api.php）拼成
  https://<域名><前缀>/provide/vod/at/xml
（如需强制统一成 /api 前缀，见下方 FORCE_PREFIX 说明），
最终写入 pq1.txt，每行格式：  栏名,完整接口地址

特点：
  * 仅依赖 Python 标准库（urllib / re / concurrent.futures），
    可直接在 GitHub Actions 的 ubuntu-latest 上运行，无需 pip 安装。
  * 多线程抓取二级页面，带重试与超时控制。

用法：
    python extract_zzzy.py            # 输出到 pq1.txt
    python extract_zzzy.py out.txt    # 自定义输出文件名
"""

import concurrent.futures as cf
import re
import ssl
import sys
import time
import urllib.request

BASE = "https://www.zzzypro.com/"
DEFAULT_OUT = "maqu1.txt"
API_SUFFIX = "/provide/vod/at/xml/"
WORKERS = 8
TIMEOUT = 20
RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 关闭证书校验（目标多为自签/泛域名证书，避免偶发 SSL 报错中断抓取）
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# 若只想统一输出 /api/provide/vod/at/xml（忽略各站真实的 /api.php 前缀），
# 把下面这行改成 FORCE_PREFIX = "/api" 即可。
FORCE_PREFIX = None  # None -> 自动沿用页面里真实的接口前缀（/api 或 /api.php 等）

# ---- 正则 ----
H4_RE = re.compile(r"<h4[^>]*>(.*?)</h4>", re.S | re.I)
A_TAG_RE = re.compile(r"<a\b[^>]*>", re.I)
HREF_RE = re.compile(r'href="([^"]+)"', re.I)
SITE_HREF_RE = re.compile(r"zzzypro\.com/sites/\d+\.html$", re.I)
SITE_NAME_RE = re.compile(
    r'<h1[^>]*class="site-name[^"]*"[^>]*>(.*?)</h1>', re.S | re.I
)
# 匹配 MacCMS / TVBox 标准接口地址：<scheme>://<host><前缀>/provide/vod
# 前缀可能是 /api、/api.php，也可能为空
API_RE = re.compile(
    r"(https?)://([^/\s\"'<>]+)(/[^/\s\"'<>]*?)?/provide/vod", re.I
)


def fetch(url):
    """带重试的 GET，返回解码后的文本；失败返回 None。"""
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    return None


def get_target_sections(html):
    """返回 [(栏目标题, 区块html), ...]，仅含「资源接口」下的
    「影视资源」与「X站资源」两个子栏目。"""
    all_h4 = list(H4_RE.finditer(html))
    sections = []
    for i, m in enumerate(all_h4):
        header_text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if "资源接口" not in header_text:
            continue
        if not (
            "影视资源" in header_text
            or re.search(r"x站资源", header_text, re.I)
        ):
            continue
        start = m.end()
        end = all_h4[i + 1].start() if i + 1 < len(all_h4) else len(html)
        sections.append((header_text, html[start:end]))
    return sections


def get_cards(section_html):
    """从栏目区块中提取所有站点卡片链接（去重保序）。"""
    cards = []
    for tag in A_TAG_RE.findall(section_html):
        hm = HREF_RE.search(tag)
        if not hm:
            continue
        href = hm.group(1)
        # 站点卡片同时满足：指向 sites/<id>.html、含 class="card"、含 data-id
        if SITE_HREF_RE.search(href) and 'class="card' in tag and "data-id" in tag:
            cards.append(href)
    seen, uniq = set(), []
    for c in cards:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def parse_detail(html):
    """从二级页面提取 (站点名称, 接口域名)。未找到返回 (name, None)。"""
    name = None
    nm = SITE_NAME_RE.search(html)
    if nm:
        name = re.sub(r"<[^>]+>", "", nm.group(1)).strip()
    if not name:
        tm = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        if tm:
            name = tm.group(1).split("-")[0].split("|")[0].strip()

    domain = None
    am = API_RE.search(html)
    if am:
        scheme, host, prefix = am.group(1), am.group(2), am.group(3)
        if FORCE_PREFIX is not None:
            prefix = FORCE_PREFIX
        elif not prefix:
            prefix = "/api"
        domain = "{}://{}{}".format(scheme, host, prefix)
    return name, domain


def process(url):
    """处理单个二级页面，返回 (url, name, full_url, status)。"""
    html = fetch(url)
    if not html:
        return (url, None, None, "fetch_fail")
    name, domain = parse_detail(html)
    if not domain:
        return (url, name, None, "no_api")
    return (url, name, domain + API_SUFFIX, "ok")


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT

    print(f"[*] 抓取主页面: {BASE}")
    main_html = fetch(BASE)
    if not main_html:
        print("[!] 主页面抓取失败，退出")
        sys.exit(1)

    sections = get_target_sections(main_html)
    print(f"[*] 命中目标栏目: {[s[0] for s in sections]}")

    tasks = []
    for title, shtml in sections:
        cards = get_cards(shtml)
        print(f"    - {title}: {len(cards)} 个站点卡片")
        tasks.extend(cards)

    print(f"[*] 共需处理 {len(tasks)} 个二级页面")

    results = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(process, u): u for u in tasks}
        done = 0
        for fut in cf.as_completed(futs):
            done += 1
            url, name, full, status = fut.result()
            if status == "ok":
                results.append((name or url, full))
                print(f"    [{done}/{len(tasks)}] OK   {name} -> {full}")
            else:
                print(f"    [{done}/{len(tasks)}] {status:9s} {url}  ({name})")

    # 去重（按完整接口地址），保序写入
    seen, lines = set(), []
    for name, full in results:
        if full in seen:
            continue
        seen.add(full)
        lines.append(f"{name},{full}")

    with open(out_path, "w", encoding="utf-8") as f:
        if lines:
            f.write("\n".join(lines) + "\n")

    print(f"[*] 完成，写入 {len(lines)} 行到 {out_path}")


if __name__ == "__main__":
    main()
