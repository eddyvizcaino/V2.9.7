# Validación V2.9

- Sintaxis Python comprobada con `py_compile`.
- Integridad del ZIP comprobable con `unzip -t`.
- Migraciones diseñadas para SQLite y PostgreSQL mediante el mecanismo existente `_ensure_col`.
- La suite completa no se ejecutó en este entorno porque Werkzeug/Flask no están instalados en el runtime de pruebas; están fijados en `requirements.txt` para el despliegue.
- Argon2id está añadido a `requirements.txt`.
