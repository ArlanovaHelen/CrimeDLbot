from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.types import InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.middlewares import BaseMiddleware
import datetime
import functions_for_bot
import sqlite_db
import ask_ai4
import os
from dotenv import load_dotenv

load_dotenv()



def get_people_ikb() -> InlineKeyboardMarkup:
	ikb = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton('Що я вмію', callback_data='about_me')],
		[InlineKeyboardButton('Отримати дані з кримінальної статистики', callback_data='show_info')],
	], reply_markup=get_cancel_kb())

	return ikb




def insert_people_ikb() -> InlineKeyboardMarkup:
	ikb = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton('Внести відомості про особу', callback_data='about_me')],

	])

	return ikb


def get_cancel_kb() -> ReplyKeyboardMarkup:
	kb = ReplyKeyboardMarkup(keyboard=[
		[KeyboardButton('/cancel')]

	], resize_keyboard=True)
	return kb


def get_start_kb() -> ReplyKeyboardMarkup:
	kb = ReplyKeyboardMarkup(keyboard=[
		[KeyboardButton('/start')]

	], resize_keyboard=True)
	return kb



storage = MemoryStorage()
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot, storage=storage)
now = datetime.datetime.today().strftime('%Y-%m-%d')

class AnswerStateGroup(StatesGroup):

	inf_answer = State()
async def on_startup(_):
	await sqlite_db.db_connect()


@dp.message_handler(commands=['start'])
async def cmd_cancel(message: types.Message) -> None:
	await bot.send_message(chat_id=message.from_user.id, text='Доброго дня!', reply_markup=get_people_ikb())


@dp.message_handler(commands=['cancel'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
	if state is None:
		return

	await message.answer('Дані не завантажено!', reply_markup=get_start_kb())





@dp.callback_query_handler(text='about_me')
async def cb_show_about_me(callback: types.CallbackQuery) -> None:
	my_text = (f"Я можу допомогти провести аналіз статей КК за роками у понад 150 категоріях, надсилаю повний список.")
	await callback.message.answer(my_text, reply_markup=get_cancel_kb())

	document = InputFile("data_to_compare.txt")

	await bot.send_document(
		chat_id=callback.from_user.id,
		document=document, reply_markup=get_people_ikb()
	)

	await bot.answer_callback_query(callback.id)

@dp.callback_query_handler(text='show_info')
async def cb_show_info(callback: types.CallbackQuery) -> None:
	my_text = (f"Задайте питання з кримінальної статистики")
	await callback.message.answer(my_text, reply_markup=get_cancel_kb())
	await AnswerStateGroup.inf_answer.set()

@dp.message_handler(state=AnswerStateGroup.inf_answer)
async def load_question(message: types.Message, state: FSMContext) -> None:
	async with state.proxy() as data:
		data['inf_answer'] = message.text

		user_question = data['inf_answer']
		file_path = "data_to_compare.txt"
		text_data = ask_ai4.load_text_data(file_path)

		text_chunks = ask_ai4.split_text(text_data)

		all_responses = []
		for chunk in text_chunks:
			gpt_response = ask_ai4.ask_gpt_with_text_context(user_question, chunk)

			if gpt_response.lower().startswith("пропу"):
				pass
			else:
				all_responses.append(gpt_response)

		if all_responses:
			final_response = "\n".join(all_responses)
			try:

				to_send = functions_for_bot.find_sql(gpt_response)
				answer_to_query = sqlite_db.find_rows(to_send)
				if len(answer_to_query) > 1 or len(answer_to_query[0]) > 1: #or len(answer_to_query[1]) > 0

					functions_for_bot.create_statistic_file(data=answer_to_query)

					await message.answer(text='Для формування відповіді на Ваше питання було опрацьовано SQL-запит:')
					await message.answer(text=to_send)
					await message.answer(text="Насилаю файл зі статистичною інформацією:")

					await bot.send_document(message.from_user.id, open('report.xlsx', 'rb'), reply_markup=get_people_ikb())


				else:
					await message.answer(text='Для формування відповіді на Ваше питання було опрацьовано SQL-запит:')
					await message.answer(text=to_send)
					if answer_to_query[0][0] == None:
						await message.answer(
							text=fr"Остаточна відповідь: інформація відсутня, спробуйте по іншому сформувати питання", reply_markup=get_people_ikb())
					else:
						await message.answer(text=fr"Остаточна відповідь: {answer_to_query[0][0]}", reply_markup=get_people_ikb())

			except:
				await message.answer(text=fr"Питання сформовано не корректно", reply_markup=get_people_ikb())


		else:
			await message.answer(text=fr"Питання сформовано не корректно. Жодної відповіді не знайдено.", reply_markup=get_people_ikb())

	await AnswerStateGroup.next()

	
if __name__ == '__main__':
	dp.middleware.setup(BaseMiddleware())
	executor.start_polling(dispatcher=dp, skip_updates=True)

