import json
import boto3
import os
import sys
import logging
import logging.config
import decimal
os.environ['handler_path'] = '/Users/macico/Dropbox/kaggle/kuloko/kuloko_handler'
sys.path.append(os.environ['handler_path'])
handler_path=os.environ['handler_path'] 
logging.config.fileConfig(os.path.join(handler_path,'./ini/logconfig.ini'),defaults={'logfilename': os.path.join(handler_path,'./log/logging.log')})
logger = logging.getLogger("KULOKO")
try:
    import src.handler.api_handler as api
except Exception as e:
    logger.error(e)


def lambda_handler(event, context):
    try:

        session = boto3.session.Session()
        table = boto3.resource('dynamodb', endpoint_url = "http://dynamodb:8000").Table('Quote')

        sym = 'BTC'
        depth=5
        orderbook = api.Orderbook(sym)
        orderbook.depth =depth
        json_orderbook = orderbook.fetch(return_type='json')
        json_orderbook['sym'] = sym

        item = json.loads(str(json_orderbook), parse_float=decimal.Decimal)
        table.put_item(
            Item=item
        )
    
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'DONE!'
            }),
        }

    except Exception as e:
        logger.exception(e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error_message': str(e)
            }),
        }

