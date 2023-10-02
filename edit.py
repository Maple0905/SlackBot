import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SOURCE_BOT_TOKEN = os.getenv("SOURCE_BOT_TOKEN")
SOURCE_USER_TOKEN = os.getenv("SOURCE_USER_TOKEN")
SOURCE_BOT_CLIENT = WebClient(token=SOURCE_BOT_TOKEN)
SOURCE_USER_CLIENT = WebClient(token=SOURCE_USER_TOKEN)

TARGET_BOT_TOKEN = os.getenv("TARGET_BOT_TOKEN")
TARGET_USER_TOKEN = os.getenv("TARGET_USER_TOKEN")
TARGET_BOT_CLIENT = WebClient(token=TARGET_BOT_TOKEN)
TARGET_USER_CLIENT = WebClient(token=TARGET_USER_TOKEN)

try :
    messages = SOURCE_BOT_CLIENT.conversations_history(channel="C05P9MY0JV6", limit=5)
    for message in messages['messages'] :
        print(message)
    # SOURCE_CLIENT.chat_update(
    #     channel="C05P9MY0JV6",
    #     ts="",
    #     text="Hello"
    # )
    # last_message = None
    # messages = SOURCE_BOT_CLIENT.conversations_history(channel="C05P9MY0JV6", limit=5)
    # for message in messages['messages'] :
    #     if 'client_msg_id' in message :
    #         last_message = message
    #         break
    # print(last_message)


    # result = TARGET_USER_CLIENT.chat_delete(
    #     channel="C05NKTPNQPM",
    #     ts="1696125216.947289"
    # )
    # print(result)

except SlackApiError as e :
    print(f"Error posting message: {e.response['error']}")
