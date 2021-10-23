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
        """ Order  Entty

        Args:
            reqBody ([type]): [description]

        Returns:
            [string]: [Order Id or None]
        """
        
        # Build order and check
        orderId = None
        try:
            self.order_web_api.validate_order_params(reqBody)
        except OrderParamException as e:
            self.logger.warning("Invalid order params:{0}".format(e))
            return orderId
        except CapacityException():
            self.logger.warning("Over capacity:{0}".format(e))
            return orderId
            
        # Post attempt
        self.logger.info("Attempt Entry: {0}".format(reqBody))
        try:
            res, success = self.order_web_api.do_order(**reqBody)
            if success:
                orderId = res['data']
                eventType = "orderEntry"
                self.logger.warning("[DONE]Order Entry")
            else:
                eventType = "orderEntry-Reject"
                self.logger.warning("Reject to order entry:{0}".format(res['messages']))
        except Exception as e:
            eventType = "orderEntry-Error"
            self.logger.warning("Fail to order entry:{0}".format(e))
        finally:
            reqBody["orderId"] = orderId
            reqBody["eventType"] = eventType
            self.mongo_db.insert_one(reqBody)    
            return orderId 

    def amend(self,reqBody):
        """ Order amend

        Args:
            reqBody ([type]): [description]

        Returns:
            [string]: [Order Id or None]
        """
        
        # Build order and check

        try:
            self.order_web_api.validate_change_params(reqBody)
            orderId = reqBody['orderId']
        except OrderParamException as e:
            self.logger.warning("Invalid order params: OrderId={0}, Reason={1}".format(orderId, e))
            return orderId
        except CapacityException():
            self.logger.warning("Over capacity: OrderId={0}, Reason={1}".format(orderId, e))
            return orderId
    
            
        # Post attempt
        self.logger.info("Attempt Amend Order: {0}".format(reqBody))
        try:
            res, success = self.order_web_api.do_change(**reqBody)
            if success:
                eventType = "orderAmend"
                self.logger.warning("[DONE]Order Entry. OrderId={0}".format(orderId))
            else:
                eventType = "orderAmend-Reject"
                self.logger.warning("Reject to order amend: OrderId={0}, Reason={1}".format(orderId, res['messages']))
        except Exception as e:
            eventType = "orderAmend-Error"
            self.logger.warning("Fail to order amend: OrderId={0}, Reason={1}".format(orderId, e))
        finally:
            reqBody["eventType"] = eventType
            self.mongo_db.insert_one(reqBody)    
            return  orderId
        
    def cancel(self,reqBody):
        """ cancel order

        Args:
            reqBody ([type]): [description]

        Returns:
            [string]: [Order Id or None]
        """
        
        # Build order and check
        try:
            orderId = reqBody['orderId']
            self.order_web_api.validate_cancel_params(reqBody)
        except OrderParamException as e:
            self.logger.warning("Invalid order params: OrderId={0}, Reason={1}".format(orderId, e))
            return orderId
            
        # Post attempt
        self.logger.info("Attempt Cancel: {0}".format(reqBody))
        try:
            res, success = self.order_web_api.do_cancel(**reqBody)
            if success:
                eventType = "orderCancel"
                self.logger.warning("[DONE]Order Cancel: OrderId={0}".format(orderId))
            else:
                eventType = "orderCancel-Reject"
                self.logger.warning("Reject to order cancel: OrderId={0}, Reason={1}".format(orderId,res['messages']))
        except Exception as e:
            eventType = "orderCancel-Error"
            self.logger.warning("Fail to order cancel: OrderId={0}, Reason={1}".format(orderId, e))
        finally:
            reqBody["eventType"] = eventType
            self.mongo_db.insert_one(reqBody)    
            return  orderId
    