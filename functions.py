async def xp_transfer(chatter_document, value: float, add: bool = True):
    try:
        break_value = 1000000
        response_level = None
        new_boost = chatter_document['data_rank']['boost']
        user_id, user_name = chatter_document['_id'], chatter_document['name']
        new_user_level, start_user_level = chatter_document['data_rank']['level'], chatter_document['data_rank']['level']
        if add:
            value = value / 2
            if chatter_document['data_rank']['boost'] > 0.0:
                if chatter_document['data_rank']['boost'] > value:
                    boost_add = abs(chatter_document['data_rank']['boost'] - (abs(chatter_document['data_rank']['boost'] - value)))
                else:
                    boost_add = chatter_document['data_rank']['boost']
                new_boost = chatter_document['data_rank']['boost'] - boost_add
                value += boost_add
            new_user_xp_points = chatter_document['data_rank']['xp'] + value
            x = 0
            while True:
                level_mult = 1.0
                if new_user_level > 1:
                    level_mult += float((new_user_level / 2) * new_user_level)
                xp_needed = (level_const * level_mult) * new_user_level
                special_logger.info(f"XP-INCREASE: {user_name} Level(XP): {new_user_level}({new_user_xp_points}) -- XP Needed: {xp_needed}")
                if new_user_xp_points >= xp_needed:
                    new_user_level += 1
                else:
                    break
                if x >= break_value:
                    special_logger.error(f"{fortime()}: breaking xp gain loop, something broke")
                    break
                x += 1
        else:
            new_user_xp_points = float(chatter_document['data_rank']['xp'] - (value / 2))
            x = 0
            while True:
                level_mult = 1.0
                new_user_level_test = new_user_level - 1
                if new_user_level_test > 1:
                    level_mult += float((new_user_level_test / 2) * new_user_level_test)
                xp_needed = (level_const * level_mult) * new_user_level_test
                special_logger.info(f"XP-DECREASE: {user_name} Level(XP): {new_user_level}({new_user_xp_points}) -- XP Needed: {xp_needed}")
                if new_user_xp_points < xp_needed and new_user_level > 1:
                    new_user_level -= 1
                else:
                    break
                if x >= break_value:
                    special_logger.error(f"{fortime()}: breaking xp loss loop, something broke")
                    break
                x += 1
        chatter_document['data_rank'].update(boost=new_boost, level=new_user_level, xp=new_user_xp_points)
        chatter_document.save()
        chatter_document = Users.objects.get(_id=user_id)
        if chatter_document['data_rank']['level'] > start_user_level:
            response_level = f"{user_name} you leveled up from {start_user_level:,} to {chatter_document['data_rank']['level']:,}. Current XP: {chatter_document['data_rank']['xp']:,.2f}"
        elif chatter_document['data_rank']['level'] < start_user_level:
            response_level = f"{user_name} you lost {'a level' if abs(start_user_level - chatter_document['data_rank']['level']) == 1 else 'some levels'} from {start_user_level:,} to {chatter_document['data_rank']['level']:,}. Current XP: {chatter_document['data_rank']['xp']:,.2f}"
        return chatter_document, response_level
    except Exception as e:
        logger.error(f"Error in xp_transfer -- {e}")
        return None


async def twitch_points_transfer(chatter_document: Document, channel_document: Document, value: float, add: bool = True, gamble: bool = False):
    try:
        if chatter_document is not None:
            response_level = None
            if add and channel_document['data_channel']['hype_train']['current']:
                value = check_hype_train(channel_document, value)
            _id = chatter_document['_id']
            if not add and gamble:
                pass
            else:
                chatter_document, response_level = await xp_transfer(chatter_document, value, add)
            if add:
                new_user_points = chatter_document['data_user']['points'] + value
            else:
                new_user_points = chatter_document['data_user']['points'] - value
            chatter_document['data_user'].update(points=new_user_points)
            chatter_document['data_user']['dates'].update(latest_chat=datetime.datetime.now())
            chatter_document.save()
            chatter_document = Users.objects.get(_id=_id)
            return chatter_document, response_level
    except Exception as e:
        logger.error(f"{fortime()}: Error in twitch_points_transfer -- {chatter_document['_id']}/{chatter_document['name']}/{chatter_document['data_user']['login']} -- {e}")
        return None


async def select_target(channel_document, chatter_id, manual_choice: bool = False, target_user_name: str = "", game_type: str = "tag"):
    try:
        users = await bot.get_chatters(id_streamer, id_streamer)
        users_collection = twitch_database.twitch.get_collection('users')
        users_documents = users_collection.find({})
        valid_users = []
        for chatter_document in users_documents:
            valid_users.append(str(chatter_document['data_user']['id']))
        if manual_choice:
            target = None
            for user in users.data:
                if user.user_name.lower() == target_user_name:
                    target = user
            if target is not None:
                if target.user_id not in valid_users:
                    target = None
        else:
            list_to_check = []
            if game_type == "tag":
                for entry in channel_document['data_lists']['lurk']:
                    if entry not in list_to_check:
                        list_to_check.append(entry)
                for entry in channel_document['data_lists']['non_tag']:
                    if entry not in list_to_check:
                        list_to_check.append(entry)
            while True:
                target = random.choice(users.data)
                special_logger.info(f"select_target_start {len(users.data)} {target.user_name} {target.user_id}")
                if target.user_id in valid_users and target.user_id not in list_to_check:
                    if chatter_id != target.user_id:
                        special_logger.info(f"select_target_chose {len(users.data)} {target.user_name} {target.user_id}")
                        break
                users.data.remove(target)
                special_logger.info(f"select_target_remove {len(users.data)} {target.user_name} {target.user_id}")
                if len(users.data) <= 1:
                    target = None
                    if game_type != "tag":
                        await bot.send_chat_message(id_streamer, id_streamer, f"Error fetching random target... Are we thee only ones here?")
                    special_logger.info(f"select_target_none total:{users.total} list_to_check:{len(list_to_check)} ignore_list:{len(channel_document['data_lists']['ignore'])} -- dif:{abs(users.total - len(list_to_check)) - len(channel_document['data_lists']['ignore'])} -- game_type:{game_type}")
                    break
        return target
    except Exception as e:
        logger.error(f"Error selecting_target -- {e}")
        return None


async def on_stream_ad_start(data: ChannelAdBreakBeginEvent):
    try:
        if not read_night_mode():
            marathon_response = None
            # old_pause = float(read_pause())
            # if old_pause not in (1.0, 2.0):
            #     old_pause = 1.0
            if data.event.is_automatic:
                auto_response = "this is a automatically scheduled ad break"
            else:
                auto_response = "this is a manually ran ad to attempt to time things better"
            ad_schedule = await bot.get_ad_schedule(id_streamer)
            ad_till_next_seconds, now_time_seconds = await get_ad_time(ad_schedule)
            ad_length = float(ad_schedule.duration)
            seconds_till_ad = ad_till_next_seconds - now_time_seconds
            await bot.send_chat_announcement(id_streamer, id_streamer, f"Incoming ad break, {auto_response} and should only last {datetime.timedelta(seconds=ad_length)}. Next ad inbound in {datetime.timedelta(seconds=seconds_till_ad)}.{f' {marathon_response}.' if marathon_response is not None else ''}", color="purple")
            # channel_document = await get_channel_document(data.event.broadcaster_user_id, data.event.broadcaster_user_name, data.event.broadcaster_user_login)
            # if channel_document['data_channel']['writing_clock']:
            #     with open(clock_pause, "w") as file:
            #         file.write(str(ad_length))
            #     special_logger.info(f"{fortime()}: Wrote pause time in on_stream_ad_start: {datetime.timedelta(seconds=ad_length)}")
            #     marathon_response = f"Marathon Timer Paused"
            # obs.set_source_visibility("NS-Overlay", "InAd", True)
            # if channel_document['data_channel']['writing_clock']:
            #     await asyncio.sleep(old_pause + 1)
            #     with open(clock_pause, "w") as file:
            #         file.write(str(old_pause))
            #     special_logger.info(f"{fortime()}: Wrote pause time in on_stream_ad_start: {old_pause}")
            # await asyncio.sleep(ad_length - (old_pause + 1) if channel_document['data_channel']['writing_clock'] else ad_length)
            # await asyncio.sleep(ad_length)
            # obs.set_source_visibility("NS-Overlay", "InAd", False)
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_ad_start' -- {e}")
        return


async def on_stream_poll_begin(data: ChannelPollBeginEvent):
    try:
        choices = []
        for n, choice in enumerate(data.event.choices):
            choices.append(f"{n+1}: {choice.title}")
        time_till_end = await get_long_sec(fortime_long(data.event.ends_at.astimezone()))
        seconds_now = await get_long_sec(fortime_long(datetime.datetime.now()))
        await bot.send_chat_announcement(id_streamer, id_streamer, f"Poll '{data.event.title}' has started. Choices are: {' - '.join(choices)}. Poll will end in {datetime.timedelta(seconds=abs(time_till_end - seconds_now))}. Voting with extra channel points is {'enabled' if data.event.channel_points_voting.is_enabled else 'disabled'}", color="green")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_poll_begin' -- {e}")
        return


async def on_stream_poll_end(data: ChannelPollEndEvent):
    try:
        if data.event.status != "completed":
            return
        choices = []
        for choice in data.event.choices:
            choices.append([choice.votes, choice.title])
        choices_sorted = sorted(choices, key=lambda choice: choice[0], reverse=True)
        winner = choices_sorted[0]
        await bot.send_chat_announcement(id_streamer, id_streamer, f"Poll '{data.event.title}' has ended. Thee winner is: {winner[1].title()} with {winner[0]} votes!", color="orange")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_poll_end' -- {e}")
        return


async def on_stream_update(data: ChannelUpdateEvent):
    try:
        channel_document = await get_channel_document(data.event.broadcaster_user_id, data.event.broadcaster_user_name, data.event.broadcaster_user_login)
        if channel_document is None:
            logger.error(f"{fortime()}: ERROR: Channel Document is NONE!!! -- in on_stream_update")
            return
        if data.event.title != channel_document['channel_details']['title'] or data.event.category_id != channel_document['channel_details']['game_id']:
            response = []
            title_new, game_id_new, game_name_new = channel_document['channel_details']['title'], channel_document['channel_details']['game_id'], channel_document['channel_details']['game_name']
            if channel_document['channel_details']['title'] != data.event.title:
                response.append(f"Title Change to {data.event.title}")
                title_new = data.event.title
            if channel_document['channel_details']['game_id'] != data.event.category_id:
                response.append(f"Category Change to {data.event.category_name}")
                game_id_new = data.event.category_id
                game_name_new = data.event.category_name
                channel_document = await game_id_check(data.event.category_id, channel_document)
                if channel_document is None:
                    return
            channel_document['channel_details'].update(title=title_new, game_id=game_id_new, game_name=game_name_new)
            channel_document.save()
            await bot.send_chat_message(id_streamer, id_streamer, f"Channel Update: {' -- '.join(response)}")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_update' -- {e}")
        return


async def on_stream_start(data: StreamOnlineEvent):
    try:
        channel_document = await get_channel_document(data.event.broadcaster_user_id, data.event.broadcaster_user_name, data.event.broadcaster_user_login)
        if channel_document is not None:
            new_ats_count, new_cod_count, new_crash_count, new_tag = [0, 0], [0, 0, 0, 0], 0, [None, None, None]
            if channel_document['channel_details']['online_last'] is not None:
                if await get_long_sec(fortime_long(datetime.datetime.now())) - await get_long_sec(fortime_long(channel_document['channel_details']['online_last'])) < 7200:
                    new_ats_count = channel_document['data_counters']['ats']
                    new_cod_count = channel_document['data_counters']['cod']
                    new_crash_count = channel_document['data_counters']['stream_crash']
                    new_tag = channel_document['data_games']['tag']
            channel_info = await bot.get_channel_information(id_streamer)
            channel_mods = []
            async for mod in bot.get_moderators(id_streamer):
                channel_mods.append(mod.user_id)
            channel_document['channel_details'].update(online=True, branded=channel_info[0].is_branded_content, title=channel_info[0].title,
                                                       game_id=channel_info[0].game_id, game_name=channel_info[0].game_name,
                                                       content_class=channel_info[0].content_classification_labels, tags=channel_info[0].tags)
            channel_document['data_channel']['hype_train'].update(current=False, current_level=1)
            channel_document['data_counters'].update(ats=new_ats_count, cod=new_cod_count, stream_crash=new_crash_count)
            channel_document['data_games'].update(tag=new_tag)
            channel_document['data_lists'].update(mods=channel_mods)
            channel_document.save()
        await bot.send_chat_announcement(id_streamer, id_streamer, f"Hola. I is here :D Big Chody Hugs.", color="green")
        if channel_document['data_channel']['writing_clock']:
            await bot.send_chat_message(id_streamer, id_streamer, f"{link_loots} | Monthly use 20% off coupon: {link_loots_discount}")
            with open("data/bot/pack_link", "r") as file:
                link = file.read()
            response_pack = list(map(str, link.splitlines()))
            for i in range(0, len(response_pack), 10):
                await bot.send_chat_message(id_streamer, id_streamer, " | ".join(response_pack[i:i + 10]))
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_start' -- {e}")
        return


async def on_stream_end(data: StreamOfflineEvent):
    try:
        channel_document = await get_channel_document(data.event.broadcaster_user_id, data.event.broadcaster_user_name, data.event.broadcaster_user_login)
        if channel_document is not None:
            channel_document['channel_details'].update(online=False, online_last=datetime.datetime.now())
            channel_document.save()
        await bot.send_chat_announcement(id_streamer, id_streamer, f"I have faded into thee shadows. {response_thanks}", color="blue")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_end' -- {e}")
        return


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def setup_logger(name: str, log_file: str, logger_list: list, level: logging = logging.INFO):
    try:
        local_logger = logging.getLogger(name)
        handler = logging.FileHandler(f"{logs_directory}{log_file}", mode="w", encoding="utf-8")
        if name in ("logger", "countdown_logger"):
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


async def full_shutdown(logger_list):
    logging.shutdown()
    for entry in logger_list:
        try:
            os.rename(f"{logs_directory}{entry}", f"{logs_directory}\\archive_log\\{entry}")
        except Exception as e:
            print(e)
            pass
    quit(420)


def fortime():
    try:
        return str(datetime.datetime.now().strftime('%y-%m-%d %H:%M:%S'))
    except Exception as e:
        print(f"Error creating formatted_time -- {e}")
        return None

