import time
from item import Item

class Orderbook(Item):
    def __init__(self):
        super(Orderbook, self).__init__(name="orderbook",item_type="orderbook",currency="BTC")
        self.orderbook_skt_api = self.skt_api.Orderbooks(self.logger, self.general_config_ini, self.private_api_ini)
        
        # Init mongo
        self.init_mongodb()
      
    def connect(self): 
        self.orderbook_skt_api.connect(
            self.orderbook_skt_api.get_public_socket_url(),self.currency)
        
    def subscribe(self):
        self.orderbook_skt_api.subscribe()
        
    def dequeue(self):
        retry_cnt=0
        max_retry_cnt=60
        if not self.orderbook_skt_api.is_connected():
            self.logger.error("Cannot find socket connection.")            
            return 
        self.logger.info("[START] Dequeue")
        
        while True:
            if retry_cnt > max_retry_cnt:
                self.logger.warning("[END]Retry cnt is over maximum") 
                break 
            try:
                time.sleep(10)
                data = self.orderbook_skt_api.get()
                self.logger.info("Dequeued Data:{0}, Retry_cnt={1}".format(len(data),retry_cnt))
                if len(data)==0:
                    retry_cnt += 1
                    continue
                insert_json =[ self.orderbook_skt_api.convert_shape(_data,5,"json") for _data in data ]
                self.mongo_db.insert_many(insert_json)
                retry_cnt = 0
            except Exception as e:
                retry_cnt += 1
                self.logger.warning("Fail to deque data:{0}".format(e))
            
            
            
    def disconnect(self):
        self.orderbook_skt_api.disconnect()