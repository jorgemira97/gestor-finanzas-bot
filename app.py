import os
import calendar
import pandas as pd
import streamlit as st
import libsql_client
from datetime import datetime, timedelta, date

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="💰",
    layout="wide"
)

# ---------------------------------------------------------
# OBTENCIÓN DE SECRETOS (ARQUITECTURA FAIL-CLOSED)
# ---------------------------------------------------------
def get_secret(key):
    """Recupera secretos sin valores por defecto inseguros."""
    if key in st.secrets:
        return st.secrets[key]
    val = os.getenv(key)
    return val if val else None

TURSO_URL = get_secret("TURSO_URL")
TURSO_AUTH_TOKEN = get_secret("TURSO_AUTH_TOKEN")
RAW_PIN = get_secret("DASHBOARD_PIN")

if not TURSO_URL or not TURSO_AUTH_TOKEN or not RAW_PIN:
    st.error("🚨 **Error de Configuración:** Faltan credenciales del sistema. Acceso revocado por seguridad.")
    st.stop()

DASHBOARD_PIN = str(RAW_PIN).strip()

# ---------------------------------------------------------
# CONTROL DE ACCESO (PIN DE SEGURIDAD)
# ---------------------------------------------------------
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("## 🔐 Acceso Restringido")
        st.markdown("Introduce tu código PIN para acceder al control financiero.")
        pin_input = st.text_input("Código PIN", type="password", max_chars=8)
        
        if st.button("Desbloquear Dashboard", use_container_width=True):
            if pin_input == DASHBOARD_PIN:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("PIN incorrecto. Acceso denegado.")
    st.stop()

# ---------------------------------------------------------
# CONEXIÓN Y CONSULTAS A TURSO (LIBSQL)
# ---------------------------------------------------------
def formato_eur(valor):
    if valor is None or pd.isna(valor):
        valor = 0.0
    return f"{float(valor):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

def obtener_cliente_turso():
    url_limpia = TURSO_URL.strip().replace("libsql://", "https://").replace("wss://", "https://")
    return libsql_client.create_client_sync(
        url=url_limpia,
        auth_token=TURSO_AUTH_TOKEN.strip()
    )

def consultar_df(query, params=None):
    cliente = obtener_cliente_turso()
    try:
        res = cliente.execute(query, params or [])
        df = pd.DataFrame(res.rows, columns=res.columns)
        if "importe" in df.columns:
            df["importe"] = pd.to_numeric(df["importe"], errors="coerce").fillna(0.0)
        return df
    finally:
        cliente.close()

def cargar_metas_mes(mes_anio):
    cliente = obtener_cliente_turso()
    try:
        cliente.execute("""
            CREATE TABLE IF NOT EXISTS metas_mensuales (
                mes_anio TEXT PRIMARY KEY,
                techo_gastos_fijos REAL DEFAULT 0,
                techo_gastos_variables REAL DEFAULT 0,
                objetivo_ahorro REAL DEFAULT 0,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        res = cliente.execute("""
            SELECT techo_gastos_fijos, techo_gastos_variables, objetivo_ahorro
            FROM metas_mensuales WHERE mes_anio = ?;
        """, [mes_anio])
        if res.rows:
            fila = res.rows[0]
            return {
                "techo_fijo": float(fila[0] or 0.0),
                "techo_variable": float(fila[1] or 0.0),
                "objetivo_ahorro": float(fila[2] or 0.0)
            }
        return {"techo_fijo": 0.0, "techo_variable": 0.0, "objetivo_ahorro": 0.0}
    except Exception:
        return {"techo_fijo": 0.0, "techo_variable": 0.0, "objetivo_ahorro": 0.0}
    finally:
        cliente.close()

def guardar_metas_mes(mes_anio, techo_fijo, techo_var, obj_ahorro):
    cliente = obtener_cliente_turso()
    try:
        cliente.execute("""
            CREATE TABLE IF NOT EXISTS metas_mensuales (
                mes_anio TEXT PRIMARY KEY,
                techo_gastos_fijos REAL DEFAULT 0,
                techo_gastos_variables REAL DEFAULT 0,
                objetivo_ahorro REAL DEFAULT 0,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cliente.execute("""
            INSERT INTO metas_mensuales (mes_anio, techo_gastos_fijos, techo_gastos_variables, objetivo_ahorro)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mes_anio) DO UPDATE SET
                techo_gastos_fijos = excluded.techo_gastos_fijos,
                techo_gastos_variables = excluded.techo_gastos_variables,
                objetivo_ahorro = excluded.objetivo_ahorro,
                actualizado_en = CURRENT_TIMESTAMP;
        """, [mes_anio, techo_fijo, techo_var, obj_ahorro])
    finally:
        cliente.close()

def cargar_meta_anual(anio_str):
    cliente = obtener_cliente_turso()
    try:
        cliente.execute("""
            CREATE TABLE IF NOT EXISTS metas_anuales (
                anio TEXT PRIMARY KEY,
                objetivo_ahorro REAL DEFAULT 0,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        res = cliente.execute("SELECT objetivo_ahorro FROM metas_anuales WHERE anio = ?;", [str(anio_str)])
        if res.rows:
            return float(res.rows[0][0] or 0.0)
        return 0.0
    except Exception:
        return 0.0
    finally:
        cliente.close()

def guardar_meta_anual(anio_str, obj_ahorro):
    cliente = obtener_cliente_turso()
    try:
        cliente.execute("""
            CREATE TABLE IF NOT EXISTS metas_anuales (
                anio TEXT PRIMARY KEY,
                objetivo_ahorro REAL DEFAULT 0,
                actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cliente.execute("""
            INSERT INTO metas_anuales (anio, objetivo_ahorro)
            VALUES (?, ?)
            ON CONFLICT(anio) DO UPDATE SET
                objetivo_ahorro = excluded.objetivo_ahorro,
                actualizado_en = CURRENT_TIMESTAMP;
        """, [str(anio_str), float(obj_ahorro)])
    finally:
        cliente.close()

def cargar_datos_mes(mes_anio):
    query = """
        SELECT 
            t.id, t.fecha, t.importe,
            COALESCE(c.nombre, 'Sin categoría') AS categoria,
            COALESCE(c.tipo, 'gasto') AS tipo,
            COALESCE(c.naturaleza, 'variable') AS naturaleza,
            COALESCE(c.icono, '🏷️') AS icono,
            t.descripcion, t.origen
        FROM transacciones t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE strftime('%Y-%m', t.fecha) = ?
        ORDER BY t.fecha DESC, t.id DESC;
    """
    return consultar_df(query, [mes_anio])

def cargar_datos_anio(anio_str):
    query = """
        SELECT 
            t.id, t.fecha, t.importe,
            COALESCE(c.nombre, 'Sin categoría') AS categoria,
            COALESCE(c.tipo, 'gasto') AS tipo,
            COALESCE(c.naturaleza, 'variable') AS naturaleza,
            COALESCE(c.icono, '🏷️') AS icono
        FROM transacciones t
        LEFT JOIN categorias c ON t.categoria_id = c.id
        WHERE strftime('%Y', t.fecha) = ?
        ORDER BY t.fecha ASC;
    """
    return consultar_df(query, [anio_str])

# ---------------------------------------------------------
# GESTIÓN DEL ESTADO TEMPORAL
# ---------------------------------------------------------
hoy = datetime.now()
mes_actual_str = hoy.strftime("%Y-%m")

df_meses_db = consultar_df("SELECT DISTINCT strftime('%Y-%m', fecha) AS mes FROM transacciones WHERE fecha IS NOT NULL ORDER BY mes DESC;")
lista_meses = [m for m in df_meses_db["mes"].dropna().tolist() if m]
if mes_actual_str not in lista_meses:
    lista_meses.insert(0, mes_actual_str)

if "mes_operativo" not in st.session_state:
    st.session_state.mes_operativo = lista_meses[0]
elif st.session_state.mes_operativo not in lista_meses:
    st.session_state.mes_operativo = lista_meses[0]

mes_seleccionado = st.session_state.mes_operativo
anio_seleccionado = mes_seleccionado.split("-")[0]

# ---------------------------------------------------------
# BARRA LATERAL (TECHOS DEL MES SELECCIONADO)
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración de Techos")
metas = cargar_metas_mes(mes_seleccionado)

st.sidebar.subheader(f"🎯 Techos de {mes_seleccionado} (€)")
nuevo_techo_fijo = st.sidebar.number_input("Techo Fijo (€):", min_value=0.0, value=float(metas["techo_fijo"]), step=50.0)
nuevo_techo_var = st.sidebar.number_input("Techo Variable (€):", min_value=0.0, value=float(metas["techo_variable"]), step=50.0)
nuevo_obj_ahorro = st.sidebar.number_input("Objetivo Ahorro (€):", min_value=0.0, value=float(metas["objetivo_ahorro"]), step=50.0)

if st.sidebar.button("💾 Guardar Techos del Mes", use_container_width=True):
    guardar_metas_mes(mes_seleccionado, nuevo_techo_fijo, nuevo_techo_var, nuevo_obj_ahorro)
    st.sidebar.success("¡Techos actualizados en Turso!")
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

# ---------------------------------------------------------
# ESTRUCTURA EN PESTAÑAS
# ---------------------------------------------------------
tab_mensual, tab_anual = st.tabs(["📅 Control Mensual Operativo", "📈 Visión Anual Macro"])

# =========================================================
# PESTAÑA 1: CONTROL MENSUAL
# =========================================================
with tab_mensual:
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.title(f"📊 Panel Operativo — {mes_seleccionado}")
    with col_m2:
        mes_elegido = st.selectbox(
            "📅 Mes:",
            options=lista_meses,
            index=lista_meses.index(mes_seleccionado),
            key="sb_mes_cabecera"
        )
        if mes_elegido != st.session_state.mes_operativo:
            st.session_state.mes_operativo = mes_elegido
            st.rerun()
    
    df_mes = cargar_datos_mes(mes_seleccionado)
    
    ingresos_m = df_mes[df_mes["tipo"] == "ingreso"]["importe"].sum() if not df_mes.empty else 0.0
    fijos_m = df_mes[(df_mes["tipo"] == "gasto") & (df_mes["naturaleza"] == "fijo")]["importe"].sum() if not df_mes.empty else 0.0
    variables_m = df_mes[(df_mes["tipo"] == "gasto") & (df_mes["naturaleza"] == "variable")]["importe"].sum() if not df_mes.empty else 0.0
    gastos_m = fijos_m + variables_m
    balance_m = ingresos_m - gastos_m
    tasa_ahorro_m = (balance_m / ingresos_m * 100) if ingresos_m > 0 else 0.0

    # Scorecards Mensuales
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💼 Ingresos", formato_eur(ingresos_m))
    c2.metric("🏠 Gastos Fijos", formato_eur(fijos_m), delta=f"Techo: {metas['techo_fijo']:,.0f} €" if metas['techo_fijo'] > 0 else None, delta_color="inverse")
    c3.metric("🍽️ Gastos Variables", formato_eur(variables_m), delta=f"Techo: {metas['techo_variable']:,.0f} €" if metas['techo_variable'] > 0 else None, delta_color="inverse")
    c4.metric("📈 Balance Neto", formato_eur(balance_m))
    c5.metric("🎯 Tasa Ahorro", f"{tasa_ahorro_m:.1f}%", delta=f"Meta: {metas['objetivo_ahorro']:,.0f} €" if metas['objetivo_ahorro'] > 0 else None)

    st.divider()

    # Diagnóstico dinámico (Pacing y Límite de Rescate)
    try:
        a_int, m_int = map(int, mes_seleccionado.split("-"))
        _, dias_tot_m = calendar.monthrange(a_int, m_int)
        dia_ref = hoy.day if mes_seleccionado == mes_actual_str else dias_tot_m
        dias_rest = max(1, dias_tot_m - dia_ref + 1)
    except Exception:
        dias_tot_m, dia_ref, dias_rest = 30, 15, 15

    techo_v = metas["techo_variable"]
    diferencia_var = techo_v - variables_m
    meta_ahorro = metas["objetivo_ahorro"]

    margen_meta_ahorro = max(0.0, balance_m - meta_ahorro) if meta_ahorro > 0 else balance_m
    diario_rescate = margen_meta_ahorro / dias_rest

    gasto_proy = fijos_m + ((variables_m / dia_ref) * dias_tot_m if dia_ref > 0 else 0.0)
    balance_proy = ingresos_m - gasto_proy
    brecha = meta_ahorro - balance_proy

    r1, r2, r3 = st.columns(3)

    with r1:
        if techo_v > 0:
            if diferencia_var >= 0:
                st.info(f"📅 **Días restantes:** {dias_rest} de {dias_tot_m}\n\nMargen en techo variable: **{formato_eur(diferencia_var)}**")
            else:
                st.warning(f"📅 **Días restantes:** {dias_rest} de {dias_tot_m}\n\n⚠️ **Techo variable agotado:** Rebasado por **{formato_eur(abs(diferencia_var))}**.")
        else:
            st.info(f"📅 **Días restantes:** {dias_rest} de {dias_tot_m}")

    with r2:
        if techo_v > 0 and diferencia_var >= 0:
            diario_sug = diferencia_var / dias_rest
            st.metric("💳 Límite Diario Recomendado", formato_eur(diario_sug))
            st.caption(f"Semana (próximos 7 días): **{formato_eur(diario_sug * min(7, dias_rest))}**")
        elif meta_ahorro > 0 and margen_meta_ahorro > 0:
            st.metric("🛡️ Límite Diario de Rescate", formato_eur(diario_rescate))
            st.caption(f"Margen diario para no incumplir tu meta de ahorro ({formato_eur(meta_ahorro)}).")
        else:
            st.error("🚨 Sin margen diario disponible.")
            st.caption("Cualquier gasto adicional incrementará el déficit respecto a tu meta de ahorro.")

    with r3:
        if meta_ahorro > 0 and ingresos_m > 0:
            if brecha > 0:
                st.error(f"⚠️ **Déficit proyectado:**\n\nAl ritmo actual, faltarán **{formato_eur(brecha)}** para tu meta.")
            else:
                st.success(f"✅ **Ahorro en ruta:**\n\nProyectas superar la meta por **{formato_eur(abs(brecha))}**.")
        else:
            st.info("Indica meta de ahorro e ingresos para proyectar el resultado.")

    st.divider()

    col_g, col_t = st.columns([1, 1])
    with col_g:
        st.subheader("📊 Gastos por Categoría")
        g_df = df_mes[df_mes["tipo"] == "gasto"]
        if not g_df.empty:
            cat_sum = g_df.groupby("categoria")["importe"].sum().sort_values(ascending=False)
            st.bar_chart(cat_sum)
        else:
            st.info("Sin gastos registrados este mes.")
    with col_t:
        st.subheader("📋 Movimientos")
        if not df_mes.empty:
            v_df = df_mes[["fecha", "icono", "categoria", "importe", "descripcion"]].copy()
            v_df["importe"] = v_df["importe"].apply(formato_eur)
            v_df.columns = ["Fecha", "Icono", "Categoría", "Importe", "Nota"]
            st.dataframe(v_df, use_container_width=True, hide_index=True)
        else:
            st.info("Sin movimientos este mes.")

# =========================================================
# PESTAÑA 2: VISIÓN ANUAL MACRO
# =========================================================
with tab_anual:
    df_anios_db = consultar_df("SELECT DISTINCT strftime('%Y', fecha) AS anio FROM transacciones WHERE fecha IS NOT NULL;")
    anios_db = [fila for fila in df_anios_db["anio"].dropna().tolist() if fila]
    
    anio_actual_str = str(datetime.now().year)
    lista_anios = sorted(list(set(anios_db + [anio_actual_str])), reverse=True)
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.title("📈 Análisis Anual y Evolutivo")
    with col_t2:
        anio_elegido = st.selectbox("📅 Año:", options=lista_anios, index=0)

    # Cargar datos y meta anual
    df_anio = cargar_datos_anio(anio_elegido)
    meta_anual = cargar_meta_anual(anio_elegido)
    
    ingresos_a = df_anio[df_anio["tipo"] == "ingreso"]["importe"].sum() if not df_anio.empty else 0.0
    gastos_fijos_a = df_anio[(df_anio["tipo"] == "gasto") & (df_anio["naturaleza"] == "fijo")]["importe"].sum() if not df_anio.empty else 0.0
    gastos_var_a = df_anio[(df_anio["tipo"] == "gasto") & (df_anio["naturaleza"] == "variable")]["importe"].sum() if not df_anio.empty else 0.0
    gastos_tot_a = gastos_fijos_a + gastos_var_a
    balance_a = ingresos_a - gastos_tot_a
    tasa_ahorro_a = (balance_a / ingresos_a * 100) if ingresos_a > 0 else 0.0

    meses_con_datos = max(1, df_anio["fecha"].apply(lambda x: str(x)[:7]).nunique()) if not df_anio.empty else 1
    media_gasto_mensual = gastos_tot_a / meses_con_datos

    # Scorecards Anuales
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("💼 Ingresos Anuales", formato_eur(ingresos_a))
    m2.metric("🏠 Gasto Fijo Acumulado", formato_eur(gastos_fijos_a))
    m3.metric("🍽️ Gasto Variable Acumulado", formato_eur(gastos_var_a))
    m4.metric("💰 Ahorro Neto Anual", formato_eur(balance_a), delta=f"Meta: {meta_anual:,.0f} €" if meta_anual > 0 else None)
    m5.metric("📊 Gasto Medio / Mes", formato_eur(media_gasto_mensual))

    # Configuración de la Meta Anual (Expander)
    with st.expander("🎯 Configuración de Meta Anual"):
        col_em1, col_em2 = st.columns([3, 1])
        with col_em1:
            nuevo_obj_anual = st.number_input(
                f"Objetivo de Ahorro para el año {anio_elegido} (€):",
                min_value=0.0,
                value=float(meta_anual),
                step=100.0,
                key=f"input_meta_anual_{anio_elegido}"
            )
        with col_em2:
            st.write("")
            st.write("")
            if st.button("💾 Guardar Meta Anual", use_container_width=True):
                guardar_meta_anual(anio_elegido, nuevo_obj_anual)
                st.success("¡Meta anual actualizada en Turso!")
                st.rerun()

    # Panel de Diagnóstico y Proyección Anual
    if meta_anual > 0:
        st.markdown("#### 🧭 Proyección de Consecución de Meta")
        
        # Determinar fecha base según la primera transacción registrada del año
        if not df_anio.empty:
            fecha_min_str = df_anio["fecha"].min()
            fecha_min = datetime.strptime(str(fecha_min_str)[:10], "%Y-%m-%d").date()
        else:
            fecha_min = hoy.date()

        fecha_ref = hoy.date() if str(hoy.year) == str(anio_elegido) else date(int(anio_elegido), 12, 31)
        dias_operativos = max(1, (fecha_ref - fecha_min).days + 1)

        if balance_a >= meta_anual:
            st.success(f"🎉 **¡Objetivo Cumplido!** Has superado el objetivo anual de {formato_eur(meta_anual)} (Superávit: {formato_eur(balance_a - meta_anual)}).")
        elif balance_a <= 0:
            st.error("🚨 **Ritmo deficitario o nulo:** Imposible proyectar fecha de consecución sin superávit acumulado.")
        else:
            ritmo_diario = balance_a / dias_operativos
            ahorro_restante = meta_anual - balance_a
            dias_necesarios = int(ahorro_restante / ritmo_diario)
            fecha_proyectada = fecha_ref + timedelta(days=dias_necesarios)

            meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            f_texto = f"{fecha_proyectada.day} de {meses_es[fecha_proyectada.month - 1]} de {fecha_proyectada.year}"

            p1, p2, p3 = st.columns(3)
            p1.metric("⚡ Ritmo de Ahorro", f"{formato_eur(ritmo_diario)} / día", help=f"Basado en {dias_operativos} días operativos reales en {anio_elegido}.")
            p2.metric("🎯 Margen Faltante", formato_eur(ahorro_restante))
            p3.metric("📅 Fecha Proyectada", f"{fecha_proyectada.strftime('%d/%m/%Y')}")

            if fecha_proyectada.year == int(anio_elegido):
                st.info(f"🚀 Al ritmo actual, alcanzarás la meta dentro de este año el **{f_texto}** (en aprox. {dias_necesarios} días).")
            else:
                st.warning(f"⏳ Al ritmo actual, la meta se alcanzará en el siguiente ciclo: el **{f_texto}** (en aprox. {dias_necesarios} días).")

    st.divider()

    # Gráficos evolutivos
    st.subheader("📉 Evolución Temporal del Gasto")
    selector_periodo = st.radio(
        "Escala temporal del gasto:",
        options=["Últimos 7 Días (Semana)", "Día a Día del Mes Seleccionado", "Mes a Mes (Año Completo)"],
        horizontal=True
    )

    df_gastos_todos = df_anio[df_anio["tipo"] == "gasto"].copy()

    if selector_periodo == "Últimos 7 Días (Semana)":
        fecha_hace_7 = (hoy - timedelta(days=6)).strftime("%Y-%m-%d")
        df_sem = df_gastos_todos[df_gastos_todos["fecha"] >= fecha_hace_7]
        dias_rango = [(hoy - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]
        serie_sem = df_sem.groupby("fecha")["importe"].sum().reindex(dias_rango, fill_value=0.0)
        st.line_chart(serie_sem)

    elif selector_periodo == "Día a Día del Mes Seleccionado":
        df_mes_gastos = df_mes[df_mes["tipo"] == "gasto"].copy()
        if not df_mes_gastos.empty:
            a_int, m_int = map(int, mes_seleccionado.split("-"))
            _, dias_en_m = calendar.monthrange(a_int, m_int)
            dias_del_mes = [f"{mes_seleccionado}-{d:02d}" for d in range(1, dias_en_m + 1)]
            serie_mes = df_mes_gastos.groupby("fecha")["importe"].sum().reindex(dias_del_mes, fill_value=0.0)
            st.area_chart(serie_mes)
        else:
            st.info("Sin registros de gastos para el mes seleccionado.")

    elif selector_periodo == "Mes a Mes (Año Completo)":
        if not df_gastos_todos.empty:
            df_gastos_todos["mes"] = df_gastos_todos["fecha"].apply(lambda x: str(x)[:7])
            meses_anio = [f"{anio_elegido}-{m:02d}" for m in range(1, 13)]
            serie_anio = df_gastos_todos.groupby("mes")["importe"].sum().reindex(meses_anio, fill_value=0.0)
            st.bar_chart(serie_anio)
        else:
            st.info("Sin registros de gastos en el año.")

    st.divider()

    st.subheader("💰 Evolución del Ahorro Anual")
    meses_completos = [f"{anio_elegido}-{m:02d}" for m in range(1, 13)]
    
    df_ing_a = df_anio[df_anio["tipo"] == "ingreso"].copy()
    if not df_ing_a.empty:
        df_ing_a["mes"] = df_ing_a["fecha"].apply(lambda x: str(x)[:7])
        s_ing = df_ing_a.groupby("mes")["importe"].sum()
    else:
        s_ing = pd.Series(0.0, index=meses_completos)
        
    df_gas_a = df_anio[df_anio["tipo"] == "gasto"].copy()
    if not df_gas_a.empty:
        df_gas_a["mes"] = df_gas_a["fecha"].apply(lambda x: str(x)[:7])
        s_gas = df_gas_a.groupby("mes")["importe"].sum()
    else:
        s_gas = pd.Series(0.0, index=meses_completos)

    matriz_ahorro = pd.DataFrame(index=meses_completos)
    matriz_ahorro["Ingresos"] = s_ing.reindex(meses_completos, fill_value=0.0)
    matriz_ahorro["Gastos"] = s_gas.reindex(meses_completos, fill_value=0.0)
    matriz_ahorro["Ahorro Neto Mensual"] = matriz_ahorro["Ingresos"] - matriz_ahorro["Gastos"]
    matriz_ahorro["Ahorro Acumulado"] = matriz_ahorro["Ahorro Neto Mensual"].cumsum()

    selector_ahorro = st.radio(
        "Perspectiva de ahorro:",
        options=["Ahorro Acumulado (Progresión del Colchón)", "Ahorro Neto Mensual (Superávit/Déficit por Mes)"],
        horizontal=True
    )

    if selector_ahorro == "Ahorro Acumulado (Progresión del Colchón)":
        st.area_chart(matriz_ahorro[["Ahorro Acumulado"]])
        st.caption("📈 Representa el volumen total neto acumulado a lo largo de los meses transcurridos del año.")
    else:
        st.area_chart(matriz_ahorro[["Ahorro Neto Mensual"]])
        st.caption("📊 Representa el margen libre generado individualmente en cada mes.")