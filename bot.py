import os
import typing as tp
import re
import json
import time
import logging
from enum import Enum

import aiohttp
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from bs4 import BeautifulSoup
from collections import OrderedDict, Counter
from yarl import URL

from database import (add_request, make_stat, make_history, load_database,
                      clear_database, delete_request, imdb_link)


logging.basicConfig(format='[%(asctime)s - %(levelname)s] %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

bot = Bot(token=os.environ['BOT_TOKEN'])
IMDB_TOKEN = os.environ['IMDB_TOKEN']
dp = Dispatcher(bot)


class RequestType(Enum):
    ID = 0,
    REF = 1


async def sorry_message(message: types.Message, start: float) -> None:
    logger.info(f'Time of search: {time.time() - start:.2f} s')
    await message.reply('Sorry, I have not found any appropriate film.')


async def warning_message(message: types.Message, func_name: str, args: str) -> None:
    await message.reply(f'Command /{func_name} requires arguments {args}', parse_mode='Markdown')


def check_correct(url: str) -> bool:
    try:
        yarl_url: URL = URL(url)
        if not yarl_url.scheme or yarl_url.scheme not in ['http', 'https']:
            return False
        return yarl_url.host is None or 'google' not in yarl_url.host
    except Exception as err:
        logger.warning(f'Got error in film link {url}, {err = }')
        return False


async def make_query(query: str, request_type: RequestType) -> tp.Optional[str]:
    if request_type == RequestType.ID:
        request: str = f'https://www.google.com/search?q={query + "%20imdb"}'
    elif request_type == RequestType.REF:
        request = f'https://www.google.com/search?q={query + "%20watch%20online"}&tbm=vid'
    else:
        logger.warning(f'Unknown {request_type = }')
        return None

    headers = {'User-Agent': ''}
    async with aiohttp.ClientSession() as session:
        async with session.get(request, headers=headers) as response:
            text: BeautifulSoup = BeautifulSoup(await response.text(), features='lxml')
            try:
                refs = [el['href'].split('=')[1].split('&')[0] for el in text.find_all('a') if
                        el['href'].startswith('/url')]
                if request_type == RequestType.ID:
                    for ref in refs:
                        elements = ref.split('/')
                        for elem in reversed(elements):
                            if elem.startswith('tt') and not re.sub('^[0-9]+', '', elem[2:]):
                                return elem
                elif request_type == RequestType.REF:
                    result: str = ""
                    refs = [ref for ref in refs if check_correct(ref)]
                    for index, (ref, _) in enumerate(sorted(Counter(refs).items(), key=lambda el: -el[1])):
                        result += f'[#{index + 1}]({ref}) '
                    return result
            except Exception as e:
                logger.warning(f'While parsing {request = } get error {e}')
    return None


class Filter:
    def __init__(self, names: OrderedDict[str, str | OrderedDict[str, str]]):
        self._names = names

    def __call__(self, info: dict[str, str | dict[str, str] | None]):
        result: str = ''
        if 'image' in info:
            info['image'] = f'[image]({info["image"]})'
        for name, value in self._names.items():
            if info[name] is None:
                continue
            if isinstance(value, str):
                assert isinstance(info[name], str), f'Expected str, get {type(info[name])}'
                result += f'{value}: {info[name]}\n'
            elif isinstance(value, dict):
                assert isinstance(info[name], dict), f'Expected dict, get {type(info[name])}'
                for k, v in value.items():
                    if info[name][k] is not None and info[name][k]:
                        result += f'{v}: {info[name][k]}\n'
            else:
                logger.warning(f'Unknown value type {type(value)} for {name = }')
        return result


feature_filter: Filter = Filter(OrderedDict((
    ('title', 'Title 🎞'),
    ('year', 'Year 📅'),
    ('image', 'Poster 🌆'),
    ('runtimeStr', 'Duration 🕥'),
    ('plot', 'Small description 📝'),
    ('links', 'Links 🏴‍☠'),
    ('genres', 'Genres 🔫'),
    ('stars', 'Stars 🤩'),
    ('imDbRating', 'IMDb Rating 🔟'),
    ('languages', 'Languages 🇬🇧'),
    ('boxOffice', OrderedDict((
        ('budget', 'Budget 💸'),
        ('cumulativeWorldwideGross', 'Box office in the world 💰'))))
)))


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message) -> None:
    await message.reply('''
Hi, I am Cinema Bot!
I will help you to find the most appropriate movies for you.

Please, type keywords, and I will show the closest film for them.
The response contains a poster, description, rating, and other interesting details.

*Commands*
/history - get a list of previous requests
/stats - group history by equal films
/link _title_ _year_ - get IMDb link
/info _link_ (or _id_) - get info about movie by its link (should contain _id_) or by _id_ (always starts with tt)
/delete _request_ - delete all results associated with request
/clear - clear history
    ''', parse_mode='Markdown')


@dp.message_handler(commands=['history'])
async def table(message: types.Message) -> None:
    await message.reply(make_history(str(message.from_id)))


@dp.message_handler(commands=['clear'])
async def clear(message: types.Message) -> None:
    del_number: int = clear_database(str(message.from_id))
    await message.reply(f'Cleared {del_number} {"item" if del_number == 1 else "items"}.')


@dp.message_handler(commands=['delete'])
async def delete(message: types.Message) -> None:
    tokens: list[str] = message.text.split(' ', 1)
    if len(tokens) != 2:
        return await warning_message(message, 'delete', '(_request_)')
    del_number: int = delete_request(str(message.from_id), tokens[1])
    await message.reply(f'Deleted {del_number} {"item" if del_number == 1 else "items"}.')


@dp.message_handler(commands=['stats'])
async def stat(message: types.Message) -> None:
    await message.reply(make_stat(str(message.from_id)))


@dp.message_handler(commands=['link'])
async def imdb(message: types.Message) -> None:
    tokens: list[str] = message.text.split(' ', 1)
    if len(tokens) != 2:
        return await warning_message(message, 'link', '(_film_ _year_)')
    await message.reply(imdb_link(str(message.from_id), tokens[1]))


@dp.message_handler(commands=['info'])
async def get_info(message: types.Message) -> None:
    tokens: list[str] = message.text.split(' ', 1)
    if len(tokens) != 2:
        return await warning_message(message, 'info', '(_link_ or _id_)')
    start = time.time()
    text: str = tokens[1]
    movie_id: str

    try:
        if text.startswith('tt'):
            movie_id = text
        else:
            tokens = text.split('/')
            movie_id = [token for token in tokens if token.startswith('tt')][-1]
        request = f'https://imdb-api.com/en/API/Title/{IMDB_TOKEN}/' + movie_id
        async with aiohttp.ClientSession() as session:
            async with session.get(request) as full_response:
                data = json.loads(await full_response.text())
                for nm in ['title', 'year']:
                    if data[nm] is None:
                        data[nm] = ""
                film_info: str = data['title'] + ' ' + data['year']
                data['links'] = await make_query(film_info, RequestType.REF)
                logger.info(f'Approximate time of search: {time.time() - start:.2f} seconds')
                await message.reply(feature_filter(data), parse_mode='Markdown')
    except Exception as e:
        logger.warning(f'While parsing get_info {text} get error = {e}')
        await sorry_message(message, start)


@dp.message_handler()
async def answer(message: types.Message) -> None:
    start: float = time.time()
    msg_text: str = re.sub('[^a-zA-Zа-яА-Я0-9 ]+', '', message.text.strip())
    lang: str = 'ru' if bool(re.search('[а-яА-Я]', msg_text)) else 'en'

    movie_id: str | None = await make_query(msg_text, RequestType.ID)
    cell: tuple[str, str, str] = (str(message.from_id), movie_id, message.text)

    if movie_id is None:
        await sorry_message(message, start)
        return

    logger.info(f'Language: {lang}, text: {msg_text}, movie_id: {movie_id}')

    request = f'https://imdb-api.com/{lang}/API/Title/{IMDB_TOKEN}/' + movie_id
    async with aiohttp.ClientSession() as session:
        async with session.get(request) as full_response:
            data = json.loads(await full_response.text())
            for nm in ['title', 'year']:
                if data[nm] is None:
                    data[nm] = ""
            film_info: str = data['title'] + ' ' + data['year']
            data['links'] = await make_query(film_info, RequestType.REF)
            logger.info(f'Approximate time of search: {time.time() - start:.2f} seconds')
            add_request(cell + (film_info, -start))
            await message.reply(feature_filter(data), parse_mode='Markdown')


if __name__ == '__main__':
    load_database()
    executor.start_polling(dp)
