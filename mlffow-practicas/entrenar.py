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

mlflow.set_experiment("Iris Classification")

iteraciones = [50, 100, 200]

for max_iter in iteraciones:
    # 3. Empezar el experimento en MLflow
    with mlflow.start_run(run_name=f"logistic_regression_iter-{max_iter}"):
        
        # Crear el modelo
        model = LogisticRegression(max_iter=max_iter, random_state=42)
        
        # Entrenar el modelo
        model.fit(X_train, y_train)

        # Hacer predicciones
        y_pred = model.predict(X_test)

        # Calcular métricas
        accuracy = accuracy_score(y_test, y_pred)
        
        # Registrar parámetros y métricas
        mlflow.log_param("max_iter", max_iter)
        mlflow.log_metric("accuracy", accuracy)

        mlflow.sklearn.log_model(sk_model=model, artifact_path="modelo")

        print(f"Experimento completado. Iteraciones: {max_iter} Accuracy: {accuracy}")    
        

