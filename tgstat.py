import re
import copy
import asyncio
import aiohttp
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum

# ---
from config.settings import BotToken, ChatID, ThreadID
# ---
from utils import pattern_builder as PB
# ---
from config.enums import GWProviders as GWP
# ---
from config.settings import GWS_AIODBP
from config.settings import VAULT_TABLE
# ---
from config.settings import TgStat
# ---
from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
# ---
from utils.module_parser import get_nicknames, has_cyrillic
from utils.module_parser import prepare_vault_object
from utils.module_parser import get_gw_provider_from_text
# ---
from utils.helpers import __setup_custom_logger__
logging = __setup_custom_logger__(__name__, "tgstat")
# ---
from utils.helpers import send_request
# ---
from utils.helpers import tg_notify

current_querries = 0
LIMIT_QUERIES_PER_DAY = 200

class QueryStatus(Enum):
    DONE = "done"
    MORE = "more"


class CustomParser:


    def __init__(self, params, endpoint_url, parsing_source, query=None):

        self.query = query # FOR LOGGING

        self.params = params
        self.url = endpoint_url
        self.parsing_source = parsing_source

        self.limit_iter_per_queue = 20

        self.additional_requests = False  # if cur requests > limit_iter_per_queue


    async def _get_iters(self) -> Optional[int]:

        start_data = await self.get_raw_data(offset=0)

        if start_data.get("status") == "ok":
            totally_parsed = start_data["response"]["total_count"]
            iters = totally_parsed // 50
            if totally_parsed % 50 != 0: iters += 1
            iters = min(iters, self.limit_iter_per_queue)
            return iters
        else:
            logging.critical(f" {self.parsing_source} response false at first request")
            await tg_notify(text=f"status !ok {self.parsing_source}:\n{start_data}",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)

            return None


    async def _processing_query(self) -> Optional[QueryStatus]:

        self.gw_provider = get_gw_provider_from_text(self.query)

        print(f"STARTING QUERY: {self.query} WITH PARAMS: {self.params}")

        total_objs = []

        iters = await self._get_iters()
        if not iters:
            return None

        # ----------- PREPARING VAULT OBJECTS
        logging.debug("PREPARING REQUESTS")
        for offset_times in range(iters):
            logging.debug(f"offset #{offset_times}/{iters}")
            raw_data = await self.get_raw_data(offset_times)
            while not raw_data:
                raw_data = await self.get_raw_data(offset_times)

            items = await self.prepare_items(raw_data)

            total_objs += items

        # ----------- LOGGING
        await tg_notify(text=f"""Total ITEMS ({self.parsing_source}) for current iteration: {len(total_objs)} \n    QUERY: {self.query}""",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)
        # ----------- LOGGING

        prepared_objs = []
        for item in total_objs:
            logging.debug(item.queue_id)
            prepared_obj = await prepare_vault_object(item, self.parsing_source)
            prepared_objs.append(prepared_obj.__dict__)

        logging.info(f"appending all the objs: {len(prepared_objs)}")
        await GWS_AIODBP.append_many(VAULT_TABLE, prepared_objs, returning=VaultKeys.QUEUE_ID)
        # ----------- PREPARING VAULT OBJECTS

        if len(total_objs) > 3:
            self.params["endDate"] = round(total_objs[-1].date_post.timestamp())
            logging.info("detected last item. Going again")
            return QueryStatus.MORE

        return QueryStatus.DONE


    async def get_raw_data(self, offset) -> Optional[dict]:
        global current_querries

        try:
            current_querries += 1

            offset_queue = 50 * offset
            logging.debug(f"getting data with offset: {offset_queue}")
            self.params["offset"] = offset_queue
            data = await send_request(self.url,
                                      method="GET",
                                      params=self.params)
            if data:
                return data.json()

        except aiohttp.ConnectionTimeoutError:
            await tg_notify(text=f'fucked up on {offset} page ({self.parsing_source})',
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.warning(f'fucked up on {offset} page')
            await asyncio.sleep(3)
        return None


    async def prepare_items(self, items: dict) -> List[VaultObject]:
        objs = []
        for item in items["response"]["items"]:

            # --- getting data

            # --- text
            text = re.sub(r'\s+', ' ', item["text"])
            # ---

            # --- date posted
            date_post = datetime.fromtimestamp(item["date"])
            # ---

            # --- channel id
            channel = next((ch for ch in items["response"]["channels"] if ch["id"] == item["channel_id"]), None)
            channel_id = channel["tg_id"]
            # ---

            # --- channel nick
            channel_nick = item["link"].split('/')[-2]
            # ---

            # --- message id
            message_id = int(item["link"].split('/')[-1])
            # ---

            # --- queue_id
            queue_id = PB.queue_id(channel_nick, message_id)
            # ---

            if channel_nick.isdigit():
                channel_nick = None

            objs.append(
                VaultObject(
                    queue_id=queue_id,
                    text=text,
                    date_post=date_post,
                    date_add=datetime.now(),
                    date_predicted=None, # takes so long, so make it later
                    channel_nick=channel_nick,
                    channel_id=channel_id,
                    message_id=message_id,
                    conditions=get_nicknames(item["text"]),
                    gw_provider=GWP.Unknown,
                    ai={}, # takes so long, so make it later
                    storage_message_id=None,
                    parsing_source=self.parsing_source
                )
            )

        return objs


    async def run_query(self, query_name):
        self.query = query_name
        self.params["q"] = query_name
        logging.critical(f"SO NEW ITER: {self.params}")
        proc_query = await self._processing_query()
        if self.additional_requests:
            while proc_query != QueryStatus.DONE:
                print(f"STARTING ADDITIONAL QUERY: {self.parsing_source} | {self.query}")
                proc_query = await self._processing_query()
        return


async def run_queries_in_turn(qs):
    global current_querries

    cp = CustomParser(params=None,
                      endpoint_url=TgStat.ENDPOINT_URL,
                      parsing_source=TgStat.NAME)
    run_time = TgStat.SCHEDULE
    original_params = TgStat.PARAMS

    while True:
        now = datetime.now()
        run_datetime = datetime.combine(now.date(), run_time)
        if run_datetime < now:
            run_datetime += timedelta(days=1)

        wait_time = (run_datetime - now).total_seconds()
        current_querries = 0
        logging.info(f'Следующий запуск запланирован на {run_datetime}. Ожидание {round(wait_time)} секунд.')

        await asyncio.sleep(wait_time)

        # PARAMS
        now = datetime.now()
        timestamp_time_ago = now - timedelta(hours=28)
        timestamp_time_ago = round(timestamp_time_ago.timestamp())
        original_params["startDate"] = timestamp_time_ago
        # PARAMS

        for q in qs:

            await tg_notify(text=f"""STARTING {cp.parsing_source} {q}""",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)

            cp.params = copy.deepcopy(original_params)
            cp.allow_additional_requests = True
            if has_cyrillic(q):
                cp.allow_additional_requests = False # потому что там невероятно дохуя результатов

            logging.info(f"started query {q} at {datetime.now()}. PARAMS: {cp.params} | {cp.allow_additional_requests}")
            await cp.run_query(q)

        await tg_notify(text=f"""done {cp.parsing_source}""",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)


async def main():
    await run_queries_in_turn(TgStat.KEYWORDS)


if __name__ == "__main__":
    asyncio.run(main())
