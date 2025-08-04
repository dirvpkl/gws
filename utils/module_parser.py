import json
import re
import logging
import aiohttp
import asyncio
import traceback
from bs4 import BeautifulSoup
from typing import Dict, Optional
from utils.clean_markdown import clean_text

# ---
from config.settings import ESCAPE_WORDS_CLEAR
from config.settings import REDISKA
# ---
from config.dataclasses_ import Commands as C
from config.dataclasses_ import Database as D
from utils.date_finder import find_date_obj

VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
# ---
from config.enums import GWProviders as GWP
from config.enums import GWProvidersKeywords as GWPK
# ---
from utils.helpers import send_request
# ---
from utils.helpers import tg_notify
# ---
from config.settings import BotToken, ChatID, ThreadID
# ---
from config.enums import Ports

def has_cyrillic(text):
    return bool(re.search('[а-яА-Я]', text))


def get_nicknames(text, additional=None):

    if not text:
        return None

    pattern_at = r"@[A-Za-z0-9_]+"
    pattern_link = r"https://t\.me/[A-Za-z0-9_]+"

    matches_at = re.findall(pattern_at, text.replace(')', ' ').replace('(', ' '))
    matches_link = re.findall(pattern_link, text.replace(')', ' ').replace('(', ' '))

    conds = list(set(matches_at + matches_link))
    if additional:
        conds = list(set(conds + additional))

    conds = list(set([i for i in conds if i.replace('@', '').lower() not in ESCAPE_WORDS_CLEAR]))
    return conds


def get_gw_provider_from_text(text, default: GWP=GWP.Unknown) -> GWP:
    for gw_key, gw_value in GWPK.items():
        if gw_key in text.lower():
            logging.debug(f"set {gw_key} for text: {text.lower()}")
            return gw_value
    else:
        return default


def _analyze_message_for_gw(req_text, channel_nick, message_id) -> GWP:
    logging.debug(f"checking message {channel_nick} {message_id} on gw")
    soup = BeautifulSoup(req_text, "lxml")
    elem = soup.find(attrs={'data-post': f'{channel_nick}/{message_id}'})
    # NO SUCH MESSAGE
    if not elem:
        return GWP.Unknown
    # NO SUCH MESSAGE

    # text search
    btn = elem.find("div", class_="tgme_widget_message_inline_row")
    if not btn:
        # NO TEXT IN MESSAGE
        txt_class = elem.find("div", class_="tgme_widget_message_text")
        if not txt_class:
            logging.warning(f"text nor button doesn't exists: {channel_nick} {message_id}")
            return GWP.Unknown
        # NO TEXT IN MESSAGE

        gw_provider = get_gw_provider_from_text(txt_class.text)
        return gw_provider
    # text search

    # button search
    inline_btn = btn.find("a", class_="tgme_widget_message_inline_button")
    if "url_button" in inline_btn.attrs["class"]:
        hrefurl = inline_btn["href"]
        if "t.me/" not in hrefurl:
            return GWP.Unknown

        gw_botname = hrefurl.split("t.me/")[1].split('/')[0].lower()

        if gw_botname in GWPK.keys():
            return GWPK[gw_botname]
        else:
            logging.warning(f'known button nor url in text was found: {channel_nick} {message_id}')
            return GWP.Unknown
    # button search
    else:
        return GWP.Callback


async def get_gw_provider_from_channel(channel_nick: str, message_id: int) -> GWP:

    url = f'https://t.me/s/{channel_nick}/{message_id}' # DIFFERENT FROM PB.LINK! (/s/)

    try:
        resp = await send_request(url, method="GET")

        if resp.status() == 200:
            return _analyze_message_for_gw(resp.text(), channel_nick, message_id)

    except UnicodeDecodeError:
        return GWP.Unknown

    return GWP.Unknown


def _clean_text(clean) -> str:
    clean = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r'\1', clean)  # Удаляем [link](url)
    clean = re.sub(r"[\*_\`\#\>\!\[\]\(\)]", '', clean)  # Удаляем *, _, `, #, > и т.д.
    clean = re.sub(r"\s+", ' ', clean).strip()  # Удаляем лишние пробелы
    return clean


async def get_ai(text: str) -> Optional[Dict]:
    try:
        ai_port = await REDISKA.get(Ports.AI_SERVER)
        ai_port = int(ai_port)
        ai = await send_request(url=f"http://localhost:{ai_port}",
                                method="POST",
                                payload=C.AI.Request(context=_clean_text(text)).__dict__)
        ai = json.dumps(ai.json())

    except aiohttp.client_exceptions.ClientConnectorError:
        ai = None

    except Exception as e:
        ai = None
        await tg_notify(text=f"ERROR WITH AI_SERVER: {e}",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)
        traceback.print_exc()
    return ai


async def prepare_vault_object(item: VaultObject, parsing_source: str) -> Optional[VaultObject]: # takes some time

    soup = BeautifulSoup(item.text, "lxml")
    for br in soup.find_all("br"): # IMPORTANT BEFORE THE GET_TEXT METHOD
        br.replace_with("\n") # IMPORTANT BEFORE THE GET_TEXT METHOD
    preproc_text = soup.get_text()
    ready_text = clean_text(preproc_text)

    item.text = ready_text

    # DATE PREDICTED
    if not item.date_predicted:
        item.date_predicted = await asyncio.to_thread(find_date_obj, item.text, item.date_post)

    # GWP
    if item.gw_provider == GWP.Unknown:
        item.gw_provider = await get_gw_provider_from_channel(item.channel_nick,
                                                              item.message_id)

    logging.debug(f'ADDING KEY IN DB {item.queue_id}')

    # AI
    item.ai = await get_ai(item.text)

    # # POSTING

    # result_message = await send_storage_message(item, parsing_source)
    # item.storage_message_id = result_message["result"]["message_id"]

    return item
