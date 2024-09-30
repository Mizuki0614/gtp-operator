import os
import json
import urllib
import boto3
import logging
from datetime import datetime
# import pytz
import openai

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    execution_arn = event['detail']['executionArn']
    logger.info(event)
    logger.info(execution_arn)
    
    # OpenAI APIの認証情報をSSMパラメータストアから読み込む
    ssm = boto3.client('ssm')
    response_openai = ssm.get_parameters(Names=['OPENAI_API_KEY'], WithDecryption=True)
    openai.api_key = response_openai['Parameters'][0]['Value']
    
    if event['detail']['status'] == 'FAILED':
        # error_message = event['detail']['name'] # ステップの名前
        # print(event['detail']['error']) # エラーコード
        error_message = event['detail']['cause'] # エラーメッセージ
        # エラー発生時刻(JST)
        failed_time = datetime.strptime(event['time'], '%Y-%m-%dT%H:%M:%SZ')
        # UTC→JSTの変換は標準ライブラリではないpytzを使用するため、レイヤーの作成が必須。
        # 20230620: OpenAI APIのみレイアーで提供
        # jst_timezone = pytz.timezone('Asia/Tokyo')
        # failed_time = failed_time.replace(tzinfo=pytz.utc).astimezone(jst_timezone)
        # failed_time = failed_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # gpt-3.5-turboへの問い合わせを実施
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            n=1,
            stop=None,
            temperature=0.7,
            messages=[
                {
                    'role': 'user',
                    'content': f'あなたはオペレータです。下記エラーメッセージについて、日本語で解析を実施して原因を展開してください。\n{error_message}'
                }, 
            ]
        )
        ai_response_text = response["choices"][0]["message"]["content"]
        
        logger.info(ai_response_text)
        
        # Slack webhook URL
        slack_url = ssm.get_parameters(Names=['SLACK_WEBHOOK_URL'], WithDecryption=True)['Parameters'][0]['Value']
        logging.info(slack_url)
        
        message = {
            "attachments":[
                {
                    "fallback":"装飾を加えたSlack通知のテスト",
                     "pretext":"装飾を加えたSlack通知のテスト",
                     "color":"#D00000",
                     "fields":[
                         {
                             "title":f'ERROR：{failed_time}',
                             "value":f'実行ARN：{execution_arn}\nエラーメッセージ：{error_message[0:500]}…\nエラー文AIパース：{ai_response_text}'
                         }
                         ]
                }
                ]
        }   
        headers = {
            'Content-Type': 'application/json'
        }
        req = urllib.request.Request(slack_url, json.dumps(message).encode(), headers)
        with urllib.request.urlopen(req) as res:
            body = res.read().decode()
        return {
            'statusCode': 200,
            'body': body
        }
