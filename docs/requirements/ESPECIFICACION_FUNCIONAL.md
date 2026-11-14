# Especificación funcional

## Requisitos funcionales
| ID | Requisito | Rol |
|---|---|---|
| RF-01 | Iniciar y cerrar sesión; cambiar contraseña | Todos |
| RF-02 | Gestionar estudiantes (crear, editar, desactivar, listar, exportar CSV) | Admin |
| RF-03 | Gestionar entrenadores | Admin |
| RF-04 | Gestionar instalaciones y mesas (estados ACTIVE/MAINTENANCE/OUT_OF_SERVICE) y bloqueos de mantenimiento | Admin |
| RF-05 | Consultar la política de reservas | Todos |
| RF-06 | Crear, listar y cancelar reservas de mesa | Admin, Estudiante |
| RF-07 | Programar clases, inscribir estudiantes y tomar asistencia | Admin, Entrenador |
| RF-08 | Registrar y consultar progreso técnico | Entrenador, Estudiante (lectura propia) |
| RF-09 | Crear torneos, inscribir participantes y registrar resultados | Admin, Entrenador |
| RF-10 | Panel con estadísticas y ocupación | Admin, Entrenador |
| RF-11 | Consultar la bitácora de auditoría | Admin |

## Reglas de negocio
- RN-01 Horario 08:00–21:00 (America/Bogota), duración 30–120 min, ranuras de 15 min.
- RN-02 No se reserva en el pasado ni a más de 30 días.
- RN-03 No pueden solaparse reservas, clases o mantenimientos en la misma mesa; solape: `nuevo_inicio < fin AND nuevo_fin > inicio`; conflicto → 409.
- RN-04 Mesas en mantenimiento o fuera de servicio no se reservan.
- RN-05 Un estudiante cancela con al menos 2 h de antelación.
- RN-06 Estados de reserva: CONFIRMED, CANCELLED, COMPLETED, NO_SHOW.
- RN-07 La capacidad de una clase no puede excederse; no hay inscripciones duplicadas.

## Requisitos no funcionales
RNF-01 Seguridad (Argon2id, cookies HttpOnly, CSRF, CSP, límite de intentos, auditoría). RNF-02 Reproducibilidad (Docker Compose, versiones fijas). RNF-03 Mantenibilidad (capas, ruff, mypy, pruebas). RNF-04 Integridad de datos (restricciones, migraciones). RNF-05 Sin dependencia de claves de IA ni de CDN en la interfaz.

## Historias de usuario (muestra)
- Como estudiante quiero reservar una mesa para entrenar libremente.
- Como entrenador quiero registrar la asistencia de mi clase.
- Como administrador quiero bloquear una mesa por mantenimiento.

## Casos de uso
Ver `docs/diagrams/usecases.png`.
