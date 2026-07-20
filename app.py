from flask import Flask, request, abort
import os
import re

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


def calculate_juggler(data_text):
    lines = [
        line.strip()
        for line in data_text.split("\n")
        if line.strip()
    ]

    if not lines:
        return None

    # 1行目だけ機種名として許可
    start = 0
    if not re.match(r"^\d+\.\d+\.\d+", lines[0]):
        start = 1

    data_lines = lines[start:]

    # 3台未満なら無視
    if len(data_lines) < 3:
        return None

    total_games = 0
    total_bb = 0
    total_rb = 0

    for line in data_lines:

        # 行頭の「数字.数字.数字」だけ取得
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", line)

        # 数字で始まらない行があれば無視
        if not m:
            return None

        games = int(m.group(1))
        bb = int(m.group(2))
        rb = int(m.group(3))

        total_games += games
        total_bb += bb
        total_rb += rb

    if total_bb == 0 or total_rb == 0:
        return None

    bb_prob = round(total_games / total_bb)
    rb_prob = round(total_games / total_rb)
    total_bonus = total_bb + total_rb
    total_prob = round(total_games / total_bonus)

    result = f"""
{len(data_lines)}台
{total_games:,}G
BB 1/{bb_prob}
RB 1/{rb_prob}
合算 1/{total_prob}
"""

    return result.strip()


@app.route("/")
def health():
    return "OK"


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    print("Webhook received!")

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()

    result = calculate_juggler(text)

    # 条件に合わない場合は完全に無視
    if result is None:
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=result)
                ]
            )
        )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
