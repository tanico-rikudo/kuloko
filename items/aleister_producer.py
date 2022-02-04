import sys, os
import pika
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from .item import Item
import public_api
import private_api

sys.path.append(os.environ["COMMON_DIR"])
from mongodb.src.mongo_handler import *
import json
from mq.mq_handler import MqProvider
import hist_data


#  stand alone from ITEM
class AleisterFeedAgent(Item):
    def __init__(self, general_config_mode, private_api_mode):
        # Note: No specific private spi
        super(AleisterFeedAgent, self).__init__(
            name="AleisterFeedAgent",
            item_type="AleisterFeedAgent",
            currency="BTC",
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
        )
        # Init handler
        self.socket_handler = {}
        self.rest_handler = {}
        self.db_accesser = None
        self.hd = hist_data.histData(general_config_mode, private_api_mode)

        # MQ
        self.interval_sec = 10  # todo: outside
        self.max_feed_instance = 4  # todo: outside
        self.load_mq_settings()

        # db
        self.mongo_util = None

    # def __del__(self):
    #     self.close_socket()
    #     self.db_accesser.dao.close()

    def load_mq_settings(self):
        self.mqserver_host = self.general_config.get("MQ_HOST")
        self.mqnames = {
            "realtime": self.general_config.get("REALTIMEFEED_MQ_NAME"),
            "historical": self.general_config.get("HISTORICAL_MQ_NAME"),
        }
        self.routing_keys = {
            "realtime": self.general_config.get("REALTIMEFEED_MQ_ROUTING"),
            "historical": self.general_config.get("HISTORICAL_MQ_ROUTING"),
        }

    """" Initilize  """

    def init_db(self):
        # Init mongo
        self.init_mongodb()

        # wrap util
        self.db_accesser = MongoUtil(self.mongo_db, self.logger)
        self.logger.info("[DONE] Init mongo DB wrpper")

    def init_skt(self):
        self.socket_handler = {
            "orderbook": public_api.Orderbook(
                self.general_config_mode, self.private_api_mode
            ),
            "trade": public_api.Trade(self.general_config_mode, self.private_api_mode),
            "ticker": public_api.Ticker(
                self.general_config_mode, self.private_api_mode
            ),
        }

    def init_rest(self):
        self.rest_handler = {
            "margin": private_api.Margin(
                self.general_config_mode, self.private_api_mode
            )
        }

    """ Socker Handle """

    def connect_sockets(self):
        """Connect Socket"""
        # setup socket
        if len(self.socket_handler.keys()) == 0:
            self.init_skt()

        # connect all
        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].connect()

        self.logger.info(f"[DONE] Connect sockets.")

    def close_socket(self):
        """Close Socket"""

        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].disconnect()

        self.logger.info(f"[STOP] Subscribe sockets.")

    def start_subscribe_socket(self):
        """
        Start subscrie in all set socket
        """
        for obj_name in self.socket_handler.keys():
            self.socket_handler[obj_name].subscribe()

        self.logger.info(f"[START] Subscribe via socket handler.")

    def setup_data_provider(self, routing_key, mqname):
        """Init/Connect all data endpoint"""
        # soket datas
        self.init_skt()
        self.connect_sockets()

        # rest datas
        self.init_rest()

        # mq
        self.mq_privider = MqProvider(
            self.mqserver_host, mqname, routing_key, self.logger
        )
        self.mq_privider.connect_mq()
        self.logger.info(f"[DONE] Init data fetch setup")

    def start_rpc_receiver(self, process_name):
        self.mq_privider.channel.basic_qos(prefetch_count=1)
        if process_name == "replay_realtime_data":
            self.mq_privider.channel.basic_consume(
                on_message_callback=lambda ch, method, properties, body: self.replay_realtime_data(
                    ch, method, properties, body
                ),
                queue=self.mqname,
            )

        elif process_name == "replay_hist_data":
            self.mq_privider.channel.basic_consume(
                on_message_callback=lambda ch, method, properties, body: self.replay_hist_data(
                    ch, method, properties, body
                ),
                queue=self.mqname,
            )
        else:
            raise Exception(f"Fail to launch RPC receiver. Process={process_name}.")

        self.logger.info(f"[START] RPC receiver. Process={process_name}")
        self.mq_privider.channel.start_consuming()

    ### Fetch data ###
    def fetch_realtime_data(self):
        """
        Get data from queue and api
        Returns:
            result json
        """
        result = {}
        # fetch socket api
        cnt = 0
        for obj_name in self.socket_handler.keys():
            result[obj_name] = self.socket_handler[obj_name].dequeue()
            cnt += len(result[obj_name]) if result[obj_name] is not None else 0
        self.logger.info(f"[DONE] Fetch data from socket. Count={cnt}")

        # fetch rest api
        cnt = 0
        for obj_name in self.rest_handler.keys():
            result[obj_name] = self.rest_handler[obj_name].fetch("json")
            cnt += len(result[obj_name])
        self.logger.info(f"[DONE] Fetch data from api. Count={cnt}")
        json_result = json.dumps(result)
        # print(json_result)
        return json_result

    def fetch_hist_data(self, kind, sym, sd, ed):
        """
        Get hist data from DB or file
        Returns:
            result dict
        """
        result = self.hd.get_data(kind, sym, sd, ed)
        json_result = json.dumps(result)
        return json_result

    ###  Get realtime data and Provide aleister  ###
    def start_realtime_fetch(self):
        """
        Provide master for  realtime to predict realtime
        """
        self.setup_data_provider(
            self.routing_keys["realtime"], self.mqnames["realtime"]
        )
        self.start_subscribe_socket()
        self.start_rpc_receiver(process_name="replay_realtime_data")

    def replay_realtime_data(self, ch, method, properties, body):
        """
        Event drivern fetch and puclish data
        Args:
            ch ([type]): [description]
            method ([type]): [description]
            properties ([type]): [description]
            body ([type]): [description]

        Returns:
            [type]: [description]
        """
        self.logger.info(f"[DONE] Get request MQ.")
        corr_id = properties.correlation_id
        corr_id = None if corr_id is None else corr_id
        try:
            if body.decode() == "END":
                self.logger.info(f"[APPROVED] Get request MQ END call")
                ch.stop_consuming()
                self.mq_privider.channel.stop_consuming()
                self.logger.info(f"[STOP] RPC receiver stop from RPC")

            data = self.fetch_realtime_data()
            if properties.reply_to is not None:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=corr_id),
                    body=data,
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                self.logger.info(f"[RETURN] Returrn RPC request. ID={corr_id}")
            else:
                self.logger.warning(
                    f"[Skip] No Returrn address. Skip return RPC request. ID={corr_id}"
                )
        except Exception as e:
            self.logger.warning(
                f"[Failure] Fail to replay. ID={corr_id}. e={e}", exc_info=True
            )

    ### Get hist data and Provide aleister ###
    def init_histdata_fetch(self):
        self.setup_data_provider(
            self.routing_key["historical"], self.mqnames["historical"]
        )
        self.start_rpc_receiver(process_name="replay_hist_data")

    def replay_hist_data(self, ch, method, properties, body):
        """
        Event drivern fetch and puclish data
        Args:
            ch ([type]): [description]
            method ([type]): [description]
            properties ([type]): [description]
            body ([type]): [description]

        Returns:
            [type]: [description]
        """
        self.logger.info(f"[DONE] Get request MQ.")
        corr_id = properties.correlation_id
        corr_id = None if corr_id is None else corr_id
        try:
            # Process end call
            producer_command_str = body.decode()
            if producer_command_str == "END":
                self.logger.info(f"[APPROVED] Get request MQ END call")
                ch.stop_consuming()
                self.mq_privider.channel.stop_consuming()
                self.logger.info(f"[STOP] RPC receiver stop from RPC")

            # fetch data
            try:
                producer_command_dict = ast.literal_eval(producer_command_str)

                data = self.fetch_hist_data(**producer_command_dict)
            except Exception as e:
                data = json.dumps({})

            #  return data
            if properties.reply_to is not None:
                ch.basic_publish(
                    exchange="",
                    routing_key=properties.reply_to,
                    properties=pika.BasicProperties(correlation_id=corr_id),
                    body=data,
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                self.logger.info(f"[RETURN] Returrn RPC request. ID={corr_id}")
            else:
                self.logger.warning(
                    f"[Skip] No Returrn address. Skip return RPC request. ID={corr_id}"
                )
        except Exception as e:
            self.logger.warning(
                f"[Failure] Fail to replay. ID={corr_id}. e={e}", exc_info=True
            )

    ###  Get realtime data. Use for test.  ###
    def start_record_realtime_data(self):
        self.logger.info("[START] Subscribe realtime data")
        #  init connection and subscribe
        self.setup_data_provider(
            self.routing_keys["realtime"], self.mqnames["realtime"]
        )
        self.start_subscribe_socket()

        # self.scheduler = BackgroundScheduler()
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(
            self.fetch_realtime_data,
            "interval",
            seconds=self.interval_sec,
            max_instances=self.max_feed_instance,
        )
        try:
            self.logger.info(
                f"[START] Realtime data recording has been scheduled. Interval={self.interval_sec}sec"
            )
            self.scheduler.start()
        except Exception as e:
            self.logger.error(f"{e}", exc_info=True)
            self.stop_record_realtime_data()

    def stop_record_realtime_data(self):
        try:
            self.scheduler.shutdown()
        except:
            pass
        finally:
            self.close_socket()
        self.logger.info("[END] Realtime data recordingn scheduleder stopped.")
