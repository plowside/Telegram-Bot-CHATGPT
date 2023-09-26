# -*- coding: utf-8 -*-
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram import Bot, types
import asyncio, sqlite3, openai, time, logging, re

#################################################################################################################################
storage = MemoryStorage()
bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s', level=logging.INFO,)

openai.api_key = openai_api_key
#################################################################################################################################

class openai_plowsidee:
	def __init__(self):
		self.alive = True
		self.response = ''

	async def create_conversation(self, question, conf=[]):
		conf.append({"role": "user", "content": question})
		last_resp = ''
		async for resp in await openai.ChatCompletion.acreate(model='gpt-3.5-turbo', messages=conf, max_tokens=2048, stream=True):
			if resp.choices[0].finish_reason != None: self.alive=False;break
			try:
				if resp.choices[0].delta.content != last_resp:
					self.response+=str(resp.choices[0].delta.content)
					last_resp = resp.choices[0].delta.content
			except:pass
		self.alive=False


con = sqlite3.connect('db.db')
cur = con.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS users(
	id INTEGER,
	username TEXT,
	first_name TEXT,
	question_num INTEGER DEFAULT (0)
	)''')
cur.execute('''CREATE TABLE IF NOT EXISTS conversations(
	id INTEGER,
	uid INTEGER,
	question TEXT,
	create_date INT,
	answer TEXT,
	is_show BOOL DEFAULT (True)
	)''')


# Hi message
@dp.message_handler(CommandStart())
async def start(message: types.Message):
	user_db = (cur.execute(f'SELECT * FROM users WHERE id = {message.from_user.id}')).fetchone()
	temp=message.from_user.first_name.replace('"','""')
	if user_db is None:
		cur.execute(f'INSERT INTO users VALUES ({message.from_user.id}, "{message.from_user.username if message.from_user.username else "no_username"}","{temp}", 0)')
	elif user_db[2] != message.from_user.first_name:
		cur.execute(f'UPDATE users SET first_name = "{temp}" WHERE id = {message.from_user.id}')
	elif user_db[1] != message.from_user.username:
		cur.execute(f'UPDATE users SET username = "{message.from_user.username}" WHERE id = {message.from_user.id}')
	con.commit()
	
	await message.answer('''<b>Привет!</b>

Этот бот открывает вам доступ к продуктам OpenAI, таким как ChatGPT, для создания текста и изображений (В будущем).

⚡️Бот использует <b>ту же модель, что и сайт ChatGPT: gpt-3.5-turbo.</b>

<b>Чатбот умеет:</b>
1. <i>Писать и редактировать тексты</i>
2. <i>Переводить с любого языка на любой</i>
3. <i>Писать и редактировать код</i>
4. <i>Отвечать на вопросы</i>

Вы можете общаться с ботом, как с живым собеседником, задавая вопросы на любом языке. Обратите внимание, что иногда бот придумывает факты, а также обладает ограниченными знаниями о событиях после 2021 года.

✉️ Чтобы получить <b>текстовый ответ</b>, просто напишите в чат ваш вопрос.

🔄 Чтобы удалить <b>контекст диалога</b> используйте команду /deletecontext.''', parse_mode=types.ParseMode.HTML)


# Delete last context 
@dp.message_handler(commands=['deletecontext'])
async def deletecontext(message: types.Message):
	cur.execute(f"UPDATE conversations SET is_show = False WHERE uid = {message.from_user.id}")
	con.commit()
	await message.answer('<b>Контекст удален. По умолчанию бот в ответе учитывает все ваши предыдущие вопросы/сообщения и свои ответы на них.</b>', parse_mode=types.ParseMode.HTML)


# get datebase backup
@dp.message_handler(commands=['db'])
async def db(message: types.Message):
	if message.from_user.id in admin_id: await message.answer_document(open('db.db','rb'))


# Main handler
@dp.message_handler(content_types=['text'])
async def get_question(message: types.Message):
	user_db = (cur.execute(f'SELECT * FROM users WHERE id = {message.from_user.id}')).fetchone()
	temp=message.from_user.first_name.replace('"','""')
	if user_db is None:
		cur.execute(f'INSERT INTO users VALUES ({message.from_user.id}, "{message.from_user.username if message.from_user.username else "no_username"}","{temp}", 0)')
	elif user_db[2] != message.from_user.first_name:
		cur.execute(f'UPDATE users SET first_name = "{temp}" WHERE id = {message.from_user.id}')
	elif user_db[1] != message.from_user.username:
		cur.execute(f'UPDATE users SET username = "{message.from_user.username}" WHERE id = {message.from_user.id}')
	con.commit()

	conversation = get_conversation(message.from_user.id)
	conf = [{'role':'user','content':x[2]} for x in conversation]
	text = message.text.replace("'","''")
	count = len((cur.execute(f'SELECT * FROM conversations WHERE uid = {message.from_user.id}')).fetchall())
	logging.info(f'User: [{message.from_user.id}|{"@"+message.from_user.username if message.from_user.username else "no_username"}|{message.from_user.first_name}|{count}]')
	await bot.send_chat_action(chat_id=message.chat.id, action="typing")
	op = openai_plowsidee()
	asyncio.get_event_loop().create_task(op.create_conversation(message.text, conf))
	last_resp = 0
	answer = ''
	message_ = None
	while op.alive:
		if len(op.response) - last_resp > 220:
			answer = op.response
			last_resp = len(answer)
			if message_ is None:
				try:message_ = await message.answer(answer)
				except:pass
			else:
				try:await message_.edit_text(answer)
				except:pass
		await asyncio.sleep(.5)
	answer = op.response

	temp=answer.replace("'","''")
	cur.execute(f"INSERT INTO conversations(id,uid,question,create_date,answer) VALUES ({count},{message.from_user.id}, '{text}', {int(time.time())}, '{temp}')")
	cur.execute(f'UPDATE users SET question_num = {count+1} WHERE id = {message.from_user.id}')
	con.commit()

	if "```" in answer:
		def kb_temp(id, uid):
			keyboard = InlineKeyboardMarkup()
			s={'Получить код':f'util:get_code:{id}:{uid}'}
			for x in s: keyboard.insert(InlineKeyboardButton(x,callback_data=s[x]))
			return keyboard
		if message_ is None:
			message_ = await message.answer(answer, reply_markup=kb_temp(count,message.from_user.id))
		else: await message_.edit_text(answer, reply_markup=kb_temp(count,message.from_user.id))
	else:
		if message_ is None:
			message_ = await message.answer(answer)
		else: 
			try:await message_.edit_text(answer)
			except:pass


# callback handler [get code from text]
@dp.callback_query_handler(text_startswith='util')
async def util(call: types.CallbackQuery):
	cd = call.data.split(':')
	if cd[1] == 'get_code':
		gg=cur.execute(f'SELECT answer FROM conversations WHERE id = {int(cd[2])} AND uid = {int(cd[3])}')
		s=gg.fetchone()[0]
		if s == '' or s is None:
			await call.answer('Error: message is empty',show_alert=True)
			return            
		last=0
		br=len(re.findall("```",s))
		text=[]
		num = 0
		while True:
			try:
				num+=1
				_1=s.index("```",last+3) + 3
				_2=s.index("```", _1)
				if len(text) * 2 >= br:
					break
				last = _2
				text.append(f'<b>Code №{num}:</b>\n<code>{s[_1:_2].strip()}</code>')
			except Exception as error:
				print(error)
				break
		await call.message.answer('\n\n'.join(text), parse_mode=types.ParseMode.HTML)

# Get active context from db
def get_conversation(uid):
	return cur.execute(f'SELECT * FROM conversations WHERE uid = {uid} AND is_show = True').fetchall()

# Get answer from openai
async def get_answer(question, conf=[]):
	conf.append({"role": "user", "content": question})
	response = await openai.ChatCompletion.acreate(model='gpt-3.5-turbo', messages=conf, max_tokens=2048, temperature=0.7)
	return response.choices[0].message['content']



#################################################################################################################################
async def on_startup(dp):
	global bot_info
	bot_info=await bot.get_me()

	async def set_default_commands(dp):
		await dp.bot.set_my_commands([types.BotCommand("start", "Запустить бота"),types.BotCommand("deletecontext", "Удалить контекст диалога")])
	await set_default_commands(dp)

if __name__ == '__main__':
	try: executor.start_polling(dp, on_startup=on_startup)
	except Exception as error:
		print(error)
		logging.critical('Неверный токен бота! | Wrond Telegram bot token!')