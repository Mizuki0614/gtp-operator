import os
import logging
from linebot import LineBotApi, WebhookParser
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import boto3

ssm = boto3.client('ssm')

# LINE Messaging APIのチャンネルアクセストークンをSSMパラメータストアから読み込む
response_line = ssm.get_parameters(Names=['LINE_CHANNEL_ACCESS_TOKEN'], WithDecryption=True)
line_bot_api = LineBotApi(response_line['Parameters'][0]['Value'])

# OpenAI APIの認証情報をSSMパラメータストアから読み込む
response_openai = ssm.get_parameters(Names=['OPENAI_API_KEY'], WithDecryption=True)
openai.api_key = response_openai['Parameters'][0]['Value']

# Lambda関数のエントリーポイント
def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # LINE Messaging APIから送信されたメッセージを取得
    try:
        if event['events'][0]['message']['type'] == 'text':
            reply_token = event['events'][0]['replyToken']
            user_message = event['events'][0]['message']['text']
    except KeyError as e:
        logger.error(f"Failed to parse event: {e}")
        return {"statusCode": 400, "body": "Bad Request"}

    # GPT-3.5-Turboを使用して回答を生成
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        n=1,
        stop=None,
        temperature=0.7,
        messages=[
            {"role": "user", "content": user_message}, 
        ]
    )
    bot_response_text = response["choices"][0]["message"]["content"]

    # LINE Messaging APIを使用して回答を返信
    line_bot_api.reply_message(
        reply_token, TextSendMessage(text=bot_response_text)
    )