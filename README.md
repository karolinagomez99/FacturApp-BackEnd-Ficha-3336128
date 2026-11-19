# FacturApp Backend

API de facturación desarrollada con Flask, SQLAlchemy y MySQL. Los endpoints de la API están bajo `/api/v1`.

## Requisitos

- Python 3.10 o superior
- MySQL 8 o compatible, ejecutándose localmente
- Postman para importar y probar la colección del directorio `postman`

## Preparación en Windows

Desde la raíz del proyecto, abre PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edita `.env` con el usuario y la contraseña de tu MySQL, y define `JWT_SECRET_KEY` con una cadena aleatoria larga. No compartas ni subas ese archivo al repositorio.

## Conectar MySQL con phpMyAdmin

1. Inicia MySQL desde el panel de XAMPP/WAMP (si lo usas) y abre `http://localhost/phpmyadmin`.
2. En la pestaña **SQL**, crea la base de datos:

```sql
CREATE DATABASE facturapp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. En `.env`, configura `DATABASE_URL` con el usuario, contraseña, host y puerto que usas para MySQL. El formato es `mysql+pymysql://usuario:contraseña@127.0.0.1:3306/facturapp`. Si la contraseña contiene caracteres reservados de URL, codifícalos antes de escribirla.

phpMyAdmin es la interfaz para administrar la base de datos; Flask se conecta directamente al servidor MySQL usando `DATABASE_URL`.

Al iniciar, la aplicación crea las tablas que falten. Para probar la creación de productos, registra una categoría inicial en MySQL:

```sql
INSERT INTO categories (name) VALUES ('General');
```

## Iniciar la API

Con MySQL iniciado, el entorno virtual activado y `.env` configurado, inicia Flask:

```powershell
python -m flask --app src.app run --debug
```

La API queda disponible en `http://127.0.0.1:5000`. También se puede iniciar con `python -m src.app`.

## Probar con Postman

Importa `postman/TestF1.postman_collection.json` en Postman y usa sus solicitudes **Auth > Register** y **Auth > Login**. La colección apunta a `http://127.0.0.1:5000/api/v1`; después del login, guarda automáticamente el token para las solicitudes protegidas. También puedes importar las otras colecciones de `postman` para probar sus historias de usuario.

## Primer administrador

1. Importa `postman/TestF1.postman_collection.json` en Postman.
2. Ejecuta **Auth > Register** para registrar la cuenta que será administradora.
3. En MySQL, asigna el rol inicial directamente:

   ```sql
   UPDATE users SET role = 'ADMIN' WHERE email = 'admin@facturapp.com';
   ```

4. Ejecuta **Auth > Login** en la colección TestF1 y asígnale el rol `SELLER` a otro usuario de prueba.
5. Importa `postman/HU2001-HU2007.postman_collection.json` y ejecuta **Auth > Login** en esa colección. Cada colección mantiene sus propias variables de token.

Para registrar un vendedor de prueba, ejecuta **Auth > Register** con otro correo desde TestF1 y asígnale el rol `SELLER` desde **Users > Assign Role** (actualiza el id de la URL si hace falta).

Las cuentas nuevas comienzan con rol `PENDING`; un administrador puede asignarles `SELLER` o `ADMIN` mediante `PUT /api/v1/users/<id>/role`.

## API

| Recurso | Endpoints principales |
| --- | --- |
| Autenticación | `POST /api/v1/register`, `POST /api/v1/login` |
| Productos | `GET/POST /api/v1/products`, `GET/PUT /api/v1/products/<id>` |
| Clientes | `GET/POST /api/v1/clients`, `GET/PUT /api/v1/clients/<id>` |
| Facturas | `GET/POST /api/v1/invoices`, `GET/PUT/DELETE /api/v1/invoices/<id>`, `PUT /api/v1/invoices/<id>/complete` |
| Detalles | `GET/POST /api/v1/invoices/<id>/details`, `PUT/DELETE /api/v1/invoices/<id>/details/<detail_id>` |

Las solicitudes protegidas requieren `Authorization: Bearer <access_token>`. Los permisos por rol y los códigos de respuesta siguen las historias HU2001–HU2007.

## Pruebas

Las pruebas automatizadas usan SQLite en memoria y no requieren levantar MySQL:

```powershell
python -m unittest discover -s tests -v
```

## Ramas y entorno

Este trabajo se mantiene en `develop`. El entorno `.venv` y las credenciales locales de `.env` no se versionan; `requirements.txt` permite reconstruir el entorno.
