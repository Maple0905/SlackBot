import os
import requests
import time

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
    response = SOURCE_CLIENT.conversations_history(
        channel=POST_CHANNEL_ID,
        limit=1
    )
    messages = response['messages']

    for message in messages :
        response = SOURCE_CLIENT.users_profile_get(user=message['user'])
        display_name = response["profile"]["real_name"]
        print(display_name, ' ', message['text'])
        if 'files' in message :
            files_len = len(message['files'])
            print('file len : ', files_len)
            uploaded_file_res = []
            for index, file in enumerate(message['files']):
                file_url = file['url_private']
                file_name = file['name']
                file_res = requests.get(
                    file_url,
                    headers={'Authorization': 'Bearer ' + SOURCE_BOT_TOKEN}
                )
                file_path = os.getcwd() + '/' + file_name

                # file_path = os.path.expanduser('~/workspace/Python/uploads/' + file_name)
                if file_res.status_code == 200 :
                    with open(file_path, 'wb') as f :
                        f.write(file_res.content)

                display_text = display_name + ' added this file.'
                if index == 0 :
                    text = display_text + '\n' + message['text']
                else :
                    text = message['text']

                start = time.time()
                result = TARGET_CLIENT.files_upload_v2(
                    channel=RETRIEVE_CHANNEL_ID,
                    initial_comment=text,
                    file=file_path,
                )
                uploaded_file_res.append(result['file'])

                try :
                    os.remove(file_path)
                except FileNotFoundError :
                    print(f"{file_path} not found !")
                except Exception as e :
                    print(f"An error occurred while deleting the file : {e}")

            print(uploaded_file_res)

            # latest_file = uploaded_file_res[0]
            # for file in uploaded_file_res :
            #     if latest_file['timestamp'] < file['timestamp'] :
            #         latest_file = file

            # print(latest_file['id'])
            # file_info = TARGET_CLIENT.files_info(file=latest_file['id'])
            # print(file_info)
            # target_ts = file_info['file']['shares']['public']['C05NKTPNQPM'][0]['ts']

        else :
            result = TARGET_CLIENT.chat_postMessage(
                channel=RETRIEVE_CHANNEL_ID,
                text=message['text']
            )

except SlackApiError as e :
    print(f"Error posting message: {e.response['error']}")
