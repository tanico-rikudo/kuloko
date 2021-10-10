from item import Item
class Orderbook(Item):
    def __init__(self):
        super(Orderbook, self).__init__(name="orderbook",item_type="orderbook",currency="BTC")
        self.api = self.base_api.Orderbooks(self.logger, self.general_config_ini, self.private_api_ini)
      
    def connect(self): 
        self.api.connect(orderbooks.api.get_public_socket_url(),self.currency)
        
    def subscribe(self):
        self.api.subscribe()
        
    def dequeue(self):
        import time
        retry_cnt=0
        max_retry_cnt=60
        self.logger.info("[START] Dequeue")
        while True:
            try:
                time.sleep(10)
                data = self.api.get()
                self.logger.info("Dequeued Data:{0}, Retry_cnt={1}".format(len(data),retry_cnt))
                if len(data)==0:
                    retry_cnt += 1
                    continue
                insert_json =[ self.api.convert_shape(_data,5,"json") for _data in data ]
                self.mongo_db.insert_many(insert_json)
                retry_cnt = 0
            except Exception as e:
                retry_cnt += 1
                if retry_cnt < max_retry_cnt:
                    continue
                self.logger.info("[END]",e)
                break
            
            
            
    def disconnect(self):
        self.api.disconnect()