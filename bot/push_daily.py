"""
bot/push_daily.py — 每晚 9 点定时推送卡片给订阅者，并缓存 payload 供预览使用。

用 cron 或 launchd 每天 21:00 执行：
  python bot/push_daily.py
"""

import os, sys, json, logging, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from process.feishu_bitable import get_tenant_token
from process.subscriber import get_subscribers
from process.feishu_card_news_and_policy import build_combined_payload
from process.feishu_card_market import build_market_card_payload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CACHE_DIR  = Path(__file__).parent / "cache"
CACHE_NEWS   = CACHE_DIR / "news.json"
CACHE_MARKET = CACHE_DIR / "market.json"


def save_cache(sub_type: str, payload: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_NEWS if sub_type == "news" else CACHE_MARKET
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    log.info(f"缓存已保存: {path}")


def load_cache(sub_type: str) -> dict | None:
    path = CACHE_NEWS if sub_type == "news" else CACHE_MARKET
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def send_card(token: str, open_id: str, payload: dict) -> bool:
    content = json.dumps({
        "type": "template",
        "data": payload["card"]["data"],
    })
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"receive_id_type": "open_id"},
        json={
            "receive_id": open_id,
            "msg_type":   "interactive",
            "content":    content,
        },
        timeout=30,
    )
    ok = resp.json().get("code") == 0
    if not ok:
        log.warning(f"发送失败 open_id={open_id}: {resp.json()}")
    return ok


def run():
    token = get_tenant_token()

    # 推送 AI 资讯
    news_subscribers = get_subscribers("news")
    log.info(f"AI 资讯订阅者: {len(news_subscribers)} 人")
    news_payload = build_combined_payload(token)
    save_cache("news", news_payload)
    for open_id in news_subscribers:
        ok = send_card(token, open_id, news_payload)
        log.info(f"  news → {open_id}: {'✅' if ok else '❌'}")

    # 推送市场行情
    market_subscribers = get_subscribers("market")
    log.info(f"市场行情订阅者: {len(market_subscribers)} 人")
    market_payload = build_market_card_payload(token)
    save_cache("market", market_payload)
    for open_id in market_subscribers:
        ok = send_card(token, open_id, market_payload)
        log.info(f"  market → {open_id}: {'✅' if ok else '❌'}")

    log.info("推送完成")


if __name__ == "__main__":
    run()
