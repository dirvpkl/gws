from datetime import datetime
from asyncpg.exceptions import UniqueViolationError

from telethon.errors.rpcerrorlist import ChannelPrivateError
from telethon.tl import types

from utils.helpers import tg_notify
from utils.helpers import __setup_custom_logger__

from utils import pattern_builder as PB

from utils.module_parser import get_nicknames
from utils.module_parser import prepare_vault_object

from config.enums import GWProviders as GWP
from config.enums import GWProvidersKeywords as GWPK

from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
DBW = D.TelegramData.Winners
TBDB = D.TelegramData.BotsData
TDBDKeys = D.TelegramData.BotsData.Keys

from config.settings import DATA_BOTS_TABLE
from config.settings import CHAT_ID_GIVESHAREBOT
from config.settings import CHAT_IDS_TO_REPLY
from config.settings import BotToken, ChatID, ThreadID
from config.settings import TgParser

from config.settings import WINNERS_TABLE
from config.settings import GWS_AIODBP
from config.settings import VAULT_TABLE
from config.settings import BOTS_ARR
from config.settings import TG_AIODBP

logging = __setup_custom_logger__(__name__, "tg_parser_utils")

bots_dict = {}
async def initialize_bots_dict():
    for bot_iter in BOTS_ARR:
        raw_doc = await TG_AIODBP.read(DATA_BOTS_TABLE, bot_iter, TDBDKeys.BOTNAME) # change to enums
        doc = TBDB(**raw_doc)
        bots_dict[doc.bot_str_id] = [bot_iter, doc.bot_str_id]

# --------------------------------------------------
async def process_message(message, client):
    gw_provider = GWP.Unknown

    original_message = message
    original_message_id = message.id
    original_chat_id = message.chat_id
    original_username = None

    if original_message.fwd_from:
        original_message_id = message.fwd_from.channel_post
        if isinstance(original_message.fwd_from.from_id, types.PeerUser):
            original_chat_id = message.fwd_from.from_id.user_id
        else:
            if message.fwd_from.from_id is None:
                return  # idk bug maybe
            original_chat_id = message.fwd_from.from_id.channel_id

        original_message = message.fwd_from

    queue_id = PB.queue_id(original_chat_id, original_message_id)

    # поиск по гвскам (есть ли в сообщении ссылка какая-то)
    if message.reply_markup:
        if message.reply_markup.rows[0].buttons[0]:
            if hasattr(message.reply_markup.rows[0].buttons[0], "url"):
                btn_url = message.reply_markup.rows[0].buttons[0].url
                gw_provider = GWP.Unknown
                for gwpk, gwpv in GWPK.items():
                    if gwpk in btn_url.lower():
                        gw_provider = gwpv
                        break
        else:
            logging.warning(f"не нашел гвску (rm): {queue_id}")

    else:
        if message.chat_id == CHAT_ID_GIVESHAREBOT:
            return
        for gwpk, gwpv in GWPK.items():
            if gwpk in message.text.lower():
                gw_provider = gwpv
                break
        else:
            logging.warning(f"не нашел гвску (text): {queue_id}")
            return

    # ------------------
    # reply gw in dm
    if message.chat_id in CHAT_IDS_TO_REPLY:
        r = await GWS_AIODBP.read(VAULT_TABLE, val=queue_id, key=VaultKeys.QUEUE_ID)
        if r is not None:
            await client.send_read_acknowledge(message.chat_id)
            await client.send_message(message.chat_id, f"<code>{queue_id}</code>", parse_mode="HTML")
            return
        else:
            await client.send_message(
                message.chat_id,
                f"добавление розыгрыша: <code>{queue_id}</code>",
                parse_mode="HTML",
            )
    # ------------------

    # getting all urls from message
    additional_urls = []
    if message.entities is not None:
        for k in message.entities:
            if isinstance(k, types.MessageEntityTextUrl):
                if "t.me" in k.url:
                    additional_urls.append(k.url)

    # --- GETTING USERNAME

    try:
        ent = await client.get_entity(original_chat_id)
        if ent.username:
            original_username = ent.username
        elif ent.usernames:
            for j in ent.usernames:
                if j.active is True:
                    original_username = j.username
                    break

    except ValueError:
        return  # no usernames on this channel
    except ChannelPrivateError:
        return

    # --- creating obj

    obj_vault = VaultObject(
        queue_id=queue_id,
        text=message.text,
        date_post=original_message.date.replace(tzinfo=None),
        date_add=datetime.now(),
        date_predicted=None,
        channel_nick=original_username,
        channel_id=original_chat_id,
        message_id=original_message_id,
        conditions=get_nicknames(message.text),
        gw_provider=gw_provider,
        ai={},
        storage_message_id=None,
        parsing_source=TgParser.NAME,
    )

    prepared_obj = await prepare_vault_object(obj_vault, TgParser.NAME)
    try:
        logging.debug(f"{prepared_obj.queue_id}")
        await GWS_AIODBP.append(VAULT_TABLE, prepared_obj.__dict__)
    except UniqueViolationError:
        logging.debug(f"{queue_id} - queue_id already exists in database")


async def check_message_winner(event, won_messages):
    message = event.message
    chat_id = event.chat_id
    message_text = message.text.lower()

    for _, bot_data in bots_dict.items():
        k_username = bot_data[0].lower()  # Имя пользователя бота в нижнем регистре
        k_id = bot_data[1]
        do_post = False  # Сбрасываем флаг для каждой записи бота

        unique = PB.win_message(chat_id, message.id, k_username)
        if unique in won_messages:
            continue

        # Создаем сообщение для отправки
        win_obj = DBW(win_id=unique,
                      bot=k_username,
                      channel_name=None,
                      channel_nick=None,
                      channel_id=chat_id,
                      message_id=message.id,
                      prize=None,
                      description=None,
                      status=DBW.Status.NOT_SEEN,
                      date_won=datetime.now(),
                      winners_message_id=None,
                      date_received=None,
                      link_message=None)

        if hasattr(message, "chat"):

            if hasattr(message.chat, "title"):
                win_obj.channel_name = message.chat.title

            if hasattr(message.chat, "username"):
                win_obj.channel_nick = message.chat.username

        post_link = PB.link_build(message_id=win_obj.message_id, channel_id=win_obj.channel_id,
                                  channel_nick=win_obj.channel_nick)
        win_obj.link_message = post_link

        win_msg = f"""🟦 WIN - @{k_username}
channel_name: {win_obj.channel_name}
channel_nick: {win_obj.channel_nick}
channel_id: {win_obj.channel_id}
message_id: {win_obj.message_id}
link: {post_link}"""

        if any(keyword in message_text for keyword in bot_data):
            logging.info(f"detected bot {k_username} in message {chat_id}")
            do_post = True

        # Проверка сущностей сообщения
        if message.entities:
            for me in message.entities:
                if isinstance(me, types.MessageEntityMentionName):
                    if str(me.user_id) == k_id:
                        logging.info(f"detected bot {k_username} in ME {chat_id}")
                        do_post = True

                if isinstance(me, types.MessageEntityTextUrl):
                    if any(keyword in me.url for keyword in bot_data):
                        logging.info(f"detected bot {k_username} in EURL {chat_id}")
                        do_post = True

        # Отправка сообщения в случае совпадения
        if do_post:
            won_messages.append(unique)

            doc = await TG_AIODBP.read(table=WINNERS_TABLE, val=win_obj.link_message, key=DBW.Keys.LINK_MESSAGE)

            if not doc or doc.get(DBW.Keys.BOT) != k_username:

                res = await tg_notify(
                    text=win_msg,
                    token=BotToken.HIVE,
                    chat_id=ChatID.HIVE,
                    thread_id=ThreadID.WINNERS,
                )

                win_obj.winners_message_id = res["result"]["message_id"]

                await TG_AIODBP.append(table=WINNERS_TABLE, obj=win_obj.__dict__)

