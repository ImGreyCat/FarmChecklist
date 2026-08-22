from datetime import datetime, timedelta
import threading
from re import sub
import telebot
import sqlite3
from time import sleep

from config import *
try:
    from devSettings import * # for development stuff
except:
    pass

bot = telebot.TeleBot(TOKEN)

if useProxy is True:
    print("Подключение через прокси...")
    if proxyUsername and proxyPassword:
        # Authenticated format: protocol://user:pass@ip:port
        proxy_url = f"{proxyType}://{proxyUsername}:{proxyPassword}@{proxyIP}:{proxyPort}"
    else:
        # Standard format: protocol://ip:port
        proxy_url = f"{proxyType}://{proxyIP}:{proxyPort}"
    telebot.apihelper.proxy = {'http': proxy_url, 'https': proxy_url}
    try:
        me = bot.get_me()
        print(f"Успешное подключение к боту @{me.username} через прокси")
    except Exception as e:
        print(f"Не удалось подключиться через прокси: {e}")
        raise SystemExit
else:
    print("Подключение...")
    try:
        me = bot.get_me()
        print(f"Успешное подключение к боту @{me.username}")
    except Exception as e:
        print(f"Не удалось подключиться: {e}")
        raise SystemExit

if not dbFilename:
    dbFilename = "accs"

print(f"Установка соединения с базой {dbFilename}.db ...")
try:
    conn = sqlite3.connect(str(dbFilename)+".db",check_same_thread=False)
    cursor = conn.cursor()
except Exception as e:
    print(f"Произошла ошибка при установке соединения с базой {dbFilename}.db: {e}")
    raise SystemExit
else:
    print("Подключение успешно!")

authDurationSec = authDuration*60

commit_cmds=[
    {"cmd": "commit",
    "desc": "Сохранить изменения в базе",
    "func": "commit_cmd"},

    {"cmd": "rollback",
     "desc": "Отменить несохранённые изменения",
     "func": "rollback_cmd"}
]

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
     "desc": "Отметить аккаунт разбаненным",
     "func": "unban_account"},

    {"cmd": "check_bans",
     "desc": "Автоматическая проверка банов",
     "func": "trigger_bancheck"},

    {"cmd": "add",
     "desc": "Добавить аккаунт в базу",
     "func": "add_account"},

    {"cmd": "edit",
     "desc": "Изменить информацию об аккаунте",
     "func": "edit_account"},

    {"cmd": "remove",
     "desc": "Удалить аккаунт из базы",
     "func": "delete_account"},

    {"cmd": "autocommit",
     "desc": "Настройка автосохранения",
     "func": "autocommit"},
]

auth_cmd = [{"cmd": "auth",
     "desc": "Использовать пароль для админ-команд",
     "func": "authenticate"}]

fancystuff={
    None: "не указано",
    True: "да",
    False: "нет",
    0:"нет",
    1:"да"
}

def update(action, force=False):
    if (autoCommit or force) != True:
        return
    if action=="commit":
        conn.commit()
    if action=="rollback":
        conn.rollback()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        number INTEGER UNIQUE,
        name TEXT,
        profile TEXT,
        FRIEND TEXT,
        farmed BOOLEAN,
        banned BOOLEAN,
        banned_until DATETIME,
        email TEXT,
        password TEXT
    )
''')

def is_user(user_id):
    if user_id in USERS:
        return True
    else:
        bot.send_message(user_id, "К сожалению, у вас нет доступа к этому боту.")
        return False

def is_authenticated(message):
    if authenticated[message.from_user.id] == True:
        return True
    bot.reply_to(message, "Вы не аутентифицированы.\nЧтобы запустить эту команду, используйте пароль: /auth <пароль>")
    return False

def newaccount(number, name):
    try:
        cursor.execute("INSERT INTO accounts (number, name, profile, FRIEND, farmed, banned, banned_until) VALUES (?, ?, ?, ?, ?, ?, ?)", (number, name, None,None,0,0,None))
    except sqlite3.IntegrityError:
        return False
    else:
        update("commit")
        # conn.commit()
        return True



def start_func(message):
    if not(is_user(message.from_user.id)):
        return
    bot.send_message(message.chat.id,f"Бот активен и вы находитесь в списке пользователей!\nДоступ к админ-командам: {fancystuff[authenticated[message.from_user.id]]}")


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
    s="ов"
    if len(text_list)%10==1:
        s=""
    if len(text_list)%10 in [2,3,4]:
        s="а"
    # 2. Объединяем список в одну строку
    final_text = f"📋 *{len(text_list)} аккаунт{s}:*\n\n" + "\n".join(text_list) + "\n\n{1} {2} | Ник\n1 - Отфармлен\n2 - Забанен"
    bot.reply_to(message,final_text,parse_mode="Markdown")

def check_user(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,"Пожалуйста, укажите номер аккаунта для просмотра информации о нём.\nСинтаксис: /check <номер>.")
    number = args[1]
    result = cursor.execute("SELECT number, name, profile, friend, farmed, banned, banned_until, email, password FROM accounts WHERE number = ?", (number,)).fetchone()
    print(result) # [0] number [1] name [2] profile [3] friend [4] farmed [5] banned [6] banned until [7] email [8] password
    if result is None:
        bot.reply_to(message,f"Аккаунт с номером {number} не был найден в базе.")
        return

    try:
        name = str(result[1])
        link = result[2]
        friend = result[3]
        farmed = fancystuff[result[4]]
        banned = fancystuff[result[5]]
        email = result[7]
        password = result[8]
        if result[6] == 0:
            banned_until = ""
        else:
            date = result[6]
            date_object = datetime.strptime(date, '%Y-%m-%d')
            banned_until = f"\nЗабанен до: *{date_object.day}.{date_object.month:02}*\n"

        profile_info_text = [
            f"Аккаунт *№{number}*\n"
            f"Имя: *{name}*\n"
            f"Ссылка на профиль: *{link}*"
            f"Код друга: *{friend}*"
            f"Отфармлен: *{farmed}*"
            f"Забанен: *{banned}*"
            f"{banned_until}"
            f"Почта: *{email}*"
            f"Пароль: *{password}*"
        ]

        bot.reply_to(message,profile_info_text,parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message,f"Произошла ошибка при отправке красивого сообщения: {e}.\nРезультат: {result}")

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
    update("commit")
    # conn.commit()
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
    update("commit")
    # conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} отмечен как неотфармленный.")

def clear_all(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return

    cursor.execute("UPDATE accounts SET farmed = 0")
    update("commit")
    # conn.commit()
    bot.reply_to(message,"Все аккаунты отмечены как неотфармленные.")

def ban_account(message):
    if not(is_user(message.from_user.id)):
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message,"Вы предоставили недостаточно аргументов.\nСинтаксис: /ban <ID> <количетсво дней бана>")
        return
    number = args[1]
    result = cursor.execute("SELECT banned FROM accounts WHERE number = ?", (number,)).fetchone()
    if 1 in result:
        bot.reply_to(message,f"Ошибка: этот аккаунт уже отмечен забаненным.\nСначала разбаньте его: /unban {number}")
        return
    try:
        days=int(args[2])
        if not 1 <= days <= 1024:
            bot.reply_to(message,"Недопустимый диапозон дней.")
            return
        unban_date_obj = datetime.now() + timedelta(days=days)
        iso_date = unban_date_obj.strftime("%Y-%m-%d")
        cursor.execute("""
                    UPDATE accounts 
                    SET banned = 1, banned_until = ? 
                    WHERE number = ?
                """, (iso_date, number))
        
        update("commit")
        # conn.commit()
    except ValueError:
        bot.reply_to(message,"Пожалуйста, предоставьте действительное количество дней бана.")
    else:
        bot.reply_to(message,f"Аккаунт {number} отмечен забаненным на {days} дней (до {unban_date_obj.strftime('%d.%m')})")

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
    update("commit")
    # conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} отмечен как незабаненный.")

def trigger_bancheck(message):
    id = message.from_user.id
    if not(is_user(id)):
        return
    check_expired_bans(True,id)

def edit_account(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return

    args = message.text.split()
    number = args[1]
    collumn = args[2]
    value = " ".join(args[3:])
    ALLOWED_COLUMNS = ["number", "name", "profile", "FRIEND", "email", "password"]

    if len(args) < 4:
        bot.reply_to(message,"Вы не указали достаточное количество аргументов.\nСинтаксис: /edit <номер аккаунта> <атрибут> <новое значение>\nДопустимые атрибуты: number, name, profile, FRIEND")
    if collumn.lower() in ALLOWED_COLUMNS:
        query = f"UPDATE accounts SET {collumn} = ? WHERE number = ?"
        cursor.execute(query, (value, number))
        update("commit")
        # conn.commit()
        bot.reply_to(message, f"Аккаунт с номером {number} обновлён.\n{collumn} -> {value}")
    else:
        bot.reply_to(message,f"Ошибка: значение атрибута {collumn} нельзя устанавливать.")

def delete_account(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    args = message.text.split()
    number = args[1]
    print(number)

    cursor.execute("DELETE FROM accounts WHERE number = ?", (number,))
    update("commit")
    # conn.commit()
    bot.reply_to(message, f"Аккаунт с номером {number} удалён из базы.")

def auth_timer(user_id):
    sleep(authDurationSec)
    authenticated[user_id] = False

def autocommit(message):
    global autoCommit
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,"Пожалуйста, укажите, включить или выключить автосохранение.\nСинтаксис: /autocommit <on/off>")
        return
    if args[1].lower() not in ["on", "off"]:
        bot.reply_to(message,"Вы ввели недействительное значение.\non - включить автосохранение\noff - выключить автосохранение")
        return

    with open('config.py', 'r', encoding='utf-8') as f:
        content = f.read()

    if args[1].lower() == "on":
        if autoCommit!=True:
            autoCommit = True
            update_cmds()
            new_content = sub(r'(autoCommit\s*=\s*)False', r'\1True', content)
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
        return
    if autoCommit!=False:
        autoCommit = False
        new_content = sub(r'(autoCommit\s*=\s*)True', r'\1False', content)
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
    update_cmds()
    return


def authenticate(message): # if else if else if else if else if else if else if else if else if else
    user_id = message.from_user.id
    if not(is_user(user_id)):
        return
    if enableAuth == False:
        return
    if authenticated[user_id]:
        bot.reply_to(message,"Вы уже аутентифицированы.")
        return
    if not authPassword: # пропускаем пользователя если не установлен пароль
        authenticated[user_id] = True
        threading.Thread(target=auth_timer, args=(user_id,), daemon=True).start()
        bot.reply_to(message, f"Вы успешно аутентифицированы на *{authDuration} минут*.", parse_mode="Markdown")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message,"Вы не указали пароль.\nСинтаксис: /auth <пароль>")
        return
    if " ".join(args[1:]) != authPassword:
        bot.reply_to(message,"Вы ввели неверный пароль.")
        return
    authenticated[user_id] = True
    threading.Thread(target=auth_timer, args=(user_id,), daemon=True).start()
    bot.reply_to(message,f"Вы успешно аутентифицированы на *{authDuration} минут*.",parse_mode="Markdown")

def commit_cmd(message):
    if not(is_user(message.from_user.id)):
        return
    update("commit",True)
def rollback_cmd(message):
    if not(is_user(message.from_user.id)):
        return
    update("rollback",True)

@bot.message_handler(commands=['migrate']) # create unique index for the numbers (to migrate from older versions without the unique index)
def migrate(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    bot.reply_to(message,"Начинаю миграцию таблицы...")

    new_schema = """
        CREATE TABLE IF NOT EXISTS accounts (
            number INTEGER UNIQUE,
            name TEXT,
            profile TEXT,
            FRIEND TEXT,
            farmed BOOLEAN,
            banned BOOLEAN,
            banned_until DATETIME,
            email TEXT,
            password TEXT
        )
    """

    try:
        # 2. Get columns that currently exist in the old table
        cursor.execute("PRAGMA table_info(accounts)")
        old_cols = {row[1] for row in cursor.fetchall()}

        if not old_cols:
            # Table doesn't exist yet, just create it
            cursor.execute(new_schema)
            update("commit")
            # conn.commit()
            print("Table created from scratch.")
            return

        # 3. Rename the current table to keep it as a backup during migration
        cursor.execute("ALTER TABLE accounts RENAME TO old_accounts")

        # 4. Create the new table
        cursor.execute(new_schema)

        # 5. Identify columns that exist in BOTH old and new formats
        cursor.execute("PRAGMA table_info(accounts)")
        new_cols = {row[1] for row in cursor.fetchall()}

        common_cols = list(old_cols.intersection(new_cols))
        cols_str = ", ".join(common_cols)

        # 6. Transfer the data
        if common_cols:
            cursor.execute(f"INSERT INTO accounts ({cols_str}) SELECT {cols_str} FROM old_accounts")

        # 7. Clean up
        cursor.execute("DROP TABLE old_accounts")
        update("commit")
        # conn.commit()
        bot.reply_to(message,f"Миграция завершена успешно. Перенесено: {common_cols}")

    except sqlite3.Error as e:
        conn.rollback()
        bot.reply_to(message,f"Произошла ошибка при миграции: {e}")

@bot.message_handler(commands=['execute'])
def execute(message):
    if not(authenticated[message.from_user.id]):
        print("Ошибка аутентификации")
        return
    args = message.text.split()
    command=" ".join(args[1:])
    cursor.execute(command)
    update("commit")
    # conn.commit()

@bot.message_handler(commands=['disconnect'])
def close_connection(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    conn.close()
    print("Соединение с базой данных закрыто")

@bot.message_handler(commands=['connect'])
def connect(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    args = message.text.split()
    print(args)
    print(len(args))
    if len(args) < 2:
        bot.reply_to(message,"Укажите имя базы для подключения.")
        return
    if len(args) > 2:
        bot.reply_to(message, "Использование пробелов не допускается.")
        return
    global conn
    global cursor

    try: # try to close an open connection if there's one
        conn.close()
        cursor.close()
    except:
        pass

    try:
        conn = sqlite3.connect(str(args[1])+".db", check_same_thread=False)
        cursor=conn.cursor()
    except Exception as e:
        bot.reply_to(message,f"Произошла ошибка при подключении: {e}")
    else:
        bot.reply_to(message, f"Успешное подключение к базе {args[1]}.db!\nЧтобы создать таблицу аккаунтов (если вы ещё это не сделали), используйте */initialize*",parse_mode="Markdown")

@bot.message_handler(commands=['initialize'])
def initialize_db(message):
    if not(is_user(message.from_user.id) and is_authenticated(message)):
        return
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                number INTEGER UNIQUE,
                name TEXT,
                profile TEXT,
                FRIEND TEXT,
                farmed BOOLEAN,
                banned BOOLEAN,
                banned_until DATETIME,
                email TEXT,
                password TEXT
            )
        ''')
    except Exception as e:
        bot.reply_to(message,f"Произошла ошибка при инициализации: {e}")


def friend(messages):
    for message in messages:
        if message.text and ("friend" in message.text.lower() or "друг" in message.text.lower()):
            print("FRIEND")
            bot.send_sticker(message.chat.id,sticker=open('FRIEND.webm','rb'))

bot.set_update_listener(friend)


def check_expired_bans(force=False,user_id=None):
    print("Проверка аккаунтов на истёкшие баны...")
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT number, name FROM accounts WHERE banned = 1 AND banned_until <= ?", (today,))
    expired_accounts = cursor.fetchall()

    if expired_accounts:
        account_list = "\n".join([f"№{acc[0]}: {acc[1]}" for acc in expired_accounts])
        print(f"Обнаружены аккаунты с истёкшим баном! ")
        append="\nОни не были отмечены разбаненными автоматически. Вам необходимо сделать это вручную: /unban <номер>"
        if clearUnbansOnStart is True or force is True:
            append="\nОни были отмечены разбаненными автоматически."
            cursor.execute("""
                UPDATE accounts 
                SET banned = 0, banned_until = 0 
                WHERE banned = 1 AND banned_until <= ?
            """, (today,))
            update("commit")
            # conn.commit()
            if force is True:
                bot.send_message(user_id,f"Обнаружены и отмечены разбаненными следующие аккаунты:\n{account_list}")
        if checkUnbansOnStart is True and force is False:
            print("Рассылка сообщения об истёкших банах...")
            for user_id in USERS:
                bot.send_message(user_id,f"Обнаружены аккаунты с истёкшим баном:\n{account_list}"+append)

    else:
        print("Истёкших банов не найдено.")
        if force is True:
            bot.send_message(user_id,"Истёкших банов не найдено.")

authenticated={}
authenticateAll=True if enableAuth is False else False # если выключена авторизация, автоматически авторизуем всех (спагетти код)
if enableAuth is True:
    authenticateAll = False
    COMMANDS.extend(auth_cmd)
for uid in USERS:
    authenticated[uid] = authenticateAll

def update_cmds():
    if autoCommit is True:
        bot.set_my_commands([telebot.types.BotCommand(c["cmd"], c["desc"]) for c in (COMMANDS + commit_cmds)])
        print("Список команд обновлён (автосохранение вкл.)")
        return
    bot.set_my_commands([telebot.types.BotCommand(c["cmd"], c["desc"]) for c in COMMANDS])
    print("Список команд обновлён (автосохранение выкл.)")
    return

update_cmds()
for cmd in COMMANDS: # for every command in vocabulary COMMANDS, do:
    func = globals()[cmd["func"]] # find the function in "func" that corresponds to "cmd" in vocabulary
    bot.message_handler(commands=[cmd["cmd"]])(func) # create a handler for the found command and bind it to its found function

check_expired_bans()
bot.infinity_polling()
