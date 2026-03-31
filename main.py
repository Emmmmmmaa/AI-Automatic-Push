#!/usr/bin/env python3
"""
AI资讯推送机器人 - 飞书版
功能：聚合多源AI资讯，通过Claude API智能摘要，推送到飞书群
"""

import os
import feedparser
import requests
import sqlite3
import json
import hashlib
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import Optional
import anthropic
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 配置区（按需修改）
# ============================================================
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
FEISHU_WEBHOOK   = os.environ["FEISHU_WEBHOOK"]
DB_PATH          = "newsletter.db"
LOOKBACK_HOURS   = 12          # 抓取过去多少小时的内容
PUSH_HOURS       = [9, 21]     # 每天推送时间（24小时制），可添加多个
MAX_ITEMS_PER_SECTION = 5      # 每板块最多展示条数

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ============================================================
# RSS 信源配置
# ============================================================
RSS_SOURCES = [
    # 中文技术媒体
    {"name": "机器之心",   "url": "https://www.jiqizhixin.com/rss",          "lang": "zh", "category": "tech"},
    {"name": "量子位",     "url": "https://www.qbitai.com/feed",              "lang": "zh", "category": "tech"},
    {"name": "新智元",     "url": "https://www.xinzhi.com/rss",               "lang": "zh", "category": "tech"},
    {"name": "36氪",       "url": "https://36kr.com/feed",                    "lang": "zh", "category": "biz"},
    {"name": "钛媒体",     "url": "https://www.tmtpost.com/feed",             "lang": "zh", "category": "biz"},

    # 英文技术媒体
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/",             "lang": "en", "category": "biz"},
    {"name": "TechCrunch Venture", "url": "https://techcrunch.com/category/venture/feed/", "lang": "en", "category": "funding"},
    {"name": "VentureBeat","url": "https://venturebeat.com/feed/",            "lang": "en", "category": "tech"},
    {"name": "Wired AI",   "url": "https://www.wired.com/feed/tag/artificial-intelligence/rss", "lang": "en", "category": "tech"},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/index", "lang": "en", "category": "tech"},

    # AI 公司官方博客
    {"name": "OpenAI Blog",   "url": "https://openai.com/news/rss.xml",       "lang": "en", "category": "model"},
    {"name": "Google DeepMind","url": "https://deepmind.google/blog/rss.xml", "lang": "en", "category": "model"},
    {"name": "Anthropic Blog", "url": "https://www.anthropic.com/news/rss",   "lang": "en", "category": "model"},
    {"name": "Microsoft AI",   "url": "https://blogs.microsoft.com/ai/feed/", "lang": "en", "category": "model"},
    {"name": "Hugging Face",   "url": "https://huggingface.co/blog/feed.xml", "lang": "en", "category": "model"},

    # arXiv（AI子领域）
    {"name": "arXiv cs.AI",   "url": "https://rss.arxiv.org/rss/cs.AI",      "lang": "en", "category": "research"},
    {"name": "arXiv cs.LG",   "url": "https://rss.arxiv.org/rss/cs.LG",      "lang": "en", "category": "research"},
    {"name": "arXiv cs.CV",   "url": "https://rss.arxiv.org/rss/cs.CV",      "lang": "en", "category": "research"},

    # 创投
    {"name": "YC Blog",       "url": "https://www.ycombinator.com/blog/rss",  "lang": "en", "category": "funding"},

    # 高质量博客
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/entries/", "lang": "en", "category": "opinion"},
    {"name": "Lilian Weng",    "url": "https://lilianweng.github.io/index.xml",  "lang": "en", "category": "opinion"},
]

# 需要直接抓取网页的博客（无RSS）
SCRAPE_SOURCES = [
    {"name": "Karpathy Blog",     "url": "https://karpathy.ai",              "category": "opinion"},
    {"name": "Sam Altman Blog",   "url": "https://blog.samaltman.com",       "category": "opinion"},
    {"name": "Dario Amodei Blog", "url": "https://www.darioamodei.com",      "category": "opinion"},
    {"name": "Colah Blog",        "url": "https://colah.github.io",          "category": "opinion"},
    {"name": "HN Buzzing",        "url": "https://hn.buzzing.cc",            "category": "opinion"},
    {"name": "AI Hub Today",      "url": "https://ai.hubtoday.app",          "category": "opinion"},
]

# ============================================================
# 关键词过滤
# ============================================================
KEYWORDS = [
    # 模型
    "GPT", "Claude", "Gemini", "LLaMA", "Llama", "DeepSeek", "Kimi", "Grok", "Qwen",
    "Flux", "Sora", "Suno", "Kling", "Runway", "Midjourney", "DALL-E", "Stable Diffusion",
    "Seed", "Hunyuan", "即梦",
    # Agent
    "multiagent", "multi-agent", "AI agent", "MCP", "智能体", "agentic",
    # 技术
    "AGI", "多模态", "multimodal", "transformer", "推理模型", "SOTA", "benchmark",
    "fine-tuning", "RLHF", "RAG", "diffusion", "vision-language",
    # 产品/融资
    "API", "SDK", "launch", "release", "产品发布", "融资", "B轮", "亿美元",
    "独角兽", "IPO", "并购", "Series", "funding", "valuation",
    # 通用
    "ChatGPT", "OpenAI", "人工智能", "大模型", "LLM", "artificial intelligence",
    "machine learning", "deep learning", "neural network",
    # 创意设计类公司
    "Adobe", "Canva", "Figma", "Midjourney", "Higgsfield", "Krea", "Recraft",
    "Fal.ai", "Luma", "Runway", "剪映", "美图",
]

def passes_filter(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)

# ============================================================
# 数据库
# ============================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            hash TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def is_seen(conn, url: str) -> bool:
    h = hashlib.md5(url.encode()).hexdigest()
    return conn.execute("SELECT 1 FROM seen_items WHERE hash=?", (h,)).fetchone() is not None

def mark_seen(conn, url: str, title: str, source: str):
    h = hashlib.md5(url.encode()).hexdigest()
    conn.execute("INSERT OR IGNORE INTO seen_items(hash,title,url,source) VALUES(?,?,?,?)",
                 (h, title, url, source))
    conn.commit()

def cleanup_old(conn):
    """清理7天前的记录"""
    conn.execute("DELETE FROM seen_items WHERE created_at < datetime('now','-7 days')")
    conn.commit()

# ============================================================
# 内容抓取
# ============================================================
def fetch_rss(source: dict, since: datetime) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            # 解析时间
            pub = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub = datetime(*entry.updated_parsed[:6])
            
            if pub and pub < since:
                continue

            title   = getattr(entry, "title", "")
            link    = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")
            
            text_to_check = f"{title} {summary}"
            if not passes_filter(text_to_check):
                continue

            items.append({
                "title":    title,
                "url":      link,
                "summary":  summary[:500],
                "source":   source["name"],
                "category": source["category"],
                "pub_time": pub.strftime("%m-%d %H:%M") if pub else "",
            })
    except Exception as e:
        log.warning(f"RSS抓取失败 {source['name']}: {e}")
    return items


def fetch_webpage(source: dict) -> list[dict]:
    """简单抓取网页，提取标题和链接"""
    items = []
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(source["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True)[:30]:
            title = a.get_text(strip=True)
            href  = a["href"]
            if not href.startswith("http"):
                from urllib.parse import urljoin
                href = urljoin(source["url"], href)
            if len(title) > 15 and passes_filter(title):
                items.append({
                    "title":    title,
                    "url":      href,
                    "summary":  "",
                    "source":   source["name"],
                    "category": source["category"],
                    "pub_time": "",
                })
    except Exception as e:
        log.warning(f"网页抓取失败 {source['name']}: {e}")
    return items


def collect_all(conn: sqlite3.Connection) -> list[dict]:
    since = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    all_items = []

    log.info("开始抓取RSS源...")
    for src in RSS_SOURCES:
        new_items = [i for i in fetch_rss(src, since) if not is_seen(conn, i["url"])]
        all_items.extend(new_items)
        log.info(f"  {src['name']}: {len(new_items)}条新内容")
        time.sleep(0.5)

    log.info("开始抓取博客页面...")
    for src in SCRAPE_SOURCES:
        new_items = [i for i in fetch_webpage(src) if not is_seen(conn, i["url"])]
        all_items.extend(new_items)
        log.info(f"  {src['name']}: {len(new_items)}条新内容")
        time.sleep(0.5)

    log.info(f"共采集到 {len(all_items)} 条新内容")
    return all_items

# ============================================================
# Claude AI 分析与摘要
# ============================================================
SECTION_MAP = {
    "model":    "🤖 模型更新",
    "research": "🔬 研究前沿",
    "biz":      "💼 应用层追踪",
    "funding":  "💰 融资动态",
    "opinion":  "💡 高质量观点",
}

def ai_summarize(items: list[dict]) -> dict:
    """
    让Claude对收集到的内容进行分类、摘要、重要性打分
    返回按板块组织的结构化数据
    """
    if not items:
        return {}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    items_text = "\n\n".join(
        f"[{i+1}] 来源:{item['source']} | 分类:{item['category']}\n"
        f"标题：{item['title']}\n"
        f"摘要：{item['summary'][:300]}\n"
        f"链接：{item['url']}"
        for i, item in enumerate(items[:60])  # 最多处理60条
    )

    prompt = f"""你是一个AI行业资讯编辑，请对以下 {len(items[:60])} 条资讯进行处理：

{items_text}

请按以下5个板块分类并摘要，每个板块选取最重要的{MAX_ITEMS_PER_SECTION}条：

1. **模型更新**（model/research）：LLM、多模态模型、开源模型、benchmark、技术突破
2. **应用层追踪**（biz）：产品发布、功能更新、创意设计工具（Adobe/Canva/Figma/Midjourney等）
3. **融资动态**（funding）：一级市场融资、并购、估值变化
4. **二级市场**：上市公司财报、股价、市值（如有）
5. **高质量观点**（opinion）：行业大佬博客、深度分析

输出格式（严格JSON）：
{{
  "model_updates": [
    {{"title": "...", "summary": "一句话中文摘要（30字内）", "url": "...", "source": "...", "importance": 1-5}}
  ],
  "app_tracking": [...],
  "funding": [...],
  "public_market": [...],
  "opinions": [...]
}}

要求：
- summary必须是中文，简洁有信息量
- importance 5=重大突破，1=一般资讯
- 只保留真正与AI相关的内容
- 按importance降序排列
"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000, # notice here
            messages=[{"role": "user", "content": prompt}]
        )
        text = msg.content[0].text
        # 去除可能的 markdown 代码块包裹
        if "```" in text:
            lines = text.splitlines()
            text = "\n".join(
                l for l in lines
                if not l.strip().startswith("```")
            )
        # 替换中文弯引号为直引号，避免 JSON 解析失败
        text = text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        start = text.find("{")
        end   = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        log.error(f"AI分析失败: {e}")
        log.error(f"原始返回内容:\n{text if 'text' in locals() else '(无内容)'}")
        return {}

# ============================================================
# 飞书消息构建与发送
# ============================================================
def importance_stars(n: int) -> str:
    return "⭐" * min(n, 5)

def build_feishu_card(sections: dict, date_str: str) -> dict:
    """构建飞书富文本卡片"""
    
    def item_line(item: dict) -> dict:
        stars = importance_stars(item.get("importance", 3))
        return {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{stars} **[{item['title'][:50]}]({item['url']})**\n"
                           f"↳ {item['summary']}  —— *{item['source']}*"
            }
        }

    section_configs = [
        ("model_updates", "🤖 模型更新"),
        ("app_tracking",  "🛠 应用层追踪"),
        ("funding",       "💰 融资动态"),
        ("public_market", "📈 二级市场"),
        ("opinions",      "💡 高质量观点"),
    ]

    elements = []
    
    for key, title in section_configs:
        items = sections.get(key, [])
        if not items:
            continue
        
        # 板块标题
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{title}**"}
        })
        elements.append({"tag": "hr"})
        
        for item in items[:MAX_ITEMS_PER_SECTION]:
            elements.append(item_line(item))
        
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": " "}})

    total = sum(len(sections.get(k, [])) for k, _ in section_configs)
    
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🗞 AI日报 · {date_str}"
                },
                "template": "blue"
            },
            "elements": elements + [
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [{
                        "tag": "plain_text",
                        "content": f"共 {total} 条资讯 · 由 Claude AI 智能摘要 · {date_str}"
                    }]
                }
            ]
        }
    }
    return card


def send_to_feishu(card: dict) -> bool:
    try:
        resp = requests.post(
            FEISHU_WEBHOOK,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        data = resp.json()
        if data.get("code") == 0 or data.get("StatusCode") == 0:
            log.info("飞书推送成功 ✅")
            return True
        else:
            log.error(f"飞书推送失败: {data}")
            return False
    except Exception as e:
        log.error(f"飞书推送异常: {e}")
        return False


def send_text_to_feishu(text: str) -> bool:
    """发送纯文本（用于测试或错误通知）"""
    payload = {"msg_type": "text", "content": {"text": text}}
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        return resp.json().get("code") == 0
    except:
        return False

# ============================================================
# 主流程
# ============================================================
def run_once():
    log.info("=" * 50)
    log.info(f"开始执行资讯推送任务 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    conn = init_db()
    cleanup_old(conn)

    # 1. 采集
    items = collect_all(conn)
    
    if not items:
        log.info("没有新内容，跳过推送")
        return

    # 2. AI分析
    log.info("调用Claude进行智能分析...")
    sections = ai_summarize(items)

    # 3. 标记已读
    for item in items:
        mark_seen(conn, item["url"], item["title"], item["source"])

    # 4. 构建并发送
    date_str = datetime.now().strftime("%Y年%m月%d日")
    
    if sections:
        card = build_feishu_card(sections, date_str)
        send_to_feishu(card)
    else:
        send_text_to_feishu(f"⚠️ AI日报 {date_str}：内容处理异常，请检查日志")

    conn.close()
    log.info("任务完成")


def run_scheduler():
    """定时任务模式"""
    log.info(f"调度模式启动，每天 {PUSH_HOURS} 推送")
    for h in PUSH_HOURS:
        schedule.every().day.at(f"{h:02d}:00").do(run_once)
    while True:
        schedule.run_pending()
        time.sleep(60)


# ============================================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        run_once()          # 立即执行一次（测试用）
    else:
        run_scheduler()     # 定时运行
