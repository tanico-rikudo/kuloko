from item import AleisterFeedAgent

class realtimeFeedAgent:
    
    def __init__(self):
        pass
    
    def start_fetch_feed(self):
        self.afa = AleisterFeedAgent()
        self.afa.start_realtime_fetch()
        
    def stop_fetch_feed(self):
        self.afa.stop_realtime_fetch()
        del self.afa
        

class histFeedAgent:
    
    def __init__(self):
        pass
    
    def fetch_feed(self):
        self.afa = AleisterFeedAgent()
        self.afa.init_db()
        data = self.afa.fetch_hist_realtime_data(20211201,20211211, ['orderbook'])[20211209]['orderbook']
        
    def end_fetch_feed(self):
        self.afa.stop_subscribe_realtime_data()
        del self.afa
    
        
        
        
        
        
    
