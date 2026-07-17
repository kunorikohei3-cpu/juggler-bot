from flask import Flask, request, abort
import os

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

    total_games = 0
    total_bb = 0
    total_rb = 0
    machine_count = 0

    for line in lines:
        try:
            parts = line.split(".")

            if len(parts) >= 3:
                games = int(parts[0])
                bb = int(parts[1])
                rb = int(parts[2])

                total_games += games
                total_bb += bb
                total_rb += rb
                machine_count += 1

        except:
            continue

    if total_games == 0:
        return "データ形式が違います。\n例：\n3120.11.15\n4311.12.19"

    bb_prob = round(total_games / total_bb) if total_bb > 0 else 999
    rb_prob = round(total_games / total_rb) if total_rb > 0 else 999

    total_bonus = total_bb + total_rb
    total_prob = round(total_games / total_bonus) if total_bonus > 0 else 999

    result = f"""
{machine_count}台
{total_games:,}G
BB1/{bb_prob}
RB1/{rb_prob}
合算1/{total_prob}
"""

    return result.strip()


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()

    if "." in text:
        result = calculate_juggler(text)
    else:
        result = "ジャグラーの台データを送信してください！\n（games.bb.rb の形式）"

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
