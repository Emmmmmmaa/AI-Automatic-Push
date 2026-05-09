"""
bot/bot_server.py — 飞书机器人长连接服务。

菜单事件:
  subscribe_news    → 写入 news 订阅表
  subscribe_market  → 写入 market 订阅表
  unsubscribe_news  → 删除 news 订阅记录
  unsubscribe_market → 删除 market 订阅记录
  preview_news      → 发送缓存的 news 卡片
  preview_market    → 发送缓存的 market 卡片

启动: python bot/bot_server.py
"""

import os, sys, json, logging, threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

import lark_oapi as lark
from lark_oapi.api.application.v6 import P2ApplicationBotMenuV6

from process.subscriber import subscribe, unsubscribe
from process.feishu_bitable import get_tenant_token
from bot.push_daily import send_card, load_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

client = lark.Client.builder() \
    .app_id(os.environ["FEISHU_APP_ID"]) \
    .app_secret(os.environ["FEISHU_APP_SECRET"]) \
    .build()


def _send_text(open_id: str, text: str) -> None:
    from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("text")
            .content(json.dumps({"text": text}))
            .build()
        )
        .build()
    )
    resp = client.im.v1.message.create(req)
    if not resp.success():
        log.error(f"发送失败 open_id={open_id}: {resp.code} {resp.msg}")


def _handle_bot_menu(data: P2ApplicationBotMenuV6) -> None:
    open_id   = data.event.operator.operator_id.open_id
    event_key = data.event.event_key
    log.info(f"菜单点击 open_id={open_id} event_key={event_key}")

    def _do():
        if event_key == "subscribe_news":
            subscribe(open_id, "news")
            _send_text(open_id, "✅ 已订阅 AI 资讯，每天北京时间 9 点推送。")
        elif event_key == "subscribe_market":
            subscribe(open_id, "market")
            _send_text(open_id, "✅ 已订阅市场行情，每天北京时间 9 点推送。")
        elif event_key == "unsubscribe_news":
            unsubscribe(open_id, "news")
            _send_text(open_id, "已取消订阅 AI 资讯。")
        elif event_key == "unsubscribe_market":
            unsubscribe(open_id, "market")
            _send_text(open_id, "已取消订阅市场行情。")
        elif event_key == "preview_news":
            payload = load_cache("news")
            if payload:
                send_card(get_tenant_token(), open_id, payload)
            else:
                _send_text(open_id, "暂无缓存，请等待每天北京时间 9 点推送后再预览。")
        elif event_key == "preview_market":
            payload = load_cache("market")
            if payload:
                send_card(get_tenant_token(), open_id, payload)
            else:
                _send_text(open_id, "暂无缓存，请等待每天北京时间 9 点推送后再预览。")
        else:
            log.warning(f"未知 event_key: {event_key}")

    threading.Thread(target=_do, daemon=True).start()


event_handler = (
    lark.EventDispatcherHandler.builder("", "")
    .register_p2_application_bot_menu_v6(_handle_bot_menu)
    .build()
)

ws_client = lark.ws.Client(
    os.environ["FEISHU_APP_ID"],
    os.environ["FEISHU_APP_SECRET"],
    event_handler=event_handler,
    log_level=lark.LogLevel.INFO,
)

if __name__ == "__main__":
    log.info("Bot 启动，等待消息...")
    ws_client.start()
