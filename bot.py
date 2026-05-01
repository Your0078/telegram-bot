import asyncio
import random
import httpx
import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = "7659324518:AAEHla0oXNEMnN6elU_GD2KxTA-DhSlCIK0"
OWNER_ID = 1780122133
OPENROUTER_API_KEY = "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"

MEMORY_FILE = "memory.json"

if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        user_memory = json.load(f)
else:
    user_memory = {}

def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_memory, f, ensure_ascii=False, indent=2)

ranks = {OWNER_ID: "مالك"}

def get_rank(user_id: int):
    return ranks.get(user_id, "عضو")

jokes = [
    "مرة واحد غبي راح للدكتور... قاله شيل الملعقة من الكوب!",
    "فيه واحد اشترى مراية قال دي مستعملة!",
    "مرة واحد نام متأخر، حلم متأخر!",
    "ليه الكمبيوتر ما يلعبش كورة؟ عشان الفيروسات!"
]

games = {}

def display_board(board):
    return "\n".join([
        f"{board[0]} | {board[1]} | {board[2]}",
        "---------",
        f"{board[3]} | {board[4]} | {board[5]}",
        "---------",
        f"{board[6]} | {board[7]} | {board[8]}"
    ])

def check_winner(board, symbol):
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    return any(board[i] == board[j] == board[k] == symbol for i,j,k in wins)

def get_bot_move(board):
    empty = [i for i, val in enumerate(board) if val not in ["X", "O"]]
    return random.choice(empty) if empty else None

async def chatgpt_reply(user_id: int, message: str):
    url = "https://openrouter.ai/api/v1/chat/completions"
    user_id = str(user_id)

    if user_id not in user_memory:
        user_memory[user_id] = [
            {
                "role": "system",
                "content": "اسمك إيفا (Eva)، أنتِ فتاة ذكية وودودة، تتكلمي بالعربية العامية المصرية بطريقة مرحة وخفيفة، وتتصرفي كأنك إنسانة حقيقية وتحبّي تساعدي الناس."
            }
        ]

    user_memory[user_id].append({"role": "user", "content": message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": user_memory[user_id][-15:]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code == 200:
                res = response.json()
                reply = res["choices"][0]["message"]["content"]

                user_memory[user_id].append({"role": "assistant", "content": reply})
                save_memory()
                return reply
            else:
                return "حصل خطأ في الرد."
        except Exception:
            return "مشكلة في الاتصال."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rank = get_rank(update.effective_user.id)
    await update.message.reply_text(f"مرحبًا بك!\nرتبتك: {rank}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start\n/help\n/info\n/joke\n/xo\n\nابدأ\nمساعدة\nمعلومات\nنكتة\nاكس او\nمسح"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("المطور: ليلى")

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(jokes))

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    games[user_id] = {"board": [str(i+1) for i in range(9)], "player": None, "bot": None, "turn": "X"}
    await update.message.reply_text("X ولا O؟")

async def xo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()

    if user_id not in games:
        return

    game = games[user_id]
    board = game["board"]

    if game["player"] is None:
        if text in ["X", "O"]:
            game["player"] = text
            game["bot"] = "O" if text == "X" else "X"
            await update.message.reply_text(display_board(board))
        return

    if not text.isdigit():
        return

    move = int(text) - 1
    if board[move] in ["X", "O"]:
        return

    board[move] = game["player"]

    if check_winner(board, game["player"]):
        await update.message.reply_text("كسبت!")
        del games[user_id]
        return

    bot_move = get_bot_move(board)
    if bot_move is not None:
        board[bot_move] = game["bot"]

    if check_winner(board, game["bot"]):
        await update.message.reply_text("خسرت!")
        del games[user_id]
        return

    await update.message.reply_text(display_board(board))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user
    lowered = text.lower()

    if lowered == "ابدأ":
        await start(update, context)
    elif lowered == "مساعدة":
        await help_command(update, context)
    elif lowered == "معلومات":
        await info_command(update, context)
    elif lowered == "نكتة":
        await joke_command(update, context)
    elif lowered == "اكس او":
        await start_game(update, context)
    elif lowered == "مسح":
        user_memory.pop(str(user.id), None)
        save_memory()
        await update.message.reply_text("تم مسح الذاكرة.")
    else:
        if user.id in games:
            await xo_handler(update, context)
        else:
            reply = await chatgpt_reply(user.id, text)
            await update.message.reply_text(reply)

async def setup():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("joke", joke_command))
    app.add_handler(CommandHandler("xo", start_game))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    return app

loop = asyncio.get_event_loop()
app = loop.run_until_complete(setup())
print("✅ Eva bot is running...")
app.run_polling()
