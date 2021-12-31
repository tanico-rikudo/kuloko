import threading
import argparse
import os, sys
sys.path.append(os.path.join(os.environ['KULOKO_DIR'],"items" ))
sys.path.append(os.path.join(os.path.dirname('__file__'),'..'))
sys.path.append(os.environ['COMMON_DIR'] )

from items.aleister_producer import AleisterFeedAgent
import hist_data
from mq.mq_handler import  *


class realtimeFeedAgent:
    
    def __init__(self, general_config_mode):
        self.afa = AleisterFeedAgent(general_config_mode)
        self.general_config  =  self.afa.general_config
        self.mqserver_host = self.general_config.get("MQ_HOST")
        self.mqname = self.general_config.get("MQ_NAME")
        self.routing_key = self.general_config.get("MQ_ROUTING")
        self.logger = self.afa.logger
        
    def init_mqclient(self):
        self.mq_rpc_client = RpcClient(self.mqserver_host,self.mqname, self.logger)
        self.logger.info("[DONE] New mq client")
        
    def start_fetch_feed(self):
        """
        Start subbscribe market data and send it to MQ
        """
        self.init_mqclient()
        try:
            #  Backgroud process=>no
            self.logger.info("[START] AleisterFeedAgent Realtime Provide.")
            # afa_provider_process = threading.Thread(target=self.start_fetch_feed)
            # # afa_provider_process.setDaemon(True)
            # afa_provider_process.start()
            
            self.start_fetch_feed()
            
        except  Exception as e:
            self.logger.info(f"[STOP] AleisterFeedAgent Realtime Privide.e={e}")
            self.stop_fetch_feed()        
                
    def stop_fetch_feed(self):
        """
        Kill fethcing market data and send it to MQ
        """
        self.mq_rpc_client.end_call()
        del self.afa
        self.logger.info("[STOP] Realtime feed STOP")
        
    def start_record(self):
        self.afa.start_record_realtime_data()

    def stop_record(self):
        self.afa.stop_record_realtime_data()()
        

class histFeedAgent:
    
    def __init__(self):
        self.hd = hist_data.histData()
        self.general_config_ini = self.hd.general_config_ini
        self.dl = self.hd.dl
        self.listed_syms = self.general_config_ini.get("LISTED_SYM")
        self.logger = self.hd._logger
        
    
    def download_hist(self, kinds=None, since_date=None ,until_date=None):
        until_date =  until_date if until_date is not None else  self.dl.add_day(self.dl.dt_to_intD(self.dl.currentTime()), -1)
        since_date =  since_date if since_date is not None else self.dl.add_day(until_date, 3)
        kinds = trades if trades is not None else ["trades"] 
        for _kind in kinds:
            for _sym in self.listed_syms:
                _ = self.hd.load(_sym, _kind, since_date,until_date)
                self.logger.info(f"[DONE] Download hist. Kind={_kind}, Sym={_sym}")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--process",
                        type=str, choices=['record', 'provider', 'killer'],
                        required=True,
                        help="Select process")
    opt = parser.parse_args()
    general_config_mode = "DEFAULT"
    #TODO: outside
    rfa  = realtimeFeedAgent(general_config_mode)
    if opt.process == "record":
        rfa.start_record()
    elif opt.process == "provider":
        rfa.start_fetch_feed()
    elif opt.process == "killer":
        rfa.stop_fetch_feed()
    else:
        raise Exception(f"Cannont recogninze option : {opt.process}")

        
        
        
        
        
    
