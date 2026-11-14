#!/bin/sh
# Se ejecuta una sola vez, al inicializar el volumen de datos (docker-entrypoint-initdb.d).
# Crea la base independiente para las pruebas de integración. Si el volumen ya existía,
# ejecuta estos mismos comandos manualmente (ver README, "Pruebas").
set -e
mariadb -uroot -p"${MARIADB_ROOT_PASSWORD}" <<SQL
CREATE DATABASE IF NOT EXISTS rallyhub_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON rallyhub_test.* TO '${MARIADB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
