import time
import requests
import os

# Получаем токены из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Проверка, что переменные подставились
if not BOT_TOKEN:
    raise ValueError("Ошибка: переменная окружения BOT_TOKEN не задана!")
if not OPENROUTER_API_KEY:
    raise ValueError("Ошибка: переменная окружения OPENROUTER_API_KEY не задана!")

print("Переменные окружения успешно загружены!")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

chat_history = {}
trigger = "черкаш"  # слово-триггер для реакции бота

def ask_openrouter(chat_id, prompt):
    history = chat_history.get(chat_id, [])
    history.append({"role": "user", "content": prompt})
    history = history[-10:]  # оставляем последние 10 сообщений

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"model": "gpt-4o-mini", "messages": history}

    response = requests.post(url, headers=headers, json=data, timeout=60)
    response.raise_for_status()
    reply = response.json()["choices"][0]["message"]["content"]

    history.append({"role": "assistant", "content": reply})
    chat_history[chat_id] = history
    return reply

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return requests.get(f"{TG_API}/getUpdates", params=params).json()

def send_message(chat_id, text):
    requests.post(f"{TG_API}/sendMessage", data={"chat_id": chat_id, "text": text})

def main():
    offset = None  # сброс offset, чтобы бот подхватывал только новые сообщения
    print("Бот с триггером запущен...")

    while True:
        try:
            updates = get_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                print("New update:", update)  # отладка

                if "message" not in update:
                    continue

                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text")

                if not text:
                    continue

                # Проверяем триггер
                if trigger.lower() not in text.lower():
                    continue

                clean_text = text.lower().replace(trigger.lower(), "").strip()

                try:
                    reply = ask_openrouter(chat_id, clean_text)
                    send_message(chat_id, reply)
                except Exception as e:
                    print("ОШИБКА:", e)
                    send_message(chat_id, f"Ошибка: {e}")

            time.sleep(1)

        except Exception as e:
            print("Ошибка в основном цикле:", e)
            time.sleep(5)  # ждем перед новой попыткой

if __name__ == "__main__":
    main()
