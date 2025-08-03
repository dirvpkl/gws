from datetime import datetime
from typing import List, Optional, TypedDict, Union
from dataclasses import dataclass, field
from config.enums import GWProviders, Tasks


class Commands:

    class Controller:

        @dataclass
        class CreateQueue:
            queue_id: str
            gw_provider: Union[GWProviders, int]
            dedicated_time: int
            bots_count: int
            message_id: int
            channel_nick: str
            additional_channels: List
            gw_link: str
            is_running: bool
            task: Tasks = field(default=Tasks.Participate, init=False)

    class AI:

        @dataclass
        class Request:
            context: str

    class DeepGlow:

        @dataclass
        class Subscribe:  # not used
            channel_nick: str
            task: Tasks = field(default=Tasks.Subscribe, init=False)


class _UaSchema:
    class Construct(TypedDict):
        system_version: str
        app_version: str
        device_model: str

    SYSTEM_VERSION = "system_version"
    APP_VERSION = "app_version"
    DEVICE_MODEL = "device_model"

class Database:

    class BMB:

        @dataclass
        class Winners:
            class Status:
                NOT_SEEN = "👁 Не просмотрено"

            win_id: str
            bot: str
            channel_id: int
            message_id: int
            status: Status
            date_won: datetime
            link_message: Optional[str]
            channel_name: Optional[str]
            channel_nick: Optional[str]
            prize: Optional[str]
            description: Optional[str]
            winners_message_id: Optional[int]
            date_received: None

            class Keys:
                WIN_ID = "win_id"
                BOT = "bot"
                LINK_MESSAGE = "link_message"
                CHANNEL_NAME = "channel_name"
                CHANNEL_NICK = "channel_nick"
                CHANNEL_ID = "channel_id"
                message_id = "message_id"
                PRIZE = "prize"
                DESCRIPTION = "description"
                STATUS = "status"
                DATE_WON = "date_won"
                WINNERS_MESSAGE_ID = "winners_message_id"
                DATE_RECEIVED = "date_received"

    class GWS:

        @dataclass
        class Vault:
            queue_id: str
            text: str
            date_post: datetime
            date_add: datetime
            date_predicted: Optional[datetime]
            channel_nick: Optional[str]
            channel_id: Optional[int]
            message_id: int
            conditions: List
            gw_provider: GWProviders
            ai: dict
            storage_message_id: Optional[int]
            parsing_source: str

            class Keys:
                QUEUE_ID = "queue_id"
                TEXT = "text"
                DATE_POST = "date_post"
                DATE_ADD = "date_add"
                DATE_PREDICTED = "date_predicted"
                CHANNEL_NICK = "channel_nick"
                CHANNEL_ID = "channel_id"
                MESSAGE_ID = "message_id"
                CONDITIONS = "conditions"
                GW_PROVIDER = "gw_provider"
                AI = "ai"
                STORAGE_MESSAGE_ID = "storage_message_id"
                PARSING_SOURCE = "parsing_source"

    class TelegramData:

        @dataclass
        class BotsData:
            botname: str
            phone_number: str
            api_name: str
            full_proxy: str
            bot_str_id: str
            user_agent: _UaSchema.Construct

            class Keys:
                BOTNAME = "botname"
                PHONE_NUMBER = "phone_number"
                API_NAME = "api_name"
                FULL_PROXY = "full_proxy"
                BOT_STR_ID = "bot_str_id"
                USER_AGENT = "user_agent"