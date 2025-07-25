
import os
import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN

class UserState(StatesGroup):
    background = State()

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "parsed_ai_plan.json"), encoding="utf-8") as f:
    ai_plan = json.load(f)
with open(os.path.join(DATA_DIR, "parsed_ai_product_plan.json"), encoding="utf-8") as f:
    product_plan = json.load(f)

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Начать подбор магистратуры", callback_data="begin")]
    ])
    await message.answer("🚀 Я помогу вам выбрать между двумя магистратурами: \n\n1. 🤖 Искусственный интеллект\n2. 📦 Продуктовый AI\n\nДля начала нажмите кнопку ниже:", reply_markup=kb)

@dp.callback_query(F.data == "begin")
async def ask_background(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserState.background)
    await callback.message.edit_text(
        "Расскажите о себе:\n\n• Что вы изучали или чем занимались?\n• Какие технологии знаете? Например: Python, SQL, Tableau, Django, TensorFlow и т.д.\n• Есть ли опыт в аналитике, программировании, менеджменте, разработке продуктов и т.п.?"
    )

@dp.message(UserState.background)
async def process_background(message: types.Message, state: FSMContext):
    background_text = message.text.lower()

    ai_keywords = [
        "машин", "ml", "ai", "tensorflow", "pytorch", "data science", "нейрон", "nlp",
        "обучение", "python", "gpu", "cuda", "матем", "алгоритм", "глубокое", "рекоменд", "статист",
        "scikit", "pandas", "нейросеть", "classification", "regression", "кластер", "оптимизац"
    ]
    product_keywords = [
        "sql", "product", "таблиц", "ux", "ui", "бизнес", "tableau", "powerbi", "mvp",
        "аналит", "проект", "jira", "управ", "маркет", "финанс", "hci", "исслед", "прототип", "a/b",
        "amplitude", "mixpanel", "retention", "conversion", "unit economy", "kpi", "figma"
    ]

    score_ai = sum(1 for word in ai_keywords if word in background_text)
    score_product = sum(1 for word in product_keywords if word in background_text)

    if score_ai > score_product:
        direction = "🤖 *Искусственный интеллект*"
        plan = ai_plan
        plan_type = "ai"
    elif score_product > score_ai:
        direction = "📦 *AI-продуктовый*"
        plan = product_plan
        plan_type = "product"
    else:
        await message.answer("⚠️ Не удалось определить подходящее направление. Попробуйте описать подробнее.")
        return

    # Найдём подходящие выборные дисциплины
    elective_matches = []
    for course in plan:
        if course.get("type") == "выборная":
            name = course.get("name", "").lower()
            if any(kw in name for kw in ai_keywords + product_keywords if kw in background_text):
                elective_matches.append(course)

    text = f"🔍 По вашему описанию подходит направление: {direction}\n\n"
    if elective_matches:
        text += "🎯 Вам могут подойти следующие выборные дисциплины:\n"
        for c in elective_matches[:5]:
            text += f"• {c['name']} ({c['credits']} ЗЕТ, семестр {c['semester']})\n"
        text += "\nВы также можете изучить все дисциплины по семестрам."
    else:
        text += "Вы можете изучить дисциплины по семестрам."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Посмотреть дисциплины по семестрам", callback_data=f"show_semesters_{plan_type}")],
        [InlineKeyboardButton(text="🔁 Вернуться к выбору направления", callback_data="begin")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)
    await state.clear()
    await state.update_data(chosen_plan=plan_type)

@dp.callback_query(F.data.startswith("show_semesters_"))
async def semester_selection(callback: types.CallbackQuery, state: FSMContext):
    plan_type = callback.data.split("_")[-1]
    await state.update_data(chosen_plan=plan_type)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📚 Семестр {i}", callback_data=f"sem_{i}")] for i in range(1, 5)
    ] + [[InlineKeyboardButton(text="🔁 Назад к выбору направления", callback_data="begin")]])
    await callback.message.edit_text("Выберите семестр, чтобы посмотреть дисциплины:", reply_markup=kb)

@dp.callback_query(F.data.startswith("sem_"))
async def show_courses(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    plan_type = user_data.get("chosen_plan", "ai")
    plan = ai_plan if plan_type == "ai" else product_plan
    sem = int(callback.data.split("_")[1])

    obligatory = [c for c in plan if int(c["semester"]) == sem and c["type"] == "обязательная"]
    elective = [c for c in plan if int(c["semester"]) == sem and c["type"] == "выборная"]

    text = f"📖 Дисциплины за {sem} семестр:\n\n"
    if obligatory:
        text += "🔹 *Обязательные:*\n" + "\n".join(f"• {c['name']} ({c['credits']} ЗЕТ)" for c in obligatory) + "\n"
    if elective:
        text += "\n🔸 *Выборные:*\n" + "\n".join(f"• {c['name']} ({c['credits']} ЗЕТ)" for c in elective)
    if not obligatory and not elective:
        text += "Нет данных по дисциплинам."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к семестрам", callback_data=f"show_semesters_{plan_type}")],
        [InlineKeyboardButton(text="🔁 Вернуться к выбору направления", callback_data="begin")]
    ])
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
