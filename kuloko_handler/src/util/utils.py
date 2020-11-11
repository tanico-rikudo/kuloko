import os, socket
def get_env():
    info = {}
    info['hostname'] = socket.gethostname()
    if info['hostname'] in ['Macico']:
        env_name = 'DEV'
    else:
        env_name = None
    info['env_name']=env_name
    return info

