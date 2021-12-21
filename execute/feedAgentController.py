import threading
from item import AleisterFeedAgent
import hist_data

class realtimeFeedAgent:
    
    def __init__(self):
        self.afa = AleisterFeedAgent()
        self.general_config_ini  =  self.afa.general_config_ini
        self.mqserver_host = self.general_config_ini .get("MQ_HOST")
        self.mqname = self.general_config_ini .get("MQ_NAME")
        self.routing_key = self.general_config_ini .get("MQ_ROUTING")
        self.logger = self.afa._logger
        
    def init_mqclient(self):
        self.mq_rpc_client = RpcClient(self.mqserver_host,self.mqname, self.logger)
        
    def build_provider(self):
        self.init_mqclient()
        
        try:
            #  Backgroud process
            afa_provider_process = threading.Thread(target=start_fetch_feed)
            afa_provider_process.setDaemon(True)
            afa_provider_process.start()
            
            self.logger.info("[START] AleisterFeedAgent Realtime Privide Deamon.")
        except  Exception as e:
            self.stop_fetch_feed()        
            self.logger.info("[STOP] AleisterFeedAgent Realtime Privide Deamon.")
            
    def start_fetch_feed(self):
        self.afa.start_realtime_fetch()
        
    def stop_fetch_feed(self):
        self.mq_rpc_client.end_call()
        del self.afa
        

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
        
        
        
        
    
    # def fetch_feed(self):
    #     self.afa = AleisterFeedAgent()
    #     self.afa.init_db()
    #     data = self.afa.fetch_hist_realtime_data(20211201,20211211, ['orderbook'])[20211209]['orderbook']
        
    # def end_fetch_feed(self):
    #     self.afa.stop_subscribe_realtime_data()
    #     del self.afa
    
        
        
        
        
        
    
