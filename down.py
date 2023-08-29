import os
import requests
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

POST_TOKEN = "xoxb-5817745880085-5806145535847-7QirBhixifN36OKKqArxhJ1C"
POST_BOT_TOKEN = "xoxb-5817745880085-5806145535847-7QirBhixifN36OKKqArxhJ1C"

RETRIEVE_TOKEN = "xoxb-5844384647568-5806162001111-y4ODRLtXVEZ8s8ewL1YgyXAa"
RETRIEVE_BOT_TOKEN = "xoxb-5844384647568-5806162001111-y4ODRLtXVEZ8s8ewL1YgyXAa"

POST_CHANNEL_ID = "C05Q4GNK69H"
RETRIEVE_CHANNEL_ID = "C05Q1NHUGBX"

POST_CLIENT = WebClient(token=POST_TOKEN)
POST_BOT_CLIENT = WebClient(token=POST_BOT_TOKEN)
RETRIEVE_CLIENT = WebClient(token=RETRIEVE_TOKEN)
RETRIEVE_BOT_CLIENT = WebClient(token=RETRIEVE_BOT_TOKEN)

try :
    response = POST_CLIENT.conversations_history(
        channel=POST_CHANNEL_ID,
        limit=1
    )
    messages = response['messages']

    for message in messages :
        response = POST_CLIENT.users_profile_get(user=message['user'])
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
                    headers={'Authorization': 'Bearer ' + POST_BOT_TOKEN}
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
                result = RETRIEVE_CLIENT.files_upload_v2(
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
                
            latest_file = uploaded_file_res[0]
            for file in uploaded_file_res :
                if latest_file['timestamp'] < file['timestamp'] :
                    latest_file = file

            print(latest_file)
            file_info = RETRIEVE_CLIENT.files_info(file=latest_file['id'])
            print(latest_file['id'])
            target_ts = file_info['file']['shares']['public']['C05NKTPNQPM'][0]['ts']

        else :
            result = RETRIEVE_BOT_CLIENT.chat_postMessage(
                channel=RETRIEVE_CHANNEL_ID,
                text=message['text']
            )

except SlackApiError as e :
    print(f"Error posting message: {e.response['error']}")
