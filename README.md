## Declaración de Autoría, Diligencia y Uso de IA (Diligence Statement)

### 1. Propósito y Contexto del Proyecto
Este repositorio alberga un sistema integral de control financiero personal (v2.0) compuesto por tres capas desacopladas y diseñadas para operar con cero fricción:
* **Capa de Persistencia:** Base de datos relacional distribuida en Turso (libSQL), estructurada con modelos relacionales para transacciones, categorización tipificada (gastos/ingresos con naturaleza fija/variable) y seguimiento de techos mensuales y metas anuales (`metas_mensuales` y `metas_anuales`).
* **Capa de Ingesta y Gestión 24/7 (Telegram):** Bot alojado en Render (Web Service Free Tier) mantenido activo de forma continua mediante un micro-servidor HTTP interno y monitorización periódica (*keep-alive* con cron-job). Integra una interfaz táctil CRUD completa con botoneras interactivas (*inline keyboards*) para registrar ingresos y gastos clasificados, modificar importes o categorías, eliminar registros con confirmación de seguridad y seleccionar fechas retrospectivas («📅 Otra fecha»).
* **Capa Analítica y Visualización (Dashboard):** Panel interactivo en Streamlit Community Cloud protegido mediante autenticación perimetral estricta (*fail-closed* sin valores por defecto públicos), cabecera simétrica con selector temporal directo, diagnóstico dinámico de *pacing*, límite diario de rescate y un motor de proyección anual libre de topes artificiales de calendario.

El proyecto fue concebido y ejecutado con el doble propósito de gestionar de forma autónoma la economía individual y afianzar competencias prácticas en la dirección y supervisión de desarrollo de software multi-paso en colaboración Humano-IA.

### 2. Matriz de Delegación y Roles (Humano vs. IA)
El desarrollo y la evolución hacia la versión 2.0 se articularon bajo el siguiente reparto de funciones:

| Dimensión | Aporte y Supervisión Humana | Rol del Copiloto IA (Gemini) |
| :--- | :--- | :--- |
| **Arquitectura y Negocio** | Definición de flujos CRUD, reglas de *pacing*, criterio de cálculo proyectivo sobre días operativos reales y decisión de diseño táctil frente a interfaces textuales propensas a errores. | Propuesta de patrones estructurales, diseño de máquinas de estado para Telegram y scaffolding modular de scripts (`bot.py` y `app.py`). |
| **Seguridad Perimetral** | Auditoría y detección de la vulnerabilidad de fallback público del PIN en repositorios abiertos; custodia, rotación manual y gestión aislada de credenciales. | Implementación de la política *fail-closed*, refactorización de lecturas de entorno sin valores por defecto e interrupción controlada de ejecución (`st.stop()`). |
| **Infraestructura y DevOps** | Gestión de cuentas y despliegues en GitHub, Turso, Render y Streamlit Cloud; resolución de ramas y rebases de Git. | Scaffolding de micro-servidor HTTP para Render, scripts de siembra (*seeding*) de base de datos y optimización de dependencias. |
| **Control de Calidad** | Doble verificación empírica de balances, validación de persistencia de transacciones en Turso y auditoría de exactitud temporal en proyecciones plurianuales. | Implementación de consultas parametrizadas en libSQL, cálculo matemático de *run-rate* y renderizado dinámico en Pandas y Streamlit. |

### 3. Privacidad, Seguridad y Gestión de Credenciales
* **Aislamiento Criptográfico y Fail-Closed:** El sistema implementa una política de fallo seguro: si variables críticas como `DASHBOARD_PIN`, `TURSO_URL` o `TURSO_AUTH_TOKEN` no están explícitamente definidas en el entorno o en el almacén de secretos, la aplicación revoca el acceso de inmediato sin exponer fallbacks predeterminados.
* **Protección de Datos Sensibles:** Ninguna transacción financiera, saldo real ni credencial privada fue expuesta en el historial público de Git ni procesada por el modelo de lenguaje. Los secretos se gestionan mediante exclusión en `.gitignore`, variables de entorno en Render y el sistema cifrado de Streamlit Secrets.
* **Validación de Identidad:** La interacción con el bot de Telegram está restringida exclusivamente al identificador numérico único del titular (`ALLOWED_USER_ID`), descartando cualquier petición ajena.

### 4. Metodología de Verificación y Asunción de Responsabilidad
Cada componente, cálculo y flujo operativo (desde la ingesta táctil y las correcciones de registros en Telegram hasta las métricas de rescate y la proyección de metas anuales) fue auditado y verificado manualmente en entorno local y de producción antes de su validación final. El titular asume la autoría intelectual, el mantenimiento técnico continuo y la responsabilidad legal y operativa íntegra sobre el uso del software y la veracidad de los datos.
