from typing import Union

# QUEUE_ID :
def queue_id(channel_id: Union[int, str], message_id: int):
    return f"{channel_id}:{message_id}"

def get_queue_id(key):
    return tuple(key.split(':'))

# WINS ! $
def win_message(chat_id, message_id, username):
    return f"{chat_id}!{message_id}${username}"

def get_win_message(argument):
    chat_id = argument.split('!')[0]
    message_id = argument.split('!')[1].split('$')[0]
    username = argument.split('$')[1]
    return chat_id, message_id, username

# LINK BUILDER
def link_build(message_id: int, channel_nick = None, channel_id = None):
    if channel_nick:
        return f"https://t.me/{channel_nick}/{message_id}"
    if channel_id:
        return f"https://t.me/c/{str(channel_id).replace("-100", '')}/{message_id}"
    raise ValueError("channel nick nor channel id specified on link builder")