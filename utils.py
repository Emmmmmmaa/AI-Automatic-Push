"""
Stock data fetching and Feishu table building.
"""

import logging
log = logging.getLogger(__name__)

STOCK_WATCHLIST = [
    {"name": "Google", "ticker": "GOOGL", "currency": "USD"},
    {"name": "Meta",   "ticker": "META",  "currency": "USD"},
    {"name": "NVIDIA", "ticker": "NVDA",  "currency": "USD"},
    {"name": "MSFT",   "ticker": "MSFT",  "currency": "USD"},
    {"name": "Adobe",  "ticker": "ADBE",  "currency": "USD"},
    # Figma: not publicly listed
]


def _fmt_num(v, currency: str) -> str:
    if v is None:
        return "—"
    if currency == "USD":
        if abs(v) >= 1e12:
            return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:
            return f"${v/1e9:.1f}B"
        return f"${v/1e6:.0f}M"
    else:
        if abs(v) >= 1e8:
            return f"HK${v/1e8:.0f}亿"
        return f"HK${v/1e6:.0f}M"


def _pct(v) -> str:
    if v is None:
        return "—"
    return f"{v*100:.1f}%"


def _ratio(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}x"


def _arrow(v) -> str:
    if v is None:
        return "—"
    sign = "▲" if v >= 0 else "▼"
    return f"{sign} {abs(v)*100:.1f}%"


def fetch_stock_data() -> list[dict]:
    try:
        import yfinance as yf
    except ImportError:
        log.warning("yfinance not installed, skipping stock data")
        return []

    rows = []
    for s in STOCK_WATCHLIST:
        try:
            ticker   = yf.Ticker(s["ticker"])
            info     = ticker.info
            fin      = ticker.financials
            cf       = ticker.cashflow
            currency = info.get("currency", s["currency"])

            # ── Price & market ───────────────────────────────
            price   = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev    = info.get("previousClose") or price
            chg_pct = (price - prev) / prev if prev else 0
            mktcap  = info.get("marketCap")
            ev      = info.get("enterpriseValue")

            # ── TTM valuation multiples ──────────────────────
            pe_ttm    = info.get("trailingPE")
            ev_rev_ttm  = info.get("enterpriseToRevenue")
            ev_ebitda_ttm = info.get("enterpriseToEbitda")

            # ── Forward valuation multiples (2026E) ──────────
            pe_fwd = info.get("forwardPE")
            fwd_rev_est  = None
            fwd_ni_est   = None
            try:
                rev_est  = ticker.revenue_estimate
                earn_est = ticker.earnings_estimate
                # Use current fiscal year ("0y") as 2026E proxy
                row_key = "0y" if "0y" in rev_est.index else "+1y"
                fwd_rev_est = rev_est.loc[row_key, "avg"]
                shares = info.get("sharesOutstanding")
                eps_fwd = earn_est.loc[row_key, "avg"]
                if shares and eps_fwd:
                    fwd_ni_est = eps_fwd * shares
            except Exception:
                pass

            # Forward EV/Revenue and EV/EBITDA (using current EV / fwd estimates)
            ev_rev_fwd    = (ev / fwd_rev_est)  if ev and fwd_rev_est  else None
            # EBITDA estimate not directly available; leave as —
            ev_ebitda_fwd = None

            # ── Income statement (latest fiscal year) ────────
            def _fin(row):
                try:
                    cols = list(fin.columns)
                    return fin.loc[row, cols[0]], fin.loc[row, cols[1]]
                except Exception:
                    return None, None

            rev_cur,  rev_prev = _fin("Total Revenue")
            ni_cur,   ni_prev  = _fin("Net Income")
            gp_cur,   _        = _fin("Gross Profit")
            rnd_cur,  _        = _fin("Research And Development")

            rev_yoy      = (rev_cur - rev_prev) / abs(rev_prev) if rev_cur and rev_prev else None
            ni_yoy       = (ni_cur  - ni_prev)  / abs(ni_prev)  if ni_cur  and ni_prev  else None
            gross_margin = gp_cur  / rev_cur if gp_cur  and rev_cur else None
            net_margin   = ni_cur  / rev_cur if ni_cur  and rev_cur else None
            rnd_pct      = rnd_cur / rev_cur if rnd_cur and rev_cur else None

            # ── Cash flow ────────────────────────────────────
            def _cf(row):
                try:
                    cols = list(cf.columns)
                    return cf.loc[row, cols[0]]
                except Exception:
                    return None

            op_cf = _cf("Operating Cash Flow")
            capex = _cf("Capital Expenditure")
            op_cf_pct  = op_cf          / rev_cur if op_cf and rev_cur else None
            capex_pct  = abs(capex)     / rev_cur if capex and rev_cur else None

            # ── Return metrics ───────────────────────────────
            roe = info.get("returnOnEquity")
            roa = info.get("returnOnAssets")

            rows.append({
                "name":           s["name"],
                "ticker":         s["ticker"],
                "currency":       currency,
                # Price
                "price":          f"{price:,.2f}",
                "chg_pct":        chg_pct,
                "chg_str":        f"{'▲' if chg_pct>=0 else '▼'} {abs(chg_pct)*100:.2f}%",
                "chg_up":         chg_pct >= 0,
                "mktcap":         _fmt_num(mktcap, currency),
                # Valuation TTM
                "pe_ttm":         _ratio(pe_ttm),
                "ev_rev_ttm":     _ratio(ev_rev_ttm),
                "ev_ebitda_ttm":  _ratio(ev_ebitda_ttm),
                # Valuation 2026E
                "pe_fwd":         _ratio(pe_fwd),
                "ev_rev_fwd":     _ratio(ev_rev_fwd),
                "ev_ebitda_fwd":  _ratio(ev_ebitda_fwd),  # — for now
                # Financials
                "revenue":        _fmt_num(rev_cur, currency),
                "rev_yoy":        _arrow(rev_yoy),
                "net_income":     _fmt_num(ni_cur, currency),
                "ni_yoy":         _arrow(ni_yoy),
                "gross_margin":   _pct(gross_margin),
                "net_margin":     _pct(net_margin),
                "rnd_pct":        _pct(rnd_pct),
                "capex_pct":      _pct(capex_pct),
                "roe":            _pct(roe),
                "roa":            _pct(roa),
                "op_cf_rev":      _pct(op_cf_pct),
                # Guidance (analyst estimates)
                "fwd_rev":        _fmt_num(fwd_rev_est, currency),
                "fwd_ni":         _fmt_num(fwd_ni_est, currency),
            })
        except Exception as e:
            log.warning(f"Stock fetch failed {s['ticker']}: {e}")

    return rows


# ── Table A: Valuation ───────────────────────────────────────
TABLE_A_COLS = [
    ("name",          "公司"),
    ("price",         "股价"),
    ("chg_str",       "涨跌幅"),
    ("mktcap",        "市值"),
    ("pe_ttm",        "PE (TTM)"),
    ("pe_fwd",        "PE (2026E)"),
    ("ev_rev_ttm",    "EV/Rev (TTM)"),
    ("ev_rev_fwd",    "EV/Rev (2026E)"),
    ("ev_ebitda_ttm", "EV/EBITDA (TTM)"),
    ("ev_ebitda_fwd", "EV/EBITDA (2026E)"),
]

# ── Table B: Financials ──────────────────────────────────────
TABLE_B_COLS = [
    ("name",         "公司"),
    ("revenue",      "收入 (LTM)"),
    ("rev_yoy",      "收入同比"),
    ("net_income",   "净利润 (LTM)"),
    ("ni_yoy",       "净利同比"),
    ("gross_margin", "毛利率"),
    ("net_margin",   "净利率"),
    ("rnd_pct",      "R&D占比"),
    ("capex_pct",    "CAPEX/Rev"),
    ("roe",          "ROE"),
    ("roa",          "ROA"),
    ("op_cf_rev",    "经营现金流/Rev"),
    ("fwd_rev",      "指引收入 (2026E)"),
    ("fwd_ni",       "指引净利 (2026E)"),
]


def build_stock_elements(rows: list[dict]) -> list[dict]:
    if not rows:
        return []

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": "**📈 二级市场行情**"}},
        {"tag": "hr"},
        {"tag": "div", "text": {"tag": "lark_md", "content": "*估值*"}},
    ]
    for r in rows:
        valuation = "  |  ".join(
            f"{disp}: {r.get(key, '—')}" for key, disp in TABLE_A_COLS if key != "name"
        )
        fundamentals = "  |  ".join(
            f"{disp}: {r.get(key, '—')}" for key, disp in TABLE_B_COLS if key != "name"
        )
        elements.append({"tag": "div", "text": {"tag": "lark_md",
            "content": f"**{r['name']} ({r['ticker']})**\n{valuation}\n{fundamentals}"}})
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": " "}})
    return elements
