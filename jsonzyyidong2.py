#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zh.py  二合一版本
1. 按原逻辑生成 4 份 JSON（zyvying / zytvbox / ysdqbox / zypcbox）
2. 新增 libretv.json（yuan.json）
3. 修复 hongguo.json 格式，sites 为对象数组
源文件统一使用 maqu.txt

【裁剪兼容两种接口前缀】
  - https://host/api/provide/vod/at/xml
  - https://host/api.php/provide/vod/at/xml
两种地址都会被正确拆出 (scheme+host, 前缀)，再按源站真实前缀重建，
保证 juliang 这类 /api/ 站点不会被错拼成 /api.php/。
"""
import json
import pathlib
import itertools
import random
import string
import re

# ---------- 通用配置 ----------
SRC = 'maqu1.txt'
PROXY = 'https://cfkua.wokaotianshi.eu.org/'

used_key = set()          # 用于生成不重复随机 key

def uid() -> str:
    """生成 4 位不重复的随机字母+数字"""
    while True:
        s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if s not in used_key:
            used_key.add(s)
            return s

# 同时识别 /api/ 与 /api.php/ 两种前缀，截出 scheme+host 与 前缀
#   例：https://hhzyapi.com/api.php/provide/vod/at/xml -> host=https://hhzyapi.com  prefix=api.php
#       https://api.juliang.live/api/provide/vod/at/xml   -> host=https://api.juliang.live  prefix=api
_PREFIX_RE = re.compile(r'(https?://[^/]+)/(api\.php|api)(?=/provide/vod)', re.I)


def parse_api(api_url):
    """把一个接口地址拆成 (scheme+host, 前缀)。
    匹配不到接口路径时退化为只返回 scheme+host，prefix=''。"""
    m = _PREFIX_RE.search(api_url)
    if m:
        return m.group(1), m.group(2).lower()
    m2 = re.match(r'(https?://[^/]+)', api_url, re.I)
    return (m2.group(1) if m2 else api_url.rstrip('/')), ''


def build_api(api_url, suffix='/provide/vod/at/xml'):
    """构造代理地址：PROXY + host + '/' + prefix + suffix
    suffix 默认带 at/xml；zytvbox 用 '/provide/vod/' 即可。"""
    host, prefix = parse_api(api_url)
    if prefix:
        return PROXY + host + '/' + prefix + suffix
    return PROXY + host + suffix


# 全局存储解析好的列表，只读取一次文件
source_list = []
with open(SRC, 'r', encoding='utf-8') as f:
    for line in f.readlines():
        line = line.strip()
        if not line or ',' not in line:
            continue
        name, api_url = map(str.strip, line.split(',', 1))
        source_list.append((name, api_url))

# ---------- 各个平台json数据组装 ----------
data_list_for_converted = []
data_list_for_zytvbox   = []
data_list_for_ysdqbox   = []
data_list_for_zypcbox   = []
id_counter = itertools.count(1)

yuan_api_site = {}
hongguo_sites_list = []  # 改成数组，直接存放 {name,url}

for name, api_url in source_list:
    # 1. zyvying
    data_list_for_converted.append({
        "key": name,
        "name": name,
        "api": build_api(api_url, '/provide/vod/at/xml'),
        "useInSearchAll": True
    })
    # 2. zytvbox
    data_list_for_zytvbox.append({
        "key": name,
        "name": name,
        "type": 1,
        "api": build_api(api_url, '/provide/vod/'),
        "searchable": 1,
        "recordable": 0
    })
    # 3. ysdqbox
    data_list_for_ysdqbox.append({
        "type": "",
        "sourceName": name,
        "baseUrl": "",
        "apiUrl": build_api(api_url, '/provide/vod/at/xml'),
        "searchUrl": "",
        "detailUrl": "",
        "parserUrl": ""
    })
    # 4. zypcbox
    data_list_for_zypcbox.append({
        "key": name,
        "name": name,
        "api": build_api(api_url, '/provide/vod/at/xml'),
        "playUrl": "",
        "search": 1,
        "group": "切片",
        "status": True,
        "type": 0,
        "id": str(next(id_counter)),
        "isActive": True,
        "resource": "",
        "download": ""
    })

    # libretv.json（原yuan.json）：取 host+prefix+/provide/vod（不含 at/xml）
    host, prefix = parse_api(api_url)
    yuan_cut = (host + '/' + prefix) if prefix else host
    yuan_cut = yuan_cut + '/provide/vod'
    yuan_api_site[uid()] = {"name": name, "api": yuan_cut}

    # hongguo.json：同样带代理前缀，使用源站真实前缀
    hongguo_sites_list.append({
        "name": name,
        "url": build_api(api_url, '/provide/vod/at/xml'),
        "rule": "",
        "type": "json"
    })

yuan_data = {
    "cache_time": 7200,
    "api_site": yuan_api_site
}

hongguo_data = {
  "format": "duanju-custom-sources",
  "version": 1,
  "count": len(hongguo_sites_list),  # 自动按实际数量，不再写死20
  "sites": hongguo_sites_list
}

# ---------- 写出全部 6 个文件 ----------
def dump(obj, file):
    pathlib.Path(file).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

dump(data_list_for_converted, 'zyvying.json')
dump(data_list_for_zytvbox,   'zytvbox.json')
dump(data_list_for_ysdqbox,   'ysdqbox.json')
dump({"tbl_site": data_list_for_zypcbox}, 'zypcbox.json')
dump(yuan_data, 'libretv.json')
dump(hongguo_data, 'hongguo.json')

print(f"全部转换完成！共生成 6 个 json 文件，hongguo.json 内站点数量：{len(hongguo_sites_list)}")
