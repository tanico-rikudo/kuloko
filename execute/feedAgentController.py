import threading
import argparse
import os, sys

sys.path.append(os.path.join(os.environ["KULOKO_DIR"], "items"))
sys.path.append(os.path.join(os.path.dirname("__file__"), ".."))
sys.path.append(os.environ["COMMON_DIR"])

from items.aleister_producer import AleisterProducer
import hist_data
from mq.mq_handler import *


class baseFeedAgent(Object):
    def __init__(self, symbol, feed_type, general_config_mode, private_api_mode):
        self.afa = AleisterProducer(symbol, general_config_mode, private_api_mode)
        self.general_config = self.afa.general_config
        self.afa.load_mq_settings()
        self.logger = self.afa.logger

        self.mqserver_host = self.afa.mqserver_host
        self.mqname = self.afa.mqnames[feed_type]
        self.routing_key = self.afa.routing_keys[feed_type]

    def init_mqclient(self):
        self.mq_rpc_client = RpcClient(
            self.mqserver_host, self.mqname, self.routing_key, self.logger
        )
        self.logger.info("[DONE] New mq client")


class realtimeFeedAgent(baseFeedAgent):
    def __init__(self, symbol, general_config_mode, private_api_mode):
        super(realtimeFeedAgent, self).__init__(
            symbol=symbol,
            feed_type="realtime",
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
        )

    """ Subscribe market data and send it to MQ  """

    def start_fetch_feed(self):
        """
        Init and Subscribe
        """
        try:
            #  Backgroud process=>no
            self.logger.info("[START] AleisterFeedAgent Realtime Provide.")
            # afa_provider_process = threading.Thread(target=self.start_fetch_feed)
            # # afa_provider_process.setDaemon(True)
            # afa_provider_process.start()
            self.afa.start_realtime_fetch()

        except Exception as e:
            self.init_mqclient()
            self.stop_fetch_feed()
            self.logger.info(f"[STOP] AleisterFeedAgent Realtime Privide.e={e}")

    def stop_fetch_feed(self):
        """
        Kill fethcing market data and send it to MQ
        """
        self.mq_rpc_client.end_call()
        del self.afa
        self.logger.info("[STOP] AleisterFeedAgent Realtime Privide")

    """ Subscribe market data and Record """

    def start_record(self):
        # Note: Non mq
        self.logger.info("[START] AleisterFeedAgent Recording.")
        try:
            self.afa.start_record_realtime_data()
        except Exception as e:
            self.stop_record()
            self.logger.info(f"[STOP] AleisterFeedAgent Recording. e={e}")

    def stop_record(self):
        self.logger.info("[STOP] AleisterFeedAgent Recording.")
        self.afa.stop_record_realtime_data()
        del self.afa


class histFeedAgent:
    def __init__(self, symbol, general_config_mode, private_api_mode):
        super(baseFeedAgent, self).__init__(
            symbol=symbol,
            feed_type="historical",
            general_config_mode=general_config_mode,
            private_api_mode=private_api_mode,
        )

        self.hd = hist_data.histData(general_config_mode, private_api_mode)
        self.dl = self.hd.dl

    def download_hist(self, kinds=None, since_date=None, until_date=None):
        until_date = (
            until_date
            if until_date is not None
            else self.dl.add_day(self.dl.dt_to_intD(self.dl.currentTime()), -1)
        )
        since_date = (
            since_date if since_date is not None else self.dl.add_day(until_date, 3)
        )
        kinds = trades if trades is not None else ["trades"]

        self.listed_syms = self.general_config.get("LISTED_SYM")
        for _kind in kinds:
            for _sym in self.listed_syms:
                _ = self.hd.load(_sym, _kind, since_date, until_date)
                self.logger.info(f"[DONE] Download hist. Kind={_kind}, Sym={_sym}")

    """ Puck hist data and send it via MQ """

    def start_liaison(self):
        """
        Init and Subscribe
        """
        try:
            #  Backgroud process=>no
            self.logger.info("[START] AleisterFeedAgent Histdata Provide.")
            # afa_provider_process = threading.Thread(target=self.start_fetch_feed)
            # # afa_provider_process.setDaemon(True)
            # afa_provider_process.start()
            self.afa.start_histdata_liaison()

        except Exception as e:
            self.init_mqclient()
            self.logger.info(f"[STOP] AleisterFeedAgent Histdata Privide.e={e}")
            self.stop_fetch_feed()

    def stop_fetch_feed(self):
        """
        Kill fethcing hist data and send it to MQ
        """
        self.mq_rpc_client.end_call()
        del self.afa
        self.logger.info("[STOP] AleisterFeedAgent Histdata Privide")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--process",
        type=str,
        choices=["record", "provider", "liaison", "rkiller", "pkiller", "lkiller"],
        required=True,
        help="Select process",
    )
    parser.add_argument(
        "-s",
        "--symbol",
        type=str,
        choices=["BTC"],
        required=True,
        help="Select process",
    )
    parser.add_argument(
        "-type",
        "--data_type",
        type=str,
        choices=["REAL", "HIST"],
        required=True,
        help="Select fetch data type. Hist data or Realtime data",
    )
    parser.add_argument(
        "-gcm",
        "--general_config_mode",
        type=str,
        required=True,
        help="Select general config mode",
    )
    parser.add_argument(
        "-pam",
        "--private_api_mode",
        type=str,
        required=True,
        help="Select private api mode",
    )
    opt = parser.parse_args()
    symbol = opt.symbol
    general_config_mode = opt.general_config_mode
    private_api_mode = opt.private_api_mode
    data_type = opt.data_type
    if data_type == "REAL":
        rfa = realtimeFeedAgent(symbol, general_config_mode, private_api_mode)
        if opt.process == "record":
            rfa.start_record()
        elif opt.process == "rkiller":
            rfa.stop_record()

        elif opt.process == "provider":
            rfa.start_fetch_feed()
        elif opt.process == "pkiller":
            rfa.stop_fetch_feed()
        else:
            raise Exception(f"Cannont recogninze option : {opt.process}")

    elif data_type == "HIST":
        hfa = histFeedAgent(symbol, general_config_mode, private_api_mode)
        if opt.process == "liaison":
            hfa.start_liaison()
        elif opt.process == "lkiller":
            hfa.stop_fetch_feed()
        else:
            raise Exception(f"Cannont recogninze option : {opt.process}")
