import asyncio
import json
import socket

from telethon import types
from telethon.sync import TelegramClient, events
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors.rpcerrorlist import ChannelsTooMuchError

from config.settings import CHAT_ID_GIVESHAREBOT
from config.settings import REDISKA
from config.settings import DINA_SAS_USERNAME
from config.settings import DEEPGLOW_SESSION
from config.settings import BAN_CONTENT_JSON

from config.enums import GWProvidersKeywords as GWPK
from config.enums import Ports
from config.enums import Tasks

from config.settings import BotToken, ChatID, ThreadID

from utils.helpers import tg_notify
from utils.helpers import __setup_custom_logger__

from config.dataclasses_ import Commands as C

from utils.tg_parser_utils import check_message_winner, process_message, initialize_bots_dict

logging = __setup_custom_logger__(__name__, "tg_parser")

won_messages = []

client = TelegramClient( # RANDOM PLACEHOLDER
    DEEPGLOW_SESSION, # RANDOM PLACEHOLDER
    api_hash="zxc", # RANDOM PLACEHOLDER
    api_id=1, # RANDOM PLACEHOLDER
    system_version="4.16.30-vxCUSTOM" # RANDOM PLACEHOLDER
)

async def handle_server(reader, writer):

    addr = writer.get_extra_info("peername")
    logging.debug(f"Подключился клиент {addr}")

    while True:
        raw_data = await reader.read(16384)
        data = json.loads(raw_data.decode())
        if not raw_data: break

        logging.debug(f"message_body is {data}")

        match data[Tasks.Task]:

            case Tasks.Subscribe:
                task_obj = C.DeepGlow.Subscribe(**data)
                channel_nick = task_obj.channel_nick
                try:
                    if "+" in channel_nick:
                        if "t.me/" in channel_nick:
                            channel_nick = channel_nick.split("t.me/")[1]
                        await client(ImportChatInviteRequest(channel_nick.replace("+", "")))
                    elif "joinchat" in channel_nick:
                        if "t.me/joinchat/" in channel_nick:
                            channel_nick = channel_nick.split("t.me/joinchat/")[1]
                        await client(ImportChatInviteRequest(channel_nick.replace("+", "")))
                    else:
                        await client(JoinChannelRequest(channel_nick))
                except ChannelsTooMuchError:
                    await tg_notify(
                        text="too much channels",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER,
                    )

        res = {"ok": True}
        res = json.dumps(res)

        writer.write(res.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()


async def start_server(free_port):
    server = await asyncio.start_server(handle_server, "localhost", free_port)
    addr = server.sockets[0].getsockname()
    print(f"Сервер запущен на {addr}")
    async with server:
        await server.serve_forever()


@client.on(events.NewMessage)
async def update_handler(event):
    message = event.message

    # --- sorting gw media
    if message.media:
        if isinstance(message.media, types.MessageMediaGiveaway):
            await client.forward_messages(DINA_SAS_USERNAME, message, from_peer=event.chat_id)

    # --- sorting giveshare chat id
    if event.chat_id == CHAT_ID_GIVESHAREBOT:

        if event.message.reply_markup:

            kbr = event.message.reply_markup.rows[0].buttons[0]
            if isinstance(kbr, types.KeyboardButtonCallback):
                if b"/subscription=raffle" in kbr.data:
                    await message.click(0)

            if "Розыгрыш набрал более 50 участников!" in message.text:
                return

            if isinstance(kbr, types.KeyboardButtonUrl):

                if "GiveShareBot/app?startapp" in kbr.url:
                    return await process_message(message, client)

    # --- sorting empy messages
    if event.message.text is None:
        return

    # --- banning chat ids
    if event.chat_id in BAN_CONTENT_JSON.get("channel_ids"):
        return

    # --- DEFAULT CHECKER
    await check_message_winner(event, won_messages)

    # --- templated channels
    for tgw in GWPK.keys():

        if (
            "Новый розыгрыш от канала" in message.text
            or "💥Суперссылка" in message.text
        ):
            if tgw in message.text.lower():
                return await process_message(message, client)

            for ent in message.entities:
                if isinstance(ent, types.MessageEntityTextUrl):
                    if "https://t.me/" in ent.url.lower():

                        if "startapp" in ent.url.lower():
                            continue

                        nickname = ent.url.split("https://t.me/")[1].split("/")[0]
                        message_id = ent.url.split("/")[-1]

                        await client.get_entity(nickname)

                        message = await client.get_messages(nickname, ids=int(message_id))

                        return await process_message(message, client)

    if event.message.reply_markup is not None:
        kbr = event.message.reply_markup.rows[0]
        if kbr is not None:
            if kbr.buttons[0]:
                return await process_message(message, client)


@client.on(events.MessageEdited)
async def update_handler(event):

    if event.chat_id in BAN_CONTENT_JSON.get("channel_ids"):
        return

    if event.message.text is None:
        return

    await check_message_winner(event, won_messages)


async def main():
    await initialize_bots_dict()

    await client.start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        free_port = s.getsockname()[1]
        await REDISKA.set(Ports.DEEPGLOW, free_port)

    await start_server(free_port)


# Запуск всего в одном цикле событий
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
