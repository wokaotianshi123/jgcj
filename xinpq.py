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

# 卡片容器候选选择器：网页改版时按优先级自动尝试，不用改逻辑
CARD_SELECTORS = [
    "article.isgood",        # 当前站点结构：<article class="isgood">
    "article",               # 退路：任意 article
    "li",                    # 常见列表卡片
    "div.item", "div.list", "div.resource", "div.api-item",
    "div[class*='item']", "div[class*='list']", "div[class*='good']",
]

# 卡片内标题的候选选择器（按优先级）
TITLE_SELECTORS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "[class*='title']", "[class*='name']", "[class*='head']",
]

# 卡片内会干扰标题的"垃圾小标签"，通常是 <span class="ico">赞助</span> 这类
ICON_SELECTOR = "[class*='ico']"

# 关键词：名称里需【同时满足】一组任意一个 + 二组任意一个
core_keywords   = ["采集接口", "接口大全", "规则地址", "接口地址", "资源接口", "API接口", "采集地址"]
supplement_words = ["资源站", "采集站", "资源网", "采集网", "云播", "资源", "综合"]

# 保底清洗用的垃圾文本（正则剔除）
RUBBISH = [
    "赞助", "苹果cms", "海洋cms", "飞飞cms", "马克斯CMS", "赞片CMS", "赤兔CMS",
    "API电影", "电视剧", "动漫", "综艺", "体育", "舞蹈", "新闻",
]
# -----------------------------------------------------------

def safe_get(url, retry=RETRY_TIMES):
    """带重试的请求封装"""
    for i in range(retry):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp
        except Exception as e:
            if i < retry - 1:
                if DEBUG_PRINT:
                    print(f"  请求失败，第{i+1}次重试: {url} 错误:{e}")
                time.sleep(DELAY)
            else:
                print(f"  多次重试失败：{url} | {e}")
    return None

def get_last_page_number():
    """获取尾页数字（带多种解析兜底）"""
    resp = safe_get(HOME_PAGE)
    if not resp:
        print("首页请求失败，默认尾页=1")
        return 1
    soup = BeautifulSoup(resp.text, "html.parser")

    # 策略1：按文字"尾页"找
    link = soup.find("a", string="尾页")
    # 策略2：按 "尾页" 属性或 title
    if not link:
        link = soup.find("a", href=re.compile(r"index_\d+\.html$"))
    if not link:
        print("未找到尾页链接，默认尾页=1")
        return 1

    href = link.get("href", "")
    m = re.search(r"index_(\d+)\.html", href)
    if m:
        last = int(m.group(1))
        print(f"✅ 识别到尾页：{last}")
        return last
    print("尾页链接格式异常，默认尾页=1")
    return 1

def get_page_url(page_num):
    if page_num == 1:
        return HOME_PAGE
    return f"{BASE_URL}index_{page_num}.html"

# ----------------- 名称提取：三级级联 + 全程兜底 -----------------
def clean_with_regex(text: str) -> str:
    """保底方案：正则剔除垃圾词与噪音符号"""
    t = text.strip()
    for kw in RUBBISH:
        # 匹配"空格/斜杠 + 垃圾词"以及孤立的垃圾词
        t = re.sub(rf"(?:[/\s·|]+{re.escape(kw)})|(?:{re.escape(kw)}[/\s·|]+)", "", t, flags=re.IGNORECASE)
    t = t.strip('"\' ').strip()
    t = re.sub(r"\s+", "", t)      # 去内部空白
    t = re.sub(r"[「」『』【】\[\]()（）]+", "", t)  # 去多余符号
    return t

def extract_title_from_node(node) -> str:
    """从任意节点里抠标题：去掉 icon 标签后取文本"""
    try:
        # 删除干扰小标签（赞助等）
        for icon in node.select(ICON_SELECTOR):
            icon.decompose()
        txt = node.get_text(" ", strip=True)
        return clean_with_regex(txt)
    except Exception:
        return ""

def extract_name_from_card(card) -> str:
    """策略A：从卡片容器内部，按优先级找标题标签取名称"""
    for sel in TITLE_SELECTORS:
        try:
            for node in card.select(sel):
                name = extract_title_from_node(node)
                if name:
                    return name
        except Exception:
            continue
    return ""

def extract_name_fallback(a_tag) -> str:
    """策略B：卡片结构失效时的保底——直接清洗链接文本"""
    return extract_title_from_node(a_tag)

def parse_page(page_url):
    """解析单个页面：找卡片→提名称→提链接，全程容错"""
    result = []
    time.sleep(DELAY)
    resp = safe_get(page_url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")

    cards = []
    # 1) 尝试按候选选择器找卡片容器
    for sel in CARD_SELECTORS:
        try:
            found = soup.select(sel)
            if found:
                cards = found
                if DEBUG_PRINT:
                    print(f"  [卡片] 命中选择器：{sel}（{len(found)} 个）")
                break
        except Exception:
            continue
    # 2) 没找到卡片 → 退回直接遍历所有 a 标签
    if not cards:
        cards = soup.find_all("a")

    for card in cards:
        try:
            # 定位卡片内的链接（可能卡片本身就是 a，也可能是包裹的 a）
            if card.name == "a":
                a_tag = card
            else:
                a_tag = card.find("a")

            href = a_tag.get("href", "").strip() if a_tag else ""
            if not href or href.startswith(("javascript:", "#")):
                continue

            # ---- 名称提取：卡片优先，失败则链接文本保底 ----
            if card.name == "a":
                name = extract_name_fallback(card)        # 卡片即链接，直接清洗
            else:
                name = extract_name_from_card(card)       # 策略A：卡片内标题
                if not name:
                    name = extract_name_fallback(a_tag)   # 策略B：链接文本保底

            if not name:
                continue  # 名称彻底取不到，跳过该条，不影响整体

            # 名称关键词过滤（避免捞进无关链接）
            has_core   = any(kw in name for kw in core_keywords)
            has_supple = any(kw in name for kw in supplement_words)
            if not (has_core and has_supple):
                continue

            full_url = urljoin(BASE_URL, href)
            result.append((name, full_url))
            if DEBUG_PRINT:
                print(f"  📌 提取: {name},{full_url}  [卡片:{card.name}]")
        except Exception as e:
            if DEBUG_PRINT:
                print(f"  ⚠️ 单条解析失败已跳过: {e}")
            continue
    return result

def main():
    last_page = get_last_page_number()
    all_data, seen = [], set()

    for page_num in range(1, last_page + 1):
        print(f"\n===== 正在处理第 {page_num}/{last_page} 页 =====")
        for name, link in parse_page(get_page_url(page_num)):
            key = (name, link)
            if key not in seen:
                seen.add(key)
                all_data.append((name, link))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for name, link in all_data:
            f.write(f"{name},{link}\n")

    print(f"\n🎉 全部完成！共 {len(all_data)} 条，已写入 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
