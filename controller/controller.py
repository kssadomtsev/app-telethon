import os

from utils.utils import get_logger

from telethon.sync import TelegramClient, events, utils
from telethon import connection

logger = get_logger()


class Controller:

    def __init__(self, session, api_id, api_hash, mode,
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
        with self.client:
            self.client.add_event_handler(self.handler, events.NewMessage)
            cat = self.client.get_entity('lazycat90210')
            print(cat)
            cat = self.client.get_input_entity('lazycat90210')
            print(cat)
            self.client.send_message('lazycat90210', '`too`')
            dialogs = self.client.get_dialogs()
            print(dialogs)
            logger.info(self.client.get_me().stringify())
            logger.info('(Press Ctrl+C to stop this)')
            self.client.run_until_disconnected()

    async def handler(self, event):
        sender = await event.get_sender()
        logger.info(sender.stringify())
        name = utils.get_display_name(sender)
        print(name, 'said', event.text, '!')
        await event.reply('hi!')
