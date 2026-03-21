import telebot
import sqlite3

from config import *
bot = telebot.TeleBot(TOKEN)
proxy_url = f"{proxyType}://{proxyIP}:{proxyPort}"
telebot.apihelper.proxy = {'http': proxy_url, 'https': proxy_url}

conn = sqlite3.connect('accs.db',check_same_thread=False)
cursor = conn.cursor()

COMMANDS = [
    {"cmd": "start",
     "desc": "Запустить бота",
     "func": "start_func"},

    {"cmd": "check",
     "desc": "Просмотреть статус аккаунта",
     "func": "check_user"},

    {"cmd": "check_all",
     "desc": "Просмотреть статус всех аккаунтов",
     "func": "check_all"},

    {"cmd": "farm",
     "desc": "Отметить аккаунт отфармленным",
     "func": "farm_account"},

    {"cmd": "wednesday",
     "desc": "Отметить все аккаунты неотфармленными",
     "func": "clear_all"},

    {"cmd": "ban",
     "desc": "Отметить аккаунт забаненным",
     "func": "ban_account"},

    {"cmd": "add",
     "desc": "Добавить аккаунт в базу",
     "func": "add_account"},

    {"cmd": "edit",
     "desc": "Отметить аккаунт забаненным",
     "func": "edit_account"},

    {"cmd": "remove",
     "desc": "Отметить аккаунт забаненным",
     "func": "delete_account"},
]


tftoyesno={
    True: "да",
    False: "нет",
    0:"нет",
    1:"да"
}

cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        number INTEGER,
        name TEXT,
        farmed BOOLEAN,
        banned BOOLEAN,
        banned_until DATETIME
    )
''')

def is_user(user_id):
    if user_id in USERS:
        return True
    else:
        bot.send_message(user_id, "К сожалению, у вас нет доступа к этому боту.")
        return False


def reset_all_users():
    # Устанавливаем false во всей колонке is_done
    cursor.execute("UPDATE todo SET is_farmed = 0")

    conn.commit()
    print("Статус всех задач сброшен на False")

def newaccount(number, name):
    cursor.execute("INSERT INTO accounts (number, name, farmed, banned, banned_until) VALUES (?, ?, ?, ?, ?)", (number, name, 0,0,0))
    conn.commit()


def start_func(message):
    if not(is_user(message.from_user.id)):
        return
    bot.send_message(message.chat.id,"Бот работает")


def check_all(message):
    cursor.execute("SELECT name, farmed FROM accounts")
    rows = cursor.fetchall()

    if not rows:
        bot.reply_to(message, "Нет аккаунтов")
        return

    # 1. Собираем все строки в один список с красивым оформлением
    text_list = []
    for name, status in rows:
        icon = "✅" if status else "❌"
        text_list.append(f"{icon} {name}")

    # 2. Объединяем список в одну строку через перенос строки (\n)
    final_text = "📋 **Аккаунты:**\n\n" + "\n".join(text_list)
    bot.reply_to(message,final_text,parse_mode="Markdown")

def check_user(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    result = cursor.execute("SELECT * FROM accounts WHERE number = ?", (number,)).fetchone()
    print(result)
    name = str(result[1])
    farmed = tftoyesno[result[2]]
    banned = tftoyesno[result[3]]
    banned_until = result[4]
    bot.reply_to(message,f"\
Аккаунт {number}\n\
Имя: {name}\n\
Отфармлен: {farmed}\n\
Забанен: {banned}\n\
Забанен до: {banned_until}")

def add_account(message):
    if not(is_user(message.from_user.id)):
        return
    input = message.text.split()
    print(input)
    if len(input) <2:
        bot.reply_to(message,"Неполные аргументы.")
        return
    else:
        number = input[1]
        name = " ".join(input[2:])
        newaccount(int(number), str(name))
        bot.reply_to(message,f"Добавлен аккаунт номер {number} с ником {name}")

def farm_account(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    cursor.execute("""
            UPDATE accounts 
            SET farmed = ? 
            WHERE number = ?
        """, (1, number))
    conn.commit()
    bot.reply_to(message,f"Аккаунт с номером {number} отмечен как отфармленный.")

def clear_all(message):
    if not(is_user(message.from_user.id)):
        return
    cursor.execute("UPDATE accounts SET farmed = 0")
    conn.commit()
    bot.reply_to(message,"Все аккаунты отмечены как неотфармленные.")

def ban_account(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    date = str(args[2])
    cursor.execute("""
            UPDATE accounts 
            SET banned = 1, banned_until = ? 
            WHERE number = ?
        """, (date, number))
    conn.commit()
    bot.reply_to(message,f"Аккаунт с номером {number} отмечен как забаненный до {date}.")

def edit_account(message):
    if not(is_user(message.from_user.id)):
        return

def delete_account(message):
    if not(is_user(message.from_user.id)):
        return

bot.set_my_commands([telebot.types.BotCommand(c["cmd"], c["desc"]) for c in COMMANDS])
for cmd in COMMANDS: # for every command in vocabulary COMMANDS, do:
    func = globals()[cmd["func"]] # find the function in "func" that corresponds to "cmd" in vocabulary
    bot.message_handler(commands=[cmd["cmd"]])(func) # create a handler for the found command and bind it to its found function
bot.infinity_polling()
