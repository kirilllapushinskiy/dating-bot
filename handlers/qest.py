from datetime import date

from aiogram import types
from aiogram.types import CallbackQuery, Message
from aiogram.utils.emoji import emojize

from core import Questionnaire
from loader import dp
from markups.inline import LookingForSelector, GenderSelector, SettlementSelector, DateSelector
from markups.text import cancel_keyboard, welcome_keyboard, yesno_keyboard
from states import QState
from toolkit import MessageBox, age_suffix


@dp.message_handler(text='Отмена', state='*')
async def cancel(message: Message):
    text = "Ну вот... всё потеряно... Попробовать ещё раз?"
    _user_id = message.from_user.id
    await MessageBox.delete_last(_user_id)
    await QState.first()
    await message.answer(text=text, reply_markup=yesno_keyboard)


@dp.message_handler(commands=['start'], state='*')
async def welcome(message: Message):
    text = "Добро пожаловать! Ну что начнём?"
    await QState.first()
    await message.answer(text=text, reply_markup=welcome_keyboard)


@dp.message_handler(text=['Начнём', 'Да'], state=QState.start.state)
async def start(message: Message):
    await message.answer("Давай знакомится, как тебя зовут: ", reply_markup=cancel_keyboard)
    await QState.input_name.set()  # Update state.


@dp.message_handler(state=QState.input_name.state)
async def name(message: Message):
    _name = message.text.capitalize()
    if not (20 > len(_name) > 1):
        await message.answer("Длина имени должна быть от 2 до 20 символов.")
        await message.answer("Введите ваше имя:")
    elif not all(char.isalpha() or char == ' ' for char in _name):
        await message.answer("Имя может содержать только буквы.")
        await message.answer("Введите ваше имя:")
    else:
        _user_id = message.from_user.id
        Questionnaire.write(user_id=_user_id, name=_name)
        _message = await message.answer(
            f"Приятно познакомиться, {_name}! Выбери свой пол:",
            reply_markup=GenderSelector.markup()
        )
        MessageBox.put(user_id=message.from_user.id, message=_message)
        await QState.select_gender.set()  # Update state.


@dp.callback_query_handler(state=QState.select_gender.state)
async def gender(callback_query: CallbackQuery):
    _user_id = callback_query.from_user.id
    await MessageBox.delete_last(user_id=_user_id)
    if callback_query.data != 'back':
        Questionnaire.write(user_id=_user_id, gender=callback_query.data)
        _message = await callback_query.message.answer("А кого хочешь найти?", reply_markup=LookingForSelector.markup())
        MessageBox.put(user_id=_user_id, message=_message)
        await QState.select_looking_for.set()  # Update state.
    else:
        _message = await callback_query.message.answer("Как тебя зовут?")
        await QState.previous()  # Update state.


@dp.callback_query_handler(state=QState.select_looking_for.state)
async def looking_for(callback_query: CallbackQuery):
    _user_id = callback_query.from_user.id
    await MessageBox.delete_last(user_id=_user_id)
    if callback_query.data != 'back':
        _looking_for = None if callback_query.data not in ('male', 'female') else callback_query.data
        Questionnaire.write(user_id=_user_id, looking_for=_looking_for)
        await callback_query.message.answer(f"Принято, {Questionnaire.get(_user_id, 'name')}! Напиши откуда ты: ")
        await QState.search_settlement.set()  # Update state.
    else:
        _message = await callback_query.message.answer(
            "Выбери свой пол:",
            reply_markup=GenderSelector.markup()
        )
        MessageBox.put(user_id=_user_id, message=_message)
        await QState.previous()  # Update state.


@dp.message_handler(state=QState.search_settlement.state)
async def search(message):
    await types.ChatActions.typing()
    await QState.select_settlement.set()

    _user_id = message.from_user.id

    settlements = Questionnaire.search_settlements(name=message)

    SettlementSelector.setup(settlements=settlements, user_id=_user_id)

    _text1 = emojize(f":mag_right: <i>Результаты по запросу</i> <b>«{message.text}» </b> ")
    _text2 = emojize(f":mag_right: <i>По запросу</i> <b>«{message.text}»</b> <i>ничего не найдено</i> :( ")

    _message = await message.answer(
        text=_text1 if len(settlements) else _text2,
        reply_markup=SettlementSelector.markup(user_id=_user_id),
        parse_mode="HTML"
    )

    MessageBox.put(message=_message, user_id=_user_id)


@dp.callback_query_handler(
    SettlementSelector.data.filter(action=[SettlementSelector.actions.next, SettlementSelector.actions.prev]),
    state=QState.select_settlement.state
)
async def select_process(callback_query, callback_data):
    _user_id = callback_query.from_user.id
    _message = await callback_query.message.edit_reply_markup(
        reply_markup=SettlementSelector.markup(
            user_id=_user_id, callback_data=callback_data
        )
    )
    MessageBox.put(message=_message, user_id=_user_id)


@dp.callback_query_handler(
    SettlementSelector.data.filter(action=SettlementSelector.actions.back),
    state=QState.select_settlement.state
)
async def back(callback_query):
    _user_id = callback_query.from_user.id
    SettlementSelector.clear(_user_id)
    await MessageBox.delete_last(_user_id)
    await callback_query.message.answer("Напиши из какого ты города:")
    await QState.search_settlement.set()  # Update state.


@dp.callback_query_handler(
    SettlementSelector.data.filter(action=SettlementSelector.actions.select),
    state=QState.select_settlement.state
)
async def done(callback_query, callback_data):
    _user_id = callback_query.from_user.id
    Questionnaire.write(user_id=_user_id, settlement_id=int(callback_data['settlement_id']))
    SettlementSelector.clear(_user_id)
    await MessageBox.delete_last(_user_id)
    DateSelector.setup(user_id=_user_id)
    _message = await callback_query.message.answer(
        "Теперь выбери дату рождения: ",
        reply_markup=DateSelector.markup(_user_id)
    )
    MessageBox.put(message=_message, user_id=_user_id)
    await QState.select_date.set()  # Update state.


@dp.callback_query_handler(
    DateSelector.data.filter(action=[
        DateSelector.actions.next_month, DateSelector.actions.prev_month,
        DateSelector.actions.next_year, DateSelector.actions.next_5_year,
        DateSelector.actions.prev_year, DateSelector.actions.prev_5_year,
        DateSelector.actions.select_day
    ]),
    state=QState.select_date.state
)
async def calendar_selection(callback_query: CallbackQuery, callback_data: dict):
    _user_id = callback_query.from_user.id
    if _user_id in DateSelector.users():
        _message = await callback_query.message.edit_reply_markup(
            DateSelector.markup(
                user_id=_user_id,
                callback_data=callback_data
            )
        )
        MessageBox.put(message=_message, user_id=_user_id)
    else:
        await callback_query.answer()


@dp.callback_query_handler(
    DateSelector.data.filter(action=DateSelector.actions.confirm),
    state=QState.select_date.state
)
async def calendar_selection(callback_query: CallbackQuery, callback_data: dict):
    _user_id = callback_query.from_user.id
    await MessageBox.delete_last(user_id=_user_id)
    DateSelector.clear(user_id=_user_id)
    _date_of_birth = date(
        day=int(callback_data['day']),
        month=int(callback_data['month']),
        year=int(callback_data['year'])
    )
    Questionnaire.write(user_id=_user_id, date_of_birth=_date_of_birth)
    _age, _suffix = age_suffix(_date_of_birth)
    await callback_query.message.answer(f'Отлично тебе {_age} {_suffix}.')
    await callback_query.message.answer(f'Пришли нам свою фотографию:')
    await QState.get_photo.set()  # Update state.


@dp.message_handler(content_types=['photo'], state=QState.get_photo)
async def get_photo(message: Message):
    _user_id = message.from_user.id
    _photo = message.photo[-1].file_id
    Questionnaire.write(user_id=_user_id, photo=_photo)
    await message.answer(f"Отлично смотришься, {Questionnaire.get(_user_id, 'name')}.")
    await message.answer("Показать твою анкету?", reply_markup=yesno_keyboard)
    await QState.finish.set()  # Update state.


@dp.message_handler(text='Да', state=QState.finish.state)
async def finish(message: Message):
    _user_id = message.from_user.id
    _photo = Questionnaire.get(_user_id, 'photo')
    _age, _suffix = age_suffix(Questionnaire.get(_user_id, 'date_of_birth'))
    _name = Questionnaire.get(_user_id, 'name')
    _settlement = Questionnaire.get(_user_id, 'settlement_id')
    await message.answer_photo(
        photo=_photo,
        caption=f"{_name}, {_settlement} - {_age} {_suffix}."
    )