# Entrega: Del script al servicio (modelo de crédito)

**Módulo:** ML-Ops y Puesta en Producción · Clase 3

El modelo de morosidad ahora funciona como una API REST (FastAPI) dentro de un contenedor
Docker (`credito-api:1.0`), y cualquier aplicación puede consumirlo por HTTP.

## Cómo ejecutarlo

`modelo_credito.joblib` no se incluye en la entrega, así que hay que generarlo antes de
construir la imagen. Sin ese paso, `docker build` falla en `COPY modelo_credito.joblib .`.
Se requiere Python 3.10 a 3.12.

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python entrenar.py               # genera modelo_credito.joblib

docker build -t credito-api:1.0 .
docker run -d -p 8000:8000 --name credito credito-api:1.0
curl http://localhost:8000/health
```

## Decisiones de empaquetado

| Buena práctica | Aplicación |
|---|---|
| Base ligera con versión fijada | `python:3.11-slim` |
| Orden de capas para la caché | `requirements.txt` y `pip install` van antes que `api.py` y el modelo |
| `.dockerignore` | Excluye `.venv`, `.git`, `__pycache__` y los archivos que el servicio no usa |
| Usuario no-root | `USER appuser` (uid 1000); `/app` pertenece a `root` y `appuser` no puede escribir en él |

Además, todas las dependencias directas de ejecución tienen versión fijada con `==`.

**Bonus (validaciones con `Field`):** el ingreso, el monto y el plazo deben ser mayores que 0;
la deuda y la antigüedad deben ser mayores o iguales a 0. La antigüedad admite 0 porque alguien
recién contratado es un solicitante válido.

## Evidencias

Todas están en la carpeta `evidencias/`.

| Prueba | Resultado | Archivo |
|---|---|---|
| Tamaño de la imagen | 602 MB en disco, 140 MB de contenido comprimido | `docker-images.txt` |
| Estado del contenedor | Up, puerto 8000 publicado | `docker-ps.txt` |
| Usuario del proceso | `appuser` (uid 1000) | `usuario-contenedor.txt` |
| `GET /health` | 200, `{"status":"ok"}` | `health.txt` |
| Solicitante de bajo riesgo | 200, `moroso: 0`, probabilidad 0.0152 | `curl-bajo-riesgo.txt` |
| Solicitante de alto riesgo | 200, `moroso: 1`, probabilidad 0.9733 | `curl-alto-riesgo.txt` |
| Ingreso negativo y campo faltante | 422 en ambos casos | `curl-invalido.txt` |
| Antigüedad igual a 0 | 200, `moroso: 0`, probabilidad 0.1150 | `curl-antiguedad-cero.txt` |
| Documentación interactiva | Capturas de `/docs`: `GET /health` y `POST /predecir` con respuesta 200 | `Evidencia_1.png`, `Evidencia_2.png` |
| Construcción de la imagen | Registro completo | `docker-build.txt` |
| Caché de capas tras cambiar `api.py` | `pip install` aparece como `CACHED` | `docker-build-cache.txt` |

## Preguntas de verificación

### 1. ¿Por qué `requirements.txt` se copia e instala antes que `api.py`?

Docker reutiliza las capas hasta encontrar la primera que cambió, y desde ahí reconstruye todas
las siguientes. El código cambia mucho más que las dependencias, así que al copiarlo después, un
cambio en `api.py` no obliga a reinstalar nada.

Si se hace al revés, cada cambio en `api.py` invalida la caché y repite todo el `pip install`.
Aquí la instalación tardó unos 15 segundos sin caché, y al cambiar `api.py` ese paso apareció como
`CACHED` (`docker-build-cache.txt`).

### 2. ¿Por qué `modelo_credito.joblib` sí va en la imagen, pero el dataset no?

El modelo se usa en cada predicción: sin él, el servicio no funciona. El dataset solo se necesita
para entrenar, que es una etapa anterior y separada. Incluirlo aumentaría el tamaño de la imagen
sin aportar nada al servicio y, con datos reales de un banco, expondría información sensible de
clientes a cualquiera con acceso a la imagen.

### 3. ¿Por qué el `CMD` usa `--host 0.0.0.0`?

Para que uvicorn escuche en todas las interfaces de red del contenedor, incluida la que recibe el
tráfico publicado con `-p 8000:8000`. Con el valor por defecto (`127.0.0.1`), solo aceptaría
conexiones desde dentro del propio contenedor: `docker ps` lo mostraría en estado Up, pero el
`curl` desde el host no obtendría respuesta.

### 4. ¿Quién rechaza una petición con ingreso negativo?

FastAPI/Pydantic, con un error 422, al validar el contrato `Solicitante`. Docker solo transporta
el tráfico y no conoce su contenido, y la petición nunca llega al modelo.

Es importante rechazarla antes porque el modelo no valida reglas de negocio: responde con cualquier
número. Al pasarle directamente un ingreso de -100, predijo `moroso: 0` con probabilidad de mora de
0.37, es decir, una respuesta de "cumple" para un dato imposible. La validación previa evita
decisiones de crédito basadas en datos erróneos y le indica al cliente qué campo debe corregir.

### 5. Ventajas de la API contenerizada frente a `predecir_local.py`

1. **Integración:** cualquier sistema, como la web de créditos, lo consume por HTTP sin instalar
   Python ni las librerías.
2. **Reproducibilidad:** la imagen lleva el mismo entorno y las mismas versiones a cualquier máquina,
   lo que elimina el "en mi máquina funciona".
3. **Sin edición manual:** los datos llegan en la petición, en lugar de que un analista edite el script
   para cada solicitante.
4. **Validación y documentación:** las entradas inválidas se rechazan automáticamente y `/docs` se
   genera solo.
5. **Operación:** `/health` permite monitorear el servicio y un orquestador puede reiniciarlo o
   ejecutar varias réplicas.
