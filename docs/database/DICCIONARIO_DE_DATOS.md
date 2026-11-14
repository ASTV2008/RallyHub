# Diccionario de datos (generado desde los modelos SQLAlchemy)

Generado automáticamente a partir de `backend/app/models/*.py`; la migración `0001_initial_schema.py` crea las mismas tablas. Las columnas enumeradas se guardan como `VARCHAR(20)` con restricción `CHECK` de valores permitidos. Los instantes se almacenan en UTC (tipo propio `UTCDateTime`).


## `audit_logs` (modelo `AuditLog`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `user_id` | `int` | sí | FK → users.id |
| `action` | `String(60)` | no |  |
| `entity` | `String(60)` | no |  |
| `entity_id` | `int` | sí |  |
| `detail` | `String(500)` | sí |  |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `Index('ix_audit_logs_created', 'created_at')`

## `classes` (modelo `ClassSession`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `name` | `String(120)` | no |  |
| `description` | `Text` | sí |  |
| `coach_id` | `int` | no | FK → coaches.id |
| `table_id` | `int` | sí | FK → tables.id |
| `level` | `Enum(VARCHAR(20))` | no |  |
| `capacity` | `Integer` | no |  |
| `starts_at` | `UTCDateTime` | no |  |
| `ends_at` | `UTCDateTime` | no |  |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `CheckConstraint('ends_at > starts_at', name='range')`; `CheckConstraint('capacity >= 1', name='capacity')`; `Index('ix_classes_coach_range', 'coach_id', 'starts_at', 'ends_at')`; `Index('ix_classes_table_range', 'table_id', 'starts_at', 'ends_at')`

## `class_enrollments` (modelo `ClassEnrollment`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `class_id` | `int` | no | FK → classes.id, índice |
| `student_id` | `int` | no | FK → students.id, índice |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `enrolled_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `UniqueConstraint('class_id', 'student_id', name='uq_class_enrollments_class_student')`

## `attendances` (modelo `Attendance`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `enrollment_id` | `int` | no | FK → class_enrollments.id, UNIQUE |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `notes` | `String(300)` | sí |  |
| `recorded_by` | `int` | sí | FK → users.id |
| `recorded_at` | `UTCDateTime` | no |  |
| `updated_at` | `UTCDateTime` | sí |  |

## `facilities` (modelo `Facility`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `name` | `String(120)` | no | UNIQUE |
| `address` | `String(200)` | sí |  |
| `description` | `Text` | sí |  |
| `is_active` | `Boolean` | no |  |
| `created_at` | `UTCDateTime` | no |  |

## `tables` (modelo `GameTable`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `facility_id` | `int` | no | FK → facilities.id, índice |
| `code` | `String(30)` | no |  |
| `table_type` | `String(60)` | sí |  |
| `description` | `Text` | sí |  |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `UniqueConstraint('facility_id', 'code', name='uq_tables_facility_code')`

## `maintenance_blocks` (modelo `MaintenanceBlock`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `table_id` | `int` | no | FK → tables.id |
| `starts_at` | `UTCDateTime` | no |  |
| `ends_at` | `UTCDateTime` | no |  |
| `reason` | `String(200)` | sí |  |
| `created_by` | `int` | sí | FK → users.id |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `CheckConstraint('ends_at > starts_at', name='range')`; `Index('ix_maintenance_blocks_table_range', 'table_id', 'starts_at', 'ends_at')`

## `progress_records` (modelo `ProgressRecord`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `student_id` | `int` | no | FK → students.id |
| `coach_id` | `int` | no | FK → coaches.id |
| `recorded_on` | `Date` | no |  |
| `serve` | `SmallInteger` | no |  |
| `receive` | `SmallInteger` | no |  |
| `ball_control` | `SmallInteger` | no |  |
| `movement` | `SmallInteger` | no |  |
| `strategy` | `SmallInteger` | no |  |
| `notes` | `String(500)` | sí |  |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `Index('ix_progress_records_student_date', 'student_id', 'recorded_on')`; `CheckConstraint(f'{s} BETWEEN 1 AND 5', name=s)`

## `reservations` (modelo `Reservation`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `student_id` | `int` | no | FK → students.id |
| `table_id` | `int` | no | FK → tables.id |
| `starts_at` | `UTCDateTime` | no |  |
| `ends_at` | `UTCDateTime` | no |  |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `notes` | `String(300)` | sí |  |
| `created_by` | `int` | sí | FK → users.id |
| `created_at` | `UTCDateTime` | no |  |
| `cancelled_at` | `UTCDateTime` | sí |  |

Restricciones de tabla / índices: `CheckConstraint('ends_at > starts_at', name='range')`; `Index('ix_reservations_table_range', 'table_id', 'starts_at', 'ends_at')`; `Index('ix_reservations_student_start', 'student_id', 'starts_at')`

## `tournaments` (modelo `Tournament`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `name` | `String(120)` | no |  |
| `category` | `String(60)` | sí |  |
| `modality` | `Enum(VARCHAR(20))` | no |  |
| `starts_on` | `Date` | no |  |
| `ends_on` | `Date` | no |  |
| `location` | `String(200)` | sí |  |
| `capacity` | `Integer` | no |  |
| `status` | `Enum(VARCHAR(20))` | no |  |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `CheckConstraint('ends_on >= starts_on', name='range')`; `CheckConstraint('capacity >= 2', name='capacity')`

## `tournament_participants` (modelo `TournamentParticipant`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `tournament_id` | `int` | no | FK → tournaments.id, índice |
| `student_id` | `int` | no | FK → students.id, índice |
| `registered_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `UniqueConstraint('tournament_id', 'student_id', name='uq_tournament_participants_tournament_student')`

## `tournament_matches` (modelo `TournamentMatch`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `tournament_id` | `int` | no | FK → tournaments.id, índice |
| `round_name` | `String(60)` | no |  |
| `participant_a_id` | `int` | no | FK → tournament_participants.id |
| `participant_b_id` | `int` | no | FK → tournament_participants.id |
| `score_a` | `SmallInteger` | no |  |
| `score_b` | `SmallInteger` | no |  |
| `winner_id` | `int` | sí | FK → tournament_participants.id |
| `created_at` | `UTCDateTime` | no |  |

Restricciones de tabla / índices: `CheckConstraint('participant_a_id <> participant_b_id', name='distinct_players')`; `CheckConstraint('score_a >= 0 AND score_b >= 0', name='scores')`

## `users` (modelo `User`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `email` | `String(254)` | no | UNIQUE |
| `password_hash` | `String(255)` | no |  |
| `role` | `Enum(VARCHAR(20))` | no |  |
| `is_active` | `Boolean` | no |  |
| `token_version` | `Integer` | no |  |
| `created_at` | `UTCDateTime` | no |  |

## `students` (modelo `Student`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `user_id` | `int` | no | FK → users.id, UNIQUE |
| `first_name` | `String(80)` | no |  |
| `last_name` | `String(80)` | no |  |
| `birth_date` | `Date` | sí |  |
| `phone` | `String(30)` | sí |  |
| `guardian_name` | `String(120)` | sí |  |
| `level` | `Enum(VARCHAR(20))` | no |  |
| `is_active` | `Boolean` | no |  |
| `created_at` | `UTCDateTime` | no |  |

## `coaches` (modelo `Coach`)

| Columna | Tipo | Nulo | Clave / restricción |
|---|---|---|---|
| `id` | `int` | no | PK |
| `user_id` | `int` | no | FK → users.id, UNIQUE |
| `first_name` | `String(80)` | no |  |
| `last_name` | `String(80)` | no |  |
| `specialty` | `String(120)` | sí |  |
| `bio` | `Text` | sí |  |
| `phone` | `String(30)` | sí |  |
| `is_active` | `Boolean` | no |  |
| `created_at` | `UTCDateTime` | no |  |
