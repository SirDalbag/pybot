import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


class Database:
    @staticmethod
    def query(sql: str, args: tuple, many: bool = True) -> list[tuple] or tuple:
        try:
            with sqlite3.connect("database.db") as connection:
                cursor = connection.cursor()
                cursor.execute(sql, args)
                if many:
                    return cursor.fetchall()
                return cursor.fetchone()
        except Exception as error:
            print(error)

    @staticmethod
    def select(id: int = None) -> list[tuple] or tuple:
        query = "SELECT id, name, date, cost FROM tickets"
        if not id:
            return Database.query(sql=query, args=())
        return Database.query(
            sql=f"{query} WHERE id =?",
            args=(id,),
            many=False,
        )

    @staticmethod
    def insert(name: str, date: str, cost: float) -> list[tuple]:
        return Database.query(
            sql="INSERT INTO tickets (name, date, cost) VALUES (?,?,?)",
            args=(name, date, cost),
        )


PROXY_URL = "http://proxy.server:3128"
bot = Bot(token="6397148691:AAG0QzG6dpDhGpoqETpkiwpQs2r4cWANL8w", proxy=PROXY_URL)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Ticket(StatesGroup):
    name = State()
    date = State()
    cost = State()


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    select = InlineKeyboardButton("Все билеты", callback_data="select")
    create = InlineKeyboardButton("Новый билет", callback_data="create")
    keyboard = InlineKeyboardMarkup().add(select, create)

    await message.reply("Привет!", reply_markup=keyboard)


@dp.callback_query_handler(
    lambda callback: callback.data in ["select", "create", "buy", "back"]
)
async def process_callback_button(callback_query: types.CallbackQuery):
    back = InlineKeyboardButton("Назад", callback_data="back")

    if callback_query.data == "select":
        rows = Database.select()
        buttons = []
        for row in rows:
            button = InlineKeyboardButton(row[1], callback_data=str(row[0]))
            buttons.append(button)
        keyboard = InlineKeyboardMarkup()
        keyboard.add(*buttons, back)
        await bot.send_message(
            callback_query.from_user.id, "Вот все билеты!", reply_markup=keyboard
        )

    elif callback_query.data == "create":
        await Ticket.name.set()
        await bot.send_message(
            callback_query.from_user.id,
            "Хорошо! Введите название рейса (От куда - куда):",
        )

    elif callback_query.data == "buy":
        await bot.send_message(callback_query.from_user.id, "Хорошего отдыха!")

    elif callback_query.data == "back":
        await start_command(callback_query.message)

    await callback_query.answer()


@dp.message_handler(state=Ticket.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["name"] = message.text

    await Ticket.date.set()
    await message.reply("Введите дату билета (День-Месяц-Год Время):")


@dp.message_handler(state=Ticket.date)
async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["date"] = message.text

    await Ticket.cost.set()
    await message.reply("Введите цену билета:")


@dp.message_handler(state=Ticket.cost)
async def process_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["cost"] = message.text

    try:
        Database.insert(name=data["name"], date=data["date"], cost=float(data["cost"]))
        await message.reply("Билет успешно добавлен!")
    except Exception as error:
        await message.reply("Билет не был добавлен!")

    await state.finish()


@dp.callback_query_handler()
async def handle_callback_button(callback_query: types.CallbackQuery):
    row = Database.select(int(callback_query.data))

    buy = InlineKeyboardButton("Купить", callback_data="buy")
    back = InlineKeyboardButton("Назад", callback_data="back")
    keyboard = InlineKeyboardMarkup().add(buy, back)

    if row:
        await bot.send_message(
            callback_query.from_user.id,
            f"Билет: {row[1]}\nДата: {row[2]}\nСтоимость: {row[3]}",
            reply_markup=keyboard,
        )
    else:
        await bot.send_message(
            callback_query.from_user.id, "Билет не найден!", reply_markup=keyboard
        )

    await callback_query.answer()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
