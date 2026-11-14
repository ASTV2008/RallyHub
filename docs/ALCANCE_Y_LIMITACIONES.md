# Alcance y limitaciones

## Alcance implementado (código escrito)
Autenticación y roles (administrador, entrenador, estudiante); CRUD de estudiantes, entrenadores, instalaciones y mesas; bloqueos de mantenimiento; reservas con validación de reglas y control de concurrencia; clases con inscripciones y asistencia; progreso técnico; torneos con resultados manuales; panel con estadísticas; auditoría; exportación CSV protegida contra inyección de fórmulas; datos semilla de demostración.

## Limitaciones conocidas
- Limitador de intentos de login **en memoria**, por proceso (se ejecuta un solo worker).
- Cerrar sesión **no revoca** el token hasta su expiración; solo el cambio de contraseña o la desactivación suben `token_version`.
- Swagger (`/docs`) requiere acceso a CDN; la CSP no se aplica a esa ruta.
- El límite de tamaño de cuerpo no cubre cuerpos *chunked*.
- "Eliminar" una clase equivale a cancelarla.
- Claves INT en vez de BIGINT.
- Torneos: solo resultados manuales, sin generador de llaves, solo individuales.
- Solo los entrenadores crean registros de progreso.
- Ocupación = reservas CONFIRMED/COMPLETED + clases no canceladas.

## No implementado
RallyBot / IA, correo electrónico, clases recurrentes, multi-tenant, app móvil (todo P2).

## Verificación
Ver `ESTADO_DEL_PROYECTO.md`. Docker, MariaDB, migraciones y pruebas de integración **no se ejecutaron** en el entorno de construcción.
