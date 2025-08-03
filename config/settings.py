import json
import os
from datetime import time

import redis.asyncio as redis
from dotenv import load_dotenv
from for_easy import AIODBP
import _kribrum_credentials

REDISKA = redis.Redis()

load_dotenv()

MODEL_FOLDER = r"D:\gws\ai_model\finetuned_model"
DEEPGLOW_SESSION = r"D:\gws\config\ses.session"

BAN_CONTENT_JSON = json.loads(open(r"D:\bmb\config\BAN_CONTENT.JSON", encoding="utf-8", mode='r').read()) # imported from bmb

# chats, where but must reply on gw
CHAT_IDS_TO_REPLY = [os.getenv("DEEPGLOW_CHATID"),
                     os.getenv("REPLIER1_CHATID")] # me

# deepglow
DINA_SAS_USERNAME = os.getenv("DINA_SAS_USERNAME")
CHAT_ID_GIVESHAREBOT = 1618805558

# bots names
BOTS_DIRECTORY = r"D:\bmb\bots"
BOTS_ARR = [
    name.split(".session")[0].lower()
    for name in os.listdir(BOTS_DIRECTORY)
    if ".session-journal" not in name
]

# TG
TGDATA_DSN = os.getenv("TGDATA_DSN")
TG_AIODBP = AIODBP(TGDATA_DSN)
DATA_BOTS_TABLE = "bots_data"

# gws
GWS_DSN = os.getenv("GWS_DSN")
GWS_AIODBP = AIODBP(GWS_DSN)
VAULT_TABLE = "vault"

# gws
BMB_DSN = os.getenv("BMB_DSN")
BMB_AIODBP = AIODBP(BMB_DSN)
WINNERS_TABLE = "winners"


class BotToken:
    LOGS = os.getenv("LOGS_BOTTOKEN")
    HIVE = os.getenv("HIVE_BOTTOKEN")  # clients
    STORAGE = os.getenv("STORAGE_BOTTOKEN")
    PARSER = os.getenv("PARSER_BOTTOKEN")
    LIST = os.getenv("LIST_BOTTOKEN")

class ChatID:
    LOGS = os.getenv("LOGS_CHATID")
    HIVE = os.getenv("HIVE_CHATID")
    STORAGE = os.getenv("STORAGE_CHATID")
    DEEPGLOW = os.getenv("DEEPGLOW_CHATID")
    PARSER = os.getenv("PARSER_CHATID")


class ThreadID:
    WINNERS = os.getenv("WINNERS_THREAD")


ESCAPE_WORDS_CLEAR = [
    "random1zebot",
    "random",
    "randomgodbot",
    "randomized",
    "givesharebot",
    "giveawaybot",
    "cryptobotru"
]


# tgstat
class TgStat:
    NAME = "tgstat"
    SCHEDULE = time(13, 35)
    ENDPOINT_URL = "https://api.tgstat.ru/posts/search"
    PARAMS = {
        "token": os.getenv("TGSTAT_TOKEN"),
        "limit": 50,
        "hideDeleted": 1,
        "extended": 1,
        "peerType": "channel",
        "minusWords": "\u0440\u043e\u0437\u044b\u0433\u0440\u044b\u0448\u044c \u0431\u0440\u0430\u0432\u043b brazzers porn genshin bts \u0433\u043e\u0434\u043b\u0438 standoff brawl \u043c\u0435\u0433\u0430\u044f\u0449\u0438\u043a \u044e\u0441\u0438 \u0444\u043a \u043f\u0438\u0430\u0440 \u0430\u0432\u0430\u0442\u0430\u0440\u043a\u0430 \u0440\u043e\u0431\u0443\u043a\u0441",
    }
    KEYWORDS = ["https://t.me/Randomized/JoinLot",
             "https://t.me/Random/JoinLot",
             "https://t.me/Random1zebot/JoinLot",

             "https://t.me/GiveShareBot/app",

             "https://t.me/tggrowbot/windowGiveaway",

             "https://t.me/CryptoBot/app",
             "https://t.me/best_contests_bot",
             "https://t.me/concubot/pass",
             "http://t.me/GiveawayLuckyBot/app",
             "https://t.me/randombeast_bot/devapp",
             "https://t.me/giveaway_random_bot",
             "https://t.me/BestRandom_bot",

             "розыгрыш",
             "конкурс",
             "рандомайзер",
             "участвую",
             "участвовать",
             "призовых",
             "выиграть",
             "победители",
             "победителей",
             "счастливчик"]


# tgfind
class TgFind:
    NAME = "tgfind"
    SCHEDULE = time(20, 00)
    ENDPOINT_URL = "https://tgfind.org/search"
    PARAMS = {"period": "d1"}
    KEYWORDS =  ["розыгрыш",
                  "конкурс",
                  "выиграть",
                  "рандомайзер",
                  "участв",
                  "участник",
                  "подпис"]

# linkbaza
class LinkBaza:
    NAME = "linkbaza"
    SCHEDULE = time(19, 00)
    ENDPOINT_URL = "https://linkbaza.com/search/posts"
    PARAMS = {"ajax": 1}
    KEYWORDS = ["розыгрыш",
                "конкурс",
                "выиграть",
                "рандомайзер",
                "участв",
                "участник",
                "подпис"]

# kribrum
class Kribrum:
    NAME = "kribrum"
    SCHEDULE = time(20, 38)
    ENDPOINT_AUTH = "https://kribrum.io/api/v1/auth/login"
    ENDPOINT_SEARCH = "https://kribrum.io/api/v1/search"
    ENDPOINT_TEXT = "https://kribrum.io/api/v1/search/post"

    LOGINS_CREDENTIALS = _kribrum_credentials.LOGINS_CREDENTIALS

    PAYLOAD = {
        "author": "",
        "platform": "telegram.org",
        "time": "3days",
        "order": "ptime",
        "dup": 0,
    }

    KEYWORDS = ["розыгрыш",
                "конкурс",
                "выиграть",
                "рандомайзер",
                "участв",
                "участник",
                "подпис"]


class TgParser:
    NAME = "tgparser"
