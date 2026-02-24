import os
import sys
import time
import asyncio
import logging
import datetime
import random
import json
from pathlib import Path
from dotenv import load_dotenv
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand


#Todo--
# Legend:
#   (-) = Started
#   (x) = Not Started
#   Remove when completed
# Phase 1:
#    -(x)add givepoints command for users to transfer their points to another user
#    -(x)add addpoints streamer/mod only command
#    -(x)add jail command(5 minute timeout)
#    -(x)add fight command for user fighting
#    -(x)add more fish to "ocean"
#    -(-)add hype event trigger
#    -(x)change followage to accurately track follow age
#    -(x)fix shoutout to accurately post shoutouts
#    -(-)add history in user docs for commands
# Phase 2:
#    -(x)add user logging(in on_messages[each message resets a timer for the user, if timer(600) is expired, they are removed from the log, thereby making them unable to be targeted in minigames])
#    -(x)add marathon timer controls(all converted to seconds for easier manipulation):
#      addtime (int)
#      remtime (int)
#      pausetime (int)
#      acceltime (int)
#      slowtime (int)
#      setmstate(current timer state[normal, slow, accel, paused])
#      setmmax(max marathon length)
#      setmtitle(marathon title)
#      startm(begin timer countdown)
#      stopm(stop marathon timer)
#      beginpower(starts 2x power hour[nonreversible])
#      lube(applies 2x for 5 minutes[can be stacked])
#      hype(triggered by hype event[multiply all times added or removed by hype level])
#      sethype(timer[int], level[int], for manual hype trigger)
#    -(x)add 'dadjoke' command comprised of long list of jokes(use dict)
#    -(x)add 'setgame' command for stream update in chat
#    -(x)add 'settitle' command for stream title
#    -(x)add 'setcategory' command for stream category
#    -(x)add inventory command for fish and dino games(use whisper)
#    -(x)fix bot restart(not included in bot[commented out, line 1807)
#    -(x)dino minigame
#    -(x)add youtubeapi
# Phase 3:
#    -(x)add tiktok api
#    -(x)add kick api
#    -(x)dino fighting
#    -(x)Hunting
# Phase 4:
#    -(x)Dino Store
# Phase 5(Mullensbot only):
#    -(x)Travel
#    -(x)Quest


if getattr(sys, 'frozen', False):
    folder_name = os.getenv("bot_name")

    if sys.platform == "win32":
        from ctypes import windll, create_unicode_buffer
        buf = create_unicode_buffer(260)

        if windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            data_path = f"{Path(buf.value)}\\{folder_name}\\"
        else:
            data_path = f"{Path(os.environ['USERPROFILE']) / 'Documents'}\\{folder_name}\\"
    else:
        data_path = f"{Path.home() / 'Documents'}\\{folder_name}\\"
else:
    data_path = f"{os.path.dirname(__file__)}\\"


logs_directory = f"{data_path}\\logs\\"
archive_logs_directory = f"{logs_directory}archive_log\\"
user_directory = f"{data_path}users\\"
chat_directory = f"{data_path}chat\\"
inventory_dir = f"{data_path}user_inventory\\"
bet_directory = f"{data_path}bet\\"
history_dir = f"{data_path}history\\"
bet_history = f"{history_dir}bet\\"
fish_history = f"{history_dir}fish\\"
Path(logs_directory).mkdir(parents=True, exist_ok=True)
Path(archive_logs_directory).mkdir(parents=True, exist_ok=True)
Path(user_directory).mkdir(parents=True, exist_ok=True)
Path(chat_directory).mkdir(parents=True, exist_ok=True)
Path(inventory_dir).mkdir(parents=True, exist_ok=True)
Path(bet_directory).mkdir(parents=True, exist_ok=True)
Path(history_dir).mkdir(parents=True, exist_ok=True)
Path(bet_history).mkdir(parents=True, exist_ok=True)
Path(fish_history).mkdir(parents=True, exist_ok=True)

load_dotenv()
bot_id = os.getenv("twitch_client")
bot_secret = os.getenv("twitch_secret")
bot_name = os.getenv("bot_name")
channel_name = os.getenv("channel_name")
discord = os.getenv("discord")
chat_file = os.path.join(chat_directory, "chat-log.txt")
user_log = os.path.join(chat_directory, "user-log.txt")
bet_log = os.path.join(bet_directory, "pot.json")
channel_doc = os.path.join(data_path, "channel_doc.json")


#-----Chat Log Creation
try:
    with open(chat_file, "x") as f:
        f.write("Date|Time|User-ID|User-Name|Message")
except FileExistsError:
    pass
#-----End Chat Log Creation

#-----userlog creation
try:
    with open(user_log, "x") as f:
        f.write("")
except FileExistsError:
    pass
#-----end userlog creation

#-----bet pot creation
if not os.path.exists(bet_log):
    default_data = {
        "value": 10000
    }
    with open(bet_log, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4)
else:
    pass
#-----end bet pot creation

#-----channel doc creation
if not os.path.exists(channel_doc):
    default_data = {
        "channel_name": channel_name,
        "marathon_mode": "off",
        "marathon_time_max": "0",
        "marathon_timer_path": "none",
        "autocast": "enabled"
    }
    with open(channel_doc, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4)
else:
    pass
#-----end channel doc creation

logger_list = []
target_scopes = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.USER_BOT, AuthScope.USER_WRITE_CHAT]
target_channel = channel_name
target_id = os.getenv("id_streamer")
nl = "\n"
long_dashes = "-------------------------------------------------------------------"


#-----tier 0 items valued 5 to 15
fish_items_tier0 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Shark", "points": 0}
]

#-----tier 1 items valued 5 to 25
fish_items_tier1 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Squid", "points": 25},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Shark", "points": 0}
]

#-----tier 2 items valued 5 to 50
fish_items_tier2 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Squid", "points": 25},
    {"item": "Clam", "points": 35},
    {"item": "Lobster", "points": 35},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Gold Coin", "points": 50},
    {"item": "Shark", "points": 0}
]

#-----tier 3 items valued 5 to 100
fish_items_tier3 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Squid", "points": 25},
    {"item": "Clam", "points": 35},
    {"item": "Lobster", "points": 35},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Orca", "points": 100},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Gold Coin", "points": 50},
    {"item": "Gold Bar", "points": 100},
    {"item": "Shark", "points": 0}
]

#-----tier 4 items valued 5 to 200
fish_items_tier4 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Squid", "points": 25},
    {"item": "Clam", "points": 35},
    {"item": "Lobster", "points": 35},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Orca", "points": 100},
    {"item": "Humpback Whale", "points": 150},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Gold Coin", "points": 50},
    {"item": "Gold Bar", "points": 100},
    {"item": "Bag of Gold", "points": 200},
    {"item": "Shark", "points": 0}
]

#-----tier 5 items valued 5 to 500(final)
fish_items_tier5 = [
    {"item": "Trout", "points": 5},
    {"item": "Catfish", "points": 15},
    {"item": "Salmon", "points": 5},
    {"item": "Perch", "points": 5},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 10},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 5},
    {"item": "Bluegill", "points": 5},
    {"item": "Squid", "points": 25},
    {"item": "Clam", "points": 35},
    {"item": "Lobster", "points": 35},
    {"item": "Eel", "points": 5},
    {"item": "Clown Fish", "points": 10},
    {"item": "Orca", "points": 100},
    {"item": "Humpback Whale", "points": 150},
    {"item": "Lost Smartphone", "points": 5},
    {"item": "Gold Coin", "points": 50},
    {"item": "Gold Bar", "points": 100},
    {"item": "Bag of Gold", "points": 200},
    {"item": "Chest of Gold", "points": 500},
    {"item": "Shark", "points": 0},
    {"item": "Health Jar", "points": 0}
]


class BotSetup(Twitch):
    def __init__(self, app_id: str, app_secret: str):
        super().__init__(app_id, app_secret)
        self.bot = Twitch


#Clears single line(use for logger entry timer on console)
#def delete_last_line():
#   sys.stdout.write('\x1b[1A')
#   sys.stdout.write('\x1b[2K')


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


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


USERS_FILE = f"{data_path}users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def xp_required(level: int) -> int:
    return int(100 * (level ** 1.45))


def add_xp(user_id: str, user_name: str, amount: int):
    users = load_users()

    if user_id not in users:
        users[user_id] = {
            "id": user_id,
            "name": user_name,
            "date_followed": fortime(),
            "level": 0,
            "xp": 0,
            "lurking": False,
            "points": 0,
            "fishtier": 0,
            "autocasts": 0,
            "casting": False,
            "inventory": 0,
            "lives": 3
        }

    user = users[user_id]
    user["xp"] += amount

    leveled_up = False

    while user["xp"] >= xp_required(user["level"]):
        user["xp"] -= xp_required(user["level"])
        user["level"] += 1
        leveled_up = True

    save_users(users)
    return leveled_up


#-----events
async def on_ready(ready_event: EventData):
    try:
        await ready_event.chat.join_room(target_channel)
        logger.info(f"{fortime()}: Connected to {target_channel} channel")
        await bot.send_chat_message(target_id, user.id, "Mullensbot is live...")
    except Exception as e:
        logger.error(f"{fortime()}: Failed to connect to {target_channel} channel -- {e}")


async def handle_cheer(event, user_data):
    user_id = event["user_id"]
    bits = event["bits"]
    user_name = event["user_name"]
    xp_gain = bits / 2
    points_gain = bits * 1.5
    filename = f"{user_directory}{user_id}.json"
    with open(filename, "r") as f:
        user_data = json.load(f)

    current_xp = user_data['xp']
    current_points = user_data['points']
    new_xp = current_xp + xp_gain
    new_points = points_gain + current_points
    user_data['xp'] = new_xp
    user_data['points'] = new_points
    with open(filename, "w", encoding="utf-8")as f:
        json.dump(user_data, f, indent=4)
    await bot.send_chat_message(target_id, user.id, f"{user_name} cheered {bits} bits. Thank you {user_name} for the support.")
    logger.info(f"{fortime()}: {user_name} Cheered {bits} bits.")

async def xp_level_check(user_id: str, user_name: str):
    filename = f"{user_directory}{user_id}.json"

    with open(filename, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    level = user_data["level"]
    xp = user_data["xp"]

    # Exponential XP curve (recommended)
    def required_xp_for(level: int) -> int:
        return int(500 * (1.25 ** level))

    leveled_up = False

    # Multi-level loop
    while xp >= required_xp_for(level):
        xp -= required_xp_for(level)
        level += 1
        leveled_up = True

    # Save only if something changed
    if leveled_up:
        user_data["level"] = level
        user_data["xp"] = xp

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4)

        await bot.send_chat_message(
            target_id,
            user.id,
            f"{user_name} leveled up to level {level}!"
        )

        logger.info(f"{fortime()}: {user_name} leveled up to {level}")


async def on_message(msg: ChatMessage):
    if msg.text.startswith("!lurk") or msg.text.startswith("!unlurk"):
        return

    try:
        user_id = msg.user.id
        user_name = msg.user.display_name
        amount = 5

        filename  = f"{user_directory}{user_id}.json"
        filename2 = f"{inventory_dir}{user_id}.json"

        # --- Default templates ---
        user_default_data = {
            "name": user_name,
            "date_followed": fortime(),
            "level": 0,
            "xp": 0,
            "lurking": False,
            "points": 0,
            "fishtier": 0,
            "autocasts": 0,
            "casting": False,
            "inventory": 0,
            "lives": 3
        }

        user_inventory_default_data = {
            "name": user_name,
            "Trout": 0, "Catfish": 0, "Salmon": 0, "Perch": 0, "Tuna": 0,
            "Walleye": 0, "Crab": 0, "Small Mouth Bass": 0, "Large Mouth Bass": 0,
            "Carp": 0, "Bluegill": 0, "Squid": 0, "Clam": 0, "Lobster": 0,
            "Eel": 0, "Clown Fish": 0, "Orca": 0, "Humpback Whale": 0,
            "Lost Smartphone": 0, "Gold Coin": 0, "Gold Bar": 0,
            "Bag of Gold": 0, "Chest of Gold": 0, "Shark": 0
        }

        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_default_data, f, indent=4)
            logger.info(f"{fortime()}: Created {filename}")
            await bot.send_chat_message(target_id, user_id, f"Welcome {user_name}, this is their first appearance!!!")

        if not os.path.exists(filename2):
            with open(filename2, "w", encoding="utf-8") as g:
                json.dump(user_inventory_default_data, g, indent=4)
            logger.info(f"{fortime()}: Created inventory file for {user_id}")

        # --- Load user profile ---
        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        if user_data["name"] != user_name:
            user_data["name"] = user_name
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
            logger.info(f"{fortime()}: Username change detected and updated")
            if user_data["lurking"]:
                await command_unlurk(msg.user.id, msg.user.display_name)

        elif user_data["lurking"]:
           await command_unlurk(msg.user.id, msg.user.display_name)

        else:
            user_data["xp"] += amount
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)

            logger.info(f"{fortime()}: Updated {filename}")
            await xp_level_check(user_id, user_name)

        # --- Chat log ---
        date = datetime.datetime.now().strftime("%y-%m-%d")
        time = datetime.datetime.now().strftime("%H:%M:%S")
        with open(chat_file, "a", encoding="utf-8") as f:
            f.write(f"{date}|{time}|{user_id}|{user_name}|{msg.text}\n")

        logger.info(f"{fortime()}: Updated chat log")

    except Exception as e:
        logger.info(f"{fortime()}: There was an error handling chat -- {e}")

async def on_sub(sub: ChatSub):
    try:
        user_id = sub.user.id
        user_name = sub.user.display_name
        amount = 100
        filename = f"{user_directory}{user_id}.json"
        filename2 = f"{inventory_dir}{user_id}.json"

        # --- Default templates ---
        user_default_data = {
            "name": user_name,
            "date_followed": fortime(),
            "level": 0,
            "xp": 0,
            "lurking": False,
            "points": 0,
            "fishtier": 0,
            "autocasts": 0,
            "casting": False,
            "inventory": 0,
            "lives": 3
        }

        user_inventory_default_data = {
            "name": user_name,
            "Trout": 0, "Catfish": 0, "Salmon": 0, "Perch": 0, "Tuna": 0,
            "Walleye": 0, "Crab": 0, "Small Mouth Bass": 0, "Large Mouth Bass": 0,
            "Carp": 0, "Bluegill": 0, "Squid": 0, "Clam": 0, "Lobster": 0,
            "Eel": 0, "Clown Fish": 0, "Orca": 0, "Humpback Whale": 0,
            "Lost Smartphone": 0, "Gold Coin": 0, "Gold Bar": 0,
            "Bag of Gold": 0, "Chest of Gold": 0, "Shark": 0
        }
        
        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_default_data, f, indent=4)
            logger.info(f"{fortime()}: Created {filename}")

        if not os.path.exists(filename2):
            with open(filename2, "w", encoding="utf-8") as g:
                json.dump(user_inventory_default_data, g, indent=4)
            logger.info(f"{fortime()}: Created inventory file for {user_id}")

        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        user_data["xp"] += amount
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4)

        logger.info(f"{fortime()}: Updated {filename}")
        await xp_level_check(user_id, user_name)

    except Exception as e:
        logger.info(f"{fortime()}: Error handling sub -- {e}")
#-----end Events


#--------Simple Commands----------#
async def command_discord(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        await cmd.reply(f"Follow my server on Discord: {discord}")


async def command_shoutout(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        try:
            so_user = cmd.text.replace("!so ", "")

            await cmd.reply(f"Shout out was given to {so_user}. Join me in following them, they are awesome")
        except Exception as e:
            logger.info(f"{fortime()}: Could not shoutout {so_user} - {e}")


async def command_joe(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        await cmd.reply("FUCK YOU JOE, you asshole!!")


async def command_slap(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_slap = cmd.text.lstrip("!slap ")
        try:
            if cmd_slap.startswith("@"):
                target = cmd_slap
                await cmd.reply(f"{cmd.user.display_name} slapped {target} because they felt like it!")
            else:
                await cmd.reply(f"{cmd.user.display_name} slapped the streamer because they felt like it!")
        except Exception as e:
            logger.info(f"{fortime()}: Error in slap_command -- {e}")


async def command_followed_on(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_id = cmd.user.id
        filename = f"{user_directory}{user_id}.json"

        try:
            # Read existing data
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            date_followed = user_data["date_followed"]
            await cmd.reply(f"{cmd.user.display_name}, you followed on {date_followed}")
        except Exception as e:
            logger.info(f"{fortime()}: Could not load {user_id}'s follow date - {e}")
            await cmd.reply(f"{cmd.user.display_name}, I could not load your document, my bad...")


async def command_lurk(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        if cmd.user.id == target_id:
            return
        try:
            filename = f"{user_directory}{cmd.user.id}.json"
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            if user_data["lurking"] == False:
                user_data["lurking"] = True
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, indent=4)
                await cmd.reply(f"{cmd.user.display_name} has left the chat!")
            else:
                pass
        except Exception as e:
            logger.info(f"{fortime()}: Error in lurk_command -- {e}")


async def command_unlurk(user_id: str, user_name: str):
    if user_id == target_id:
        return
    try:
        filename = f"{user_directory}{user_id}.json"
        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        if user_data["lurking"] == True:
            user_data["lurking"] = False
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
            await bot.send_chat_message(target_id, user.id, f"{user_name} has returned to the chat!")
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in unlurk_command -- {e}")


async def command_pointscheck(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_id = cmd.user.id
        filename = f"{user_directory}{user_id}.json"

        try:
            # Read existing data
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            points = user_data["points"]
            await cmd.reply(f"{cmd.user.display_name}, you have {points} points")
        except Exception as e:
            logger.info(f"{fortime()}: Could not load {user_id}'s points - {e}")
            await cmd.reply(f"{cmd.user.display_name}, I could not load your points, my bad...")


async def command_xpcheck(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_id = cmd.user.id
        filename = f"{user_directory}{user_id}.json"

        try:
            # Read existing data
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            xp = user_data["xp"]
            await cmd.reply(f"{cmd.user.display_name}, you have {xp} xp")
        except Exception as e:
            logger.info(f"{fortime()}: Could not load {user_id}'s xp - {e}")
            await cmd.reply(f"{cmd.user.display_name}, I could not load your xp, my bad...")


async def command_levelcheck(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_id = cmd.user.id
        filename = f"{user_directory}{user_id}.json"

        try:
            # Read existing data
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            level = user_data["level"]
            await cmd.reply(f"{cmd.user.display_name}, your level is {level}")
        except Exception as e:
            logger.info(f"{fortime()}: Could not load {user_id}'s level - {e}")
            await cmd.reply(f"{cmd.user.display_name}, I could not load your level, my bad...")


async def command_kick(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_kick = cmd.text.lstrip("!kick ")
        try:
            if cmd_kick.startswith("@"):
                target = cmd_kick
                await cmd.reply(f"{cmd.user.display_name} kicked {target} because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} kicked the streamer because they felt like it!")
        except Exception as e:
            logger.info(f"{fortime()}: Error in kick_command -- {e}")


async def command_bite(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        bite_items = [
            {"item": "Joe's Mouth"},
            {"item": "Viper Fangs"},
            {"item": "Dracula's Mouth"},
            {"item": "with love"}
        ]
        bite_item = random.choice(bite_items)
        cmd_bite = cmd.text.lstrip("!bite ")
        try:
            if cmd_bite.startswith("@"):
                target = cmd_bite
                await cmd.reply(f"{cmd.user.display_name} bit {target} with {bite_item['item']}")
            else:
                await cmd.reply(f"{cmd.user.display_name} bit the streamer with {bite_item['item']}")
        except Exception as e:
            logger.info(f"{fortime()}: Error in bite_command -- {e}")


async def command_pinch(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_pinch = cmd.text.lstrip("!pinch ")
        try:
            if cmd_pinch.startswith("@"):
                target = cmd_pinch
                await cmd.reply(f"{cmd.user.display_name} pinched {target} because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} pinched the streamer because they felt like it.")
        except Exception as e:
            logger.info(f"{fortime()}: Error in pinch_command -- {e}")
        

async def command_pp(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_name = cmd.user.display_name
        size = random.randint(1, 15)
        await cmd.reply(f"{user_name}, your pp size is {size} inches...")


async def command_iq(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        user_name = cmd.user.display_name
        iq = random.randint(0, 500)
        await cmd.reply(f"{user_name}, your iq is {iq}...")


async def command_lick(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_lick = cmd.text.lstrip("!lick ")
        try:
            if cmd_lick.startswith("@"):
                target = cmd_lick
                await cmd.reply(f"{cmd.user.display_name} licked {target} because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} licked the streamer because they felt like it.")
        except Exception as e:
            logger.info(f"{fortime()}: Error in lick_command -- {e}")


async def command_pants(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        pant_items = [
            {"item": "Wearing Boxers"},
            {"item": "Wearing Briefs"},
            {"item": "Going Commando"}
        ]

        cmd_pants = cmd.text.lstrip("!pants ")
        try:
            ran_item = random.choice(pant_items)
            if cmd_pants.startswith("@"):
                target = cmd_pants
                await cmd.reply(f"{cmd.user.display_name} pantsed {target} and found them {ran_item['item']}")
            else:
                await cmd.reply(f"{cmd.user.display_name} pantsed the streamer and found them {ran_item['item']}")
        except Exception as e:
            logger.info(f"{fortime()}: Error in pants_command -- {e}")


async def command_pounce(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        pounce_items = [
            {"item": "they looked like a comfy pillow."},
            {"item": "they felt like it."},
            {"item": "they needed cuddles."}
        ]

        cmd_pounce = cmd.text.lstrip("!pounce ")
        try:
            ran_item = random.choice(pounce_items)
            if cmd_pounce.startswith("@"):
                target = cmd_pounce
                await cmd.reply(f"{cmd.user.display_name} pounced {target} because {ran_item['item']}")
            else:
                await cmd.reply(f"{cmd.user.display_name} pounced the streamer because {ran_item['item']}")
        except Exception as e:
            logger.info(f"{fortime()}: Error in pounce_command -- {e}")


async def command_tickle(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_tickle = cmd.text.lstrip("!tickle ")
        try:
            if cmd_tickle.startswith("@"):
                target = cmd_tickle
                await cmd.reply(f"{cmd.user.display_name} tickles {target} because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} tickles the streamer because they felt like it.")
        except Exception as e:
            logger.info(f"{fortime()}: Error in tickle_command -- {e}")


async def command_poke(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_poke = cmd.text.lstrip("!poke ")
        try:
            if cmd_poke.startswith("@"):
                target = cmd_poke
                await cmd.reply(f"{cmd.user.display_name} poked {target} because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} poked the streamer because they felt like it.")
        except Exception as e:
            logger.info(f"{fortime()}: Error in poke_command -- {e}")


async def command_burn(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_burn = cmd.text.lstrip("!burn ")
        try:
            if cmd_burn.startswith("@"):
                target = cmd_burn
                await cmd.reply(f"{cmd.user.display_name} burned {target} with a lighter because they felt like it.")
            else:
                await cmd.reply(f"{cmd.user.display_name} burned the streamer with a lighter because they felt like it.")
        except Exception as e:
            logger.info(f"{fortime()}: Error in burn_command -- {e}")


async def test_internal_command():
    await bot.send_chat_message(target_id, user.id, "Hello, I'm still here...")
#--------End Simple Commands------#


#--------Streamer Only Commands--------#
async def command_cast_initiate():
    try:
        with open(channel_doc, "r", encoding="utf-8") as f:
            data = json.load(f)
        autocast_enabled = data["autocast"]
        if autocast_enabled == "disabled":
            logger.info(f"{fortime()}: Casting is paused, skipping autocast_initiate")
            pass
        else:
            users = [
                f for f in os.listdir(user_directory)
                if f.endswith(".json")
            ]

            for filename in users:
                filepath = os.path.join(user_directory, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as g:
                        user_data = json.load(g)

                    if user_data.get("casting") == 1:
                        user_id = filename.rstrip(".json")
                        user_name = user_data.get("name")
                        await bot.send_chat_message(target_id, user.id, f"!fish @{user_name}")
                        logger.info(f"{fortime()}: Autocast Initiated for {user_name}")
                        await asyncio.sleep(1.5)
                        await command_autofish(user_id, user_name)

                    continue

                except Exception as e:
                    print(f"Error reading {filename}: {e}")
                    continue

            await asyncio.sleep(1.5)
        logger.info(f"{fortime()}: Cast initiation complete")
    except Exception as e:
        logger.info(f"{fortime()}: Error checking channel_doc in init_cast -- {e}")


async def shutdown_refund():
    users = [
        f for f in os.listdir(user_directory)
        if f.endswith(".json")
    ]

    for filename in users:
        filepath = os.path.join(user_directory, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as g:
                user_data = json.load(g)

            if user_data.get("casting") == 1:
                user_id = filename.rstrip(".json")
                user_name = user_data['name']
                current_points = user_data['points']
                current_casts = user_data['autocasts']
                tier = user_data['fishtier']
                if tier == 1:
                    value = current_casts * 20
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 2:
                    value = current_casts * 30
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 3:
                    value = current_casts * 40
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 4:
                    value = current_casts * 50
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 5:
                    value = current_casts * 60
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                else:
                    logger.info(f"{fortime()}: Error Refunding autocasts for {user_id}")
        except Exception as e:
            logger.info(f"{fortime()}: Error in shutdown_refund -- {e}")


async def reset_command(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id:
            users = [
                f for f in os.listdir(user_directory)
                if f.endswith(".json")
            ]

            for filename in users:
                filepath = os.path.join(user_directory, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as g:
                        user_data = json.load(g)
                    user_name = user_data['name']
                    date_followed = user_data['date_followed']
                    default_data = {
                        "name": f"{user_name}",
                        "date_followed": f"{date_followed}",
                        "level": 0,
                        "xp": 0,
                        "lurking": False,
                        "points": 0,
                        "fishtier": 0,
                        "autocasts": 0,
                        "casting": 0,
                        "inventory": 0,
                        "lives": 3
                    }
                    with open(filepath, "w", encoding="utf-8") as g:
                        json.dump(default_data, g, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.info(f"{fortime()}: error resetting document for {filepath} -- {e}")
            users2 = [
                f for f in os.listdir(inventory_dir)
                if f.endswith(".json")
            ]

            for filename in users2:
                filepath2 = os.path.join(inventory_dir, filename)

                try:
                    with open(filepath2, "r", encoding="utf-8") as g:
                        user_data = json.load(g)
                    user_name = user_data['name']
                    user_inventory_default_data = {
                        "name": f"{user_name}",
                        "Trout": 0,
                        "Catfish": 0,
                        "Salmon": 0,
                        "Perch": 0,
                        "Tuna": 0,
                        "Walleye": 0,
                        "Crab": 0,
                        "Small Mouth Bass": 0,
                        "Large Mouth Bass": 0,
                        "Carp": 0,
                        "Bluegill": 0,
                        "Squid": 0,
                        "Clam": 0,
                        "Lobster": 0,
                        "Eel": 0,
                        "Clown Fish": 0,
                        "Orca": 0,
                        "Humpback Whale": 0,
                        "Lost Smartphone": 0,
                        "Gold Coin": 0,
                        "Gold Bar": 0,
                        "Bag of Gold": 0,
                        "Chest of Gold": 0,
                        "Shark": 0
                    }
                    with open(filepath2, "w", encoding="utf-8") as g:
                        json.dump(user_inventory_default_data, g, ensure_ascii=False, indent=4)
                except Exception as e:
                    logger.info(f"{fortime()}: error resetting document for {filepath2} -- {e}")
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in reset_command -- {e}")


async def command_pause(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id:
            with open(channel_doc, "r", encoding="utf-8") as f:
                data = json.load(f)
            autocast_enabled = data["autocast"]
            if autocast_enabled == "enabled":
                data["autocast"] = "disabled"
                with open(channel_doc, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"{fortime()}: Casting paused")
                await cmd.reply("Casting has been paused by the streamer")
            else:
                logger.info(f"{fortime()}: Casting is already paused")
                await cmd.reply("Casting is already paused...")
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in command_pause, could not pause casting -- {e}")


async def command_resume(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id:
            with open(channel_doc, "r", encoding="utf-8") as f:
                data = json.load(f)
            autocast_enabled = data["autocast"]
            if autocast_enabled == "disabled":
                data["autocast"] = "enabled"
                with open(channel_doc, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"{fortime()}: Casting resumed, initiating momentarily")
                await cmd.reply("Casting has been resumed, initiating momentarily")
                await asyncio.sleep(5)
                await command_cast_initiate()
            else:
                logger.info(f"{fortime()}: Casting is already in progress")
                await cmd.reply("Casting is already in progress...")
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in command_resume, could not resume casting -- {e}")
#--------End--------#


#--------Mini Games---------------#
async def command_bet(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        cmd_bet = cmd.text.lstrip("!bet ")
        try:
            win_chance = 0.33
            start_balance = 10000
            min_cost = 100
            filename = f"{user_directory}{cmd.user.id}.json"
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            current_points = user_data["points"]
            filename2 = f"{bet_directory}pot.json"
            with open(filename2, "r", encoding="utf-8") as f:
                bet_data = json.load(f)
            old_pot = bet_data["value"]
            if current_points < min_cost:
                await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to gamble right now")
                return
            elif current_points >= min_cost:
                bet_roll = random.random() < win_chance

                if bet_roll == False:
                    user_newpoints = user_data["points"] - min_cost
                    user_data["points"] = user_newpoints
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    new_pot = old_pot + min_cost
                    bet_data["value"] = new_pot
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you lost {min_cost} points. Your new points are {user_newpoints}. The total to be won is now {new_pot}.")
                    return
                else:
                    user_newpoints = user_data["points"] + old_pot
                    user_data["points"] = user_newpoints
                    bet_data["value"] = start_balance
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you won {old_pot} points. You now have {user_newpoints} points. Pot total has been reset to {start_balance}")
                    return
        except Exception as e:
            logger.info(f"{fortime()}: Error in bet_command -- {e}")


async def command_fish(cmd: ChatCommand):
    with open(channel_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    autocast_enabled = data['autocast']
    if autocast_enabled == "disabled":
        pass
    else:
        fish_cmd = cmd.text.lstrip("!fish ")
        user_id = cmd.user.id
        try:
            if fish_cmd.endswith("upgrade"):
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                fishtier = user_data["fishtier"]
                if fishtier == 1:
                    points = user_data["points"]
                    if points < 5000:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 2
                        user_data["points"] -= 5000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have successfully upgraded your fishtier for 5000 points, now tier 2")
                elif fishtier == 2:
                    points = user_data["points"]
                    if points < 20000:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 3
                        user_data["points"] -= 20000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 3")
                elif fishtier == 3:
                    points = user_data["points"]
                    if points < 50000:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 4
                        user_data["points"] -= 50000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 4")
                elif fishtier == 4:
                    points = user_data["points"]
                    if points < 100000:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 5
                        user_data["points"] -= 100000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 5(MAX). There are no more upgrades available!")
                else:
                    logger.info(f"{fortime()}: Error upgrading fishtier for {cmd.user.id}")
            elif fish_cmd.startswith("@"):
                username = fish_cmd.lstrip("@")
                file = os.listdir(user_directory)
                for f in file:
                    user_id = f.rstrip(".json")
                    file2 = os.path.join(user_directory, f)
                    with open(file2, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    if user_data['name'] == username:
                        await asyncio.sleep(30)
                        await command_autofish(user_id, username)
                        return
                    else:
                        return
#--------Convert to own command--------#
#            elif fish_cmd.endswith("inventory"):
#                filename = f"{user_directory}{user_id}.json"
#                with open(filename, "r", encoding="utf-8") as f:
#                    user_data = json.load(f)
#                inventory = user_data["inventory"]
#                await cmd.reply(f"{cmd.user.display_name}, you have {inventory} fish in your inventory.")
#--------End Note--------#
            elif fish_cmd.endswith("topup"):
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                current_points = user_data['points']
                current_casts = user_data['autocasts']
                tier = user_data['fishtier']
                if tier == 1:
                    new_casts = 50 - current_casts
                    cost = new_casts * 20
                    if current_points < cost:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 50
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 50 casts remaining.")
                elif tier == 2:
                    new_casts = 100 - current_casts
                    cost = new_casts * 30
                    if current_points < cost:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 100
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 100 casts remaining.")
                elif tier == 3:
                    new_casts = 200 - current_casts
                    cost = new_casts * 40
                    if current_points < cost:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 200
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 200 casts remaining.")
                elif tier == 4:
                    new_casts = 300 - current_casts
                    cost = new_casts * 50
                    if current_points < cost:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 300
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 300 casts remaining.")
                elif tier == 5:
                    new_casts = 400 - current_casts
                    cost = new_casts * 60
                    if current_points < cost:
                        await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 400
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 400 casts remaining.")
                else:
                    logger.info(f"{fortime()}: Error topping up autocasts for {cmd.user.id}")
            elif fish_cmd.endswith("refund"):
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                current_points = user_data['points']
                current_casts = user_data['autocasts']
                tier = user_data['fishtier']
                if tier == 1:
                    value = current_casts * 20
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 2:
                    value = current_casts * 30
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 3:
                    value = current_casts * 40
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 4:
                    value = current_casts * 50
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 5:
                    value = current_casts * 60
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                else:
                    logger.info(f"{fortime()}: Error Refunding autocasts for {cmd.user.id}")
            elif fish_cmd.isdigit():
                casts = int(fish_cmd)
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                tier = user_data["fishtier"]
                if tier == 1:
                    if casts > 50:
                        await cmd.reply(f"{cmd.user.display_name}, you cannot set above 50 casts for your fishtier. Aborting...")
                    else:
                        if user_data["points"] < casts * 20:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 20
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 20} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 2:
                    if casts > 100:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you cannot set above 50 casts for your fishtier. Aborting...")
                    else:
                        if user_data["points"] < casts * 30:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 30
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 30} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 3:
                    if casts > 200:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you cannot set above 50 casts for your fishtier. Aborting...")
                    else:
                        if user_data["points"] < casts * 40:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 40
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 40} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 4:
                    if casts > 300:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you cannot set above 50 casts for your fishtier. Aborting...")
                    else:
                        if user_data["points"] < casts * 50:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 50
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 50} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 5:
                    if casts > 400:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you cannot set above 50 casts for your fishtier. Aborting...")
                    else:
                        if user_data["points"] < casts * 60:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 60
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 60} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                else:
                    return
            else:
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                fishtier = user_data["fishtier"]
                if fishtier == 0:
                    item = random.choice(fish_items_tier0)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    user_data["points"] = new_points
                    user_data["fishtier"] = 1
                    user_data["inventory"] +=1
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    filename2 = f"{inventory_dir}{user_id}.json"
                    with open(filename2, "r", encoding="utf-8") as f:
                        inventory_data = json.load(f)
                    inventory_data[f"{item['item']}"] += 1
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(inventory_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']} points. You now have {new_points} points, and automatically level up to fishtier 1!")
                elif fishtier == 1:
                    item = random.choice(fish_items_tier1)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    user_data["points"] = new_points
                    user_data["inventory"] += 1
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    filename2 = f"{inventory_dir}{user_id}.json"
                    with open(filename2, "r", encoding="utf-8") as f:
                        inventory_data = json.load(f)
                    inventory_data[f"{item['item']}"] += 1
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(inventory_data, f, indent=4)
                    await cmd.reply(f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']} points. You now have {new_points} points!")
                elif fishtier == 2:
                    item = random.choice(fish_items_tier2)
                    if item['item'] == "Shark":
                        if user_data["lives"] == 1:
                            user_data["lives"] = 3
                            user_data["level"] = 0
                            user_data["xp"] = 0
                            user_data["fishtier"] = 0
                            user_data["points"] = 0
                            user_data["autocasts"] = 0
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                        else:
                            current_lives = user_data["lives"]
                            new_lives = current_lives - 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you caught a shark, loosing a life. you now have {new_lives} left...")
                    elif item['item'] == "Health Jar":
                        current_lives = user_data["lives"]
                        new_lives = current_lives + 1
                        user_data["lives"] = new_lives
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives...")
                    else:
                        current_points = user_data["points"]
                        new_points = current_points + item["points"]
                        user_data["points"] = new_points
                        user_data["inventory"] += 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename2 = f"{inventory_dir}{user_id}.json"
                        with open(filename2, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename2, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points!")
                elif fishtier == 3:
                    item = random.choice(fish_items_tier3)
                    if item['item'] == "Shark":
                        if user_data["lives"] == 1:
                            user_data["lives"] = 3
                            user_data["level"] = 0
                            user_data["xp"] = 0
                            user_data["fishtier"] = 0
                            user_data["points"] = 0
                            user_data["autocasts"] = 0
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                        else:
                            current_lives = user_data["lives"]
                            new_lives = current_lives - 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you caught a shark, loosing a life. you now have {new_lives} left...")
                    elif item['item'] == "Health Jar":
                        current_lives = user_data["lives"]
                        new_lives = current_lives + 1
                        user_data["lives"] = new_lives
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives...")
                    else:
                        current_points = user_data["points"]
                        new_points = current_points + item["points"]
                        user_data["points"] = new_points
                        user_data["inventory"] += 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename2 = f"{inventory_dir}{user_id}.json"
                        with open(filename2, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename2, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points!")
                elif fishtier == 4:
                    item = random.choice(fish_items_tier4)
                    if item['item'] == "Shark":
                        if user_data["lives"] == 1:
                            user_data["lives"] = 3
                            user_data["level"] = 0
                            user_data["xp"] = 0
                            user_data["fishtier"] = 0
                            user_data["points"] = 0
                            user_data["autocasts"] = 0
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                        else:
                            current_lives = user_data["lives"]
                            new_lives = current_lives - 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you caught a shark, loosing a life. you now have {new_lives} left...")
                    elif item['item'] == "Health Jar":
                        current_lives = user_data["lives"]
                        new_lives = current_lives + 1
                        user_data["lives"] = new_lives
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives...")
                    else:
                        current_points = user_data["points"]
                        new_points = current_points + item["points"]
                        user_data["points"] = new_points
                        user_data["inventory"] += 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename2 = f"{inventory_dir}{user_id}.json"
                        with open(filename2, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename2, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points!")
                elif fishtier == 5:
                    item = random.choice(fish_items_tier5)
                    if item['item'] == "Shark":
                        if user_data["lives"] == 1:
                            user_data["lives"] = 3
                            user_data["level"] = 0
                            user_data["xp"] = 0
                            user_data["fishtier"] = 0
                            user_data["points"] = 0
                            user_data["autocasts"] = 0
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                        else:
                            current_lives = user_data["lives"]
                            new_lives = current_lives - 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(f"{cmd.user.display_name}, you caught a shark, loosing a life. you now have {new_lives} left...")
                    elif item['item'] == "Health Jar":
                        current_lives = user_data["lives"]
                        new_lives = current_lives + 1
                        user_data["lives"] = new_lives
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives...")
                    else:
                        current_points = user_data["points"]
                        new_points = current_points + item["points"]
                        user_data["points"] = new_points
                        user_data["inventory"] += 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename2 = f"{inventory_dir}{user_id}.json"
                        with open(filename2, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename2, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points!")
                else:
                    logger.info(f"{fortime()}: Error fishing for {cmd.user.id}")
        except Exception as e:
            logger.info(f"{fortime()}: Error in fish_command -- {e}")


async def command_autofish(user_id: str, user_name: str):
    try:
        filename = f"{user_directory}{user_id}.json"
        filename2 = f"{channel_doc}"
        with open(filename2, "r", encoding="utf-8") as f:
            data = json.load(f)
        autocast_enabled = data["autocast"]
        if autocast_enabled == "enabled":
            with open(filename, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            fishtier = user_data["fishtier"]
            if user_data["autocasts"] > 0:
                if fishtier == 1:
                    item = random.choice(fish_items_tier1)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    current_casts = user_data["autocasts"]
                    new_casts = current_casts - 1
                    user_data["points"] = new_points
                    user_data["autocasts"] = new_casts
                    user_data["inventory"] += 1
                    if current_casts == 1:
                        user_data["casting"] = 0
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename3 = f"{inventory_dir}{user_id}.json"
                        with open(filename3, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename3, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
                        return
                    else:
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename3 = f"{inventory_dir}{user_id}.json"
                        with open(filename3, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename3, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                        await asyncio.sleep(120)
                        await command_autofish(user_id, user_name)
                elif fishtier == 2:
                    item = random.choice(fish_items_tier2)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    current_casts = user_data["autocasts"]
                    new_casts = current_casts - 1
                    user_data["points"] = new_points
                    user_data["autocasts"] = new_casts
                    user_data["inventory"] += 1
                    if current_casts == 1:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
                        else:
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
                            return
                    else:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(110)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
                            await asyncio.sleep(110)
                            await command_autofish(user_id, user_name)
                        else:
                            user_data["inventory"] += 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                            await asyncio.sleep(110)
                            await command_autofish(user_id, user_name)
                elif fishtier == 3:
                    item = random.choice(fish_items_tier3)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    current_casts = user_data["autocasts"]
                    new_casts = current_casts - 1
                    user_data["points"] = new_points
                    user_data["autocasts"] = new_casts
                    user_data["inventory"] += 1
                    if current_casts == 1:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
                        else:
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
                            return
                    else:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(100)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
                            await asyncio.sleep(100)
                            await command_autofish(user_id, user_name)
                        else:
                            user_data["inventory"] += 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                            await asyncio.sleep(100)
                            await command_autofish(user_id, user_name)
                elif fishtier == 4:
                    item = random.choice(fish_items_tier4)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    current_casts = user_data["autocasts"]
                    new_casts = current_casts - 1
                    user_data["points"] = new_points
                    user_data["autocasts"] = new_casts
                    user_data["inventory"] += 1
                    if current_casts == 1:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
                        else:
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
                            return
                    else:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(90)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
                            await asyncio.sleep(90)
                            await command_autofish(user_id, user_name)
                        else:
                            user_data["inventory"] += 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                            await asyncio.sleep(90)
                            await command_autofish(user_id, user_name)
                elif fishtier == 5:
                    item = random.choice(fish_items_tier5)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    current_casts = user_data["autocasts"]
                    new_casts = current_casts - 1
                    user_data["points"] = new_points
                    user_data["autocasts"] = new_casts
                    if current_casts == 1:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
                        else:
                            user_data["casting"] = 0
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
                            return
                    else:
                        if item['item'] == "Shark":
                            if user_data["lives"] == 1:
                                user_data["lives"] = 3
                                user_data["level"] = 0
                                user_data["xp"] = 0
                                user_data["fishtier"] = 0
                                user_data["points"] = 0
                                user_data["autocasts"] = 0
                                user_data["casting"] = 0
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(80)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id, f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
                            await asyncio.sleep(80)
                            await command_autofish(user_id, user_name)
                        else:
                            user_data["inventory"] += 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            filename2 = f"{inventory_dir}{user_id}.json"
                            with open(filename2, "r", encoding="utf-8") as f:
                                inventory_data = json.load(f)
                            inventory_data[f"{item['item']}"] += 1
                            with open(filename2, "w", encoding="utf-8") as f:
                                json.dump(inventory_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                            await asyncio.sleep(80)
                            await command_autofish(user_id, user_name)
                else:
                    logger.info(f"{fortime()}: Error fishing for {user_id}")
                    await asyncio.sleep(200)
                    return
            else:
                return
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error reading channel doc for autofish -- {e}")
#--------End Mini Games-----------#


#-----main process-----#
async def run():
    async def shutdown():
        await shutdown_refund()
        chat.stop()
        await asyncio.sleep(1)
        await bot.close()
        logger.info(f"{long_dashes}\nTwitch Processes Shutdown")
        await asyncio.sleep(1)
        logger.info(f"{long_dashes}\nShutdown Sequence Completed")
        await bot.send_chat_message(target_id, user.id, "Mullensbot is leaving the chat...")


#--------Fix this broke shit--------#
#    async def restart_no_autocast():
#        try:
#            await bot.send_chat_message(target_id, user.id, "Bot restarting, please hold all commands...")
#            filename = f"{channel_doc}"
#            with open(filename, "r", encoding="utf-8") as f:
#                data = json.load(f)
#            autocast_new = "disabled"
#            data['autocast'] = autocast_new
#            with open(filename, "w", encoding="utf-8") as f:
#                json.dump(data, f, indent=4)
#            user_input = input("Enter 1 to initiate autocasts\n"
#                               "Enter 0 to shutdown\n")
#
#            if user_input == "":
#                pass
#            elif not user_input.isdigit():
#                print("Not valid, just enter a number")
#            else:
#                user_input = int(user_input)
#                if user_input == 0:
#                    await shutdown()
#                elif user_input == 1:
#                    filename = f"{channel_doc}"
#                    with open(filename, "r", encoding="utf-8") as f:
#                        data = json.load(f)
#                    autocast_new = "enabled"
#                    data['autocast'] = autocast_new
#                    with open(filename, "w", encoding="utf-8") as f:
#                        json.dump(data, f, indent=4)
#                    await asyncio.sleep(2.5)
#                    await run()
#                    await asyncio.sleep(2.5)
#                    await command_cast_initiate()
#                else:
#                    print("Not valid, try again")
#        except KeyboardInterrupt:
#            print("EXITING")
#            await shutdown()
#        except Exception as e:
#            print(f"ERROR!! -- {e}")
#            await shutdown()
#--------End Note--------#

    chat = await Chat(bot)

    #---event activation
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    chat.register_event(ChatEvent.SUB, on_sub)
    #---end event activation

    #---simple command activation
    chat.register_command('bite', command_bite)
    chat.register_command('discord', command_discord)
    chat.register_command('so', command_shoutout)
    chat.register_command('joe', command_joe)
    chat.register_command('slap', command_slap)
    chat.register_command('lurk', command_lurk)
    chat.register_command('datefollowed', command_followed_on)
    chat.register_command('pointscheck', command_pointscheck)
    chat.register_command('checkpoints', command_pointscheck)
    chat.register_command('kick', command_kick)
    chat.register_command('checkxp', command_xpcheck)
    chat.register_command('xpcheck', command_xpcheck)
    chat.register_command('checklevel', command_levelcheck)
    chat.register_command('levelcheck', command_levelcheck)
    chat.register_command('pinch', command_pinch)
    chat.register_command('pp', command_pp)
    chat.register_command('iq', command_iq)
    chat.register_command('poke', command_poke)
    chat.register_command('pants', command_pants)
    chat.register_command('pounce', command_pounce)
    chat.register_command('burn', command_burn)
    chat.register_command('tickle', command_tickle)
    chat.register_command('lick', command_lick)
    #---end simple command activation

    #minigame activation
    chat.register_command('bet', command_bet)
    chat.register_command('fish', command_fish)
    #---end minigame activation

    #---streamer only commands
    chat.register_command('reset', reset_command)
    chat.register_command('pause', command_pause)
    chat.register_command('resume', command_resume)
    #---end


    chat.start()

    await asyncio.sleep(2.5)
    while True:
        cls()
        try:
            user_input = input("Enter 1 To Run Test Command\n"
                               #"Enter 2 To Restart without autocasts\n"
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
#--------Bot Restart(BROKE ASS SHIT)--------#
#                elif user_input == 2:
#                    await restart_no_autocast()
#                    break
#--------End Note--------#
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
                    time.sleep(1)
                    twitch_helper = asyncio.run(auth_bot())
                    user = asyncio.run(get_auth_user_id())
                    if user is not None:
                        asyncio.run(run())
                    break
                else:
                    logger.error(f"{fortime()} You entered {user_input} which is not valid, try again")
    asyncio.run(log_shutdown(logger_list))
