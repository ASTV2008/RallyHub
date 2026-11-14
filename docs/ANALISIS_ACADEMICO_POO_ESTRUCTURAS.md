# Análisis académico: POO, estructuras de datos y complejidad

Todos los ejemplos remiten a código real del repositorio.

## 1. Programación orientada a objetos
- **Abstracción y herencia:** `services/base.py` define la clase `Service` (sesión de BD, reloj inyectable, `audit()`, `require_roles`); los servicios de cada módulo la extienden.
- **Encapsulación:** `BookingPolicy` (`domain/booking_rules.py`) agrupa las reglas de horario y duración; `LoginThrottle` (`core/ratelimit.py`) oculta su estado interno detrás de métodos.
- **Inyección de dependencias:** el reloj se inyecta en los servicios para probar sin depender de la hora real.
- **Polimorfismo / jerarquía de errores:** `domain/errors.py` define excepciones de dominio con código y estado HTTP (409, 429, etc.) que un manejador común traduce a respuestas JSON.
- **Modelos:** 15 clases SQLAlchemy mapeadas a tablas (relaciones 1–N y N–M mediante tablas asociativas, p. ej. `class_enrollments`).

## 2. Estructuras de datos usadas
| Estructura | Dónde | Para qué |
|---|---|---|
| `dict` / `defaultdict` | `domain/stats.py` (`occupancy_by_table`, `count_by`), `services/facilities.py` | Agrupar minutos reservados y huecos por mesa |
| `deque` | `core/ratelimit.py` | Ventana deslizante de intentos fallidos por clave |
| `set` | `services/people.py`, `services/tournaments.py` | Validar campos editables y existencia de ids |
| `list` | Resultados paginados | Colecciones ordenadas |

## 3. Complejidad (Big-O)
- `occupancy_by_table`: **O(R + T)** (R reservas, T mesas); un recorrido sobre cada colección.
- `count_by`: **O(n)**.
- Verificación de solape de una reserva: una consulta indexada sobre la mesa; en memoria la comparación de intervalos es **O(1)** por par. El bloqueo de fila serializa reservas concurrentes sobre la misma mesa.
- `LoginThrottle`: poda amortizada **O(k)** por llamada (k = intentos expirados); memoria proporcional al número de claves activas.
- Listados: paginación `LIMIT/OFFSET`; el costo en BD depende de los índices definidos en la migración.

## 4. Límites
No se midieron tiempos reales de ejecución; las cotas son análisis teórico del código.
