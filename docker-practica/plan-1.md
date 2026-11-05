# Plan 1: Del script al servicio (modelo de crédito con FastAPI y Docker)

**Objetivo:** dejar el modelo de morosidad disponible como API REST en un contenedor
(`credito-api:1.0`), reunir las evidencias y responder las preguntas de verificación.

**Regla:** `entrenar.py` y `predecir_local.py` no se modifican.

---

## 1. Estado actual (revisado el 2026-11-04)

Parte del trabajo ya está hecho, así que este plan se centra en lo que falta.

| Requisito                                    | Estado         | Detalle                                                           |
|----------------------------------------------|----------------|-------------------------------------------------------------------|
| `GET /health`                                | Cumple         | Responde `{"status":"ok"}`                                        |
| `POST /predecir` con contrato Pydantic       | Cumple         | Devuelve `moroso` y `probabilidad`                                |
| Bonus: validaciones con `Field`              | Corregir       | `antiguedad_laboral` rechaza 0 (ver 2.1)                          |
| `requirements.txt` con versiones `==`        | Mejorable      | Comentario obsoleto; dependencias transitivas sin fijar (ver 2.2) |
| Dockerfile: base `python:3.11-slim`          | Cumple         |                                                                   |
| Dockerfile: dependencias antes que el código | Cumple         |                                                                   |
| Dockerfile: usuario no-root                  | **Falta**      | `docker exec credito whoami` devuelve `root`                      |
| `.dockerignore`                              | **Incompleto** | Falta `__pycache__`                                               |
| `uvicorn` en `0.0.0.0`                       | Cumple         |                                                                   |
| Imagen `credito-api:1.0`                     | Reconstruir    | Hoy pesa 602 MB, pero no incluye las correcciones                 |
| Evidencias                                   | **Falta**      | Aún no se han guardado                                            |
| Respuestas a las preguntas                   | **Falta**      |                                                                   |

Entorno: el `.venv` usa Python 3.11.9, correcto. El Python global es 3.14, que **no** sirve
para este proyecto según el README. Docker 29.9.2 está disponible.

---

## 2. Parte A: ajustes al código

### 2.1 `api.py`

- Cambiar `antiguedad_laboral` de `gt=0` a `ge=0`. Hoy se rechaza con 422 a quien acaba de
  empezar a trabajar, aunque es un valor válido: los datos de entrenamiento usan el rango
  0 a 35 (`entrenar.py:37`).
- Precisar las descripciones de `Field` con sus unidades (USD, años, meses).

### 2.2 `requirements.txt`

- Quitar el comentario "OJO: tendrás que agregar...", que ya no aplica.
- Fijar también `scipy==1.17.1` y `threadpoolctl==3.7.0`, las versiones que ya tiene la imagen.
  Scikit-learn las necesita para cargar y ejecutar el modelo, y sin fijarlas un rebuild futuro
  podría instalar otras.

### 2.3 Verificación local

El contenedor `credito` ocupa hoy el puerto 8000, así que hay que detenerlo primero:

```powershell
docker rm -f credito
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --port 8000
curl.exe http://localhost:8000/health     # desde otra terminal
```

Detener `uvicorn` (Ctrl+C) antes de seguir con la Parte B.

---

## 3. Parte B: el contenedor

### 3.1 `Dockerfile` (agregar el usuario no-root)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py .
COPY modelo_credito.joblib .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Los archivos quedan como propiedad de `root` y `appuser` solo puede leerlos. Así, un proceso
comprometido no podría alterar el código ni el modelo.

### 3.2 `.dockerignore`

```
.venv/
venv/
.git
.gitignore
.env
__pycache__/
*.pyc
.idea/
evidencias/
predecir_local.py
entrenar.py
README.md
ENTREGA.md
command
plan-1
Dockerfile
.dockerignore
```

`modelo_credito.joblib` **no** debe aparecer en esta lista, porque la imagen lo necesita.

### 3.3 Construir y anotar el tamaño

```powershell
docker build -t credito-api:1.0 .
docker images credito-api
```

Criterio: muy por debajo de 1 GB. Si la tabla muestra dos tamaños, anotar `DISK USAGE`
(hoy 602 MB) y mencionar también `CONTENT SIZE` (hoy 140 MB).

Para demostrar la caché de capas, se puede cambiar algo menor en `api.py` y reconstruir:
el paso `pip install` debe aparecer como `CACHED`. Sirve de evidencia para la pregunta 1.

---

## 4. Parte C: consumir el modelo por API

```powershell
docker run -d -p 8000:8000 --name credito credito-api:1.0
docker ps
docker exec credito whoami          # debe devolver appuser
```

**Aviso para Windows:** en PowerShell 5.1, `curl` es un alias de `Invoke-WebRequest` y las
comillas simples del enunciado no funcionan igual. Hay dos alternativas: ejecutar los comandos
de abajo tal cual en **Git Bash**, o usar `curl.exe` con el JSON en un archivo (`-d "@bajo.json"`).

### Casos de prueba

Probados con la imagen actual; se deben repetir con la imagen nueva.

| Caso                       | JSON                                                                                                             | Resultado actual                         |
|----------------------------|------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| Bajo riesgo                | `{"ingreso_mensual":3500,"deuda_actual":500,"antiguedad_laboral":10,"monto_solicitado":4000,"plazo_meses":36}`   | `moroso: 0`, probabilidad ≈ 0.015        |
| Alto riesgo                | `{"ingreso_mensual":800,"deuda_actual":6000,"antiguedad_laboral":0.5,"monto_solicitado":15000,"plazo_meses":12}` | `moroso: 1`, probabilidad ≈ 0.973        |
| Inválido: ingreso negativo | `{"ingreso_mensual":-100,"deuda_actual":500,"antiguedad_laboral":10,"monto_solicitado":4000,"plazo_meses":36}`   | 422, `greater_than`                      |
| Inválido: campo faltante   | `{"deuda_actual":500,"antiguedad_laboral":10,"monto_solicitado":4000,"plazo_meses":36}`                          | 422, `missing`                           |
| Regresión: antigüedad 0    | `{"ingreso_mensual":3500,"deuda_actual":500,"antiguedad_laboral":0,"monto_solicitado":4000,"plazo_meses":36}`    | Hoy 422; tras el ajuste 2.1 debe ser 200 |

```bash
curl -i -X POST http://localhost:8000/predecir \
  -H 'Content-Type: application/json' \
  -d '<JSON del caso>'
```

### Documentación interactiva

Abrir http://localhost:8000/docs, ejecutar `POST /predecir` con "Try it out" y tomar la captura
donde se vean la petición y la respuesta 200.

---

## 5. Evidencias (carpeta `evidencias/`)

| Archivo                | Contenido               | Comando                           |
|------------------------|-------------------------|-----------------------------------|
| `docker-images.txt`    | Tamaño de la imagen     | `docker images credito-api`       |
| `docker-ps.txt`        | Contenedor en estado Up | `docker ps`                       |
| `health.txt`           | Respuesta de salud      | `curl -i .../health`              |
| `curl-bajo-riesgo.txt` | Solicitante válido 1    | Caso bajo riesgo                  |
| `curl-alto-riesgo.txt` | Solicitante válido 2    | Caso alto riesgo                  |
| `curl-invalido.txt`    | Errores 422             | Ingreso negativo y campo faltante |
| `docs.png`             | Captura de `/docs`      | Manual, en el navegador           |

---

## 6. Preguntas de verificación (redactar en `ENTREGA.md`)

1. **`requirements.txt` antes que `api.py`:** Docker reutiliza cada capa hasta encontrar la
   primera que cambió, y a partir de ahí reconstruye todas las siguientes. Como el código cambia
   mucho más que las dependencias, copiarlo después evita reinstalarlas. Al revés, cualquier
   cambio en `api.py` invalidaría la caché y repetiría todo el `pip install`.
2. **El modelo sí, el dataset no:** `modelo_credito.joblib` se necesita en cada predicción. El
   dataset solo se usa para entrenar: dentro de la imagen aumentaría su tamaño sin aportar nada
   al servicio y expondría datos sensibles de clientes a quien tenga acceso a ella. El servicio
   entrega inferencia; el entrenamiento es otra etapa.
3. **`--host 0.0.0.0`:** hace que uvicorn escuche en todas las interfaces del contenedor,
   incluida la que recibe el tráfico publicado con `-p`. Con `127.0.0.1` solo aceptaría
   conexiones desde dentro del propio contenedor: seguiría en estado Up, pero el `curl` desde
   el host fallaría.
4. **Quién rechaza el ingreso negativo:** FastAPI/Pydantic, con un 422. Docker solo transporta
   el tráfico y no conoce el contenido. El modelo no valida reglas de negocio: un
   RandomForest devolvería una predicción con apariencia válida para un ingreso negativo.
   Rechazarlo antes evita decisiones de crédito basadas en datos erróneos y le da al cliente un
   error claro sobre qué campo corregir.
5. **Ventajas frente a `predecir_local.py`:**
   - Integración: cualquier sistema, como la web de créditos, lo consume por HTTP sin usar Python.
   - Reproducibilidad: mismo entorno y versiones en cualquier máquina, sin "en mi máquina funciona".
   - Sin edición manual: los datos llegan en la petición, lo que elimina errores al tocar el script.
   - Validación automática de la entrada y documentación en `/docs`.
   - Operación: `/health` permite monitorearlo y orquestarlo, y puede escalarse con más contenedores.

---

## 7. Entrega final

**Incluir:** `api.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `ENTREGA.md`, `evidencias/`.
También se puede dejar el material original (`entrenar.py`, `README.md`).

**Excluir:** `.venv/`, `modelo_credito.joblib`, `.idea/`, `__pycache__/`.

Como el modelo no se entrega, quien revise debe ejecutar `python entrenar.py` antes de
`docker build`; de lo contrario, `COPY modelo_credito.joblib .` fallará. Conviene indicarlo en
`ENTREGA.md` y comprobarlo desde una copia limpia de la carpeta.

---

## 8. Orden de ejecución

1. [x] Corregir `api.py` y `requirements.txt` (2.1 y 2.2).
2. [x] Eliminar el contenedor actual y verificar la API en local (2.3).
3. [x] Actualizar `Dockerfile` y `.dockerignore` (3.1 y 3.2).
4. [x] Reconstruir `credito-api:1.0` y anotar el tamaño (3.3).
5. [x] Ejecutar el contenedor y confirmar `appuser` (sección 4).
6. [x] Correr los 5 casos de prueba y guardar las evidencias (secciones 4 y 5).
7. [x] Tomar la captura de `/docs` (manual).
8. [x] Redactar `ENTREGA.md` con las respuestas (sección 6).
9. [x] Armar la carpeta de entrega y probarla desde una copia limpia (sección 7).

## 9. Fuera de alcance

Autenticación, HTTPS, CI/CD, `docker-compose`, colecciones de Postman y reentrenamiento: el
enunciado no los pide y `curl` junto con `/docs` cubren la demostración.
