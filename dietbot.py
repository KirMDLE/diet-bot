import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import re


logging.basicConfig(level=logging.INFO)


dp = Dispatcher(bot, storage=MemoryStorage())

class RecipeSearch(StatesGroup):
    waiting_for_ingredient = State()

class DiaryEntry(StatesGroup):
    waiting_for_food = State()

PRODUCTS = {
    "apple": {"XE_per_100g": 1.0, "P": 0.3, "F": 0.2, "C": 18},
    "banana": {"XE_per_100g": 1.3, "P": 1.1, "F": 0.3, "C": 22},
    "egg": {"XE_per_100g": 0, "P": 13, "F": 11, "C": 1},
    "chicken": {"XE_per_100g": 0, "P": 27, "F": 3, "C": 0},
}

RECIPES = {
    "egg": [
        {
            "title": "Omelet with vegetables",
            "calories": 210,
            "P": 12,
            "F": 14,
            "C": 6,
            "XE": 0.5,
            "ingredients": "eggs, broccoli, tomatoes, butter",
            "instructions": "Beat the eggs and fry with vegetables."
        },
        {
            "title": "Fried eggs with tomatoes",
            "calories": 190,
            "P": 11,
            "F": 13,
            "C": 4,
            "XE": 0.4,
            "ingredients": "eggs, tomatoes, oil",
            "instructions": "Fry eggs with tomatoes in a pan."
        }
    ],
    "apple": [
        {
            "title": "Fruit salad with apple",
            "calories": 150,
            "P": 1,
            "F": 0,
            "C": 35,
            "XE": 1.9,
            "ingredients": "apple, kiwi, orange",
            "instructions": "Chop the fruits and mix."
        }
    ]
}

def calculate_xe(product_name: str, grams: float):
    product = PRODUCTS.get(product_name.lower())
    if not product:
        return None
    xe = product["XE_per_100g"] * grams / 100
    p = product["P"] * grams / 100
    f = product["F"] * grams / 100
    c = product["C"] * grams / 100
    return {"XE": round(xe, 2), "P": round(p, 2), "F": round(f, 2), "C": round(c, 2)}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔍 Find Recipe"))
    kb.add(KeyboardButton("📦 Product XE"))
    kb.add(KeyboardButton("📓 Food Diary"))
    await message.answer("Welcome to DiabeticaBot!\nPlease choose an action:", reply_markup=kb)

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    help_text = (
        "🤖 *DiabeticaBot — your diabetes assistant*\n\n"
        "*🍽️ 1. Find a Recipe by Ingredient*\n"
        "Type an ingredient, e.g. `apple`, `egg`, `chicken`.\n"
        "Get recipe suggestions with XE, protein, fat, carbs, and instructions.\n\n"
        "*⚖️ 2. Product XE & Nutrients*\n"
        "Type: `product, grams` (e.g. `banana, 120`)\n"
        "Get XE, protein, fat, and carbs per portion.\n\n"
        "*📓 3. Food Diary*\n"
        "Use diary menu:\n"
        "➕ Add Entry — add food\n"
        "📋 Show Diary — view all entries\n"
        "🗑 Clear Diary — clear your list\n\n"
        "You can also use the buttons or type commands manually."
    )
    await message.answer(help_text, parse_mode='Markdown')

@dp.message_handler(lambda message: message.text == "🔍 Find Recipe")
async def ask_ingredient(message: types.Message):
    await message.answer("Enter the main ingredient:", reply_markup=ReplyKeyboardRemove())
    await RecipeSearch.waiting_for_ingredient.set()

@dp.message_handler(state=RecipeSearch.waiting_for_ingredient)
async def find_recipe(message: types.Message, state: FSMContext):
    ingredient = message.text.lower()
    found = False
    responses = []
    for key, recipes in RECIPES.items():
        if ingredient in key:
            found = True
            for r in recipes:
                res = (
                    f"🥗 *{r['title']}*\n"
                    f"Calories: {r['calories']} kcal | P: {r['P']}g, F: {r['F']}g, C: {r['C']}g | XE: {r['XE']}\n"
                    f"Ingredients: {r['ingredients']}\n"
                    f"Instructions: {r['instructions']}\n"
                    "---------------------------"
                )
                responses.append(res)
    if not found:
        await message.answer(f"Sorry, no recipes found with '{ingredient}'.")
    else:
        await message.answer("\n".join(responses), parse_mode='Markdown')
    await state.finish()
    await send_welcome(message)

@dp.message_handler(lambda message: message.text == "📦 Product XE")
async def ask_product(message: types.Message):
    await message.answer("Enter product and weight in grams, e.g.:\napple, 150", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(lambda message: re.match(r"^[a-zA-Z\s]+,\s*\d+(\.\d+)?$", message.text))
async def calculate_xe_handler(message: types.Message):
    try:
        product_name, grams_str = map(str.strip, message.text.split(","))
        grams = float(grams_str)
        if grams <= 0:
            await message.answer("Weight must be a positive number.")
            return
        result = calculate_xe(product_name, grams)
        if not result:
            await message.answer("I don't know this product yet.")
            return
        await message.answer(
            f"Product: {product_name.capitalize()} {grams}g\n"
            f"XE: {result['XE']} | P: {result['P']}g, F: {result['F']}g, C: {result['C']}g"
        )
    except Exception:
        await message.answer("Please enter data in format: product, grams (e.g. apple, 150)")

user_diaries = {}

@dp.message_handler(lambda message: message.text == "📓 Food Diary")
async def diary_menu(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("➕ Add Entry"))
    kb.add(KeyboardButton("📋 Show Diary"))
    kb.add(KeyboardButton("🗑 Clear Diary"))
    kb.add(KeyboardButton("⬅ Back"))
    await message.answer("Choose an action:", reply_markup=kb)

@dp.message_handler(lambda message: message.text == "➕ Add Entry")
async def diary_add_start(message: types.Message):
    await message.answer("Enter product and grams, e.g.:\nbanana, 120", reply_markup=ReplyKeyboardRemove())
    await DiaryEntry.waiting_for_food.set()

@dp.message_handler(state=DiaryEntry.waiting_for_food)
async def diary_add(message: types.Message, state: FSMContext):
    try:
        product_name, grams_str = map(str.strip, message.text.split(","))
        grams = float(grams_str)
        if grams <= 0:
            await message.answer("Weight must be a positive number.")
            return
        result = calculate_xe(product_name, grams)
        if not result:
            await message.answer("Unknown product.")
            return
        user_id = message.from_user.id
        diary = user_diaries.setdefault(user_id, [])
        diary.append({"product": product_name, "grams": grams, **result})
        await message.answer(
            f"Added: {product_name.capitalize()} {grams}g\n"
            f"XE: {result['XE']} | P: {result['P']}g, F: {result['F']}g, C: {result['C']}g",
            reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
                KeyboardButton("➕ Add Entry"),
                KeyboardButton("📋 Show Diary"),
                KeyboardButton("🗑 Clear Diary"),
                KeyboardButton("⬅ Back"),
            )
        )
        await state.finish()
    except Exception:
        await message.answer("Error. Use format: product, grams (e.g. banana, 120)")

@dp.message_handler(lambda message: message.text == "📋 Show Diary")
async def show_diary(message: types.Message):
    user_id = message.from_user.id
    diary = user_diaries.get(user_id, [])
    if not diary:
        await message.answer("Your diary is empty.")
        return
    text = "Your food diary:\n\n"
    total_xe = total_p = total_f = total_c = 0
    for i, entry in enumerate(diary, 1):
        text += (f"{i}. {entry['product'].capitalize()} {entry['grams']}g - XE: {entry['XE']}, P: {entry['P']}g, F: {entry['F']}g, C: {entry['C']}g\n")
        total_xe += entry['XE']
        total_p += entry['P']
        total_f += entry['F']
        total_c += entry['C']
    text += f"\nTotal: XE: {round(total_xe,2)}, P: {round(total_p,2)}g, F: {round(total_f,2)}g, C: {round(total_c,2)}g"
    await message.answer(text)

@dp.message_handler(lambda message: message.text == "🗑 Clear Diary")
async def clear_diary(message: types.Message):
    user_id = message.from_user.id
    user_diaries[user_id] = []
    await message.answer("Diary cleared.")

@dp.message_handler(lambda message: message.text == "⬅ Back")
async def go_back(message: types.Message):
    await send_welcome(message)

@dp.message_handler()
async def fallback(message: types.Message):
    await message.answer("Please use the menu or write a valid request.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
