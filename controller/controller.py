import os
import asyncio

from utils.utils import get_logger
from model.database import Database, Channel

from telethon.sync import TelegramClient, events, utils
from telethon.tl.functions.channels import JoinChannelRequest
from telethon import connection

logger = get_logger()

# Create a global variable to hold the loop we will be using
loop = asyncio.get_event_loop()


class Controller:

    def __init__(self, session, api_id, api_hash, channels, mode,
                 proxy=None):
        """
        Initializes the InteractiveTelegramClient.
        :param session: Name of the *.session file.
        :param api_id: Telegram's api_id acquired through my.telegram.org.
        :param api_hash: Telegram's api_hash.
        :param mode: development or production mode
        :param proxy: Optional proxy tuple/dictionary.
        """
        if mode == "dev":
            self.client = TelegramClient(session, api_id, api_hash, proxy=proxy,
                                         connection=connection.ConnectionTcpMTProxyRandomizedIntermediate)

        elif mode == "prod":
            self.client = TelegramClient(session, api_id, api_hash)
        # Use the client in a `with` block. It calls `start/disconnect` automatically.
        self.database = Database()
        with self.client:
            self.client.add_event_handler(self.handler, events.NewMessage)
            loop.run_until_complete(self.join_channel(channels.split(",")))
            # cat = self.client.get_entity('lazycat90210')
            # print(cat)
            # cat = self.client.get_input_entity('lazycat90210')
            # print(cat)
            # self.client.send_message('lazycat90210', '`too`')
            # dialogs = self.client.get_dialogs()
            # print(dialogs)
            # logger.info(self.client.get_me().stringify())
            # logger.info('(Press Ctrl+C to stop this)')
            self.database.fetchAllChannels()
            self.client.run_until_disconnected()

    async def handler(self, event):
        sender = await event.get_sender()
        logger.info(sender.stringify())
        name = utils.get_display_name(sender)
        print(name, 'said', event.text, '!')
        await event.reply('hi!')

    async def join_channel(self, channels):
        for channel_url in channels:
            channel_entity = await self.client.get_entity(channel_url)
            if self.database.fetchChannelByID(channel_entity.id) is None:
                channel = Channel(channel_entity.id, channel_entity.title, True)
                self.database.addChannel(channel)
                logger.info('%s %s', channel_entity.title, 'was added to database')
                try:
                    await self.client(JoinChannelRequest(channel_url))
                    logger.info('%s %s', 'success join to the channel', channel_entity.title)
                except:
                    logger.error('%s %s', 'failed join to the channel', channel_entity.title)
            else:
                logger.info('%s %s %s', 'channel with ID', channel_entity.id, 'already in database')
