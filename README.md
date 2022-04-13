Телеграм бот для создания и прохождения курсов, включает в себя создание и прохождение курсов с тестированием по пройденному материалу. На основе aiogram, использует Postgres для хранения курсов и данных учеников, MongoStorage - состояний  aiogram

Возможности: создание и управление собственным курсом, выдача доступа к курсам определенным ученикам,

 Курс состоит из отдельных уроков в виде теории (текст и/или картинки), после теории предлагается пройти тестирование по пройденному материалу, вопросы могут быть как с вариантами ответа так и без, по прохождению тестовой части открывается доступ к следующему уроку курса

Для управления курсом есть админ панель, в которой можно: удалить курс, сделать неактивным, организовать права доступа учеников, добавлять новые уроки

Структура:
bot.py - запуск бота
bd_interface.py - создание БД