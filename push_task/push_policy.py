"""
Collect policy news from sources_policy.py and write to Feishu Bitable.
Usage: python push_policy.py
catgeory: hard-coded as "policy" for now, can be extended to more categories in the future if needed.
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
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from process.feishu_bitable import get_tenant_token
from sources_policy import RSS_SOURCES, SCRAPE_SOURCES, WECHAT_ACCOUNTS

APP_TOKEN = "ZaJGbWgnkaTzchsPwp2clTTlnKb"
TABLE_ID  = "tblW0ZKtC5yAeVFC"
LOOKBACK_HOURS = 24

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Date extraction (same logic as main.py) ──────────────────
import re

DATE_PATTERNS = [
    (r"\b(\d{4}-\d{2}-\d{2})\b",                "%Y-%m-%d"),
    (r"\b([A-Z][a-z]+ \d{1,2},\s+\d{4})\b",     "%B %d, %Y"),
    (r"\b([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})\b", "%b %d, %Y"),
    (r"\b([A-Z][a-z]{2}\d{1,2},\s+\d{4})\b",    "%b%d, %Y"),
]

def _try_parse(text):
    for pat, fmt in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            try: return datetime.strptime(m.group(1), fmt)
            except: pass
    return None

def _extract_nearby_time(tag) -> Optional[datetime]:
    node = tag.parent
    for _ in range(6):
        if node is None: break
        t = node.find("time")
        if t and t.get("datetime"):
            try: return datetime.fromisoformat(t["datetime"][:19])
            except: pass
        node = node.parent
    node = tag.parent
    for _ in range(6):
        if node is None: break
        r = _try_parse(node.get_text(" ", strip=True))
        if r: return r
        node = node.parent
    for sibling in tag.parent.children if tag.parent else []:
        if sibling is tag: continue
        text = sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)
        r = _try_parse(text)
        if r: return r
    return None


# ── Fetch ─────────────────────────────────────────────────────
def fetch_rss(source: dict, since: datetime) -> list[dict]:
    items = []
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
            if hasattr(entry, "content") and entry.content:
                raw = entry.content[0].get("value", "")
            else:
                raw = getattr(entry, "summary", "")
            try:
                summary = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
            except Exception:
                summary = raw
            items.append({
                "title":       title,
                "url":         link,
                "summary":     summary[:500],
                "source":      source["name"],
                "category":    "policy",
                "pub_time":    pub.strftime("%m-%d %H:%M") if pub else "",
                "source_type": "rss",
            })
    except Exception as e:
        log.warning(f"RSS抓取失败 {source['name']}: {e}")
    return items


NAV_KEYWORDS = {"pricing","login","signup","sign-up","register","contact",
                "about","careers","terms","privacy","faq","help","home",
                "features","api","docs","explore","tag","category"}

def fetch_webpage(source: dict, since: datetime) -> list[dict]:
    items = []
    try:
        resp = requests.get(source["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True)[:200]:
            title = a.get_text(strip=True)
            href  = a["href"]
            if not href.startswith("http"):
                href = urljoin(source["url"], href)
            if len(title) <= 15: continue
            if any(kw in href.lower() for kw in NAV_KEYWORDS): continue
            if href in seen: continue
            seen.add(href)
            pub_time = _extract_nearby_time(a)
            if not pub_time: continue
            if pub_time < since: continue
            body = ""
            try:
                ar = requests.get(href, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                as_ = BeautifulSoup(ar.text, "html.parser")
                for tag in as_(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                body = as_.get_text(" ", strip=True)
            except Exception:
                pass
            items.append({
                "title":       title,
                "url":         href,
                "summary":     body[:500],
                "source":      source["name"],
                "category":    "policy",
                "pub_time":    pub_time.strftime("%m-%d %H:%M"),
                "source_type": "webpage",
            })
    except Exception as e:
        log.warning(f"网页抓取失败 {source['name']}: {e}")
    return items


# ── Fetch WeChat ──────────────────────────────────────────────
def fetch_wechat(since: datetime) -> list[dict]:
    token = os.environ.get("WECHAT_TOKEN", "")
    if not token:
        log.warning("WECHAT_TOKEN 未配置，跳过微信抓取")
        return []

    cookies = {
        "wxuin":       os.environ.get("WECHAT_WXUIN", ""),
        "uuid":        os.environ.get("WECHAT_UUID", ""),
        "bizuin":      os.environ.get("WECHAT_BIZUIN", ""),
        "cert":        os.environ.get("WECHAT_CERT", ""),
        "data_ticket": os.environ.get("WECHAT_DATA_TICKET", ""),
        "slave_sid":   os.environ.get("WECHAT_SLAVE_SID", ""),
        "slave_user":  "gh_33df2c086412",
    }
    items = []
    feishu_webhook = os.environ.get("FEISHU_WEBHOOK", "")

    for acct in WECHAT_ACCOUNTS:
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
                if feishu_webhook:
                    requests.post(feishu_webhook, json={"msg_type": "text", "content": {"text": "[微信采集] 凭证已过期，请更新 .env 中的 WECHAT_* 字段"}}, timeout=10)
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


# ── Write to Bitable ──────────────────────────────────────────
BATCH_SIZE = 500

def _batch_insert(token: str, records: list[dict]) -> int:
    if not records:
        return 0
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_create",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"records": [{"fields": r} for r in records]},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") == 0:
        return len(records)
    log.warning(f"Bitable batch insert failed: {data}")
    return 0


def write_to_bitable(items: list[dict]):
    if not items:
        return
    token = get_tenant_token()
    year = datetime.now().year
    records = []
    for item in items:
        pub_time_ms = None
        pt = item.get("pub_time", "")
        if pt:
            try:
                dt = datetime.strptime(f"{year}-{pt}", "%Y-%m-%d %H:%M")
                pub_time_ms = int(dt.timestamp() * 1000)
            except Exception:
                pass
        records.append({
            "title":       item.get("title", ""),
            "url":         item.get("url", ""),
            "summary":     item.get("summary", "")[:500],
            "source":      item.get("source", ""),
            "category":    item.get("category", ""),
            "pub_time":    pub_time_ms,
            "source_type": item.get("source_type", ""),
            "push_time":   int(datetime.now().timestamp() * 1000),
        })

    success = 0
    for i in range(0, len(records), BATCH_SIZE):
        success += _batch_insert(token, records[i:i + BATCH_SIZE])
    log.info(f"写入完成: {success}/{len(items)}")


# ── Main ──────────────────────────────────────────────────────
def run():
    since_utc   = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)
    since_local = datetime.now()    - timedelta(hours=LOOKBACK_HOURS)
    all_items = []

    for src in RSS_SOURCES:
        items = fetch_rss(src, since_utc)
        all_items.extend(items)
        log.info(f"  RSS {src['name']}: {len(items)}条")
        time.sleep(0.5)

    for src in SCRAPE_SOURCES:
        items = fetch_webpage(src, since_local)
        all_items.extend(items)
        log.info(f"  Web {src['name']}: {len(items)}条")
        time.sleep(0.5)

    wechat_items = fetch_wechat(since_local)
    all_items.extend(wechat_items)
    log.info(f"  微信公众号: {len(wechat_items)}条")

    log.info(f"共采集 {len(all_items)} 条，开始写入...")
    write_to_bitable(all_items)


if __name__ == "__main__":
    run()
