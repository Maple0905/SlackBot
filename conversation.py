import os
import pymysql
import requests
import asyncio

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SOURCE_BOT_TOKEN = os.getenv("SOURCE_BOT_TOKEN")
TARGET_BOT_TOKEN = os.getenv("TARGET_BOT_TOKEN")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

limit = 100
messages = []

DB_CONN = pymysql.connect(
    host=DB_HOST,
    port=int(DB_PORT),
    user=DB_USERNAME,
    password=DB_PASSWORD,
    db=DB_DATABASE
)

DB_CURSOR = DB_CONN.cursor()

async def fileUpload(client, channel, text, file_path, ts) :
    if ts == '' :
        client.files_upload_v2(
            channel=channel,
            initial_comment=text,
            file=file_path,
        )
    else :
        client.files_upload_v2(
            channel=channel,
            initial_comment=text,
            file=file_path,
            thread_ts=ts
        )

async def rePost(source_token, target_token, source_channel_id, target_channel_id, messages, last_client_msg_id) :
    new_messages = []
    for message in messages :
        if 'client_msg_id' in message :
            if message['client_msg_id'] == last_client_msg_id :
                break
            else :
                new_messages.append(message)

    source_client = WebClient(token=source_token)
    target_client = WebClient(token=target_token)

    reversed_messages = list(reversed(new_messages))
    for message in reversed_messages :
        response = source_client.users_profile_get(user=message['user'])
        display_name = response["profile"]["real_name"]
        icon_url = "https://ui-avatars.com/api/?background=0D8ABC&color=fff&name=" + display_name
        if 'image_original' in response['profile'] :
            icon_url = response['profile']['image_original']

        if 'files' in message :
            print('file')
            for index, file in enumerate(message['files']) :
                file_url = file['url_private']
                file_name = file['name']
                file_res = requests.get(
                    file_url,
                    headers={'Authorization': 'Bearer ' + source_token}
                )
                print(file_res.status_code)

                file_path = os.getcwd() + '/uploads/' + file_name
                if file_res.status_code == 200 :
                    with open(file_path, 'wb') as f :
                        f.write(file_res.content)

                display_text = '*@' + display_name + '* mentioned. :mega:'
                if index == 0 :
                    text = display_text + '\n' + message['text']
                else :
                    text = ''

                await fileUpload(target_client, target_channel_id, text, file_path, '')
                # try :
                #     file_res = target_client.files_upload_v2(
                #         channel=target_channel_id,
                #         initial_comment=text,
                #         file=file_path,
                #     )
                # except Exception as e :
                #     print({e})

                # target_ts = file_res['files'][index]['shares']['public'][target_channel_id][0]['ts']
                try :
                    os.remove(file_path)
                except FileNotFoundError :
                    print(f"{file_path} not found !")
                except Exception as e :
                    print(f"An error occurred while deleting the file : {e}")

            # query = "INSERT INTO conversation ( source_channel_id, target_channel_id, source_ts, target_ts ) VALUES ( %s, %s, %s, %s )"
            # DB_CURSOR.execute(query, (source_channel_id, target_channel_id, message['ts'], target_ts))
            # DB_CONN.commit()
        else :
            print('not file')
            response = target_client.chat_postMessage(
                channel=target_channel_id,
                text=message['text'],
                icon_url=icon_url,
                username=display_name
            )
            assert response["message"]["text"] == message['text']
            query = "INSERT INTO conversation ( source_channel_id, target_channel_id, source_ts, target_ts ) VALUES ( %s, %s, %s, %s )"
            DB_CURSOR.execute(query, (source_channel_id, target_channel_id, message['ts'], response['ts']))
            DB_CONN.commit()

async def getMessageHistory(source_token, target_token, source_channel_id, target_channel_id) :
    source_client = WebClient(token=source_token)

    try :
        response = source_client.conversations_history(
            channel=source_channel_id,
            limit=limit
        )
        messages = response["messages"]

        if len(messages) == 0 :
            return

        last_message = None
        for message in messages :
            if 'client_msg_id' in message :
                last_message = message
                break

        if last_message is None :
            return

        query = "SELECT * FROM message_last_status WHERE source_channel_id = %s AND target_channel_id = %s AND is_thread = 0"
        DB_CURSOR.execute(query, (source_channel_id, target_channel_id))
        response = DB_CURSOR.fetchall()

        if len(response) == 0 :
            query = "INSERT INTO message_last_status ( source_channel_id, target_channel_id, last_msg_id, last_thread_ts, is_thread ) VALUES ( %s, %s, %s, NULL, 0 )"
            DB_CURSOR.execute(query, ( source_channel_id, target_channel_id, last_message['client_msg_id'] ))
        else :
            query = "UPDATE message_last_status SET last_msg_id = %s WHERE source_channel_id = %s AND target_channel_id = %s AND is_thread = 0"
            DB_CURSOR.execute(query, (last_message['client_msg_id'], source_channel_id, target_channel_id))
            if response[0][3] is not None and response[0][3] != last_message['client_msg_id'] :
                await rePost(source_token, target_token, source_channel_id, target_channel_id, messages, response[0][3])
        DB_CONN.commit()

    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

async def rePostThreads(source_token, target_token, source_channel_id, target_channel_id, thread_messages, latest_thread_ts) :
    source_client = WebClient(token=source_token)
    target_client = WebClient(token=target_token)

    new_thread_messages = []
    for message in thread_messages :
        if message['latest_reply'] > latest_thread_ts :
            new_thread_messages.append(message)

    for message in new_thread_messages :
        response = source_client.conversations_replies(
            channel=source_channel_id,
            ts=message['thread_ts'],
            oldest=latest_thread_ts,
        )
        repost_messages = response['messages']

        DB_CURSOR.execute("SELECT * FROM conversation WHERE source_ts = %s", message['thread_ts'])
        response = DB_CURSOR.fetchall()

        if len(response) == 0 :
            continue
        else :
            repost_ts = response[0][4]
            for repost_message in repost_messages :
                if 'parent_user_id' in repost_message :
                    user_response = source_client.users_profile_get(user=repost_message['user'])
                    display_name = user_response["profile"]["real_name"]
                    icon_url = "https://ui-avatars.com/api/?background=0D8ABC&color=fff&name=" + display_name
                    if 'image_original' in user_response['profile'] :
                        icon_url = user_response['profile']['image_original']

                    if 'files' in repost_message :
                        for index, file in enumerate(repost_message['files']) :
                            file_url = file['url_private']
                            file_name = file['name']
                            file_res = requests.get(
                                file_url,
                                headers={'Authorization': 'Bearer ' + source_token}
                            )
                            print(file_res.status_code)

                            file_path = os.getcwd() + '/uploads/' + file_name
                            if file_res.status_code == 200 :
                                with open(file_path, 'wb') as f :
                                    f.writable(file_res.content)

                            display_text = '*@' + display_name + '* mentioned. :mega:'
                            if index == 0 :
                                text = display_text + '\n' + repost_message['text']
                            else :
                                text = ''

                            await fileUpload(target_client, target_channel_id, text, file_path, repost_ts)
                            # try :
                            #     file_res = target_client.files_upload_v2(
                            #         channel=target_channel_id,
                            #         initial_comment=text,
                            #         file=file_path,
                            #         thread_ts=repost_ts
                            #     )
                            # except Exception as e :
                            #     print({e})

                            try :
                                os.remove(file_path)
                            except FileNotFoundError :
                                print(f"{file_path} not found !")
                            except Exception as e :
                                print(f"An error occurred while deleting the file : {e}")
                    else :
                        repost_response = target_client.chat_postMessage(
                            channel=target_channel_id,
                            thread_ts=repost_ts,
                            text=repost_message['text'],
                            icon_url=icon_url,
                            username=display_name
                        )
                        assert repost_response["message"]["text"] == repost_message['text']

async def getThreadMessageHistory(source_token, target_token, source_channel_id, target_channel_id) :
    source_client = WebClient(token=source_token)

    try :
        response = source_client.conversations_history(
            channel=source_channel_id,
            limit=limit
        )
        messages = response["messages"]

        if len(messages) == 0 :
            return

        thread_messages = []
        for message in messages :
            if 'thread_ts' in message :
                thread_messages.append(message)

        if len(thread_messages) == 0 :
            return

        latest_thread_ts = thread_messages[0]['latest_reply']
        for message in thread_messages :
            if latest_thread_ts < message['latest_reply'] :
                latest_thread_ts = message['latest_reply']

        query = "SELECT * FROM message_last_status WHERE source_channel_id = %s AND target_channel_id = %s AND is_thread = 1"
        DB_CURSOR.execute(query, (source_channel_id, target_channel_id))
        response = DB_CURSOR.fetchall()

        if len(response) == 0 :
            query = "INSERT INTO message_last_status ( source_channel_id, target_channel_id, last_msg_id, last_thread_ts, is_thread ) VALUES ( %s, %s, NULL, %s, 1 )"
            DB_CURSOR.execute(query, ( source_channel_id, target_channel_id, latest_thread_ts ))
        else :
            query = "UPDATE message_last_status SET last_thread_ts = %s WHERE source_channel_id = %s AND target_channel_id = %s AND is_thread = 1"
            DB_CURSOR.execute(query, (latest_thread_ts, source_channel_id, target_channel_id))
            if response[0][4] is not None and latest_thread_ts > response[0][4]  :
                await rePostThreads(source_token, target_token, source_channel_id, target_channel_id, thread_messages, response[0][4])
        DB_CONN.commit()

    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

async def syncMessage(source_token, target_token) :
    source_client = WebClient(token=source_token)
    target_client = WebClient(token=target_token)

    source_channel_list = []
    target_channel_list = []
    source_response = source_client.conversations_list()
    source_channel_list = source_response['channels']
    target_response = target_client.conversations_list()
    target_channel_list = target_response['channels']

    for source_channel in source_channel_list :
        for target_channel in target_channel_list :
            if source_channel['name'] == target_channel['name'] :
                await getMessageHistory(source_token, target_token, source_channel['id'], target_channel['id'])
                await getThreadMessageHistory(source_token, target_token, source_channel['id'], target_channel['id'])

async def main() :
    await syncMessage(SOURCE_BOT_TOKEN, TARGET_BOT_TOKEN)
    await syncMessage(TARGET_BOT_TOKEN, SOURCE_BOT_TOKEN)

asyncio.run(main())
