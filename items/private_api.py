import time
from item import Item

class Margin(Item):
    def __init__(self):
        super(Margin, self).__init__(name="margin",item_type="margin",currency="BTC")
        self.margin_web_api = self.web_api.Margin(self.currency, self.logger, self.general_config_ini, self.private_api_ini)
        self.init_mongodb()
      
    def fetch(self, return_type="json"): 
        v = self.margin_web_api.fetch(return_type)
        if return_type=="json":
            self.mongo_db.insert_one(v)
        return v
    

class Assets(Item):
    def __init__(self):
        super(Assets, self).__init__(name="assets",item_type="assets",currency="BTC")
        self.assets_web_api = self.web_api.Assets(self.currency, self.logger, self.general_config_ini, self.private_api_ini)
        self.init_mongodb()
      
    def fetch(self, return_type="json"): 
        v = self.assets_web_api.fetch(return_type)
        return v
        #todo 
        # if return_type=="json":
        #     self.mongo_db.insert
        # return v
        
class Orders(Item):
    def __init__(self):
        super(Orders, self).__init__(name="orders",item_type="orders",currency="BTC")
        self.orders_web_api = self.web_api.Orders(self.currency, self.logger, self.general_config_ini, self.private_api_ini)
        self.init_mongodb()
      
    def fetch_sym(self, sym=None,  return_type="json"): 
        if sym is None:
            sym = self.currency
        v = self.orders_web_api.fetch_active(sym,return_type)
        return v
    
    def fetch_id(self, id,  return_type="json"): 
        v = self.orders_web_api.fetch_by_orderId(id,return_type)
        return v

    
        
        