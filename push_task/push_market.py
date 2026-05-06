"""
push_market.py — 二级市场数据模块，每天定时推送到飞书多维表格

模块一：行业指数 (Index)
模块二：公司IR新闻 (IR_News)
模块三：个股新闻+归因 (Stock_News)
模块四：个股基本面数据 (Stock)
"""

import os
import math
import time
import logging
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

BITABLE_APP_TOKEN = "ZaJGbWgnkaTzchsPwp2clTTlnKb"

TABLE_INDEX       = "tblWCwECJS7NZEoX"
TABLE_IR_NEWS     = "tblxhkrbR94hOL1G"
TABLE_STOCK_NEWS  = "tblMxxmozvfSDPxs"


# ── 股票监控列表（与 utils.py 保持同步） ─────────────────────────────
WATCHLIST = [
    {"name": "Google",  "ticker": "GOOGL"},
    {"name": "Meta",    "ticker": "META"},
    {"name": "NVIDIA",  "ticker": "NVDA"},
    {"name": "MSFT",    "ticker": "MSFT"},
    {"name": "Adobe",   "ticker": "ADBE"},
    {"name": "MiniMax", "ticker": "0100.HK"},
    {"name": "智谱AI",  "ticker": "2513.HK"},
    {"name": "美图",    "ticker": "1357.HK"},
    {"name": "群核科技","ticker": "0068.HK"},
]

# 行业指数
INDEX_LIST = [
    {"ticker": "SPY",  "name": "S&P 500"},
    {"ticker": "QQQ",  "name": "Nasdaq 100"},
    {"ticker": "XLK",  "name": "Tech Sector"},
    {"ticker": "SOXX", "name": "Semiconductors"},
]

# IR新闻：只抓美股（港股无 SEC filings）；GOOGL 无 SEC filings，改用 GOOG
US_TICKERS = [
    {"name": s["name"], "ticker": "GOOG" if s["ticker"] == "GOOGL" else s["ticker"]}
    for s in WATCHLIST if not s["ticker"].endswith(".HK")
]

# 只关注这些 filing 类型
IR_FILING_TYPES = {"8-K", "10-Q", "10-K"}


# ── Feishu helpers ────────────────────────────────────────────────────

def _get_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": os.environ["FEISHU_APP_ID"], "app_secret": os.environ["FEISHU_APP_SECRET"]},
        timeout=10,
    )
    return resp.json()["tenant_access_token"]


def _batch_insert(token: str, table_id: str, records: list[dict]):
    if not records:
        return
    resp = requests.post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{table_id}/records/batch_create",
        headers={"Authorization": f"Bearer {token}"},
        json={"records": [{"fields": r} for r in records]},
        timeout=15,
    )
    data = resp.json()
    if data.get("code") == 0:
        log.info(f"[{table_id}] inserted {len(records)} records")
    else:
        log.warning(f"[{table_id}] insert failed: {data}")


def _num(v):
    if v is None or not isinstance(v, (int, float)):
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def _today_ms() -> int:
    now = datetime.now()
    return int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)


# ── 模块一：行业指数 ──────────────────────────────────────────────────

def fetch_index_data() -> list[dict]:
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance not installed")
        return []

    rows = []
    for idx in INDEX_LIST:
        try:
            t    = yf.Ticker(idx["ticker"])
            info = t.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("navPrice")
            prev  = info.get("previousClose") or price
            chg_1d = (price - prev) / prev if prev else None

            hist = t.history(period="1y")
            close = hist["Close"] if hist is not None and len(hist) else None

            chg_1w = chg_1m = chg_ytd = None
            if close is not None and len(close) >= 2:
                if len(close) >= 6:
                    chg_1w = (price - float(close.iloc[-6])) / float(close.iloc[-6])
                if len(close) >= 22:
                    chg_1m = (price - float(close.iloc[-22])) / float(close.iloc[-22])
                # YTD: first trading day of the year
                year_start = close[close.index.year == datetime.now().year]
                if len(year_start):
                    chg_ytd = (price - float(year_start.iloc[0])) / float(year_start.iloc[0])

            rows.append({
                "ticker": idx["ticker"],
                "name":   idx["name"],
                "price":  price,
                "chg_1d": chg_1d,
                "chg_1w": chg_1w,
                "chg_1m": chg_1m,
                "chg_ytd": chg_ytd,
            })
        except Exception as e:
            log.warning(f"Index fetch failed {idx['ticker']}: {e}")

    return rows


def push_index(token: str):
    rows = fetch_index_data()
    if not rows:
        log.info("No index data")
        return

    date_ms = _today_ms()
    records = []
    for r in rows:
        rec = {
            "日期":  date_ms,
            "指数":  r["ticker"],
            "名称":  r["name"],
            "价格":  _num(r["price"]),
            "1D%":   _num(r["chg_1d"]),
            "1W%":   _num(r["chg_1w"]),
            "1M%":   _num(r["chg_1m"]),
            "YTD%":  _num(r["chg_ytd"]),
        }
        records.append({k: v for k, v in rec.items() if v is not None})

    _batch_insert(token, TABLE_INDEX, records)
    print(f"[Index] pushed {len(records)} rows")


# ── 模块二：IR 新闻（SEC Filings） ───────────────────────────────────

def _fetch_filing_text(exhibits: dict) -> str:
    """从 exhibits CDN 链接抓取 filing 全文，优先 EX-99.1，其次主文件。"""
    from bs4 import BeautifulSoup

    priority = ["EX-99.1", "EX-99.2"] + [k for k in exhibits if k not in ("EX-99.1", "EX-99.2")]
    for key in priority:
        url = exhibits.get(key)
        if not url:
            continue
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if r.status_code != 200:
                continue
            text = BeautifulSoup(r.text, "html.parser").get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text[:8000]  # 截断避免 token 过多
        except Exception as e:
            log.debug(f"exhibit fetch failed {url}: {e}")
    return ""


def fetch_ir_news() -> list[dict]:
    try:
        import yfinance as yf
    except ImportError:
        return []

    today = datetime.now().date()
    items = []
    for s in US_TICKERS:
        try:
            filings = yf.Ticker(s["ticker"]).sec_filings or []
            for f in filings:
                if f.get("type") not in IR_FILING_TYPES:
                    continue
                filing_date = f.get("date", "")
                try:
                    if filing_date:
                        if isinstance(filing_date, str):
                            fd = datetime.strptime(filing_date, "%Y-%m-%d").date()
                        else:
                            fd = filing_date
                        if hasattr(fd, "date"):
                            fd = fd.date()
                        if fd != today:
                            continue
                except (ValueError, TypeError):
                    continue

                exhibits = f.get("exhibits") or {}
                full_text = _fetch_filing_text(exhibits) if exhibits else ""

                items.append({
                    "company":   s["name"],
                    "ticker":    s["ticker"],
                    "type":      f.get("type", ""),
                    "title":     f.get("title", ""),
                    "url":       f.get("edgarUrl", ""),
                    "date":      filing_date,
                    "full_text": full_text,
                })
        except Exception as e:
            log.warning(f"IR fetch failed {s['ticker']}: {e}")

    return items


def push_ir_news(token: str):
    items = fetch_ir_news()
    if not items:
        print("[IR_News] no new filings today")
        return

    date_ms = _today_ms()
    records = []
    for it in items:
        rec = {
            "日期":  date_ms,
            "公司":  f"{it['company']} ({it['ticker']})",
            "类型":  it["type"],
            "标题":  it["title"],
        }
        if it.get("url"):
            rec["链接"] = {"link": it["url"], "text": it["url"]}
        if it.get("full_text"):
            rec["全文"] = it["full_text"]
        records.append(rec)

    _batch_insert(token, TABLE_IR_NEWS, records)
    print(f"[IR_News] pushed {len(records)} filings")


# ── 模块三：个股新闻 + 分析师评级动作 ────────────────────────────────

# def fetch_ticker_headline(ticker: str) -> str:
#     """Scrape the 'News headlines' AI summary from finance.yahoo.com/quote/{ticker}/"""
#     url = f"https://finance.yahoo.com/quote/{ticker}/"
#     try:
#         from bs4 import BeautifulSoup
#         resp = requests.get(url, timeout=10, headers={
#             "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
#         })
#         soup = BeautifulSoup(resp.text, "html.parser")
#         h2 = soup.find("h2", class_=lambda c: c and "yf-1jwogtj" in c)
#         if h2:
#             title_attr = h2.get("title", "")
#             return title_attr.replace("News headlines", "", 1).strip()
#     except Exception as e:
#         log.debug(f"Headline fetch failed {ticker}: {e}")
#     return ""


def fetch_ticker_headline(ticker: str) -> str:
    """Scrape the expanded AI summary from Yahoo Finance by clicking 'View more' via Playwright."""
    import asyncio
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup

    async def _fetch():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ))
            try:
                await page.goto(
                    f"https://finance.yahoo.com/quote/{ticker}/",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await asyncio.sleep(10)
                btn = page.locator("button.ai-analyst-sheet-trigger-button")
                if await btn.count() == 0:
                    return ""
                await btn.click()
                await asyncio.sleep(10)
                html = await page.content()
            finally:
                await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        div = soup.find("div", class_=lambda c: c and "yf-ouyd5p" in c)
        if not div:
            return ""

        for tag in div.find_all("div", class_=lambda c: c and "sources-accordion" in " ".join(c)):
            tag.decompose()

        content_div = div.find("div", class_=lambda c: c and "animated-markdown-renderer" in " ".join(c))
        target = content_div if content_div else div
        return target.get_text(separator=" ", strip=True)

    try:
        return asyncio.run(_fetch())
    except Exception as e:
        log.debug(f"Headline fetch failed {ticker}: {e}")
    return ""


def fetch_stock_news() -> list[dict]:
    items = []
    for s in WATCHLIST:
        if s["ticker"].endswith(".HK"):
            continue
        headline = fetch_ticker_headline(s["ticker"])
        if headline:
            items.append({
                "company": s["name"],
                "ticker":  s["ticker"],
                "title":   f"[News Summary] {s['name']}",
                "summary": headline,
                "source":  "Yahoo Finance",
                "url":     f"https://finance.yahoo.com/quote/{s['ticker']}/",
                "type":    "headline",
            })
    return items


def push_stock_news(token: str):
    items = fetch_stock_news()
    if not items:
        print("[Stock_News] no news today")
        return

    date_ms = _today_ms()
    records = []
    for it in items:
        rec = {
            "日期":  date_ms,
            "公司":  f"{it['company']} ({it['ticker']})",
            "标题":  it["title"],
            "新闻总结":  it["summary"],
            "来源":  it["source"],
            "类型":  it["type"],
        }
        if it.get("url"):
            rec["链接"] = {"link": it["url"], "text": it["url"]}
        records.append(rec)

    _batch_insert(token, TABLE_STOCK_NEWS, records)
    print(f"[Stock_News] pushed {len(records)} items")


# ── 模块四：个股基本面数据 ────────────────────────────────────────────

TABLE_STOCK = "tblCykxhEyIGJwPR"

def push_stock(token: str):
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from utils import fetch_stock_data
    rows = fetch_stock_data()
    if not rows:
        print("[Stock] no data fetched")
        return

    date_ms = _today_ms()
    records = []
    for r in rows:
        rec = {
            "日期":           date_ms,
            "公司":           f"{r['name']} ({r['ticker']})",
            "股价":           _num(r["price_raw"]),
            "涨跌幅":         _num(r["chg_pct"]),
            "市值":           r["mktcap"],
            "PE (TTM)":       _num(r["pe_ttm_raw"]),
            "PE (2026E)":     _num(r["pe_fwd_raw"]),
            "EV/Rev (TTM)":   _num(r["ev_rev_ttm_raw"]),
            "EV/Rev (2026E)": _num(r["ev_rev_fwd_raw"]),
            "收入 (LTM)":     r["revenue"],
            "收入同比":       _num(r["rev_yoy_raw"]),
            "毛利率":         _num(r["gross_margin_raw"]),
            "净利率":         _num(r["net_margin_raw"]),
        }
        records.append({k: v for k, v in rec.items() if v is not None})

    _batch_insert(token, TABLE_STOCK, records)
    print(f"[Stock] pushed {len(records)} rows")


# ── 入口 ─────────────────────────────────────────────────────────────

def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = _get_token()

    push_index(token)
    time.sleep(0.5)
    push_ir_news(token)
    time.sleep(0.5)
    push_stock_news(token)
    time.sleep(0.5)
    push_stock(token)


if __name__ == "__main__":
    run()
