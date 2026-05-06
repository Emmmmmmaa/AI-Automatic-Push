# #!/usr/bin/env python3

# # option2 可以尝试rag
# """
# AI资讯推送机器人 - 飞书版
# 功能：聚合多源AI资讯，通过Claude API智能摘要，推送到飞书群
# """

# import os
# import feedparser
# import requests
# import sqlite3
# import json
# import hashlib
# import time
# import schedule
# import logging
# from datetime import datetime, timedelta
# from typing import Optional
# import anthropic
# from dotenv import load_dotenv

# load_dotenv()

# # ============================================================
# # 配置区（按需修改）
# # ============================================================
# ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
# FEISHU_WEBHOOK   = os.environ["FEISHU_WEBHOOK"]
# LOOKBACK_HOURS   = 24          # 抓取过去多少小时的内容
# MAX_PER_SECTION = 10  # 每板块最多渲染条数（控制飞书卡片30KB限制）

# os.makedirs("logs", exist_ok=True)
# _log_file = os.path.join("logs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s %(levelname)s %(message)s",
#     handlers=[
#         logging.StreamHandler(),
#         logging.FileHandler(_log_file, encoding="utf-8"),
#     ],
# )
# log = logging.getLogger(__name__)

# # ============================================================
# # 信源配置（见 sources.py）
# # ============================================================
# from sources import RSS_SOURCES, SCRAPE_SOURCES, TWITTER_ACCOUNTS  


# # ============================================================
# # 关键词过滤，也可以用LLM来判定是否与AI相关，但成本较高，所以先用简单关键词过滤掉明显不相关的内容
# # ============================================================
# KEYWORDS = [ 
#     # 模型（关注你列出的重点模型）
#     "GPT", "Claude", "Gemini", "LLaMA", "Llama", "DeepSeek", "Kimi", "Grok", "Qwen",
#     "Flux", "Sora", "Suno", "Kling", "Runway", "Midjourney", "DALL-E", "Stable Diffusion",
#     "Seed", "Hunyuan", "即梦", "Mistral", "Llama", "Imagen", "Veo", "Emu",
#     # 多模态 / 图像 / 视频 / 3D 生成
#     "image generation", "video generation", "3D generation", "text-to-image", "text-to-video",
#     "图像生成", "视频生成", "3D生成", "视觉生成", "多模态",
#     "multimodal", "vision-language", "diffusion", "NeRF", "Gaussian Splatting",
#     # 数据集 & 评测基准
#     "benchmark", "dataset", "leaderboard", "SOTA", "evaluation", "评测基准", "开源数据",
#     # Agent / 框架
#     "multiagent", "multi-agent", "AI agent", "MCP", "智能体", "agentic",
#     "AutoGPT", "LangChain", "CrewAI", "tool use",
#     # 技术
#     "AGI", "transformer", "推理模型", "fine-tuning", "RLHF", "RAG",
#     # 创意设计 AI 工具（AI原生）
#     "Higgsfield", "Krea", "Recraft", "Fal.ai", "Fal", "Midjourney", "Luma",
#     "即梦", "Tapnow", "Flova", "Oiioii", "Pika", "Kling", "Hailuo",
#     "HeyGen", "ElevenLabs", "Suno", "Ideogram", "Meshy", "Rodin", "Trippo",
#     "Dreamina", "Vidmuse", "Crepal", "Manus", "GenSpark", "PixVerse", "OpenArt",
#     "Stability AI",
#     # 创意设计传统工具
#     "Adobe", "Canva", "Figma", "剪映", "美图", "Photoshop", "Firefly",
#     # 社交娱乐 AI
#     "Character.AI", "Replika", "Elys", "Talkie", "星野", "猫箱", "Loopit",
#     "松果时刻", "Wayshot", "无限谷", "AI companion", "AI entertainment",
#     "interactive AI", "AI native", "AI社交",
#     # 中文 AI 公司
#     "阶跃星辰", "智谱", "MiniMax", "豆包", "Kimi", "混元",
#     "字节", "快手", "Moonshot",
#     # 产品/融资
#     "API", "SDK", "launch", "release", "产品发布", "融资", "B轮", "亿美元",
#     "独角兽", "IPO", "并购", "Series", "funding", "valuation", "Pre-A", "A轮",
#     # 二级市场重点公司
#     "NVIDIA", "Google", "Meta", "Microsoft", "OpenAI", "Anthropic", "SpaceX",
#     "英伟达", "谷歌", "苹果", "Apple",
#     "earnings", "revenue", "财报", "市值", "股价", "PE", "EV",
#     # 通用
#     "ChatGPT", "人工智能", "大模型", "LLM", "artificial intelligence",
#     "machine learning", "deep learning", "neural network",
# ]

# def passes_filter(text: str) -> bool: # notice, 如果用llm判定成本会高
#     text_lower = text.lower()
#     return any(kw.lower() in text_lower for kw in KEYWORDS)


# # ============================================================
# # 内容抓取
# # ============================================================
# def fetch_rss(source: dict, since: datetime) -> tuple[list[dict], int]:
#     """Returns (filtered_items, raw_count_in_window)"""
#     items = []
#     raw = 0
#     try:
#         feed = feedparser.parse(source["url"])
#         for entry in feed.entries:
#             pub = None
#             if hasattr(entry, "published_parsed") and entry.published_parsed:
#                 pub = datetime(*entry.published_parsed[:6])
#             elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
#                 pub = datetime(*entry.updated_parsed[:6])

#             if pub and pub < since:
#                 continue

#             title   = getattr(entry, "title", "")
#             link    = getattr(entry, "link", "")
#             raw += 1

#             # prefer full content over summary
#             if hasattr(entry, "content") and entry.content:
#                 raw_summary = entry.content[0].get("value", "")
#             else:
#                 raw_summary = getattr(entry, "summary", "")

#             try:
#                 from bs4 import BeautifulSoup as _BS
#                 summary = _BS(raw_summary, "html.parser").get_text(" ", strip=True)
#             except Exception:
#                 summary = raw_summary

#             items.append({
#                 "title":       title,
#                 "url":         link,
#                 "summary":     summary,
#                 "source":      source["name"],
#                 "category":    source["category"],
#                 "pub_time":    pub.strftime("%m-%d %H:%M") if pub else "",
#                 "source_type": "rss",
#             })
#     except Exception as e:
#         log.warning(f"RSS抓取失败 {source['name']}: {e}")
#     return items, raw


# def _extract_nearby_time(tag) -> Optional[datetime]:
#     """Try to find a pub date near an <a> tag: check <time> in parent/siblings."""
#     import re

#     DATE_PATTERNS = [
#         (r"\b(\d{4}-\d{2}-\d{2})\b",                    "%Y-%m-%d"),
#         (r"\b([A-Z][a-z]+ \d{1,2},\s+\d{4})\b",         "%B %d, %Y"),   # April 13, 2026
#         (r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b",     "%b %d, %Y"),   # Apr 13, 2026
#         (r"\b([A-Z][a-z]{2}\d{1,2},\s+\d{4})\b",         "%b%d, %Y"),
#     ]

#     def _try_parse(text):
#         for pat, fmt in DATE_PATTERNS:
#             m = re.search(pat, text)
#             if m:
#                 try:
#                     return datetime.strptime(m.group(1), fmt)
#                 except Exception:
#                     pass
#         return None

#     # 1. Walk up looking for <time datetime="...">
#     node = tag.parent
#     for _ in range(6):
#         if node is None:
#             break
#         t = node.find("time")
#         if t and t.get("datetime"):
#             try:
#                 return datetime.fromisoformat(t["datetime"][:19])
#             except Exception:
#                 pass
#         node = node.parent

#     # 2. Walk up scanning text of each ancestor (catches sibling <p> with date)
#     node = tag.parent
#     for _ in range(6):
#         if node is None:
#             break
#         result = _try_parse(node.get_text(" ", strip=True))
#         if result:
#             return result
#         node = node.parent

#     return None


# def fetch_webpage(source: dict, since: Optional[datetime] = None) -> tuple[list[dict], int]:
#     """Returns (filtered_items, raw_count). Scrapes up to 30 links.
#     If since is provided, items with a detectable pub date older than since are skipped.
#     Items with no detectable date are always included (rely on dedup instead).
#     """
#     items = []
#     raw = 0
#     try:
#         from bs4 import BeautifulSoup
#         from urllib.parse import urljoin
#         resp = requests.get(source["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
#         soup = BeautifulSoup(resp.text, "html.parser")
#         NAV_KEYWORDS = {"pricing", "login", "signup", "sign-up", "register", "contact",
#                         "about", "careers", "terms", "privacy", "faq", "help", "home",
#                         "features", "api", "docs", "explore", "tag", "category"}
#         seen_hrefs = set()
#         for a in soup.find_all("a", href=True)[:200]:
#             title = a.get_text(strip=True)
#             href  = a["href"]
#             if not href.startswith("http"):
#                 href = urljoin(source["url"], href)
#             if len(title) <= 15:
#                 continue
#             # skip nav/utility links
#             href_lower = href.lower()
#             if any(kw in href_lower for kw in NAV_KEYWORDS):
#                 continue
#             if href in seen_hrefs:
#                 continue
#             seen_hrefs.add(href)
#             raw += 1

#             pub_time = _extract_nearby_time(a)
#             if not pub_time:
#                 continue  # no date = likely not an article
#             if since and pub_time < since:
#                 continue  # too old, skip

#             # 抓取文章正文
#             body = ""
#             try:
#                 article_resp = requests.get(href, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
#                 article_soup = BeautifulSoup(article_resp.text, "html.parser")
#                 for tag in article_soup(["script", "style", "nav", "footer", "header"]):
#                     tag.decompose()
#                 body = article_soup.get_text(" ", strip=True)
#             except Exception:
#                 pass

#             items.append({
#                 "title":       title,
#                 "url":         href,
#                 "summary":     body,
#                 "source":      source["name"],
#                 "category":    source["category"],
#                 "pub_time":    pub_time.strftime("%m-%d %H:%M"),
#                 "source_type": "webpage",
#             })
#     except Exception as e:
#         log.warning(f"网页抓取失败 {source['name']}: {e}")
#     return items, raw


# def fetch_twitter(since: datetime) -> list[dict]:
#     """Fetch recent tweets from monitored accounts via Twitter API v2."""
#     bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
#     if not bearer:
#         return []

#     headers = {"Authorization": f"Bearer {bearer}"}
#     since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
#     items = []

#     for username, meta in TWITTER_ACCOUNTS.items():
#         display_name = meta["name"]
#         category     = meta["category"]
#         try:
#             # Resolve username -> user ID
#             resp = requests.get(
#                 f"https://api.twitter.com/2/users/by/username/{username}",
#                 headers=headers, timeout=10,
#             )
#             user_id = resp.json()["data"]["id"]

#             # Fetch recent tweets
#             resp = requests.get(
#                 f"https://api.twitter.com/2/users/{user_id}/tweets",
#                 headers=headers,
#                 params={
#                     "start_time": since_str,
#                     "max_results": 10,
#                     "tweet.fields": "created_at,text",
#                     "exclude": "retweets,replies",
#                 },
#                 timeout=10,
#             )
#             tweets = resp.json().get("data", [])
#             for tweet in tweets:
#                 import re as _re
#                 clean_text = _re.sub(r'https://t\.co/\S+', '', tweet["text"]).strip()
#                 url = f"https://x.com/{username}/status/{tweet['id']}"
#                 items.append({
#                     "title":       clean_text[:100],
#                     "url":         url,
#                     "summary":     clean_text,
#                     "source":      display_name,
#                     "category":    category,
#                     "pub_time":    tweet.get("created_at", "")[:16].replace("T", " "),
#                     "source_type": "twitter",
#                 })
#             time.sleep(1)  # rate limit buffer
#         except Exception as e:
#             log.warning(f"Twitter抓取失败 {username}: {e}")

#     return items


# def collect_all() -> list[dict]:
#     since = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
#     all_items = []
#     total_raw = 0

#     log.info("开始抓取RSS源...")
#     for src in RSS_SOURCES:
#         fetched, raw = fetch_rss(src, since)
#         all_items.extend(fetched)
#         total_raw += raw
#         log.info(f"  {src['name']}: {len(fetched)}条")
#         time.sleep(0.5)

#     log.info("开始抓取博客页面...")
#     for src in SCRAPE_SOURCES:
#         fetched, raw = fetch_webpage(src, since=since)
#         all_items.extend(fetched)
#         total_raw += raw
#         log.info(f"  {src['name']}: {len(fetched)}条")
#         time.sleep(0.5)

#     # log.info("开始抓取Twitter...")
#     # twitter_items = fetch_twitter(since)
#     # all_items.extend(twitter_items)
#     # log.info(f"  Twitter: {len(twitter_items)}条")

#     print(f"\n{'='*40}")
#     print(f"共采集到 {len(all_items)} 条")
#     print(f"{'='*40}\n")
#     log.info(f"共采集到 {len(all_items)} 条")
#     return all_items

# # ============================================================
# # Claude AI 分析与摘要
# # ============================================================
# SECTION_MAP = {
#     "model":    "🤖 模型更新", # model
#     "research": "🔬 研究前沿", # research
#     "biz":      "💼 应用层追踪", # creative, social
#     "media":     "📰 媒体", # media, tech, public market
#     "funding":  "💰 一级市场", # funding

#     "opinion":  "💡 高质量观点", # opinion
#         # "public_market": "📈 二级市场",
# }

# # 将信源 category 归并到推送 section
# CATEGORY_TO_SECTION = {
#     "model":         "model_updates",
#     "research":      "research",
#     "creative":      "app_tracking",
#     "social":        "app_tracking",
#     "biz":           "media",
#     "tech":          "media",
#     "public_market": "public_market",
#     "funding":       "funding",
#     "opinion":       "opinions",
# }



# SECTION_LOG_ORDER = [
#     ("model_updates", "🤖 模型更新"),
#     ("research",      "🔬 研究前沿"),
#     ("app_tracking",  "💼 应用层追踪"),
#     ("media",         "📰 媒体"),
#     ("funding",       "💰 一级市场"),
#     # ("public_market", "📈 二级市场"), 
#     ("opinions",      "💡 高质量观点"),
# ]

# from utils import fetch_stock_data
# from process.feishu_bitable import write_items_to_bitable


# # ============================================================
# # 飞书消息构建与发送
# # ============================================================
# def importance_stars(n: int) -> str:
#     return "⭐" * min(n, 5)

# def build_feishu_card(sections: dict, date_str: str) -> dict:
#     """构建飞书富文本卡片"""
    
#     def item_line(item: dict) -> dict:
#         stars = importance_stars(item.get("importance", 3))
#         return {
#             "tag": "div",
#             "text": {
#                 "tag": "lark_md",
#                 "content": f"{stars} **[{item['title']}]({item['url']})**\n"
#                            f"{item['summary']}  —— *{item['source']}*"
#             }
#         }

#     section_configs = [
#         ("model_updates", "🤖 模型更新"),
#         ("research",      "🔬 研究前沿"),
#         ("app_tracking",  "💼 应用层追踪"),
#         ("media",         "📰 媒体"),
#         ("funding",       "💰 一级市场"),
#         ("opinions",      "💡 高质量观点"),
#     ]

#     elements = []

#     for key, title in section_configs:
#         items = sections.get(key, [])
#         if not items:
#             continue

#         # 板块标题
#         elements.append({
#             "tag": "div",
#             "text": {"tag": "lark_md", "content": f"**{title}**"}
#         })
#         elements.append({"tag": "hr"})

#         for item in items:
#             elements.append(item_line(item))

#         elements.append({"tag": "div", "text": {"tag": "lark_md", "content": " "}})

#     total = sum(len(sections.get(k, [])) for k, _ in section_configs)

#     # 二级市场股价表格（独立板块，不走 AI 摘要）
#     stock_rows = fetch_stock_data()
#     stock_elements = build_stock_elements(stock_rows)
#     print("\n── stock_elements（发送给飞书的结构）──")
#     print(json.dumps(stock_elements, ensure_ascii=False, indent=2))

#     card = {
#         "msg_type": "interactive",
#         "card": {
#             "header": {
#                 "title": {
#                     "tag": "plain_text",
#                     "content": f"🗞 AI日报 · 前12小时"
#                 },
#                 "template": "blue"
#             },
#             "elements": elements + stock_elements 
#         }
#     }
#     return card


# def send_to_feishu(card: dict) -> bool:
#     try:
#         resp = requests.post(
#             FEISHU_WEBHOOK,
#             json=card,
#             headers={"Content-Type": "application/json"},
#             timeout=10
#         )
#         data = resp.json()
#         if data.get("code") == 0 or data.get("StatusCode") == 0:
#             log.info("飞书推送成功 ✅")
#             return True
#         else:
#             log.error(f"飞书推送失败: {data}")
#             return False
#     except Exception as e:
#         log.error(f"飞书推送异常: {e}")
#         return False


# def send_text_to_feishu(text: str) -> bool:
#     """发送纯文本（用于测试或错误通知）"""
#     payload = {"msg_type": "text", "content": {"text": text}}
#     try:
#         resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
#         return resp.json().get("code") == 0
#     except:
#         return False

# # ============================================================
# # 主流程
# # ============================================================


# def run_scheduler():
#     """定时任务模式"""
#     log.info(f"调度模式启动，每天 {PUSH_HOURS} 推送")
#     for h in PUSH_HOURS:
#         schedule.every().day.at(f"{h:02d}:00").do(run_once)
#     while True:
#         schedule.run_pending()
#         time.sleep(60)


# # ============================================================
# def test_source(url: str, scrape: bool = False):
#     """Quick test for a single source. scrape=True uses fetch_webpage, default uses fetch_rss."""
#     src = {"name": "test", "url": url, "category": "test"}
#     items, raw = fetch_webpage(src) if scrape else fetch_rss(src, datetime.now() - timedelta(days=365))
#     print(f"Fetched {len(items)}/{raw} items (filtered/raw) from {url}")
#     for i, it in enumerate(items, 1):
#         print(f"[{i:02d}] {it['title']}")
#         print(f"     {it['url']}")
#         print()



# def run_collect():
#     """只采集+写入多维表格，跳过AI分析和飞书卡片推送。"""
#     log.info("=" * 50)
#     log.info(f"采集模式启动 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
#     items = collect_all()
#     if not items:
#         log.info("没有新内容")
#         send_text_to_feishu(f"[AI采集] {datetime.now().strftime('%Y-%m-%d %H:%M')} 完成，无新内容")
#         return
#     write_items_to_bitable(items)
#     log.info("采集完成")
#     send_text_to_feishu(f"[AI采集] {datetime.now().strftime('%Y-%m-%d %H:%M')} 完成，共采集 {len(items)} 条")


# if __name__ == "__main__":
#     import sys
#     args = sys.argv[1:]
#     if args and args[0] == "--collect":
#         run_collect()
#     elif args and args[0] == "--test" and len(args) >= 2:
#         test_source(args[1], scrape="--scrape" in args)
#     else:
#         run_scheduler()
