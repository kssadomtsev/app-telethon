from datetime import date, time, datetime, timedelta
import pytz
import asyncio
import pickle

from utils.utils import get_logger
from model.database import Database, Channel, Post

from telethon.sync import TelegramClient, events, utils
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
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
            loop.run_until_complete(self.periodic_tasks())
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
        await event.mark_read()
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
        await event.mark_read()
        logger.info('%s %s', "Event", str(event))
        sender = await event.get_sender()
        logger.info('%s %s', "Recieved new message for forwarding from", str(sender.username))
        msg = event.message
        logger.info('%s %s', "Message", str(msg))
        if msg.media is not None and (isinstance(msg.media, MessageMediaPhoto)
                                      or isinstance(msg.media, MessageMediaDocument)):
            logger.info('Message contains media photo or video')
            media = msg.media
            await self.client.send_file('lazycat90210', media,
                                        caption='✅ [Сохранёнки](https://t.me/savedmemess)')
        else:
            logger.info("Message doesn't contain media photo or video")
            if msg.message.lower() == 'help':
                logger.info('Message is help request')
                await event.respond(f'help')
            elif msg.message.lower() == 'list':
                logger.info('Message is channels list request')
                try:
                    channels = self.database.getAllChannels()
                    response = "Now is listening following channels:\n" + "\n".join(map(str, channels))
                    logger.info(response)
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
                        success_msg = channel_entity.title + ' was added to database. Dumping will start at 8:00 GMT+3'
                        logger.info(success_msg)
                        await event.respond(success_msg)
                    else:
                        error_msg = 'Channel with ID ' + str(channel_entity.id) + ' already in database'
                        logger.error(error_msg)
                        await event.respond(error_msg)
                except Exception as ex:
                    error_msg = "Failed to add channel to list with exception: " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)
            elif msg.message.lower().startswith('delete'):
                logger.info('Message is request to delete channel from list')
                try:
                    channel_id = msg.message.lower().split(' ')[1]
                    if self.database.getChannelByID(channel_id) is not None:
                        self.database.delChannelByID(channel_id)
                        success_msg = channel_id + ', channel with this id was successfully deleted from the database.' \
                                                   'Media from this channel will be posted until 8:00 GMT+3'
                        logger.info(success_msg)
                        await event.respond(success_msg)
                    else:
                        error_msg = 'Channel with ID ' + str(channel_id) + ' not in database'
                        logger.error(error_msg)
                        await event.respond(error_msg)
                except Exception as ex:
                    error_msg = "Failed to delete channel from list with exception: " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)

    async def join_channel(self):
        channels = self.database.getAllChannels()
        for channel in channels:
            try:
                await self.client(JoinChannelRequest(channel.channel_id))
                logger.info('%s %s', 'success join to the channel', channel.title)
            except Exception as ex:
                logger.error('%s %s %s', 'failed join to the channel', channel.title, str(ex))

    async def periodic_tasks(self):
        asyncio.create_task(self.print_forever())
        asyncio.create_task(self.dump_channels())

    async def dump_channels(self):
        while True:
            current_time_utc = datetime.time(datetime.now(pytz.utc)).strftime("%H:%M")
            # if current_time_utc == "05:00":
            if True:
                logger.info('Now 08:00 GMT+3. Task#1 - clear messages table')
                try:
                    r = self.database.clearPosts()
                    logger.info('%s %s', str(r), ' posts was cleared')
                except Exception as ex:
                    error_msg = "Failed to clear messages table with exception: " + str(ex)
                    logger.error(error_msg)
                logger.info('Task#2 - join to channels')
                try:
                    await self.join_channel()
                except Exception as ex:
                    error_msg = "Failed to join to channels with exception: " + str(ex)
                    logger.error(error_msg)
                logger.info('Task#3 - Get last 200 messages from channels in date range'
                            ' [current date-1 21:00; current date-2 21:00]')
                # Current date in UTC
                current_date = datetime.date(datetime.now(pytz.utc))
                logger.info('%s %s', 'Current date in UTC ', str(current_date))
                # 18:00 in UTC = 21:00 in GMT + 3
                time_dump = time(hour=18, minute=0)
                # before datetime = current date-1 21:00
                dt_before = datetime.combine(current_date - timedelta(days=1), time_dump).replace(tzinfo=pytz.UTC)
                logger.info('%s %s', 'before datetime = current date-1 21:00 ', str(dt_before))
                # after datetime = current date-2 21:00
                dt_after = datetime.combine(current_date - timedelta(days=2), time_dump).replace(tzinfo=pytz.UTC)
                logger.info('%s %s', 'after datetime = current date-2 21:00 ', str(dt_after))
                # global posts list
                posts_list_global = []
                try:
                    logger.info('Get actual channel list')
                    channels = self.database.getAllChannels()
                    for channel in channels:
                        logger.info('%s %s', 'Try to dump message from channel', channel.title)
                        try:
                            logger.info('At first we need to be sure that channel hasnt been dumped yet')
                            if self.database.getRevisionByIDAndDate(channel.channel_id, current_date) is None:
                                logger.info('This channel hasnt been dumped yet')
                                logger.info('Init telethon request')
                                channel_entity = await self.client.get_input_entity(channel.channel_id)
                                posts_list = []
                                # Get first 100 messages
                                logger.info('Get first 100 messages')
                                posts = await self.client(GetHistoryRequest(
                                    peer=channel_entity,
                                    limit=100,
                                    offset_date=dt_before,
                                    offset_id=0,
                                    max_id=0,
                                    min_id=0,
                                    add_offset=0,
                                    hash=0))
                                logger.info('%s %s', 'Got messages: ', str(len(posts.messages)))
                                posts_list.extend(posts.messages)
                                offset_id = posts_list[99].id
                                logger.info('%s %s', 'Offset message id: ', str(offset_id))
                                logger.info('Get another 100 messages')
                                posts = await self.client(GetHistoryRequest(
                                    peer=channel_entity,
                                    limit=100,
                                    offset_date=dt_before,
                                    offset_id=offset_id,
                                    max_id=0,
                                    min_id=0,
                                    add_offset=0,
                                    hash=0))
                                logger.info('%s %s', 'Got messages: ', str(len(posts.messages)))
                                posts_list.extend(posts.messages)
                                logger.info('%s %s', 'Totally got messages: ', str(len(posts_list)))
                                logger.info(
                                    'Filter messages that not album with media photo or video and text without invite link')
                                filtered_posts_list = list(
                                    filter(lambda msg: (dt_after <= msg.date and dt_before >= msg.date)
                                                       and (msg.grouped_id is None)
                                                       and (msg.media is not None)
                                                       and (isinstance(msg.media, MessageMediaPhoto)
                                                            or isinstance(msg.media, MessageMediaDocument))
                                                       and (not any(
                                        s in msg.message for s in ["https", ".shop", ".com", ".ru"])), posts_list))
                                logger.info('%s %s', 'After filtering  messages list contain: ',
                                            str(len(filtered_posts_list)))
                                # for x in filtered_posts_list: logger.info(str(x))
                                logger.info('Sort list by views and save 50% first more popular post to global')
                                filtered_posts_list.sort(key=lambda msg: msg.views, reverse=True)
                                # for x in filtered_posts_list[:int(len(filtered_posts_list)/2)]: logger.info(str(x))
                                posts_list_global.extend(filtered_posts_list[:int(len(filtered_posts_list) / 2)])

                        except Exception as ex:
                            error_msg = "Failed to dump message from channel " + channel.title + " : " + str(ex)
                            logger.error(error_msg)
                except Exception as ex:
                    error_msg = "Failed to get last 200 messages from channels in general: " + str(ex)
                    logger.error(error_msg)
                logger.info('%s %s', 'Totally from all channels got messages: ', str(len(posts_list_global)))
                logger.info('Task#4 - Now we should cast class Message to Posts')
                logger.info('Now we should cast class Message to Post')
                #print(posts_list_global[0])
                filtered_posts_list_global_in_post = list(
                    map(lambda msg: Post(msg.id, msg.to_id.channel_id, pickle.dumps(msg.media), False), posts_list_global))
                for x in filtered_posts_list_global_in_post: print(x)
                self.database.addPosts(filtered_posts_list_global_in_post)
                for post in filtered_posts_list_global_in_post:
                    await self.client.send_file('test_channel_5', pickle.loads(post.media),
                                                caption='✅ [Сохранёнки](https://t.me/savedmemess)')
                    await asyncio.sleep(5)
                await asyncio.sleep(60)
        # print("Await function")
        # await asyncio.sleep(60)

    async def print_forever(self):
        while True:
            print("Await function")
            await asyncio.sleep(60)
