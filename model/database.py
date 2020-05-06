import os
import configparser

from sqlalchemy import create_engine
from sqlalchemy import Table, Column, String, MetaData, Integer, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from utils.utils import get_logger

logger = get_logger()

# Read config data
config = configparser.ConfigParser()
config.read("config.ini")

# Apply config values to vars
username = config['Database']['username']

password_db = os.getenv("password_db")

host = config['Database']['host']
port = config['Database']['port']
database = config['Database']['database']

database_uri = 'postgres://' + username + ':' + password_db + '@' + host + ':' + port + "/" + database


class Database:
    engine = create_engine(database_uri)
    Session = sessionmaker(engine)
    meta = MetaData(engine)
    channels_table = Table('channels', meta,
                           Column('channel_id', Integer, primary_key=True),
                           Column('title', String),
                           Column('enable', Boolean))

    def __init__(self):
        self.connection = self.engine.connect()
        logger.info("DB Instance created")
        if not self.engine.dialect.has_table(self.engine, 'channels'):
            self.channels_table.create()

    def addChannel(self, channel):
        session = self.Session()
        session.add(channel)
        session.commit()
        session.close()

    def fetchChannelByID(self, channel_id):
        session = self.Session()
        r = session.query(Channel).filter(Channel.channel_id == channel_id).first()
        session.expunge_all()
        session.close()
        return r

    def fetchAllChannels(self):
        session = self.Session()
        channels = session.query(Channel).all()
        for channel in channels:
            print(channel)
        session.close()


Base = declarative_base()


class Channel(Base):
    """Model for channel"""
    __tablename__ = 'channels'
    channel_id = Column(Integer, primary_key=True)
    title = Column(String)
    enable = Column(Boolean)

    def __init__(self, channel_id, title, enable):
        self.channel_id = channel_id
        self.title = title
        self.enable = enable

    def __repr__(self):
        return "<Channel(id='%s', title='%s', enable='%s')>" % (self.channel_id, self.title, self.enable)
