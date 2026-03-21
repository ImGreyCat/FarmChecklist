import telebot
import sqlite3

from config import *
bot = telebot.TeleBot(TOKEN)
proxy_url = f"{proxyType}://{proxyIP}:{proxyPort}"
telebot.apihelper.proxy = {'http': proxy_url, 'https': proxy_url}

conn = sqlite3.connect('accs.db',check_same_thread=False)
cursor = conn.cursor()

farmed_states={
    True: "отфармлен",
    False: "не отфармлен"
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
        return False


def reset_all_users():
    # Устанавливаем false во всей колонке is_done
    cursor.execute("UPDATE todo SET is_farmed = 0")

    conn.commit()
    print("Статус всех задач сброшен на False")

def newaccount(number, name):
    cursor.execute("INSERT INTO accounts (number, name, farmed, banned, banned_until) VALUES (?, ?, ?, ?, ?)", (number, name, 0,0,0))
    conn.commit()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not(is_user(message.from_user.id)):
        return
    bot.send_message(message.chat.id,"Бот работает")

@bot.message_handler(commands=['checkall'])
def check_all(message):
    cursor.execute("SELECT name, farmed FROM accounts")
    rows = cursor.fetchall()
    conn.close()

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

@bot.message_handler(commands=['check'])
def check_user(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    number = args[1]
    result = cursor.execute("SELECT * FROM accounts WHERE number = ?", (number,)).fetchall()
    status = farmed_states[bool(result[0])]
    bot.reply_to(message,f"Статус аккаунта {number}: {status}")

@bot.message_handler(commands=['add'])
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

@bot.message_handler(commands=['farm'])
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
    bot.reply_to(message,f"Аккаунт с номером {number} отмечен как отфармленный.")

@bot.message_handler(commands=['wednesday'])
def clear_all(message):
    if not(is_user(message.from_user.id)):
        return
    cursor.execute("UPDATE accounts SET farmed = 0")
    bot.reply_to(message,"Все аккаунты отмечены как неотфармленные.")

bot.infinity_polling()
