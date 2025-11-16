import os
import sys
import time
import asyncio
import logging
import datetime
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticationStorageHelper
from mongoengine import connect, disconnect_all, DEFAULT_CONNECTION_NAME
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand

if getattr(sys, 'frozen', False):
    application_path = f"{os.path.dirname(sys.executable)}\\_internal"
else:
    application_path = os.path.dirname(__file__)

data_directory = f"{application_path}\\data\\"
logs_directory = f"{data_directory}\\logs\\"
archive_logs_directory = f"{logs_directory}archive_log\\"
db_directory = f"{data_directory}\\databases\\"
Path(data_directory).mkdir(parents=True, exist_ok=True)
Path(logs_directory).mkdir(parents=True, exist_ok=True)
Path(archive_logs_directory).mkdir(parents=True, exist_ok=True)
Path(db_directory).mkdir(parents=True, exist_ok=True)

load_dotenv()
bot_id = os.getenv("twitch_client")
bot_secret = os.getenv("twitch_secret")
mongo_login_string = os.getenv("monlog_string")
mongo_collection = os.getenv("montwi_string")

logger_list = []
target_scopes = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.USER_BOT, AuthScope.USER_WRITE_CHAT]
target_channel = "sir_almullens1991"
target_id = "1090192917"
nl = "\n"
long_dashes = "-------------------------------------------------------------------"

#INITIAL DB SETUP
conn = sqlite3.connect(f"{db_directory}data.db")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, name TEXT NOT NULL, date_followed TEXT, level INTEGER, xp INTEGER, points INTEGER, lurking INTEGER)")
conn.commit()
conn.close()
conn2 = sqlite3.connect(f"{db_directory}chat.db")
cursor2 = conn2.cursor()
cursor2.execute("CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, name TEXT NOT NULL, date TEXT, message TEXT)")
conn2.commit()
conn2.close()
#---


class BotSetup(Twitch):
    def __init__(self, app_id: str, app_secret: str):
        super().__init__(app_id, app_secret)
        self.bot = Twitch


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def connect_mongo(db, alias):
    try:
        client = connect(db=db, host=mongo_login_string, alias=alias)
        logger.info(f"{fortime()}: MongoDB Connected\n{long_dashes}")
        time.sleep(1)
        client.get_default_database(db)
        logger.info(f"{fortime()}: Database Loaded\n{long_dashes}")
        return client
    except Exception as e:
        logger.error(f"{fortime()}: Error Connecting MongoDB -- {e}")
        return None


async def disconnect_mongo():
    try:
        disconnect_all()
        logger.info(f"{long_dashes}\nDisconnected from MongoDB")
    except Exception as e:
        logger.error(f"{fortime()}: Error Disconnection MongoDB -- {e}")
        return


def fortime():
    try:
        return str(datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error creating formatted_time -- {e}")
        return None


async def log_shutdown(logger_list):
    logging.shutdown()
    for entry in logger_list:
        try:
            os.rename(f"{logs_directory}{entry}", f"{archive_logs_directory}{entry}")
            print(f"{entry} moved to archives..")
        except Exception as e:
            print(e)
            pass

def setup_logger(name: str, log_file: str, logger_list: list, level=logging.INFO):
    try:
        local_logger = logging.getLogger(name)
        handler = logging.FileHandler(f"{logs_directory}{log_file}", mode="w", encoding="utf-8")
        if name == "logger":
            console_handler = logging.StreamHandler()
            local_logger.addHandler(console_handler)
        local_logger.setLevel(level)
        local_logger.addHandler(handler)
        logger_list.append(f"{log_file}")
        return local_logger
    except Exception as e:
        formatted_time = fortime()
        print(f"{formatted_time}: ERROR in setup_logger - {name}/{log_file}/{level} -- {e}")
        return None


async def on_ready(ready_event: EventData):
    try:
        await ready_event.chat.join_room(target_channel)
        logger.info(f"{fortime()}: Connected to {target_channel} channel")
        await bot.send_chat_message(target_id, user.id, "Mullensbot is live...")
    except Exception as e:
        logger.error(f"{fortime()}: Failed to connect to {target_channel} channel -- {e}")



async def on_message(msg: ChatMessage):
    conn = sqlite3.connect(f"{db_directory}data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT xp FROM users WHERE uid = ?", (f"{msg.user.id}",))
    result = cursor.fetchone()

    if result is not None:
        current_xp = result[0]
        new_xp = current_xp + 5
        cursor.execute("UPDATE users SET xp = ? WHERE uid = ?",(new_xp, f"{msg.user.id}"))
        conn.commit()
        await command_unlurk(msg.user.id, msg.user.display_name)
    else:
        cursor.execute("INSERT INTO users (uid, name, level, xp, points, lurking) VALUES (?, ?, ?, ?, ?, ?)", (f"{msg.user.id}", f"{msg.user.display_name}", 0, 0, 0, 0))
        conn.commit()
        conn.close()

    conn2 = sqlite3.connect(f"{db_directory}chat.db")
    cursor2 = conn2.cursor()
    cursor2.execute("INSERT INTO chat (uid, name, date, message) VALUES (?, ?, ?, ?)",(f"{msg.user.id}", f"{msg.user.display_name}", f"{datetime.datetime.now()}", f"{msg.text}"))
    conn2.commit()
    conn2.close()

async def on_sub(sub: ChatSub):
    conn = sqlite3.connect(f"{db_directory}data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT xp FROM users WHERE uid = ?", (f"{sub.user.id}",))
    result = cursor.fetchone()

    if result is not None:
        current_xp = result[0]
        new_xp = current_xp + 100
        cursor.execute("UPDATE users SET xp = ? WHERE uid = ?", (new_xp, f"{sub.user.id}"))
        conn.commit()
    else:
        cursor.execute("INSERT INTO users (uid, name, level, xp, points, lurking) VALUES (?, ?, ?, ?, ?, ?)", (f"{sub.user.id}", f"{sub.user.display_name}", 0, 100, 0, 0))
        conn.commit()
        conn.close()

#--------Simple Commands----------#
async def command_joe(cmd: ChatCommand):
    await cmd.reply("FUCK YOU JOE!")

async def command_lurk(data: ChatCommand):
    if data.user.id == user.id:
        return
    else:
        conn = sqlite3.connect(f"{db_directory}data.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET lurking = ? WHERE name = ?", (1, f"{data.user.display_name}"))
        conn.commit()
        await data.reply(f"{data.user.display_name} has returned to the chat...")
        conn.close()

async def command_unlurk(user_id: str, user_name: str):
    if user_id == user.id:
        return
    else:
        conn = sqlite3.connect(f"{db_directory}data.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET lurking = ? WHERE uid = ?", (0, f"{user_id}"))
        conn.commit()
        conn.close()


#--------End Simple Commands------#


#--------Mini Games---------------#
async def command_fish(cmd: ChatCommand):
    await cmd.reply("Fishing isn't available yet")
    pass

#async def command_kick(cmd: ChatCommand):
#    await cmd.reply(f"You kicked {random.user.display_name}")

#--------End Mini Games-----------#

async def test_internal_command():
    await bot.send_chat_message(target_id, user.id, "TEST MSG FROM BOT")


async def run():
    async def shutdown():
        chat.stop()
        await asyncio.sleep(1)
        await bot.close()
        logger.info(f"{long_dashes}\nTwitch Processes Shutdown")
        await asyncio.sleep(1)
        await disconnect_mongo()
        await asyncio.sleep(1)
        logger.info(f"{long_dashes}\nShutdown Sequence Completed")
        await bot.send_chat_message(target_id, user.id, "Mullensbot is leaving the chat...")
    async def restart():
        cls()
        try:
            logger.info(f"{long_dashes}\nBot Initiated...")
            await asyncio.sleep(1)
            cls()
            await bot.send_chat_message(target_id, user.id, "Mullensbot is back...")
            await asyncio.sleep(1)
            cls()
            user_input = input("Enter 1 To Run Test Command\n"
                               "Enter 2 To Restart Bot\n"
                               "Enter 0 To Shutdown Bot\n")
            if user_input == "":
                pass
            elif not user_input.isdigit():
                print("Not valid, just enter a number")
            else:
                user_input = int(user_input)
                if user_input == 0:
                    await shutdown()
                elif user_input == 1:
                    await test_internal_command()
                    pass
                elif user_input == 2:
                    cls()
                    await pause()
                else:
                    print("Not valid, try again")
        except KeyboardInterrupt:
            print("EXITING")
            await shutdown()
        except Exception as e:
            print(f"ERROR!! -- {e}")
            await shutdown()
    async def pause():
        cls()
        try:
            logger.info(f"{long_dashes}\nPausing Bot")
            await asyncio.sleep(1)
            await bot.send_chat_message(target_id, user.id, "Mullensbot will BRB, Patience...")
            await asyncio.sleep(1)
            cls()
            user_input = input("Enter 1 To Restart Bot\n"
                               "Enter 0 To Shutdown Bot\n")
            if user_input == "":
                pass
            elif not user_input.isdigit():
                print("Not valid, just enter a number")
            else:
                user_input = int(user_input)
                if user_input == 0:
                    await shutdown()
                elif user_input == 1:
                    await restart()
                else:
                    print("Not valid, try again")
        except KeyboardInterrupt:
            print("EXITING")
            await shutdown()
        except Exception as e:
            print(f"ERROR!! -- {e}")
            await shutdown()


    chat = await Chat(bot)

    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    chat.register_event(ChatEvent.SUB, on_sub)
    chat.register_command('joe', command_joe)
    chat.register_command('lurk', command_lurk)
    chat.register_command('unlurk', command_unlurk)

    chat.start()

    await asyncio.sleep(2.5)
    while True:
        cls()
        try:
            user_input = input("Enter 1 To Run Test Command\n"
                               "Enter 2 To Restart Bot\n"
                               "Enter 0 To Shutdown Bot\n")
            if user_input == "":
                pass
            elif not user_input.isdigit():
                print("Not valid, just enter a number")
            else:
                user_input = int(user_input)
                if user_input == 0:
                    await shutdown()
                    break
                elif user_input == 1:
                    await test_internal_command()
                elif user_input == 2:
                    cls()
                    await pause()
                    break
                else:
                    print("Not valid, try again")
        except KeyboardInterrupt:
            print("EXITING")
            await shutdown()
            break
        except Exception as e:
            print(f"ERROR!! -- {e}")
            await shutdown()
            break

async def auth_bot():
    twitch_helper = UserAuthenticationStorageHelper(bot, target_scopes)
    await twitch_helper.bind()
    logger.info(f"{fortime()}: Bot Authenticated Successfully!!\n{long_dashes}")
    return twitch_helper


async def get_auth_user_id():
    user = None
    user_info = bot.get_users()
    try:
        async for entry in user_info:
            if type(entry) == TwitchUser:
                user = entry
                break  # Technically should do this to be "safe". Should only ever be ONE entry in here at the point of call...
            else:
                logger.error(f"{fortime()}: Error getting user_id!!")
    except Exception as e:
        logger.error(f"{fortime()}: Error getting users!! -- {e}")
        return None
    return user


if __name__ == "__main__":
    init_time = fortime().replace(' ', '--').replace(':', '-')
    logger = setup_logger("logger", f"main_log--{init_time}.log", logger_list)
    if None in logger_list:
        print(f"One of thee loggers isn't setup right -- {logger} -- Quitting program")
    else:
        bot = BotSetup(bot_id, bot_secret)
        while True:
            cls()
            user_input = input("Enter 1 to start bot\nEnter 0 to exit\n")
            if not user_input.isdigit():
                logger.error(f"{fortime()}: Enter Just A Number, you entered {user_input}")
                time.sleep(1)
            else:
                user_input = int(user_input)
                if user_input == 0:
                    logger.info("Exiting App")
                    break
                elif user_input == 1:
                    logger.info(long_dashes)
                    mongo_db = connect_mongo(mongo_collection, DEFAULT_CONNECTION_NAME)
                    time.sleep(1)
                    if mongo_db is None:
                        logger.error(f"{fortime()}: Error connecting to DB!! Exiting App")
                        break
                    twitch_helper = asyncio.run(auth_bot())
                    user = asyncio.run(get_auth_user_id())
                    if user is not None:
                        asyncio.run(run())
                    break
                else:
                    logger.error(f"{fortime()} You entered {user_input} which is not valid, try again")
    asyncio.run(log_shutdown(logger_list))
