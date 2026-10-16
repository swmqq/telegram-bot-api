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
    parts = message.text.split()

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

bot.infinity_polling()