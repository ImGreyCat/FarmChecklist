import threading
import telebot
import sqlite3
from time import sleep

from config import *
bot = telebot.TeleBot(TOKEN)
proxy_url = f"{proxyType}://{proxyIP}:{proxyPort}"
telebot.apihelper.proxy = {'http': proxy_url, 'https': proxy_url}

conn = sqlite3.connect('accs.db',check_same_thread=False)
cursor = conn.cursor()

authenticated = {}
authDurationSec = authDuration*60

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

    {"cmd": "unfarm",
     "desc": "Отметить аккаунт неотфармленным",
     "func": "farm_account"},

    {"cmd": "wednesday",
     "desc": "Отметить все аккаунты неотфармленными",
     "func": "clear_all"},

    {"cmd": "ban",
     "desc": "Отметить аккаунт забаненным",
     "func": "ban_account"},

    {"cmd": "unban",
     "desc": "Отметить аккаунт забаненным",
     "func": "unban_account"},

    {"cmd": "add",
     "desc": "Добавить аккаунт в базу",
     "func": "add_account"},

    {"cmd": "edit",
     "desc": "Изменить информацию об аккаунте",
     "func": "edit_account"},

    {"cmd": "remove",
     "desc": "Удалить аккаунт из базы",
     "func": "delete_account"},

    {"cmd": "auth",
     "desc": "Использовать пароль для доступа к админ-командам",
     "func": "authenticate"},
]


tftoyesno={
    True: "да",
    False: "нет",
    0:"нет",
    1:"да"
}

cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        number INTEGER UNIQUE,
        name TEXT,
        profile TEXT,
        FRIEND TEXT,
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


def reset_all_users(message):
    # Устанавливаем false во всей колонке is_done
    cursor.execute("UPDATE todo SET is_farmed = 0")

    conn.commit()
    bot.reply_to(message,"Все аккаунты отмечены как неотфармленные.")

def newaccount(number, name):
    try:
        cursor.execute("INSERT INTO accounts (number, name, farmed, banned, banned_until) VALUES (?, ?, ?, ?, ?)", (number, name, 0,0,0))
    except sqlite3.IntegrityError:
        return False
    else:
        conn.commit()
        return True



def start_func(message):
    if not(is_user(message.from_user.id)):
        return
    bot.send_message(message.chat.id,"Бот работает")


def check_all(message):
    cursor.execute("SELECT name, farmed, banned FROM accounts ORDER BY number ASC")
    rows = cursor.fetchall()

    if not rows:
        bot.reply_to(message, "Нет аккаунтов")
        return

    # 1. Собираем все строки в один список с красивым оформлением
    text_list = []
    for name, status, banned in rows:
        icon = "✅" if status else "❌"
        icon2 = "✅" if banned else "❌"
        text_list.append(f"{icon} {icon2} | {name}")

    # 2. Объединяем список в одну строку через перенос строки (\n)
    final_text = f"📋 *{len(text_list)} аккаунтов:*\n\n" + "\n".join(text_list) + "\n\n{1} {2} | Ник\n1 - Отфармлен\n2 - Забанен"
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
    if result[4]==0:
        banned_until="не забанен"
    else:
        banned_until = result[4]
    bot.reply_to(message,f"\
Аккаунт *№{number}*\n\
Имя: *{name}*\n\
Отфармлен: *{farmed}*\n\
Забанен: *{banned}*\n\
Забанен до: *{banned_until}*",parse_mode="Markdown")

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
        result = newaccount(int(number), str(name))
        if result == False:
            bot.reply_to(message,f"Не удалось добавить: номер {number} уже занят.")
            return
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

def unfarm_account(message):
    if not (is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    cursor.execute("""
            UPDATE accounts 
            SET farmed = ? 
            WHERE number = ?
        """, (0, number))
    conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} отмечен как неотфармленный.")

def clear_all(message): # добавить пароль рома жирный
    if not(is_user(message.from_user.id)):
        return

    if not authenticated[message.from_user.id]:
        bot.reply_to(message,"Вы не аутентифицированы.\nЧтобы запустить эту команду, используйте пароль: /auth <пароль>")
        return

    cursor.execute("UPDATE accounts SET farmed = 0")
    conn.commit()
    bot.reply_to(message,"Все аккаунты отмечены как неотфармленные.")

def ban_account(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,"Вы предоставили недостаточно аргументов.\nСинтаксис: /ban <ID> <дата разбана ДД.ММ>")
        return
    number = args[1]
    date = str(args[2])
    cursor.execute("""
            UPDATE accounts 
            SET banned = 1, banned_until = ? 
            WHERE number = ?
        """, (date, number))
    conn.commit()
    bot.reply_to(message,f"Аккаунт с номером {number} отмечен как забаненный до {date}.")

def unban_account(message):
    if not (is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    cursor.execute("""
            UPDATE accounts 
            SET banned = 0, banned_until = ? 
            WHERE number = ?
        """, (0, number))
    conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} отмечен как незабаненный.")

def edit_account(message):
    if not(is_user(message.from_user.id)):
        return

def delete_account(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    print(number)
    if not authenticated[message.from_user.id]:
        bot.reply_to(message,"Вы не аутентифицированы.\nЧтобы запустить эту команду, используйте пароль: /auth <пароль>")
        return
    cursor.execute("""
                DELETE FROM accounts WHERE number = ?
            """, (number,))
    conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} удалён из базы.")

def auth_timer(user_id):
    sleep(authDurationSec)
    authenticated[user_id] = False

def authenticate(message):
    if not(is_user(message.from_user.id)):
        return
    if authenticated[message.from_user.id]:
        bot.reply_to(message,"Вы уже аутентифицированы.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,"Вы не указали пароль.\nСинтаксис: /auth <пароль>")
        return
    if " ".join(args[1:]) != authPassword:
        bot.reply_to(message,"Вы ввели неверный пароль.")
        return
    user_id = message.from_user.id
    authenticated[user_id] = True
    threading.Thread(target=auth_timer, args=(user_id,), daemon=True).start()
    bot.reply_to(message,f"Вы успешно аутентифицированы на *{authDuration} минут*.",parse_mode="Markdown")

@bot.message_handler(commands=["checkauth"])
def check_auth(message):
    bot.reply_to(message,str(authenticated[message.from_user.id]))

@bot.message_handler(commands=['migrate'])
def migrate(message):
    if not(is_user(message.from_user.id)):
        return
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_number on accounts (number)")
    conn.commit()

bot.set_my_commands([telebot.types.BotCommand(c["cmd"], c["desc"]) for c in COMMANDS])
for cmd in COMMANDS: # for every command in vocabulary COMMANDS, do:
    func = globals()[cmd["func"]] # find the function in "func" that corresponds to "cmd" in vocabulary
    bot.message_handler(commands=[cmd["cmd"]])(func) # create a handler for the found command and bind it to its found function

for uid in USERS:
    authenticated[uid] = False
bot.infinity_polling()
