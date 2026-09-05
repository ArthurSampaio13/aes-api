#!/bin/sh
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_user="$AES_APP_USER" -v app_password="'$AES_APP_PASSWORD'" <<'SQL'
CREATE ROLE :app_user LOGIN PASSWORD :app_password NOSUPERUSER NOBYPASSRLS;
GRANT ALL ON SCHEMA public TO :app_user;
SQL
