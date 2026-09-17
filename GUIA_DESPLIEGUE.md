# 🚀 Guía de Despliegue en 6 Pasos: Tu Gestor Financiero Personal

Esta guía te permitirá instalar tu propio sistema de control financiero privado, autónomo y 100% gratuito sin escribir código ni usar terminales.

---

### 📋 Antes de empezar: Tu "Libreta de Claves"
Abre un bloc de notas en tu ordenador. Durante los pasos guardarás estos 5 datos para usarlos al final:
1. `BOT_TOKEN`: Clave del bot de Telegram.
2. `ALLOWED_USER_ID`: Tu número de usuario en Telegram.
3. `TURSO_URL`: Dirección de tu base de datos privada.
4. `TURSO_AUTH_TOKEN`: Clave de tu base de datos.
5. `DASHBOARD_PIN`: Un código de 4 a 6 dígitos que tú elijas para entrar a tu web.

---

### Paso 1: Configurar Telegram (Tus llaves de acceso)
1. **Crear tu Bot:**
   * Entra en Telegram y busca a **`@BotFather`** (asegúrate de que tenga la insignia azul de verificación).
   * Pulsa **Iniciar** y escribe: `/newbot`.
   * Ponle un nombre visible a tu bot (ejemplo: *Mis Finanzas*).
   * Elige un nombre de usuario que termine obligatoriamente en `bot` (ejemplo: *mi_cartera_personal_bot*).
   * BotFather te responderá con un mensaje de felicitación que incluye un texto largo: el **Token**. Cópialo y guárdalo en tu libreta como `BOT_TOKEN`.
2. **Obtener tu Identificador Personal:**
   * Busca en Telegram el bot **`@userinfobot`** y pulsa **Iniciar**.
   * Te responderá con tu perfil. Copia el número que aparece en la línea **Id** (ejemplo: `123456789`) y guárdalo como `ALLOWED_USER_ID`.

---

### Paso 2: Crear tu Base de Datos Privada en Turso
Tus datos financieros se guardan en un almacén en la nube al que solo tú tienes acceso.
1. Entra en **[turso.tech](https://turso.tech)** y pulsa en **Sign Up / Get Started Free**. Regístrate con tu correo o cuenta de Google.
2. En el panel principal, haz clic en el botón **Create Database**.
3. Escribe un nombre simple (ejemplo: `finanzas`) y confirma la creación.
4. Una vez creada:
   * Copia la dirección que empieza por `libsql://...` y guárdala como `TURSO_URL`.
   * Pulsa en **Create Token** (o pestaña de claves), copia la clave extensa que genera y guárdala como `TURSO_AUTH_TOKEN`.

---

### Paso 3: Copiar el Proyecto en GitHub
1. Crea una cuenta gratuita en **[github.com](https://github.com)** si aún no la tienes.
2. Entra en el enlace del proyecto que te han compartido.
3. En la esquina superior derecha de la pantalla, pulsa el botón que dice **Fork**.
4. Deja las opciones tal como están y pulsa **Create fork**. Ahora tienes una copia privada y completa del sistema en tu propia cuenta.

---

### Paso 4: Poner el Bot en Marcha en Render
1. Entra en **[render.com](https://render.com)** y regístrate seleccionando la opción **Continue with GitHub**.
2. En tu panel de Render, pulsa el botón **New +** (arriba a la derecha) y selecciona **Web Service**.
3. Conecta el repositorio que acabas de copiar en el Paso 3 (*gestor-finanzas-bot*).
4. Configura los campos básicos:
   * **Name:** `mi-bot-finanzas` (o el nombre que prefieras).
   * **Runtime:** `Python 3`.
   * **Build Command:** `pip install -r requirements.txt`.
   * **Start Command:** `python bot.py`.
   * **Instance Type:** Selecciona la opción **Free**.
5. Baja hasta la sección **Environment Variables** (Variables de Entorno), pulsa **Add Environment Variable** e introduce las siguientes claves con los valores de tu libreta:
   * `PORT` $\rightarrow$ `8080`
   * `BOT_TOKEN` $\rightarrow$ *(Pega tu BOT_TOKEN del Paso 1)*
   * `ALLOWED_USER_ID` $\rightarrow$ *(Pega tu número de ID del Paso 1)*
   * `TURSO_URL` $\rightarrow$ *(Pega la URL de Turso del Paso 2)*
   * `TURSO_AUTH_TOKEN` $\rightarrow$ *(Pega el token de Turso del Paso 2)*
6. Pulsa **Create Web Service**. Espera unos 2 minutos hasta que aparezca una etiqueta verde que diga **Live**.
7. Copia la dirección web pública de tu servicio que aparece arriba a la izquierda (ejemplo: `https://mi-bot-finanzas.onrender.com`).

---

### Paso 5: Evitar que el Bot se Duerma (Cron-Job)
El servidor gratuito se apaga si pasa 15 minutos sin usarse. Un vigilante gratuito se encargará de enviarle un aviso para que responda siempre al instante:
1. Entra en **[cron-job.org](https://cron-job.org)** y crea una cuenta gratuita.
2. Pulsa en **Cronjobs** > **Create Cronjob**.
3. En **Title**, pon `Despertador Bot`.
4. En **URL**, pega la dirección web que copiaste en Render al final del Paso 4.
5. En **Execution schedule**, selecciona **Every 10 minutes** (Cada 10 minutos).
6. Pulsa **Create**. ¡Tu bot ya está activo 24 horas al día!

---

### Paso 6: Activar tu Panel de Control Web en Streamlit
1. Entra en **[share.streamlit.io](https://share.streamlit.io)** e inicia sesión con tu cuenta de GitHub.
2. Pulsa el botón **New app**.
3. Selecciona tu repositorio (*gestor-finanzas-bot*), deja la rama en `main` y en **Main file path** escribe `app.py`.
4. Pulsa en **Advanced settings...** y en la pestaña **Secrets** pega este texto sustituyendo los datos entre comillas por los de tu libreta:

```toml
TURSO_URL = "pega_aqui_tu_url_de_turso"
TURSO_AUTH_TOKEN = "pega_aqui_tu_token_de_turso"
DASHBOARD_PIN = "1234"
```
*(Cambia `1234` por el PIN numérico privado que tú elijas).*

5. Pulsa **Save** y después **Deploy!**.

---

### 🆘 Resolución Rápida de Problemas (Troubleshooting)

Si algo no funciona a la primera, localiza aquí el síntoma visual y aplica la solución en menos de un minuto:

#### 1. Le escribo `/start` a mi bot en Telegram y no responde nada
* **Causa más probable:** El bot no te reconoce porque el identificador numérico tiene algún error, o Render todavía está instalando el sistema.
* **Solución:**
  1. Ve a Render y comprueba que junto al nombre de tu servicio aparezca la etiqueta **Live** en verde (si pone *Building*, espera 1 minuto más).
  2. Comprueba en Telegram con `@userinfobot` que tu `ALLOWED_USER_ID` son **únicamente números** (no pongas tu arroba `@usuario`). Si estaba mal, corrígelo en las variables de Render y pulsa *Manual Deploy* > *Deploy latest commit*.

#### 2. La web de Streamlit muestra una pantalla roja con aviso de error de configuración
* **Causa más probable:** Falta alguna comilla en los secretos, la URL no empieza por `https://` o se copió un espacio en blanco por error.
* **Solución:**
  1. En Streamlit, entra en la barra lateral de configuración (tres puntos arriba a la derecha $\rightarrow$ **Settings** $\rightarrow$ pestaña **Secrets**).
  2. Asegúrate de que las tres líneas sigan exactamente este formato, con comillas al principio y al final de cada clave:
     ```toml
     TURSO_URL = "[https://tu-base-de-datos.turso.io](https://tu-base-de-datos.turso.io)"
     TURSO_AUTH_TOKEN = "tu_token_largo_sin_espacios"
     DASHBOARD_PIN = "1234"
     ```
  3. Comprueba que `TURSO_URL` empiece obligatoriamente por `https://` (si empieza por `libsql://`, cámbialo a `https://`). Guarda los cambios.

#### 3. El bot funcionó el primer día, pero al día siguiente deja de responder
* **Causa más probable:** El vigilante de Cron-Job no está logrando mantener el servidor activo.
* **Solución:**
  1. Entra en tu panel de **cron-job.org**.
  2. Revisa el historial de ejecuciones de tu tarea. Si aparece en rojo, verifica que la dirección web copiada sea exactamente la URL pública que te dio Render (ejemplo: `https://mi-bot-finanzas.onrender.com`).
  3. Puedes probar a pulsar el botón de prueba (*Test*) dentro de Cron-Job; debe devolver un mensaje que dice: `Bot 24/7 Activo y Saludable`.

#### 4. Error al consultar o registrar datos ("Database error" o error de conexión)
* **Causa más probable:** El token de Turso se copió incompleto o con un espacio accidental al principio o al final.
* **Solución:**
  1. Entra en tu panel de Turso, pulsa en tu base de datos y genera un nuevo token (*Create token*).
  2. Cópialo asegurándote de no arrastrar espacios en blanco y sustitúyelo en las variables de Render y en los secretos de Streamlit.

---

### 🎉 ¡Todo listo!
* **Para apuntar gastos o ingresos:** Abre Telegram, busca tu bot y pulsa `/start`.
* **Para ver gráficos y balances:** Entra al enlace de tu aplicación en Streamlit e introduce tu PIN.