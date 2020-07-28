from datetime import date, time, datetime, timedelta
import pytz
import asyncio
import configparser
import codecs

from utils.utils import get_logger
from model.database import Database, Channel, Post, Revision

from telethon.sync import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.channels import LeaveChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import GetMessagesRequest
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from telethon import connection

# Read config data
config = configparser.ConfigParser()
config.read("config.ini")

# Apply config values to vars
chat = config['Bot']['chat']
buffer_chat = config['Bot']['buffer_chat']

logger = get_logger()

# Create a global variable to hold the loop we will be using
loop = asyncio.get_event_loop()


class Controller:
    albums = {}
    active_posting = True

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
            # Task to print alive-messages every 5 minutes
            loop.create_task(self.print_forever())
            # Task to grab the most popular posts from channels (table "channels") every day at 08:00 GMT+3
            loop.create_task(self.do_dump_schedule())
            # Task to post 2 times in hour 3 random media from posts (table "posts") in period 09:00-23:00 GMT+3
            loop.create_task(self.do_post_schedule())
            self.client.run_until_disconnected()

    async def forward_album_legacy(self, event):
        logger.info('Recieved message with album')
        await event.mark_read()
        pair = (event.chat_id, event.grouped_id)
        if pair in self.albums:
            self.albums[pair].append(event.message)
            return
        self.albums[pair] = [event.message]
        await asyncio.sleep(0.3)
        messages = self.albums.pop(pair)
        logger.info('%s %s', 'Album contains photos:', str(len(messages)))
        await event.respond(f'Got {len(messages)} photos!')
        medias = []
        for msg in messages:
            medias.append(msg.media)
        await self.client.send_file(chat, medias, caption='✅ [Сохранёнки](https://t.me/savedmemess)')

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
            await self.client.send_file(chat, media,
                                        caption='✅ [Сохранёнки](https://t.me/savedmemess)')
        else:
            logger.info("Message doesn't contain media photo or video")
            if msg.message.lower() == 'help':
                logger.info('Message is help request')
                with codecs.open('help.html', "r", encoding='utf-8') as help_file:
                    help_msg = help_file.read()
                    await event.respond(help_msg, parse_mode='html')
            elif msg.message.lower() == 'list':
                logger.info('Message is channels list  request')
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
                        channel_entity = await self.client.get_input_entity(
                            self.database.getChannelByID(channel_id).link)
                        await self.client(LeaveChannelRequest(
                            channel=channel_entity))
                        self.database.delChannelByID(channel_id)
                        success_msg = channel_id + ', channel with this id was successfully deleted from the database.' \
                                                   'Media from this channel was deleted too and bot leave channel'
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
            elif msg.message.lower() == 'dump':
                logger.info('Message is request dump messages from channel manually')
                try:
                    await self.do_dump()
                    success_msg = 'Request dump messages from channel manually was handled success'
                    logger.info(success_msg)
                    await event.respond(success_msg)
                except Exception as ex:
                    error_msg = "Failed dump messages from channels " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)
            elif msg.message.lower() == 'post':
                logger.info('Message is request to do 3 posts manually')
                try:
                    await self.do_post()
                    success_msg = 'Request to do 3 posts manually was handled success'
                    logger.info(success_msg)
                    await event.respond(success_msg)
                except Exception as ex:
                    error_msg = "Failed to do 3 posts manually " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)
            elif msg.message.lower() == 'start':
                logger.info('Message is request to start automatic posting')
                if self.active_posting is True:
                    logger.info('Automatic posting is active already')
                    await event.respond('Automatic posting is active already')
                else:
                    self.active_posting = True
                    logger.info('Automatic posting is set true')
                    await event.respond('Automatic posting is set true')
            elif msg.message.lower() == 'stop':
                logger.info('Message is request to stop automatic posting')
                if self.active_posting is False:
                    logger.info('Automatic posting is stop already')
                    await event.respond('Automatic posting is stop already')
                else:
                    self.active_posting = False
                    logger.info('Automatic posting stopped')
                    await event.respond('Automatic posting stopped')
            elif msg.message.lower() == 'stats':
                logger.info('Message is request to get bot statistic')
                try:
                    logger.info('Get information about posts database')
                    total, posted, not_posted = self.database.getPostsInfo()
                    msg = 'Bot statistic:\nPost database contains posts: ' + str(total) + '\nPosted count: ' + str(
                        posted) + '\nNot posted count: ' + str(not_posted) + '\nInformation about last 10 revisions:\n'
                    logger.info('Get information about last 10 revisions')
                    revisions = self.database.getLast10Revisions()
                    for revision in revisions:
                        msg += 'Channel ID: ' + str(revision[0]) + ', channel name: ' + revision[1] + ', collected: ' \
                               + str(revision[2]) + ', time(GMT+3): ' \
                               + str(
                            revision[3].astimezone(pytz.timezone("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")) + '\n'
                    # print(revisions)
                    logger.info(msg)
                    await event.respond(msg)
                except Exception as ex:
                    error_msg = "Failed to to get bot statistic " + str(ex)
                    logger.error(error_msg)
                    await event.respond(error_msg)
            else:
                logger.info('Command is unrecognized. Use help command')
                await event.respond('Command is unrecognized. Use help command')

    async def join_channel(self):
        channels = self.database.getAllChannels()
        for channel in channels:
            try:
                await self.client(JoinChannelRequest(channel.channel_id))
                logger.info('%s %s', 'success join to the channel', channel.title)
            except Exception as ex:
                logger.error('%s %s %s', 'failed join to the channel', channel.title, str(ex))

    async def do_dump_schedule(self):
        while True:
            logger.info("Get current time in UTC")
            current_time_utc = datetime.time(datetime.now(pytz.utc))
            logger.info('%s %s', 'Now: ', str(current_time_utc))
            dump_time_utc = time(hour=5, minute=0)
            if current_time_utc <= dump_time_utc:
                logger.info("Current time less than 08:00 GMT+3(05:00 UTC)")
                remaining = (datetime.combine(datetime.date(datetime.now(pytz.utc)), dump_time_utc)
                             - datetime.combine(datetime.date(datetime.now(pytz.utc)),
                                                current_time_utc)).total_seconds()
            else:
                logger.info("Current time greater than 08:00 GMT+3(05:00 UTC)")
                remaining = (datetime.combine(datetime.date(datetime.now(pytz.utc)) + timedelta(days=1), dump_time_utc)
                             - datetime.combine(datetime.date(datetime.now(pytz.utc)),
                                                current_time_utc)).total_seconds()
            logger.info('%s %s', "Now go sleep for: ", str(remaining))
            await asyncio.sleep(remaining)
            logger.info('Now 08:00 GMT+3. Dump process wake up!')
            try:
                await self.do_dump()
            except Exception as ex:
                error_msg = "Failed dump messages from channels " + str(ex)
                logger.error(error_msg)

    async def do_dump(self):
        logger.info('Task#1 - clear messages table')
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
                        'Filter messages that not album with media photo or video and text without invite link and not reply')
                    filtered_posts_list = list(
                        filter(lambda msg: (dt_after <= msg.date and dt_before >= msg.date)
                                           and (msg.grouped_id is None)
                                           and (msg.media is not None)
                                           and (msg.reply_markup is None)
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
                    logger.info('%s %s', 'Add revision record about channel for this date', channel.title)
                    revision = Revision(channel.channel_id, datetime.now(pytz.utc), len(filtered_posts_list))
                    try:
                        self.database.addRevision(revision)
                    except Exception as ex:
                        error_msg = "Failed to store revision to database with exception " + str(ex)
                        logger.error(error_msg)
                except Exception as ex:
                    error_msg = "Failed to dump message from channel " + channel.title + " : " + str(ex)
                    logger.error(error_msg)
        except Exception as ex:
            error_msg = "Failed to get last 200 messages from channels in general: " + str(ex)
            logger.error(error_msg)
        logger.info('%s %s', 'Totally from all channels got messages: ', str(len(posts_list_global)))
        logger.info('Task#4 - Now we should cast class Message to Posts')
        logger.info('Now we should cast class Message to Post')
        # logger.info(posts_list_global[0])
        filtered_posts_list_global_in_post = list(
            map(lambda msg: Post(msg.to_id.channel_id, msg.id, "", msg.date, False), posts_list_global))
        # for x in filtered_posts_list_global_in_post: print(x)
        self.database.addPosts(filtered_posts_list_global_in_post)
        # for post in filtered_posts_list_global_in_post:
        #     await self.client.send_file('test_channel_5', pickle.loads(post.media),
        #                                 caption='✅ [Сохранёнки](https://t.me/savedmemess)')
        #     await asyncio.sleep(5)
        #    await asyncio.sleep(80)

    async def do_post_schedule(self):
        while True:
            logger.info("Function post 2 times in hour 3 random media from database in period 09:00-23:00 GMT+3 "
                        "or 06:00-20:00 UTC")
            logger.info("Get current time in UTC")
            current_time_utc = datetime.time(datetime.now(pytz.utc))
            logger.info('%s %s', 'Now: ', str(current_time_utc))
            after_time_utc = time(hour=6, minute=0)
            before_time_utc = time(hour=20, minute=0)
            if current_time_utc < after_time_utc:
                logger.info("Current time less than 09:00 GMT+3(06:00 UTC)")
                remaining = (datetime.combine(datetime.date(datetime.now(pytz.utc)), after_time_utc)
                             - datetime.combine(datetime.date(datetime.now(pytz.utc)),
                                                current_time_utc)).total_seconds()
                logger.info('%s %s', "Now go sleep for: ", str(remaining))
                await asyncio.sleep(remaining)
            if current_time_utc > before_time_utc:
                logger.info("Current time greater than 23:00 GMT+3(20:00 UTC)")
                remaining = (datetime.combine(datetime.date(datetime.now(pytz.utc)) + timedelta(days=1), after_time_utc)
                             - datetime.combine(datetime.date(datetime.now(pytz.utc)),
                                                current_time_utc)).total_seconds()
                logger.info('%s %s', "Now go sleep for: ", str(remaining))
                await asyncio.sleep(remaining)
            else:
                if self.active_posting is True:
                    logger.info('Automatic posting is active now')
                    # self.database.printAllPosts()
                    logger.info("Time to post!")
                    await self.do_post()
                    logger.info("Done! Now sleep for 29 minutes")
                    await asyncio.sleep(1740)
                else:
                    logger.info('Automatic posting is inactive now')
                    logger.info("Now sleep for 30 minutes")
                    await asyncio.sleep(1800)

    async def do_post(self):
        for i in range(0, 3):
            try:
                post = self.database.getRandomPost()
                logger.info("Select from database following random post:")
                logger.info(str(post))
                logger.info("Trying to retrive message from channel:")
                channel_entity = await self.client.get_input_entity(post.channel_id)
                logger.info(str(channel_entity))
                msg = await self.client(GetMessagesRequest(
                    channel=channel_entity,
                    id=[post.message_id]
                ))
                logger.info(str(msg))
                media = msg.messages[0].media
                await self.client.send_file(buffer_chat, media,
                                            caption='✅ [Сохранёнки](https://t.me/savedmemess) \n Поста из канала: ' + post.channel_id)
                logger.info("Post was send. Now mark it in database as marked")
                try:
                    self.database.setPostPosted(post)
                except Exception as ex:
                    error_msg = "Failed with exception: " + str(ex)
                    logger.error(error_msg)
            except Exception as ex:
                error_msg = "Failed to post exception: " + str(ex)
                logger.error(error_msg)
            finally:
                await asyncio.sleep(5)

    async def print_forever(self):
        while True:
            logger.info("Await(alive) function")
            current_time_utc = datetime.time(datetime.now(pytz.utc))
            logger.info('%s %s', 'Now: ', str(current_time_utc))
            await asyncio.sleep(300)
