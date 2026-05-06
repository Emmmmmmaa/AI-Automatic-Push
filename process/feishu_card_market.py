"""
process/market.py — Read market data from Feishu Bitable and build card payload variables.

Produces two template variables:
  - stock_table : list of stock rows (for the stock watchlist table)
  - index_table : list of index rows
  - stock_news  : list of {company, summary, url} from tblMxxmozvfSDPxs / vewYXGfIQf
"""
APP_TOKEN        = "ZaJGbWgnkaTzchsPwp2clTTlnKb"
TABLE_STOCK      = "tblCykxhEyIGJwPR"
VIEW_STOCK       = "vewbx0MpG2"
TABLE_INDEX      = "tblWCwECJS7NZEoX"
VIEW_INDEX       = "vew9Fs23Qz"
TABLE_STOCK_NEWS = "tblMxxmozvfSDPxs"
VIEW_STOCK_NEWS  =  "vewYXGfIQf"
TABLE_IR_NEWS    = "tblxhkrbR94hOL1G"
VIEW_IR_NEWS     = "vewYLcsaHg"

TEMPLATE_ID      = "AAqeo3Mrc2HZ2"
TEMPLATE_VERSION = "1.0.5"


import os
import requests
from pathlib import Path
try:
    from process.read_bitable import wrap_card_payload
except ModuleNotFoundError:
    from read_bitable import wrap_card_payload

# Load .env
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# def _change_color(val) -> str:
#     if val is None:
#         return "grey"
#     try:
#         v = float(val)
#     except (TypeError, ValueError):
#         return "grey"
#     if v > 0:
#         return "green"
#     if v < 0:
#         return "red"
#     return "grey"


def _get_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": os.environ["FEISHU_APP_ID"], "app_secret": os.environ["FEISHU_APP_SECRET"]},
        timeout=10,
    )
    data = resp.json()
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"Failed to get token: {data}")
    return token


def _read_records(token: str, table_id: str, view_id: str = None) -> list[dict]:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    records = []
    page_token = None

    while True:
        params = {"page_size": 100}
        if view_id:
            params["view_id"] = view_id
        if page_token:
            params["page_token"] = page_token

        resp = requests.get(url, headers=headers, params=params, timeout=15)
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"API error: {data}")

        items = data.get("data", {}).get("items", [])
        records.extend(items)

        if not data.get("data", {}).get("has_more") or not data.get("data", {}).get("page_token"):
            break
        page_token = data["data"]["page_token"]

    return records


def _fmt_pct(val) -> str:
    if val is None:
        return ""
    try:
        return f"{float(val)*100:+.1f}%"
    except (TypeError, ValueError):
        return str(val)


def _fmt_2dp(val) -> str:
    if val is None:
        return ""
    try:
        return f"{float(val):.2f}"
    except (TypeError, ValueError):
        return str(val)


# HKD -> USD rate (approximate)
_HKD_TO_USD = 1 / 7.8

def _fmt_money(val) -> str:
    """Normalize market cap / revenue to USD B/T.

    Accepts:
      - numeric (already in USD)
      - "$4.71T" / "$402.8B"  → pass through after re-formatting
      - "HK$2454亿" / "HK$39亿" → convert HKD 亿 to USD
    """
    if val is None:
        return ""
    if isinstance(val, str):
        import re
        val = val.strip()
        # already USD formatted: "$4.71T", "$402.8B", "$79M"
        m = re.match(r'^\$([0-9.]+)([TBM])$', val)
        if m:
            n, unit = float(m.group(1)), m.group(2)
            usd = n * {"T": 1e12, "B": 1e9, "M": 1e6}[unit]
            if usd >= 1e12:
                return f"${usd/1e12:.2f}T"
            if usd >= 1e9:
                return f"${usd/1e9:.2f}B"
            return f"${usd/1e6:.2f}M"
        # HKD 亿: "HK$2454亿", "HK$79M"
        m2 = re.match(r'^HK\$([0-9.]+)亿$', val)
        if m2:
            usd = float(m2.group(1)) * 1e8 * _HKD_TO_USD
            if usd >= 1e12:
                return f"${usd/1e12:.2f}T"
            if usd >= 1e9:
                return f"${usd/1e9:.2f}B"
            return f"${usd/1e6:.2f}M"
        m3 = re.match(r'^HK\$([0-9.]+)([TBM])$', val)
        if m3:
            n, unit = float(m3.group(1)), m3.group(2)
            usd = n * {"T": 1e12, "B": 1e9, "M": 1e6}[unit] * _HKD_TO_USD
            if usd >= 1e9:
                return f"${usd/1e9:.2f}B"
            return f"${usd/1e6:.2f}M"
        return val  # unrecognised format, pass through
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    if abs(v) >= 1e12:
        return f"${v/1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    return f"${v/1e6:.2f}M"


def _colored_pct(val) -> str:
    text = _fmt_pct(val)
    if not text:
        return ""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return text
    if v > 0:
        return f"<font color='green'>{text}</font>"
    if v < 0:
        return f"<font color='red'>{text}</font>"
    return text


def _to_md_table(headers: list[str], rows: list[list]) -> str:
    sep = "| " + " | ".join(["--------"] * len(headers)) + " |"
    header_row = "| " + " | ".join(headers) + " |"
    data_rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]
    return "\n".join([header_row, sep] + data_rows)


def build_stock_table(token: str) -> str:
    """Returns stock watchlist as a Markdown table string."""
    records = _read_records(token, TABLE_STOCK, VIEW_STOCK)
    headers = ["Company", "Price", "Change", "Mkt Cap", "P/E (TTM)", "P/E (2026E)",
               "EV/Rev (TTM)", "EV/Rev (2026E)", "Revenue (LTM)", "Rev YoY", "Gross Margin", "Net Margin"]
    rows = []
    for rec in records:
        f = rec.get("fields", {})
        rows.append([
            f.get("公司", ""),
            _fmt_2dp(f.get("股价")),
            _colored_pct(f.get("涨跌幅")),
            _fmt_money(f.get("市值")),
            _fmt_2dp(f.get("PE (TTM)")),
            _fmt_2dp(f.get("PE (2026E)")),
            _fmt_2dp(f.get("EV/Rev (TTM)")),
            _fmt_2dp(f.get("EV/Rev (2026E)")),
            _fmt_money(f.get("收入 (LTM)")),
            _colored_pct(f.get("收入同比")),
            _fmt_pct(f.get("毛利率")),
            _fmt_pct(f.get("净利率")),
        ])
    return _to_md_table(headers, rows)


def build_index_table(token: str) -> str:
    """Returns index table as a Markdown table string."""
    records = _read_records(token, TABLE_INDEX, VIEW_INDEX)
    headers = ["Name", "Ticker", "Price", "1D%", "1W%", "1M%", "YTD%"]
    rows = []
    for rec in records:
        f = rec.get("fields", {})
        rows.append([
            f.get("名称", ""),
            f.get("指数", ""),
            f.get("价格", ""),
            _colored_pct(f.get("1D%")),
            _colored_pct(f.get("1W%")),
            _colored_pct(f.get("1M%")),
            _colored_pct(f.get("YTD%")),
        ])
    return _to_md_table(headers, rows)


def build_ir_news(token: str) -> list[dict]:
    """Read tblxhkrbR94hOL1G / vewYLcsaHg. Returns all fields."""
    records = _read_records(token, TABLE_IR_NEWS, VIEW_IR_NEWS)
    seen_urls = set()
    rows = []
    for rec in records:
        f = rec.get("fields", {})
        url_field = f.get("链接", {})
        url = url_field.get("link", "") if isinstance(url_field, dict) else ""
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        rows.append({
            "company":  f.get("公司", ""),
            "title":    f.get("标题", ""),
            "type":     f.get("类型", ""),
            "summary":  f.get("总结", ""),
            "url":      url,
        })
    return rows


def build_stock_news(token: str) -> list[dict]:
    """
    Read tblMxxmozvfSDPxs / vewYXGfIQf.
    Returns list of {company, summary, url}.
    Uses summary-cn if available, else 摘要.
    """
    records = _read_records(token, TABLE_STOCK_NEWS, VIEW_STOCK_NEWS)
    seen_urls = set()
    rows = []
    for rec in records:
        f = rec.get("fields", {})
        url_field = f.get("链接", {})
        url = url_field.get("link", "") if isinstance(url_field, dict) else ""
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        rows.append({
            "company": f.get("公司", ""),
            "news_headline": f.get("news_headline_cn", ""),
            "news_headline_summary": f.get("news_headline_summary_cn", ""),
            "url":     url,
        })
    return rows


def build_market_variables(token: str = None) -> dict:
    """Return all three market variables ready for template_variable."""
    if token is None:
        token = _get_token()
    return {
        "stock_table": build_stock_table(token),
        "index_table": build_index_table(token),
        "ir_news":     build_ir_news(token),
        "stock_news":  build_stock_news(token),
    }


def build_market_card_payload(token: str = None) -> dict:
    """Return a full Feishu webhook card body for market data."""
    return wrap_card_payload(build_market_variables(token), TEMPLATE_ID, TEMPLATE_VERSION)

# def build_stock_table(token: str) -> list[dict]:
#     """All fields from VIEW_STOCK, with colored tag for change."""
#     records = _read_records(token, TABLE_STOCK, VIEW_STOCK)
#     rows = []
#     for rec in records:
#         f = rec.get("fields", {})
#         chg = f.get("涨跌幅")
#         rows.append({
#             "company":       f.get("公司", ""),
#             "price":         f.get("股价"),
#             "change":        [{"text": _fmt_pct(chg), "color": _change_color(chg)}],
#             "market_cap":    f.get("市值"),
#             "pe_ttm":        f.get("PE (TTM)"),
#             "pe_2026e":      f.get("PE (2026E)"),
#             "ev_rev_ttm":    f.get("EV/Rev (TTM)"),
#             "ev_rev_2026e":  f.get("EV/Rev (2026E)"),
#             "revenue_ltm":   f.get("收入 (LTM)"),
#             "rev_yoy":       [{"text": _fmt_pct(f.get("收入同比")), "color": _change_color(f.get("收入同比"))}],
#             "gross_margin":  _fmt_pct(f.get("毛利率")),
#             "net_margin":    _fmt_pct(f.get("净利率")),
#         })
#     return rows


# def build_index_table(token: str) -> list[dict]:
#     """All fields from VIEW_INDEX, with colored tags for change columns."""
#     records = _read_records(token, TABLE_INDEX, VIEW_INDEX)
#     rows = []
#     for rec in records:
#         f = rec.get("fields", {})
#         rows.append({
#             "name":    f.get("名称", ""),
#             "ticker":  f.get("指数", ""),
#             "price":   f.get("价格"),
#             "chg_1d":  _fmt_pct(f.get("1D%")),
#             "chg_1w":  _fmt_pct(f.get("1W%")),
#             "chg_1m":  _fmt_pct(f.get("1M%")),
#             "chg_ytd": _fmt_pct(f.get("YTD%")),
#         })
#     return rows


if __name__ == "__main__":
    import sys
    import json
    as_json = "--json" in sys.argv

    payload = build_market_card_payload()

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        webhook = os.environ.get("FEISHU_WEBHOOK", "")
        if not webhook:
            print("FEISHU_WEBHOOK not set")
        else:
            resp = requests.post(webhook, json=payload, timeout=10)
            print(f"Push result: {resp.json()}")
