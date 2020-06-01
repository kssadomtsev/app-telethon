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

#### Admins access

Application accepts control connection as specific telegram commands in direct chat to your bot user. List of users how can send this command is hardcoded in controller/controller.py (look at parameter from_users)
```
self.client.add_event_handler(self.forward_album_legacy,
                              events.NewMessage(from_users=('@user1', '@user2'),
                                                            func=lambda e: e.grouped_id))
self.client.add_event_handler(self.forward_msg, events.NewMessage(from_users=('@user1', '@user2'),
                                                            func=lambda e: e.grouped_id is None))
```
#### Spam filter

For preventing resend promotion and posts with links application application uses hardcoded lambda expression in controller/controller.py 
```
filtered_posts_list = list(
        filter(lambda msg: (dt_after <= msg.date and dt_before >= msg.date)
                           and (msg.grouped_id is None)
                           and (msg.media is not None)
                           and (msg.reply_markup is None)
                           and (isinstance(msg.media, MessageMediaPhoto)
                                or isinstance(msg.media, MessageMediaDocument))
                           and (not any(
            s in msg.message for s in ["https", ".shop", ".com", ".ru"])), posts_list))
```
#### Text watermark

Application send posts in your channel with text link watermark. Look at parameter `caption` in command `await self.client.send_file`

#### Periods & timers

Application has following hardcoded period time parameters:
* Application is grabbing the most popular posts from channels (table "channels") every day at 05:00 UTC (08:00 GMT+3)
* Application is posting 2 times in hour 3 random media from posts (table "posts") in period 06:00 - 20:00 UTC (09:00-23:00 GMT+3)

Those parameters are hardcoded in controller/controller.py 

## Deployment

I used as production environment Docker containers. You can deploy application on your own environment (even on your PC) or you can use instruction below to deploy in Docker.

### Docker network

At first you should create Docker network:
```
docker network create telethon-net
```
And than check network status:
```
docker network inspect telethon-net
```

### Alpine

Alpine Linux is a security-oriented, lightweight Linux distribution based on musl libc and busybox. We will use it to run Python application.
Create new image (alpline + specific dependencies):
```
mkdir alpine-telethon
nano Dockerfile
 ```
Docker file:
```
FROM python:3.8.2-alpine
LABEL maintainer="your_email@gmail.com"
RUN apk add git
RUN apk --update add build-base libffi-dev openssl-dev postgresql-dev gcc python3-dev musl-dev
RUN git init .
RUN git remote add origin <Your repo in Github>.git
RUN git pull origin master
RUN pip install --no-cache-dir -r requirements.txt
 ```
Build image:
```
docker build --no-cache --tag kssadomtsev/alpine-telethon .
 ```
Make sure that new build was created:
```
docker images
 ```

### Postgres
Pull Postgres image from Docker Hub:
```
docker pull postgres:12.3
 ```
Run container in Docker network:
```
docker run --name postgres -e POSTGRES_PASSWORD=***** -e POSTGRES_DB=telethon -d --net telethon-net -e VIRTUAL_HOST=postgres.local postgres:12.3
 ```
Make sure that container is running:
```
docker ps
```
Enter to container shell (if needed):
```
docker exec -it postgres psql -U postgres telethon
```

### Application bot
Create new image:
```
mkdir app-telethon
nano Dockerfile
```
Docker file:
```
FROM kssadomtsev/alpine-telethon
LABEL maintainer="your_email@gmail.com"
ENV MODE dev
ENV api_id *****
ENV api_hash *****
ENV password_db *****
ENV host_db postgres
WORKDIR /usr/src/
RUN git init .
RUN git remote add origin <Your repo in Github>.git
RUN git pull origin master
RUN ls -la
EXPOSE 8002
CMD ["python", "main.py"]
```

Build image:
```
docker build --no-cache -t kssadomtsev/app-telethon .
 ```
Make sure that new build was created:
```
docker images
 ```
Run container in Docker network:
```
docker run --name app-telethon -d --net telethon-net -e VIRTUAL_HOST=app-telethon.local -p 127.0.0.1:8002:8002 kssadomtsev/app-telethon
 ```
View logs:
```
docker logs -f <container ID>
 ```

## Use the Application
Once the application is running either from the IDE or in production user can interact with it.

Currently following commands are supported:
<ol>
<li><strong>list</strong> - display list of monitored channels</li>
<li><strong>add &lt;channel join link&gt;</strong> - add new channel to list of monitored channels . Examples:&nbsp;add <a href="https://t.me/Krololochanne">https://t.me/Krololochannel</a> or: add @grustnie_memi</li>
<li><strong>delete &lt;ID channel&gt;</strong> - delete channel from list by its ID (you can view ID in output list command). Will be deleted all posts from this channel from the database and bot will leave this channel</li>
<li><strong>dump</strong> - delete all posts from the database and collect new posts by actual list. Will be collected 50% most viewed post. Time range: from 21:00 two days ago until 21:00 yesterday (GMT +3).</li>
<li><strong>post</strong> - send to your channel 3 posts that wasn't posted before</li>
<li><strong>start</strong> - start process automate posting to your channel in period 09:00-23:00 (GMT +3) </li>
<li><strong>stop</strong> - stop process automate posting to your channel in period 09:00-23:00 (GMT +3)</li>
<li><strong>stats</strong> - bot statistic</li>
<li><strong>help</strong> - help</li>
</ol>
<p>By default bot one time in day is clearing posts database (at 05:00 UTC or at 08:00 GMT+3) and fill it again by actual channels list. In period 06:00-20:00 UTC (09:00-23:00 GMT+3) bot is sending 3 posts in your channel two times in hour.</p>
<p>Just send or forward bot video, photo or album and it do new post in your channel with your watermark</p>

## Technologies

* Python 3.8
* [Telethon](https://tl.telethon.dev/)
* asyncio
* PostgreSQL
* [SQLAlchemy](https://www.sqlalchemy.org/)
* Docker

## Questions
Please make use of this bot, share your knowledge and adapt it for your needs.

## Contributing
Feedback is highly appreciated. You may open issues, send pull requests or simply contact me.