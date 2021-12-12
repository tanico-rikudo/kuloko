import pika
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from item import Item
import public_api
import private_api
from mongodb.src.mongo_handler import *
import json 

#  stand alone from ITEM

class AleisterFeedAgent(Item):
    def  __init__(self):
        super(AleisterFeedAgent, self).__init__(name="AleisterFeedAgent",item_type="AleisterFeedAgent",currency="BTC")
        
        # Init handler 
        self.socket_handler = {}
        self.rest_handler = {}
        self.db_accesser = None
        
        #MQ
        self.mqserver_host = self.general_config_ini.get("MQ_HOST")
        self.mqname = self.general_config_ini.get("MQ_NAME")
        self.routing_key = self.general_config_ini.get("MQ_ROUTING")
        self.interval_sec = 10
        self.max_feed_instance =4
        
        #db
        self.mongo_util = None
        
    def __del__(self):
        self.close_socket()
        self.db_accesser.dao.close()
        
    def init_db(self):
        # target set
        self.tables = ['orderbook','trade','ticker']
        # Init mongo
        self.init_mongodb()
        
        # wrap util
        self.db_accesser =  MongoUtil(self.mongo_db, self.logger)
        self.logger.info("[DONE] Init mongo DB wrpper")
        
    def connect_mq(self):

        self.connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=self.mqserver_host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.mqname)
        self.logger.info(f"[DONE] Connect MQ server. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def publish_mq(self, data, exchange='', routing_key=None,properties=None ):  
        exchange = '' if exchange is None else exchange
        routing_key = self.routing_key if routing_key is None else routing_key
        self.channel.basic_publish(exchange=exchange,
                                    routing_key=routing_key,
                                    properties= properties,
                                    body=data)
        self.logger.info(f"[DONE] Send data via MQ. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def close_mq(self):
        self.channel.basic_cancel() # declare no more send
        self.connection.close()
        self.logger.info(f"[DONE] Close MQ connecton. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def init_skt(self):
        self.socket_handler = {
            "orderbook" : public_api.Orderbook(),
            "trade" : public_api.Trade(),
            "ticker": public_api.Ticker()
            }
        
    def init_rest(self):
        self.rest_handler = {
            "margin" : private_api.Margin()
        }
        
    def connect_sockets(self):
        # setup socket
        if len(self.socket_handler.keys()) == 0:
           self.init_skt() 
        
        # connect all
        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].connect()

        self.logger.info(f"[DONE] Connect sockets.")
        
    def close_socket(self):
        # stop subscribeb
        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].disconnect()
    
        self.logger.info(f"[STOP] Subbscrieb sockets.")
        
    def start_subscribe_socket(self):
        # start subscribeb
        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].subscribe()
    
        self.logger.info(f"[START] Subbscrieb sockets.")

    def setup_realtime_data(self):
        """
        Get realtime data
        """
        # soket datas
        self.init_skt()
        self.connect_sockets()

        # rest datas
        self.init_rest()
        
        #mq
        self.connect_mq()
        self.logger.info(f"[DONE] Init data fetch setup")
        
    def subscribe_realtime_data(self):
        self.logger.info("[START] Subscribe realtime data")
        #  init connection and subscrieb
        self.start_subscribe_socket()
        
        self.scheduler = BackgroundScheduler() 
        self.scheduler.add_job(self.publish_realtime_data, 'interval', seconds=self.interval_sec, max_instances=self.max_feed_instance)  
        self.scheduler.start()
        self.logger.info("[START] Realtime data Subscription has been scheduled.")
    
    def stop_subscribe_realtime_data(self):
        self.scheduler.shutdown() 
        self.close_socket()
        self.logger.info("[END] Realtime data Subscription scheduleder stopped.")
        
    def start_realtime_rpc_receiver(self):
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(on_message_callback= lambda ch, method, properties, body: self.replay_realtime_data(ch, method, properties, body), queue=self.mqname)

        self.logger.info(f"[START] RPC receiver")
        self.channel.start_consuming()

                
    def fetch_realtime_data(self):
        result = {}
        # fetch socket api
        cnt = 0
        for obj_name in self.socket_handler.keys():
            result[obj_name] = self.socket_handler[obj_name].dequeue()
            cnt += len(result[obj_name]) if result[obj_name] is not None else  0
        self.logger.info(f"[DONE] Fetch data from socket. Count={cnt}")
        
        # fetch rest api
        cnt = 0
        for obj_name in self.rest_handler.keys():
            result[obj_name] = self.rest_handler[obj_name].fetch('json')
            cnt += len(result[obj_name])
        self.logger.info(f"[DONE] Fetch data from api. Count={cnt}")
        json_result = json.dumps(result)
        return json_result
    
    def publish_realtime_data(self):
        data = self.fetch_realtime_data()
        self.publish_mq(data)
        
    def replay_realtime_data(self, ch, method, properties, body):
        self.logger.info(f"[DONE] Get request MQ.")
        corr_id = properties.correlation_id
        corr_id = None if corr_id is None else corr_id
        try:
            if body.decode() == 'END':
                self.logger.info(f"[APPROVED] Get request MQ END call")
                ch.stop_consuming()
                self.channel.stop_consuming()
                self.logger.info(f"[STOP] RPC receiver stop from RPC")

            data = self.fetch_realtime_data()
            ch.basic_publish(exchange='',
                            routing_key=properties.reply_to,
                            properties=pika.BasicProperties(correlation_id = corr_id),
                            body=data)
            ch.basic_ack(delivery_tag = method.delivery_tag)
            self.logger.info(f"[RETURN] Returrn RPC request. ID={corr_id}")
        except Exception as e:
            self.logger.warning(f"[Failure] Fail to replay. ID={corr_id}")
                
    def fetch_hist_realtime_data(self, start_date, end_date, tables):
        """
        Get realtime feed data from DB
        """
        if  tables is None:
            tables  = self.tables
            
        datas = {}
        date_list  = self.dl.get_between_date(start_date, end_date)
        for _date in  date_list:
            datas[_date] = {}
            for table_name in tables:
                datas[_date][table_name] = self.db_accesser.find_at_date(table_name, str(_date))
        
        return datas

    def start_realtime_fetch(self):
        """
        Provide master for  realtime to predict realtime
        """
        self.setup_realtime_data()
        # self.subscribe_realtime_data()
        self.start_realtime_rpc_receiver()
        
    def stop_realtime_fetch(self):
        self.stop_subscribe_realtime_data()
        