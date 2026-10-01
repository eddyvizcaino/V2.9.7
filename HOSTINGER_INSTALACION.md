# Sistema Iglesia Web V2.7.6 — Hostinger VPS

Esta edición está preparada para Ubuntu en Hostinger VPS con PostgreSQL, Gunicorn y Nginx.
FOLIGRUC no utiliza puntuaciones numéricas; los resultados académicos se manejan por estado.

## Variables de producción
Configure en `/etc/iglesia-web.env`:

```
DATABASE_URL=postgresql://iglesia:CONTRASENA@127.0.0.1:5432/iglesia
SECRET_KEY=CAMBIE_ESTA_CLAVE_POR_UNA_ALEATORIA_DE_64_CARACTERES
IGLESIA_HTTPS=1
HOSTINGER=1
TZ=America/Santo_Domingo
```

Proteja el archivo: `sudo chmod 600 /etc/iglesia-web.env`.

## Instalación base

```
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx
sudo mkdir -p /var/www/iglesia-web
sudo chown -R $USER:$USER /var/www/iglesia-web
```

Copie el contenido del ZIP a `/var/www/iglesia-web` y ejecute:

```
cd /var/www/iglesia-web
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## PostgreSQL
Cree una base y usuario PostgreSQL con una contraseña fuerte. Luego coloque la URL resultante en `DATABASE_URL`.
Inicialice una base nueva con:

```
set -a; source /etc/iglesia-web.env; set +a
source /var/www/iglesia-web/.venv/bin/activate
python manage.py --ask-admin-password init
```

Para importar un SQLite anterior use el comando `manage.py import-sqlite` y siga README.md. Conserve siempre el respaldo original.

## systemd
Copie `deploy/iglesia-web.service` a `/etc/systemd/system/iglesia-web.service`, luego:

```
sudo systemctl daemon-reload
sudo systemctl enable --now iglesia-web
sudo systemctl status iglesia-web
```

## Nginx
Copie `deploy/nginx-iglesia-web.conf` a `/etc/nginx/sites-available/iglesia-web`, cambie `SU_DOMINIO.com`, active el sitio y pruebe:

```
sudo ln -s /etc/nginx/sites-available/iglesia-web /etc/nginx/sites-enabled/iglesia-web
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS
Después de apuntar el dominio al VPS, instale Certbot y genere el certificado:

```
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d SU_DOMINIO.com -d www.SU_DOMINIO.com
```

Compruebe `https://SU_DOMINIO.com/healthz` y luego inicie sesión.
