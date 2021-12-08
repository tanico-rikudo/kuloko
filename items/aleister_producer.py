import pika
from apscheduler.schedulers.blocking import BlockingScheduler

import public_api
import private_api

class AleisterFeedAgent:
    
    def  __init__(self):
        # Init Logger 
        self.logger = cm.load_log_config(os.path.join(LOGDIR,'logging.log'),log_name="KULOKO")
        self.socket_handler = {}
        self.rest_handler = {}
        
        #MQ
        self.mqserver_host = "localhost"
        self.mqname = "aleister"
        self.routing_key = "realtime_data"
        self.interval_sec = 60
        self.max_feed_instance =4
        
    def connect_mq(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.mqserver_host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.mqname)
        self.logger.info(f"[DONE] Connect MQ server. Host={self.mqserver_host}, Name={self.mqname}, Routing={self.routing_key}")
        
    def send_data_via_mq(self, data): 
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
            self.socket_handler[_k].connect()
        
        # start subscribeb
        for obj_name in self.socket_handler.keys():
            self.socket_handler[_k].subscribe()

        self.logger.info(f"[DONE] Connect sockets.")

    def setup_realtime_data(self):
        """
        Get realtime data
        """
        # soket datas
        self.init_skt()
        self.connect_sockets()

        # rest datas
        self.init_rest()
        
    def subscribe_realtime_data(self):
        self.logger.info("[START] Subscribe realtime data")
        self.scheduler = BackgroundScheduler() 
        self.scheduler.add_job(self.fetch_realtime_data, 'interval', seconds=self.interval_sec, max_instances=self.max_feed_instance)  
        self.scheduler.start()
        self.logger.info("[START] Realtime data Subscription has been scheduled.")
    
    def stop_subscribe_realtime_data(self):
        self.scheduler.shutdown() 
        self.logger.info("[END] Realtime data Subscription scheduleder stopped.")
        
    
    def fetch_realtime_data(self):
        result = {}
        cnt = 0
        # fetch socket api
        for obj_name in self.socket_handler.keys():
            result[_k] = self.socket_handler[_k].dequeue()
            cnt += len(result[_k])
        
        # fetch rest api
        for obj_name in self.rest_handler.keys():
            result[_k] = self.rest_handler[_k].fetch('json')
            cnt += len(result[_k])
        self.logger.info(f"[DONE] Fetch data from socket and api. Count={cnt}")
        
        # take over to MQ       
        self.feed_mq(result)
        
    def fetch_hist_realtime_data():
        """
        Get realtime feed data from DB
        """
        pass

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