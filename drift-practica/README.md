# Drift en modelos de Machine Learning: el ejemplo de la heladería

Un notebook para enseñar, paso a paso, qué es el **drift** en un modelo de Machine Learning y cómo se detectan sus dos tipos: **data drift** y **concept drift**. Cada línea de código tiene un comentario que explica qué hace.

---

## ¿Qué es el drift?

Un modelo de Machine Learning aprende con datos del **pasado**. Mientras el mundo siga igual, predice bien. Pero el mundo cambia, y cuando cambia, el modelo puede quedar desactualizado y empezar a equivocarse. A ese cambio se le llama **drift** (deriva).

Hay dos tipos:

|                         | **Data drift**                                                   | **Concept drift**                                                     |
| ----------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| ¿Qué cambia?            | Los **datos** que entran al modelo                               | La **regla** que une los datos con el resultado                       |
| Ejemplo en la heladería | Llega el verano: hace más calor                                  | Sube el precio: con el mismo calor se venden menos helados            |
| ¿Cómo se detecta?       | Comparando los datos nuevos con los de entrenamiento (prueba KS) | Comparando lo que predijo el modelo con lo que pasó de verdad (error) |
| ¿Daña al modelo?        | A veces sí, a veces no                                           | Casi siempre                                                          |
| ¿Qué hay que hacer?     | Vigilar                                                          | Reentrenar el modelo                                                  |

## ¿Qué hace el notebook?

Cuenta la historia de una heladería que usa un modelo para **predecir cuántos helados va a vender en el día según la temperatura**. El modelo es una regresión lineal, es decir, una recta.

| Paso                  | Qué pasa                                                                                                  | Qué se aprende                                                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 1. Simular el mundo   | Una función decide cuántos helados se venden según la temperatura. Hace de "realidad".                    | En la vida real no conocemos esta regla; solo vemos sus resultados.                                                               |
| 2. Primavera          | Se entrena el modelo con 100 días de ~20 °C y se guarda su error como **referencia**.                     | Sin referencia no hay contra qué comparar.                                                                                        |
| 3. Verano             | Llegan 100 días de ~30 °C. La regla no cambia.                                                            | **Data drift**: los datos cambian (la prueba KS lo detecta), pero el modelo sigue acertando.                                      |
| 4. Precio alto        | Siguen los ~30 °C, pero con el mismo calor se venden menos helados.                                       | **Concept drift**: los datos no cambian, pero el modelo se equivoca muchísimo. Solo se descubre comparando con las ventas reales. |
| 5. Reentrenar         | Se entrena un modelo nuevo con los datos del precio alto.                                                 | El modelo nuevo aprende la regla nueva y vuelve a acertar.                                                                        |
| 6. Revisor automático | Una función hace las dos revisiones y dice si todo está bien, si hay que vigilar o si hay que reentrenar. | Así se monitorea un modelo en producción.                                                                                         |

Al final hay un **resumen** y **3 ejercicios**. Las respuestas para el docente están en la última celda; conviene borrarla antes de compartir el notebook con los estudiantes.

### Resultados que se van a ver

| Momento            | ¿Cambiaron los datos? | Error del modelo        | Diagnóstico                    |
| ------------------ | --------------------- | ----------------------- | ------------------------------ |
| Primavera          | —                     | ~8 helados por día      | referencia                     |
| Verano             | **sí**                | ~8 helados por día      | **data drift** → vigilar       |
| Precio alto        | **no**                | **~74 helados por día** | **concept drift** → reentrenar |
| Modelo reentrenado | —                     | ~8 helados por día      | resuelto                       |

Los datos son simulados con una semilla fija, así que todos obtienen los mismos números.

---

## Cómo levantarlo

### Requisitos

- **Python 3.10 a 3.13**. Para ver la versión instalada: `python3 --version` (en Windows: `python --version`).
- Los archivos `clase_drift.ipynb`, `requirements.txt` y este `README.md`, en la misma carpeta.

### 1. Abrir una terminal en la carpeta del proyecto

```bash
cd ruta/a/la/carpeta
```

### 2. Crear el entorno virtual

Un entorno virtual (`venv`) es una carpeta con su propio Python y sus propias librerías, para no mezclarlas con las del sistema.

En macOS o Linux:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
```

En Windows:

```bash
python -m venv .venv
```

### 3. Activar el entorno virtual

En macOS o Linux:

```bash
source .venv/bin/activate
```

En Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

En Windows (CMD):

```bash
.venv\Scripts\activate.bat
```

Al activarlo, la línea de la terminal empieza con `(.venv)`.

### 4. Instalar las librerías

```bash
pip install -r requirements.txt
```

Se instalan:

| Librería       | Para qué se usa                                       |
| -------------- | ----------------------------------------------------- |
| `numpy`        | generar los datos y hacer cálculos                    |
| `matplotlib`   | dibujar los gráficos                                  |
| `scipy`        | la prueba de Kolmogórov-Smirnov (detectar data drift) |
| `scikit-learn` | el modelo (regresión lineal) y el cálculo del error   |
| `jupyterlab`   | abrir y ejecutar el notebook                          |

### 5. Abrir el notebook

```bash
jupyter lab clase_drift.ipynb
```

Se abre en el navegador. Para ejecutarlo:

- **Celda por celda:** seleccionar una celda y presionar `Shift + Enter`.
- **Todo de una vez:** menú **Run → Run All Cells**.

Todo corre en unos segundos y no necesita internet.

### 6. Al terminar

Cerrar Jupyter con `Ctrl + C` en la terminal y desactivar el entorno:

```bash
deactivate
```

La próxima vez solo hay que repetir los pasos **3** (activar) y **5** (abrir).

### Alternativa: Visual Studio Code

1. Hacer los pasos 2 a 4.
2. Abrir la carpeta en VS Code e instalar la extensión **Jupyter** (de Microsoft).
3. Abrir `clase_drift.ipynb`, hacer clic en **Select Kernel** (arriba a la derecha) y elegir el Python de `.venv`.
4. Ejecutar con **Run All**.

### Problemas comunes

| Problema                                                              | Solución                                                                                                                        |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `python3: command not found` (o `python` en Windows)                  | Instalar Python desde python.org y marcar **"Add Python to PATH"** durante la instalación.                                      |
| En Windows PowerShell: _"la ejecución de scripts está deshabilitada"_ | Ejecutar `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y volver a activar el entorno.                                   |
| `ModuleNotFoundError: No module named 'sklearn'`                      | El entorno no está activado o el notebook usa otro Python. Activar `.venv` (paso 3) o, en VS Code, elegir el kernel de `.venv`. |
| `pip install` falla con Python muy nuevo                              | Usar Python 3.12 o 3.13: las librerías tardan un tiempo en publicarse para versiones recién salidas.                            |
