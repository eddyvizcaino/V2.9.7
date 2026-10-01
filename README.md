# Sistema Iglesia Web V2.7.6.1

Paquete para actualizar el servicio existente **IGLESIA-PROFECIA** en Render con PostgreSQL mediante `DATABASE_URL`. También funciona localmente con SQLite. No contiene bases de datos personales, fotos de miembros, contraseñas de Render ni una URL de conexión real.

## Antes de actualizar

1. En la versión que está funcionando, entre como Administrador y descargue una copia de seguridad de `iglesia.db`.
2. Conserve también la carpeta anterior `static/profiles` si tiene fotos. Los respaldos SQLite antiguos pueden no incluir esas imágenes.
3. Guarde el código anterior para poder consultarlo. No sustituya todavía su base ni borre el servicio de Render.
4. Durante la migración, deje de registrar cambios en la versión anterior. Un respaldo es una fotografía del momento en que se generó.
5. Extraiga el ZIP en una carpeta nueva. Se debe ver `app.py`, `manage.py`, `requirements.txt`, `iglesia/`, `templates/` y `static/` dentro de `Sistema_Iglesia_Web_V2_7_1/`.

**Agregar DATABASE_URL no copia los registros de SQLite.** Para conservarlos debe completar la importación de la siguiente sección antes de comenzar a usar la nueva versión.

## 1. Preparar la migración a la base PostgreSQL existente

Si `iglesia-db` todavía no contiene datos de este sistema, puede usarla como destino. Si ya contiene información de trabajo, no la sobrescriba: descargue un respaldo y use otra base vacía para validar la restauración. El importador rechaza un destino con registros existentes.

En su computadora, instale Python **3.12** y abra una terminal dentro de la carpeta extraída:

```sh
python -m venv .venv
```

Activación en Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activación en macOS/Linux:

```sh
source .venv/bin/activate
```

Instale las dependencias:

```sh
python -m pip install -r requirements.txt
```

En Render, abra **iglesia-db → Connect / Connections → External Database URL**. La conexión externa se usa desde su computadora; el servicio web usará la conexión interna. Si hay una lista de IP permitidas, autorice únicamente la IP de su computadora durante la importación.

Inicialice el esquema:

```sh
python manage.py --ask-database --ask-admin-password init
```

El programa pedirá la URL completa sin mostrarla ni guardarla. Después pedirá una contraseña temporal de al menos 8 caracteres para crear el administrador de una base vacía. No entre todavía a la web nueva ni cree registros en esta base antes de importar.

Importe su respaldo anterior (cambie solo la ruta del archivo):

```sh
python manage.py --ask-database import-sqlite "/ruta/al/iglesia_backup.db"
```

Si conserva las fotos anteriores:

```sh
python manage.py --ask-database import-sqlite "/ruta/al/iglesia_backup.db" --photos "/ruta/a/static/profiles"
```

Ejecute **una sola** de las dos variantes. Vuelva a proporcionar la misma URL externa cuando se solicite. El programa copia los datos a PostgreSQL en una transacción y mantiene intacto el SQLite de origen. Los usuarios y sus contraseñas cifradas mediante hash se conservan; el administrador temporal del destino se reemplaza por los usuarios importados.

La importación reconoce miembros, ministerios, usuarios, eventos, auditoría y el esquema anterior de FOLIGRUC (`FStudents`, `FSubjects`, `FPeriods`, `FEnrollments`, `FPriorCredits`). Conserva intentos, notas, profesores y materias aprobadas previamente; corrige los títulos del pénsum según las 15 materias oficiales. No incorpora los módulos eliminados ni sus tablas de asistencia, visitantes o familias. Conserve el respaldo original como archivo histórico.

Si aparece un conflicto de cédula, materia o integridad, la importación se revierte. Revise el respaldo y vuelva a intentarlo; no elimine datos de producción para forzarla. Una base que no siga uno de los esquemas reconocidos requiere revisar su mapeo antes de importar.

## 2. Actualizar el mismo servicio de Render

1. Abra **Render → IGLESIA-PROFECIA → Settings** y anote el repositorio y la rama conectados. Mantenga ese mismo servicio.
2. En el repositorio, reemplace el código anterior por **el contenido** de `Sistema_Iglesia_Web_V2_7_1/`, incluyendo las carpetas `iglesia`, `templates` y `static`. Suba los archivos extraídos, no el ZIP. No suba `.venv`, archivos `.db`, respaldos, `secret.key`, fotos privadas ni credenciales. Elimine los archivos de logo del repositorio anterior.
3. En **Settings**, el directorio raíz debe apuntar a la carpeta que contiene `app.py`. Si los archivos están en la raíz del repositorio, deje **Root Directory** vacío. Runtime: **Python 3**.
4. Configure **Build Command**:

```sh
pip install -r requirements.txt
```

5. Configure **Start Command**:

```sh
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

6. En **Environment**, conserve/añada estas variables:

| Clave | Valor que debe colocar en Render |
| --- | --- |
| `DATABASE_URL` | La **Internal Database URL completa** de `iglesia-db`; no solo el hostname. |
| `SECRET_KEY` | Una clave aleatoria privada de al menos 32 caracteres. Use el generador de Render. |
| `ADMIN_INITIAL_PASSWORD` | Una contraseña elegida por usted de al menos 8 caracteres, necesaria únicamente si la base está vacía. |
| `IGLESIA_HTTPS` | `1` |
| `PYTHON_VERSION` | `3.12.12` |
| `TZ` | `America/Santo_Domingo` |

No escriba estas credenciales en archivos del repositorio. La base y el servicio deben estar en la misma región para usar la conexión interna. Después de crear o importar los usuarios, puede retirar `ADMIN_INITIAL_PASSWORD`: no modifica contraseñas existentes.

7. Configure **Health Check Path** como `/healthz`.
8. Guarde los cambios. Use **Manual Deploy → Deploy latest commit** si Render no comienza automáticamente.
9. En los logs debe aparecer el arranque de Gunicorn. Abra la URL habitual del servicio y luego `/healthz`: debe responder `{"status":"ok","version":"V2.7.1"}` (el orden de las claves puede variar).
10. Inicie sesión con su usuario importado, o con `admin` y la contraseña inicial que configuró si partió de una base nueva. Revise miembros, fotos, ministerios, usuarios y FOLIGRUC.
11. Registre un miembro de prueba, reinicie o vuelva a desplegar el servicio y verifique que continúa guardado. Envíelo a la papelera al terminar la comprobación.

En Render, la aplicación se detiene con una explicación si falta `DATABASE_URL` o `SECRET_KEY`: no cambia silenciosamente a un SQLite efímero. Las fotos optimizadas se guardan en PostgreSQL, por lo que no requieren un disco persistente para sobrevivir a los despliegues.

Referencia oficial de [despliegue Flask en Render](https://render.com/docs/deploy-flask) y [conexiones internas/externas de PostgreSQL](https://render.com/docs/postgresql-creating-connecting).

## 3. Uso local con SQLite

Sin `DATABASE_URL`, la aplicación crea `iglesia.db` junto a `app.py`:

```sh
python app.py
```

Abra `http://127.0.0.1:5000`. En Windows también puede usar `INICIAR_SISTEMA.bat`. En una base local nueva, el usuario inicial es `admin` y la contraseña inicial es `admin123`; el sistema obliga a cambiarla antes de continuar. Use esta opción solo para el arranque local. No exponga el servidor de desarrollo a Internet.

Para actualizar una base local antigua, conviértala a **un archivo nuevo**:

```sh
python manage.py convert-sqlite "/ruta/iglesia_anterior.db" "/ruta/iglesia_convertida.db" --photos "/ruta/static/profiles"
```

Omita `--photos` si no conserva esa carpeta. El destino no debe existir. Con el sistema detenido, copie `iglesia_convertida.db` a la carpeta nueva con el nombre `iglesia.db`. Conserve el archivo anterior. Las bases con FOLIGRUC antiguo deben pasar por esta conversión; no se modifican a ciegas al arrancar.

La clave local de sesión se genera en `secret.key`. No la suba al repositorio. Los respaldos locales usan la API consistente de SQLite, incluyendo las fotos ya importadas a la base. Con `python app.py` se generan copias automáticas locales y una copia diaria; en Gunicorn se requiere programar respaldos por separado.

## 4. Copias de seguridad y restauración PostgreSQL

En **COPIA DE SEGURIDAD**, el Administrador puede crear y descargar un respaldo lógico JSON de las 14 tablas de la aplicación, incluidas fotos, cuentas y FOLIGRUC. La lectura utiliza una instantánea consistente. No es una copia del archivo SQLite ni depende del disco efímero de Render.

También puede descargar un respaldo desde su computadora:

```sh
python manage.py --ask-database backup "respaldo_iglesia_2026-09-25.json"
```

Use un nombre nuevo: el comando no sobrescribe archivos existentes. Guarde respaldos fuera del servicio web en un lugar privado y pruebe periódicamente su restauración. Este JSON es un respaldo de la aplicación, no de roles, extensiones ni configuración global de PostgreSQL.

Para restaurar desde la aplicación en Render, entre como Administrador en **COPIA DE SEGURIDAD**, descargue primero una copia actual y guárdela en su computadora, seleccione el respaldo JSON, escriba `RESTAURAR` y confirme. Se reemplazan todos los datos de las tablas de la aplicación y se cierra la sesión. La operación se ejecuta en una transacción y revierte los cambios si falla. El respaldo anterior no se almacena automáticamente en el disco efímero del servidor.

Como alternativa, puede restaurar en otra base para comprobarla antes de cambiar el servicio:

1. Prepare una base PostgreSQL vacía y use su URL externa en los comandos siguientes.
2. Inicialice el esquema sin iniciar sesiones ni registrar información:

```sh
python manage.py --ask-database --ask-admin-password init
python manage.py --ask-database restore-empty "respaldo_iglesia_2026-09-25.json"
```

3. La restauración valida las columnas y relaciones, se ejecuta en una transacción y reajusta las secuencias de identificadores. Rechaza un destino que ya tiene información de trabajo. Un fallo revierte toda la operación.
4. Compruebe la copia restaurada; después cambie `DATABASE_URL` del servicio existente a la URL interna de esa base y genere una nueva `SECRET_KEY` para invalidar sesiones antiguas.
5. Vuelva a desplegar y verifique el acceso con los usuarios del respaldo. Mantenga la base anterior hasta confirmar la recuperación.

Para respaldar toda la base, use también `pg_dump`/`pg_restore` o las opciones de **Recovery** disponibles en Render. El cliente PostgreSQL debe ser de la misma versión principal que el servidor o compatible con ella. No restaure volcados sobre una base con información que deba conservarse.

Render ofrece recuperación y exportaciones administradas en bases de pago; las bases Free no incluyen esas capacidades. Consulte las [opciones oficiales de respaldo y recuperación](https://render.com/docs/postgresql-backups). Esta aplicación no programa automáticamente respaldos externos de PostgreSQL: configure la retención del proveedor o ejecute periódicamente el comando de respaldo en un entorno que conserve el archivo fuera del servicio.

## Registro de miembros por enlace y QR

El Administrador abre **MIEMBROS → ENLACE Y QR DE REGISTRO**, comparte la dirección pública `/registro-miembros` o descarga el QR SVG. Los datos enviados quedan pendientes en **Solicitudes**; solo un Administrador puede aprobarlos o descartarlos. Al aprobar se crea el miembro, se comprueba si ya existe la cédula y se registra la acción en el historial. El solicitante no obtiene acceso al sistema. Configure `PUBLIC_BASE_URL=https://SU-DOMINIO` si la dirección mostrada no coincide con el dominio público; no agregue la ruta al valor. Los respaldos JSON incluyen también las solicitudes pendientes.

## 5. Funciones incluidas

- FOLIGRUC asigna un código correlativo automático al crear cada estudiante (`FOL-000001`, `FOL-000002`, etc.); conserva los códigos ya registrados.
- Panel: totales, activos/inactivos, bautizados, nuevos ingresos, distribución por ministerio, próximos eventos y celebraciones de los próximos 30 días.
- Miembros: nombres/apellidos, cédula, contacto, dirección, nacimiento, ingreso, bautizo, ministerio, cargo, estado, observaciones y seguimiento; historial con fecha y usuario.
- Fotos: orientación corregida, recorte de 600 × 600 y compresión JPEG; almacenamiento en base de datos y acceso autenticado según permisos.
- Ministerios: encargado, asistente, notas, miembros y cargos. Las modificaciones de ministerios están reservadas al Administrador.
- Calendario mensual y eventos: fecha/hora, lugar, responsable, descripción y recordatorio interno. Los recordatorios se muestran en el sistema; no envían correo, SMS ni avisos push.
- Cumpleaños con panel de hoy, últimos 7 días, próximos 7 y 30 días, lista anual y acceso a WhatsApp; los del 29 de febrero se muestran el 28 de febrero en años no bisiestos.
- Reportes PDF/Excel por ministerio, estado, bautismo, rango de edad y período de ingreso. Reportes generales solo para Administrador; cada expediente FOLIGRUC permite exportar su propio historial según el acceso al estudiante.
- Papelera/restauración de miembros, sin eliminar definitivamente su historial ni liberar su cédula para duplicados.
- Contraseñas con hash, CSRF, consultas parametrizadas, bloqueo temporal tras intentos fallidos, cierre tras 30 minutos de inactividad y autorización comprobada en servidor.
- Solo Administrador crea usuarios y cambia permisos. Secretaría puede consultar los datos de todos los ministerios en sus módulos permitidos; un usuario de ministerio queda limitado a su ministerio y a eventos generales de solo lectura.
- Los módulos visibles para usuarios no administradores son exclusivamente INICIO, MIEMBROS, MINISTERIOS, FOLIGRUC, CUMPLEAÑOS y CALENDARIO & EVENTOS, según sus permisos. El cambio de contraseña está en **Mi cuenta**.
- Sin logo, Finanzas, Asistencia, QR de asistencia, Visitantes, Familias/Relaciones ni Buscador avanzado.

## 6. Tera, cámara y OCR

Conecte el Tera en modo teclado USB/Bluetooth. En **Nuevo miembro → Lector Tera USB / Bluetooth**, coloque el cursor y escanee. Se admite terminación Enter/Tab y el botón **LEER CÓDIGO**. Se interpretan cédulas de 11 dígitos, campos etiquetados y JSON reconocido; los formatos posicionales desconocidos no se adivinan.

Si el código incluye nombres, apellidos, nacimiento y número, se proponen esos valores. Si solo contiene el número, los demás campos quedan disponibles para completarlos. **ESCANEAR FRENTE DE CÉDULA** utiliza la cámara y Tesseract.js en el navegador. Se presenta una revisión editable antes de aplicar los datos al formulario. El sistema verifica duplicados al escribir y al guardar, incluyendo los registros de la papelera.

La imagen completa de la cédula no se envía al servidor ni se guarda. Solo vive en memoria durante la lectura. El motor OCR y el idioma español se descargan desde sus proveedores/CDN; se necesita Internet. La cámara requiere HTTPS o localhost y permiso del navegador. La lectura de códigos por cámara depende de `BarcodeDetector`; cuando el navegador no lo admite se puede usar Tera, OCR o entrada manual.

No se consulta una base de la JCE ni se promete recuperar información que no esté codificada o visible. El OCR puede equivocarse: revise siempre los cuatro campos. La lectura física del modelo Tera y una cédula real deben comprobarse en el equipo de la iglesia. Esta entrega se probó con datos sintéticos y lectura de texto simulada.

El JavaScript del lector está separado en archivos `.js`; la compilación Python se verifica con `SyntaxWarning` tratado como error, corrigiendo el problema del patrón `\D` incrustado en cadenas Python.

## 7. FOLIGRUC

Menú: Inicio, Estudiantes, Materias, Períodos e Inscripciones. Puede vincular un miembro o registrar un estudiante externo. Cada expediente conserva código, datos personales, congregación, estado, progreso, resultados e historial de cambios.

Los períodos duran tres meses desde la fecha de inicio. Las 15 materias están disponibles en cada período; se inscribe cada estudiante en las que le correspondan. Los resultados académicos se registran únicamente por estado: En curso, Aprobada o Reprobada. No se utilizan puntuaciones numéricas. Los intentos de otro período se conservan. Solo puede cerrarse un período cuando no tiene resultados pendientes; después queda bloqueada su modificación académica.

El Administrador puede usar **Registrar materia aprobada anteriormente**, con fecha opcional. Cuenta para el progreso sin inventar un período. La graduación requiere las 15 materias aprobadas. No se realiza promoción automática ni se obliga a repetir materias ya aprobadas.

Pénsum precargado según la imagen oficial aportada:

1. Sanidad Interior
2. Liderazgo Saludable
3. Salud Financiera
4. Ética Cristiana
5. Auto-Liderazgo, 21 cualidades de un líder
6. Ganador de Almas
7. Un líder como Jesús
8. Formación de Grupos de Crecimiento
9. Perfil de los Tres Monarcas
10. Los llamados a Enseñar
11. El Pase
12. Liderazgo, Ministerio y Batalla
13. Iglesia y su Comunidad
14. Mentoreo
15. Misiología

La materia Salud Financiera forma parte del pénsum; no habilita un módulo de Finanzas.

## 8. Validación y procedencia

La base es el proyecto modular V2.6 disponible y el trabajo local más reciente V2.7 del lector/OCR. Se integraron las especificaciones y el pénsum de las conversaciones de Iglesia Web/FOLIGRUC. No se reutilizaron secretos ni datos personales en el paquete.

Comprobaciones reproducibles:

```sh
python -W error::SyntaxWarning -m compileall -q app.py manage.py iglesia tests
python -m unittest discover -s tests -v
node tests/test_parser.js
```

La versión se validó con Python 3.12, 52 pruebas de servidor aprobadas y 12 escenarios del lector. Se probó arranque Gunicorn, consultas/escrituras y respaldo con PostgreSQL local mediante PGlite/psycopg, además de SQLite; PGlite no sustituye una prueba de carga ni una comprobación contra su instancia real de Render. Se revisaron en navegador el panel, la ficha móvil, revisión del lector y bloqueo de duplicados. La importación del esquema anterior se comprobó con fixtures sintéticos y con una copia temporal del respaldo disponible, sin modificar el original ni incluirlo en el ZIP.

El archivo `VALIDACION.md` resume los alcances y límites de las pruebas. **No se ha desplegado esta entrega en su servicio de Render ni se ha conectado a sus credenciales reales.**


## 9. Hostinger VPS

Esta edición incluye `HOSTINGER_INSTALACION.md` y archivos de ejemplo en `deploy/` para ejecutar con PostgreSQL, Gunicorn, systemd, Nginx y HTTPS en un VPS de Hostinger. En producción configure `HOSTINGER=1`, `DATABASE_URL`, `SECRET_KEY` e `IGLESIA_HTTPS=1`.

## Cambios V2.7.6.1
- Administrador: crear, editar y eliminar usuarios, con protección contra autoeliminación y contra quedar sin administrador activo.
- Líder de Ministerio: acceso limitado a su ministerio mediante controles del servidor existentes en la base V2.7.6.
- Ministerios: opción para agregar una ficha de miembro existente que todavía no tenga ministerio, sin duplicarla.
- Miembros: campo Estado civil con Casado/a, Soltero/a, Viudo/a y Unión Libre.
- Auditoría: creación, edición y eliminación de usuarios y asignación de miembros a ministerios quedan registradas.


## V2.7.6.1 - Conversiones
Se agregó registro histórico de conversiones, tarjeta CONVERSIONES ESTE MES en Inicio, filtros por mes/año/ministerio/nombre, totales y exportación PDF.


## V2.7.6.1 — Liderazgo de ministerios
- Los líderes pueden abrir MIEMBROS, registrar nuevos miembros y editar únicamente miembros de su ministerio.
- La asignación del ministerio del líder se fuerza en servidor; no puede editar miembros de otros ministerios.
- Eliminar miembros continúa reservado al Administrador.
- En Nuevos Creyentes, al agregar miembros, los convertidos pendientes sin ministerio aparecen primero y se identifican por fecha de conversión, sin duplicar fichas.


## V2.7.6.1 — QR & LINK (base Ministerios con Tarjetas)
- Nuevo acceso independiente **QR & LINK** en el menú izquierdo, solo para Administrador.
- Muestra QR, link público, copiar link, descargar QR y abrir formulario.
- Solicitudes recibidas se revisan con ACEPTAR / RECHAZAR.
- Solo al aceptar se crea el miembro oficial.
- No se modificó la lógica de la página INICIO.

## V2.9
Actualización de seguridad y roles. Roles oficiales: Administrador (todo), Pastor/a y Asistente Pastora (Miembros, Ministerios, Cumpleaños, FOLIGRUC y Reportes, con crear/editar/borrar dentro de esos módulos), y Líder Ministerio (solo su ministerio, con crear/editar/borrar sus miembros). El líder entra directamente a su ministerio. Se reforzaron encabezados HTTP (CSP, HSTS en HTTPS, Permissions-Policy), se conservan CSRF, cookies seguras, expiración de sesión, bloqueo temporal y auditoría. Login institucional renovado con Efesios 3:17.

## V2.9.1
- Contraseña mínima de 8 caracteres.
- Lista de miembros simplificada: Código, Nombre, Apellido, Teléfono, Estado, Fecha de ingreso y Acciones.
- Cédula fuera de la lista principal; permanece en VER/EDITAR.
- Eliminación de miembro movida al perfil individual.
- Mejoras visuales y móviles en Miembros.
- Ministerios rediseñados con tarjetas y administración compacta.
- Hasta 3 encargados por ministerio, seleccionados de miembros existentes: Líder y dos Asistentes.


## V2.9.2 — Ficha de miembro e importación Mayo 2026
- Bautizado Sí/No y nuevos estados aprobados.
- Importador idempotente para 496 registros de ACTUALIZACIÓN MAYO 2026.
- Fecha de ingreso no se inventa; datos ausentes permanecen vacíos.
- Ejecutar primero `python manage.py import-mayo-2026 --dry-run` y luego `python manage.py import-mayo-2026`.


## V2.9.6
- Importación automática, única e idempotente de ACTUALIZACIÓN MAYO 2026 al iniciar.
- Los 496 registros fuente se comparan con miembros existentes; duplicados se omiten.
- La vista MIEMBROS no usa LIMIT 50 ni paginación: muestra todos los miembros autorizados por el rol.
- El buscador filtra sobre todos los miembros cargados y autorizados.


## V2.9.7
- CONVERTIDOS ya no administra una lista separada de Líderes de Nuevos Creyentes.
- Los usuarios responsables del Ministerio de Nuevos Creyentes pueden acceder al módulo CONVERTIDOS según su ministerio asignado.
- Se eliminó el campo Iglesia de la interfaz, registro nuevo y PDF de Convertidos.
- Se mantienen registro, seguimiento, historial, estadísticas mensuales/anuales y reporte PDF.
