#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zh.py  二合一版本
1. 按原逻辑生成 4 份 JSON（zyvying / zytvbox / ysdqbox / zypcbox）
2. 再新增一份 yuan.json（格式同 yuan.txt，key 随机 4 位字母+数字）
源文件统一使用 maqu.txt
"""
import json
import pathlib      # ←←← 补上这一行
import itertools
import random
import string

# ---------- 通用 ----------
SRC = 'maqu.txt'
used_key = set()          # 用于生成不重复随机 key

def uid() -> str:
    """生成 4 位不重复的随机字母+数字"""
    while True:
        s = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        if s not in used_key:
            used_key.add(s)
            return s

# ---------- 原 zh.txt 逻辑 ----------
data_list_for_converted = []
data_list_for_zytvbox   = []
data_list_for_ysdqbox   = []
data_list_for_zypcbox   = []
data_list_for_hongguo   = []

id_counter = itertools.count(1)

with open(SRC, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    line = line.strip()
    if not line or ',' not in line:
        continue
    name, api_url = map(str.strip, line.split(',', 1))
    api_url = api_url.rsplit('api.php/provide/vod/at/xml', 1)[0]          # 去掉尾部 at/xml

    # 1. zyvying
    data_list_for_converted.append({
        "key": name,
        "name": name,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + api_url + 'api.php/provide/vod/at/xml',
        "useInSearchAll": True
    })

    # 2. zytvbox
    data_list_for_zytvbox.append({
        "key": name,
        "name": name,
        "type": 1,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + api_url + 'api.php/provide/vod/',
        "searchable": 1,
        "recordable": 0
    })

    # 3. ysdqbox
    data_list_for_ysdqbox.append({
        "type": "",
        "sourceName": name,
        "baseUrl": "",
        "apiUrl": 'https://cfkua.wokaotianshi.eu.org/' + api_url + 'api.php/provide/vod/at/xml',
        "searchUrl": "",
        "detailUrl": "",
        "parserUrl": ""
    })

    # 4. zypcbox
    data_list_for_zypcbox.append({
        "key": name,
        "name": name,
        "api": 'https://cfkua.wokaotianshi.eu.org/' + api_url + 'api.php/provide/vod/at/xml',
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
          # 5. hongguo
    data_list_for_hongguo.append({
        "name": name,
        "url": 'https://cfkua.wokaotianshi.eu.org/' + api_url
    })


# ---------- 新增 yuan.json 逻辑 ----------
yuan_api_site = {}
for line in lines:
    line = line.strip()
    if not line or ',' not in line:
        continue
    name, api_url = map(str.strip, line.split(',', 1))
    api_url = api_url.rsplit('/at/xml', 1)[0]   
    yuan_api_site[uid()] = {"name": name, "api": api_url}

yuan_data = {
    "cache_time": 7200,
    "api_site": yuan_api_site
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
dump(data_list_for_hongguo,   'hongguo.json')

print("全部转换完成！共生成 6 个 json 文件。")






