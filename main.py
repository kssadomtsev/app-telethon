import os
import configparser

from utils.utils import get_logger

from telethon.sync import TelegramClient
from telethon import connection

logger = get_logger()

# Read config data
config = configparser.ConfigParser()
config.read("config.ini")

# Apply config values to vars
api_id = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']

mode = os.getenv("MODE")
if mode == "dev":
    logger.info("Dev mode select")
    proxy_ip = config['Telegram']['proxy_ip']
    proxy_port = int(config['Telegram']['proxy_port'])
    secret = config['Telegram']['secret']
    proxy = (proxy_ip, proxy_port, secret)
    client = TelegramClient(username, api_id, api_hash, proxy=proxy,
                            connection=connection.ConnectionTcpMTProxyRandomizedIntermediate)
elif mode == "prod":
    logger.info("Prod mode select")
    client = TelegramClient(username, api_id, api_hash)


# This is our update handler. It is called when a new update arrives.
async def handler(update):
    logger.info(update)


# Use the client in a `with` block. It calls `start/disconnect` automatically.
with client:
    # Register the update handler so that it gets called
    client.add_event_handler(handler)

    # Run the client until Ctrl+C is pressed, or the client disconnects
    logger.info('(Press Ctrl+C to stop this)')
    client.run_until_disconnected()
