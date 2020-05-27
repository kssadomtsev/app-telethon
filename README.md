[![Build Status](https://travis-ci.org/kssadomtsev/ordicynbot_4.svg?branch=master)](https://travis-ci.org/kssadomtsev/ordicynbot_4)

# Channels grabber Telegram bot

This Telegram bot can be used to automatic monitoring some public Telegram channels, storing most popular posts in database and reposting in your channel by schedule.

## Tutorial

### Creating your Telegram Application
1. Follow [this link](https://my.telegram.org/auth) and login with your phone number.
2. Go to ['API development tools'](https://my.telegram.org/apps) and fill out the form.
3. You will get basic addresses as well as the **api_id** and **api_hash** parameters required for user authorization. Store this parameters in safe place!

### Installation

1. Create new project in your favorite IDE
2. Clone this repo to your local machine in project directory using `https://github.com/kssadomtsev/ordicynbot_4`
3. Install needed requirements using `pip install -r requirements.txt` (if it needed you should update pip before)

### Configure the Application

To run this Python application with your own bot you usually have to adjust the config.ini file.
```shell
[Telegram]
session = <here you should pass unique session name as every new session required new authentication >
proxy_ip = <MTProto proxy domain name or IP address>
proxy_port = <MTProto proxy port>
secret= <MTProto proxy secret>
[Database]
username = <Postgres usename with rights to write to database>
port = <Postgres port, usually 5432>
database = <Database name>
[Bot]
chat = <Your channel unique name>
```
### Set environment variables

Your should create 5 environment variables:

| Variable | Value |
| --- | --- |
| `MODE` | dev, prod |
| `api_id` | Unique api_id from ['API development tools'](https://my.telegram.org/apps) |
| `api_hash` | Unique api_hash from ['API development tools'](https://my.telegram.org/apps) |
| `password_db` | Password for user from config.ini value Database.username |
| `host_db` | IP, domain name or docker container name |

### First start
As your new client not authorized yet after first application start will appear prompt to enter new code that Telegram sent you over the app (over phone application for example).
In success case new session will be store in file <Telegram.session>.session (Telegram.session - value from config.ini)  in your disk (persistent information such as access key and others). This is by default a database file using Python’s sqlite3.
In case if you will decide to move project from dev to prod environment you should move *.session file too.

## How it works

### Model
![UML](https://raw.githubusercontent.com/kssadomtsev/app-telethon/master/UML.png)

Application class model is based on UML diagram bellow. By using ORM SQLAlchemy class model related with database model.
Let's see purpose every class (table):
1. Channel (table ''channels'') - represent Telegram channel and store information about channels than should be used as content source.
2. Revision (table ''revision'')  - represent history log with information about Telegram channel revision. It needed for statistic purpose.
3. Post (table ''posts'') - represent single telegram post. Application is clearing and filling this table by schedule.

Tables ''revision'' and ''posts'' are empty by default, but table ''channels'' init SQL script is hardcoded in model/database.py

### asyncio

asyncio is a Python 3's built-in library. This means it's already installed if you have Python 3.

Application based on  asynchronous module Telethon. By this reason controller class controller/controller.py has some asyncio methods.

Assigning the default event loop from the main thread to a variable:
```
# Create a global variable to hold the loop we will be using
loop = asyncio.get_event_loop()
```

Adding tasks to event loop:
```
# Task to print alive-messages every 5 minutes
loop.create_task(self.print_forever())
# Task to grab the most popular posts from channels (table "channels") every day at 08:00 GMT+3
loop.create_task(self.do_dump_schedule())
# Task to post 2 times in hour 3 random media from posts (table "posts") in period 09:00-23:00 GMT+3
loop.create_task(self.do_post_schedule())
```

And finally run Telegram client (and all it's event handlers). It should be run after all operations with event loop as it takes control until end.
```
self.client.run_until_disconnected()
```

### Hardcoded details
Application accepts control connection as specific telegram commands in direct chat to your bot user. List of users how can send this command is hardcoded in controller/controller.py (look at parameter from_users)
```
self.client.add_event_handler(self.forward_album_legacy,
                              events.NewMessage(from_users=('@user1', '@user2'),
                                                            func=lambda e: e.grouped_id))
self.client.add_event_handler(self.forward_msg, events.NewMessage(from_users=('@user1', '@user2'),
                                                            func=lambda e: e.grouped_id is None))
```



## Technologies

* Python 3.8
* [Telethon](https://tl.telethon.dev/)
* asyncio
* PostgreSQL
* [SQLAlchemy](https://www.sqlalchemy.org/)
* Docker