#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zh.py  二合一版本
1. 按原逻辑生成 4 份 JSON（zyvying / zytvbox / ysdqbox / zypcbox）
2. 新增 libretv.json（yuan.json）
3. 修复 hongguo.json 格式，sites 为对象数组
源文件统一使用 maqu.txt
"""
import json
import pathlib
import itertools
import random
import string

# ---------- 通用配置 ----------
SRC = 'maqu.txt'
used_key = set()          # 用于生成不重复随机 key

def uid() -> str:
    """生成 4 位不重复的随机字母+数字"""
    while True:
        s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if s not in used_key:
            used_key.add(s)
            return s

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
    # 统一裁剪
    cut_url = api_url.rsplit('api.php/provide/vod/at/xml', 1)[0]

    # 1. zyvying
    data_list_for_converted.append({
        "key": name,
        "name": name,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + cut_url + '/api.php/provide/vod/at/xml',
        "useInSearchAll": True
    })
    # 2. zytvbox
    data_list_for_zytvbox.append({
        "key": name,
        "name": name,
        "type": 1,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + cut_url + 'api.php/provide/vod/',
        "searchable": 1,
        "recordable": 0
    })
    # 3. ysdqbox
    data_list_for_ysdqbox.append({
        "type": "",
        "sourceName": name,
        "baseUrl": "",
        "apiUrl": 'https://cfkua.wokaotianshi.eu.org/' + cut_url + 'api.php/provide/vod/at/xml',
        "searchUrl": "",
        "detailUrl": "",
        "parserUrl": ""
    })
    # 4. zypcbox
    data_list_for_zypcbox.append({
        "key": name,
        "name": name,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + cut_url + 'api.php/provide/vod/at/xml',
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

    # libretv.json（原yuan.json）
    yuan_cut = api_url.rsplit('/at/xml', 1)[0]
    yuan_api_site[uid()] = {"name": name, "api": yuan_cut}

    # hongguo.json 【重点修改】直接append对象到数组
    hongguo_cut = api_url.rsplit('/api.php/provide/vod/at/xml', 1)[0]
    hongguo_sites_list.append({
        "name": name,
        "url": 'https://cfkua.wokaotianshi.eu.org/' + hongguo_cut + '/api.php/provide/vod/at/xml',
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
