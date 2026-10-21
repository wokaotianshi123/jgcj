import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin

# -------------------------- 配置区 --------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.yszzq.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
BASE_URL = "https://www.yszzq.com/ziyuan/api/"
HOME_PAGE = f"{BASE_URL}index.html"
OUTPUT_FILE = "pq.txt"
DELAY = 1.2        # 每页请求间隔，防反爬
RETRY_TIMES = 2    # 请求失败重试次数
DEBUG_PRINT = True # 是否打印每条提取结果

# 关键词：需要【同时包含】一组里任意一个 + 二组里任意一个
core_keywords = ["采集接口", "接口大全", "规则地址", "接口地址", "资源接口", "API接口", "采集地址"]
supplement_keywords = ["资源站", "采集站", "资源网", "采集网", "云播", "资源", "综合"]

# 需要清除的垃圾文本列表
rubbish_list = [
    "赞助",
    "苹果cms", "苹果CMS",
    "海洋cms", "海洋CMS",
    "飞飞cms", "飞飞CMS",
    "马克斯CMS", "马克斯cms",
    "赞片CMS", "赞片cms",
    "赤兔CMS", "赤兔cms",
    "API电影", "电视剧", "动漫", "综艺","失效","api", "体育", "舞蹈", "新闻"
]
# -----------------------------------------------------------

def clean_title(raw_text: str) -> str:
    """清洗标题，剔除后面CMS、分类、赞助后缀，只保留主体名称"""
    text = raw_text.strip()
    # 正则：匹配 空格 / 斜杠 分隔的垃圾内容，全部删掉
    rubbish_pat = re.compile(r"[ /]+(" + "|".join(re.escape(x) for x in rubbish_list) + r")", re.IGNORECASE)
    text = rubbish_pat.sub("", text)
    # 清理连续空格
    text = re.sub(r"\s+", "", text)
    return text

def safe_get(url, retry=RETRY_TIMES):
    """带重试的requests.get封装"""
    for i in range(retry):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp
        except Exception as e:
            if i < retry - 1:
                if DEBUG_PRINT:
                    print(f"请求失败，第{i+1}次重试: {url} 错误:{e}")
                time.sleep(DELAY)
            else:
                print(f"多次重试失败：{url} | {e}")
    return None

def get_last_page_number():
    """获取尾页数字"""
    resp = safe_get(HOME_PAGE)
    if not resp:
        print("首页请求失败，默认尾页=1")
        return 1
    soup = BeautifulSoup(resp.text, "html.parser")
    last_page_link = soup.find("a", string="尾页")
    if not last_page_link:
        print("未找到尾页按钮，默认尾页=1")
        return 1
    href = last_page_link.get("href", "")
    match = re.search(r"index_(\d+)\.html", href)
    if match:
        last_page = int(match.group(1))
        print(f"✅ 识别到尾页：{last_page}")
        return last_page
    else:
        print("尾页链接匹配失败，默认尾页=1")
        return 1

def get_page_url(page_num):
    if page_num == 1:
        return HOME_PAGE
    return f"{BASE_URL}index_{page_num}.html"

def parse_page(page_url):
    result = []
    time.sleep(DELAY)
    resp = safe_get(page_url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    a_tags = soup.find_all("a")
    for a in a_tags:
        raw_text = a.get_text(strip=True)
        href = a.get("href", "").strip()
        # 跳过无效链接
        if not href or href.startswith(("javascript:", "#")):
            continue
        has_core = any(kw in raw_text for kw in core_keywords)
        has_supplement = any(kw in raw_text for kw in supplement_keywords)
        if has_core and has_supplement:
            clean_name = clean_title(raw_text)
            # 清洗后为空就跳过这条
            if not clean_name:
                continue
            full_url = urljoin(BASE_URL, href)
            result.append((clean_name, full_url))
            if DEBUG_PRINT:
                print(f"📌 清洗后: {clean_name},{full_url} 【原始：{raw_text}】")
    return result

def main():
    last_page = get_last_page_number()
    all_data = []
    seen = set()

    for page_num in range(1, last_page + 1):
        print(f"\n===== 正在处理第 {page_num}/{last_page} 页 =====")
        page_url = get_page_url(page_num)
        page_items = parse_page(page_url)
        for name, link in page_items:
            key = (name, link)
            if key not in seen:
                seen.add(key)
                all_data.append((name, link))

    # 写入文件，严格格式：名称,url
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for name, link in all_data:
            f.write(f"{name},{link}\n")

    print(f"\n🎉 全部完成！一共提取 {len(all_data)} 条，保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
