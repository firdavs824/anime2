from aiogram.fsm.state import State, StatesGroup


class CreateAnimeStates(StatesGroup):
    waiting_for_title = State()        # Anime nomi
    waiting_for_code = State()         # Anime kodi (masalan: 1, 105, naruto)
    waiting_for_video = State()        # 1-qism videosi


class AddEpisodeStates(StatesGroup):
    waiting_for_anime_code = State()   # Qaysi anime kodi
    waiting_for_episode_num = State()  # Qism raqami
    waiting_for_video = State()        # Qism videosi


class SearchAnimeStates(StatesGroup):
    waiting_for_code = State()         # Qidiruv kodi


class DeleteAnimeStates(StatesGroup):
    waiting_for_code = State()         # O'chirish kodi


class BroadcastStates(StatesGroup):
    waiting_for_message = State()      # Xabar tarqatish


class AdminLoginStates(StatesGroup):
    waiting_for_password = State()     # Adminlik paroli


class ChannelPostStates(StatesGroup):
    waiting_for_media = State()        # Rasm yoki video (muqova)
    waiting_for_text = State()         # Post matni (caption)
    confirm_post = State()             # Tasdiqlash va kanalga jo'natish

