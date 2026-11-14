# Referencia académica: Proyecto_TP.pptx

Este documento separa **lo que dice la presentación** de **lo que se decidió en RallyHub**.

## 1. Lo que contiene la presentación (hechos)

La presentación "Proyecto Taller de Programación" tiene 10 diapositivas. Los títulos son: Proyecto Taller de Programación; Temas; Estructura de aprendizaje; Proyecto integrador; Arquitectura tecnológica; Flujo de trabajo; Proyecto completo; Estructura inicial (dos diapositivas); Herramientas de creación. Buena parte del contenido está en imágenes.

- **Secuencia de preguntas del curso:** ¿Qué es un objeto? → ¿Cómo organizo mi código? → ¿Cómo guardo información? → ¿Cómo expongo esa información? → ¿Cómo creo una interfaz? → ¿Cómo pruebo mi código? → ¿Cómo lo hago más seguro? → ¿Cómo lo conecto con IA? → ¿Cómo lo despliego?
- **Proyecto de ejemplo:** "SmartCampus", plataforma de servicios universitarios con estudiantes, cursos, profesores, solicitudes/tickets, eventos, recursos académicos, estadísticas y consultas mediante IA.
- **Arquitectura de ejemplo:** frontend React, API Spring Boot, JPA/ORM, PostgreSQL, servicios de IA (OpenAI/Gemini), comunicación REST.
- **Estructura inicial de ejemplo:** archivos por clase (`Estudiante`, `Profesor`, `Curso`, `Solicitud`, y en la variante Python también `Evento`, `RecursoAcademico`) más `main` y `README.md`.

## 2. Correspondencia con RallyHub (decisiones propias)

RallyHub **no** replica la pila del ejemplo; usa el de la especificación (`PROMPT_MAESTRO_RALLYHUB_CLAUDE.md`). La correspondencia con las preguntas del curso es:

| Pregunta del curso | Dónde se responde en RallyHub |
|---|---|
| ¿Qué es un objeto? | Modelos y servicios (`backend/app/models`, `services`) |
| ¿Cómo organizo mi código? | Capas router → servicio → repositorio → modelo; dominio puro en `app/domain` |
| ¿Cómo guardo información? | MariaDB 11.4 con SQLAlchemy 2 y migraciones Alembic (15 tablas) |
| ¿Cómo expongo esa información? | API REST versionada `/api/v1` con FastAPI y Pydantic v2 |
| ¿Cómo creo una interfaz? | Frontend JavaScript sin framework en `backend/app/static` |
| ¿Cómo pruebo mi código? | pytest: unitarias (ejecutadas) e integración (escritas, no ejecutadas aquí) |
| ¿Cómo lo hago más seguro? | Argon2id, JWT en cookie HttpOnly, CSRF, roles, auditoría |
| ¿Cómo lo conecto con IA? | **No implementado** (RallyBot queda como trabajo futuro, P2) |
| ¿Cómo lo despliego? | Docker Compose (`db` + `app`) y CI en GitHub Actions (sin CD) |

## 3. Recomendaciones (no son hechos de la presentación)

- La diferencia de pila con el ejemplo (Python/FastAPI en vez de Spring Boot, sin React) es una decisión del proyecto y se justifica en `docs/architecture/DECISIONES_ARQUITECTURA.md`.
- El docente debe confirmar si exige una pila concreta; el campo del docente queda como `[Completar]`.
