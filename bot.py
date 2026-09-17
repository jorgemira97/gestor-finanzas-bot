# bot.py
import os
import logging
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import libsql_client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
TURSO_URL = os.getenv("TURSO_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------------------------------------------------------
# SERVIDOR WEB PARA HEALTH CHECK (RENDER FREE TIER)
# ---------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot activo 24/7")

    def log_message(self, format, *args):
        pass  # Silencia peticiones HTTP para mantener limpia la consola

def iniciar_servidor_web():
    servidor = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    servidor.serve_forever()

# ---------------------------------------------------------
# CONEXIÓN CON TURSO / LIBSQL
# ---------------------------------------------------------
def obtener_cliente_turso():
    url_limpia = TURSO_URL.strip().replace("libsql://", "https://").replace("wss://", "https://")
    return libsql_client.create_client_sync(
        url=url_limpia,
        auth_token=TURSO_AUTH_TOKEN.strip()
    )

def obtener_categorias():
    cliente = obtener_cliente_turso()
    try:
        res = cliente.execute("SELECT id, nombre, icono FROM categorias WHERE tipo = 'gasto' ORDER BY id ASC;")
        return [(fila[0], fila[1], fila[2]) for fila in res.rows]
    finally:
        cliente.close()

def guardar_transaccion(fecha_str, importe, categoria_id, descripcion=""):
    cliente = obtener_cliente_turso()
    try:
        cliente.execute(
            """
            INSERT INTO transacciones (fecha, importe, categoria_id, descripcion, origen)
            VALUES (?, ?, ?, ?, 'telegram_bot');
            """,
            [fecha_str, importe, categoria_id, descripcion]
        )
    finally:
        cliente.close()

# ---------------------------------------------------------
# SEGURIDAD PERIMETRAL
# ---------------------------------------------------------
async def usuario_autorizado(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER_ID:
        if update.message:
            await update.message.reply_text("⛔ No tienes autorización para usar este bot.")
        elif update.callback_query:
            await update.callback_query.answer("⛔ No autorizado.", show_alert=True)
        return False
    return True

# ---------------------------------------------------------
# COMANDOS Y FLUJO CONVERSACIONAL
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await usuario_autorizado(update):
        return
    await update.message.reply_text(
        "👋 ¡Hola! Envíame un importe para registrar un gasto (por ejemplo: `12.50` o `8.30 café`).",
        parse_mode="Markdown"
    )

async def manejar_mensaje_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await usuario_autorizado(update):
        return

    texto = update.message.text.strip().replace(",", ".")
    partes = texto.split(maxsplit=1)
    
    try:
        importe = float(partes[0])
        if importe <= 0:
            await update.message.reply_text("⚠️ El importe debe ser mayor que 0.")
            return
    except ValueError:
        await update.message.reply_text("⚠️ No reconocí un número válido al inicio del mensaje.")
        return

    descripcion = partes[1] if len(partes) > 1 else ""
    context.user_data["temp_gasto"] = {
        "importe": importe,
        "descripcion": descripcion
    }

    categorias = obtener_categorias()
    teclado = []
    fila = []
    for cid, nombre, icono in categorias:
        etiqueta = f"{icono} {nombre}" if icono else nombre
        fila.append(InlineKeyboardButton(etiqueta, callback_data=f"cat_{cid}"))
        if len(fila) == 2:
            teclado.append(fila)
            fila = []
    if fila:
        teclado.append(fila)

    reply_markup = InlineKeyboardMarkup(teclado)
    desc_txt = f" ({descripcion})" if descripcion else ""
    await update.message.reply_text(
        f"💶 Importe: *{importe:.2f} €*{desc_txt}\nSelecciona la categoría:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not await usuario_autorizado(update):
        return

    data = query.data

    if data.startswith("cat_"):
        cat_id = int(data.split("_")[1])
        context.user_data["temp_gasto"]["categoria_id"] = cat_id

        # Selector de fecha (Hoy, Ayer, Anteayer)
        hoy = datetime.now().date()
        ayer = hoy - timedelta(days=1)
        anteayer = hoy - timedelta(days=2)

        teclado_fechas = [
            [InlineKeyboardButton(f"Hoy ({hoy.strftime('%d/%m')})", callback_data=f"fecha_{hoy.isoformat()}")],
            [InlineKeyboardButton(f"Ayer ({ayer.strftime('%d/%m')})", callback_data=f"fecha_{ayer.isoformat()}")],
            [InlineKeyboardButton(f"Anteayer ({anteayer.strftime('%d/%m')})", callback_data=f"fecha_{anteayer.isoformat()}")]
        ]
        await query.edit_message_text(
            "📅 ¿En qué fecha se realizó el gasto?",
            reply_markup=InlineKeyboardMarkup(teclado_fechas)
        )

    elif data.startswith("fecha_"):
        fecha_str = data.split("_")[1]
        temp = context.user_data.get("temp_gasto")

        if not temp:
            await query.edit_message_text("⚠️ Sesión expirada. Vuelve a enviar el importe.")
            return

        guardar_transaccion(
            fecha_str=fecha_str,
            importe=temp["importe"],
            categoria_id=temp["categoria_id"],
            descripcion=temp.get("descripcion", "")
        )

        desc_txt = f" [{temp.get('descripcion')}]" if temp.get("descripcion") else ""
        await query.edit_message_text(
            f"✅ *Gasto registrado en Turso*\n"
            f"• Importe: {temp['importe']:.2f} €{desc_txt}\n"
            f"• Fecha: {fecha_str}",
            parse_mode="Markdown"
        )
        context.user_data.pop("temp_gasto", None)

def main():
    # Arrancar micro-servidor HTTP en un hilo independiente para Render
    hilo_web = threading.Thread(target=iniciar_servidor_web, daemon=True)
    hilo_web.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje_texto))
    app.add_handler(CallbackQueryHandler(manejar_callback))

    print("🤖 Bot conectado a Turso y en ejecución...")
    app.run_polling()

if __name__ == "__main__":
    main()