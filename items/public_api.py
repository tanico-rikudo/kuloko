import time
from datetime import datetime as dt
from item import Item

from util import daylib
from util import utils
dl = daylib.daylib()

import  copy

class venueStatus(Item):
    def __init__(self):
        super(venueStatus, self).__init__(name="venueStatus",item_type="venueStatus",currency="BTC",
                                         general_config_mode="DEFAULT",private_api_mode="DEFAULT")
        self.vStatus_web_api = self.web_api.venueStatus(self.logger,
                                                        self.general_config_ini, self.private_api_ini,
                                                        self.general_config_mode,self.private_api_mode)
        
        # Init mongo
        self.init_mongodb()
              
    def get(self):
        try:
            res = self.vStatus_web_api.fetch(return_type='json')
        except Exception as e:
            res = {"res_time":dl.currentTime(self.vStatus_web_api.tz), "status":"INQUIRY_ERROR"}
        finally:
            self.mongo_db.insert_many(res)
            self.logger.info("[DONE] API venue status inquiry: {0}".format(res['status']))
            return res
        
class Orderbook(Item):
    def __init__(self, general_config_mode, private_api_mode):
        super(Orderbook, self).__init__(name="orderbook",item_type="orderbook",currency="BTC",
                                         general_config_mode="DEFAULT",private_api_mode="DEFAULT")
        self.orderbook_skt_api = self.skt_api.Orderbooks(self.logger,
                                                         self.general_config_ini, self.private_api_ini,
                                                         self.general_config_mode,self.private_api_mode)
        self.deque_none = 0
        self.no_update_attmpt = 6 #1min. #TODO;set out side
        
        # Init mongo
        self.init_mongodb()
        
    def connect(self): 
        self.orderbook_skt_api.connect(
            self.orderbook_skt_api.get_public_socket_url(),self.currency)
        
    def subscribe(self):
        self.orderbook_skt_api.subscribe()
        
    def dequeue(self, autosave_mongo=True):
        data = self.orderbook_skt_api.get()
        if len(data)==0:
            if self.no_update_attmpt < self.deque_none:
                #NOTE: heatbeat. No heartbbeat  method 
                self.logger.warning("Reconnect Orderbook Socket due to No data")
                self.deque_none = 0
                self.orderbook_skt_api.reconnect()
            else:
                self.deque_none += 1
            return None
        # self.logger.info("Dequeued Data:{0}".format(len(data)))
        ret_json =[ self.orderbook_skt_api.convert_shape(_data,5,"json") for _data in data ]
        insert_json =  copy.deepcopy(ret_json)
        if autosave_mongo:  
            self.mongo_db.insert_many(insert_json)
        self.logger.info("Deque Orderbook:{0}".format(len(ret_json)))
        self.deque_none = 0
        return ret_json
          
    def dequeue_forever(self):
        no_update_second=60*60  #TODO: define outside
        if not self.orderbook_skt_api.is_connected():
            self.logger.error("Cannot find socket connection.")            
            return 
        self.logger.info("[START] Dequeue")
        update_time = dt.now()
        while True:
            time.sleep(1)
            lapse_seconds = (dt.now() - update_time).seconds
            if lapse_seconds > no_update_second:
                self.logger.warning("[END]Update time is too past. Last update time:{0}. Lapse={1} sec".format(update_time, lapse_seconds)) 
                break 
            self.dequeue()
            try:
                insert_json =  self.dequeue()
                update_time = dt.now()
            except Exception as e:
                self.logger.warning("Fail to deque data:{0}".format(e))
            
                    
    def disconnect(self):
        self.orderbook_skt_api.disconnect()
        
class Ticker(Item):
    def __init__(self, general_config_mode, private_api_mode):
        super(Ticker, self).__init__(name="ticker",item_type="ticker",currency="BTC",
                                     general_config_mode="DEFAULT",private_api_mode="DEFAULT")
        self.ticker_skt_api = self.skt_api.Ticker(self.logger, 
                                                  self.general_config_ini, self.private_api_ini,
                                                  self.general_config_mode,self.private_api_mode)
        self.deque_none = 0
        self.no_update_attmpt = 6*10
        
        # Init mongo
        self.init_mongodb()
      
    def connect(self): 
        self.ticker_skt_api.connect(
            self.ticker_skt_api.get_public_socket_url(),self.currency)
        
    def subscribe(self):
        self.ticker_skt_api.subscribe()
        
    def dequeue(self, autosave_mongo=True):
        data = self.ticker_skt_api.get()
        if len(data)==0:
            if self.no_update_attmpt < self.deque_none:
                self.logger.warning("Reconnect Ticker Socket due to No data")
                self.deque_none = 0
                self.ticker_skt_api.reconnect()
            else:
                self.deque_none += 1
            return None
        # self.logger.info("Dequeued Data:{0}".format(len(data)))
        ret_json =[ self.ticker_skt_api.convert_shape(_data,"json") for _data in data ]
        insert_json =  copy.deepcopy(ret_json)
        if  autosave_mongo:
            self.mongo_db.insert_many(insert_json)
            
        self.logger.info("Deque Ticker:{0}".format(len(ret_json)))
        self.deque_none = 0
        return ret_json
                
    def dequeue_forever(self):
        no_update_second=60*60  #TODO: define outside
        if not self.ticker_skt_api.is_connected():
            self.logger.error("Cannot find socket connection.")            
            return 
        self.logger.info("[START] Dequeue")
        update_time = dt.now()
        while True:
            lapse_seconds = (dt.now() - update_time).seconds
            if lapse_seconds > no_update_second:
                self.logger.warning("[END]Update time is too past. Last update time:{0}. Lapse:{1}".format(update_time, lapse_seconds)) 
                break 
            try:
                self.dequeue()
                update_time = dt.now()
            except Exception as e:
                self.logger.warning("Fail to deque data:{0}".format(e))
            
    def disconnect(self):
        self.ticker_skt_api.disconnect()
        
class Trade(Item):
    def __init__(self, general_config_mode, private_api_mode):
        super(Trade, self).__init__(name="trade",item_type="trade",currency="BTC",
                                     general_config_mode="DEFAULT",private_api_mode="DEFAULT")
        self.trade_skt_api = self.skt_api.Trade(self.logger, 
                                                self.general_config_ini, self.private_api_ini,
                                                self.general_config_mode,self.private_api_mode)
        self.deque_none = 0
        self.no_update_attmpt = 6*10
        
        # Init mongo
        self.init_mongodb()
      
    def connect(self): 
        self.trade_skt_api.connect(
            self.trade_skt_api.get_public_socket_url(),self.currency)
        
    def subscribe(self):
        self.trade_skt_api.subscribe()
        
    def dequeue(self, autosave_mongo=True):
        data = self.trade_skt_api.get()
        if len(data)==0:
            if self.no_update_attmpt < self.deque_none:
                self.logger.warning("Reconnect Trade Socket due to No data")
                self.deque_none = 0
                self.trade_skt_api.reconnect()
            else:
                self.deque_none += 1
            return None
        # self.logger.info("Dequed Tr: Data:{0}".format(len(data)))
        ret_json =[ self.trade_skt_api.convert_shape(_data,"json") for _data in data ]
        insert_json =  copy.deepcopy(ret_json)

        if autosave_mongo:
            self.mongo_db.insert_many(insert_json)
        self.logger.info("Deque Trade :{0}".format(len(ret_json)))
        self.deque_none = 0
        return ret_json
      
    def dequeue_forever(self):
        no_update_second=60*60  #TODO: define outside
        if not self.trade_skt_api.is_connected():
            self.logger.error("Cannot find socket connection.")            
            return 
        self.logger.info("[START] Dequeue")
        update_time = dt.now()
        while True:
            now = dt.now()
            lapse_seconds = (now - update_time ).seconds
            if lapse_seconds> no_update_second:
                self.logger.warning("[END]Update time is too past. Last update time:{0}. Lapse:{1}. {2}".format(update_time,lapse_seconds, dt.now())) 
                break 
            try:
                self.dequeue()
                update_time = dt.now()
            except Exception as e:
                self.logger.warning("Fail to deque data:{0}".format(e))
            
    def disconnect(self):
        self.trade_skt_api.disconnect()