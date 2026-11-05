# Plan: Práctica 01 — Servidor web NGINX en Kubernetes

## Objetivo

Desplegar `nginx:alpine` en el clúster local, dentro del namespace `practica1`, primero como Pod independiente y después como Deployment con varias réplicas expuesto mediante un Service. Luego, probar la recuperación automática, el escalamiento, la actualización y la reversión de la imagen. Cada operación se verifica con comandos de Kubernetes y se acompaña de una explicación breve.

Todos los archivos de la práctica van en `./practica-01/`.

## Entorno

Estado comprobado el 2026-11-05:

| Elemento | Valor |
| --- | --- |
| Clúster | k3d `local`, contexto `k3d-local` |
| Nodos | 1 server y 3 agents, todos `Ready`, v1.35.4-rc2+k3s1 |
| Namespace `practica1` | Todavía no existe; se crea en la Fase 1 |
| Puerto publicado por k3d | `31446` en `localhost`, libre y sin uso en el clúster |
| Otros componentes | `metrics-server` activo; Traefik desactivado |

## Estructura de archivos

```text
practica-01/
├── namespace.yaml         # Namespace practica1
├── pod.yaml               # Pod web-basico
├── deployment.yaml        # Estado inicial: 2 réplicas, sin resources ni probes
├── deployment-final.yaml  # Estado final: 3 réplicas, con resources y probes
├── service.yaml           # Service web-service
├── command.txt            # Comandos en orden, como en los demás módulos del repo
├── README.md              # Informe: resultado y explicación de cada paso
└── evidencias/            # Capturas de pantalla (ver tabla de evidencias)
```

Los comandos se ejecutan desde la raíz del repositorio, igual que en los módulos existentes (`kubectl apply -f ./practica-01/...`).

## Decisiones de diseño

1. **Namespace `practica1` declarado en los manifiestos.** Cada recurso lleva `metadata.namespace: practica1`, como en `05-rolling-update/`. Así, `kubectl apply -f` no puede crear recursos en otro namespace por olvido.
2. **`-n practica1` explícito en los comandos.** No se cambia el namespace por defecto del contexto, para no alterar el kubeconfig y para que cada captura muestre el namespace consultado.
3. **Service de tipo `NodePort` con `nodePort: 31446`.** Es el puerto que k3d ya publica en `localhost`, por lo que no hay que recrear el clúster. `kubectl port-forward service/...` no sirve para este requisito porque conecta con un solo Pod y no reparte las solicitudes. El puerto de un `NodePort` es global al clúster, así que el acceso sigue siendo `localhost:31446` aunque el Service esté en un namespace.
4. **Dos archivos de Deployment.** `kubectl scale` deja el clúster en 3 réplicas mientras `deployment.yaml` sigue indicando 2. Aplicar ese archivo otra vez reduciría las réplicas sin querer. `deployment-final.yaml` declara el estado real y `deployment.yaml` conserva el estado inicial que pide el enunciado. El repo ya usa esta convención en `05-rolling-update/` (`app-v1.yaml` y `app-v2.yaml`).
5. **Etiqueta distinta en el Pod inicial.** `web-basico` usa `app: web-basico` para que nunca entre en el selector `app: web` del Service, ya que ambos comparten namespace.
6. **Imagen `nginx:alpine` en `deployment-final.yaml`.** Es la imagen vigente después de la reversión de la Fase 6, así que aplicar el archivo no revierte ese resultado.
7. **Historial con `kubernetes.io/change-cause`.** Se usa esta anotación porque `--record` está obsoleto.
8. **Limpieza eliminando el namespace.** Borrar `practica1` elimina todo lo que contiene y no afecta a otros namespaces ni al clúster.

## Manifiestos

Todos los recursos, salvo el propio Namespace, llevan `namespace: practica1` en `metadata`.

### `namespace.yaml`

- Namespace `practica1`.

### `pod.yaml`

- Pod `web-basico`, etiqueta `app: web-basico`.
- Contenedor `web`, imagen `nginx:alpine`, `containerPort: 80`.

### `deployment.yaml`

- Deployment `web-deployment`, `replicas: 2`.
- Selector y etiqueta de la plantilla: `app: web`.
- Contenedor `web`, imagen `nginx:alpine`, `containerPort: 80`.

### `service.yaml`

- Service `web-service`, `type: NodePort`, selector `app: web`.
- `port: 80`, `targetPort: 80`, `nodePort: 31446`.

### `deployment-final.yaml`

Parte de `deployment.yaml`, con `replicas: 3` y lo siguiente en el contenedor:

```yaml
resources:
  requests:
    cpu: "50m"
    memory: "32Mi"
  limits:
    cpu: "200m"
    memory: "128Mi"
readinessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 2
  periodSeconds: 5
livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3
```

## Fases de ejecución

### Fase 1: Verificar el entorno y crear el namespace

```bash
kubectl version
kubectl cluster-info
kubectl get nodes

kubectl apply -f ./practica-01/namespace.yaml
kubectl get namespace practica1
```

**Resultado esperado:** cliente y servidor responden, todos los nodos aparecen `Ready` 📸 Evidencia 1, y `practica1` queda `Active`.

### Fase 2: Pod independiente

```bash
kubectl apply -f ./practica-01/pod.yaml
kubectl get pods -n practica1
kubectl describe pod web-basico -n practica1

# Terminal 1 (queda en primer plano)
kubectl port-forward pod/web-basico 8080:80 -n practica1
# Terminal 2, o el navegador en http://localhost:8080
curl -i http://localhost:8080

# Detener el port-forward con Ctrl+C
kubectl delete pod web-basico -n practica1
kubectl get pods -n practica1
```

**Resultado esperado:**

- El Pod queda `Running` y NGINX responde `200 OK`. 📸 Evidencias 2 y 3.
- `describe` permite comentar el namespace, el nodo, la IP, la imagen, el estado y los eventos.
- Tras borrarlo aparece `No resources found in practica1 namespace`: ningún controlador administra un Pod independiente, por lo que no se vuelve a crear.

### Fase 3: Deployment y Service

```bash
kubectl apply -f ./practica-01/deployment.yaml
kubectl rollout status deployment/web-deployment -n practica1
kubectl get deployment web-deployment -n practica1
kubectl get pods -l app=web -n practica1 -o wide

kubectl apply -f ./practica-01/service.yaml
kubectl describe service web-service -n practica1
kubectl get endpointslices -l kubernetes.io/service-name=web-service -n practica1
curl -i http://localhost:31446
```

**Resultado esperado:**

- El Deployment muestra `READY 2/2`. 📸 Evidencia 4.
- Las IP de los endpoints coinciden con las de los Pods listados con `-l app=web`, lo que confirma que el selector funciona.

**Reparto de solicitudes.** La página de NGINX es igual en todos los Pods, así que el reparto se comprueba en sus logs:

```bash
for i in $(seq 1 30); do curl -s -o /dev/null http://localhost:31446; done
kubectl logs -l app=web -n practica1 --prefix --tail=-1 | grep 'GET /' | grep -v kube-probe | awk '{print $1}' | sort | uniq -c
```

Ambos Pods deben registrar solicitudes. El reparto es aproximado, no una rotación estricta.

### Fase 4: Recuperación automática

```bash
kubectl get pods -l app=web -n practica1
kubectl delete pod <nombre-de-un-pod> -n practica1
kubectl get pods -l app=web -n practica1
```

**Resultado esperado:** aparece un Pod con otro nombre y poca antigüedad, y se mantienen 2 réplicas, porque el ReplicaSet restablece el estado deseado. 📸 Evidencia 5, con el listado de antes y el de después en la misma captura.

### Fase 5: Escalamiento

```bash
kubectl scale deployment/web-deployment --replicas=5 -n practica1
kubectl rollout status deployment/web-deployment -n practica1
kubectl get pods -l app=web -n practica1 -o wide

kubectl scale deployment/web-deployment --replicas=3 -n practica1
kubectl get deployment web-deployment -n practica1
kubectl get pods -l app=web -n practica1
```

**Resultado esperado:** primero `5/5`, con los Pods repartidos entre los nodos 📸 Evidencia 6, y luego `3/3`. Escalar no crea una revisión nueva porque no cambia la plantilla del Pod.

### Fase 6: Actualización y reversión

```bash
kubectl annotate deployment/web-deployment kubernetes.io/change-cause="Despliegue inicial con nginx:alpine" -n practica1

kubectl set image deployment/web-deployment web=nginx:stable-alpine -n practica1
kubectl annotate deployment/web-deployment kubernetes.io/change-cause="Actualización a nginx:stable-alpine" --overwrite -n practica1
kubectl rollout status deployment/web-deployment -n practica1
kubectl get deployment web-deployment -n practica1 -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl rollout history deployment/web-deployment -n practica1

kubectl rollout undo deployment/web-deployment -n practica1
kubectl rollout status deployment/web-deployment -n practica1
kubectl annotate deployment/web-deployment kubernetes.io/change-cause="Reversión a nginx:alpine" --overwrite -n practica1
kubectl get deployment web-deployment -n practica1 -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl rollout history deployment/web-deployment -n practica1
```

**Resultado esperado:**

- La imagen cambia a `nginx:stable-alpine` sin dejar de haber réplicas disponibles. 📸 Evidencia 7.
- La imagen vuelve a `nginx:alpine`. 📸 Evidencia 8.
- La revisión 1 pasa a ser la 3 en el historial, porque `undo` reutiliza esa plantilla como revisión nueva.

### Fase 7: Recursos y pruebas de salud

```bash
kubectl apply -f ./practica-01/deployment-final.yaml
kubectl annotate deployment/web-deployment kubernetes.io/change-cause="Recursos y pruebas de salud" --overwrite -n practica1
kubectl rollout status deployment/web-deployment -n practica1
kubectl get pods -l app=web -n practica1
kubectl describe pod <nombre-de-un-pod> -n practica1
kubectl top pods -l app=web -n practica1
curl -i http://localhost:31446
```

**Resultado esperado:**

- `describe` muestra `Limits`, `Requests`, `Readiness` y `Liveness`.
- Los Pods quedan `1/1` con `RESTARTS 0`, y el Service sigue respondiendo.
- `kubectl top` puede tardar cerca de un minuto en mostrar métricas de Pods nuevos.

### Fase 8: Limpieza

```bash
kubectl get all -n practica1
kubectl delete namespace practica1
kubectl get namespace
kubectl get all -n practica1
```

**Resultado esperado:** `delete` puede tardar unos segundos porque espera a que terminen los Pods. Después, `practica1` ya no aparece en la lista y la última consulta indica `No resources found in practica1 namespace`. El clúster se conserva porque no forma parte de lo creado en la práctica. 📸 Evidencia 9.

## Trazabilidad de actividades

| # | Actividad | Fase |
| --- | --- | --- |
| 1 | Verificar Kubernetes y kubectl | 1 |
| 2 | Crear el Pod `web-basico` | 2 |
| 3 | `kubectl get pods` y `kubectl describe pod` | 2 |
| 4 | Acceso con `kubectl port-forward` | 2 |
| 5 | Eliminar el Pod y comprobar que no se recrea | 2 |
| 6 | Crear `deployment.yaml` con `web-deployment` | 3 |
| 7 | Dos réplicas y etiqueta `app: web` | 3 |
| 8 | Crear `service.yaml` | 3 |
| 9 | Verificar la selección de Pods por etiquetas | 3 |
| 10 | Eliminar un Pod y comprobar que se recrea | 4 |
| 11 | Escalar de 2 a 5 réplicas | 5 |
| 12 | Reducir a 3 réplicas | 5 |
| 13 | Actualizar a `nginx:stable-alpine` | 6 |
| 14 | `kubectl rollout status` | 6 |
| 15 | Historial y `kubectl rollout undo` | 6 |
| 16 | Solicitudes y límites de CPU y memoria | 7 |
| 17 | `readinessProbe` y `livenessProbe` | 7 |
| 18 | Eliminar todos los recursos | 8 |

## Evidencias

Las capturas se toman manualmente durante la ejecución y se guardan en `practica-01/evidencias/`.

| # | Evidencia | Fase | Comando que debe verse | Archivo |
| --- | --- | --- | --- | --- |
| 1 | Nodo en estado `Ready` | 1 | `kubectl get nodes` | `01-nodo-ready.png` |
| 2 | Pod inicial en `Running` | 2 | `kubectl get pods -n practica1` | `02-pod-running.png` |
| 3 | Acceso correcto a NGINX | 2 | `curl -i` o navegador | `03-acceso-nginx.png` |
| 4 | Deployment con 2 réplicas disponibles | 3 | `kubectl get deployment web-deployment -n practica1` | `04-deployment-2-replicas.png` |
| 5 | Pod nuevo tras eliminar uno | 4 | `kubectl get pods -l app=web -n practica1`, antes y después | `05-recuperacion-pod.png` |
| 6 | Escalamiento a 5 réplicas | 5 | `kubectl get pods -l app=web -n practica1 -o wide` | `06-escalamiento-5.png` |
| 7 | Actualización de la imagen | 6 | `rollout status` e imagen actual | `07-actualizacion-imagen.png` |
| 8 | Reversión de la actualización | 6 | `rollout undo`, imagen e historial | `08-reversion.png` |
| 9 | Eliminación final de los recursos | 8 | `kubectl delete namespace practica1`, `kubectl get namespace` y `kubectl get all -n practica1` | `09-limpieza.png` |

## Riesgos

| Riesgo | Señal | Respuesta |
| --- | --- | --- |
| Se omite `-n practica1` en un comando | `No resources found in default namespace` o `NotFound` | Repetir el comando con `-n practica1`. |
| `localhost:31446` no responde | `curl` falla aunque los Pods estén `Ready` | Revisar `describe service` y los endpoints. Si el problema es la publicación del puerto, usar `kubectl port-forward service/web-service 8081:80 -n practica1` para el acceso e indicar en el informe que así no se demuestra el reparto. |
| No se puede descargar la imagen | `ErrImagePull` o `ImagePullBackOff` | Revisar la conexión o el límite de Docker Hub y consultar los eventos con `describe pod`. |
| El puerto 8080 está ocupado | `port-forward` no puede escuchar | Usar otro puerto local, por ejemplo `8081:80`. |
| Se aplica `deployment.yaml` después de escalar | Las réplicas vuelven a 2 | Usar `deployment-final.yaml` desde la Fase 7. |

## Criterios de finalización

- [ ] Existen los archivos de la estructura definida en `practica-01/`.
- [ ] Todos los recursos de la práctica se crearon en el namespace `practica1`.
- [ ] Las 18 actividades se ejecutaron y sus resultados coinciden con los esperados.
- [ ] `README.md` incluye una explicación breve de cada operación.
- [ ] Las 9 capturas están en `practica-01/evidencias/` y enlazadas desde `README.md`.
- [ ] `practica1` ya no aparece en `kubectl get namespace` al terminar.
