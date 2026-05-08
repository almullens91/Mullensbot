import os
import sys
import time
import asyncio
import logging
import datetime
import random
import json
import glob
import shutil
from pathlib import Path
from dotenv import load_dotenv
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand


# Todo
#   Legend:
#     (-) = Started
#     (x) = Not Started
#     Remove when completed
#   Phase 1:
#    -(x)add commands list(priority for carnagebot)
#    -(x)add fight command for user fighting
#    -(x)add more fish to "ocean"
#    -(-)add hype event trigger
#    -(x)change followage to accurately track follow age(currently using stream elements)
#    -(-)add history in user docs for commands
#   Phase 2:
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
#    -(x)dino minigame
#    -(x)add youtubeapi
#   Phase 3:
#    -(x)add TikTok api
#    -(x)add kick api
#    -(x)dino fighting
#    -(x)Hunting
#   Phase 4:
#    -(x)Dino Store
#      armor
#      weapons
#   Phase 5(Mullensbot only):
#    -(x)Travel
#    -(x)Quest
#    -(x)Create Music Player
#      sr command(song request)
#    -(x)Create UI Alerts(popups)

load_dotenv()

def get_data_path() -> Path:
    folder_name = "Mullensbot"
    if getattr(sys, 'frozen', False):
        if sys.platform == "win32":
            try:
                from ctypes import windll, create_unicode_buffer
                buf = create_unicode_buffer(260)
                # noinspection PyUnresolvedReferences  -- This is mostly because #1 old school way of doing this, will work all the way back to windows 95 days. #2 we're on linux now, so there are no windows dll files or any related windows stuff in the sys stuff
                if windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
                    base = Path(buf.value)
                else:
                    base = Path(os.environ["USERPROFILE"]) / "Documents"
            except Exception as e:
                logger.error(f"{fortime()}: Error in 'get_data_path' -- {e}")
                base = Path(os.environ["USERPROFILE"]) / "Documents"
        else:
            base = Path.home() / "Documents"
        return base / folder_name
    else:
        return Path(__file__).parent


data_path = get_data_path()

archive_dir = f"{data_path}/archives/"
backup_dir = f"{data_path}/backups/"
logs_directory = f"{data_path}/logs/"
archive_logs_directory = f"{logs_directory}/archive_log/"
user_directory = f"{data_path}/users/"
chat_directory = f"{data_path}/chat/"
inventory_dir = f"{data_path}/user_inventory/"
bet_directory = f"{data_path}/bet/"
history_dir = f"{data_path}/history/"
checkin_directory = f"{data_path}/checkin/"
bet_history = f"{history_dir}/bet/"
bite_history = f"{history_dir}/bite/"
fish_history = f"{history_dir}/fish/"
iq_history = f"{history_dir}/iq/"
kick_history = f"{history_dir}/kick/"
pinch_history = f"{history_dir}/pinch/"
phone_history = f"{history_dir}/phone/"
pp_history = f"{history_dir}/pp/"
slap_history = f"{history_dir}/slap/"
autocast_tracker = f"{fish_history}/autocasts/"
autocast_archive = f"{autocast_tracker}/archive/"
Path(archive_dir).mkdir(parents=True, exist_ok=True)
Path(backup_dir).mkdir(parents=True, exist_ok=True)
Path(logs_directory).mkdir(parents=True, exist_ok=True)
Path(archive_logs_directory).mkdir(parents=True, exist_ok=True)
Path(user_directory).mkdir(parents=True, exist_ok=True)
Path(chat_directory).mkdir(parents=True, exist_ok=True)
Path(inventory_dir).mkdir(parents=True, exist_ok=True)
Path(bet_directory).mkdir(parents=True, exist_ok=True)
Path(history_dir).mkdir(parents=True, exist_ok=True)
Path(checkin_directory).mkdir(parents=True, exist_ok=True)
Path(bet_history).mkdir(parents=True, exist_ok=True)
Path(bite_history).mkdir(parents=True, exist_ok=True)
Path(fish_history).mkdir(parents=True, exist_ok=True)
Path(iq_history).mkdir(parents=True, exist_ok=True)
Path(pinch_history).mkdir(parents=True, exist_ok=True)
Path(phone_history).mkdir(parents=True, exist_ok=True)
Path(pp_history).mkdir(parents=True, exist_ok=True)
Path(slap_history).mkdir(parents=True, exist_ok=True)
Path(kick_history).mkdir(parents=True, exist_ok=True)
Path(autocast_tracker).mkdir(parents=True, exist_ok=True)
Path(autocast_archive).mkdir(parents=True, exist_ok=True)

bot_id = str(os.getenv("twitch_client"))
bot_secret = os.getenv("twitch_secret")
bot_name = os.getenv("bot_name")
channel_name = os.getenv("channel_name")
discord = os.getenv("discord")
chat_file = os.path.join(chat_directory, "chat-log.txt")
user_log = os.path.join(chat_directory, "user_log.txt")
bet_log = os.path.join(bet_directory, "pot.json")
channel_doc = os.path.join(data_path, "channel_doc.json")
banned_phrases = os.path.join(data_path, "banned_phrases.txt")
bot_doc = os.path.join(data_path, "bot_doc.json")


# -----Bot Doc creation(for resets to work)
if not os.path.exists(bot_doc):
    default_data = {
        "reseting": 0
    }
    with open(bot_doc, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4)
else:
    pass
# -----End bot doc creation


# -----Chat Log Creation
try:
    with open(chat_file, "x") as f:
        f.write("Date|Time|User-ID|User-Name|Message")
except FileExistsError:
    pass
# -----End Chat Log Creation

# -----userlog creation
try:
    with open(user_log, "x") as f:
        f.write("")
except FileExistsError:
    pass
# -----end userlog creation

# -----bet pot creation
if not os.path.exists(bet_log):
    default_data = {
        "value": 10000
    }
    with open(bet_log, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4)
else:
    pass
# -----end bet pot creation

# -----channel doc creation
if not os.path.exists(channel_doc):
    default_data = {
        "channel_name": channel_name,
        "marathon_mode": "off",
        "marathon_time_max": "0",
        "marathon_timer_path": "none",
        "autocast": "enabled",
        "live": 0
    }
    with open(channel_doc, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4)
else:
    pass
# -----end channel doc creation

# -----begin banned phrases creation
if not os.path.exists(banned_phrases):
    with open(banned_phrases, "x", encoding="utf-8") as f:
        f.close()
else:
    pass
# -----end banned phrases creation


logger_list = []
target_scopes = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.USER_BOT, AuthScope.USER_WRITE_CHAT,AuthScope.BITS_READ, AuthScope.CLIPS_EDIT, AuthScope.CHANNEL_BOT,
                 AuthScope.USER_READ_CHAT, AuthScope.CHANNEL_MODERATE, AuthScope.CHANNEL_READ_ADS, AuthScope.CHANNEL_MANAGE_ADS, AuthScope.CHANNEL_READ_GOALS,
                 AuthScope.USER_READ_BROADCAST, AuthScope.CHANNEL_MANAGE_POLLS, AuthScope.USER_MANAGE_WHISPERS, AuthScope.CHANNEL_SUBSCRIPTIONS,
                 AuthScope.CHANNEL_READ_HYPE_TRAIN, AuthScope.MODERATOR_READ_CHATTERS, AuthScope.MODERATOR_READ_FOLLOWERS,
                 AuthScope.CHANNEL_READ_PREDICTIONS, AuthScope.MODERATOR_MANAGE_SHOUTOUTS, AuthScope.CHANNEL_MANAGE_REDEMPTIONS,
                 AuthScope.CHANNEL_READ_SUBSCRIPTIONS, AuthScope.CHANNEL_MANAGE_PREDICTIONS, AuthScope.MODERATOR_MANAGE_BANNED_USERS,
                 AuthScope.MODERATOR_MANAGE_CHAT_MESSAGES, AuthScope.MODERATION_READ, AuthScope.CHANNEL_MANAGE_MODERATORS,
                 AuthScope.MODERATOR_MANAGE_ANNOUNCEMENTS, AuthScope.MODERATOR_MANAGE_WARNINGS]
target_channel = channel_name
target_id = str(os.getenv("id_streamer"))
id_mullens = str(os.getenv("id_mullens"))
id_mullensbot = str(os.getenv("id_mullensbot"))
nl = "\n"
long_dashes = "-------------------------------------------------------------------"


# -----tier 0 items valued 10 to 50
fish_items_tier0 = [
    {"item": "Trout", "points": 20},
    {"item": "Catfish", "points": 45},
    {"item": "Salmon", "points": 50},
    {"item": "Perch", "points": 25},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 20},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Carp", "points": 50},
    {"item": "Bluegill", "points": 25},
    {"item": "Eel", "points": 25},
    {"item": "Clown Fish", "points": 30},
    {"item": "Lost Smartphone", "points": 15},
    {"item": "Shark", "points": 0}
]


# -----tier 1 items valued 10 to 75
fish_items_tier1 = [
    {"item": "Trout", "points": 20},
    {"item": "Catfish", "points": 45},
    {"item": "Salmon", "points": 50},
    {"item": "Perch", "points": 25},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 20},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 50},
    {"item": "Bluegill", "points": 25},
    {"item": "Squid", "points": 25},
    {"item": "Eel", "points": 25},
    {"item": "Clown Fish", "points": 30},
    {"item": "Lost Smartphone", "points": 15},
    {"item": "Shark", "points": 0}
]

# -----tier 2 items valued 5 to 50
fish_items_tier2 = [
    {"item": "Trout", "points": 20},
    {"item": "Catfish", "points": 45},
    {"item": "Salmon", "points": 50},
    {"item": "Perch", "points": 25},
    {"item": "Tuna", "points": 15},
    {"item": "Walleye", "points": 20},
    {"item": "Crab", "points": 25},
    {"item": "Small Mouth Bass", "points": 15},
    {"item": "Large Mouth Bass", "points": 25},
    {"item": "Carp", "points": 50},
    {"item": "Bluegill", "points": 25},
    {"item": "Squid", "points": 25},
    {"item": "Clam", "points": 35},
    {"item": "Lobster", "points": 35},
    {"item": "Eel", "points": 25},
    {"item": "Clown Fish", "points": 30},
    {"item": "Lost Smartphone", "points": 15},
    {"item": "Gold Coin", "points": 50},
    {"item": "Shark", "points": 0}
]

# -----tier 3 items valued 5 to 100
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

# -----tier 4 items valued 5 to 200
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

# -----tier 5 items valued 5 to 500(final)
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


# Clears single line(use for logger entry timer on console)
def delete_last_line():
    time.sleep(5)
    sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()


def delete_last_2lines():
    time.sleep(5)
    sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()
    sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def fortime():
    try:
        return str(datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error creating formatted_time -- {e}")
        return None

def fordate():
    try:
        return str(datetime.datetime.now().strftime('%y-%m-%d'))
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


def track_autocasts(user_id: str, tracker_type: str, casts: int, cost: int, gain: int, end_time: str):
    filename = f"{autocast_tracker}/{user_id}.json"
    if not os.path.exists(filename):
        tracker_default_data = {
            "date": fordate(),
            "time_start": fortime(),
            "time_end": "null",
            "casts": casts,
            "cost": cost,
            "gain": 0,
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(tracker_default_data, f, indent=4)
        logger.info(f"{fortime()}: Created Autocasts Tracker for {user_id}")
        delete_last_line()
    else:
        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        logger.info(f"{fortime()}: Loaded Autocasts Tracker for {user_id}")
        delete_last_line()
        tracker_date = user_data['date']
        time_start = user_data['time_start']
        start_casts = user_data['casts']
        start_cost = user_data['cost']
        start_gain = user_data['gain']
        if tracker_type == "cast":
            new_casts = start_casts + casts
            new_cost = start_cost + cost
            new_gain = start_gain + gain
#            logger.info(f"{fortime()}: Fishing returnede following variables: \n"
#                    f"tracker_date = {tracker_date} {type(tracker_date)}\n"
#                    f"time_start = {time_start} {type(time_start)}\n"
#                    f"new_casts = {new_casts} {type(new_casts)}\n"
#                    f"new_cost = {new_cost} {type(new_cost)}\n"
#                    f"new_gain = {new_gain} {type(new_gain)}\n")
            user_data['date'] = tracker_date
            user_data['time_start'] = time_start
            user_data['time_end'] = end_time
            user_data['casts'] = new_casts
            user_data['cost'] = new_cost
            user_data['gain'] = new_gain
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
        else:
            new_casts = start_casts - casts
            new_cost = start_cost - cost
            new_gain = start_gain - gain
#            logger.info(f"{fortime()}: Fishing returnede following variables: \n"
#                        f"tracker_date = {tracker_date} {type(tracker_date)}\n"
#                        f"time_start = {time_start} {type(time_start)}\n"
#                        f"new_casts = {new_casts} {type(new_casts)}\n"
#                        f"new_cost = {new_cost} {type(new_cost)}\n"
#                        f"new_gain = {new_gain} {type(new_gain)}\n")
            user_data['date'] = tracker_date
            user_data['time_start'] = time_start
            user_data['time_end'] = end_time
            user_data['casts'] = new_casts
            user_data['cost'] = new_cost
            user_data['gain'] = new_gain
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)


# --------Bot Only Commands--------#
async def command_cast_initiate():
    try:
        with open(channel_doc, "r", encoding="utf-8") as f:
            data = json.load(f)
        autocast_enabled = data["autocast"]
        if autocast_enabled == "disabled":
            logger.info(f"{fortime()}: Casting is paused, skipping autocast_initiate")
            delete_last_line()
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
        delete_last_line()
    except Exception as e:
        logger.info(f"{fortime()}: Error checking channel_doc in init_cast -- {e}")
        delete_last_line()


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
                filename2 = f"{autocast_tracker}{user_id}.json"
                if tier == 1:
                    value = int(current_casts) * 5
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id, f"{user_name}, your casts have been refunded due to bot restart.")
                    end_time = f"{fortime()}"
                    gain = 0
                    tracker_type = "refund"
                    track_autocasts(user_id, tracker_type, current_casts, value, gain, end_time)
                    with open(filename2, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    total_casts = user_data['casts']
                    total_cost = user_data['cost']
                    total_gain = user_data['gain']
                    true_gain = int(total_gain) - int(total_cost)
                    await bot.send_chat_message(target_id, user.id,
                        f"{user_name}, during your {total_casts} casts, you gained {true_gain} points.")
                    await asyncio.sleep(1)
                    os.rename(filename2, f"{autocast_archive}/{user_id}_{fortime()}.json")
                elif tier == 2:
                    value = current_casts * 10
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                                                f"{user_name}, your autocasts have been refunded. You recieved {value} points, now having {new_points} points.")
                elif tier == 3:
                    value = current_casts * 15
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                                                f"{user_name}, your autocasts have been refunded. You recieved {value} points, now having {new_points} points.")
                elif tier == 4:
                    value = current_casts * 20
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                                                f"{user_name}, your autocasts have been refunded. You recieved {value} points, now having {new_points} points.")
                elif tier == 5:
                    value = current_casts * 25
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await bot.send_chat_message(target_id, user.id,
                                                f"{user_name}, your autocasts have been refunded. You recieved {value} points, now having {new_points} points.")
                else:
                    logger.info(f"{fortime()}: Error Refunding autocasts for {user_id}")
                    delete_last_line()
        except Exception as e:
            logger.info(f"{fortime()}: Error in shutdown_refund -- {e}")
            delete_last_line()


async def sort_command():
    try:
        with open(user_log, "w", encoding="utf-8") as g:
            g.write("")
            g.close()
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
                user_id = filename.rstrip(".json")

                with open(user_log, "a", encoding="utf-8") as f:
                    f.write(f"{user_name} = {user_id}\n")


                logger.info(f"{fortime()}: Loaded user document({user_name} = {user_id})")
                await asyncio.sleep(1)
            except Exception as e:
                logger.info(f"{fortime()}: Error in sort command -- {e}")
    except Exception as e:
        logger.info(f"{fortime()}: Error in sort command -- {e}")
#--End Bot Commands

# -----events
async def on_ready(ready_event: EventData):
    try:
        await ready_event.chat.join_room(target_channel)
        logger.info(f"{fortime()}: Connected to {target_channel} channel")
    except Exception as e:
        logger.error(f"{fortime()}: Failed to connect to {target_channel} channel -- {e}")


#Begin Cheer Handler(incomplete)
#async def handle_cheer(event, user_data):
#    user_id = event["user_id"]
#    bits = event["bits"]
#    user_name = event["user_name"]
#    xp_gain = bits / 2
#    points_gain = bits * 1.5
#    filename = f"{user_directory}{user_id}.json"
#    with open(filename, "r") as f:
#        user_data = json.load(f)
#
#    current_xp = user_data['xp']
#    current_points = user_data['points']
#    new_xp = current_xp + xp_gain
#    new_points = points_gain + current_points
#    user_data['xp'] = new_xp
#    user_data['points'] = new_points
#    with open(filename, "w", encoding="utf-8") as f:
#        json.dump(user_data, f, indent=4)
#    await bot.send_chat_message(target_id, user.id,
#                                f"{user_name} cheered {bits} bits. Thank you {user_name} for the support.")
#    logger.info(f"{fortime()}: {user_name} Cheered {bits} bits.")
#End Cheer Handler


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
        delete_last_line()


async def on_message(msg: ChatMessage):
    if msg.text.startswith("!"):
        return
    elif msg.text.startswith(f"{bot_name}"):
        return
    else:
        with open(banned_phrases, "r") as file:
            for line in file:
                clean_line = line.strip()
                if clean_line in msg.text:
                    logger.info(f"{fortime()}: {clean_line} found in message from {msg.user.id}, they have been banned.")
                    await bot.ban_user(target_id, target_id, msg.user.id, reason="Banned phrase in chat", duration=86400)
                    await bot.send_chat_message(target_id, user.id, f"{msg.user.display_name}, you have used a banned term, you are hereby banned. Good bye")
                    break
                else:
                    try:
                        user_id = msg.user.id
                        user_name = msg.user.display_name
                        amount = 5

                        filename = f"{user_directory}{user_id}.json"
                        filename2 = f"{inventory_dir}{user_id}.json"


                        # --- Default templates ---
                        user_default_data = {
                            "name": user_name,
                            "id": user_id,
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
                            logger.info(f"{fortime()}: Created user doc for {msg.user.id}")
                            delete_last_line()
                            await bot.send_chat_message(target_id, user_id, f"Welcome {user_name}, this is their first appearance!!!")
                            await sort_command()

                        if not os.path.exists(filename2):
                            with open(filename2, "w", encoding="utf-8") as g:
                                json.dump(user_inventory_default_data, g, indent=4)
                            logger.info(f"{fortime()}: Created inventory file for {user_id}")
                            delete_last_line()

                        # --- Load user profile ---
                        with open(filename, "r", encoding="utf-8") as f:
                            user_data = json.load(f)

                        if user_data["name"] != user_name:
                            user_data["name"] = user_name
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            logger.info(f"{fortime()}: Username change detected and updated")
                            delete_last_line()
                            if user_data["lurking"]:
                                await command_unlurk(msg.user.id, msg.user.display_name)

                        elif user_data["lurking"]:
                            await command_unlurk(msg.user.id, msg.user.display_name)
                        else:
                            user_data["xp"] += amount
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)

                            logger.info(f"{fortime()}: Updated user doc for {msg.user.id}")
                            delete_last_line()
                            await xp_level_check(user_id, user_name)

                        # --- Chat log ---
                        date = datetime.datetime.now().strftime("%y-%m-%d")
                        time = datetime.datetime.now().strftime("%H:%M:%S")
                        with open(chat_file, "a", encoding="utf-8") as f:
                            f.write(f"{date}|{time}|{user_id}|{user_name}|{msg.text}\n")

                        logger.info(f"{fortime()}: Updated chat log")
                        delete_last_line()

                    except Exception as e:
                        logger.info(f"{fortime()}: There was an error handling chat -- {e}")
                        delete_last_line()


async def on_sub(sub: ChatSub):
    try:
        user_id = sub.id
        user_name = sub.display_name
        amount = 100
        filename = f"{user_directory}{user_id}.json"
        filename2 = f"{inventory_dir}{user_id}.json"

        # --- Default templates ---
        user_default_data = {
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
            delete_last_line()
            await sort_command()
            cls()

        if not os.path.exists(filename2):
            with open(filename2, "w", encoding="utf-8") as g:
                json.dump(user_inventory_default_data, g, indent=4)
            logger.info(f"{fortime()}: Created inventory file for {user_id}")
            delete_last_line()

        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        user_data["xp"] += amount
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=4)

        logger.info(f"{fortime()}: Updated {filename}")
        delete_last_line()
        await xp_level_check(user_id, user_name)

    except Exception as e:
        logger.info(f"{fortime()}: Error handling sub -- {e}")
        delete_last_line()
# -----end Events


# -----Begin Chat Message Commands
async def command_discord(cmd: ChatCommand):
    await cmd.reply("Come to the darkside, join the community!: https://discord.gg/2gXGYMZg")

async def command_donate(cmd: ChatCommand):
    await cmd.reply("It's not required, but you can donate to me directly on the following services: Cashapp = $almullens91")
    
async def command_tech(cmd: ChatCommand):
    await cmd.reply("It wouldn't be a stream without tech issues.")
    
async def command_joe(cmd: ChatCommand):
    await cmd.reply("FUCK YOU JOE, you asshole!!")
# -----End Chat Message Commands


# --------Simple Commands----------
async def command_phone(cmd: ChatCommand):
    distance = random.randint(1, 70)
    if not os.path.exists(f"{phone_history}/{fordate()}.json"):
        default_data = {
            "date": fordate(),
            "times": 0
        }
        with open(f"{phone_history}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        await asyncio.sleep(1)
        with open(f"{phone_history}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        times = data['times']
        new_times = times + 1
        data['times'] = new_times
        with open(f"{phone_history}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await cmd.reply(f"{cmd.user.display_name}, you threw that phone {distance} yards. {new_times} phones have been thrown today.")
    else:
        with open(f"{phone_history}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        times = data['times']
        new_times = times + 1
        data['times'] = new_times
        with open(f"{phone_history}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await cmd.reply(f"{cmd.user.display_name}, you threw that phone {distance} yards. {new_times} phones have been thrown today.")


async def command_shoutout(cmd: ChatCommand):
    if cmd.user.id == target_id:
        cmd_so = cmd.text.lstrip("!so")
        if cmd_so.startswith(" @"):
            target = cmd_so.lstrip(" @")
            with open(user_log, "r") as file:
                for line in file:
                    clean_line = line.strip()
                    if target in clean_line:
                        targets_id = str(clean_line.split(' ', 2)[-1])
                        await bot.send_a_shoutout(target_id, targets_id, target_id)


async def command_slap(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_slap = cmd.text.lstrip("!slap")
    if cmd_slap.startswith(" history"):
        if not os.path.exists(f"{slap_history}{user_id}.json"):
            await cmd.reply(f"{cmd.user.display_name}, you don't have any history yet.")
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"{fortime()}: Created slap_history for {user_id}")
            delete_last_line()
        else:
            with open(f"{slap_history}{user_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            attacks = data['attacks']
            await cmd.reply(f"{cmd.user.display_name}, you have successfully attacked someone {attacks} times")
    else:
        if not os.path.exists(f"{slap_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                if cmd_slap.startswith(" @"):
                    target = cmd_slap
                    await cmd.reply(f"{cmd.user.display_name} slapped {target} because they felt like it!")
                    with open(f"{slap_history}{user_id}.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    attacks = data['attacks']
                    new_attacks = attacks + 1
                    data['attacks'] = new_attacks
                    with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{fortime()}: updated slap_history for {user_id}")
                    delete_last_line()
                else:
                    await cmd.reply(f"{cmd.user.display_name} slapped the streamer because they felt like it!")
                    with open(f"{slap_history}{user_id}.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    attacks = data['attacks']
                    new_attacks = attacks + 1
                    data['attacks'] = new_attacks
                    with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{fortime()}: updated slap_history for {user_id}")
                    delete_last_line()
            else:
                if cmd_slap.startswith(" @"):
                    target = cmd_slap
                    await cmd.reply(
                        f"{target}, {cmd.user.display_name} attempted to slap you, but you were able to evade")
                    with open(f"{slap_history}{user_id}.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    attacks = data['attacks']
                    new_attacks = attacks + 1
                    data['attacks'] = new_attacks
                    with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{fortime()}: updated slap_history for {user_id}")
                    delete_last_line()
                else:
                    await cmd.reply(
                        f"{cmd.user.display_name}, you attempted to slap the streamer, but they were able to evade")
                    with open(f"{slap_history}{user_id}.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    attacks = data['attacks']
                    new_attacks = attacks + 1
                    data['attacks'] = new_attacks
                    with open(f"{slap_history}{user_id}.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{fortime()}: updated slap_history for {user_id}")
                    delete_last_line()


async def command_lurk(cmd: ChatCommand):
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
        delete_last_line()


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
        delete_last_line()


async def command_pointscheck(cmd: ChatCommand):
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
        delete_last_line()
        await cmd.reply(f"{cmd.user.display_name}, I could not load your points, my bad...")


async def command_xpcheck(cmd: ChatCommand):
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
        delete_last_line()
        await cmd.reply(f"{cmd.user.display_name}, I could not load your xp, my bad...")


async def command_levelcheck(cmd: ChatCommand):
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
        delete_last_line()
        await cmd.reply(f"{cmd.user.display_name}, I could not load your level, my bad...")


async def command_kick(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_kick = cmd.text.lstrip("!kick")
    if cmd_kick.startswith(" history"):
        if not os.path.exists(f"{kick_history}{user_id}.json"):
            await cmd.reply(f"{cmd.user.display_name}, you don't currently have any history.")
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
        else:
            with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            attacks = data['attacks']
            await cmd.reply(f"{cmd.user.display_name}, you have successfully kicked someone {attacks} times")
    elif cmd_kick.startswith(" @"):
        if not os.path.exists(f"{kick_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            target = cmd_kick
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} kicked {target} because they felt like it.")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to kick you, but you were able to evade")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            target = cmd_kick
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} kicked {target} because they felt like it.")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to kick you, but you were able to evade")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
    else:
        if not os.path.exists(f"{kick_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} kicked the streamer because they felt like it.")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(f"{cmd.user.display_name} attempted to kick the streamer, but they were able to evade")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} kicked the streamer because they felt like it.")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(f"{cmd.user.display_name} attempted to kick the streamer, but they were able to evade")
                with open(f"{kick_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{kick_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)


async def command_bite(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_bite = cmd.text.lstrip("!bite")
    if cmd_bite.startswith(" history"):
        if not os.path.exists(f"{bite_history}{user_id}.json"):
            await cmd.reply(f"{cmd.user.display_name}, you don't have any history currently")
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
        else:
            with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            attacks = data['attacks']
            await cmd.reply(f"{cmd.user.display_name}, you have successfully bit {attacks} people")
    elif cmd_bite.startswith(" @"):
        if not os.path.exists(f"{bite_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            bite_items = [
                {"item": "Joe's Mouth"},
                {"item": "Viper Fangs"},
                {"item": "Dracula's Mouth"},
                {"item": "with love"}
            ]
            bite_item = random.choice(bite_items)
            if evade_roll == False:
                target = cmd_bite
                await cmd.reply(f"{cmd.user.display_name} bit {target} with {bite_item['item']}")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                target = cmd_bite
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to bite you, but you were able to evade")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            bite_items = [
                {"item": "Joe's Mouth"},
                {"item": "Viper Fangs"},
                {"item": "Dracula's Mouth"},
                {"item": "with love"}
            ]
            bite_item = random.choice(bite_items)
            if evade_roll == False:
                target = cmd_bite
                await cmd.reply(f"{cmd.user.display_name} bit {target} with {bite_item['item']}")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                target = cmd_bite
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to bite you, but you were able to evade")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
    else:
        if not os.path.exists(f"{bite_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            bite_items = [
                {"item": "Joe's Mouth"},
                {"item": "Viper Fangs"},
                {"item": "Dracula's Mouth"},
                {"item": "with love"}
            ]
            bite_item = random.choice(bite_items)
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} bit the streamer with {bite_item['item']}")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(
                    f"{cmd.user.display_name}, you attempted to bite the streamer, but they were able to evade")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            bite_items = [
                {"item": "Joe's Mouth"},
                {"item": "Viper Fangs"},
                {"item": "Dracula's Mouth"},
                {"item": "with love"}
            ]
            bite_item = random.choice(bite_items)
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} bit the streamer with {bite_item['item']}")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(
                    f"{cmd.user.display_name}, you attempted to bite the streamer, but they were able to evade")
                with open(f"{bite_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{bite_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)


async def command_pinch(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_pinch = cmd.text.lstrip("!pinch")
    if cmd_pinch.startswith(" history"):
        if not os.path.exists(f"{pinch_history}{user_id}.json"):
            await cmd.reply(f"{cmd.user.display_name}, you currently don't have any history")
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"{fortime()}: Created pinch_history for {user_id}")
            delete_last_line()
        else:
            with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            attacks = data['attacks']
            await cmd.reply(f"{cmd.user.display_name}, you have successfully pinched {attacks} people")
    elif cmd_pinch.startswith(" @"):
        if not os.path.exists(f"{pinch_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"{fortime()}: Created pinch_history for {user_id}")
            delete_last_line()
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                target = cmd_pinch
                await cmd.reply(f"{cmd.user.display_name} pinched {target} because they felt like it.")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                target = cmd_pinch
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to pinch you, but you were able to evade")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                target = cmd_pinch
                await cmd.reply(f"{cmd.user.display_name} pinched {target} because they felt like it.")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                target = cmd_pinch
                await cmd.reply(f"{target}, {cmd.user.display_name} attempted to pinch you, but you were able to evade")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
    else:
        if not os.path.exists(f"{pinch_history}{user_id}.json"):
            default_data = {
                "attacks": 0,
                "attacked": 0,
                "evades": 0,
                "evaded": 0,
                "users_attacked": [],
                "users_defend": []
            }
            with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            logger.info(f"{fortime()}: Created pinch_history for {user_id}")
            delete_last_line()
            await asyncio.sleep(1)
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} pinched the streamer because they felt like it.")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(
                    f"{cmd.user.display_name}, you attempted to pinch the streamer, but they were able to evade")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
        else:
            evade_chance = 0.32
            evade_roll = random.random() < evade_chance
            if evade_roll == False:
                await cmd.reply(f"{cmd.user.display_name} pinched the streamer because they felt like it.")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            else:
                await cmd.reply(
                    f"{cmd.user.display_name}, you attempted to pinch the streamer, but they were able to evade")
                with open(f"{pinch_history}{user_id}.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                attacks = data['attacks']
                new_attacks = attacks + 1
                data['attacks'] = new_attacks
                with open(f"{pinch_history}{user_id}.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)


async def command_pp(cmd: ChatCommand):
    user_id = cmd.user.id
    user_name = cmd.user.display_name
    cmd_pp = cmd.text.lstrip("!pp")
    if not os.path.exists(f"{pp_history}/{user_id}/{fordate()}.json"):
        Path(f"{pp_history}/{user_id}/").mkdir(parents=True, exist_ok=True)
        default_data = {
            "date": fordate(),
            "size": 0
        }
        with open(f"{pp_history}/{user_id}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        await asyncio.sleep(1)
        pp_size = random.randint(1, 15)
        with open(f"{pp_history}/{user_id}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        current_size = data['size']
        new_size = pp_size
        data['size'] = new_size
        with open(f"{pp_history}/{user_id}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await cmd.reply(f"{cmd.user.display_name}, your pp size for today is {pp_size} inches.")
    elif cmd_pp.startswith(" history"):
        folder_path = f"{pp_history}/{user_id}/"
        files = glob.glob(os.path.join(folder_path, '*.json'))
        
        files.sort(key=os.path.getmtime)
        last_five_files = files[-5:]
        
        combined_output = []
        
        for file_path in last_five_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                date = data['date']
                size = data['size']
                combined_output.append(f"{date}={size}")
            except Exception as e:
                logger.info(f"{fortime()}: Error in pp_history -- {e}")
                await cmd.reply(f"{user_name}, couldn't retrieve your history. Something broke.")
        clean_output = str(combined_output).strip("[]'").replace("', '", " | ")
        #logger.info(f"{fortime()}: pp_history returned: clean_output = {clean_output}")
        
        await cmd.reply(f"{user_name}, your pp history is as follows: {clean_output}")
    else:
        with open(f"{pp_history}/{user_id}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        todays_size = data['size']
        await cmd.reply(f"{cmd.user.display_name}, your pp size for today has already been chaecked. It's {todays_size} inches.")




async def command_iq(cmd: ChatCommand):
    user_id = cmd.user.id
    user_name = cmd.user.display_name
    cmd_iq = cmd.text.lstrip("!iq")
    iq = random.randint(0, 500)
    if not os.path.exists(f"{iq_history}/{user_id}/{fordate()}.json"):
        Path(f"{iq_history}/{user_id}/").mkdir(parents=True, exist_ok=True)
        default_data = {
            "date": fordate(),
            "iq": 0
        }
        with open(f"{iq_history}/{user_id}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        await asyncio.sleep(1)
        with open(f"{iq_history}/{user_id}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        current_iq = data['iq']
        new_iq = iq
        data['iq'] = new_iq
        with open(f"{iq_history}/{user_id}/{fordate()}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        await cmd.reply(f"{cmd.user.display_name}, your iq for today is {iq}.")
    elif cmd_iq.startswith(" history"):
    	  folder_path = f"{iq_history}/{user_id}/"
    	  files = glob.glob(os.path.join(folder_path, '*.json'))
    	  
    	  files.sort(key=os.path.getmtime)
    	  last_five_files = files[-5:]
    	  
    	  combined_output = []
    	  
    	  for file_path in last_five_files:
    	  	   try:
    	  	   	 with open(file_path, "r", encoding="utf-8") as f:
    	  	   	 	  data = json.load(f)
    	  	   	 date = data['date']
    	  	   	 iq = data['iq']
    	  	   	 combined_output.append(f"{date}={iq}")
    	  	   except Exception as e:
    	  	   	logger.info(f"{fortime()}: Error in pp_history -- {e}")
    	  	   	await cmd.reply(f"{user_name}, couldn't load your history. Something broke.")
    	  clean_output = str(combined_output).strip("[]'").replace("', '", " | ")
    	  
    	  await cmd.reply(f"{user_name}, your iq history is as follows: {clean_output}")
    else:
        with open(f"{iq_history}/{user_id}/{fordate()}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        todays_iq = data['iq']
        await cmd.reply(f"{cmd.user.display_name}, you have already checked your iq for today. It's {todays_iq}")


async def command_lick(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    cmd_lick = cmd.text.lstrip("!lick ")
    if evade_roll == False:
        if cmd_lick.startswith("@"):
            target = cmd_lick
            await cmd.reply(f"{cmd.user.display_name} licked {target} because they felt like it.")
        else:
            await cmd.reply(f"{cmd.user.display_name} licked the streamer because they felt like it.")
    else:
        if cmd_lick.startswith("@"):
            target = cmd_lick
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to lick you. but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to lick the streamer, but they were able to evade")


async def command_pants(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    pant_items = [
        {"item": "Wearing Boxers"},
        {"item": "Wearing Briefs"},
        {"item": "Going Commando"}
    ]

    cmd_pants = cmd.text.lstrip("!pants ")
    if evade_roll == False:
        ran_item = random.choice(pant_items)
        if cmd_pants.startswith("@"):
            target = cmd_pants
            await cmd.reply(f"{cmd.user.display_name} pantsed {target} and found them {ran_item['item']}")
        else:
            await cmd.reply(f"{cmd.user.display_name} pantsed the streamer and found them {ran_item['item']}")
    else:
        if cmd_pants.startswith("@"):
            target = cmd_pants
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to pants you, but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to pants the streamer, but they were able to evade")


async def command_pounce(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    pounce_items = [
        {"item": "they looked like a comfy pillow."},
        {"item": "they felt like it."},
        {"item": "they needed cuddles."}
    ]

    cmd_pounce = cmd.text.lstrip("!pounce ")
    if evade_roll == False:
        ran_item = random.choice(pounce_items)
        if cmd_pounce.startswith("@"):
            target = cmd_pounce
            await cmd.reply(f"{cmd.user.display_name} pounced {target} because {ran_item['item']}")
        else:
            await cmd.reply(f"{cmd.user.display_name} pounced the streamer because {ran_item['item']}")
    else:
        if cmd_pounce.startswith("@"):
            target = cmd_pounce
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to pounce you, but your were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to pounce the streamer, but they were able to evade")


async def command_tickle(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    cmd_tickle = cmd.text.lstrip("!tickle ")
    if evade_roll == False:
        if cmd_tickle.startswith("@"):
            target = cmd_tickle
            await cmd.reply(f"{cmd.user.display_name} tickles {target} because they felt like it.")
        else:
            await cmd.reply(f"{cmd.user.display_name} tickles the streamer because they felt like it.")
    else:
        if cmd_tickle.startswith("@"):
            target = cmd_tickle
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to tickle you, but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to tickle the streamer, but they were able to evade")


async def command_poke(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    cmd_poke = cmd.text.lstrip("!poke ")
    if evade_roll == False:
        if cmd_poke.startswith("@"):
            target = cmd_poke
            await cmd.reply(f"{cmd.user.display_name} poked {target} because they felt like it.")
        else:
            await cmd.reply(f"{cmd.user.display_name} poked the streamer because they felt like it.")
    else:
        if cmd_poke.startswith("@"):
            target = cmd_poke
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to poke you, but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to poke the streamer, but they were able to evade")


async def command_burn(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    cmd_burn = cmd.text.lstrip("!burn ")
    if evade_roll == False:
        if cmd_burn.startswith("@"):
            target = cmd_burn
            await cmd.reply(f"{cmd.user.display_name} burned {target} with a lighter because they felt like it.")
        else:
            await cmd.reply(
                f"{cmd.user.display_name} burned the streamer with a lighter because they felt like it.")
    else:
        if cmd_burn.startswith("@"):
            target = cmd_burn
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to burn you, but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to burn the streamer, but they were able to evade")


async def command_jail(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_jail = cmd.text.lstrip("!jail")
    if cmd_jail.startswith(" @"):
        target = cmd_jail.lstrip(" @")
        with open(user_log, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if target in clean_line:
                    targets_id = str(clean_line.split(' ', 2)[-1])
                    if targets_id == target_id:
                        await cmd.reply(f"{cmd.user.display_name}, you cannot jail the streamer.")
                        return
                    else:
                        filename = f"{user_directory}{user_id}.json"
                        with open(filename, "r", encoding="utf-8") as g:
                            data = json.load(g)
                        points = data['points']
                        if points < 5000:
                            await cmd.reply(f"{cmd.user.display_name}, you don't have enough points to jail anyone right now")
                            return
                        else:
                            new_points = points - 5000
                            data['points'] = new_points
                            with open(filename, "w", encoding="utf-8") as g:
                                json.dump(data, g, indent=4)
                            await bot.ban_user(target_id, target_id, targets_id, reason='Jail command', duration=300)
                            await cmd.reply(f"{cmd_jail}, you have been jailed by {cmd.user.display_name}.")
                            await cmd.reply(f"{cmd.user.display_name}, you now have {new_points} points.")
                            logger.info(f"{fortime()}: {targets_id} was jailed by {cmd.user.id}")
                            delete_last_line()
    else:
        pass


async def checkin_command(cmd: ChatCommand):
    user_id = cmd.user.id
    filename = f"{checkin_directory}{user_id}.json"
    filename2 = f"{user_directory}{user_id}.json"
    user_default_data = {
        "total": 1,
        "last": fordate(),
        "boost_lvl": 1
    }
    if not os.path.exists(filename):
        with open(filename, "x", encoding="utf-8") as f:
            json.dump(user_default_data, f, indent=4)
        await cmd.reply(f"{cmd.user.display_name}, you have successfully completed your first checkin. Come back next stream and check in again to start accumulating checkins and gain points")
    else:
        with open(filename, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        total_checkins = user_data['total']
        last_checkin = user_data['last']
        boost_lvl = user_data['boost_lvl']

        if last_checkin == fordate():
            await cmd.reply(f"{cmd.user.display_name}, you've already checked in today, {total_checkins} total check-ins")
        else:
            booster_trigger = 3 * boost_lvl
            if total_checkins >= booster_trigger:
                new_total = total_checkins + 1
                new_checkin = fordate()
                new_boost = boost_lvl + 1
                user_data['total'] = new_total
                user_data['last'] = new_checkin
                user_data['boost'] = new_boost
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, indent=4)
                    f.close()
                logger.info(f"{fortime()}: {filename} updated successfully")
                delete_last_line()
                with open(filename2, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                current_points = user_data['points']
                booster = 1000 * boost_lvl
                new_points = current_points + booster
                user_data['points'] = new_points
                with open(filename2, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, indent=4)
                logger.info(f"{fortime()}: {filename2} updated successfully")
                delete_last_line()
                await cmd.reply(f"{cmd.user.display_name}, you have successfully checked in, {new_total} total check-ins. You gained {booster} points for continuous checkins.")
            else:
                new_total = total_checkins + 1
                new_checkin = fordate()
                user_data['total'] = new_total
                user_data['last'] = new_checkin
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(user_data, f, indent=4)
                    f.close()
                await cmd.reply(f"{cmd.user.display_name}, you have successfully checked in. You are now at {new_total} cumulative check ins")
                logger.info(f"{fortime()}: {filename} updated successfully")
                delete_last_line()


async def command_bonk(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    cmd_bonk = cmd.text.lstrip("!bonk ")
    if evade_roll == False:
        if cmd_bonk.startswith("@"):
            target = cmd_bonk
            await cmd.reply(f"{target}, you have been bonked by {cmd.user.display_name}")
        else:
            await cmd.reply(f"{cmd.user.display_name} bonked the streamer")
    else:
        if cmd_bonk.startswith("@"):
            target = cmd_bonk
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to bonk you, but you evaded their shenanigans")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to bonk the streamer, but they were able to evade")


async def command_dropkick(cmd: ChatCommand):
    evade_chance = 0.32
    evade_roll = random.random() < evade_chance
    dropkick_items = [
        {"item": "off the Empire State Building"},
        {"item": "off the summit of Mount Everest"}
    ]
    cmd_dropkick = cmd.text.lstrip("!dropkick")
    if evade_roll == False:
        ran_item = random.choice(dropkick_items)
        if cmd_dropkick.startswith("@"):
            target = cmd_dropkick
            await cmd.reply(f"{target}, you were drop kicked {ran_item} by {cmd.user.display_name}")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you drop kicked the streamer {ran_item}")
    else:
        if cmd_dropkick.startswith("@"):
            target = cmd_dropkick
            await cmd.reply(f"{target}, {cmd.user.display_name} attempted to dropkick you, but you were able to evade")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to dropkick the streamer, but they were able to evade")
            

async def steal_command(cmd: ChatCommand):
    cmd_steal = cmd.text.lstrip("!steal")
    amount = random.randint(100, 5000)
    if cmd_steal.startswith(" @"):
        target = cmd_steal.lstrip(" @")
        with open(user_log, "r", encoding="utf-8") as file:
            for line in file:
                clean_line = line.strip()
                if target in clean_line:
                    targets_id = clean_line.split(' ', 2)[-1]
                    #logger.info(f"{fortime()}: steal_command returned targets_id = {targets_id}")
                    with open(f"{user_directory}{targets_id}.json", "r", encoding="utf-8") as f:
                        target_data = json.load(f)
                    target_current_points = target_data['points']
                    target_new_points = target_current_points - amount
                    target_data['points'] = target_new_points
                    with open(f"{user_directory}{targets_id}.json", "w", encoding="utf-8") as f:
                        json.dump(target_data, f, indent=4)
                    with open(f"{user_directory}{cmd.user.id}.json", "r", encoding="utf-8") as g:
                        attacker_data = json.load(g)
                    attacker_current_points = attacker_data['points']
                    attacker_new_points = attacker_current_points + amount
                    attacker_data['points'] = attacker_new_points
                    with open(f"{user_directory}{cmd.user.id}.json", "w", encoding="utf-8") as g:
                        json.dump(attacker_data, g, indent=4)
                    await cmd.reply(f"{cmd_steal}, {cmd.user.display_name} stole {amount} points from you. You now have {target_new_points} points.")
                    await cmd.reply(f"{cmd.user.display_name}, you now have {attacker_new_points} points.")
    else:
        await cmd.reply(f"{cmd.user.display_name}, you must target a user(!steal @user name).")


async def rob_command(cmd: ChatCommand):
    defend_chance = 0.75
    defend_roll = random.random() < defend_chance
    cmd_rob = cmd.text.lstrip("!rob")
    if cmd_rob.startswith(" @"):
        target = cmd.text.lstrip("!rob @")
        if defend_roll == False:
            with open(user_log, "r", encoding="utf-8") as file:
                for line in file:
                    clean_line = line.strip()
                    if target in clean_line:
                        targets_id = clean_line.split(' ', 2)[-1]
                        with open(f"{user_directory}{targets_id}.json", "r", encoding="utf-8") as f:
                            target_data = json.load(f)
                        targets_current_points = target_data['points']
                        targets_new_points = 0
                        target_data['points'] = targets_new_points
                        with open(f"{user_directory}{targets_id}.json", "w", encoding="utf-8") as f:
                            json.dump(target_data, f, indent=4)
                        await asyncio.sleep(1)
                        with open(f"{user_directory}{cmd.user.id}.json", "r", encoding="utf-8") as g:
                            attacker_data = json.load(g)
                        attacker_current_points = attacker_data['points']
                        attacker_new_points = attacker_current_points + targets_current_points
                        attacker_data['points'] = attacker_new_points
                        with open(f"{user_directory}{cmd.user.id}.json", "w", encoding="utf-8") as g:
                            json.dump(attacker_data, g, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you successfully robbed {target}. You gained {targets_current_points} points in you endeavor. You now have {attacker_new_points} points")
        else:
            await cmd.reply(f"{cmd.user.display_name}, you attempted to rob {target}, but they were able to get away.")
    else:
        await cmd.reply(f"{cmd.user.display_name}, you must target someone.")


async def test_internal_command():
    await bot.send_chat_message(target_id, user.id, "Hello, I'm still here...")
# --------End Simple Commands------#


#--Streamer & Mod Commands
async def command_control(cmd: ChatCommand):
    cmd_ctrl = cmd.text.lstrip("!cmd")
    if cmd.user.id == target_id:
        if cmd_ctrl.startswith(" add"):
            message = cmd_ctrl.split(' ', 3)[-1]
            #logger.info(f"{fortime()}: cmd_ctrl returned message = {message}")
            cmd_trigger = cmd_ctrl.lstrip(" add ").rstrip(message)
            with open(cmd_list, "r") as file:
                for line in file:
                    clean_line = line.strip()
                    if not cmd_trigger in clean_line:
                        with open(cmd_list, "a") as f:
                            f.write(f"{cmd_trigger} = {message}\n")
                            f.close()
                            await cmd.reply("Command added successfully")
                            break
                    else:
                        await cmd.reply("That command already exists.")
                        break
        elif cmd_ctrl.startswith(" remove"):
            cmd_trigger = cmd_ctrl.lstrip(" remove ")
            #logger.info(f"{fortime()}: cmd_ctrl returned cmd_trigger = {cmd_trigger}")
            found = False
            with open(cmd_list, "r") as file:
                lines = file.readlines()

            with open(cmd_list, "r") as f:
                for line in lines:
                    if cmd_trigger not in line:
                        f.write(str(line))
                    else:
                        found = True

            if found:
                await cmd.reply("Command removed successfully")
            else:
                await cmd.reply("Command not found")
        else:
            pass
    else:
        pass


async def add_banned_term(term: str):
    with open(banned_phrases, "a") as f:
        f.write(nl)
        f.write(term)
        f.close()
    await bot.send_chat_message(target_id, user.id, f"'{term}' has been added to banned terms")


async def banned_term_command(cmd: ChatCommand):
    if cmd.user.id == target_id:
        cmd_ban_term = cmd.text.lstrip("!banterm")
        if cmd_ban_term.startswith(" add"):
            term = cmd_ban_term.lstrip(" add ")
            with open(banned_phrases, "r") as file:
                for line in file:
                    clean_line = line.strip()
                    if term in clean_line:
                        await cmd.reply(f"{term} already in banned terms list")
                        break
                    else:
                        await add_banned_term(term)
                        break
        else:
            pass
    else:
        pass


#Archive Log Deletion
async def archive_delete_console():
    folder_path = f"{archive_logs_directory}"

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                logger.info(f"{fortime()}: Removed {file_path}")
                delete_last_line()
        except Exception as e:
            logger.info(f"{fortime()}: Error in archive_delete_console -- {e}")
            delete_last_line()


async def archive_delete_command(cmd: ChatCommand):
    if cmd.user.id == target_id or cmd.user.id == id_mullensbot:
        cmd_clear = cmd.text.lstrip("!clear")
        if cmd_clear.startswith(" archives"):
            folder_path = f"{archive_logs_directory}"

            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"{fortime()}: Removed {file_path}")
                        delete_last_line()
                except Exception as e:
                    logger.info(f"{fortime()}: Error in archive_delete_console -- {e}")
                    delete_last_line()
        else:
            pass
    else:
        pass


async def mkbkup_command(cmd: ChatCommand):
    if cmd.user.id == target_id or cmd.user.id == id_mullensbot:
        backup_path = f"{backup_dir}/{fortime()}/"

        shutil.copytree(bet_directory, f"{backup_path}/bet/", dirs_exist_ok=False)
        shutil.copytree(chat_directory, f"{backup_path}/chat/", dirs_exist_ok=False)
        shutil.copytree(checkin_directory, f"{backup_path}/checkin/", dirs_exist_ok=False)
        shutil.copytree(history_dir, f"{backup_path}/history/", dirs_exist_ok=False)
        shutil.copytree(logs_directory, f"{backup_path}/logs/", dirs_exist_ok=False)
        shutil.copytree(inventory_dir, f"{backup_path}/user_inventory/", dirs_exist_ok=False)
        shutil.copytree(user_directory, f"{backup_path}/users/", dirs_exist_ok=False)
        shutil.copy(bot_doc, backup_path)
        shutil.copy(f"{data_path}/banned_phrases.json", backup_path)
        shutil.copy(channel_doc, backup_path)
        shutil.copy(f"{data_path}/users.json", backup_path)
        #Add any additional dirs or files here when needed
    else:
        pass


async def live_command(cmd: ChatCommand):
    if cmd.user.id == target_id or cmd.user.id == id_mullensbot:
        filename = channel_doc
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        live = data['live']
        if live == 1:
            data['live'] = 0
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            await cmd.reply("sir_almullens is now offline...")
        else:
            data['live'] = 1
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            await cmd.reply("sir_almullens is now live...")
    else:
        pass


async def addpoints_command(cmd: ChatCommand):
    cmd_addpoints = cmd.text.lstrip("!addpoints")
    if cmd.user.id == target_id:
        if cmd_addpoints.startswith(" @"):
            points = cmd_addpoints.split(' ', 2)[-1]
            if not points.isdigit():
                logger.info(f"{fortime()}: Error in addpoints_command -- Must include a points value")
            else:
                target = cmd_addpoints.lstrip(" @").rstrip(f" {points}")
                with open(user_log, "r") as file:
                    for line in file:
                        clean_line = line.strip()
                        if target in clean_line:
                            targets_id = clean_line.split(' ', 2)[-1]
                            with open(f"{user_directory}{targets_id}.json", "r", encoding="utf-8") as f:
                                data = json.load(f)
                            current_points = data['points']
                            new_points = current_points + int(points)
                            data['points'] = new_points
                            with open(f"{user_directory}{targets_id}.json", "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4)
                            await cmd.reply(f"{target}, you were given {points} points. You now have {new_points} points.")
        else:
            logger.info(f"{fortime()}: Error in addpoints_command. Must contain two variables(target & points value)")
    else:
        pass


async def givepoints_command(cmd: ChatCommand):
    cmd_givepoints = cmd.text.lstrip("!givepoints")
    if cmd_givepoints.startswith(" @"):
        points = cmd_givepoints.split(' ', 2)[-1]
        if not points.isdigit():
            await cmd.reply(f"{cmd.user.display_name}, you must add a point value to use that command. Correct format: '!givepoints @user name #'")
        else:
            target = cmd_givepoints.lstrip(" @").rstrip(f" {points}")
            with open(user_log, "r") as file:
                for line in file:
                    clean_line = line.strip()
                    if target in clean_line:
                        targets_id = clean_line.split(' ', 2)[-1]
                        with open(f"{user_directory}{targets_id}.json", "r", encoding="utf-8") as f:
                            target_data = json.load(f)
                        target_current_points = target_data['points']
                        target_new_points = target_current_points + int(points)
                        target_data['points'] = target_new_points
                        with open(f"{user_directory}{targets_id}.json", "w", encoding="utf-8") as f:
                            json.dump(target_data, f, indent=4)
                        with open(f"{user_directory}{cmd.user.id}.json", "r", encoding="utf-8") as f:
                            giver_data = json.load(f)
                        giver_current_points = giver_data['points']
                        giver_new_points = giver_current_points - int(points)
                        giver_data['points'] = giver_new_points
                        with open(f"{user_directory}{cmd.user.id}.json", "w", encoding="utf-8") as f:
                            json.dump(giver_data, f, indent=4)
                        await cmd.reply(f"{cmd.user.display_name}, you successfully gave {points} points to {target}. you now have {giver_new_points} points.")
                        await cmd.reply(f"{target}, you were given {points} points. you now have {target_new_points} points.")
    else:
        await cmd.reply(f"{cmd.user.display_name}, you must target a user('@users name') to perform this action. be sure to include points you want to give after tag.")


async def reset_command(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id or cmd.user.id == id_mullens:
            with open(bot_doc, "r", encoding="utf-8") as f:
                data = json.load(f)
            reset_true = data['resetting']
            if reset_true == 0:
                data['resetting'] = 1
                with open(bot_doc, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                await bot.send_chat_message(target_id, user.id, f"{bot_name} is leaving the chat...")
                logger.info(f"{fortime()}: Initiating bot reset...")
                delete_last_line()
                await bot.close()
                os.rename(f"{bet_directory}", f"{archive_dir}/bet/")
                os.rename(f"{checkin_directory}", f"{archive_dir}/checkin/")
                os.rename(f"{history_dir}", f"{archive_dir}/history/")
                os.rename(f"{inventory_dir}", f"{archive_dir}/user_inventory/")
                os.rename(f"{user_directory}", f"{archive_dir}/users/")
                os.rename(f"{data_path}/users.json", f"{archive_dir}/users.json")
                logger.info(f"{fortime()}: Bot reset complete. Please restart the bot when you are ready to initiate setup of new version...")
            else:
                pass
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in reset_command -- {e}")
        delete_last_line()


async def command_pause(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id or cmd.user.id == id_mullens:
            with open(channel_doc, "r", encoding="utf-8") as f:
                data = json.load(f)
            autocast_enabled = data["autocast"]
            if autocast_enabled == "enabled":
                data["autocast"] = "disabled"
                with open(channel_doc, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"{fortime()}: Casting paused")
                delete_last_line()
                await cmd.reply(f"Casting has been paused by {cmd.user.display_name}")
            else:
                logger.info(f"{fortime()}: Casting is already paused")
                delete_last_line()
                await cmd.reply("Casting is already paused...")
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error in command_pause, could not pause casting -- {e}")
        delete_last_line()


async def command_resume(cmd: ChatCommand):
    try:
        if cmd.user.id == target_id or cmd.user.id == id_mullens:
            with open(channel_doc, "r", encoding="utf-8") as f:
                data = json.load(f)
            autocast_enabled = data["autocast"]
            if autocast_enabled == "disabled":
                data["autocast"] = "enabled"
                with open(channel_doc, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                logger.info(f"{fortime()}: Casting resumed")
                delete_last_line()
                await cmd.reply("Casting has been resumed")
    except Exception as e:
        logger.info(f"{fortime()}: Error in resume_command -- {e}")
        delete_last_line()
# --------End--------#


# --------Mini Games---------------#
async def command_bet(cmd: ChatCommand):
    user_id = cmd.user.id
    cmd_bet = cmd.text.lstrip("!bet")
    if cmd_bet.startswith(" history"):
        filename = f"{bet_history}{user_id}.json"
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        total_bet = data['total_bet']
        total_won = data['total_won']
        total_bets = int(total_bet / 100)
        gain_loss = int(total_won) - int(total_bet)
        await cmd.reply(f"{cmd.user.display_name}, you have bet {total_bets} times, for a total gain/loss of {gain_loss} points.")
    else:
        if not os.path.exists(f"{bet_history}{user_id}.json"):
            default_data = {
                "total_bet": 0,
                "total_won": 0
            }
            with open(f"{bet_history}{user_id}.json", "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
            await asyncio.sleep(1)
            win_chance = 0.18
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

                if not bet_roll:
                    user_newpoints = user_data["points"] - min_cost
                    user_data["points"] = user_newpoints
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    new_pot = old_pot + (min_cost * 2)
                    bet_data["value"] = new_pot
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you lost {min_cost} points. Your new points are {user_newpoints}. The total to be won is now {new_pot}.")
                    filename3 = f"{bet_history}{user_id}.json"
                    with open(filename3, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    total_bet = data['total_bet']
                    total_won = data['total_won']
                    new_total_bet = int(total_bet) + 100
                    new_total_won = int(total_won) + 0
                    data['total_bet'] = new_total_bet
                    data['total_won'] = new_total_won
                    with open(filename3, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    return
                else:
                    user_newpoints = user_data["points"] + old_pot
                    user_data["points"] = user_newpoints
                    bet_data["value"] = start_balance
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you won {old_pot} points. You now have {user_newpoints} points. Pot total has been reset to {start_balance}")
                    filename3 = f"{bet_history}{user_id}.json"
                    with open(filename3, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    total_bet = data['total_bet']
                    total_won = data['total_won']
                    new_total_bet = int(total_bet) + 100
                    new_total_won = int(total_won) + int(old_pot)
                    data['total_bet'] = new_total_bet
                    data['total_won'] = new_total_won
                    with open(filename3, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    return
        else:
            win_chance = 0.18
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
                    new_pot = old_pot + (min_cost * 2)
                    bet_data["value"] = new_pot
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you lost {min_cost} points. Your new points are {user_newpoints}. The total to be won is now {new_pot}.")
                    filename3 = f"{bet_history}{user_id}.json"
                    with open(filename3, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    total_bet = data['total_bet']
                    total_won = data['total_won']
                    new_total_bet = int(total_bet) + 100
                    new_total_won = int(total_won) + 0
                    data['total_bet'] = new_total_bet
                    data['total_won'] = new_total_won
                    with open(filename3, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    return
                else:
                    user_newpoints = user_data["points"] + old_pot
                    user_data["points"] = user_newpoints
                    bet_data["value"] = start_balance
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(bet_data, f, indent=4)
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you won {old_pot} points. You now have {user_newpoints} points. Pot total has been reset to {start_balance}")
                    filename3 = f"{bet_history}{user_id}.json"
                    with open(filename3, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    total_bet = data['total_bet']
                    total_won = data['total_won']
                    new_total_bet = int(total_bet) + 100
                    new_total_won = int(total_won) + int(old_pot)
                    data['total_bet'] = new_total_bet
                    data['total_won'] = new_total_won
                    with open(filename3, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"{fortime()}: {user_id} bet history updated successfully")
                    delete_last_line()
                    return


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
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 2
                        user_data["points"] -= 5000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have successfully upgraded your fishtier for 5000 points, now tier 2")
                elif fishtier == 2:
                    points = user_data["points"]
                    if points < 20000:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 3
                        user_data["points"] -= 20000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 3")
                elif fishtier == 3:
                    points = user_data["points"]
                    if points < 50000:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 4
                        user_data["points"] -= 50000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 4")
                elif fishtier == 4:
                    points = user_data["points"]
                    if points < 100000:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to upgrade right now. Continue fishing to build up your points!")
                    else:
                        user_data["fishtier"] = 5
                        user_data["points"] -= 100000
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have successfully upgraded your fishtier, now tier 5(MAX). There are no more upgrades available!")
                else:
                    logger.info(f"{fortime()}: Error upgrading fishtier for {cmd.user.id}")
                    delete_last_line()
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
            # --------Convert to own command--------#
            #            elif fish_cmd.endswith("inventory"):
            #                filename = f"{user_directory}{user_id}.json"
            #                with open(filename, "r", encoding="utf-8") as f:
            #                    user_data = json.load(f)
            #                inventory = user_data["inventory"]
            #                await cmd.reply(f"{cmd.user.display_name}, you have {inventory} fish in your inventory.")
            # --------End Note--------#
            elif fish_cmd.endswith("topup"):
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                current_points = user_data['points']
                current_casts = user_data['autocasts']
                tier = user_data['fishtier']
                if tier == 1:
                    new_casts = 50 - current_casts
                    cost = new_casts * 5
                    if current_points < cost:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 50
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 50 casts remaining.")
                        track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                elif tier == 2:
                    new_casts = 100 - current_casts
                    cost = new_casts * 10
                    if current_points < cost:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 100
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 100 casts remaining.")
                        track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                elif tier == 3:
                    new_casts = 200 - current_casts
                    cost = new_casts * 15
                    if current_points < cost:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 200
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 200 casts remaining.")
                        track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                elif tier == 4:
                    new_casts = 300 - current_casts
                    cost = new_casts * 20
                    if current_points < cost:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 300
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 300 casts remaining.")
                        track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                elif tier == 5:
                    new_casts = 400 - current_casts
                    cost = new_casts * 25
                    if current_points < cost:
                        await cmd.reply(
                            f"{cmd.user.display_name}, you don't have enough points to max out your autocast.")
                    else:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 400
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name}, you have added {new_casts} to your fishing for {cost} points. You now have 400 casts remaining.")
                        track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                else:
                    logger.info(f"{fortime()}: Error topping up autocasts for {cmd.user.id}")
                    delete_last_line()
            elif fish_cmd.endswith("refund"):
                filename = f"{user_directory}{user_id}.json"
                filename2 = f"{autocast_tracker}/{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                current_points = user_data['points']
                current_casts = user_data['autocasts']
                tier = user_data['fishtier']
                if tier == 1:
                    value = int(current_casts) * 5
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                    end_time = f"{fortime()}"
                    gain = 0
                    tracker_type = "refund"
                    track_autocasts(user_id, tracker_type, current_casts, value, gain, end_time)
                    with open(filename2, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    total_casts = user_data['casts']
                    total_cost = user_data['cost']
                    total_gain = user_data['gain']
                    true_gain = int(total_gain) - int(total_cost)
                    await cmd.reply(f"{cmd.user.display_name}, during your {total_casts} casts, you gained {true_gain} points.")
                    await asyncio.sleep(1)
                    os.rename(filename2, f"{autocast_archive}/{user_id}_{fortime()}.json")
                elif tier == 2:
                    value = current_casts * 10
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 3:
                    value = current_casts * 15
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 4:
                    value = current_casts * 20
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                elif tier == 5:
                    value = current_casts * 25
                    new_points = current_points + value
                    user_data['points'] = new_points
                    user_data['autocasts'] = 0
                    user_data['casting'] = 0
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you have successfully canceled your autocasts. you recieved {value} points, now having {new_points} points.")
                else:
                    logger.info(f"{fortime()}: Error Refunding autocasts for {cmd.user.id}")
                    delete_last_line()
            elif fish_cmd.isdigit():
                casts = int(fish_cmd)
                filename = f"{user_directory}{user_id}.json"
                with open(filename, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                tier = user_data["fishtier"]
                casting = user_data['casting']
                current_casts = user_data['autocasts']
                current_points = user_data['points']
                if tier == 1:
                    if casting == 1:
                        if current_casts == 50:
                            await cmd.reply(f"{cmd.user.display_name}, you are already at the maximum permitted autocasts for your tier(Tier 1, maximum = 50).")
                        else:
                            new_casts = int(current_casts) + int(casts)

                            if new_casts > 50:
                                gain = 0
                                end_time = "null"
                                tracker_type = "cast"
                                added_casts = 50 - int(current_casts)
                                cost = int(added_casts) * 5
                                new_points = int(current_points) - int(cost)
                                user_data['points'] = new_points
                                user_data['autocasts'] = 50
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(f"{cmd.user.display_name} you have successfully added {added_casts} to your autocasts for {cost} points, you now have 50 autocasts remaining.")
                                track_autocasts(user_id, tracker_type, added_casts, cost, gain, end_time)
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {added_casts} to their autocasts")
                            else:
                                gain = 0
                                end_time = "null"
                                tracker_type = "cast"
                                cost = int(casts) * 5
                                new_points = int(current_points) - int(cost)
                                user_data['points'] = new_points
                                user_data['autocasts'] = new_casts
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                track_autocasts(user_id, tracker_type, new_casts, cost, gain, end_time)
                                await cmd.reply(f"{cmd.user.display_name} you successfully added {casts} autocasts for {cost} points, you now have {new_casts} autocasts remaining.")
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {casts} to their autocasts")
                    elif casts > 50:
                        gain = 0
                        end_time = "null"
                        tracker_type = "cast"
                        cost = 50 * 5
                        truecasts = 50
                        new_points = int(current_points) - int(cost)
                        user_data['points'] = new_points
                        user_data['autocasts'] = 50
                        user_data['casting'] = 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        track_autocasts(user_id, tracker_type, truecasts, cost, gain, end_time)
                        await cmd.reply(f"{cmd.user.display_name} you cannot autocast more than 50 for your current tier(Tier 1), autocasts set for {cost} points, you have 50 autocasts remaining.")
                        logger.info(f"{fortime()}: {cmd.user.id} successfully initiated autocasts, 50")
                    else:
                        if user_data["points"] < casts * 5:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            gain = 0
                            end_time = "null"
                            tracker_type = "cast"
                            cost = int(casts) * 5
                            user_data["autocasts"] = casts
                            user_data["points"] -= cost
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 5} points!")
                            track_autocasts(user_id, tracker_type, casts, cost, gain, end_time)
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 2:
                    if casting == 1:
                        if current_casts == 100:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you are already at the maximum permitted autocasts for your tier(Tier 2, max casts = 100).")
                        else:
                            new_casts = current_casts + casts

                            if new_casts > 100:
                                added_casts = 100 - current_casts
                                cost = added_casts * 10
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = 100
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you have successfully added {added_casts} to your autocasts for {cost} points, you now have 100 autocasts remaining.")
                                logger.info(
                                    f"{fortime()}: {cmd.user.id} successfully added {added_casts} to their autocasts")
                                delete_last_line()
                            else:
                                cost = casts * 10
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = new_casts
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you successfully added {casts} autocasts for {cost} points, you now have {new_casts} autocasts remaining.")
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {casts} to their autocasts")
                                delete_last_line()
                    elif casts > 100:
                        cost = 100 * 10
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 100
                        user_data['casting'] = 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name} you cannot autocast more than 100 for your current tier(Tier 2), autocasts set for {cost} points, you have 100 autocasts remaining.")
                        logger.info(f"{fortime()}: {cmd.user.id} successfully initiated autocasts, 100")
                        delete_last_line()
                    else:
                        if user_data["points"] < casts * 10:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 10
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 10} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 3:
                    if casting == 1:
                        if current_casts == 150:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you are already at the maximum permitted autocasts for your tier(Tier 3, max casts = 150).")
                        else:
                            new_casts = current_casts + casts

                            if new_casts > 150:
                                added_casts = 150 - current_casts
                                cost = added_casts * 15
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = 150
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you have successfully added {added_casts} to your autocasts for {cost} points, you now have 150 autocasts remaining.")
                                logger.info(
                                    f"{fortime()}: {cmd.user.id} successfully added {added_casts} to their autocasts")
                                delete_last_line()
                            else:
                                cost = casts * 15
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = new_casts
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you successfully added {casts} autocasts for {cost} points, you now have {new_casts} autocasts remaining.")
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {casts} to their autocasts")
                                delete_last_line()
                    elif casts > 150:
                        cost = 150 * 15
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 150
                        user_data['casting'] = 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name} you cannot autocast more than 150 for your current tier(Tier 3), autocasts set for {cost} points, you have 150 autocasts remaining.")
                        logger.info(f"{fortime()}: {cmd.user.id} successfully initiated autocasts, 150")
                        delete_last_line()
                    else:
                        if user_data["points"] < casts * 15:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 15
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 15} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 4:
                    if casting == 1:
                        if current_casts == 200:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you are already at the maximum permitted autocasts for your tier(Tier 4, max casts = 200).")
                        else:
                            new_casts = current_casts + casts

                            if new_casts > 200:
                                added_casts = 200 - current_casts
                                cost = added_casts * 20
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = 200
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you have successfully added {added_casts} to your autocasts for {cost} points, you now have 200 autocasts remaining.")
                                logger.info(
                                    f"{fortime()}: {cmd.user.id} successfully added {added_casts} to their autocasts")
                                delete_last_line()
                            else:
                                cost = casts * 20
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = new_casts
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you successfully added {casts} autocasts for {cost} points, you now have {new_casts} autocasts remaining.")
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {casts} to their autocasts")
                                delete_last_line()
                    elif casts > 200:
                        cost = 200 * 20
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 200
                        user_data['casting'] = 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name} you cannot autocast more than 200 for your current tier(Tier 4), autocasts set for {cost} points, you have 200 autocasts remaining.")
                        logger.info(f"{fortime()}: {cmd.user.id} successfully initiated autocasts, 200")
                        delete_last_line()
                    else:
                        if user_data["points"] < casts * 20:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 20
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 20} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                elif tier == 5:
                    if casting == 1:
                        if current_casts == 250:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you are already at the maximum permitted autocasts for your tier(Tier 5, max casts = 250).")
                        else:
                            new_casts = current_casts + casts

                            if new_casts > 250:
                                added_casts = 250 - current_casts
                                cost = added_casts * 25
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = 250
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you have successfully added {added_casts} to your autocasts for {cost} points, you now have 250 autocasts remaining.")
                                logger.info(
                                    f"{fortime()}: {cmd.user.id} successfully added {added_casts} to their autocasts")
                                delete_last_line()
                            else:
                                cost = casts * 25
                                new_points = current_points - cost
                                user_data['points'] = new_points
                                user_data['autocasts'] = new_casts
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await cmd.reply(
                                    f"{cmd.user.display_name} you successfully added {casts} autocasts for {cost} points, you now have {new_casts} autocasts remaining.")
                                logger.info(f"{fortime()}: {cmd.user.id} successfully added {casts} to their autocasts")
                                delete_last_line()
                    elif casts > 250:
                        cost = 250 * 25
                        new_points = current_points - cost
                        user_data['points'] = new_points
                        user_data['autocasts'] = 250
                        user_data['casting'] = 1
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        await cmd.reply(
                            f"{cmd.user.display_name} you cannot autocast more than 250 for your current tier(Tier 5), autocasts set for {cost} points, you have 250 autocasts remaining.")
                        logger.info(f"{fortime()}: {cmd.user.id} successfully initiated autocasts, 250")
                        delete_last_line()
                    else:
                        if user_data["points"] < casts * 25:
                            await cmd.reply(
                                f"{cmd.user.display_name}, you don't have enough points to set that many autocasts. Aborting...")
                        else:
                            user_data["autocasts"] = casts
                            user_data["points"] -= casts * 25
                            user_data["casting"] = 1
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await cmd.reply(
                                f"{cmd.user.display_name}, you have successfully set {casts} for {casts * 25} points!")
                            await asyncio.sleep(30)
                            await command_autofish(cmd.user.id, cmd.user.display_name)
                else:
                    return
            else:
                user_id = cmd.user.id
                user_name = cmd.user.display_name
                filename = f"{user_directory}{user_id}.json"
                filename2 = f"{inventory_dir}{user_id}.json"
                #default data
                user_default_data = {
                    "name": user_name,
                    "id": user_id,
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
                #end default data
                if not os.path.exists(filename):
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_default_data, f, indent=4)
                    logger.info(f"{fortime()}: Created {filename}")
                    delete_last_line()
                    await sort_command()
                    await asyncio.sleep(1)
                    with open(filename2, "w", encoding="utf-8") as g:
                        json.dump(user_inventory_default_data, g, indent=4)
                    logger.info(f"{fortime()}: Created inventory file for {user_id}")
                    delete_last_line()
                    await asyncio.sleep(1)
                    with open(filename, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    item = random.choice(fish_items_tier0)
                    current_points = user_data["points"]
                    new_points = current_points + item["points"]
                    user_data["points"] = new_points
                    user_data["fishtier"] = 1
                    user_data["inventory"] += 1
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(user_data, f, indent=4)
                    await asyncio.sleep(1)
                    with open(filename2, "r", encoding="utf-8") as f:
                        inventory_data = json.load(f)
                    inventory_data[f"{item['item']}"] += 1
                    with open(filename2, "w", encoding="utf-8") as f:
                        json.dump(inventory_data, f, indent=4)
                    await cmd.reply(
                        f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']} points. You now have {new_points} points, and automatically level up to fishtier 1!")
                else:
                    with open(filename, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                    casting = user_data['casting']
                    fishtier = user_data["fishtier"]
                    if casting == 1:
                        await cmd.reply(f"{cmd.user.display_name}, you are already autocasting. Please wait until your autocasts expire before fishing manually.")
                    elif fishtier == 0:
                        item = random.choice(fish_items_tier0)
                        current_points = user_data["points"]
                        new_points = current_points + item["points"]
                        user_data["points"] = new_points
                        user_data["fishtier"] = 1
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
                            f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']} points. You now have {new_points} points, and automatically level up to fishtier 1!")
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
                        await cmd.reply(
                            f"{cmd.user.display_name}, you caught a {item['item']} worth {item['points']} points. You now have {new_points} points!")
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
                    else:
                        logger.info(f"{fortime()}: Error fishing for {cmd.user.id}")
                        delete_last_line()
        except Exception as e:
            logger.info(f"{fortime()}: Error in fish_command -- {e}")
            delete_last_line()


async def command_autofish(user_id: str, user_name: str):
    try:
        filename = f"{user_directory}{user_id}.json"
        filename2 = f"{channel_doc}"
        filename3 = f"{autocast_tracker}/{user_id}.json"
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
                        end_time = f"{fortime()}"
                        casts = 0
                        cost = 0
                        tracker_type = "cast"
                        gain = item['points']
                        track_autocasts(user_id, tracker_type, casts, cost, gain, end_time)
                        await asyncio.sleep(5)

                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        with open(filename3, "r", encoding="utf-8") as f:
                            tracker_data = json.load(f)
                        tracker_casts = tracker_data['casts']
                        tracker_cost = tracker_data['cost']
                        tracker_gain = tracker_data['gain']
                        true_gain = tracker_gain - tracker_cost
                        filename4 = f"{inventory_dir}{user_id}.json"
                        with open(filename4, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        with open(filename4, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await bot.send_chat_message(target_id, user.id,
                                                    f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished! You casted {tracker_casts} casts, for a gain of {true_gain} points.")
                        os.rename(filename3, f"{autocast_archive}/{user_id}_{fortime()}.json")
                        return
                    else:
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(user_data, f, indent=4)
                        filename3 = f"{inventory_dir}{user_id}.json"
                        with open(filename3, "r", encoding="utf-8") as f:
                            inventory_data = json.load(f)
                        inventory_data[f"{item['item']}"] += 1
                        tracker_type = "cast"
                        casts = 0
                        cost = 0
                        gain = item['points']
                        end_time = "null"
                        track_autocasts(user_id, tracker_type, casts, cost, gain, end_time)
                        with open(filename3, "w", encoding="utf-8") as f:
                            json.dump(inventory_data, f, indent=4)
                        await bot.send_chat_message(target_id, user.id,
                                                    f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(110)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(100)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(90)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. Your casts have expired!")
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. Your casts have expired!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! Your autocasts have finished!")
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
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, had no lives left and died. In order to return to the living, you gave up everything you had.")
                            else:
                                current_lives = user_data["lives"]
                                new_lives = current_lives - 1
                                user_data["lives"] = new_lives
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(user_data, f, indent=4)
                                await bot.send_chat_message(target_id, user.id,
                                                            f"{user_name}, you caught a shark, loosing a life. you now have {new_lives} left. You have {new_casts} casts remaining!")
                                await asyncio.sleep(80)
                                await command_autofish(user_id, user_name)
                        elif item['item'] == "Health Jar":
                            current_lives = user_data["lives"]
                            new_lives = current_lives + 1
                            user_data["lives"] = new_lives
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(user_data, f, indent=4)
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a Health Jar. You gain a life. You now have {new_lives} lives. You have {new_casts} casts remaining!")
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
                            await bot.send_chat_message(target_id, user.id,
                                                        f"{user_name}, you caught a {item['item']} worth {item['points']}. You now have {new_points} points! You have {new_casts} casts remaining!")
                            await asyncio.sleep(80)
                            await command_autofish(user_id, user_name)
                else:
                    logger.info(f"{fortime()}: Error fishing for {user_id}")
                    delete_last_line()
                    await asyncio.sleep(200)
                    return
            else:
                return
        else:
            pass
    except Exception as e:
        logger.info(f"{fortime()}: Error reading channel doc for autofish -- {e}")
        delete_last_line()
# --------End Mini Games-----------#


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


# -----main process-----#
async def run():
    async def shutdown():
        with open(bot_doc, "r", encoding="utf-8") as f:
            data = json.load(f)
        bot_resetting = data['resetting']
        if bot_resetting == 1:
            chat.stop()
            await asyncio.sleep(1)
            await bot.close()
            logger.info(f"{long_dashes}\nTwitch Processes Shutdown")
            await asyncio.sleep(1)
            logger.info(f"{long_dashes}\nShutdown Sequence Completed")
        else:
            await shutdown_refund()
            chat.stop()
            await asyncio.sleep(1)
            await bot.close()
            logger.info(f"{long_dashes}\nTwitch Processes Shutdown")
            await asyncio.sleep(1)
            logger.info(f"{long_dashes}\nShutdown Sequence Completed")
            filename = channel_doc
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            live = data['live']
            if live == 0:
                await bot.send_chat_message(target_id, user.id, f"{bot_name} is leaving the chat...")
            else:
                await bot.send_chat_message(target_id, user.id, f"{bot_name} is restarting, bare with me...")

    # --------Fix this broke shit--------#
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
    # --------End Note--------#

    with open(bot_doc, "r", encoding="utf-8") as f:
        data = json.load(f)
    resetting_true = data['resetting']
    if resetting_true == 1:
        print("Completing bot reset...")
        os.rename(f"{logs_directory}", f"{archive_dir}/logs/")
        print("Reset complete, now booting...")
        await asyncio.sleep(1)
        data['resetting'] = 0
        with open(bot_doc, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        Path(logs_directory).mkdir(parents=True, exist_ok=True)
        Path(archive_logs_directory).mkdir(parents=True, exist_ok=True)

        chat = await Chat(bot)

        # ---event activation
        chat.register_event(ChatEvent.READY, on_ready)
        chat.register_event(ChatEvent.MESSAGE, on_message)
        chat.register_event(ChatEvent.SUB, on_sub)
        # ---end event activation
        
        # ---chat message command activation
        chat.register_command('discord', command_discord)
        chat.register_command('donate', command_donate)
        chat.register_command('tech', command_tech)
        chat.register_command('joe', command_joe)
        # ---end chat message command activation
        
        # ---simple command activation
        chat.register_command('bite', command_bite)
        chat.register_command('so', command_shoutout)
        chat.register_command('slap', command_slap)
        chat.register_command('lurk', command_lurk)
        #To be fixed(VVVVV)
        #chat.register_command('followage', command_followage)
        #To be fixed(^^^^^)
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
        chat.register_command('checkin', checkin_command)
        chat.register_command('bonk', command_bonk)
        chat.register_command('phone', command_phone)
        chat.register_command('steal', steal_command)
        chat.register_command('jail', command_jail)
        chat.register_command('givepoints', givepoints_command)
        chat.register_command('rob', rob_command)
        # ---end simple command activation

        # minigame activation
        chat.register_command('bet', command_bet)
        chat.register_command('fish', command_fish)
        # ---end minigame activation

        # ---streamer only commands
        chat.register_command('islive', live_command)
        chat.register_command('reset', reset_command)
        chat.register_command('pause', command_pause)
        chat.register_command('resume', command_resume)
        chat.register_command('banterm', banned_term_command)
        chat.register_command('sort', sort_command)
        chat.register_command('clear', archive_delete_command)
        chat.register_command('mkbkup', mkbkup_command)
        chat.register_command('addpoints', addpoints_command)
        chat.register_command('cmd', command_control)
        # ---end

        chat.start()

        logger.info(f"Please wait, {bot_name} is loading user documents...")
        await asyncio.sleep(1)
        await sort_command()
        await asyncio.sleep(1)
        logger.info(f"{fortime()}: Loaded user documents successfully")
        await bot.send_chat_message(target_id, user.id, f"{bot_name} is live...")
        await asyncio.sleep(2.5)
        while True:
            cls()
            try:
                user_input = input("Enter 1 To Run Test Command\n"
                               "Enter 2 to clear archives\n"
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
                        await archive_delete_console()
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
    else:
        chat = await Chat(bot)

        # ---event activation
        chat.register_event(ChatEvent.READY, on_ready)
        chat.register_event(ChatEvent.MESSAGE, on_message)
        chat.register_event(ChatEvent.SUB, on_sub)
        # ---end event activation

        # ---chat message command activation
        chat.register_command('discord', command_discord)
        chat.register_command('donate', command_donate)
        chat.register_command('tech', command_tech)
        chat.register_command('joe', command_joe)
        # ---end chat message command activation
        
        # ---simple command activation
        chat.register_command('bite', command_bite)
        chat.register_command('so', command_shoutout)
        chat.register_command('slap', command_slap)
        chat.register_command('lurk', command_lurk)
        #To be fixed(VVVVV)
        #chat.register_command('followage', command_followage)
        #To be fixed(^^^^^)
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
        chat.register_command('checkin', checkin_command)
        chat.register_command('bonk', command_bonk)
        chat.register_command('phone', command_phone)
        chat.register_command('steal', steal_command)
        chat.register_command('jail', command_jail)
        chat.register_command('givepoints', givepoints_command)
        chat.register_command('rob', rob_command)
        # ---end simple command activation

        # minigame activation
        chat.register_command('bet', command_bet)
        chat.register_command('fish', command_fish)
        # ---end minigame activation

        # ---mod/streamer only commands
        chat.register_command('islive', live_command)
        chat.register_command('reset', reset_command)
        chat.register_command('pause', command_pause)
        chat.register_command('resume', command_resume)
        chat.register_command('banterm', banned_term_command)
        chat.register_command('sort', sort_command)
        chat.register_command('clear', archive_delete_command)
        chat.register_command('mkbkup', mkbkup_command)
        chat.register_command('addpoints', addpoints_command)
        chat.register_command('cmd', command_control)
        # ---end

        chat.start()

        logger.info(f"Please wait, {bot_name} is loading user documents...")
        await asyncio.sleep(1)
        await sort_command()
        await asyncio.sleep(1)
        logger.info(f"{fortime()}: Loaded user documents successfully")
        await asyncio.sleep(2)
        await bot.send_chat_message(target_id, user.id, f"{bot_name} is live...")
        await asyncio.sleep(2.5)
        while True:
            cls()
            try:
                user_input = input("Enter 1 To Run Test Command\n"
                                   "Enter 2 To Clear Archives\n"
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
                        await archive_delete_console()
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
