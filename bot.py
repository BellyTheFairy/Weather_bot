#бот
#логгирование действий 
#Обработка написания сообщений пользователем по принципу: Пользователь пишет: «привет, как дела?»   –    Бот отвечает: «Вы написали «привет, как дела?», я не знаю такой команды»;
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import csv
from datetime import datetime  #get date and time

load_dotenv()  

bot_token = os.getenv("BOT_TOKEN")
weather_api = os.getenv("WEATHER_API")
currency_api = os.getenv("CURRENCY_API")
news_api = os.getenv("NEWS_API")

bot = Bot(token = bot_token)
dp = Dispatcher()

log_file = "user_actions.csv"

BOT_PICTURE_PATH = os.path.join(os.path.dirname(__file__), "bot_picture.jpg")

class UserState(StatesGroup):
    #ожидание ввода города пользователем 
    waiting_for_city = State()

def init_log_file():
    log_path = os.path.dirname(log_file)

    if log_path and not os.path.exists(log_path):
        os.makedirs(log_path)

    if not os.path.exists(log_file):
        with open(log_file, "w", newline = "", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["Uniс_ID", "@TG_nick", "Motion", "API", "Date", "Time", "API_answer"])
        print(f"Файл создан: {os.path.abspath(log_file)}")
    else:
        print(f"Файл уже существует: {os.path.abspath(log_file)}")

def log_action(user: types.User, motion: str, api: str, api_answer: str):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    
    tg_nick = f"@{user.username}" if user.username else user.first_name
    
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            user.id,
            tg_nick,
            motion,
            api,
            date,
            time,
            api_answer
        ])

def get_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🌤️ Какая сегодня погода", callback_data="action_weather")],
                [InlineKeyboardButton(text="📍 Куда сходить", callback_data="action_places")],
                [InlineKeyboardButton(text="👕 Как сегодня одеться", callback_data="action_outfit")],
                [InlineKeyboardButton(text="👕 Курс валют", callback_data="currency")],
                [InlineKeyboardButton(text="📰 Новости дня", callback_data="news")]
            ])
        
async def get_weather(city: str):
    url = "http://api.openweathermap.org/data/2.5/weather"
    parameters = {
        "q": city,
        "appid": weather_api,
        "units": "metric",
        "lang": "ru"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=parameters, timeout=5) as response:
                if response.status != 200:
                    print(f"OpenWeatherMap вернул {response.status} для '{city}'")
                    return None
                data = await response.json()

        return {
            "temp": data["main"]["temp"],
            "wind": data["wind"].get("speed", 0),
            "desc": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
        }
    except Exception as e:
        print(f"get_weather error: {e}")
        return None

def get_advice(temp: float, wind: float, descr: str):
    advice = []
    if temp <= -10:
        advice.append("❄️ Очень холодно! Пуховик, шапка, шарф и варежки обязательны.")
    elif -10 < temp <= 0:
        advice.append("🌨️ На улице холодно! Лучше надеть зимнюю куртку и шапку.")
    elif 0 < temp <= 10:
        advice.append("🌫️ На улице прохладно! Лучше надеть куртку или пальто, можно добавить шарф.")
    elif 10 < temp <= 20:
        advice.append("⛅ На улице прохладно! Легкая куртка или толстовка - и ты будешь в тепле!")
    else:
        advice.append("☀️ На улице тепло! Можно надеть футболку или легкую рубашку.")

    if "дождь" in descr.lower():
        advice.append("☔ Возможен дождь! Не забудьте зонт или дождевик!")
    if "снег" in descr.lower():
        advice.append("🌧️ Возможен снегопад! Одевайтесь тепло!")
    if wind > 10:
        advice.append("💨 Ветер сильный, одевайтесь тепло.")
        
    return " ".join(advice)
         
@dp.message(Command("start"))
async def start_message(message: types.Message):
    bot_photo = FSInputFile(BOT_PICTURE_PATH)
    user_name = message.from_user.first_name or "Пользователь"
    #здесь была локальная переменная кейбоард

    await message.answer_photo(photo = bot_photo)
    await message.answer(f"Привет, {user_name}! Я Weather_bot. Выбери действие:",
                                             reply_markup=get_keyboard())

    log_action(
        user=message.from_user,
        motion="Command /start",
        api="NONE",
        api_answer="NONE"
    )

async def get_currency_rates():

    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    
    async with aiohttp.ClientSession() as session:

        async with session.get(url, timeout=5) as response:

            if response.status != 200:
                return None
            data = await response.json()
    
    return {
        "USD": data["Valute"]["USD"]["Value"],
        "EUR": data["Valute"]["EUR"]["Value"],
        "CNY": data["Valute"]["CNY"]["Value"]
    }

async def get_news():

    url = "https://newsapi.org/v2/everything"

    parameters = {
        "q": "новости",           
        "language": "ru",         
        "sortBy": "publishedAt",  
        "pageSize": 5,            
        "apiKey": news_api
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=parameters, timeout=5) as response:
            if response.status != 200:
                print(f"NewsAPI вернул статус {response.status}")
                return None
            data = await response.json()
    
    return data.get("articles", [])

#обработка нажатий на кнопки
@dp.callback_query(F.data.startswith("action_"))
async def process_action_selection(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    
    await state.update_data(action=action)
    await state.set_state(UserState.waiting_for_city)
    
    action_names = {
        "weather": "погоду",
        "places": "куда сходить",
        "outfit": "как одеться"
    }
    
    await callback.message.answer(f" Отлично! Введите название города:")
    await callback.answer()
    
    log_action(callback.from_user, f"Clicked {action}", "NONE", "Waiting for city")

@dp.callback_query(F.data == "currency")
async def process_currency(callback: CallbackQuery):
    await callback.answer()
    rates = await get_currency_rates()
    
    if not rates:
        await callback.message.answer(
            "Не удалось получить актуальный курс валют. Попробуйте позже.", 
            reply_markup=get_keyboard()
        )
        log_action(callback.from_user, "Get Currency", "CBR API", "Failed to fetch")
        return
        
    text = (
        "💱 Актуальный курс валют ЦБ: \n"
        f"Доллар США (USD): `{rates['USD']:.2f}` ₽\n"
        f"Евро (EUR): `{rates['EUR']:.2f}` ₽\n"
        f"Китайский юань (CNY): `{rates['CNY']:.2f}` ₽\n\n"
    )
    
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=get_keyboard())
    
    api_answer = f"USD: {rates['USD']:.2f}, EUR: {rates['EUR']:.2f}, CNY: {rates['CNY']:.2f}"
    log_action(callback.from_user, "Get Currency", "CBR API", api_answer)

@dp.callback_query(F.data == "news")
async def process_news(callback: CallbackQuery):

    await callback.answer()  
    articles = await get_news()
    
    # Проверка: если новостей нет или API вернул ошибку
    if not articles:
        await callback.message.answer(
            "Не удалось загрузить новости. Попробуйте позже.",
            reply_markup=get_keyboard()
        )
        log_action(callback.from_user, "Get News", "NewsAPI", "Failed")
        return
    
    text = "📰 Топ-5 новостей дня:\n"
    for i, article in enumerate(articles, 1):
        title = article.get("title", "Без заголовка")
        source = article.get("source", {}).get("name", "Неизвестно")
        url = article.get("url", "")
        description = article.get("description", "") or ""
        # Обрезаем описание до 100 символов для читаемости
        short_desc = description[:100] + "..." if len(description) > 100 else description
        
        text += f"*{i}. [{source}]({url})*\n"
        text += f"_{title}_\n"
        if short_desc:
            text += f"{short_desc}\n"
        text += "\n"
    
    await callback.message.answer(
        text, 
        parse_mode="Markdown", 
        disable_web_page_preview=True,
        reply_markup=get_keyboard()
    )
    
    titles = "; ".join([a.get("title", "")[:30] for a in articles])
    log_action(callback.from_user, "Get News", "NewsAPI", f"Articles: {titles}")

@dp.message(UserState.waiting_for_city) 
async def process_city_input(message: types.Message, state: FSMContext):
    city = message.text.strip()

    #действие сохраненное в памяти бота 
    data = await state.get_data()
    action = data.get("action")
    
    await state.clear()
    
    weather_data = await get_weather(city)
    
    if not weather_data:
        await message.answer("Не знаю такой город, попробуйте еще.")
        log_action(message.from_user, f"Failed {action}", "OpenWeatherMap", f"City not found: {city}")
        return

    #Пользователь выбрал узнать погоду
    if action == "weather":
        temp = weather_data["temp"]
        wind = weather_data["wind"]
        desc = weather_data["desc"]
        icon_code = weather_data["icon"]
        image_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        text = f"🌆 {city.title()}\n🌡️ {temp}°C\n☁️ {desc.capitalize()}"
        
        await message.answer_photo(photo=image_url, caption=text, reply_markup=get_keyboard())
        log_action(message.from_user, "Get Weather", "OpenWeatherMap", f"{city}: {temp}C, {desc}")

    #Пользователь выбрал узнать как одеться
    elif action == "outfit":
        temp = weather_data["temp"]
        wind = weather_data["wind"]
        desc = weather_data["desc"]
        advice = get_advice(temp, wind, desc)
        await message.answer(f"Как одеться в г. {city.title()}:\n\n{advice}", reply_markup=get_keyboard())
        log_action(message.from_user, "Get Outfit", "OpenWeatherMap + Rules", f"{city}: {advice[:50]}...")

    #Пользователь выбрал узнать куда сходить
    elif action == "places":
        temp = weather_data["temp"]
        wind = weather_data["wind"]
        desc = weather_data["desc"]
        
        #Рекомендации
        if "дождь" in desc.lower() or "снег" in desc.lower() or temp < 5:
            suggestion = "На улице не очень, рекомендую посетить:\n🏛️ Музеи,\n🎬 Кинотеатры,\n☕ Кофейни."
        else:
            suggestion = "Погода отличная! Самое время посетить:\n🌳 Городские парки,\n☀️Пешеходные набережные,\n🏛️ Летние веранды."
            
        await message.answer(f" Куда сходить в г. {city.title()}:\n\n{suggestion}", reply_markup=get_keyboard())
        log_action(message.from_user, "Get Places", "Rule-based", f"{city}: {suggestion[:50]}...")

@dp.message(F.text)
async def another_message(message: types.Message):
    user_text = message.text
    await message.answer(f"Вы написали {user_text}, я не знаю такой команды.\nНажмите /start чтобы продолжить.")
    log_action(message.from_user, "Unknown command", "NONE", f"text: {user_text}")

async def main():
    init_log_file()
    print("Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
