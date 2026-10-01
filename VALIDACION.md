# Validación V2.7.1

- Python 3.12: compilación de todos los archivos con `SyntaxWarning` tratado como error, aprobada.
- Servidor: **52 pruebas aprobadas**, ninguna omitida. Incluyen autenticación, CSRF, permisos por ministerio y módulo, validación, duplicados, fotos privadas, papelera, auditoría, reportes, FOLIGRUC e importación del esquema académico anterior.
- Lector: **12 escenarios del analizador JavaScript aprobados**.
- PostgreSQL: esquema idempotente, arranque, inicio de sesión, consultas de páginas, escrituras de miembros/eventos/FOLIGRUC, fotos, exportaciones PDF/Excel, papelera/restauración de miembros y respaldo lógico probados con PGlite y psycopg. PGlite usa el motor PostgreSQL compilado a WebAssembly; estas pruebas no son una prueba de carga ni sustituyen la comprobación en Render.
- Gunicorn 23.0.0: arranque local correcto con `app:app` y conexión PostgreSQL de prueba.
- Respaldo/restauración completa: ida y vuelta, fotos y rechazo de destino ocupado/datos inválidos probados con SQLite. La restauración completa PostgreSQL debe ensayarse en una base vacía antes de utilizarla para recuperación real; no se completó ese ensayo contra una instancia de Render.
- Migración: se comprobó la conversión de V2.6/FOLIGRUC anterior con datos sintéticos y una lectura de un respaldo disponible en un temporal. El origen no se modifica. No se incluyeron datos personales en el paquete.
- Navegador: inicio de sesión, panel, captura de texto equivalente al lector Tera, revisión/aplicación de los cuatro campos y bloqueo de duplicado con enlace a perfil. Ficha FOLIGRUC revisada a 390 px sin desbordamiento horizontal; sin errores de consola en esa revisión.
- El Tera físico, una cédula real, permisos de cámara y calidad OCR en el equipo final no se probaron. El flujo conserva la revisión humana y la entrada manual.
- ZIP: una carpeta raíz, rutas relativas seguras, archivos esperados y prueba de integridad; compilación y arranque de la copia extraída.
- No hubo despliegue al servicio del usuario ni acceso a credenciales reales de Render.

## V2.7.3
Migración de cuentas heredadas: añade campos faltantes y normaliza valores NULL en Active, Locked y FailedAttempts sin desbloquear cuentas bloqueadas. Dos pruebas de migración e inicio de sesión pasaron con SQLite. PostgreSQL de Render requiere validación posterior al despliegue; no se accedió a su base de datos.

## V2.7.4
Restauración desde el panel administrador para PostgreSQL con archivo JSON, confirmación escrita y reemplazo transaccional; validación de columnas previa al borrado. Probada la restauración y la reversión ante formato incompatible con SQLite. No se ejecutó una prueba sobre la instancia PostgreSQL real de Render.

## V2.7.5
El registro de estudiantes genera códigos FOL correlativos automáticamente y conserva los existentes. Prueba de creación y continuidad con un código anterior: correcta. PostgreSQL de Render no fue probado directamente.

## V2.7.6
Registro público de miembros mediante enlace y QR SVG. En una prueba local se envió la solicitud, apareció pendiente y se aprobó; el miembro fue creado. Se verificó la descarga del QR y la restauración de respaldos. La instancia real de Render no fue probada.
