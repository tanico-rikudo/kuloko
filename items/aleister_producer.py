import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='aleister')
channel.basic_publish(exchange='',
                      routing_key='realtime_data',
                      body=json.dumps(a))
connection.close()

class AleisterFeedAgent:
    
    def  __init__(self):
        pass


    def merge_data(method="default", datas=None):
        """
        Construct integrated data from realtime(past/now)
        datas are privided by subscribe_realtime_data or  fetch_hist_realtime_data
        """
        pass

    def feed_mq():
        """
        Produce data for aleister through MQ
        """
        pass

    def subscribe_realtime_data():
        """
        Get realtime data
        """
        pass

    def fetch_hist_realtime_data():
        """
        Get realtime feed data from DB
        """
        pass

    def do_in_realtime():
        """
        Provide master for  realtime to predict realtime
        """
        pass

    def do_in_past():
        """
        Provide master for afterward to  learning
        """
        pass