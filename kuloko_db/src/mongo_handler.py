from pymongo import MongoClient
import configparser
import logging
import logging.config

class MongoHandler:
    def __init__(self,config,db_name):
        self.host = config.get('host')
        self.clint = MongoClient(self.host)
        self.db_name = db_name
        self.db = self.clint[self.db_name]

    def insert_one(self, json):
        return self.db[self.db_name].insert_one(json)

    def insert_many(self, json_list):
        return self.db[self.db_name].insert_many(json_list)

    def delete_all(self):
        self.db[self.db_name].delete_many({})
        return 

    def find(self):
        return self.db[self.db_name].find({})
         