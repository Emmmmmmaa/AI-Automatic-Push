#!/usr/bin/env python3
"""
push_new.py — AI资讯采集 + 写入飞书多维表格
从 RSS / 网页采集最近24小时内容，批量写入 Bitable。
"""

import os
import sys
import json
import time
import logging
import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# 确保项目根目录在 path 中（脚本在 push_task/ 子目录下）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

LOOKBACK_HOURS = 24

os.makedirs("logs", exist_ok=True)
_log_file = os.path.join("logs", datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_log_file, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

import re
from sources import RSS_SOURCES, SCRAPE_SOURCES, WECHAT_ACCOUNTS as WECHAT_ACCOUNTS_AI, TWITTER_ACCOUNTS
from sources_policy import WECHAT_ACCOUNTS as WECHAT_ACCOUNTS_POLICY
from process.feishu_bitable import write_items_to_bitable

FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")



def fetch_rss(source: dict, since: datetime) -> tuple[list[dict], int]:
    items = []
    raw = 0
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            pub = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub = datetime(*entry.updated_parsed[:6])

            if pub and pub < since:
                continue

            title = getattr(entry, "title", "")
            link  = getattr(entry, "link", "")
            raw += 1

            if hasattr(entry, "content") and entry.content:
                raw_summary = entry.content[0].get("value", "")
            else:
                raw_summary = getattr(entry, "summary", "")

            try:
                from bs4 import BeautifulSoup as _BS
                summary = _BS(raw_summary, "html.parser").get_text(" ", strip=True)
            except Exception:
                summary = raw_summary

            items.append({
                "title":       title,
                "url":         link,
                "summary":     summary,
                "source":      source["name"],
                "category_hardcode":    source["category"],
                "pub_time":    pub.strftime("%m-%d %H:%M") if pub else "",
                "source_type": "rss",
            })
    except Exception as e:
        log.warning(f"RSS抓取失败 {source['name']}: {e}")
    return items, raw


def _extract_nearby_time(tag) -> Optional[datetime]:
    import re

    DATE_PATTERNS = [
        (r"\b(\d{4}-\d{2}-\d{2})\b",                "%Y-%m-%d"),
        (r"\b([A-Z][a-z]+ \d{1,2},\s+\d{4})\b",     "%B %d, %Y"),
        (r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b", "%b %d, %Y"),
        (r"\b([A-Z][a-z]{2}\d{1,2},\s+\d{4})\b",     "%b%d, %Y"),
    ]

    def _try_parse(text):
        for pat, fmt in DATE_PATTERNS:
            m = re.search(pat, text)
            if m:
                try:
                    return datetime.strptime(m.group(1), fmt)
                except Exception:
                    pass
        return None

    # 1. 向上找 <time datetime="...">
    node = tag.parent
    for _ in range(6):
        if node is None:
            break
        t = node.find("time")
        if t and t.get("datetime"):
            try:
                return datetime.fromisoformat(t["datetime"][:19])
            except Exception:
                pass
        node = node.parent

    # 2. 向上找包含日期文本的祖先（含兄弟节点的文本）
    node = tag.parent
    for _ in range(6):
        if node is None:
            break
        result = _try_parse(node.get_text(" ", strip=True))
        if result:
            return result
        node = node.parent

    # 3. 找兄弟节点中的日期文本
    for sibling in tag.parent.children if tag.parent else []:
        if sibling is tag:
            continue
        text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        result = _try_parse(text)
        if result:
            return result

    return None


def fetch_webpage(source: dict, since: Optional[datetime] = None) -> tuple[list[dict], int]:
    items = []
    raw = 0
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
        resp = requests.get(source["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        NAV_KEYWORDS = {"pricing", "login", "signup", "sign-up", "register", "contact",
                        "about", "careers", "terms", "privacy", "faq", "help", "home",
                        "features", "api", "docs", "explore", "tag", "category"}
        seen_hrefs = set()
        for a in soup.find_all("a", href=True)[:200]:
            title = a.get_text(strip=True)
            href  = a["href"]
            if not href.startswith("http"):
                href = urljoin(source["url"], href)
            if len(title) <= 15:
                continue
            href_lower = href.lower()
            if any(kw in href_lower for kw in NAV_KEYWORDS):
                continue
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            raw += 1

            pub_time = _extract_nearby_time(a)
            if not pub_time:
                continue
            if since and pub_time < since:
                continue

            body = ""
            try:
                article_resp = requests.get(href, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                article_soup = BeautifulSoup(article_resp.text, "html.parser")
                for tag in article_soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                body = article_soup.get_text(" ", strip=True)
            except Exception:
                pass

            items.append({
                "title":       title,
                "url":         href,
                "summary":     body,
                "source":      source["name"],
                "category":    source["category"],
                "pub_time":    pub_time.strftime("%m-%d %H:%M"),
                "source_type": "webpage",
            })
    except Exception as e:
        log.warning(f"网页抓取失败 {source['name']}: {e}")
    return items, raw


def _wechat_cookie() -> dict:
    return {
        "wxuin":       os.environ.get("WECHAT_WXUIN", ""),
        "uuid":        os.environ.get("WECHAT_UUID", ""),
        "bizuin":      os.environ.get("WECHAT_BIZUIN", ""),
        "cert":        os.environ.get("WECHAT_CERT", ""),
        "data_ticket": os.environ.get("WECHAT_DATA_TICKET", ""),
        "slave_sid":   os.environ.get("WECHAT_SLAVE_SID", ""),
        "slave_user":  "gh_33df2c086412",
    }


def fetch_wechat(accounts: list[dict], since: datetime) -> list[dict]:
    token = os.environ.get("WECHAT_TOKEN", "")
    if not token:
        log.warning("WECHAT_TOKEN 未配置，跳过微信抓取")
        return []

    cookies = _wechat_cookie()
    items = []

    for acct in accounts:
        biz = acct.get("biz", "")
        if not biz:
            continue
        try:
            resp = requests.get(
                "https://mp.weixin.qq.com/cgi-bin/appmsgpublish",
                params={
                    "sub": "list", "search_field": "null", "begin": 0, "count": 10,
                    "query": "", "fakeid": biz, "type": "101_1",
                    "free_publish_type": 1, "sub_action": "list_ex",
                    "token": token, "lang": "zh_CN", "f": "json", "ajax": 1,
                },
                cookies=cookies,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
                    "x-requested-with": "XMLHttpRequest",
                },
                timeout=10,
            )
            data = resp.json()

            if data.get("base_resp", {}).get("ret") != 0:
                log.warning(f"微信凭证失效 [{acct['name']}]: {data.get('base_resp')}")
                send_text_to_feishu(f"[微信采集] 凭证已过期，请更新 .env 中的 WECHAT_* 字段")
                break

            publish_page = json.loads(data.get("publish_page", "{}"))
            for pub in publish_page.get("publish_list", []):
                info = json.loads(pub.get("publish_info", "{}"))
                sent_time = info.get("sent_info", {}).get("time", 0)
                pub_dt = datetime.fromtimestamp(sent_time)
                if pub_dt < since:
                    continue
                for msg in info.get("appmsgex", []):
                    title = msg.get("title", "")
                    url   = msg.get("link", "")
                    if not title:
                        continue
                    items.append({
                        "title":       title,
                        "url":         url,
                        "summary":     "",
                        "source":      acct["name"],
                        "category":    acct.get("category", "wechat"),
                        "pub_time":    pub_dt.strftime("%m-%d %H:%M"),
                        "source_type": "wechat",
                    })
            time.sleep(0.5)
        except Exception as e:
            log.warning(f"微信抓取失败 [{acct['name']}]: {e}")

    return items


def fetch_twitter(since: datetime) -> list[dict]:
    bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if not bearer:
        log.warning("TWITTER_BEARER_TOKEN 未配置，跳过 Twitter 抓取")
        return []

    headers = {"Authorization": f"Bearer {bearer}"}
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    items = []

    for username, meta in TWITTER_ACCOUNTS.items():
        display_name = meta["name"]
        category = meta["category"]
        try:
            resp = requests.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                headers=headers, timeout=10,
            )
            user_id = resp.json()["data"]["id"]

            resp = requests.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                headers=headers,
                params={
                    "start_time": since_str,
                    "max_results": 10,
                    "tweet.fields": "created_at,text",
                    "exclude": "retweets,replies",
                },
                timeout=10,
            )
            tweets = resp.json().get("data", [])
            for tweet in tweets:
                clean_text = re.sub(r'https://t\.co/\S+', '', tweet["text"]).strip()
                url = f"https://x.com/{username}/status/{tweet['id']}"
                items.append({
                    "title":       clean_text[:100],
                    "url":         url,
                    "summary":     clean_text,
                    "source":      display_name,
                    "category_hardcode":    category,
                    "pub_time":    tweet.get("created_at", "")[:16].replace("T", " "),
                    "source_type": "twitter",
                })
            time.sleep(1)
        except Exception as e:
            log.warning(f"Twitter抓取失败 {username}: {e}")

    return items


def collect_all() -> list[dict]:
    since_utc   = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    since_local = datetime.now()    - timedelta(hours=LOOKBACK_HOURS)
    all_items = []

    log.info("开始抓取RSS源...")
    for src in RSS_SOURCES:
        fetched, _ = fetch_rss(src, since_utc)
        all_items.extend(fetched)
        log.info(f"  {src['name']}: {len(fetched)}条")
        time.sleep(0.5)

    log.info("开始抓取博客页面...")
    for src in SCRAPE_SOURCES:
        fetched, _ = fetch_webpage(src, since=since_local)
        all_items.extend(fetched)
        log.info(f"  {src['name']}: {len(fetched)}条")
        time.sleep(0.5)

    log.info("开始抓取微信公众号...")
    all_wechat = WECHAT_ACCOUNTS_AI
    wechat_items = fetch_wechat(all_wechat, since_local)
    all_items.extend(wechat_items)
    log.info(f"  微信公众号: {len(wechat_items)}条")

    log.info("开始抓取 Twitter...")
    twitter_items = fetch_twitter(since_utc)
    all_items.extend(twitter_items)
    log.info(f"  Twitter: {len(twitter_items)}条")

    log.info(f"共采集到 {len(all_items)} 条")
    return all_items


def send_text_to_feishu(text: str) -> bool:
    if not FEISHU_WEBHOOK:
        return False
    payload = {"msg_type": "text", "content": {"text": text}}
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        return resp.json().get("code") == 0
    except Exception:
        return False


def run():
    log.info("=" * 50)
    log.info(f"采集模式启动 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    items = collect_all()
    if not items:
        log.info("没有新内容")
        send_text_to_feishu(f"[AI采集] {datetime.now().strftime('%Y-%m-%d %H:%M')} 完成，无新内容")
        return
    write_items_to_bitable(items)
    log.info("采集完成")
    send_text_to_feishu(f"[AI采集] {datetime.now().strftime('%Y-%m-%d %H:%M')} 完成，共采集 {len(items)} 条")


if __name__ == "__main__":
    run()
