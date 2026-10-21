# mypy: ignore-errors
"""Generate JSON command cards for the built-in command library."""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
COMMANDS_DIR = BASE_DIR / "content" / "commands"

ALL_COMMANDS = [
    {
        "slug": "ban",
        "name": "ban",
        "title": "Блокировка участника",
        "category": "moderation",
        "description": "Навсегда блокирует пользователя на сервере",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 4,
        "default_member_permissions": "4",
        "required_intents": ["GUILD_MEMBERS"],
        "cooldown": {"type": "user", "seconds": 5},
        "options": [
            {"name": "user", "description": "Кого забанить", "type": 6, "required": True},
            {"name": "reason", "description": "Причина бана", "type": 3, "required": False},
            {"name": "delete_days", "description": "Удалить сообщения за N дней", "type": 4, "required": False}
        ]
    },
    {
        "slug": "unban",
        "name": "unban",
        "title": "Разблокировка участника",
        "category": "moderation",
        "description": "Снимает бан с указанного пользователя",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 4,
        "default_member_permissions": "4",
        "required_intents": ["GUILD_MEMBERS"],
        "options": [
            {"name": "user_id", "description": "Discord ID забаненного пользователя", "type": 3, "required": True},
            {"name": "reason", "description": "Причина разбана", "type": 3, "required": False}
        ]
    },
    {
        "slug": "kick",
        "name": "kick",
        "title": "Исключение с сервера",
        "category": "moderation",
        "description": "Выгоняет участника с сервера",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 2,
        "default_member_permissions": "2",
        "required_intents": ["GUILD_MEMBERS"],
        "options": [
            {"name": "user", "description": "Кого исключить", "type": 6, "required": True},
            {"name": "reason", "description": "Причина кика", "type": 3, "required": False}
        ]
    },
    {
        "slug": "timeout",
        "name": "timeout",
        "title": "Тайм-аут (мьют)",
        "category": "moderation",
        "description": "Временно запрещает участнику писать и говорить",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 1099511627776,
        "default_member_permissions": "1099511627776",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True},
            {"name": "duration_minutes", "description": "Длительность в минутах", "type": 4, "required": True},
            {"name": "reason", "description": "Причина", "type": 3, "required": False}
        ]
    },
    {
        "slug": "warn",
        "name": "warn",
        "title": "Выдать предупреждение",
        "category": "moderation",
        "description": "Выдает официальный варн участнику с записью в журнал",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "user", "description": "Кому выдать варн", "type": 6, "required": True},
            {"name": "reason", "description": "Причина варна", "type": 3, "required": True}
        ]
    },
    {
        "slug": "warnings",
        "name": "warnings",
        "title": "Список предупреждений",
        "category": "moderation",
        "description": "Просмотр всех варнов пользователя",
        "type": "slash",
        "required_module": "moderation",
        "options": [
            {"name": "user", "description": "Чьи варны посмотреть", "type": 6, "required": False}
        ]
    },
    {
        "slug": "clearwarns",
        "name": "clearwarns",
        "title": "Очистить варны",
        "category": "moderation",
        "description": "Сбрасывает все предупреждения пользователя",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True}
        ]
    },
    {
        "slug": "purge",
        "name": "purge",
        "title": "Массовое удаление сообщений",
        "category": "moderation",
        "description": "Удаляет последние N сообщений в канале",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "amount", "description": "Количество сообщений (от 1 до 100)", "type": 4, "required": True}
        ]
    },
    {
        "slug": "slowmode",
        "name": "slowmode",
        "title": "Медленный режим",
        "category": "moderation",
        "description": "Устанавливает задержку между сообщениями в канале",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 16,
        "default_member_permissions": "16",
        "options": [
            {"name": "seconds", "description": "Секунды задержки (0 для отключения)", "type": 4, "required": True}
        ]
    },
    {
        "slug": "lock",
        "name": "lock",
        "title": "Заблокировать канал",
        "category": "moderation",
        "description": "Запрещает отправку сообщений в канале для @everyone",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 16,
        "default_member_permissions": "16"
    },
    {
        "slug": "unlock",
        "name": "unlock",
        "title": "Разблокировать канал",
        "category": "moderation",
        "description": "Возвращает право писать в канал для @everyone",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 16,
        "default_member_permissions": "16"
    },
    {
        "slug": "nick",
        "name": "nick",
        "title": "Сменить никнейм",
        "category": "moderation",
        "description": "Изменяет никнейм указанного участника на сервере",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 134217728,
        "default_member_permissions": "134217728",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True},
            {"name": "nickname", "description": "Новый никнейм (оставьте пустым для сброса)", "type": 3, "required": False}
        ]
    },
    {
        "slug": "modlog",
        "name": "modlog",
        "title": "Журнал модерации",
        "category": "moderation",
        "description": "Просмотр последних действий модераторов на сервере",
        "type": "slash",
        "required_module": "moderation",
        "required_permissions": 128,
        "default_member_permissions": "128"
    },

    {
        "slug": "ping",
        "name": "ping",
        "title": "Проверка связи",
        "category": "utility",
        "description": "Показывает пинг шлюза Discord и статус бота",
        "type": "slash",
        "cooldown": {"type": "user", "seconds": 3}
    },
    {
        "slug": "serverinfo",
        "name": "serverinfo",
        "title": "Информация о сервере",
        "category": "utility",
        "description": "Показывает детальную статистику сервера",
        "type": "slash"
    },
    {
        "slug": "userinfo",
        "name": "userinfo",
        "title": "Информация о пользователе",
        "category": "utility",
        "description": "Показывает дату регистрации, роли и статус участника",
        "type": "slash",
        "options": [{"name": "user", "description": "Участник", "type": 6, "required": False}]
    },
    {
        "slug": "avatar",
        "name": "avatar",
        "title": "Аватар участника",
        "category": "utility",
        "description": "Отображает полноразмерную аватарку участника",
        "type": "slash",
        "options": [{"name": "user", "description": "Участник", "type": 6, "required": False}]
    },
    {
        "slug": "roleinfo",
        "name": "roleinfo",
        "title": "Информация о роли",
        "category": "utility",
        "description": "Отображает ID, цвет, права и число участников роли",
        "type": "slash",
        "options": [{"name": "role", "description": "Роль", "type": 8, "required": True}]
    },
    {
        "slug": "channelinfo",
        "name": "channelinfo",
        "title": "Информация о канале",
        "category": "utility",
        "description": "Отображает тип, ID и тему канала",
        "type": "slash",
        "options": [{"name": "channel", "description": "Канал", "type": 7, "required": False}]
    },
    {
        "slug": "poll",
        "name": "poll",
        "title": "Создать голосование",
        "category": "utility",
        "description": "Создает интерактивный опрос с реакциями или кнопками",
        "type": "slash",
        "options": [
            {"name": "question", "description": "Вопрос голосования", "type": 3, "required": True},
            {"name": "option1", "description": "Вариант 1", "type": 3, "required": True},
            {"name": "option2", "description": "Вариант 2", "type": 3, "required": True}
        ]
    },
    {
        "slug": "remind",
        "name": "remind",
        "title": "Установить напоминание",
        "category": "utility",
        "description": "Бот напомнит вам о важном событии через указанное время",
        "type": "slash",
        "options": [
            {"name": "minutes", "description": "Через сколько минут напомнить", "type": 4, "required": True},
            {"name": "text", "description": "Текст напоминания", "type": 3, "required": True}
        ]
    },
    {
        "slug": "embed",
        "name": "embed",
        "title": "Отправить красивый Embed",
        "category": "utility",
        "description": "Отправляет форматированное сообщение-карточку в текущий канал",
        "type": "slash",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "title", "description": "Заголовок эмбеда", "type": 3, "required": True},
            {"name": "description", "description": "Текст сообщения", "type": 3, "required": True},
            {"name": "color", "description": "HEX-цвет (например #5865F2)", "type": 3, "required": False}
        ]
    },
    {
        "slug": "say",
        "name": "say",
        "title": "Сказать от имени бота",
        "category": "utility",
        "description": "Отправляет введенный текст от имени бота",
        "type": "slash",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "text", "description": "Сообщение для отправки", "type": 3, "required": True}
        ]
    },

    {
        "slug": "role_add",
        "name": "role_add",
        "title": "Выдать роль",
        "category": "roles",
        "description": "Выдает указанную роль участнику",
        "type": "slash",
        "required_module": "roles",
        "required_permissions": 268435456,
        "default_member_permissions": "268435456",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True},
            {"name": "role", "description": "Роль", "type": 8, "required": True}
        ]
    },
    {
        "slug": "role_remove",
        "name": "role_remove",
        "title": "Снять роль",
        "category": "roles",
        "description": "Забирает роль у участника",
        "type": "slash",
        "required_module": "roles",
        "required_permissions": 268435456,
        "default_member_permissions": "268435456",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True},
            {"name": "role", "description": "Роль", "type": 8, "required": True}
        ]
    },
    {
        "slug": "autorole",
        "name": "autorole",
        "title": "Настроить авто-роль",
        "category": "roles",
        "description": "Задает роль, выдаваемую при входе на сервер",
        "type": "slash",
        "required_module": "welcomes",
        "required_permissions": 268435456,
        "default_member_permissions": "268435456",
        "options": [
            {"name": "role", "description": "Роль для новичков", "type": 8, "required": True}
        ]
    },
    {
        "slug": "reactionroles",
        "name": "reactionroles",
        "title": "Создать реакции-роли",
        "category": "roles",
        "description": "Прикрепляет выдачу ролей по реакциям к сообщению",
        "type": "slash",
        "required_module": "roles",
        "required_permissions": 268435456,
        "default_member_permissions": "268435456"
    },
    {
        "slug": "selfroles",
        "name": "selfroles",
        "title": "Меню выбора ролей",
        "category": "roles",
        "description": "Открывает меню самостоятельного выбора ролей",
        "type": "slash",
        "required_module": "roles"
    },
    {
        "slug": "rolemenu",
        "name": "rolemenu",
        "title": "Панель ролей с кнопками",
        "category": "roles",
        "description": "Отправляет интерактивную панель с кнопками для выдачи ролей",
        "type": "slash",
        "required_module": "roles",
        "required_permissions": 268435456,
        "default_member_permissions": "268435456"
    },
    {
        "slug": "colorrole",
        "name": "colorrole",
        "title": "Выбрать цвет ника",
        "category": "roles",
        "description": "Позволяет пользователю выбрать цвет своего ника из доступных",
        "type": "slash",
        "required_module": "roles"
    },

    {
        "slug": "profile",
        "name": "profile",
        "title": "Карточка профиля",
        "category": "social",
        "description": "Показывает социальный профиль, репутацию и значки",
        "type": "slash",
        "options": [{"name": "user", "description": "Чей профиль", "type": 6, "required": False}]
    },
    {
        "slug": "rep",
        "name": "rep",
        "title": "Повысить репутацию (+rep)",
        "category": "social",
        "description": "Выражает благодарность и добавляет очко репутации участнику",
        "type": "slash",
        "cooldown": {"type": "user", "seconds": 43200},
        "options": [{"name": "user", "description": "Кому повысить репутацию", "type": 6, "required": True}]
    },
    {
        "slug": "birthday",
        "name": "birthday",
        "title": "Указать день рождения",
        "category": "social",
        "description": "Сохраняет дату вашего дня рождения для автопоздравления",
        "type": "slash",
        "options": [
            {"name": "day", "description": "День (1-31)", "type": 4, "required": True},
            {"name": "month", "description": "Месяц (1-12)", "type": 4, "required": True}
        ]
    },
    {
        "slug": "hug",
        "name": "hug",
        "title": "Обнять участника",
        "category": "social",
        "description": "Дружески обнимает выбранного пользователя с анимацией",
        "type": "slash",
        "options": [{"name": "user", "description": "Кого обнять", "type": 6, "required": True}]
    },
    {
        "slug": "pat",
        "name": "pat",
        "title": "Погладить по голове",
        "category": "social",
        "description": "Отправляет милую реакцию поглаживания",
        "type": "slash",
        "options": [{"name": "user", "description": "Кого погладить", "type": 6, "required": True}]
    },
    {
        "slug": "afk",
        "name": "afk",
        "title": "Установить AFK-статус",
        "category": "social",
        "description": "Бот будет отвечать, что вы отошли, когда вас тегают",
        "type": "slash",
        "options": [{"name": "reason", "description": "Причина отсутствия", "type": 3, "required": False}]
    },
    {
        "slug": "marry",
        "name": "marry",
        "title": "Заключить брак",
        "category": "social",
        "description": "Сделать предложение руки и сердца другому участнику",
        "type": "slash",
        "options": [{"name": "user", "description": "Избранник", "type": 6, "required": True}]
    },
    {
        "slug": "leaderboard",
        "name": "leaderboard",
        "title": "Таблица репутации",
        "category": "social",
        "description": "Топ участников сервера по очкам репутации",
        "type": "slash"
    },

    {
        "slug": "rank",
        "name": "rank",
        "title": "Ранг и уровень",
        "category": "levels",
        "description": "Показывает ваш текущий уровень и прогресс до следующего",
        "type": "slash",
        "required_module": "levels",
        "options": [{"name": "user", "description": "Участник", "type": 6, "required": False}]
    },
    {
        "slug": "top",
        "name": "top",
        "title": "Топ по опыту",
        "category": "levels",
        "description": "Таблица лидеров сервера по набранному опыту",
        "type": "slash",
        "required_module": "levels"
    },
    {
        "slug": "setxp",
        "name": "setxp",
        "title": "Установить опыт",
        "category": "levels",
        "description": "Изменяет количество опыта участника (для администрации)",
        "type": "slash",
        "required_module": "levels",
        "required_permissions": 8,
        "default_member_permissions": "8",
        "options": [
            {"name": "user", "description": "Участник", "type": 6, "required": True},
            {"name": "amount", "description": "Новое значение опыта", "type": 4, "required": True}
        ]
    },
    {
        "slug": "levelroles",
        "name": "levelroles",
        "title": "Роли за уровни",
        "category": "levels",
        "description": "Список наградных ролей, выдаваемых за достижение уровней",
        "type": "slash",
        "required_module": "levels"
    },
    {
        "slug": "resetlevels",
        "name": "resetlevels",
        "title": "Сбросить уровни",
        "category": "levels",
        "description": "Полный сброс рангов и опыта на сервере",
        "type": "slash",
        "required_module": "levels",
        "required_permissions": 8,
        "default_member_permissions": "8"
    },
    {
        "slug": "xpboost",
        "name": "xpboost",
        "title": "Множитель опыта",
        "category": "levels",
        "description": "Включает глобальный буст опыта на определенное время",
        "type": "slash",
        "required_module": "levels",
        "required_permissions": 8,
        "default_member_permissions": "8",
        "options": [
            {"name": "multiplier", "description": "Множитель (например 2 для x2)", "type": 4, "required": True}
        ]
    },

    {
        "slug": "balance",
        "name": "balance",
        "title": "Баланс кошелька",
        "category": "economy",
        "description": "Показывает количество монет в кошельке и в банке",
        "type": "slash",
        "required_module": "economy",
        "options": [{"name": "user", "description": "Чей баланс", "type": 6, "required": False}]
    },
    {
        "slug": "daily",
        "name": "daily",
        "title": "Ежедневная награда",
        "category": "economy",
        "description": "Получить ежедневный бонус монет раз в 24 часа",
        "type": "slash",
        "required_module": "economy",
        "cooldown": {"type": "user", "seconds": 86400}
    },
    {
        "slug": "work",
        "name": "work",
        "title": "Пойти на работу",
        "category": "economy",
        "description": "Выполнить разовую работу и получить честную зарплату",
        "type": "slash",
        "required_module": "economy",
        "cooldown": {"type": "user", "seconds": 3600}
    },
    {
        "slug": "pay",
        "name": "pay",
        "title": "Перевести монеты",
        "category": "economy",
        "description": "Отправляет указанную сумму монет другому участнику",
        "type": "slash",
        "required_module": "economy",
        "options": [
            {"name": "user", "description": "Получатель", "type": 6, "required": True},
            {"name": "amount", "description": "Сумма перевода", "type": 4, "required": True}
        ]
    },
    {
        "slug": "shop",
        "name": "shop",
        "title": "Магазин сервера",
        "category": "economy",
        "description": "Витрина товаров и эксклюзивных ролей за монеты",
        "type": "slash",
        "required_module": "economy"
    },
    {
        "slug": "buy",
        "name": "buy",
        "title": "Купить товар",
        "category": "economy",
        "description": "Приобрести товар из магазина по его ID",
        "type": "slash",
        "required_module": "economy",
        "options": [{"name": "item_id", "description": "ID товара", "type": 3, "required": True}]
    },
    {
        "slug": "inventory",
        "name": "inventory",
        "title": "Инвентарь",
        "category": "economy",
        "description": "Список купленных вами предметов и активных эффектов",
        "type": "slash",
        "required_module": "economy"
    },
    {
        "slug": "gamble",
        "name": "gamble",
        "title": "Сыграть на монеты",
        "category": "economy",
        "description": "Ставка в азартную игру с шансом удвоить баланс",
        "type": "slash",
        "required_module": "economy",
        "options": [{"name": "bet", "description": "Размер ставки", "type": 4, "required": True}]
    },
    {
        "slug": "baltop",
        "name": "baltop",
        "title": "Топ богачей",
        "category": "economy",
        "description": "Список самых богатых участников сервера",
        "type": "slash",
        "required_module": "economy"
    },

    {
        "slug": "coinflip",
        "name": "coinflip",
        "title": "Бросить монетку",
        "category": "fun",
        "description": "Подбрасывает монетку: Орёл или Решка",
        "type": "slash",
        "required_module": "fun"
    },
    {
        "slug": "dice",
        "name": "dice",
        "title": "Бросить игральный кубик",
        "category": "fun",
        "description": "Выпадение случайного числа от 1 до 6 (или N граней)",
        "type": "slash",
        "required_module": "fun",
        "options": [{"name": "sides", "description": "Количество граней (по умолчанию 6)", "type": 4, "required": False}]
    },
    {
        "slug": "8ball",
        "name": "8ball",
        "title": "Магический шар 8-ball",
        "category": "fun",
        "description": "Дает мистический ответ на ваш вопрос",
        "type": "slash",
        "required_module": "fun",
        "options": [{"name": "question", "description": "Ваш вопрос", "type": 3, "required": True}]
    },
    {
        "slug": "rps",
        "name": "rps",
        "title": "Камень, Ножницы, Бумага",
        "category": "fun",
        "description": "Сыграть в классическую игру против бота",
        "type": "slash",
        "required_module": "fun",
        "options": [
            {
                "name": "choice",
                "description": "Ваш выбор",
                "type": 3,
                "required": True,
                "choices": [
                    {"name": "Камень 🪨", "value": "rock"},
                    {"name": "Ножницы ✂️", "value": "scissors"},
                    {"name": "Бумага 📄", "value": "paper"}
                ]
            }
        ]
    },
    {
        "slug": "trivia",
        "name": "trivia",
        "title": "Интеллектуальная викторина",
        "category": "fun",
        "description": "Случайный вопрос с вариантами ответов на кнопках",
        "type": "slash",
        "required_module": "fun"
    },
    {
        "slug": "guessnumber",
        "name": "guessnumber",
        "title": "Угадай число",
        "category": "fun",
        "description": "Мини-игра: угадайте число от 1 до 100",
        "type": "slash",
        "required_module": "fun"
    },
    {
        "slug": "slots",
        "name": "slots",
        "title": "Игровой автомат (Слоты)",
        "category": "fun",
        "description": "Крутить барабан с эмодзи в надежде выбить 777",
        "type": "slash",
        "required_module": "fun"
    },
    {
        "slug": "hangman",
        "name": "hangman",
        "title": "Игра Виселица",
        "category": "fun",
        "description": "Угадывание спрятанного слова по буквам",
        "type": "slash",
        "required_module": "fun"
    },

    {
        "slug": "ticket_panel",
        "name": "ticket_panel",
        "title": "Панель создания тикетов",
        "category": "tickets",
        "description": "Отправляет интерактивную кнопку «Открыть тикет» в канал",
        "type": "slash",
        "required_module": "tickets",
        "required_permissions": 16,
        "default_member_permissions": "16"
    },
    {
        "slug": "ticket_close",
        "name": "ticket_close",
        "title": "Закрыть тикет",
        "category": "tickets",
        "description": "Закрывает текущее обращение и архивирует транскрипт",
        "type": "slash",
        "required_module": "tickets",
        "options": [{"name": "reason", "description": "Причина закрытия", "type": 3, "required": False}]
    },
    {
        "slug": "ticket_add",
        "name": "ticket_add",
        "title": "Добавить участника в тикет",
        "category": "tickets",
        "description": "Предоставляет доступ к каналу обращения указанному пользователю",
        "type": "slash",
        "required_module": "tickets",
        "options": [{"name": "user", "description": "Участник", "type": 6, "required": True}]
    },
    {
        "slug": "ticket_remove",
        "name": "ticket_remove",
        "title": "Удалить участника из тикета",
        "category": "tickets",
        "description": "Забирает доступ к тикету у указанного пользователя",
        "type": "slash",
        "required_module": "tickets",
        "options": [{"name": "user", "description": "Участник", "type": 6, "required": True}]
    },
    {
        "slug": "ticket_transcript",
        "name": "ticket_transcript",
        "title": "Выгрузить транскрипт",
        "category": "tickets",
        "description": "Формирует текстовый файл со всеми сообщениями тикета",
        "type": "slash",
        "required_module": "tickets"
    },

    {
        "slug": "autoresponder",
        "name": "autoresponder",
        "title": "Настроить авто-ответ",
        "category": "automation",
        "description": "Добавляет автоматический ответ на ключевое слово",
        "type": "slash",
        "required_module": "automation",
        "required_permissions": 8192,
        "default_member_permissions": "8192",
        "options": [
            {"name": "trigger", "description": "Слово или фраза триггера", "type": 3, "required": True},
            {"name": "response", "description": "Ответ бота", "type": 3, "required": True}
        ]
    },
    {
        "slug": "welcome",
        "name": "welcome",
        "title": "Настроить приветствие",
        "category": "automation",
        "description": "Задает канал и текст приветствия новых участников",
        "type": "slash",
        "required_module": "welcomes",
        "required_permissions": 32,
        "default_member_permissions": "32",
        "options": [
            {"name": "channel", "description": "Канал приветствий", "type": 7, "required": True},
            {"name": "message", "description": "Текст приветствия", "type": 3, "required": False}
        ]
    },
    {
        "slug": "goodbye",
        "name": "goodbye",
        "title": "Настроить прощание",
        "category": "automation",
        "description": "Задает канал для сообщений об уходе участников",
        "type": "slash",
        "required_module": "welcomes",
        "required_permissions": 32,
        "default_member_permissions": "32",
        "options": [
            {"name": "channel", "description": "Канал прощаний", "type": 7, "required": True},
            {"name": "message", "description": "Текст прощания", "type": 3, "required": False}
        ]
    },
    {
        "slug": "autodelete",
        "name": "autodelete",
        "title": "Автоудаление сообщений",
        "category": "automation",
        "description": "Автоматически удаляет сообщения в канале через заданное время",
        "type": "slash",
        "required_module": "automation",
        "required_permissions": 16,
        "default_member_permissions": "16",
        "options": [
            {"name": "seconds", "description": "Время жизни сообщений в секундах", "type": 4, "required": True}
        ]
    },
    {
        "slug": "schedule",
        "name": "schedule",
        "title": "Запланировать сообщение",
        "category": "automation",
        "description": "Регулярная отправка объявления по расписанию (cron)",
        "type": "slash",
        "required_module": "automation",
        "required_permissions": 32,
        "default_member_permissions": "32",
        "options": [
            {"name": "channel", "description": "Куда отправить", "type": 7, "required": True},
            {"name": "text", "description": "Текст сообщения", "type": 3, "required": True},
            {"name": "cron", "description": "Cron-выражение (например '0 12 * * *')", "type": 3, "required": True}
        ]
    },
    {
        "slug": "counting",
        "name": "counting",
        "title": "Игра в счёт",
        "category": "automation",
        "description": "Включает в канале режим счета по порядку (1, 2, 3...)",
        "type": "slash",
        "required_module": "automation",
        "required_permissions": 16,
        "default_member_permissions": "16"
    },

    {
        "slug": "giveaway_start",
        "name": "giveaway_start",
        "title": "Запустить розыгрыш",
        "category": "giveaways",
        "description": "Создает розыгрыш призов с таймером и реакцией 🎉",
        "type": "slash",
        "required_module": "giveaways",
        "required_permissions": 16,
        "default_member_permissions": "16",
        "options": [
            {"name": "prize", "description": "Что разыгрывается", "type": 3, "required": True},
            {"name": "duration_minutes", "description": "Длительность в минутах", "type": 4, "required": True},
            {"name": "winners_count", "description": "Количество победителей (по умолчанию 1)", "type": 4, "required": False}
        ]
    },
    {
        "slug": "giveaway_end",
        "name": "giveaway_end",
        "title": "Досрочно завершить розыгрыш",
        "category": "giveaways",
        "description": "Немедленно останавливает розыгрыш и выбирает победителя",
        "type": "slash",
        "required_module": "giveaways",
        "required_permissions": 16,
        "default_member_permissions": "16",
        "options": [{"name": "message_id", "description": "ID сообщения розыгрыша", "type": 3, "required": True}]
    },
    {
        "slug": "giveaway_reroll",
        "name": "giveaway_reroll",
        "title": "Перевыбрать победителя",
        "category": "giveaways",
        "description": "Случайно выбирает нового победителя завершенного розыгрыша",
        "type": "slash",
        "required_module": "giveaways",
        "required_permissions": 16,
        "default_member_permissions": "16",
        "options": [{"name": "message_id", "description": "ID сообщения розыгрыша", "type": 3, "required": True}]
    },
    {
        "slug": "giveaway_list",
        "name": "giveaway_list",
        "title": "Список активных розыгрышей",
        "category": "giveaways",
        "description": "Показывает текущие активные розыгрыши на сервере",
        "type": "slash",
        "required_module": "giveaways"
    }
]

def generate_command_json_files():
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for cmd in ALL_COMMANDS:
        category = cmd["category"]
        cat_dir = COMMANDS_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        card = dict(cmd)
        card.setdefault("options", [])
        card.setdefault("required_permissions", 0)
        card.setdefault("required_intents", [])
        card.setdefault("default_member_permissions", None)
        card.setdefault("cooldown", {"type": "user", "seconds": 3})
        
        card["preview"] = {
            "embed": {
                "title": f"Команда /{cmd['name']}",
                "description": cmd["description"],
                "color": 5793266
            }
        }
        card["flow"] = {
            "trigger": {"type": "slash_command", "name": cmd["name"]},
            "nodes": [
                {
                    "id": "node_reply",
                    "type": "send_message",
                    "params": {
                        "content": f"Выполнена команда /{cmd['name']}.",
                        "ephemeral": True
                    }
                }
            ],
            "edges": []
        }

        file_path = cat_dir / f"{cmd['slug']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
        count += 1

    print(f"Успешно сгенерировано {count} команд в директории {COMMANDS_DIR}")

if __name__ == "__main__":
    generate_command_json_files()
