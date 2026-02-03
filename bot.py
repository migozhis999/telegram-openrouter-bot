import time
import requests
import os
import sqlite3
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    raise ValueError("Ошибка: переменная окружения BOT_TOKEN не задана!")
if not OPENROUTER_API_KEY:
    raise ValueError("Ошибка: переменная окружения OPENROUTER_API_KEY не задана!")

print("Переменные окружения успешно загружены!")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
trigger = "черкаш"
DB_FILE = "memory.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_history (
    chat_id TEXT PRIMARY KEY,
    history TEXT
)
""")
conn.commit()

def get_chat_history(chat_id):
    cursor.execute("SELECT history FROM chat_history WHERE chat_id=?", (str(chat_id),))
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])
    return []

def save_chat_history(chat_id, history):
    cursor.execute(
        "REPLACE INTO chat_history (chat_id, history) VALUES (?, ?)",
        (str(chat_id), json.dumps(history, ensure_ascii=False))
    )
    conn.commit()

def ask_openrouter(chat_id, prompt):
    history = get_chat_history(chat_id)
    history.append({"role": "user", "content": prompt})
    history = history[-10:]

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
    save_chat_history(chat_id, history)
    return reply

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    return requests.get(f"{TG_API}/getUpdates", params=params).json()

def send_message(chat_id, text):
    requests.post(f"{TG_API}/sendMessage", data={"chat_id": chat_id, "text": text})

def main():
    offset = None
    print("Бот с постоянной SQLite-памятью запущен...")

    while True:
        try:
            updates = get_updates(offset)
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                print("New update:", update)

                if "message" not in update:
                    continue

                message = update["message"]
                chat_id = message["chat"]["id"]
                text = message.get("text")
                if not text:
                    continue

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
            time.sleep(5)

if __name__ == "__main__":
    main()
