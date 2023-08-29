import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SOURCE_BOT_TOKEN = os.getenv("SOURCE_BOT_TOKEN")
TARGET_BOT_TOKEN = os.getenv("TARGET_BOT_TOKEN")

POST_CHANNEL_ID = "C05Q4GNK69H"
RETRIEVE_CHANNEL_ID = "C05Q1NHUGBX"

SOURCE_CLIENT = WebClient(token=SOURCE_BOT_TOKEN)
TARGET_CLIENT = WebClient(token=TARGET_BOT_TOKEN)

try :
    info = TARGET_CLIENT.files_info(file="F05QUNVEMK2")
    print(info)

except Exception as e :
    print({e})
