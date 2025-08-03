import asyncio
import math

import requests
from typing import Optional, List
from bs4 import BeautifulSoup
import bs4
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
from config.settings import TgFind
# ---
from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
# ---
from utils.module_parser import get_nicknames
from utils.module_parser import prepare_vault_object
# ---
from utils.helpers import __setup_custom_logger__
logging = __setup_custom_logger__(__name__, "tgfind")
# ---
from utils.helpers import CFScraper
SCRAPER = CFScraper()
# ---
from utils.helpers import tg_notify
# ---

class CustomParser:

    def __init__(self, params, endpoint_url, parsing_source):
        self.params = params
        self.url = endpoint_url
        self.headers = {'Content-Type': 'text/html; charset=utf-8'} # stock
        self.parsing_source = parsing_source


    async def get_raw_data(self, query, offset) -> Optional[BeautifulSoup]:
        try:
            self.params["query"] = query
            self.params["offset"] = offset
            eq = await SCRAPER.get(url=self.url,
                                   params=self.params,
                                   headers=self.headers)
            eq.encoding = 'utf-8'

            soup = BeautifulSoup(eq.text, "lxml")
            return soup

        except requests.exceptions.ConnectionError:
            await tg_notify(text=f"fucked up on {offset} offset ({self.parsing_source})",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.warning(f"fucked up on {offset} offset")
            await asyncio.sleep(5)
            return None


    async def prepare_items(self, items: List[bs4.element.Tag]) -> List[VaultObject]:
        objs = []
        for item in items:
            for a_tag in item.find_all('a'):
                a_tag.decompose()

            block_cache = item.find("div", class_="block-cache")
            date_post_non_formatted = block_cache.find_all("div")[0].text.replace('/', '').strip()
            date_posted = datetime.fromisoformat(date_post_non_formatted).replace(tzinfo=None)

            text = item.find("div", class_="mt-3").text.strip()
            link = item.find("script").attrs["data-telegram-post"]
            channel_nick, message_id = link.split('/')
            message_id = int(message_id)
            channel_id = None

            queue_id = PB.queue_id(channel_nick, message_id)

            if channel_nick.isdigit():
                channel_id = int(channel_nick)
                channel_nick = None

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

        # FIRST INITIAL REQUEST
        init_soup = await self.get_raw_data(query, 0)
        page_counter = init_soup.find("div", class_="col fw-bold text-secondary d-flex justify-content-center")

        if not page_counter:
            await tg_notify(text="tgfind broken again",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            return

        # ITERS / OFFSETS / PAGES
        offset_text = page_counter.get_text(strip=True)
        offset_count = int(offset_text.split(' ')[0].replace(">=", ''))

        total_objs = []
        offset = -10

        results_by_pages = offset_count/10

        for _ in range(math.ceil(results_by_pages)):
            offset += 10
            logging.debug(f"process offset: {offset}/{offset_count}")

            soup = await self.get_raw_data(query, offset)
            while not soup:
                soup = await self.get_raw_data(query, offset)

            posts_feed = soup.find("div", class_="col-lg-8 mt-3")
            if not posts_feed:
                await asyncio.sleep(5)
                logging.error(f"posts_feed is None! BREAKING")
                break

            posts = posts_feed.find_all("div", class_="mt-4", recursive=False)
            posts = [i for i in posts if "row" not in i.attrs["class"]]
            items = await self.prepare_items(posts)
            total_objs += items


        prepared_objs = []
        for obj in total_objs:
            logging.debug(obj.queue_id)
            prepared_obj = await prepare_vault_object(obj, self.parsing_source)
            prepared_objs.append(prepared_obj.__dict__)

        logging.info(f"appending all the objs: {len(prepared_objs)}")
        await GWS_AIODBP.append_many(VAULT_TABLE, prepared_objs, returning=VaultKeys.QUEUE_ID)


async def run_queries_in_turn(qs):

    cp = CustomParser(params=TgFind.PARAMS,
                      endpoint_url=TgFind.ENDPOINT_URL,
                      parsing_source=TgFind.NAME)
    run_time = TgFind.SCHEDULE

    while True:
        now = datetime.now()
        run_datetime = datetime.combine(datetime.now().date(), run_time)
        if run_datetime < now:
            run_datetime += timedelta(days=1)

        wait_time = (run_datetime - now).total_seconds()
        logging.info(f"Следующий запуск запланирован на {run_datetime}. Ожидание {round(wait_time)} секунд.")

        await asyncio.sleep(wait_time)

        for q in qs:
            await tg_notify(text=f"""STARTING {cp.parsing_source} {q}""",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.info(f"started query {q} at {datetime.now()}")
            await cp.run_query(q)

        await tg_notify(text=f"""done {cp.parsing_source}""",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)


async def main():
    await run_queries_in_turn(TgFind.KEYWORDS)


if __name__ == "__main__":
    asyncio.run(main())