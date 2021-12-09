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
        self.mqserver_host = "localhost"
        self.mqname = "aleister"
        self.routing_key = "realtime_data"
        self.interval_sec = 10
        self.max_feed_instance =4
        
        #db
        self.mongo_util = None
        
    def init_mongodb(self):
        # target set
        self.tables = ['orderbook','trade','ticker']
        # Init mongo
        self.init_mongodb()
        
        # wrap util
        self.db_accesser =  MongoUtil(self.mongo_db, self.logger)
        self.logger.info("[DONE] Init mongo DB wrpper")
        
    def connect_mq(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.mqserver_host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.mqname)
        self.logger.info(f"[DONE] Connect MQ server. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def send_data_via_mq(self, data):  
        # self.logger.info(data)
        self.channel.basic_publish(exchange='',
                                    routing_key=self.routing_key,
                                    body=json.dumps(data))
        self.logger.info(f"[DONE] Send data via MQ. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def close_mq(self):
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
        self.scheduler.add_job(self.fetch_realtime_data, 'interval', seconds=self.interval_sec, max_instances=self.max_feed_instance)  
        self.scheduler.start()
        self.logger.info("[START] Realtime data Subscription has been scheduled.")
    
    def stop_subscribe_realtime_data(self):
        self.scheduler.shutdown() 
        self.close_socket()
        self.logger.info("[END] Realtime data Subscription scheduleder stopped.")
        
    
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
        
        # take over to MQ       
        self.send_data_via_mq(result)
        
    def fetch_hist_realtime_data(self, start_date, end_date, tables):
        """
        Get realtime feed data from DB
        """
        if  tables is None:
            tables  = self.tables
            
        datas = {}
        date_list  = get_between_date(start_date, end_date)
        for _date in  date_list:
            datas[_date] = {}
            for table_name in tables:
                datas[_date][table_name] = self.db_accesser.find_at_date(table_name, str(_date))
        
        return datas

    def do_in_realtime():
        """
        Provide master for  realtime to predict realtime
        """
        self.setup_realtime_data()
        self.subscribe_realtime_data()
        

    def do_in_past():
        """
        Provide master for afterward to  learning
        """
        pass