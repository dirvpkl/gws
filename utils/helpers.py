import sys
import json
import logging
import asyncio
import aiohttp
import requests
from cloudscraper import create_scraper
from requests.models import Response

from utils import pattern_builder as PB

from config.enums import GWProvidersPostTags as GWPPT

from config.settings import BotToken, ChatID

from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault


class ResponseWrapper:
    def __init__(self, res, text, status):
        self._res = res
        self._text = text
        self._status = status

    def json(self):
        return self._res

    def text(self):
        return self._text

    def status(self):
        return self._status


class CFScraper: # FROM BMB

    def __init__(self):
        self.scraper = create_scraper()

    async def get(self, url, data=None, params=None, headers=None) -> Response:
        def blocking_call():
            resp = self.scraper.get(url=url, json=data, params=params,
                                    headers=headers, timeout=120)
            return resp

        response = await asyncio.to_thread(blocking_call)
        return response

    async def post(self, url, data=None, json=None, params=None, headers=None) -> Response:
        def blocking_call():
            resp = self.scraper.post(url=url, json=json, data=data, params=params,
                                     headers=headers, timeout=120)
            return resp

        response = await asyncio.to_thread(blocking_call)
        return response


async def send_request(url, payload=None, params=None, headers=None, proxy=None,  method: str="POST", timeout=60) -> ResponseWrapper:

    max_retries = 10
    retry_delay = 5

    timeout = aiohttp.ClientTimeout(total=timeout, connect=timeout/2)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(max_retries):
            try:
                match method:
                    case "GET":
                        async with session.get(url, params=params, timeout=timeout, headers=headers, proxy=proxy) as response:

                            try:
                                res = await response.json()
                            except aiohttp.ClientError:
                                res = None

                            text = await response.text()
                                
                            status = response.status

                            break
                            
                    case "POST":
                        async with session.post(url, params=params, json=payload, timeout=timeout, headers=headers,
                                                proxy=proxy) as response:
                            try:
                                res = await response.json()
                            except aiohttp.ClientError:
                                res = None

                            text = await response.text()

                            status = response.status

                            break

            except asyncio.TimeoutError:
                logging.warning(f"Таймаут при запросе {url}")
            except aiohttp.client_exceptions.ClientConnectorError:
                logging.warning(f"Ошибка соединения с {url}, попытка {attempt + 1}/{max_retries}: connectionerror")
            except aiohttp.ClientError as e:
                logging.warning(f"Ошибка соединения с {url}, попытка {attempt + 1}/{max_retries}: {e}")
            except UnicodeDecodeError:
                logging.error("UnicodeEncodeError proc")
                raise
            except Exception as e:
                logging.error(f"Неожиданная ошибка при запросе {url}: {e}", exc_info=True)
                break

            if attempt < max_retries - 1:  # Не ждем после последней попытки
                await asyncio.sleep(retry_delay * (attempt + 1))  # Экспоненциальная задержка

    return ResponseWrapper(res, text, status)

async def tg_notify(text, token, chat_id, thread_id=None, kb=None, attached_photo=None, attached_file=None):
    logging.debug(f"Notifying with '{text}' to {chat_id}")
    files = None
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if attached_file:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        del payload["text"]
        payload["caption"] = text
        attached_file.seek(0)
        files = {
            "document": ("file", attached_file, "application/octet-stream")
        }

    if attached_photo:
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        del payload["text"]
        payload["caption"] = text
        attached_photo.seek(0)
        files = {
            "photo": ("file", attached_photo, "image/jpeg")
        }

    if thread_id:
        payload["message_thread_id"] = str(thread_id)

    if kb:
        keyboard = {
            "inline_keyboard": kb
        }
        payload["reply_markup"] = json.dumps(keyboard)

    # bool -> str для payload
    payload = {k: str(v) if isinstance(v, bool) else v for k, v in payload.items()}
    while 1:
        try:
            async with aiohttp.ClientSession() as session:
                if files:
                    data = aiohttp.FormData()
                    for key, value in payload.items():
                        data.add_field(key, value)
                    for key, (field_name, file, content_type) in files.items():
                        data.add_field(key, file, filename=getattr(file, "name", "file"), content_type=content_type)
                    async with session.post(url, data=data) as response:
                        response_json = await response.json()
                else:
                    async with session.post(url, data=payload) as response:
                        response_json = await response.json()
                break

        except aiohttp.client_exceptions.ClientConnectorError:
            logging.warning(f'Ошибка соединения tg_notify')

    return response_json


def tg_notify_synchronous(text, token, chat_id, thread_id=None, files=None):
    logging.debug(f"Notifying with '{text}' to {chat_id}")
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if thread_id:
        payload["message_thread_id"] = str(thread_id)

    # Приводим булевы значения к строке
    payload = {k: str(v) if isinstance(v, bool) else v for k, v in payload.items()}

    if files:
        data = {k: str(v) for k, v in payload.items()}
        multipart_files = {
            key: (getattr(file, "name", "file"), file, content_type)
            for key, (field_name, file, content_type) in files.items()
        }
        response = requests.post(url, data=data, files=multipart_files)
    else:
        response = requests.post(url, data=payload)

    try:
        response_json = response.json()
    except Exception as e:
        logging.error(f"Failed to parse JSON: {e}")
        response_json = {"error": str(e), "response_text": response.text}

    print(response_json)
    return response_json



async def send_storage_message(v: VaultObject, from_file='deepglo_w_parser') -> dict:

    # from_file is not used

    url = f"https://api.telegram.org/bot{BotToken.STORAGE}/sendMessage"

    if len(v.text) > 3200:
        v.text = v.text[:3200] + '…'


    message_text = (
f"━━━━━━━━━━━━━━━━━━━━━━\n"
f"📌 QUEUE ID:\n"
f"      {v.queue_id}\n"
f"━━━━━━━━━━━━━━━━━━━━━━\n\n"

f"📝 TEXT:\n"
f"{v.text}\n\n"

f"━━━━━━━━━━━━━━━━━━━━━━\n"
f"📡 CHANNEL NICK:\n"
f"      {f"@{v.channel_nick}" or '—'}\n"
f"🔗 MESSAGE LINK:\n"
f"      {PB.link_build(message_id=v.message_id, channel_nick=v.channel_nick, channel_id=v.channel_id)}\n"
f"━━━━━━━━━━━━━━━━━━━━━━\n\n"

f"🧩 CONDITIONS:\n" +
("\n".join([
    f"      ➤ {'@' + cond if 't.me' not in cond and '@' not in cond else cond}"
    for cond in v.conditions
]) if v.conditions else "      —"
 ) + "\n\n"

f"━━━━━━━━━━━━━━━━━━━━━━\n"
f"🤖 GW PROVIDER:\n"
f"      #{GWPPT[v.gw_provider]}\n"
f"📂 FROM SOURCE:\n"
f"      #{from_file}\n"
f"━━━━━━━━━━━━━━━━━━━━━━"



)

    keyboard = {"inline_keyboard": [[{"text": "🔓 Активировать клавиатуру", "callback_data": f"activate_{v.queue_id}"}]]}

    payload = {"chat_id": ChatID.STORAGE, "text": message_text, "reply_markup": json.dumps(keyboard)}

    res = await send_request(url, payload=payload)
    while res.status() != 200:
        res = await send_request(url, payload=payload)

    return res.json()


def __setup_custom_logger__(name, filename):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not logger.hasHandlers():
        file_handler = logging.FileHandler(f"logs/{filename}.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
