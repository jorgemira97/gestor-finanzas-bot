## Declaración de Autoría, Diligencia y Uso de IA (Diligence Statement) — v2.1

### 1. Propósito y Contexto del Proyecto
Este repositorio alberga un sistema integral de control financiero personal diseñado bajo un paradigma de **soberanía de datos absoluta y coste cero** (v2.1). La arquitectura desacopla tres capas independientes:
* **Capa de Persistencia:** Base de datos relacional distribuida en Turso (libSQL) con esquemas tipificados para transacciones, categorización fija/variable y seguimiento de techos mensuales y metas anuales (`metas_mensuales` y `metas_anuales`).
* **Capa de Ingesta y Gestión Táctil (Telegram):** Bot alojado en Render (Web Service Free Tier) con microservidor HTTP keep-alive, interfaz CRUD táctil completa y selección de fechas retrospectivas.
* **Capa Analítica y Visualización (Dashboard):** Panel interactivo en Streamlit Community Cloud protegido por autenticación perimetral estricta (*fail-closed* sin fallbacks públicos), cabecera simétrica y motor de proyección de ahorro anual en días operativos reales.
* **Capa de Autoservicio e Incorporación Zero-Code (v2.1):** Automatización de infraestructura mediante Blueprint (`render.yaml`) y manual de despliegue paso a paso (`GUIA_DESPLIEGUE.md`) para permitir a usuarios no técnicos desplegar y gestionar su propia instancia privada sin tocar terminales ni código fuente.

El proyecto persigue un doble fin: resolver la gestión económica individual con máxima ergonomía y servir como caso de estudio riguroso de desarrollo multi-paso mediante colaboración Humano-IA.

### 2. Matriz de Delegación y Roles (Humano vs. IA)
El diseño, refactorización y documentación del sistema se articularon bajo el siguiente marco de gobernanza:

| Dimensión | Aporte y Supervisión Humana | Rol del Copiloto IA (Gemini) |
| :--- | :--- | :--- |
| **Estrategia y Negocio** | Definición de flujos CRUD táctiles, criterios de *pacing*, reglas de proyección y decisión de arquitectura descentralizada (*deploy-your-own*) frente al riesgo de custodia multi-inquilino. | Propuesta de patrones de diseño, máquinas de estado para Telegram y modelado matemático de run-rate en días operativos reales. |
| **Seguridad Perimetral** | Auditoría y detección de la vulnerabilidad de fallback del PIN en repositorios públicos; custodia y rotación manual de secretos. | Implementación del patrón de autenticación *fail-closed*, interrupción controlada de ejecución (`st.stop()`) y consultas parametrizadas contra inyección SQL. |
| **DevOps y Automatización** | Creación y administración de cuentas cloud; resolución manual de bifurcaciones y rebases de Git. | Configuración de Blueprints (`render.yaml`), scaffolding de micro-servidor HTTP para Render y adaptación de dependencias en `requirements.txt`. |
| **Documentación y UX** | Validación del tono, empatía con usuarios no técnicos y revisión del orden lógico del proceso de onboarding. | Estructuración pedagógica de `GUIA_DESPLIEGUE.md`, metáfora de la "Libreta de Claves" y redacción de protocolos de contingencia (*troubleshooting*). |

### 3. Privacidad, Soberanía Distribuida y Gestión de Credenciales
* **Modelo "Deploy-Your-Own" (Sin Custodia Central):** Para preservar la privacidad financiera, la plataforma rechaza intencionadamente el modelo SaaS multiusuario centralizado. Cada usuario final despliega su propia base de datos en Turso y sus propios servicios cloud, garantizando que el autor de este repositorio **nunca tiene acceso, visibilidad ni custodia** sobre saldos o transacciones ajenas.
* **Aislamiento Criptográfico y Fail-Closed:** El sistema revoca de inmediato la ejecución si faltan variables críticas de entorno (`DASHBOARD_PIN`, `TURSO_URL`, `TURSO_AUTH_TOKEN`, `BOT_TOKEN`, `ALLOWED_USER_ID`), imposibilitando el acceso con credenciales genéricas por defecto.
* **Ofuscación de Datos:** Ningún registro bancario, importe personal ni clave privada fue procesado por modelos de lenguaje comercial ni almacenado en el historial de Git.

### 4. Metodología de Verificación y Asunción de Responsabilidad
* **Auditoría Técnica:** Cada script (`bot.py`, `app.py`, `render.yaml`) fue ejecutado, testeado y verificado en entornos de desarrollo y producción bajo supervisión humana continua antes de su consolidación en la rama principal.
* **Titularidad del Código:** El autor mantiene la autoría intelectual de la configuración del sistema, asumiendo la supervisión directa sobre cada propuesta algorítmica generada por la IA.

### 5. Exención de Responsabilidad y Términos de Uso
El software y la documentación contenidos en este repositorio se comparten exclusivamente con fines educativos, de divulgación tecnológica y de uso personal bajo la modalidad **"tal cual" (*as-is*)**, sin garantías de ningún tipo:
* **Sin Asesoramiento Financiero:** Las herramientas de cálculo, métricas de *pacing*, límites de gasto y proyecciones de ahorro son meras estimaciones estadísticas automatizadas y no constituyen recomendación de inversión, asesoría financiera, contable ni legal.
* **Sin Compromiso de Soporte:** El autor no adquiere obligación alguna de mantenimiento continuo, resolución de incidencias, disponibilidad de servicio ni asistencia técnica 24/7 respecto a las instancias independientes desplegadas por terceros.
* **Responsabilidad Individual:** Cada usuario es el único y exclusivo responsable de la seguridad de sus credenciales, de las copias de seguridad de sus datos en Turso y del control del gasto en las plataformas cloud utilizadas.
