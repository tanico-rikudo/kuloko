import boto3
class Dynamo:
    def __init__(self,  db='dynamodb',table=None):
        self.dynamodb = boto3.resource(db)
        self.table    = self.dynamodb.Table(table)

    def insert(self, item):
        self.table.put_item(item)