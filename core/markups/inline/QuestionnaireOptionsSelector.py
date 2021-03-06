from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.emoji import emojize


class QuestionnaireOptionsSelector:
    @staticmethod
    def markup(action=None):
        _markup = InlineKeyboardMarkup(row_width=1)
        if action == 'report':
            _markup.add(
                InlineKeyboardButton(text=emojize('К предыдущей :arrow_left:'),
                                     callback_data='previous'),
                InlineKeyboardButton(text=emojize('Пожаловаться :warning:'),
                                     callback_data='_')
            )
        elif action == 'previous':
            _markup.add(
                InlineKeyboardButton(text=' ',
                                     callback_data='_'),
                InlineKeyboardButton(text=emojize('Пожаловаться :warning:'),
                                     callback_data='report')
            )
        else:
            _markup.add(
                InlineKeyboardButton(text=emojize('К предыдущей :arrow_left:'),
                                     callback_data='previous'),
                InlineKeyboardButton(text=emojize('Пожаловаться :warning:'),
                                     callback_data='report')
            )
        return _markup
