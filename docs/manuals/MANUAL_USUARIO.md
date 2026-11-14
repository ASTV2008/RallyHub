# Manual de usuario

> No incluye capturas de pantalla: la interfaz no pudo ejecutarse contra el backend real en el entorno de construcción.

## Ingreso
Abra `http://localhost:8000/`, introduzca correo y contraseña. Tras varios intentos fallidos el acceso se bloquea temporalmente.

## Estudiante
- **Reservas:** elija mesa, fecha y hora; duración 30–120 min, entre 08:00 y 21:00, hasta 30 días de anticipación. Si el horario choca, la aplicación muestra un conflicto.
- **Cancelar:** hasta 2 horas antes del inicio.
- **Progreso y clases:** consulta de su información.
- **Perfil:** cambio de contraseña (cierra las demás sesiones).

## Entrenador
Clases, asistencia (presente, ausente, justificado), registro de progreso técnico, torneos y panel.

## Administrador
Estudiantes, entrenadores, instalaciones, mesas, mantenimiento, torneos, panel y auditoría; exportación CSV.

## Mensajes frecuentes
- *Conflicto de reserva (409):* la mesa ya está ocupada.
- *Fuera de horario:* ajuste la hora al horario operativo.
