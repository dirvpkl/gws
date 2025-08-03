# я этот код не трогал с предыдущей версии
# возможно хуйня
# мне похуй

import re
import dateparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

emoji_to_digit = {
    '0️⃣': '0',
    '1️⃣': '1',
    '2️⃣': '2',
    '3️⃣': '3',
    '4️⃣': '4',
    '5️⃣': '5',
    '6️⃣': '6',
    '7️⃣': '7',
    '8️⃣': '8',
    '9️⃣': '9'
}

days_map = {
    'понедельник': 0,
    'вторник': 1,
    'среду': 2,
    'четверг': 3,
    'пятницу': 4,
    'субботу': 5,
    'воскресенье': 6
}

date_with_time_regex = r"(\d{1,2}[:.]\d{2},?\s?(\d{1,2}[./-]\d{1,2}[./-]\d{4}))"
date_regex = r"\b(\d{1,2})[а-яА-Я]*?\s?(?:[-.\s])?\s?(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|january|february|march|april|may|june|july|august|september|october|november|december)\b"
short_date_regex = r"(\b\d{1,2}[.-]\d{1,2}\b)"
relative_date_regex = r"(завтра|послезавтра|в (?:эту|следующую|ближайшую)?\s?(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)|на следующей неделе|через неделю|через месяц|через\s?\d+\s?дн[яей]|сутк[иа]|недел|час[аов])"
# for func
pattern = re.compile('|'.join(map(re.escape, emoji_to_digit.keys())))


def _process_post_text(post_text) -> str:
    post_text = pattern.sub(lambda x: emoji_to_digit[x.group(0)], post_text)
    post_text = post_text.lower().replace('\n', ' ').replace('-', '')
    soup = BeautifulSoup(post_text, "lxml")
    post_text = soup.get_text()
    return post_text


def _convert_short_date(short_date_str: datetime, now) -> str:
    return f"{short_date_str}.{now.year}"


# Преобразуем относительные даты в точные
def _convert_relative_date(relative_str, now: datetime) -> str:
    if relative_str == "сегодня":
        return now.strftime("%Y-%m-%d")
    elif relative_str == "завтра":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif relative_str == "послезавтра":
        return (now + timedelta(days=2)).strftime("%Y-%m-%d")
    elif "сутк" in relative_str:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "неделю" in relative_str:
        return (now + timedelta(days=7)).strftime("%Y-%m-%d")
    elif "месяц" in relative_str:
        return (now + timedelta(days=30)).strftime("%Y-%m-%d")
    elif "в" in relative_str:
        day_name = re.findall(r"(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)", relative_str)
        if day_name:
            day_num = days_map[day_name[0]]
            days_ahead = (day_num - now.weekday() + 7) % 7
            if "следующую" in relative_str:
                days_ahead += 7
            elif "ближайшую" in relative_str and days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    elif "через" in relative_str:
        numbers = re.findall(r'\d+', relative_str)
        if numbers:
            num_in_msg = int(numbers[0])
            if "недел" in relative_str:
                return (now + timedelta(days=num_in_msg*7)).strftime("%Y-%m-%d")
            elif "час" in relative_str:
                return (now + timedelta(hours=num_in_msg)).strftime("%Y-%m-%d")
            else:
                return (now + timedelta(days=num_in_msg)).strftime("%Y-%m-%d")


def find_date_obj(text, date_posted: datetime):

    post_text = _process_post_text(text)

    null_obj = None

    if len(post_text.split(' ')) == 1:
        return null_obj

    def efv(matches):
        return [match[0] for match in matches]

    dates_with_time = re.findall(date_with_time_regex, post_text)
    dates = re.findall(date_regex, post_text)
    short_dates = re.findall(short_date_regex, post_text)
    relative_dates = efv(re.findall(relative_date_regex, post_text))

    converted_relative_dates = [_convert_relative_date(rd, date_posted) for rd in relative_dates]
    converted_short_dates = [_convert_short_date(sd, date_posted) for sd in short_dates]

    formats = [
        ("dates_with_time", lambda: [dates_with_time[0][1]] if dates_with_time else None),
        ("dates", lambda: dates if dates else None),
        ("converted_short_dates", lambda: converted_short_dates if converted_short_dates else None),
        ("converted_relative_dates", lambda: converted_relative_dates if converted_relative_dates else None)
    ]

    used_formats = []
    for _ in range(4):
        selected_dates = None

        for fmt_name, getter in formats:
            if fmt_name not in used_formats:
                result = getter()
                if result:
                    selected_dates = result
                    used_formats.append(fmt_name)
                    break

        formatted = None
        if selected_dates:
            for sc in selected_dates:
                if sc is None:
                    continue

                if not isinstance(sc, str):
                    sc = ' '.join(sc)

                formatted = dateparser.parse(sc, languages=["ru", "en"])
                if formatted is not None:
                    break

        return formatted
    else:
        return null_obj
