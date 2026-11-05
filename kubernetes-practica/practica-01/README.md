# Práctica 01: Servidor web NGINX en Kubernetes

Despliegue de `nginx:alpine` en un clúster local k3d, dentro del namespace `practica1`, primero como Pod independiente y después como Deployment expuesto con un Service.

**Entorno:** clúster `k3d-local` con 1 server y 3 agents, Kubernetes v1.35.4-rc2+k3s1 y kubectl v1.36.1.

Los comandos completos están en [`command.txt`](command.txt) y se ejecutan desde la raíz del repositorio.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `namespace.yaml` | Namespace `practica1` |
| `pod.yaml` | Pod `web-basico` |
| `deployment.yaml` | Deployment `web-deployment` en su estado inicial, con 2 réplicas |
| `deployment-final.yaml` | Estado final, con 3 réplicas, recursos y pruebas de salud |
| `service.yaml` | Service `web-service`, de tipo `NodePort`, en el puerto 31446 |

## Resultados

### 1. Entorno

Los 4 nodos aparecen `Ready`, y tanto el cliente como el servidor responden. El namespace `practica1` quedó `Active`.

### 2. Pod independiente

El Pod `web-basico` llegó a `Running` en el nodo `k3d-local-agent-2`, y `describe` mostró su IP, su imagen y los eventos de programación y descarga. Con `kubectl port-forward pod/web-basico 8080:80`, NGINX respondió `HTTP/1.1 200 OK`.

Al eliminarlo, `kubectl get pods` indicó `No resources found`. Kubernetes no lo vuelve a crear porque ningún controlador administra un Pod independiente.

### 3. Deployment y Service

`web-deployment` llegó a `2/2` réplicas disponibles. El Service seleccionó los Pods correctos: las IP de sus endpoints (`10.42.0.12` y `10.42.3.14`) coinciden con las de los Pods con la etiqueta `app=web`.

El servidor respondió en `http://localhost:31446`. Para comprobar el reparto se enviaron 31 solicitudes en total, y todas las de la prueba de 30 devolvieron `200`. Los logs registraron 16 en un Pod y 15 en el otro. El reparto es aproximado, no una rotación estricta.

Se usó `NodePort` porque `kubectl port-forward service/...` conecta con un solo Pod y no reparte las solicitudes.

### 4. Recuperación automática

Se eliminó el Pod `web-deployment-578b67f69-9pb5k` y apareció `web-deployment-578b67f69-45gwz`, así que se mantuvieron las 2 réplicas. El ReplicaSet creado por el Deployment restablece el estado deseado.

### 5. Escalamiento

Con `kubectl scale` el Deployment pasó de 2 a `5/5` réplicas, repartidas entre los 4 nodos, y luego se redujo a `3/3`. Escalar no crea una revisión nueva porque no cambia la plantilla del Pod.

### 6. Actualización y reversión

| Operación | Imagen | Versión que informa NGINX | Revisión |
| --- | --- | --- | --- |
| Estado inicial | `nginx:alpine` | 1.31.8 | 1 |
| `kubectl set image` | `nginx:stable-alpine` | 1.30.6 | 2 |
| `kubectl rollout undo` | `nginx:alpine` | 1.31.8 | 3 |

`kubectl rollout status` mostró el reemplazo gradual de los Pods hasta `successfully rolled out`, y el Service respondió `200 OK` después de cada cambio. En el historial, la revisión 1 desaparece y pasa a ser la 3, porque `undo` reutiliza esa plantilla como revisión nueva.

`rollout undo` advirtió que no actualiza la anotación `last-applied-configuration`. Es esperable al mezclar comandos imperativos con `kubectl apply`, y el siguiente `apply` deja la configuración alineada.

### 7. Recursos y pruebas de salud

Se aplicó `deployment-final.yaml`, y `describe pod` confirmó esta configuración:

| Configuración | Valor |
| --- | --- |
| Solicitudes | `cpu: 50m`, `memory: 32Mi` |
| Límites | `cpu: 200m`, `memory: 128Mi` |
| `readinessProbe` | `GET /` en el puerto 80, cada 5 s, con 2 s de espera inicial |
| `livenessProbe` | `GET /` en el puerto 80, cada 10 s, con 10 s de espera inicial y 3 fallos permitidos |
| Clase QoS | `Burstable` |

Los 3 Pods quedaron `1/1` con 0 reinicios. Cada uno consumía 1m de CPU y 18Mi de memoria, dentro de los límites. La `readinessProbe` decide si el Pod recibe tráfico del Service, y la `livenessProbe` decide si hay que reiniciar el contenedor.

### 8. Limpieza

`kubectl delete namespace practica1` eliminó todos los recursos de la práctica. `practica1` ya no aparece en `kubectl get namespace`, y `kubectl get all -n practica1` indica `No resources found`. El clúster se conservó.

## Evidencias

Las salidas de los comandos están en `evidencias/`. Las capturas de pantalla **están pendientes** y se deben añadir con los nombres indicados.

| # | Evidencia | Salida registrada | Captura pendiente |
| --- | --- | --- | --- |
| 1 | Nodo en estado `Ready` | [`01-nodo-ready.txt`](evidencias/01-nodo-ready.txt) | `01-nodo-ready.png` |
| 2 | Pod inicial en `Running` | [`02-pod-running.txt`](evidencias/02-pod-running.txt) | `02-pod-running.png` |
| 3 | Acceso correcto a NGINX | [`03-acceso-nginx.txt`](evidencias/03-acceso-nginx.txt) | `03-acceso-nginx.png` |
| 4 | Deployment con 2 réplicas disponibles | [`04-deployment-2-replicas.txt`](evidencias/04-deployment-2-replicas.txt) | `04-deployment-2-replicas.png` |
| 5 | Pod nuevo tras eliminar uno | [`05-recuperacion-pod.txt`](evidencias/05-recuperacion-pod.txt) | `05-recuperacion-pod.png` |
| 6 | Escalamiento a 5 réplicas | [`06-escalamiento-5.txt`](evidencias/06-escalamiento-5.txt) | `06-escalamiento-5.png` |
| 7 | Actualización de la imagen | [`07-actualizacion-imagen.txt`](evidencias/07-actualizacion-imagen.txt) | `07-actualizacion-imagen.png` |
| 8 | Reversión de la actualización | [`08-reversion.txt`](evidencias/08-reversion.txt) | `08-reversion.png` |
| 9 | Eliminación final de los recursos | [`09-limpieza.txt`](evidencias/09-limpieza.txt) | `09-limpieza.png` |

La salida de la Fase 7, que no requiere captura, está en [`extra-recursos-probes.txt`](evidencias/extra-recursos-probes.txt).
