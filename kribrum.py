import copy
import random

import bs4
import asyncio
import requests
from typing import Optional, List
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
from config.settings import Kribrum
# ---
from config.dataclasses_ import Database as D
VaultObject = D.GWS.Vault
VaultKeys = D.GWS.Vault.Keys
# ---
from utils.module_parser import get_nicknames
from utils.module_parser import prepare_vault_object
# ---
from utils.helpers import __setup_custom_logger__
logging = __setup_custom_logger__(__name__, "kribrum")
# ---
from utils.helpers import CFScraper
# ---
from utils.helpers import tg_notify


class CustomParser:

    def __init__(self, parsing_source, url_search, url_text, url_auth, payload):
        self.payload = payload
        self.url_text = url_text
        self.url_search = url_search
        self.parsing_source = parsing_source
        self.url_auth = url_auth

        self.login_creds = None
        self.scraper = None

    async def _get_text(self, yauid, url_text):
        logging.debug(f"called get text to {yauid}")
        try:
            r = await self.scraper.post(url=url_text,
                                   params={"id": yauid})
            resp = r.json()
        except Exception as e:
            logging.debug(yauid)
            logging.error(f"Неожиданная ошибка при запросе YAUID: {e}", exc_info=True)
            return None
        return resp["post"]["body"]

    async def init(self, to_change=False) -> bool:
        self.scraper = CFScraper()
        if len(self.login_creds) == 0: # limit for creds resets every 24h
            return False
        if to_change:
            cred = self.login_creds.pop(0)
            logging.info(f"using new cred. creds left: {len(self.login_creds)}")
            await self.scraper.post(url=self.url_auth,
                                    data=cred)
        return True

    async def get_raw_data(self, q, page) -> Optional[dict]:
        try:
            self.payload["query"] = q
            self.payload["page"] = page

            while True:
                data = await self.scraper.post(self.url_search,
                                           data=self.payload)
                data = data.json()

                if data["result_code"] == 429:
                    logging.info("result code 429. CHANGING CREDS")
                    await self.init(to_change=True)
                    continue

                break

            return data
        except requests.exceptions.ConnectionError:
            await tg_notify(text=f"fucked up on {q} query ({self.parsing_source})",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.warning(f"fucked up on {q} query")
            await asyncio.sleep(5)
            return None


    async def prepare_items(self, posts: List[bs4.element.Tag]) -> List[VaultObject]:
        objs = []

        for post in posts:

            try:

                if post["type"] == 's' or post["type"] == 'i':  # s - repost, i - image

                    if "_parent" in post: # repost owner exists in db
                        url = post["_parent"]["url"]
                        ptime = post["_parent"]["ptime"]
                        text = post["_parent"]["src"]["body"]
                    else:
                        url = post["parent"]
                        ptime = post["ptime"]
                        text = await self._get_text(post["yauid"], self.url_text)

                elif post["type"] == 'p':  # post

                    url = post["url"]
                    if "t.me" not in url:
                        url = post["parent"]
                    ptime = post["ptime"]
                    text = await self._get_text(post["yauid"], self.url_text)

                # type c - comment
                # type p - post
                # type s - repost from parent
                # type i - image post

                else:
                    logging.warning(f"unknown post type {post}")
                    continue

            except Exception as e:
                logging.error(f'{post}: {e}')
                continue

            date_posted = datetime.fromtimestamp(ptime)
            channel_nick = url.split('/')[-2]
            try:
                message_id = int(url.split('/')[-1])
            except ValueError:
                logging.warning(f"post from bot. have no message_id")
                continue
            channel_id = None

            queue_id = PB.queue_id(channel_nick, message_id)

            logging.debug(f"{queue_id} proceed")

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
            # --- stop loop if date doesn't match

        return objs


    async def run_query(self, query):

        # FIRST INITIAL REQUEST
        start_data = await self.get_raw_data(query, 0)
        total_objs = []

        # ----------- PREPARING VAULT OBJECTS
        for page in range(0, start_data["limit"] // start_data["max_per_page"]):

            logging.debug(f"process page: {page}")

            posts = await self.get_raw_data(query, page)
            logging.debug(f"len posts: {len(posts.get("posts", [i for i in range(99999)]))}")

            objs = await self.prepare_items(posts.get("posts", None))

            total_objs += objs

            await asyncio.sleep(3)

        prepared_objs = []
        for obj in total_objs:
            logging.debug(obj.queue_id)
            prepared_obj = await prepare_vault_object(obj, self.parsing_source)
            prepared_objs.append(prepared_obj.__dict__)

        logging.info(f"appending all the objs: {len(prepared_objs)}")
        await GWS_AIODBP.append_many(VAULT_TABLE, prepared_objs, returning=VaultKeys.QUEUE_ID)
        # ----------- PREPARING VAULT OBJECTS


async def run_queries_in_turn(qs):

    cp = CustomParser(url_search=Kribrum.ENDPOINT_SEARCH,
                      url_text=Kribrum.ENDPOINT_TEXT,
                      url_auth=Kribrum.ENDPOINT_AUTH,
                      parsing_source=Kribrum.NAME,
                      payload=Kribrum.PAYLOAD)
    run_time = Kribrum.SCHEDULE

    while True:
        now = datetime.now()
        run_datetime = datetime.combine(datetime.now().date(), run_time)
        if run_datetime < now:
            run_datetime += timedelta(days=1)

        wait_time = (run_datetime - now).total_seconds()
        logging.info(f'Следующий запуск запланирован на {run_datetime}. Ожидание {round(wait_time)} секунд.')

        await asyncio.sleep(wait_time)

        cp.login_creds = copy.deepcopy(Kribrum.LOGINS_CREDENTIALS)
        random.shuffle(cp.login_creds)

        for q in qs:
            init_r = await cp.init()
            if init_r is False:
                logging.warning("closing the loop. no more available creds")
                break
            await tg_notify(text=f"""STARTING {cp.parsing_source} {q}""",
                            token=BotToken.PARSER,
                            chat_id=ChatID.PARSER)
            logging.info(f'started query {q} at {datetime.now()}')
            try:
                await cp.run_query(q)
            except ZeroDivisionError:
                print("ZERODIVISIONERROR")
            logging.info(f'query {q} done at {datetime.now()}')

        await tg_notify(text=f"""done {cp.parsing_source}""",
                        token=BotToken.PARSER,
                        chat_id=ChatID.PARSER)

async def main():
    await run_queries_in_turn(Kribrum.KEYWORDS)


if __name__ == '__main__':
    asyncio.run(main())
