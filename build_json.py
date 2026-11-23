#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_json.py —— 统一采集源生成器

把两个采集脚本产出的源文件合并成一份，去重后生成各平台配置：

  源文件：
    maqu.txt   —— main.yml 采集（影视站之家 yszzq.com，经 xinpq.py + lins.py）
    maqu1.txt  —— main2.yml 采集（zzzypro.com，经 extract_zzzy.py）

  输出：
    hongguo.json  红果（duanju-custom-sources，sites 为对象数组）
    libretv.json  LibreTV（cache_time + api_site 字典）
    zcying.json   资源影视（key/name/api/useInSearchAll 数组）
    zypcbox.json  zypc 版（tbl_site 包裹）
    zytvbox.json  TVBox（type/searchable/recordable）
    zyvying.json  v影（key/name/api/useInSearchAll 数组）
    ysdqbox.json  影视大全（旧格式，继续保留兼容 README 里的旧链接）

去重规则：
  以「接口地址」为准，去掉代理前缀、协议、尾部斜杠后比较；同一接口只保留
  第一次出现的名称。两个源站的重合站点（约 21 个）因此只会出现一次。

用法：
    python build_json.py                       # 默认读 maqu.txt + maqu1.txt
    python build_json.py A.txt B.txt           # 自定义源文件路径
"""

import hashlib
import json
import pathlib
import re
import sys

# ---------- 通用配置 ----------
DEFAULT_SOURCES = ('maqu.txt', 'maqu1.txt')
PROXY = 'https://cfkua.wokaotianshi.eu.org/'

# 同时识别 /api/ 与 /api.php/ 两种前缀
#   https://hhzyapi.com/api.php/provide/vod/at/xml -> host=https://hhzyapi.com prefix=api.php
#   https://api.juliang.live/api/provide/vod/at/xml -> host=https://api.juliang.live prefix=api
_PREFIX_RE = re.compile(r'(https?://[^/]+)/(api\.php|api)(?=/provide/vod)', re.I)
_HOST_RE = re.compile(r'(https?://[^/]+)', re.I)


def parse_api(api_url):
    """把一个接口地址拆成 (scheme+host, 前缀)，匹配不到时前缀为空。"""
    m = _PREFIX_RE.search(api_url)
    if m:
        return m.group(1), m.group(2).lower()
    m2 = _HOST_RE.match(api_url)
    return (m2.group(1) if m2 else api_url.rstrip('/')), ''


def build_api(api_url, suffix='/provide/vod/at/xml'):
    """构造代理地址：PROXY + host + '/' + prefix + suffix。"""
    host, prefix = parse_api(api_url)
    if prefix:
        return PROXY + host + '/' + prefix + suffix
    return PROXY + host + suffix


def normalize(api_url):
    """归一化接口地址用于去重：去代理前缀、去协议、去尾部斜杠、小写。"""
    url = api_url.strip().rstrip('/').lower()
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^cfkua\.wokaotianshi\.eu\.org/', '', url)
    return url


def read_sources(paths):
    """读取若干源文件，按 URL 去重（先出现的优先），返回 [(name, url), ...]。"""
    merged, seen = [], set()
    stats = {}
    for path in paths:
        p = pathlib.Path(path)
        if not p.exists():
            print(f'[跳过] 源文件不存在: {p}')
            stats[str(p)] = 0
            continue
        count = 0
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or ',' not in line:
                continue
            name, api = map(str.strip, line.split(',', 1))
            if not name or not api:
                continue
            count += 1
            key = normalize(api)
            if key in seen:
                continue
            seen.add(key)
            merged.append((name, api))
        stats[str(p)] = count
        print(f'[读取] {p}: {count} 条（累计去重后 {len(merged)} 条）')
    return merged, stats


def stable_key(api_url):
    """由接口地址派生的 4 位稳定 key，避免每次运行随机变化导致无意义提交。"""
    return hashlib.md5(normalize(api_url).encode('utf-8')).hexdigest()[:4]


def dump(obj, filename):
    pathlib.Path(filename).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    paths = sys.argv[1:3] or DEFAULT_SOURCES
    sources, stats = read_sources(paths)
    if not sources:
        print('[错误] 两个源文件都没有有效条目，拒绝生成空配置。')
        sys.exit(1)

    data_zcying = []
    data_zyvying = []
    data_zytvbox = []
    data_ysdqbox = []
    data_zypcbox = []
    yuan_api_site = {}
    hongguo_sites = []

    for index, (name, api_url) in enumerate(sources, 1):
        url_xml = build_api(api_url, '/provide/vod/at/xml')
        url_vod = build_api(api_url, '/provide/vod/')

        # zcying / zyvying：同一套 v影 格式，内容都是合并后的全量源
        item_vod = {
            'key': name,
            'name': name,
            'api': url_xml,
            'useInSearchAll': True,
        }
        data_zcying.append(dict(item_vod))
        data_zyvying.append(dict(item_vod))

        # zytvbox
        data_zytvbox.append({
            'key': name,
            'name': name,
            'type': 1,
            'api': url_vod,
            'searchable': 1,
            'recordable': 0,
        })

        # ysdqbox（旧格式，兼容保留）
        data_ysdqbox.append({
            'type': '',
            'sourceName': name,
            'baseUrl': '',
            'apiUrl': url_xml,
            'searchUrl': '',
            'detailUrl': '',
            'parserUrl': '',
        })

        # zypcbox
        data_zypcbox.append({
            'key': name,
            'name': name,
            'api': url_xml,
            'playUrl': '',
            'search': 1,
            'group': '切片',
            'status': True,
            'type': 0,
            'id': str(index),
            'isActive': True,
            'resource': '',
            'download': '',
        })

        # libretv（不带代理，保留源站真实前缀）
        host, prefix = parse_api(api_url)
        yuan_cut = (host + '/' + prefix) if prefix else host
        yuan_api_site[stable_key(api_url)] = {
            'name': name,
            'api': yuan_cut + '/provide/vod',
        }

        # hongguo
        hongguo_sites.append({
            'name': name,
            'url': url_xml,
            'rule': '',
            'type': 'json',
        })

    dump(data_zcying, 'zcying.json')
    dump(data_zyvying, 'zyvying.json')
    dump(data_zytvbox, 'zytvbox.json')
    dump(data_ysdqbox, 'ysdqbox.json')
    dump({'tbl_site': data_zypcbox}, 'zypcbox.json')
    dump({'cache_time': 7200, 'api_site': yuan_api_site}, 'libretv.json')
    dump({
        'format': 'duanju-custom-sources',
        'version': 1,
        'count': len(hongguo_sites),
        'sites': hongguo_sites,
    }, 'hongguo.json')

    print(f'\n[完成] 合并 {sum(stats.values())} 条源 → 去重后 {len(sources)} 条，'
          f'已生成 7 个 JSON（hongguo.json 内站点数 {len(hongguo_sites)}）。')
    for path, count in stats.items():
        print(f'       {path}: {count} 条')


if __name__ == '__main__':
    main()
