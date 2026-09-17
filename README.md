## Declaración de Autoría, Diligencia y Uso de IA (Diligence Statement)

### 1. Propósito y Contexto del Proyecto
Este repositorio alberga un sistema integral de control financiero personal compuesto por tres componentes desacoplados:
* **Capa de Persistencia:** Base de datos relacional distribuida en Turso (libSQL).
* **Capa de Ingesta 24/7:** Bot de Telegram alojado en Render (Web Service Free Tier), mantenido en ejecución continua mediante monitorización periódica de salud (*keep-alive* con cron-job).
* **Capa Analítica y Visualización:** Dashboard interactivo en Streamlit Community Cloud con autenticación perimetral mediante PIN, diagnósticos de *pacing*, límite diario de rescate y comparativas macro anuales.

El desarrollo se realizó como un proyecto personal enfocado en optimizar la gestión económica individual y afianzar capacidades técnicas en la ejecución de proyectos multi-paso mediante colaboración Humano-IA.

### 2. Matriz de Delegación y Roles (Humano vs. IA)
El diseño e implementación del software se ejecutó siguiendo un marco estructurado de colaboración híbrida:

| Dimensión | Aporte y Supervisión Humana | Rol del Copiloto IA (Gemini) |
| :--- | :--- | :--- |
| **Arquitectura** | Definición de flujos de negocio, reglas de cálculo financiero y decisiones de pivote técnico ante restricciones de cuotas en plataformas cloud. | Propuesta de patrones estructurales, scaffolding de código y diseño modular de scripts (`bot.py` y `app.py`). |
| **Infraestructura** | Creación y administración de cuentas (Turso, Render, Streamlit Cloud, GitHub), vinculación de repositorios y despliegues. | Resolución de bloqueos de despliegue en capas gratuitas (implementación de micro-servidor HTTP interno para Render). |
| **Control de Calidad** | Auditoría y doble verificación manual de fórmulas de balance, proyecciones *run-rate* y límites diarios de gasto. | Generación de sintaxis para consultas parametrizadas en libSQL y visualización en Pandas/Streamlit. |

### 3. Privacidad, Seguridad y Gestión de Credenciales
* **Ofuscación Estricta:** Ningún dato transaccional real, saldo bancario ni identificador personal privado fue compartido con el modelo de lenguaje ni volcado en el historial de versiones de Git.
* **Aislamiento de Secretos:** Todas las credenciales críticas (`BOT_TOKEN`, `ALLOWED_USER_ID`, `TURSO_URL`, `TURSO_AUTH_TOKEN`, `DASHBOARD_PIN`) se gestionan de forma aislada mediante variables de entorno en Render, el gestor cifrado de Streamlit Secrets y `.streamlit/secrets.toml` en local, protegido mediante exclusión explícita en `.gitignore`.

### 4. Verificación y Responsabilidad Final
La integridad funcional y la exactitud matemática de cada métrica fueron comprobadas y validadas de primera mano mediante pruebas controladas en entorno local antes de la puesta en producción. El autor asume la titularidad completa del código, su mantenimiento futuro y la responsabilidad exclusiva sobre el uso del sistema.
