TOKEN = ""
USERS = [] # пример: [1234567890, 1234567891, 1234567892]

authPassword = ""
authDuration = 5 # после этого количества минут аутентификация истекает

dbFilename = "accs"

checkUnbansOnStart = True # отправлять пользователям сообщение с разбанившимися аккаунтами
clearUnbansOnStart = True # автоматически отмечать разбанившиеся аккаунты при запуске

useProxy = False
proxyType = "" # опции: "socks5", "http", "https"
proxyIP = ""
proxyPort = 00000
proxyUsername = ""
proxyPassword = ""