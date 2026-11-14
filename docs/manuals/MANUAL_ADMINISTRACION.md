# Manual de administración

## Variables de entorno
Copie `.env.example` a `.env` y cambie **todos** los valores marcados `change-me`. En producción (`ENVIRONMENT=production`) la aplicación se niega a arrancar con la clave por defecto o con `COOKIE_SECURE=false`.

## Operación
```bash
docker compose up --build -d
docker compose ps
docker compose logs -f app
docker compose exec app alembic upgrade head
docker compose exec app python -m scripts.seed   # solo desarrollo
docker compose down                              # conserva datos
```
**Advertencia:** `docker compose down -v` borra el volumen y TODOS los datos.

## Respaldo y restauración
```bash
docker compose exec db sh -c 'mariadb-dump -uroot -p"$MARIADB_ROOT_PASSWORD" rallyhub' > backup.sql
docker compose exec -T db sh -c 'mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" rallyhub' < backup.sql
```
Estos comandos no fueron ejecutados en el entorno de construcción.

## Seguridad operativa
Usar HTTPS delante de la app, no publicar el puerto de la BD, rotar `SECRET_KEY`, y recordar que el limitador de intentos es por proceso (un worker).

## Pruebas
`docker compose --profile test run --rm tests` (la BD `rallyhub_test` solo se crea con un volumen nuevo).
