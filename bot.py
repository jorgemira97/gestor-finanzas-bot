import os
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
import libsql_client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# ---------------------------------------------------------
# VARIABLES DE ENTORNO
# ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID")
TURSO_URL = os.getenv("TURSO_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
PORT = int(os.getenv("PORT", "8080"))

# ---------------------------------------------------------
# MICRO-SERVIDOR HTTP PARA KEEP-ALIVE EN RENDER
# ---------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot 24/7 Activo y Saludable")

    def log_message(self, format, *args):
        pass  # Silenciar pings periódicos para mantener limpia la consola

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

# ---------------------------------------------------------
# CONEXIÓN A TURSO (LIBSQL)
# ---------------------------------------------------------
def get_turso_client():
    url_limpia = TURSO_URL.strip().replace("libsql://", "https://").replace("wss://", "https://")
    return libsql_client.create_client_sync(url=url_limpia, auth_token=TURSO_AUTH_TOKEN.strip())

def init_db():
    client = get_turso_client()
    try:
        # 1. Asegurar tabla de categorías
        client.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                icono TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('gasto', 'ingreso')),
                naturaleza TEXT NOT NULL CHECK(naturaleza IN ('fijo', 'variable'))
            );
        """)

        # 2. Asegurar tabla de transacciones
        client.execute("""
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                importe REAL NOT NULL,
                categoria_id INTEGER REFERENCES categorias(id),
                descripcion TEXT,
                origen TEXT DEFAULT 'telegram'
            );
        """)

        # 3. Sembrar categorías de GASTO si no existen
        res_gasto = client.execute("SELECT COUNT(*) FROM categorias WHERE tipo = 'gasto';")
        if res_gasto.rows[0][0] == 0:
            categorias_gasto = [
                ("Supermercado", "🛒", "gasto", "variable"),
                ("Restaurantes / Ocio", "🍽️", "gasto", "variable"),
                ("Vivienda / Alquiler", "🏠", "gasto", "fijo"),
                ("Suministros / Facturas", "💡", "gasto", "fijo"),
                ("Transporte / Gasolina", "🚗", "gasto", "variable"),
                ("Suscripciones", "📱", "gasto", "fijo"),
                ("Salud / Cuidado", "💊", "gasto", "variable"),
                ("Compras / Varios", "🛍️", "gasto", "variable")
            ]
            for nombre, icono, tipo, nat in categorias_gasto:
                client.execute("""
                    INSERT INTO categorias (nombre, icono, tipo, naturaleza)
                    VALUES (?, ?, ?, ?);
                """, [nombre, icono, tipo, nat])

        # 4. Sembrar categorías de INGRESO si no existen
        res_ingreso = client.execute("SELECT COUNT(*) FROM categorias WHERE tipo = 'ingreso';")
        if res_ingreso.rows[0][0] == 0:
            categorias_ingreso = [
                ("Nómina", "💼", "ingreso", "fijo"),
                ("Bizum / Transferencia", "📱", "ingreso", "variable"),
                ("Inversiones", "📈", "ingreso", "variable"),
                ("Otros Ingresos", "💰", "ingreso", "variable")
            ]
            for nombre, icono, tipo, nat in categorias_ingreso:
                client.execute("""
                    INSERT INTO categorias (nombre, icono, tipo, naturaleza)
                    VALUES (?, ?, ?, ?);
                """, [nombre, icono, tipo, nat])

    finally:
        client.close()

# ---------------------------------------------------------
# TECLADOS INLINE DE NAVEGACIÓN
# ---------------------------------------------------------
def teclado_acciones_base():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Añadir", callback_data="act_add"),
            InlineKeyboardButton("✏️ Editar", callback_data="act_edit"),
            InlineKeyboardButton("🗑️ Borrar", callback_data="act_del")
        ]
    ])

def teclado_fechas(prefix="dt"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Hoy", callback_data=f"{prefix}_hoy"),
            InlineKeyboardButton("Ayer", callback_data=f"{prefix}_ayer"),
            InlineKeyboardButton("📅 Otra fecha", callback_data=f"{prefix}_otra")
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")]
    ])

def obtener_teclado_categorias(tipo="gasto"):
    client = get_turso_client()
    try:
        res = client.execute("SELECT id, nombre, icono FROM categorias WHERE tipo = ? ORDER BY id ASC;", [tipo])
        botones = []
        fila = []
        for r in res.rows:
            fila.append(InlineKeyboardButton(f"{r[2]} {r[1]}", callback_data=f"cat_{r[0]}"))
            if len(fila) == 2:
                botones.append(fila)
                fila = []
        if fila:
            botones.append(fila)
        botones.append([InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")])
        return InlineKeyboardMarkup(botones)
    finally:
        client.close()

# ---------------------------------------------------------
# MANEJO DE COMANDOS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ALLOWED_USER_ID:
        return
    context.user_data.clear()
    await update.message.reply_text(
        "👋 **Gestor Financiero Personal Activo**\n\n"
        "Puedes escribir un importe directamente (ej: `12.50 Supermercado`) o usar las opciones:",
        reply_markup=teclado_acciones_base(),
        parse_mode="Markdown"
    )

# ---------------------------------------------------------
# GESTIÓN DE MENSAJES DE TEXTO
# ---------------------------------------------------------
async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ALLOWED_USER_ID:
        return

    texto = update.message.text.strip()
    modo = context.user_data.get("modo")

    # Caso A: Esperando fecha personalizada (DD/MM o DD/MM/AAAA)
    if modo in ["esperando_fecha_alta", "esperando_fecha_consulta"]:
        patron = r"^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?$"
        match = re.match(patron, texto)
        if not match:
            await update.message.reply_text("⚠️ Formato inválido. Escribe la fecha como `DD/MM/AAAA` o `DD/MM` (ej: `14/05/2026`):")
            return

        dia, mes, anio = match.groups()
        anio = anio if anio else str(datetime.now().year)
        fecha_parsed = f"{int(anio):04d}-{int(mes):02d}-{int(dia):02d}"

        if modo == "esperando_fecha_alta":
            context.user_data["fecha"] = fecha_parsed
            await finalizar_registro(update, context)
        else:
            context.user_data["modo"] = None
            await mostrar_movimientos_dia(update, context, fecha_parsed)
        return

    # Caso B: Esperando nuevo importe para editar
    if modo == "esperando_nuevo_importe":
        try:
            nuevo_imp = float(texto.replace(",", "."))
            tx_id = context.user_data.get("tx_id_editar")
            client = get_turso_client()
            try:
                client.execute("UPDATE transacciones SET importe = ? WHERE id = ?;", [nuevo_imp, tx_id])
            finally:
                client.close()

            context.user_data.clear()
            await update.message.reply_text(
                f"✅ **Importe actualizado a {nuevo_imp:.2f} €**",
                reply_markup=teclado_acciones_base(),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("⚠️ Introduce un número válido (ej: `14.90`):")
        return

    # Caso C: Ingesta rápida de transacción por texto tradicional
    patron_rapido = r"^([+-]?\d+(?:[\.,]\d{1,2})?)\s*(.*)$"
    match = re.match(patron_rapido, texto)
    if match:
        context.user_data.clear()
        importe = float(match.group(1).replace(",", "."))
        desc = match.group(2).strip()

        context.user_data["importe"] = abs(importe)
        context.user_data["desc"] = desc
        context.user_data["tipo"] = "ingreso" if importe < 0 or "ingreso" in desc.lower() else "gasto"

        await update.message.reply_text(
            f"Selecciona la categoría para **{abs(importe):.2f} €**:",
            reply_markup=obtener_teclado_categorias(context.user_data["tipo"]),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("¿Qué deseas realizar?", reply_markup=teclado_acciones_base())

# ---------------------------------------------------------
# GESTIÓN DE INTERACCIONES TÁCTILES (CALLBACKS)
# ---------------------------------------------------------
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if str(update.effective_user.id) != ALLOWED_USER_ID:
        return

    # Cancelar operación
    if data == "op_cancelar":
        context.user_data.clear()
        await query.edit_message_text("Operación cancelada.", reply_markup=teclado_acciones_base())
        return

    # 1. Menú Añadir
    if data == "act_add":
        teclado = InlineKeyboardMarkup([
            [InlineKeyboardButton("💶 Gasto", callback_data="alta_gasto"),
             InlineKeyboardButton("💼 Ingreso", callback_data="alta_ingreso")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")]
        ])
        await query.edit_message_text("¿Qué tipo de registro vas a incorporar?", reply_markup=teclado)
        return

    if data in ["alta_gasto", "alta_ingreso"]:
        context.user_data["tipo"] = "gasto" if data == "alta_gasto" else "ingreso"
        await query.edit_message_text("Escribe el importe por el chat (ej: `15.50` o `25 supermercado`):")
        return

    # 2. Selección de categoría tras definir importe o al cambiar de categoría
    if data.startswith("cat_"):
        cat_id = int(data.split("_")[1])
        if context.user_data.get("modo") == "cambiando_categoria":
            tx_id = context.user_data.get("tx_id_editar")
            client = get_turso_client()
            try:
                client.execute("UPDATE transacciones SET categoria_id = ? WHERE id = ?;", [cat_id, tx_id])
            finally:
                client.close()
            context.user_data.clear()
            await query.edit_message_text("✅ **Categoría actualizada con éxito.**", reply_markup=teclado_acciones_base(), parse_mode="Markdown")
            return

        context.user_data["cat_id"] = cat_id
        await query.edit_message_text("¿En qué fecha se realizó el movimiento?", reply_markup=teclado_fechas("dt"))
        return

    # 3. Asignación de fecha en alta
    if data.startswith("dt_"):
        opcion = data.split("_")[1]
        hoy = datetime.now()
        if opcion == "hoy":
            context.user_data["fecha"] = hoy.strftime("%Y-%m-%d")
            await finalizar_registro(query, context, via_callback=True)
        elif opcion == "ayer":
            context.user_data["fecha"] = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
            await finalizar_registro(query, context, via_callback=True)
        elif opcion == "otra":
            context.user_data["modo"] = "esperando_fecha_alta"
            await query.edit_message_text("Escribe la fecha por el chat con formato `DD/MM/AAAA` o `DD/MM`:")
        return

    # 4. Flujo de Edición / Borrado: Selección de día
    if data in ["act_edit", "act_del"]:
        context.user_data["accion_crud"] = "editar" if data == "act_edit" else "borrar"
        await query.edit_message_text("Selecciona el día de la transacción que deseas gestionar:", reply_markup=teclado_fechas("qry"))
        return

    if data.startswith("qry_"):
        opcion = data.split("_")[1]
        hoy = datetime.now()
        if opcion == "hoy":
            fecha = hoy.strftime("%Y-%m-%d")
            await mostrar_movimientos_dia(query, context, fecha, via_callback=True)
        elif opcion == "ayer":
            fecha = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
            await mostrar_movimientos_dia(query, context, fecha, via_callback=True)
        elif opcion == "otra":
            context.user_data["modo"] = "esperando_fecha_consulta"
            await query.edit_message_text("Escribe la fecha a consultar con formato `DD/MM/AAAA` o `DD/MM`:")
        return

    # 5. Selección de la transacción concreta
    if data.startswith("seltx_"):
        tx_id = int(data.split("_")[1])
        accion = context.user_data.get("accion_crud")

        if accion == "borrar":
            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚠️ Sí, Borrar definitivamente", callback_data=f"cfmdel_{tx_id}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")]
            ])
            await query.edit_message_text("¿Estás seguro de que deseas eliminar este registro de Turso?", reply_markup=teclado)
        else:
            context.user_data["tx_id_editar"] = tx_id
            teclado = InlineKeyboardMarkup([
                [InlineKeyboardButton("💵 Cambiar Importe", callback_data=f"edopt_imp_{tx_id}"),
                 InlineKeyboardButton("🏷️ Cambiar Categoría", callback_data=f"edopt_cat_{tx_id}")],
                [InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")]
            ])
            await query.edit_message_text("¿Qué parámetro deseas corregir?", reply_markup=teclado)
        return

    # 6. Ejecución del Borrado
    if data.startswith("cfmdel_"):
        tx_id = int(data.split("_")[1])
        client = get_turso_client()
        try:
            client.execute("DELETE FROM transacciones WHERE id = ?;", [tx_id])
        finally:
            client.close()
        context.user_data.clear()
        await query.edit_message_text("🗑️ **Transacción eliminada correctamente de Turso.**", reply_markup=teclado_acciones_base(), parse_mode="Markdown")
        return

    # 7. Bifurcación de Edición
    if data.startswith("edopt_"):
        _, campo, tx_id = data.split("_")
        context.user_data["tx_id_editar"] = int(tx_id)

        if campo == "imp":
            context.user_data["modo"] = "esperando_nuevo_importe"
            await query.edit_message_text("Escribe el nuevo importe numérico por el chat (ej: `18.50`):")
        elif campo == "cat":
            context.user_data["modo"] = "cambiando_categoria"
            client = get_turso_client()
            tipo_tx = "gasto"
            try:
                res = client.execute("""
                    SELECT COALESCE(c.tipo, 'gasto') 
                    FROM transacciones t 
                    LEFT JOIN categorias c ON t.categoria_id = c.id 
                    WHERE t.id = ?;
                """, [int(tx_id)])
                if res.rows:
                    tipo_tx = res.rows[0][0]
            finally:
                client.close()

            await query.edit_message_text("Elige la nueva categoría asignada:", reply_markup=obtener_teclado_categorias(tipo_tx))
        return

# ---------------------------------------------------------
# FUNCIONES AUXILIARES DE BASE DE DATOS
# ---------------------------------------------------------
async def finalizar_registro(target, context: ContextTypes.DEFAULT_TYPE, via_callback=False):
    datos = context.user_data
    client = get_turso_client()
    try:
        client.execute("""
            INSERT INTO transacciones (fecha, importe, categoria_id, descripcion, origen)
            VALUES (?, ?, ?, ?, 'telegram');
        """, [datos["fecha"], datos["importe"], datos["cat_id"], datos.get("desc", "")])
    finally:
        client.close()

    texto_salida = (
        f"✅ **Registro completado con éxito en Turso**\n\n"
        f"📅 Fecha: `{datos['fecha']}`\n"
        f"💰 Importe: `{datos['importe']:.2f} €`"
    )
    context.user_data.clear()

    if via_callback:
        await target.edit_message_text(texto_salida, reply_markup=teclado_acciones_base(), parse_mode="Markdown")
    else:
        await target.message.reply_text(texto_salida, reply_markup=teclado_acciones_base(), parse_mode="Markdown")

async def mostrar_movimientos_dia(target, context, fecha_str, via_callback=False):
    client = get_turso_client()
    filas = []
    try:
        res = client.execute("""
            SELECT t.id, t.importe, COALESCE(c.nombre, 'Sin categoría'), COALESCE(c.icono, '🏷️'), COALESCE(t.descripcion, '')
            FROM transacciones t
            LEFT JOIN categorias c ON t.categoria_id = c.id
            WHERE t.fecha = ?
            ORDER BY t.id DESC;
        """, [fecha_str])
        filas = res.rows
    finally:
        client.close()

    if not filas:
        msg = f"No hay movimientos registrados para el día `{fecha_str}`."
        if via_callback:
            await target.edit_message_text(msg, reply_markup=teclado_acciones_base(), parse_mode="Markdown")
        else:
            await target.message.reply_text(msg, reply_markup=teclado_acciones_base(), parse_mode="Markdown")
        return

    botones = []
    for r in filas:
        desc_txt = f" - {r[4]}" if r[4] else ""
        etiqueta = f"{r[3]} {r[1]:.2f}€ ({r[2]}{desc_txt})"
        botones.append([InlineKeyboardButton(etiqueta, callback_data=f"seltx_{r[0]}")])
    botones.append([InlineKeyboardButton("❌ Cancelar", callback_data="op_cancelar")])

    accion = context.user_data.get("accion_crud", "gestionar")
    msg = f"Selecciona la operación que deseas **{accion}** del `{fecha_str}`:"

    if via_callback:
        await target.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")
    else:
        await target.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(botones), parse_mode="Markdown")

# ---------------------------------------------------------
# ARRANQUE PRINCIPAL
# ---------------------------------------------------------
def main():
    init_db()

    # Micro-servidor en hilo secundario para mantener activo Render
    t = threading.Thread(target=run_http_server, daemon=True)
    t.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manejar_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()