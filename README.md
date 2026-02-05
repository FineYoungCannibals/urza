# urza
a server client architecture for distributed tasking

urza/
├── core/                       # BUSINESS LOGIC LAYER
│   ├── telegram_client.py      # Domain: Telegram operations
│   ├── bot_manager.py          # Domain: Bot lifecycle & orchestration
│   └── spaces_client.py        # Domain: Storage operations
│
├── db/                         # DATA PERSISTENCE LAYER
│   ├── models.py               # ORM: Bot, Task, BotKey tables
│   └── database.py             # Connection & session management
│
├── api/                        # PRESENTATION LAYER
│   ├── server.py               # FastAPI app setup
│   ├── schemas.py              # Pydantic: Request/response validation
│   └── routes/
│       ├── bots.py             # Endpoints: /api/bot/*
│       └── tasks.py            # Endpoints: /api/task/*
│
├── cli/                        # PRESENTATION LAYER (alternate)
│   └── shell.py                # cmd2: Interactive commands
│
└── config/
    ├── settings.py             # Environment & paths
    └── display.py              # Banners, formatting



### Functionality
* Login to TG as a USER
* Create Bots
  - DO Token needed for creating DO Spaces Keys
  - Creates bot through TG api, creates a bot token for your enrollment
  - each bot gets a unique urza id and key, the urza key is used to authenticate messages from bots, the urza server processes messages from bots and checks the authentication
 Revoke a bot's tokens
    - resets TG token, you will have to redeploy the bot with hte new token
    - spaces token functionality? 
* Urza is dumb to downstream processing tasks on proof of work
     - if you want downstream processing, automation should be written to monitor a specific folder in your s3 bucket to process the files that drop there
     - Urza is only going to mark tasks as complete in it's own data store

### ENV VAR REQUIREMENTS 

**how do i find my channel id?**
```
The easiest way:

Just send your invite link to your private channel to @username_to_id_bot (https://t.me/username_to_id_bot) bot. It will return its ID. The simplest level: maximum! :)

PS. I am not an owner of this bot.

PS 2. the Bot will not join your group, but to be sure in security. Just revoke your old invitation link if it is matter for you after bot using.

### Testing
```
set -a 
source .env
set +a 

uv run tests/test_telegram.py
```


### Docker 
```
docker network create --driver bridge dev_lab
```

### Running for the first time
Using alembic to prepare the database: 

``` 
uv add alembic && \
uv run alembic init almebic && \ # from the project root
# make edits to the env.py file
# - import your settings that define your datasource url
# - import your db.models Base object
# - set your target_metadata variable to Base's metadata property
# - set your sqlalchemy url key
# - config.set_main_option("sqlalchemy.url", settings.your_sync_database_url_property)
uv run alembic upgrade head
```