# Decisiones de arquitectura

Cada decisión indica contexto, alternativa descartada y consecuencia.

## D1. Monolito modular
Un solo proceso FastAPI con módulos (auth, personas, instalaciones, reservas, clases, torneos, progreso, panel, auditoría). **Descartado:** microservicios (complejidad operativa injustificada para un proyecto académico de un desarrollador). **Consecuencia:** despliegue simple; el límite entre módulos es por convención de capas.

## D2. Capas
`routers → dependencias/servicios → repositorios → modelos → MariaDB`. Las reglas puras (solapes, horarios, estadísticas, CSV) viven en `app/domain` sin dependencias externas, lo que permite probarlas sin base de datos (57 pruebas unitarias ejecutadas).

## D3. Frontend sin framework, mismo origen
JavaScript nativo servido por la propia app. Sin `innerHTML` ni `localStorage`; helper `h()` para construir DOM; modales `<dialog>`. **Ventaja:** sin Node en producción, sin CORS, CSP estricta. **Costo:** más código manual que con un framework.

## D4. MariaDB 11.4.5 fijada
Versión fija (no `latest`) para reproducibilidad. No se publica el puerto de la base de datos; solo un override opcional en `127.0.0.1` (`compose.db-local.yaml`).

## D5. SQLAlchemy 2 + Alembic
Esquema versionado con migraciones (`0001_initial_schema`). Nombres de restricciones e índices con convención fija. Estados (enums) guardados como VARCHAR(20) con restricciones CHECK.

## D6. Autenticación
Contraseñas con Argon2id (pwdlib). JWT HS256 en cookie `rh_session` (HttpOnly, SameSite=Lax). CSRF por doble envío: cookie `rh_csrf` legible por JS y cabecera `X-CSRF-Token` que debe coincidir con la claim `csrf` firmada. Middleware de verificación de `Origin`. `token_version` invalida sesiones al cambiar la contraseña o desactivar al usuario.

## D7. Concurrencia de reservas
Al reservar se bloquea la fila de la mesa con `SELECT ... FOR UPDATE`, luego se consulta el solape (`nuevo_inicio < fin_existente AND nuevo_fin > inicio_existente`) y se inserta; conflicto → HTTP 409. El motor usa `READ COMMITTED` para que, tras obtener el bloqueo, la lectura vea las filas ya confirmadas por la transacción anterior (con `REPEATABLE READ` la instantánea podría omitirlas). También chocan con clases en la misma mesa y bloques de mantenimiento. **Estado:** diseñado y con prueba de concurrencia escrita; **no ejecutado** aquí por falta de MariaDB.

## D8. Fechas
Fechas con zona horaria de extremo a extremo, almacenadas en UTC (`UTCDateTime`), mostradas en America/Bogota. Horario operativo 08:00–21:00, duración 30–120 min, anticipación máxima 30 días, cancelación de estudiantes hasta 2 h antes.

## D9. Claves primarias INT
La especificación recomienda BIGINT; se usó INT autoincremental por simplicidad. Es una desviación documentada; cambiarla requiere una migración.

## D10. Sin Chart.js
Las gráficas son barras CSS: evita CDN y dependencias externas y permite una CSP restrictiva.

## D11. Docker y CI
Dockerfile multietapa (`runtime` y `dev`), entrypoint que espera la BD, migra (`RUN_MIGRATIONS=1`) y siembra datos demo (`SEED_DEMO=1`, nunca en producción). CI en GitHub Actions con servicio MariaDB; no hay CD.

## D12. Dependencias
Fijadas en `backend/requirements.txt`; cada una cumple una función concreta (FastAPI/uvicorn, Pydantic, SQLAlchemy/Alembic/PyMySQL, pwdlib[argon2], PyJWT, tzdata, email-validator). Las versiones **no se instalaron ni verificaron** en este entorno.
