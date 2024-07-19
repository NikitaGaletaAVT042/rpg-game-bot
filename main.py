import datetime
import random
import time

import telebot
from telebot.types import Message, CallbackQuery as Cq, ReplyKeyboardRemove as Rkr
from telebot.types import InlineKeyboardMarkup as Ikm, InlineKeyboardButton as Ikb, ReplyKeyboardMarkup as Rkm

from config import TOKEN
from database import *

bot = telebot.TeleBot(TOKEN)
clear = Rkr()

temp = {}

powers = {
    'Огонь': (120, 15),
    'Воздух': (100, 25),
    "Земля": (100, 20),
    "Металл": (110, 20),
    "Дерево": (130, 14),
    "Вода": (110, 25)
}


class Enemy:
    enemies = {
        'Вурдалак': (80, 20),
        'Призрак': (85, 15),
        'Минотавр': (100, 15),
        'Медуза': (75, 25),
        'Вор': (60, 20),
        'Феникс': (130, 30),
        'Дракон': (150, 40),
        'Единорог': (90, 25),
        'Циклоп': (100, 20)
    }

    def __init__(self, hero_lvl):
        self.name = random.choice(list(self.enemies))
        self.hp = self.enemies[self.name][0] + (5 * (hero_lvl - 1))  # зависимость от уровня героя
        self.damage = self.enemies[self.name][1] + (5 * (hero_lvl - 1))  # зависимость от уровня героя


@bot.message_handler(["start"])
def start(m: Message):
    if is_new_player(m):
        temp[m.chat.id] = {}
        reg_1(m)
    else:
        menu(m)


@bot.message_handler(["menu"])
def menu(m: Message):
    try:
        print(temp[m.chat.id])
    except KeyError:
        temp[m.chat.id] = {}
    txt = "Что будешь делать?\n/square - идём на главную площадь\n/home - путь домой\n/stats - статистика"
    bot.send_message(m.chat.id, txt, reply_markup=clear)


@bot.message_handler(["square"])
def square(m: Message):
    kb = Rkm(True, True)
    kb.row("Тренировка", "Испытание ловкости", "Пойти в бой")
    bot.send_message(m.chat.id, "Ты на главной площади, что будешь делать?", reply_markup=kb)
    bot.register_next_step_handler(m, reg_4)


@bot.message_handler(["home"])
def home(m: Message):
    kb = Rkm(True, True)
    kb.row("Пополнить ХП", "Передохнуть")
    bot.send_message(m.chat.id, "Ты дома, выбирай, чем хочешь заняться)", reply_markup=kb)
    bot.register_next_step_handler(m, reg_5)


@bot.message_handler(["stats"])
def stats(m: Message):
    player = db.read("user_id", m.chat.id)
    t = f"Стихия: {player[2]}\nНикнейм: {player[1]}\n" \
        f"Здоровье: {player[3]}❤️\n" \
        f"Урон: {player[4]}⚔️\n" \
        f"Уровень: {player[5]}\nОпыт: {player[6]}⚜️\n\n" \
        f"Еда:\n"
    _, food = heals.read("user_id", m.chat.id)
    for f in food:
        t += f"{f} ❤️{food[f][1]} — {food[f][0]}шт.\n"
    bot.send_message(m.chat.id, t)
    time.sleep(3)
    menu(m)


@bot.callback_query_handler(func=lambda call: True)
def callback(call: Cq):
    print(call.data)
    if call.data.startswith("food_"):
        a = call.data.split("_")
        eating(call.message, a[1], a[2])
        # Еще раз создаём клавиатуру
        kb = Ikm()
        _, food = heals.read("user_id", call.message.chat.id)
        if food == {}:
            bot.send_message(call.message.chat.id, 'Кушать нечего, воспользуйся командой /add_heal чтобы '
                                                   'пополнить свои запасы)', reply_markup=clear)
            menu(call.message)
            return
        for key in food:
            kb.row(Ikb(f"{key} {food[key][1]} hp. - {food[key][0]} шт.", callback_data=f"food_{key}_{food[key][1]}"))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb)
    if call.data.startswith("sleep_"):
        a = call.data.split("_")
        t = int(a[1])
        bot.send_message(call.message.chat.id, f"Ты лег отдыхать, кол-во секунд для сна: {t}.")
        time.sleep(t)
        sleeping(call.message, a[1])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        menu(call.message)
    if call.data == '0':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        menu(call.message)
    if call.data == "menu":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        menu(call.message)
    if call.data == "workout":
        player = db.read("user_id", call.message.chat.id)
        player[4] += player[5] / 10
        player[4] = round(player[4], 2)
        db.write(player)
        bot.answer_callback_query(call.id, "Ты тренируешься и твоя сила увеличивается! \n"
                                           f"Теперь ты наносишь {player[4]}⚔️", True)


@bot.message_handler(["add_heal"])
def add_heal(msg: Message):
    _, food = heals.read("user_id", msg.chat.id)
    print(food)

    food["Пельмени"] = [15, 15]

    heals.write([msg.chat.id, food])
    bot.send_message(msg.chat.id, "Герой получил припасы")


def eat(msg: Message):
    kb = Ikm()
    _, food = heals.read("user_id", msg.chat.id)
    if food == {}:
        bot.send_message(msg.chat.id, 'Кушать нечего, воспользуйся командой /add_heal чтобы пополнить '
                                      'свои запасы)', reply_markup=clear)
        menu(msg)
        return
    for key in food:
        if food[key][0] > 0:
            kb.row(Ikb(f"{key} {food[key][1]} hp. - {food[key][0]} шт.", callback_data=f"food_{key}_{food[key][1]}"))
    bot.send_message(msg.chat.id, "Выбери что будешь есть:", reply_markup=kb)


def eating(msg, ft, hp):
    _, food = heals.read("user_id", msg.chat.id)
    player = db.read("user_id", msg.chat.id)
    # Отнимаем еду
    if food[ft][0] == 1:
        del food[ft]
    else:
        food[ft][0] -= 1
    heals.write([msg.chat.id, food])

    # Добавляем ХП
    player[3] += int(hp)
    db.write(player)
    print("Игрок поел")


def sleep(m: Message):
    player = db.read("user_id", m.chat.id)
    low = int(powers[player[2]][0] * player[5]) // 2 - player[3]
    high = int(powers[player[2]][0] * player[5]) - player[3]
    kb = Ikm()
    if low > 0:
        kb.row(Ikb(f"Вздремнуть — +{low}❤️", callback_data=f"sleep_{low}"))
    if high > 0:
        kb.row(Ikb(f"Поспать — +{high}❤️", callback_data=f"sleep_{high}"))
    if len(kb.keyboard) == 0:
        kb.row(Ikb('Спать не хочется', callback_data='0'))
    bot.send_message(m.chat.id, "Выбери, сколько будешь отдыхать:", reply_markup=kb)


def sleeping(m: Message, hp):
    player = db.read("user_id", m.chat.id)
    player[3] += int(hp)
    db.write(player)
    print("Игрок поспал")


def workout(msg: Message):
    kb = Ikm()
    kb.row(Ikb("Тренироваться", callback_data="workout"))
    kb.row(Ikb("Назад", callback_data="menu"))
    bot.send_message(msg.chat.id, "Жми, чтобы тренироваться!", reply_markup=kb)


def block(m: Message):
    try:
        print(temp[m.chat.id]['win'])
    except KeyError:
        temp[m.chat.id]['win'] = 0
    bot.send_message(m.chat.id, f"Приготовься к атаке!", reply_markup=clear)
    time.sleep(3)
    # Создаём список сторон и перемешиваем его
    sides = ["Слева", "Справа", "Сверху", "Снизу"]
    random.shuffle(sides)

    # Создаём клавиатуру
    kb = Rkm(True, False)
    kb.row(sides[0], sides[3])
    kb.row(sides[1], sides[2])

    # Выбираем сторону удара и отправляем сообщение
    right = random.choice(sides)
    bot.send_message(m.chat.id, f"Защищайся! Удар {right}!", reply_markup=kb)
    temp[m.chat.id]["block_start"] = datetime.datetime.now().timestamp()
    bot.register_next_step_handler(m, block_handler, right)


def block_handler(m: Message, side: str):
    final = datetime.datetime.now().timestamp()
    if final - temp[m.chat.id]["block_start"] > 3 or side != m.text:
        # player[4] - это урон из БД (замена методу read_obj)
        bot.send_message(m.chat.id, "Твоя реакция медленная или ты пропустил удар, испытание окончено")
        time.sleep(5)
        menu(m)
        return
    if temp[m.chat.id]['win'] < 5:
        bot.send_message(m.chat.id, "Ты справился, продолжаем!")
        temp[m.chat.id]['win'] += 1
        block(m)
        return
    else:
        temp[m.chat.id]['win'] = 0
        player = db.read("user_id", m.chat.id)
        player[3] += 20
        db.write(player)
        bot.send_message(m.chat.id, "Ты прошел испытание ловкости, твоё хп увеличилось на 20!)")
        time.sleep(2)
        menu(m)
        return


def fight(m: Message):
    bot.send_message(m.chat.id, 'Ты отправился за пределы замка в поисках врагов...')
    time.sleep(3)
    bot.send_message(m.chat.id, 'Кажется враги уже близко...')
    time.sleep(1)
    new_enemy(m)


def new_enemy(m: Message):
    player = db.read('user_id', m.chat.id)
    enemy = Enemy(player[5])
    kb = Rkm(True, True)
    kb.row("Сразиться", "Сбежать")
    kb.row("Вернуться в город")
    txt = f'ты встретил врага: {enemy.name}, хп: {enemy.hp}, урон: {enemy.damage}.\nЧто будешь делать?'
    bot.send_message(m.chat.id, txt, reply_markup=kb)
    bot.register_next_step_handler(m, fight_handler, enemy)


def fight_handler(m: Message, enemy: Enemy):
    if m.text == 'Сразиться':
        attack(m, enemy)
    elif m.text == 'Сбежать':
        a = random.randint(1, 5)
        if a in range(1, 4):
            bot.send_message(m.chat.id, 'Ты сбежал, и отправился на поиск других врагов!')
            time.sleep(2)
            new_enemy(m)
        else:
            bot.send_message(m.chat.id, 'Сбежать не удалось, приготовься к сражению!')
            attack(m, enemy)
    elif m.text == 'Вернуться в город':
        time.sleep(1)
        bot.send_message(m.chat.id, 'Ты держишь путь обратно в город...')
        time.sleep(3)
        menu(m)


def attack(m: Message, enemy: Enemy):
    atk = player_attack(m, enemy)
    if atk is True:
        atk = enemy_attack(m, enemy)
        if atk is True:
            attack(m, enemy)
    else:
        player = db.read('user_id', m.chat.id)
        time.sleep(2)
        exp = random.randint(25, 40)
        bot.send_message(m.chat.id, f'За этот бой ты получаешь {exp} опыта')
        player[6] += exp
        db.write(player)
        exp_check(m)
        bot.send_message(m.chat.id, 'Ты отправился на поиск других врагов!')
        new_enemy(m)
        return


def player_attack(m: Message, enemy: Enemy):
    time.sleep(1)
    player = db.read('user_id', m.chat.id)
    enemy.hp -= player[4]
    if enemy.hp <= 0:
        bot.send_message(m.chat.id, 'Ты одержал победу над врагом!')
        return False
    else:
        bot.send_message(m.chat.id, f'{enemy.name}, хп {round(enemy.hp, 1)}')
        return True


def enemy_attack(m: Message, enemy: Enemy):
    time.sleep(1)
    player = db.read('user_id', m.chat.id)
    player[3] -= enemy.damage
    db.write(player)
    if player[3] <= 0:
        player[3] = 1
        db.write(player)
        bot.send_message(m.chat.id, 'Ты получил сокрушительный удар! Проходивший мимо охотник заметил тебя, и '
                                    'повез обратно в замок... Ты находишься на волосок от смерти...')
        time.sleep(3)
        menu(m)
        return
    else:
        bot.send_message(m.chat.id, f'{player[1]}, хп {round(player[3], 1)}')
        return True


def exp_check(m: Message):
    player = db.read('user_id', m.chat.id)
    if player[6] >= 100 + ((player[5] - 1) * 50):
        player[6] -= 100 + ((player[5] - 1) * 50)
        player[3] = powers[player[2]][0] + ((player[5] - 1) * 15)
        player[5] += 1
        player[4] += 5
        player[3] += 15
        db.write(player)
        t = f"Стихия: {player[2]}\nНикнейм: {player[1]}\n" \
            f"Здоровье: {player[3]}❤️\n" \
            f"Урон: {player[4]}⚔️\n" \
            f"Уровень: {player[5]}\nОпыт: {player[6]}⚜️"
        bot.send_message(m.chat.id, f'Поздравляю с повышением уровня!!! Вот твои характеристики:\n' + t)
        time.sleep(2)
        return
    return


def is_new_player(m: Message):
    result = db.read_all()
    for user in result:
        if user[0] == m.chat.id:
            return False
    return True


def reg_1(m: Message):
    txt = ("Привет, %s. В этой игре ты отринешь свою сущность и станешь настоящим магом 🧙‍♂️. Мир на пороге "
           "уничтожения: народ огня 🔥 развязал войну, и именно ты станешь тем, кто поможет им в ней или будет"
           "противостоять им⚔️!\nЯ верю в тебя!\n\nНазови своё имя, новобранец:")
    bot.send_message(m.chat.id, text=txt % m.from_user.first_name)
    bot.register_next_step_handler(m, reg_2)


def reg_2(m: Message):
    temp[m.chat.id]["nick"] = m.text
    kb = Rkm(True, True)
    kb.row("Вода", "Воздух")
    kb.row("Металл", "Земля")
    kb.row("Огонь", "Дерево")
    bot.send_message(m.chat.id, "Выбери стихию:", reply_markup=kb)
    bot.register_next_step_handler(m, reg_3)


def reg_3(m: Message):
    temp[m.chat.id]["power"] = m.text
    hp, dmg = powers[m.text]
    db.write([m.chat.id, temp[m.chat.id]["nick"], temp[m.chat.id]["power"], hp, dmg, 1, 0])
    heals.write([m.chat.id, {}])
    print("Пользователь добавлен в базу данных")
    bot.send_message(m.chat.id, "Инициализация ...")
    time.sleep(2)
    menu(m)


def reg_4(m: Message):
    if m.text == "Тренировка":
        workout(m)
    if m.text == "Испытание ловкости":
        block(m)
    if m.text == "Пойти в бой":
        fight(m)


def reg_5(m: Message):
    if m.text == "Пополнить ХП":
        eat(m)
    if m.text == "Передохнуть":
        sleep(m)


bot.infinity_polling()
