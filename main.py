import os
import configparser

from utils.utils import get_logger
from controller.controller import Controller

logger = get_logger()

# Read config data
config = configparser.ConfigParser()
config.read("config.ini")

# Apply config values to vars
session = config['Telegram']['session']

mode = os.getenv("MODE")
api_id = os.getenv('api_id')
api_hash = os.getenv('api_hash')


if __name__ == '__main__':
    if mode == "dev":
        logger.info("Dev mode select")
        proxy_ip = config['Telegram']['proxy_ip']
        proxy_port = int(config['Telegram']['proxy_port'])
        secret = config['Telegram']['secret']
        proxy = (proxy_ip, proxy_port, secret)
        controller = Controller(session, api_id, api_hash, mode="dev", proxy=proxy)
    elif mode == "prod":
        logger.info("Prod mode select")
        controller = Controller(session, api_id, api_hash, mode="prod", proxy=None)
