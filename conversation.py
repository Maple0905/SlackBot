import os
import pymysql
import requests
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SOURCE_BOT_TOKEN = os.getenv("SOURCE_BOT_TOKEN")
SOURCE_USER_TOKEN = os.getenv("SOURCE_USER_TOKEN")
TARGET_BOT_TOKEN = os.getenv("TARGET_BOT_TOKEN")
TARGET_USER_TOKEN = os.getenv("TARGET_USER_TOKEN")

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

def rePost(source_token, target_token, source_channel_id, target_channel_id, messages, last_client_msg_id) :
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
            files_len = len(message['files'])
            uploaded_file_res = []
            for index, file in enumerate(message['files']) :
                file_url = file['url_private']
                file_name = file['name']
                file_res = requests.get(
                    file_url,
                    headers={'Authorization': 'Bearer ' + source_token}
                )

                file_path = '/var/www/SlackBot/uploads/' + file_name
                if file_res.status_code == 200 :
                    with open(file_path, 'wb') as f :
                        f.write(file_res.content)

                display_text = '*@' + display_name + '* mentioned. :mega:'
                if index == 0 :
                    text = display_text + '\n' + message['text']
                else :
                    text = ''

                try :
                    file_res = target_client.files_upload_v2(
                        channel=target_channel_id,
                        initial_comment=text,
                        file=file_path,
                    )
                    uploaded_file_res.append(file_res['file'])
                except Exception as e :
                    print({e})

                try :
                    os.remove(file_path)
                except FileNotFoundError :
                    print(f"{file_path} not found !")
                except Exception as e :
                    print(f"An error occurred while deleting the file : {e}")

            time.sleep(6)
            latest_file = uploaded_file_res[0]
            for file in uploaded_file_res :
                if latest_file['timestamp'] < file['timestamp'] :
                    latest_file = file

            file_info = target_client.files_info(file=latest_file['id'])
            target_ts = file_info['file']['shares']['public'][target_channel_id][0]['ts']

            if index == files_len - 1 :
                query = "INSERT INTO conversation ( source_channel_id, target_channel_id, source_ts, target_ts ) VALUES ( %s, %s, %s, %s )"
                DB_CURSOR.execute(query, (source_channel_id, target_channel_id, message['ts'], target_ts))
                DB_CONN.commit()

        else :
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

def getMessageHistory(source_token, target_token, source_channel_id, target_channel_id) :
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
            DB_CONN.commit()
        else :
            query = "UPDATE message_last_status SET last_msg_id = %s WHERE source_channel_id = %s AND target_channel_id = %s AND is_thread = 0"
            DB_CURSOR.execute(query, (last_message['client_msg_id'], source_channel_id, target_channel_id))
            DB_CONN.commit()
            if response[0][3] is not None and response[0][3] != last_message['client_msg_id'] :
                rePost(source_token, target_token, source_channel_id, target_channel_id, messages, response[0][3])

            if target_token == TARGET_BOT_TOKEN :
                target_user_client = WebClient(token=TARGET_USER_TOKEN)
            if target_token == SOURCE_BOT_TOKEN :
                target_user_client = WebClient(token=SOURCE_USER_TOKEN)
            # Edit Message
            edit_messages = []
            for message in messages :
                if 'client_msg_id' in message :
                    if 'edited' in message :
                        edit_messages.append(message)
            if len(edit_messages) != 0 :
                for message in edit_messages :
                    query = "SELECT * FROM conversation WHERE source_ts = %s AND source_channel_id = %s"
                    DB_CURSOR.execute(query, (message['ts'], source_channel_id))
                    response = DB_CURSOR.fetchall()
                    DB_CONN.commit()
                    if len(response) != 0 :
                        target_user_client.chat_update(
                            channel=target_channel_id,
                            ts=response[0][4],
                            text=message['text']
                        )

            # Delete Message
            live_messages = []
            for message in messages :
                if 'client_msg_id' in message :
                    live_messages.append(message['ts'])
            deleted_messages = None
            if len(live_messages) != 0 :
                deleted_messages = ', '.join(live_messages)
            if deleted_messages is not None :
                query = f"SELECT * FROM conversation WHERE source_channel_id = '{source_channel_id}' AND source_ts NOT IN ({deleted_messages})"
                DB_CURSOR.execute(query)
                responses = DB_CURSOR.fetchall()
                DB_CONN.commit()
                print(responses)
                if len(responses) != 0 :
                    for response in responses :
                        print(response)
                        query = "DELETE FROM conversation WHERE source_channel_id = %s AND source_ts = %s"
                        DB_CURSOR.execute(query, (source_channel_id, response[3]))
                        DB_CONN.commit()
                        target_user_client.chat_delete(
                            channel=target_channel_id,
                            ts=response[4]
                        )

    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

def rePostThreads(source_token, target_token, source_channel_id, target_channel_id, thread_messages, latest_thread_ts) :
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

                            file_path = '/var/www/SlackBot/uploads/' + file_name
                            if file_res.status_code == 200 :
                                with open(file_path, 'wb') as f :
                                    f.write(file_res.content)

                            display_text = '*@' + display_name + '* mentioned. :mega:'
                            if index == 0 :
                                text = display_text + '\n' + repost_message['text']
                            else :
                                text = ''

                            try :
                                file_res = target_client.files_upload_v2(
                                    channel=target_channel_id,
                                    initial_comment=text,
                                    file=file_path,
                                    thread_ts=repost_ts
                                )
                            except Exception as e :
                                print({e})

                            try :
                                os.remove(file_path)
                            except FileNotFoundError :
                                print(f"{file_path} not found !")
                            except Exception as e :
                                print(f"An error occurred while deleting the file : {e}")
                            time.sleep(6)
                    else :
                        repost_response = target_client.chat_postMessage(
                            channel=target_channel_id,
                            thread_ts=repost_ts,
                            text=repost_message['text'],
                            icon_url=icon_url,
                            username=display_name
                        )
                        assert repost_response["message"]["text"] == repost_message['text']

def getThreadMessageHistory(source_token, target_token, source_channel_id, target_channel_id) :
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
                rePostThreads(source_token, target_token, source_channel_id, target_channel_id, thread_messages, response[0][4])
        DB_CONN.commit()

    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

def syncMessage(source_token, target_token) :
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
                getMessageHistory(source_token, target_token, source_channel['id'], target_channel['id'])
                getThreadMessageHistory(source_token, target_token, source_channel['id'], target_channel['id'])

def main() :
    syncMessage(SOURCE_BOT_TOKEN, TARGET_BOT_TOKEN)
    syncMessage(TARGET_BOT_TOKEN, SOURCE_BOT_TOKEN)

main()
