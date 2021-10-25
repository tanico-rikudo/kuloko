import time
from item import Item
import json
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

class Executions(Item):
    def __init__(self):
        super(Executions, self).__init__(name="executions",item_type="executions",currency="BTC")
        self.executions_web_api = self.web_api.Executions(self.currency, self.logger, self.general_config_ini, self.private_api_ini)
        self.init_mongodb()
      
    def fetch_latest(self, sym=None, return_type="json"): 
        if sym is None:
            sym = self.currency
        v = self.executions_web_api.fetch_latestExecutions(sym,count=100, return_type=return_type)
        return v
    # TODO by order
    # def fetch(self, sym=None, return_type="json"): 
    #     if sym is None:
    #         sym = self.currency
    #     v = self.executions_web_api.fetch_latestExecutions(sym,count=100, return_type=return_type)
    #     return v
    
class Order(Item):
    def __init__(self):
        super(Order, self).__init__(name="order",item_type="order",currency="BTC")
        self.order_web_api = self.web_api.Order(self.currency, self.logger, self.general_config_ini, self.private_api_ini)
        self.init_mongodb()
        
    def create_entry_order(self, sym, side, executionType, timeInForce, price, losscutPrice,  size, cacnelBefore):
        reqBody = {
            "symbol": sym,
            "side": side,
            "executionType": executionType,
            "timeInForce": timeInForce,
            "price": price,
            "losscutPrice":losscutPrice,
            "size": size,
            "cacnelBefore":cacnelBefore
        }
        return reqBody
    
    def create_amend_order(self, orderId, price, losscutPrice):
        reqBody = {
            "orderId": orderId,
            "price": 1094001,
            "losscutPrice": None
        }
        return reqBody
    

    def entry(self,reqBody):
        try:
            self.order_web_api.validate_order_params(reqBody)
        except OrderParamException as e:
            self.logger.warning("")
        except CapacityException():
            self.logger.warning("")
            
        orderId = ""
        eventType = "orderEntry"
        try:
            res = self.order_web_api.do_order(**reqBody)
            orderId = res['data']
            return orderId
        except Exception as e:
            eventType = "orderEntry-Error"
        finally:
            reqBody["orderId"] = orderId
            reqBody["eventType"] = eventType
            self.logger.info("Attempt Entry: {0}".format(**reqBody))
            self.mongo_db.insert_one(reqBody)     
            
                  
      
