import re
import json
import traceback

import torch
import socket
import asyncio
from aiohttp import web
# ---
from config.enums import Ports
# ---
from config.settings import REDISKA
# ---
from transformers import pipeline
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
# ---
from config.settings import BotToken, ChatID, ThreadID
from config.settings import MODEL_FOLDER

from utils.helpers import tg_notify_synchronous

async def dedicate_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        free_port = s.getsockname()[1]
        await REDISKA.set(Ports.AI_SERVER, free_port)
    return free_port


# ------------------------------


tokenizer = AutoTokenizer.from_pretrained(MODEL_FOLDER)
model = AutoModelForQuestionAnswering.from_pretrained(MODEL_FOLDER)
torch.cuda.synchronize()

QUESTION = "какой приз разыгрывается?"


def _init_pipeline(dev):
    p0 = pipeline("question-answering",
                  model=model,
                  tokenizer=tokenizer,
                  device=dev,
                  torch_dtype=torch.float16,
                  top_k=3)
    return p0


PIPE = _init_pipeline(0)

def process_data(context: str):
    prediction = {"score": 0,
                  "start": 0,
                  "end": 0,
                  "answer": None}
    try:
        input_data = {
            "context": context,
            "question": QUESTION
        }
        prediction = PIPE(**input_data)
    except ValueError:
        pass
    except Exception as e:
        tg_notify_synchronous(text=f"AI exception: {e}",
                              token=BotToken.PARSER,
                              chat_id=ChatID.PARSER)
    finally:
        return prediction


# ------------------------------

async def process(data):
    text = re.sub(r'\s+', ' ', data["context"]).strip()
    print(text)
    try:
        res = await asyncio.to_thread(process_data, text)
        return res
    except Exception as e:
        print(e)
        traceback.print_exc()

async def handle(request):
    if request.method == "POST":
        try:
            data = await request.json()

            response = await process(data)

            print(f'=== RESP: --- {response} --- ')

            return web.json_response(
                response,
                dumps=lambda obj: json.dumps(obj, ensure_ascii=False)
            )
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    else:
        return web.json_response({"error": "Method not allowed"}, status=405)


async def start_server():
    free_port = await dedicate_port()

    app = web.Application(client_max_size=25 * 1024 * 1024)

    app.add_routes([
        web.post('/', handle)  # Обработка POST-запросов на /endpoint
    ])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", free_port)
    await site.start()
    print(f"Server started at http://localhost:{free_port}")
    while True:
        await asyncio.sleep(3600)  # Ждет 1 час между проверками


if __name__ == '__main__':
    asyncio.run(start_server())
