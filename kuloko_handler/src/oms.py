# coding: utf-8

import urllib.parse
import logging
import logging.config
import configparser

import pandas as pd
import numpy as np

import requests
import json

import time
from datetime import datetime as dt
from datetime import  timedelta, timezone

import hmac
import hashlib

from .util import daylib

private_api_ini = configparser.ConfigParser()
private_api_ini.read('./ini/private_api.ini', encoding='utf-8')

config_ini = configparser.ConfigParser()
config_ini.read('./ini/config.ini', encoding='utf-8')

logging.config.fileConfig('./ini/logconfig.ini')
logger = logging.getLogger("KULOKO")

dl = daylib.daylib()

import api_handler as api


class RequestError(Exception):
    pass

class InvalidArgumentError(Exception):
    pass


class OMS:
    def __init__(self):
        pass


    def 

    


        
