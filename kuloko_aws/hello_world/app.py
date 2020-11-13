import json
import boto3
import os
import sys
import logging
import logging.config

import decimal


def lambda_handler(event, context):
    try:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        session = boto3.session.Session()
        table = boto3.resource('dynamodb', endpoint_url = "http://dynamodb:8000").Table('Quote')
        json_item = '{"feed_datetime":"20201001125959101", "sym":"BTC", "ask1":100.5, "ask1_size":2.0}'
        item = json.loads(json_item, parse_float=decimal.Decimal)
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

