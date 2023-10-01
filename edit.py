import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SOURCE_BOT_TOKEN = os.getenv("SOURCE_BOT_TOKEN")
SOURCE_CLIENT = WebClient(token=SOURCE_BOT_TOKEN)

try :
    SOURCE_CLIENT.chat_update(
        channel="C05P9MY0JV6",
        ts="",
        text="Hello"
    )

except SlackApiError as e :
    print(f"Error posting message: {e.response['error']}")
