from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware
import logging

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseMiddleware):
    async def on_process_message(self, message: types.Message, data: dict):
        try:
            return await super().on_process_message(message, data)
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await message.answer("⚠️ Произошла ошибка при обработке запроса")

    async def on_process_callback_query(self, query: types.CallbackQuery, data: dict):
        try:
            return await super().on_process_callback_query(query, data)
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}", exc_info=True)
            await query.answer("⚠️ Произошла ошибка при обработке запроса")
