import telebot
import requests
import os
from dotenv import load_dotenv

# игнорируем предупреждение, что сертификата нет не защищен, только для локальной разработки!!!!!!!! 
from requests.packages import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_API")

bot = telebot.TeleBot(BOT_TOKEN)
url = 'https://localhost:7003/authors'

@bot.message_handler(commands=['authors'])
def get_author_by_id(message): 
    parts = message.text.strip().split()

    # проверяем что команда корректна, некорректа - /authors
    if len(parts) < 2:
        bot.send_message(message.chat.id, "Укажите ID! Пример: /authors 4")
        return

    # проверка что именно число
    if not parts[1].isdigit():
        bot.send_message(message.chat.id, "ID должен состоять только из цифр!")
        return

    author_id = parts[1]

    get_url = f"{url}/{author_id}"

    responce = requests.get(get_url, verify=False)

    if responce.status_code == 404:
        bot.send_message(message.chat.id, f"Автор с ID {author_id} не найден!")
        return

    data = responce.json()

    books_list = []
    count = 1
    for book in data['books']:
        books_list.append(f"{count}. {book['title']}, год выпуска: {book['publishedYear']} г.")
        count += 1
    books_text = "\n".join(books_list)

    text = (
        f"Автор: {data['name']}\n"
        f"Возраст: {data['age']}\n"
        f"Книги:\n"
        f"{books_text}"
    )

    bot.send_message(message.chat.id, text)
    print(data)

user_data ={}

# Получение списка всех автора ()
# в будущем добавить пагинацию!!!!!!!! потому что при добавление 100 авторов будет беда
@bot.message_handler(commands=["authorslist"])
def get_author_list(message):
    url = 'https://localhost:7003/authors'

    try: 
        responce = requests.get(url, verify=False)

        if responce.status_code == 200: 
            authors = responce.json()

            if not authors:
                bot.send_message(message.chat.id, "Список авторов пуст.")
                return

            text = [f"Список всех авторов!\n"]
            count = 1
            for author in authors:
                text.append(f"{count}. Имя автора: {author.get('name')}, {author.get('age')} лет")
                count += 1
                books = author.get("books", [])
                book_count = 1
                if books:
                    for book in books:
                        text.append(f"\t\t{book_count}.) - Название: <b><u>{book.get('title')}</u></b>, Год выпуска: <b><u>{book.get('publishedYear')}</u></b>")
                        book_count += 1
                else:
                    text.append(f"Книг пока нет!")
            bot.send_message(message.chat.id, "\n".join(text), parse_mode="HTML")

        else:
            bot.send_message(message.chat.id, f"Ошибка сервера - {responce.status_code}")

    except Exception as e:
        bot.send_message(message.chat.id, f"Не удалось выполнить запрос: {e}")
# __________________________________________________________________________


# обраьботка команды createauthor которая post нового автора 
# (работаем постепенно с данными не все сразу! - register_next_step_handler)
# обязательно получать message.chat.id чтобы не было путаницы на сервере
# нет проверок! максимально сырый обработчик! 
@bot.message_handler(commands=["createauthor"])
def start(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"books": []}
    
    bot.send_message(chat_id, "Привет! Введи имя автора:")
    bot.register_next_step_handler(message, get_author_name)


def get_author_name(message):
    chat_id = message.chat.id
    user_data[chat_id]["name"] = message.text
    
    bot.send_message(chat_id, "Сколько лет автору?")
    bot.register_next_step_handler(message, get_author_age)


def get_author_age(message):
    chat_id = message.chat.id
    user_data[chat_id]["age"] = int(message.text)
    
    bot.send_message(chat_id, "Сколько книг хотите добавить?")
    bot.register_next_step_handler(message, get_books_count)


def get_books_count(message):
    chat_id = message.chat.id
    # простой счетчик количества оставшихся книг
    user_data[chat_id]["books_remaining"] = int(message.text)
    
    ask_next_book(message)


def ask_next_book(message):
    chat_id = message.chat.id
    count = len(user_data[chat_id]["books"]) + 1
    
    bot.send_message(chat_id, f"Введите название книги #{count}:")
    bot.register_next_step_handler(message, get_book_title)


def get_book_title(message):
    chat_id = message.chat.id
    user_data[chat_id]["temp_title"] = message.text
    
    bot.send_message(chat_id, "Введите год публикации:")
    bot.register_next_step_handler(message, get_book_year)


def get_book_year(message):
    chat_id = message.chat.id
    
    # добавляем книгу в общий список books
    user_data[chat_id]["books"].append({
        "title": user_data[chat_id]["temp_title"],
        "publishedYear": int(message.text)
    })
    user_data[chat_id]["books_remaining"] -= 1

    # проверка счетика оставшихся книг - если не ноль, то запрашиваем данные для книги
    if user_data[chat_id]["books_remaining"] > 0:
        ask_next_book(message)
    else:
        # если все собранно отправляем запрос
        send_post_request(message)

# запрос post
def send_post_request(message):
    chat_id = message.chat.id

    # создаем тело запроса (если не понятно как создается тело запроса - можно посмотреть на конечное,
    # на основе ответа get и строется тело запроса!!!!!)
    payload = {
        "name": user_data[chat_id]["name"],
        "age": user_data[chat_id]["age"],
        "books": user_data[chat_id]["books"]
    }

    bot.send_message(chat_id, "Отправляю POST-запрос на сервер...")
    url = "https://localhost:7003/authors"
    response = requests.post(url, json=payload, verify=False)

    # Ответ пользователю в чат (сырой Json)
    bot.send_message(chat_id, f"Статус: {response.status_code}\n\nОтвет сервера:\n{response.text}")
    
    # удаляем данные пользователя
    del user_data[chat_id]
# __________________________________________________________________________


# удаление автора (удаление только по id в БАЗЕ ДАННЫХ (на номер в /authorslist не смотреть, там встроенный счетчик))
@bot.message_handler(commands=["delete"])
def ask_author_id_for_delete(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Введите ID автора, которого нужно удалить:")
    bot.register_next_step_handler(message, process_delete_author)

def process_delete_author(message):
    chat_id = message.chat.id
    raw_id = (message.text or "").strip()

    # Простая проверка, что введено число
    if not raw_id.isdigit():
        bot.send_message(chat_id, "ID должен быть числом. Попробуйте снова: /delete")
        return

    author_id = int(raw_id)
    url = f"https://localhost:7003/authors/{author_id}"

    try:
        response = requests.delete(url, verify=False)

        if response.status_code in (200, 204):
            bot.send_message(chat_id, f"Автор с ID {author_id} успешно удален.")
        elif response.status_code == 404:
            bot.send_message(chat_id, f"Автор с ID {author_id} не найден.")
        else:
            bot.send_message(chat_id, f"Не удалось удалить. Ошибка сервера: {response.status_code}")
            
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при отправке запроса: {e}")


# __________________________________________________________________________
# изменение автора!
edit_data = {}

@bot.message_handler(commands=["edit"])
def start_edit_author(message):
    chat_id = message.chat.id
    edit_data[chat_id] = {}
    
    bot.send_message(chat_id, "Введите ID автора, данные которого хотите изменить:")
    bot.register_next_step_handler(message, get_edit_author_id)


def get_edit_author_id(message):
    chat_id = message.chat.id
    raw_id = (message.text or "").strip()

    if not raw_id.isdigit():
        bot.send_message(chat_id, "ID должен быть числом. Начните заново: /edit")
        del edit_data[chat_id]
        return

    edit_data[chat_id]["author_id"] = int(raw_id)
    bot.send_message(chat_id, "Введите новое имя автора:")
    bot.register_next_step_handler(message, get_edit_author_name)


def get_edit_author_name(message):
    chat_id = message.chat.id
    edit_data[chat_id]["name"] = message.text.strip()
    
    bot.send_message(chat_id, "Введите новый возраст автора:")
    bot.register_next_step_handler(message, get_edit_author_age)


def get_edit_author_age(message):
    chat_id = message.chat.id
    raw_age = message.text.strip()

    if not raw_age.isdigit():
        bot.send_message(chat_id, "Возраст должен быть числом. Начните заново: /edit")
        del edit_data[chat_id]
        return

    author_id = edit_data[chat_id]["author_id"]
    payload = {
        "name": edit_data[chat_id]["name"],
        "age": int(raw_age),
        "books": []
    }

    url = f"https://localhost:7003/authors/{author_id}"
    bot.send_message(chat_id, "Отправляю PUT-запрос...")

    try:
        response = requests.put(url, json=payload, verify=False)

        if response.status_code == 200:
            bot.send_message(chat_id, f"Автор с ID {author_id} успешно обновлен!")
        elif response.status_code == 404:
            bot.send_message(chat_id, f"Автор с ID {author_id} не найден на сервере.")
        elif response.status_code == 400:
            bot.send_message(chat_id, response.json()["message"])
        else:
            bot.send_message(chat_id, f"Ошибка сервера: {response.status_code}")
            
    except Exception as e:
        bot.send_message(chat_id, f"Не удалось выполнить запрос: {e}")
        
    finally:
        # Очищаем временную сессию
        edit_data.pop(chat_id, None)

bot.infinity_polling()