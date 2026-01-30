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

### Testing
```
set -a 
source .env
set +a 

uv run tests/test_telegram.py
```