# Informe de reflexión - Pipeline CI/CD de inventario-app

**Materia:** Sistemas Distribuidos<br>
**Estudiante:** Alex Chuquipoma<br>
**Fecha:** 26 de julio de 2026<br>
**Repositorio:** https://github.com/AlexChuquipoma/inventario-app

## Resultado y estrategia de despliegue

Se construyó un pipeline fail-fast para una aplicación Node.js/Express. Las
pruebas se ejecutan tanto en GitHub Actions como durante el build multi-stage de
Docker. La imagen se analiza con Trivy antes de publicar las etiquetas del
commit y `latest` en GHCR. En Minikube se desplegaron dos réplicas con
RollingUpdate, probes de arranque, disponibilidad y vida, un Secret para
`API_KEY`, y una estrategia Blue-Green.

Elegí Blue-Green porque `/version` expone versión, color y hostname. Esto
permite validar Green directamente antes del corte y comprobar de forma
determinista qué versión recibe el tráfico. El Service cambia su selector entre
`slot: blue` y `slot: green`, de modo que el cambio y el rollback son
inmediatos y usan únicamente recursos nativos de Kubernetes. Para esta app,
Canary habría complicado la demostración: el reparto sería probabilístico y
cada pod conserva una base JSON local distinta. El costo de duplicar
temporalmente dos ambientes es aceptable en este laboratorio.

## Métricas DORA propias

Todos los eventos se realizaron el 26 de julio de 2026. Los tiempos de commit y
despliegue se normalizaron a UTC.

| Commit | Cambio | Lead time |
|---|---|---:|
| `0568410` | Pipeline e imagen inicial | `00:28:47` |
| `117567a` | Rolling deployment | `00:04:05.297` |
| `1077675` | Arranque lento y probes | `00:09:59.821` |
| `99d4de3` | Secret para `API_KEY` | `00:05:09` |
| `30fb843` | Trivy y runtime endurecido | `00:10:59` |

El lead time promedio fue `00:11:48.024`. La frecuencia fue de **7 despliegues
exitosos en 1 día**, o `7 despliegues/día`. Se contaron las promociones que
crearon o actualizaron Deployments; los cambios de selector del Service
Blue-Green se registraron como cortes de tráfico, pero no como revisiones
nuevas.

Se realizaron ocho intentos de despliegue. Uno necesitó una corrección:

`change failure rate = 1 / 8 x 100 = 12.5 %`

El rollback Blue-Green fue una demostración planificada y los `503` del
startupProbe fueron esperados, por lo que no se clasificaron como fallos.

## Persistencia y problemas reales

El producto `POD-001`, creado directamente en un pod, desapareció cuando ese
pod fue eliminado y Kubernetes creó su reemplazo. El archivo
`data/products.json` vive en la capa efímera de cada contenedor: no es
almacenamiento compartido y una réplica puede mostrar datos diferentes de
otra. En producción se necesitaría una base externa o un volumen con una
arquitectura compatible con varias réplicas; aumentar réplicas por sí solo no
resuelve la persistencia.

El primer problema real fue `CreateContainerConfigError`. Aunque la imagen
declaraba `USER node`, Kubernetes no podía verificar que el nombre no numérico
fuera non-root. Se conservaron `runAsNonRoot: true` y las restricciones de
seguridad, pero se añadieron `runAsUser: 1000` y `runAsGroup: 1000`.

El escaneo inicial de Trivy encontró `CVE-2026-59873` crítica en `tar 7.5.15`,
incluido por el npm global de la imagen runtime. Como la aplicación solo
necesita `node` al ejecutarse, npm/npx se conservaron en la etapa de build y se
eliminaron de runtime. El mismo escaneo pasó después con código 0 y la
aplicación siguió respondiendo correctamente.

También se observó que `kubectl exec deployment/inventario-app` podía elegir un
pod Blue-Green debido a la etiqueta compartida `app=inventario-app`. Para las
verificaciones del Deployment base se usó `app=inventario-app,!slot`. Esta
experiencia mostró que etiquetas, selectores y evidencia precisa son parte del
comportamiento distribuido, no simples detalles de configuración.

## Reflexión final

La automatización útil no termina cuando una imagen compila. Las pruebas
reducen errores funcionales; Trivy evita publicar una imagen crítica; los
probes impiden enviar tráfico a procesos aún no listos; el Secret separa la
credencial del código; y Blue-Green limita el riesgo del cambio de versión.
Las métricas DORA hicieron visible el tiempo completo hasta el clúster, no solo
la duración del workflow. El resultado más importante fue poder reproducir
tanto los éxitos como los fallos y explicar por qué ocurrieron.
