TOKEN = ""
USERS = [] # пример: [1234567890, 1234567891, 1234567892]

# аутентификация
enableAuth = True # если оставить выключенным, то все опасные команды будут доступны без использования /auth
authPassword = "" # если оставить пустым, то /auth будет принимать любые пароли
authDuration = 5 # после этого количества минут аутентификация истекает

dbFilename = "accs"
autoCommit = True
# автоматически записывать изменения данных в базу

checkUnbansOnStart = True # проверять аккаунты на разбаны и уведомлять пользователей
clearUnbansOnStart = True # автоматически отмечать разбанившиеся аккаунты при запуске

useProxy = False
proxyType = "" # опции: "socks5", "http", "https"
proxyIP = ""
proxyPort = 00000
proxyUsername = ""
proxyPassword = ""