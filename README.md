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


## Technologies

* Python 3.8
* [Telethon](https://tl.telethon.dev/)
* asyncio
* PostgreSQL
* [SQLAlchemy](https://www.sqlalchemy.org/)
* Docker