# Async Cinema Searcher Bot

This project implements [an asynchronous Telegram bot](https://docs.aiogram.dev/en/latest/) for searching movies.

Initial request (keywords) is made in `google` with additional word _imdb_.
Then the most frequent `movie_id` is selected from response using [Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).
The next step is collecting data associated with movie. For this goal is applied [IMDB API](https://developer.imdb.com/).
Finally, request and movie title are saved in database. All requests and replies for messages support concurrency.

The bot supports the history of requests by using [SQLite](https://www.sqlite.org/index.html).

## Getting started

### Prerequisites

It is strongly recommended to use Python 3.10 and above versions.

The script requires libraries `aiogram` and `aiohttp` for concurrent execution.
Necessary packages and versions can be installed with the following command
```bash
pip install -r requirements.txt
```

### Usage

After cloning the repository and installing requirements two tokens are needed.

- Token for Telegram bot. It can be taken from [BotFather](https://t.me/BotFather).
- Token for IMDb API. It will be available after registration [here](https://imdb-api.com/).

Then tokens are placed into environment variables
```bash
export BOT_TOKEN=<your bot token>
export IMDB_TOKEN=<your imdb token>
python3 bot.py
# or simpler
BOT_TOKEN=<your bot token> IMDB_TOKEN=<your imdb token> python3 bot.py
```

## Example

Possible sequence of messages (_U_: _user_, _B_ _bot_)
```text
    U: /start
    B: [welcome message]
    U: some keywords
    B: [title, poster, duration, description, links, etc.]
    U: /history
    B: [history of requests]
    U: /stats
    B: [statistics of requests]
    U: /delete request
    B: Deleted 2 items. # request has been deleted from the database
    U: /link title year
    B: [link to movie description on IMDb]
    U: /info movie_id (or link)  # generating description without searching by keywords
    B: [the same with 4th line]
```

*Note*: History depends on user id (independent for everyone). It is saved on HDD and 
can be deleted only by `/delete` and `/clear` commands.

During the next several months bot is available [here](https://t.me/CinemaDescriptorBot).
