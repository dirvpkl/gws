import asyncio
import json
import aiohttp
from bs4 import BeautifulSoup
from utils.helpers import send_request

queue = asyncio.Queue()

async def _analyze_message(req_text, channel_nick, message_id):
    # оставляю без изменений
    soup = BeautifulSoup(req_text, "lxml")
    elem = soup.find(attrs={'data-post': f'{channel_nick}/{message_id}'})
    if not elem:
        return
    btn = elem.find("div", class_="tgme_widget_message_inline_row")
    if not btn:
        return

    inline_btn = btn.find("a", class_="tgme_widget_message_inline_button")
    if inline_btn and "url_button" in inline_btn.attrs.get("class", []):
        hrefurl = inline_btn.get("href", "")
        if "t.me/" not in hrefurl:
            return 0
        print(f"FOUND BUTTON! {channel_nick}/{message_id}")
        return True
    return

async def get_gw_provider_from_channel(channel_nick: str, message_id: int, session: aiohttp.ClientSession, proxy: str = None):
    url = f'https://t.me/s/{channel_nick}/{message_id}'
    try:
        resp = await send_request(url, method="GET", session=session, proxy=proxy)
        if resp.status == 200:
            text = await resp.text()
            return await _analyze_message(text, channel_nick, message_id)
        else:
            print(f"Неправильный статус {resp.status} для {url}")
    except UnicodeDecodeError:
        print(f"UnicodeDecodeError при обработке {url}")
    except Exception as e:
        print(f"Ошибка при запросе {url}: {e}")

async def worker(queue: asyncio.Queue, session: aiohttp.ClientSession, proxy: str = None, semaphore: asyncio.Semaphore = None):
    while True:
        item = await queue.get()
        try:
            channel_nick, message_id_str = item.split(':')
            message_id = int(message_id_str)

            if semaphore:
                async with semaphore:
                    await get_gw_provider_from_channel(channel_nick, message_id, session, proxy)
            else:
                await get_gw_provider_from_channel(channel_nick, message_id, session, proxy)

        except Exception as e:
            print(f"Ошибка при обработке {item}: {e}")
        finally:
            queue.task_done()

async def main():
    proxy = "http://user:password@proxy_address:port"

    # Подстрой под себя - например 1000 одновременных запросов - осторожно с лимитами!
    max_concurrent_requests = 300
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    with open("output_test_.json", 'r', encoding='utf-8') as fr:
        data = json.load(fr)

    for d in data:
        queue.put_nowait(d)

    async with aiohttp.ClientSession() as session:
        tasks = []
        # Кол-во воркеров можно сделать равным 2x или 3x семафору для высокой загрузки CPU,
        # но учитывай лимиты на сеть и сервер
        num_workers = max_concurrent_requests
        for _ in range(num_workers):
            task = asyncio.create_task(worker(queue, session, proxy, semaphore))
            tasks.append(task)

        await queue.join()

        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    print("Все запросы завершены.")

if __name__ == "__main__":
    asyncio.run(main())
