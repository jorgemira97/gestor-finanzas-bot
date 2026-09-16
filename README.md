## Declaración de Autoría, Diligencia y Uso de IA (Diligence Statement)

### 1. Marco de Desarrollo y Herramientas
Este software fue conceptualizado, probado y puesto en producción bajo un modelo de colaboración Humano-IA:
- **Diseño de producto y toma de decisiones:** Autor del proyecto (definición de reglas financieras, criterios de control mensual/anual, UX de captura y pruebas de aceptación).
- **Copiloto técnico:** Modelo LLM utilizado para la síntesis de esquemas relacionales (SQL), aceleración de scripting en Python (Streamlit y Telegram Bot API) y parametrización matemática del pacing de gasto.

### 2. Matriz de Responsabilidad y Verificación
- **Validación empírica:** Todos los cálculos matemáticos (balance acumulado, límites diarios móviles, proyecciones a fin de mes e integridad referencial en SQLite) fueron auditados y verificados manualmente contra escenarios reales.
- **Seguridad perimetral:** Se implementó una capa de validación de identidad para llamadas entrantes en la API de Telegram, asegurando ejecución exclusiva para el propietario del sistema.
- **Privacidad de datos:** Arquitectura 100% *on-premise*. Ningún dato financiero o credencial es transmitido a modelos de lenguaje ni almacenado en infraestructuras compartidas.

### 3. Asunción de Responsabilidad
El autor asume la total propiedad, mantenimiento y responsabilidad sobre el código, la arquitectura final y la operación del sistema aquí presentado.