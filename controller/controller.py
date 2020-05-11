from datetime import date, time, datetime
import asyncio

from utils.utils import get_logger
from model.database import Database, Channel

from telethon.sync import TelegramClient, events, utils
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message
from telethon import connection

logger = get_logger()

# Create a global variable to hold the loop we will be using
loop = asyncio.get_event_loop()


class Controller:
    albums = {}

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
        self.database = Database()
        with self.client:
            self.client.add_event_handler(self.forward_album_legacy,
                                          events.NewMessage(from_users=('@Ordicyn', '@lazycat90210'),
                                                            func=lambda e: e.grouped_id))
            self.client.add_event_handler(self.forward_msg, events.NewMessage(from_users=('@Ordicyn', '@lazycat90210'),
                                                                              func=lambda e: e.grouped_id is None))
            # loop.run_until_complete(self.join_channel(channels.split(",")))
            # loop.run_until_complete(self.periodic_tasks())
            # cat = self.client.get_entity('lazycat90210')
            # print(cat)
            # cat = self.client.get_input_entity('lazycat90210')
            # print(cat)
            # self.client.send_message('lazycat90210', '`too`')
            # dialogs = self.client.get_dialogs()
            # print(dialogs)
            # logger.info(self.client.get_me().stringify())
            # logger.info('(Press Ctrl+C to stop this)')
            # self.database.fetchAllChannels()
            self.client.run_until_disconnected()

    async def forward_album_legacy(self, event):
        pair = (event.chat_id, event.grouped_id)
        if pair in self.albums:
            self.albums[pair].append(event.message)
            return
        self.albums[pair] = [event.message]
        await asyncio.sleep(0.3)
        messages = self.albums.pop(pair)
        await event.respond(f'Got {len(messages)} photos!')
        medias = []
        for msg in messages:
            medias.append(msg.media)
        await self.client.send_file('lazycat90210', medias, caption='✅ [Сохранёнки](https://t.me/savedmemess)')

    async def forward_msg(self, event):
        logger.info('%s %s', "Event", str(event))
        sender = await event.get_sender()
        logger.info('%s %s', "Recieved new message for forwarding from", str(sender.username))
        msg = event.message
        logger.info('%s %s', "Message", str(msg))
        if msg.media is not None and (type(msg.media) == 'MessageMediaPhoto'
                                      or type(msg.media) == 'MessageMediaDocument'):
            logger.info('Message contains media photo or video')
            media = msg.media
            await self.client.send_file('lazycat90210', media,
                                        caption='✅ [Сохранёнки](https://t.me/savedmemess)')
        else:
            logger.info("Message doesn't contain some media")
            if msg.message.lower() == 'help':
                logger.info('Message is help request')
                await event.respond(f'help')
            elif msg.message.lower() == 'list':
                logger.info('Message is channels list request')
                try:
                    channels = self.database.getAllChannels()
                    response = "Now is listening following channels:\n" + "\n".join(map(str, channels))
                    logger.error(response)
                    await event.respond(message=response, link_preview=False)
                except Exception as ex:
                    error_msg = "Failed to get chanel list with exception: " + str(ex)
                    logger.error(error_msg)
            elif msg.message.lower().startswith('add'):
                logger.info('Message is request to add channel to list')
                try:
                    channel_url = msg.message.lower().split(' ')[1]
                    logger.info('%s %s', "Trying to add new channel by link", channel_url)
                    channel_entity = await self.client.get_entity(channel_url)
                    if self.database.getChannelByID(channel_entity.id) is None:
                        channel = Channel(channel_entity.id, channel_entity.title, channel_url, True)
                        self.database.addChannel(channel)
                        success_msg = channel_entity.title + ' was added to database'
                        logger.info(success_msg)
                        await event.respond(success_msg)
                    else:
                        error_msg = 'channel with ID ' + str(channel_entity.id) + ' already in database'
                        logger.error(error_msg)
                        await event.respond(error_msg)
                except Exception as ex:
                    error_msg = "Failed to add channel to list with exception: " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)
            elif msg.message.lower().startswith('delete'):
                logger.info('Message is request to delete channel from list')

    async def join_channel(self, channels):
        for channel_url in channels:
            channel_entity = await self.client.get_entity(channel_url)
            if self.database.getChannelByID(channel_entity.id) is None:
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

    async def periodic_tasks(self):
        asyncio.create_task(self.print_forever())
        asyncio.create_task(self.dump_channels())

    async def dump_channels(self):
        while True:
            current_time = datetime.time(datetime.now()).strftime("%H:%M:%S")
            # if current_time == "09:00:00":

            channels = self.database.getAllChannels()
            for channel in channels:
                logger.info('%s %s', 'Try to dump message from channel', channel.title)
                try:
                    logger.info('At first we need to be sure that channel hasnt been dumped yet')
                    current_date = date.today()
                    current_datetime = datetime.now()
                    print(current_date)
                    if self.database.getRevisionByIDAndDate(channel.channel_id, current_date) is None:
                        logger.info('This channel hasnt been dumped yet')
                        try:
                            logger.info('Init telethon request')
                            channel_entity = await self.client.get_input_entity(channel.channel_id)
                            posts = await self.client(GetHistoryRequest(
                                peer=channel_entity,
                                limit=100,
                                offset_date=None,
                                offset_id=0,
                                max_id=0,
                                min_id=0,
                                add_offset=0,
                                hash=0))

                            print(posts.messages.__class__)
                            print(len(posts.messages))
                            # for msg in posts.messages:
                            #     print(msg.__class__)
                            # print(msg.stringify())
                        except:
                            logger.info('%s %s', 'Failed to dump message from channel via telethon', channel.title)
                except:
                    logger.info('%s %s', 'Failed to dump message from channel', channel.title)
            await asyncio.sleep(60)
        # print("Await function")
        # await asyncio.sleep(60)

    async def print_forever(self):
        while True:
            print("Await function")
            await asyncio.sleep(60)
