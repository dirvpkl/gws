import asyncio
import requests
from typing import List, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

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
from config.settings import LinkBaza
# ---
from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
# ---
from utils.module_parser import get_nicknames
from utils.module_parser import prepare_vault_object
# ---
from utils.helpers import __setup_custom_logger__
logging = __setup_custom_logger__(__name__, "linkbaza")
# ---
from utils.helpers import CFScraper
SCRAPER = CFScraper()
# ---
from utils.helpers import tg_notify


class CustomParser:


    def __init__(self, params, endpoint_url, parsing_source, end_date: datetime = None):
        self.params = params
        self.url = endpoint_url
        self.parsing_source = parsing_source
        self.end_date = end_date


    async def get_raw_data(self, page, query):
        try:
            self.params["search"] = query
            self.params["page"] = page
            r = await SCRAPER.get(url=self.url,
                                  params=self.params)
            soup = BeautifulSoup(r.json()["posts"]["html"], "lxml")
            post_items = soup.find_all("div", class_="post-item-container")
            return post_items

        except requests.exceptions.ConnectionError:
            await tg_notify(text=f"fucked up on {page} page ({self.parsing_source})",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.warning(f"fucked up on {page} page")
            await asyncio.sleep(5)
            return None


    async def prepare_items(self, items) -> Optional[List[VaultObject]]:
        objs = []
        for item in items:
            # --- getting data
            date_post_str = item.find("div", class_="post-date").text.strip()
            date_posted = datetime.strptime(date_post_str, "%d.%m.%y %H:%M")

            channel_id = int(item.get("data-channel-id").strip())
            channel_nick = item.get("data-channel-username")

            message_id = int(item.get("data-post-id"))
            text = item.find("div", class_="post-item-text").text

            # --- stop loop if date doesn't match
            if date_posted < self.end_date:
                return None

            queue_id = PB.queue_id(channel_id, message_id)

            obj = VaultObject(
                queue_id=queue_id,
                text=text,
                date_post=date_posted,
                date_add=datetime.now(),
                date_predicted=None,
                channel_nick=channel_nick,
                channel_id=channel_id,
                message_id=message_id,
                conditions=get_nicknames(text),
                gw_provider=GWP.Unknown,
                ai={},
                storage_message_id=None,
                parsing_source=self.parsing_source
            )

            objs.append(obj)

        return objs


    async def run_query(self, query):

        total_objs = []
        page = 2 # page 1 не выдает json формат в ответе

        # ----------- PREPARING VAULT OBJECTS
        while True:
            logging.debug(f"process page: {page}")

            raw_data = await self.get_raw_data(page, query)
            while not raw_data:
                raw_data = await self.get_raw_data(page, query)
            items = await self.prepare_items(raw_data) # if none - break
            if not items:
                logging.info("parsed_date < end_date")
                break
            total_objs += items

            await asyncio.sleep(3)

            page += 1

        prepared_objs = []
        for obj in total_objs:
            logging.debug(obj.queue_id)
            prepared_obj = await prepare_vault_object(obj, self.parsing_source)
            prepared_objs.append(prepared_obj.__dict__)

        logging.info(f"appending all the objs: {len(prepared_objs)}")
        await GWS_AIODBP.append_many(VAULT_TABLE, prepared_objs, returning=VaultKeys.QUEUE_ID)
        # ----------- PREPARING VAULT OBJECTS


async def run_queries_in_turn(qs):

    cp = CustomParser(params=LinkBaza.PARAMS,
                      endpoint_url=LinkBaza.ENDPOINT_URL,
                      parsing_source=LinkBaza.NAME)
    run_time = LinkBaza.SCHEDULE

    while True:
        now = datetime.now()
        run_datetime = datetime.combine(datetime.now().date(), run_time)
        if run_datetime < now:
            run_datetime += timedelta(days=1)

        wait_time = (run_datetime - now).total_seconds()
        logging.info(f'Следующий запуск запланирован на {run_datetime}. Ожидание {round(wait_time)} секунд.')

        await asyncio.sleep(wait_time)

        for q in qs:
            timestamp_end = datetime.now() - timedelta(hours=36)
            cp.end_date = timestamp_end

            await tg_notify(text=f"""STARTING {cp.parsing_source} {q}""",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)

            logging.info(f'started query {q} at {datetime.now()}')
            await cp.run_query(q)

        await tg_notify(text=f"""done {cp.parsing_source}""",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)


async def main():
    await run_queries_in_turn(LinkBaza.KEYWORDS)


if __name__ == "__main__":
    asyncio.run(main())
