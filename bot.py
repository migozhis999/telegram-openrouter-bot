import time
import requests

BOT_TOKEN = "8500307111:AAF5hJILHfPSlltwvBtdiFgq-Icuy_Zp6dU"
OPENROUTER_API_KEY = "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"

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

chat_history = {}
trigger = "черкаш"  # измените на любое слово, по которому бот будет реагировать

def ask_openrouter(chat_id, prompt):
    history = chat_history.get(chat_id, [])
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
    chat_history[chat_id] = history
    return reply

def get_updates(offset):
    return requests.get(f"{TG_API}/getUpdates", params={"timeout": 30, "offset": offset}).json()

def send_message(chat_id, text):
    requests.post(f"{TG_API}/sendMessage", data={"chat_id": chat_id, "text": text})

def main():
    offset = 0
    print("Бот с триггером запущен...")
    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text")

            if not text:
                continue

            # Проверяем наличие триггера
            if trigger.lower() not in text.lower():
                continue  # игнорируем, если триггер не найден

            # Убираем триггер из текста перед отправкой в OpenRouter
            clean_text = text.lower().replace(trigger.lower(), "").strip()

            try:
                reply = ask_openrouter(chat_id, clean_text)
                send_message(chat_id, reply)
            except Exception as e:
                print("ОШИБКА:", e)
                send_message(chat_id, f"Ошибка: {e}")

        time.sleep(1)

if __name__ == "__main__":
    main()
