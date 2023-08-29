import os
import requests
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

POST_TOKEN = "xoxb-5753499915335-5801233296276-NbCHssGcWNzhQUvnqUxIzLLb"
POST_BOT_TOKEN = "xoxb-5753499915335-5801233296276-NbCHssGcWNzhQUvnqUxIzLLb"

print(time.time())

RETRIEVE_TOKEN = "xoxb-5780675552945-5812548008481-3SYhjXABqUHXWaBoGJ23RCoS"
RETRIEVE_BOT_TOKEN = "xoxb-5780675552945-5812548008481-3SYhjXABqUHXWaBoGJ23RCoS"

POST_CHANNEL_ID = "C05P9MY0JV6"
RETRIEVE_CHANNEL_ID = "C05NKTPNQPM"

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
            for index, file in enumerate(message['files']):
                print(index)
                file_url = file['url_private']
                file_name = file['name']
                file_res = requests.get(
                    file_url,
                    headers={'Authorization': 'Bearer ' + POST_BOT_TOKEN}
                )
                file_path = os.getcwd() + '/uploads/' + file_name

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

                try :
                    result = RETRIEVE_CLIENT.files_upload_v2(
                        channel=RETRIEVE_CHANNEL_ID,
                        initial_comment=text,
                        file=file_path,
                    )
                    print(result)
                except Exception as e :
                    print({e})

                end = time.time()
                # ts = file['shares']['public']['C05NKTPNQPM'][0]['ts']
                ts = result['files'][index]['shares']['public']['C05NKTPNQPM'][0]['ts']

                print("start : ", start)
                print("end : ", end)
                print("ts : ", ts)
                print("duration start and ts : ", float(ts) - start)
                print("duration ts and end : ", end - float(ts))

                try :
                    os.remove(file_path)
                except FileNotFoundError :
                    print(f"{file_path} not found !")
                except Exception as e :
                    print(f"An error occurred while deleting the file : {e}")
        else :
            result = RETRIEVE_BOT_CLIENT.chat_postMessage(
                channel=RETRIEVE_CHANNEL_ID,
                text=message['text']
            )

except SlackApiError as e :
    print(f"Error posting message: {e.response['error']}")
