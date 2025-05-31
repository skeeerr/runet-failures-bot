from aiogram import Bot
from aiogram.utils.deep_linking import get_start_link

async def generate_referral_link(bot: Bot, user_id: int) -> str:
    return await get_start_link(payload=str(user_id), encode=True)
