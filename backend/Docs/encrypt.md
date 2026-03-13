Aquí tienes el contenido completo del archivo Markdown listo para copiar y guardar como `Security_Architecture_Django_GraviTea.md`.

# Protocolo de Arquitectura de Seguridad y Criptografía para GraviTea ERP

**Proyecto:** GraviTea ERP (SaaS Multi-tenant)
**Stack Tecnológico:** Django 5.2.9, Python 3.14.3, PostgreSQL 18.1, Google Cloud Platform (GCP), Next.js, Electron.
**Versión del Documento:** 1.1
**Objetivo:** Definir los estándares de protección de datos, cifrado a nivel de aplicación y aislamiento de inquilinos para ser procesado por el equipo de desarrollo y herramientas de IA (NotebookLM).

---

## 1. Introducción y Estrategia de Defensa

Este protocolo establece los lineamientos de seguridad para el backend de GraviTea ERP. La estrategia adoptada es **Defensa en Profundidad (Defense in Depth)**.

Aunque la infraestructura (GCP Cloud SQL) provee *Encryption at Rest* (cifrado de disco), esto no protege contra vectores de ataque donde un actor malicioso obtiene acceso a las credenciales de la base de datos o realiza un volcado (SQL Dump). Por ello, se implementa **Cifrado a Nivel de Aplicación (Application-Level Encryption)** para Datos de Identificación Personal (PII) y datos fiscales sensibles.

### 1.1 Clasificación de Datos (Data Sensitivity)

Basado en el esquema de base de datos (`Database_schemas.md`), los datos se clasifican en tres niveles:

1.  **Público/Interno (Plain):** Datos estructurales y comerciales no sensibles (nombres de productos, configuración de tenant, precios, fechas). Se almacenan en texto plano.
2.  **Identificable/Buscable (Hash):** Datos que requieren confidencialidad pero deben ser buscables exactamente (CUIT, Email). Se almacenan como un **HASH determinista** (HMAC-SHA256) para permitir índices de búsqueda (`Blind Indexing`).
3.  **Confidencial (Encrypted App):** Datos altamente sensibles que solo deben ser legibles por el usuario autorizado y nunca por administradores de BD o logs (Detalles de pasarelas de pago, Tokens de AFIP, direcciones personales). Se almacenan cifrados (**AES-256-GCM**).

---

## 2. Criptografía a Nivel de Aplicación (Columnas `_encrypted`)

Para las columnas marcadas como `encrypted_app` en el esquema, el cifrado y descifrado ocurre en la memoria del servidor Django.

### 2.1 Estándar de Cifrado
Se utilizará criptografía simétrica autenticada.

* **Algoritmo:** AES-256-GCM (Galois/Counter Mode).
* **Justificación:** AES-GCM provee confidencialidad (nadie puede leerlo) e integridad (nadie puede modificar el texto cifrado sin que el sistema lo note). Es superior a modos antiguos como CBC que son vulnerables a ataques de oráculo de relleno (Padding Oracle Attacks).
* **Librería Recomendada:** `django-cryptography` (wrapper de `cryptography`).

### 2.2 Gestión de Claves (Key Management)
La seguridad del cifrado depende enteramente de la protección de la llave maestra (Master Key).

* **Almacenamiento:** La llave **NUNCA** debe estar hardcodeada en el código fuente, ni en el `Dockerfile`, ni en el repositorio Git.
* **Proveedor:** Se utilizará **Google Secret Manager**.
* **Inyección:** Durante el arranque de la aplicación (boot), Django recuperará la clave desde la API de GCP y la mantendrá en memoria (Variable de entorno volátil `CRYPTOGRAPHY_KEY`).

### 2.3 Implementación Técnica

Configuración en `settings.py`:
```python
# settings.py
import os
# La clave se inyecta desde GCP Secret Manager al entorno de ejecución
CRYPTOGRAPHY_KEY = os.getenv('FIELD_ENCRYPTION_KEY') 
CRYPTOGRAPHY_SALT = os.getenv('FIELD_ENCRYPTION_SALT')
````

Definición en `models.py`:

```python
from django.db import models
from django_cryptography.fields import encrypt

class Supplier(models.Model):
    # El campo se cifra transparente al guardar y se descifra al acceder
    # En la DB se verá como un blob binario ininteligible.
    tax_id_encrypted = encrypt(models.CharField(max_length=50, blank=True))
```

-----

## 3\. Estrategia de Blind Indexing (Columnas `_hash`)

Dado que los datos cifrados con AES generan resultados aleatorios (por el vector de inicialización IV) cada vez que se guardan, no es posible realizar consultas SQL del tipo `WHERE tax_id_encrypted = '20-12345678-9'`. Para solucionar esto, se implementa **Blind Indexing** mediante columnas espejo de hash.

### 3.1 Algoritmo de Hashing

Para las columnas marcadas como `hash` en el esquema (ej: `tax_id_hash`, `email_hash`).

  * **Algoritmo:** HMAC-SHA256 (Hash-based Message Authentication Code).
  * **Pepper (Clave Secreta):** Se utiliza una `HASHING_PEPPER_KEY` (distinta a la de cifrado) específica como clave del HMAC.
  * **Justificación:** Un hash simple (SHA256) es vulnerable a ataques de tablas arcoíris o diccionarios precomputados. HMAC requiere la clave secreta para generar el hash, haciendo imposible revertir o adivinar el hash sin acceso al servidor de aplicaciones.

### 3.2 Normalización de Datos

Para garantizar que las búsquedas sean efectivas (User Experience), el dato de entrada debe normalizarse antes de hashear:

1.  Convertir a minúsculas (`.lower()`).
2.  Eliminar espacios en blanco al inicio/final (`.strip()`).
3.  Codificar a UTF-8.

### 3.3 Implementación (Helper Function)

```python
import hashlib
import hmac
from django.conf import settings

def compute_blind_index(plaintext):
    """
    Genera un hash determinista seguro para búsquedas exactas.

    NOTE: Function renamed from generate_blind_index to compute_blind_index.
    Actual implementation is in apps/core/encryption/utils.py
    """
    if not plaintext:
        return None
        
    # 1. Normalización
    normalized = str(plaintext).strip().lower().encode('utf-8')
    
    # 2. HMAC-SHA256
    msg_hash = hmac.new(
        key=settings.HASHING_PEPPER_KEY.encode('utf-8'),
        msg=normalized,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return msg_hash
```

-----

## 4\. Seguridad en Autenticación y Sesiones

### 4.1 Hashing de Contraseñas

  * **Algoritmo:** Argon2.
  * **Configuración:** Django por defecto usa PBKDF2. Se debe instalar la librería `argon2-cffi` y configurar `PASSWORD_HASHERS` en `settings.py` para priorizar `Argon2PasswordHasher`. Argon2 es resistente a ataques por GPU/ASIC.

### 4.2 Protección de Sesiones (Cookies)

Dado que el cliente puede ser un navegador o Electron, las cookies deben configurarse con máxima restricción:

  * `SESSION_COOKIE_SECURE = True`: Solo viajar por HTTPS.
  * `SESSION_COOKIE_HTTPONLY = True`: No accesible vía JavaScript (`document.cookie`), mitiga robo de sesión por XSS.
  * `SESSION_COOKIE_SAMESITE = 'Lax'` (o `'Strict'`): Mitiga ataques CSRF.

-----

## 5\. Aislamiento Multi-Tenant

La seguridad más crítica en GraviTea es evitar la fuga de datos entre inquilinos.

### 5.1 Estrategia de Aislamiento Lógico

Se utilizará un aislamiento a nivel de fila (`Row-Level Isolation`) forzado por la aplicación.

1.  **Middleware de Identificación:** Cada request debe ser interceptado para identificar el `tenant_id` (basado en subdominio o token JWT) y almacenarlo en el contexto local del thread (`threading.local` o `contextvars`).
2.  **Managers Personalizados:** Todos los modelos deben heredar de un Manager base que inyecte automáticamente el filtro `.filter(tenant_id=current_tenant_id)` en cada consulta (`QuerySet`).

### 5.2 Validación de Clave Foránea

En operaciones de escritura (Create/Update), se debe validar que las Foreign Keys (ej. `branch_id`, `supplier_id`) pertenezcan al mismo `tenant_id` del objeto que se está creando, para evitar referencias cruzadas inseguras (Insecure Direct Object References - IDOR).

-----

## 6\. Protección de API (Next.js / Electron)

### 6.1 CORS (Cross-Origin Resource Sharing)

  * **Herramienta:** `django-cors-headers`.
  * **Política:** Whitelist estricta. Solo permitir los dominios controlados (ej. `app.gravitea.com`) y, en el caso de Electron, verificar si se requiere permitir esquemas locales (`file://` o `app://`) de forma controlada, o preferiblemente manejar la comunicación Electron \<-\> Django vía API REST segura sobre HTTPS exclusivamente.

### 6.2 Content Security Policy (CSP)

  * **Herramienta:** `django-csp`.
  * **Política:** Implementar cabeceras CSP para restringir las fuentes de ejecución de scripts, preveniendo que un atacante inyecte scripts maliciosos que exfiltren datos del cliente Electron o Web.

-----

## 7\. Resumen de Librerías para `requirements.txt`

| Librería | Función Crítica |
| :--- | :--- |
| `django-cryptography` | Cifrado de campos (AES-256). |
| `argon2-cffi` | Hashing de contraseñas robusto. |
| `google-cloud-secret-manager` | Gestión segura de secretos en GCP. |
| `django-csp` | Cabeceras de seguridad (CSP). |
| `django-axes` | Protección contra fuerza bruta (Rate Limiting). |
| `django-cors-headers` | Control de acceso CORS para el frontend. |

```