import os
import configparser

from sqlalchemy import create_engine
from sqlalchemy import desc
from sqlalchemy import Table, Column, String, MetaData, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func

from utils.utils import get_logger

logger = get_logger()

# Read config data
config = configparser.ConfigParser()
config.read("config.ini")

# Apply config values to vars
username = config['Database']['username']

password_db = os.getenv("password_db")
host = os.getenv("host_db")

port = config['Database']['port']
database = config['Database']['database']

database_uri = 'postgres://' + username + ':' + password_db + '@' + host + ':' + port + "/" + database

channels_init = text(""" INSERT INTO channels (channel_id, title, link, enable) 
             VALUES ('1019255153', 'картинки-картиночки', 'https://t.me/ny_privetik', True), 
             ('1103602213', 'KrololoPower', 'https://t.me/Krololochannel', True) """)


class Database:
    engine = create_engine(database_uri)
    Session = sessionmaker(engine, expire_on_commit=False)
    meta = MetaData(engine)
    channels_table = Table('channels', meta,
                           Column('channel_id', Integer, primary_key=True),
                           Column('title', String),
                           Column('link', String),
                           Column('enable', Boolean))

    revision_table = Table('revisions', meta,
                           Column('channel_id', Integer, ForeignKey('channels.channel_id'), primary_key=True),
                           Column('date_time', DateTime, primary_key=True),
                           Column('number', Integer))

    posts_table = Table('posts', meta,
                        Column('channel_id', Integer, ForeignKey('channels.channel_id'), primary_key=True),
                        Column('message_id', Integer, primary_key=True),
                        Column('media', String),
                        Column('posted', Boolean, default=False))

    def __init__(self):
        self.connection = self.engine.connect()
        logger.info("DB Instance created")
        if not self.engine.dialect.has_table(self.engine, 'channels'):
            self.channels_table.create()
            self.engine.execute(channels_init)
        if not self.engine.dialect.has_table(self.engine, 'revisions'):
            self.revision_table.create()
        if not self.engine.dialect.has_table(self.engine, 'posts'):
            self.posts_table.create()

    def addChannel(self, channel):
        session = self.Session()
        session.add(channel)
        session.commit()
        session.close()

    def addRevision(self, revision):
        session = self.Session()
        session.add(revision)
        session.commit()
        session.close()

    def addPosts(self, posts):
        session = self.Session()
        session.add_all(posts)
        session.commit()
        session.close()

    def getRandomPost(self):
        session = self.Session()
        r = session.query(Post).filter(Post.posted == False).order_by(func.random()).first()
        session.expunge_all()
        session.close()
        return r

    def setPostPosted(self, post):
        session = self.Session()
        r = session.query(Post).filter(Post.channel_id == post.channel_id).filter(
            Post.message_id == post.message_id).first()
        r.posted = True
        session.commit()
        session.close()

    def getRevisionByIDAndDate(self, channel_id, date):
        session = self.Session()
        r = session.query(Revision).filter(Revision.channel_id == channel_id).filter(Revision.date == date).first()
        session.expunge_all()
        session.close()
        return r

    def getChannelByID(self, channel_id):
        session = self.Session()
        r = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        session.expunge_all()
        session.close()
        return r

    def delChannelByID(self, channel_id):
        session = self.Session()
        r = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        session.delete(r)
        session.commit()
        session.close()

    def getAllChannels(self):
        session = self.Session()
        channels = session.query(Channel).all()
        session.expunge_all()
        session.close()
        return channels

    def printAllChannels(self):
        session = self.Session()
        channels = session.query(Channel).all()
        for channel in channels:
            print(channel)
        session.close()

    def printAllRevisions(self):
        session = self.Session()
        revisions = session.query(Revision).all()
        for revision in revisions:
            print(revision)
        session.close()

    def printAllPosts(self):
        session = self.Session()
        posts = session.query(Post).all()
        for post in posts:
            print(post)
        session.close()

    def clearPosts(self):
        session = self.Session()
        r = session.query(Post).delete()
        session.commit()
        session.close()
        return r

    def getPostsInfo(self):
        session = self.Session()
        total = session.query(Post).count()
        posted = session.query(Post).filter(Post.posted == True).count()
        not_posted = session.query(Post).filter(Post.posted == False).count()
        session.expunge_all()
        session.close()
        return total, posted, not_posted

    def getLast10Revisions(self):
        session = self.Session()
        result = session.query(Revision.channel_id, Channel.title, Revision.number, Revision.date_time).filter(
            Revision.channel_id == Channel.channel_id).order_by(desc(Revision.date_time)).limit(10).all()
        session.expunge_all()
        session.close()
        return result


Base = declarative_base()


class Channel(Base):
    """Model for channel"""
    __tablename__ = 'channels'
    channel_id = Column(Integer, primary_key=True)
    title = Column(String)
    link = Column(String)
    enable = Column(Boolean)

    revision = relationship('Revision', backref="parent", cascade='all, delete-orphan')
    post = relationship('Post', backref="parent", cascade='all, delete-orphan')

    def __init__(self, channel_id, title, link, enable):
        self.channel_id = channel_id
        self.title = title
        self.link = link
        self.enable = enable

    def __repr__(self):
        return "<Channel(id='%s', title='%s', link='%s' enable='%s')>" % (
            self.channel_id, self.title, self.link, self.enable)


class Revision(Base):
    """Model for revision channel"""
    __tablename__ = 'revisions'
    channel_id = Column(Integer, ForeignKey('channels.channel_id', ondelete='CASCADE'), primary_key=True)
    date_time = Column(DateTime, primary_key=True)
    number = Column(Integer)

    def __init__(self, channel_id, date_time, number):
        self.channel_id = channel_id
        self.date_time = date_time
        self.number = number

    def __repr__(self):
        return "<Revision(channel_id='%s', date_time='%s', number='%s')>" % (
            self.channel_id, self.date_time, self.number)


class Post(Base):
    """Model for storing post"""
    __tablename__ = 'posts'
    channel_id = Column(Integer, ForeignKey('channels.channel_id', ondelete='CASCADE'), primary_key=True)
    message_id = Column(Integer, primary_key=True)
    media = Column(String)
    posted = Column(Boolean)

    def __init__(self, channel_id, message_id, media, posted):
        self.channel_id = channel_id
        self.message_id = message_id
        self.media = media
        self.posted = posted

    def __repr__(self):
        return "<Post(channel_id='%s', message_id='%s', media='%s' posted='%s')>" % \
               (self.channel_id, self.message_id, self.media, self.posted)
