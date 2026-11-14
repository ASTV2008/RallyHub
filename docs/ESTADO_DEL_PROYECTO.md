# Estado del proyecto

Fecha: 2026-11-12. Solo se marca como verificado lo que se ejecutó en el entorno de construcción.

## Matriz de verificación
| Elemento | Resultado | Evidencia |
|---|---|---|
| Pruebas unitarias (57) | **Ejecutadas, pasan** | `pytest tests/unit` |
| ruff | **Ejecutado, sin errores** | `ruff check .` |
| mypy (`--ignore-missing-imports`) | Ejecutado (sin las librerías instaladas, alcance limitado) | — |
| compileall, `node --check` del frontend | Ejecutados | — |
| Prueba de contrato esquemas↔modelos (AST) | Ejecutada, pasa | unit |
| Humo del frontend con Playwright contra API simulada | Ejecutado | no prueba el backend real |
| Diagramas Mermaid | Renderizados a PNG | `docs/diagrams` |
| Pruebas de integración y concurrencia | **Escritas, NO ejecutadas** | requieren MariaDB |
| Migración Alembic y comparación modelo↔migración | **NO ejecutadas** | — |
| `docker compose build/up`, imagen `mariadb:11.4.5` | **NO ejecutados** | sin Docker |
| FastAPI/SQLAlchemy/Argon2 en ejecución real | **NO ejecutados** | dependencias no instaladas |
| Cobertura | No medida | — |
| Capturas reales de la interfaz | No existen | no se inventan |

## Lista de aceptación
- [x] Código del backend, frontend, migración, seed, Docker, CI y pruebas escrito.
- [x] Unitarias y análisis estático ejecutados.
- [ ] Arranque con Docker verificado.
- [ ] Migración verificada contra MariaDB.
- [ ] Integración y concurrencia verificadas.

## Pendiente para el usuario
Ejecutar `docker compose up --build` y `docker compose --profile test run --rm tests`, y corregir lo que aparezca. Completar el nombre del docente (`[Completar]`).
