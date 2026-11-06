from mlflow.models import infer_signature
import mlflow
import mlflow.sklearn

from sklearn.datasets import load_iris

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# 1. Cargar los datos
data = load_iris()

X = data.data
y = data.target

# 2. Dividir en datos de entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

mlflow.set_tracking_uri("http://127.0.0.1:5050")
mlflow.set_experiment("Iris Classification Regularización de Parametros")

valores_c = [0.01, 0.10, 1.00, 10.0, 100.0]

for valor_c in valores_c:
    # 3. Empezar el experimento en MLflow
    with mlflow.start_run(run_name=f"logistic_regression_c-{valor_c}"):
        
        # Crear el modelo
        model = LogisticRegression(C=valor_c, max_iter=200, random_state=42)
        
        # Entrenar el modelo
        model.fit(X_train, y_train)

        # Hacer predicciones
        y_pred = model.predict(X_test)

        # Calcular métricas
        accuracy = accuracy_score(y_test, y_pred)
        
        firma = infer_signature(X_train, model.predict(X_train))
        
        # Registrar parámetros y métricas
        mlflow.log_param("C", valor_c)
        mlflow.log_metric("accuracy", accuracy)

        mlflow.set_tag("algoritmo", "regresion-logistica")
        mlflow.set_tag("dataset", "iris")

        mlflow.sklearn.log_model(
            sk_model=model, 
            signature=firma, 
            input_example=X_train[:3], 
            name="modelo")

        print(f"Experimento completado. c: {valor_c} Accuracy: {accuracy}")    
        

