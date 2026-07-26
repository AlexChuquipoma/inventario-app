# inventario-app

Catálogo de inventario con interfaz web y base de datos local, preparado como
práctica de CI/CD con Docker, GitHub Actions, GHCR y Kubernetes.

## Qué es

Una app Node.js/Express con:

- **Interfaz web** (`public/index.html`, `public/app.js`, `public/styles.css`): una tabla de productos con formulario para agregar y botón para eliminar.
- **Base de datos local** (`db.js`): un archivo JSON en `data/products.json` que persiste los productos entre reinicios del proceso — sin motor de base de datos externo ni dependencias nativas.
- **API REST** consumida por la interfaz.

## Ejecutar en local

```bash
npm ci
npm start
# abrir http://localhost:3000
```

## Pruebas

```bash
npm test
```

## Construcción y prueba con Docker

El `Dockerfile` usa dos etapas. La primera instala las dependencias y ejecuta
las pruebas; si una prueba falla, la construcción se detiene. La segunda etapa
contiene únicamente los archivos y dependencias necesarios para ejecutar la
aplicación.

Construir la imagen:

```bash
docker build -t inventario-app:local .
```

Ejecutar el contenedor:

```bash
docker run --rm --name inventario-local -p 3000:3000 \
  -e APP_VERSION=v1-docker \
  -e APP_COLOR=blue \
  inventario-app:local
```

En PowerShell, el comando anterior se puede ejecutar en una sola línea:

```powershell
docker run --rm --name inventario-local -p 3000:3000 -e APP_VERSION=v1-docker -e APP_COLOR=blue inventario-app:local
```

Verificar las rutas desde una segunda terminal:

```powershell
curl.exe -i http://localhost:3000/
curl.exe -i http://localhost:3000/health
curl.exe -i http://localhost:3000/version
curl.exe -i http://localhost:3000/api/products
```

Verificar que el proceso no se ejecuta como `root`:

```powershell
docker exec inventario-local id
```

## CI/CD y publicación en GHCR

El workflow `.github/workflows/ci-cd.yml` se ejecuta con cada `push` a `main`
y también permite ejecución manual. Contiene dos jobs encadenados:

1. `build-test`: ejecuta `npm ci` y `npm test`.
2. `build-push`: tiene `needs: build-test`, construye la imagen y la publica
   solamente si las pruebas finalizaron correctamente.

La imagen se publica con el hash completo del commit y con la etiqueta
`latest`:

```text
ghcr.io/alexchuquipoma/inventario-app:<commit-sha>
ghcr.io/alexchuquipoma/inventario-app:latest
```

Comprobar que la imagen pública se puede descargar:

```powershell
docker pull ghcr.io/alexchuquipoma/inventario-app:latest
```

### Escaneo de seguridad con Trivy

El job `build-push` construye y carga la imagen localmente, ejecuta Trivy y solo
después realiza los dos `docker push`. El escaneo revisa vulnerabilidades de
paquetes del sistema operativo y librerías, muestra una tabla en el log y usa
`exit-code: 1` para detener el pipeline si encuentra severidad `CRITICAL`.

La Action está fijada al SHA completo de `trivy-action` v0.36.0 para evitar que
una etiqueta mutable cambie el código ejecutado por el pipeline:

```text
aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25
```

Reproducir el mismo criterio contra la imagen publicada, usando Trivy v0.70.0
en un contenedor:

```powershell
docker run --rm aquasec/trivy:0.70.0 image --scanners vuln --pkg-types os,library --severity CRITICAL --exit-code 1 ghcr.io/alexchuquipoma/inventario-app:latest
```

Un resultado sin vulnerabilidades críticas termina con código `0`. Si aparece
al menos una, termina con código `1`; GitHub Actions marca el job como fallido y
omite `Push commit image` y `Push latest image`.

El primer escaneo real de la imagen devolvió código `1`: detectó
`CVE-2026-59873` en `tar 7.5.15`, una dependencia del npm global incluido por la
imagen base, con corrección disponible en `7.5.19`. La aplicación solo necesita
el binario `node` durante la ejecución, por lo que el Dockerfile conserva npm en
la etapa `build` y elimina npm/npx de la etapa `runtime`. De este modo las
pruebas y `npm prune` siguen funcionando durante el build, pero la dependencia
vulnerable no se distribuye en la imagen final. Después de reconstruir, el
mismo comando de Trivy devolvió código `0` y no reportó vulnerabilidades
críticas.

## Despliegue base en Kubernetes

Los manifiestos `k8s/deployment.yaml` y `k8s/service.yaml` crean:

- Un Deployment con dos réplicas.
- Una estrategia `RollingUpdate` con `maxUnavailable: 1` y `maxSurge: 1`.
- Startup, readiness y liveness probes contra `/health`.
- Un Service `ClusterIP` que dirige el tráfico a los pods listos.

Iniciar Minikube y comprobar el nodo:

```powershell
minikube start --driver=docker
kubectl get nodes
```

Validar y aplicar los manifiestos:

```powershell
kubectl apply --dry-run=client -f .\k8s\
kubectl apply -f .\k8s\
kubectl rollout status deployment/inventario-app --timeout=120s
kubectl get pods -l app=inventario-app -o wide
kubectl get service inventario-app
```

Acceder al Service desde el equipo local:

```powershell
kubectl port-forward service/inventario-app 8080:80
```

Desde una segunda terminal:

```powershell
curl.exe -i http://localhost:8080/
curl.exe -i http://localhost:8080/health
curl.exe -i http://localhost:8080/version
curl.exe -i http://localhost:8080/api/products
```

### Arranque lento y estado de disponibilidad

La variable `STARTUP_DELAY_SECONDS` permite simular una aplicación que ya
escucha conexiones, pero todavía está inicializando dependencias. Durante ese
intervalo, `/health` responde `503 Service Unavailable`; al terminar, responde
`200 OK`.

Prueba local reproducible:

```powershell
$env:STARTUP_DELAY_SECONDS = "20"
npm.cmd start
```

Desde otra terminal:

```powershell
1..12 | ForEach-Object {
  $hora = Get-Date -Format "HH:mm:ss"
  $codigo = curl.exe -s -o NUL -w "%{http_code}" http://localhost:3000/health
  Write-Output "$hora HTTP $codigo"
  Start-Sleep -Seconds 2
}
```

La prueba produjo primero respuestas `503` y después respuestas `200`, sin
reiniciar el proceso. En Kubernetes, el Deployment configura un retraso de 15
segundos y utiliza tres comprobaciones complementarias:

- `startupProbe` concede tiempo para finalizar la inicialización y evita que
  `livenessProbe` reinicie prematuramente el contenedor.
- `readinessProbe` mantiene el pod fuera de los endpoints del Service mientras
  `/health` responda `503`.
- `livenessProbe` comprueba, después del arranque, que el proceso continúe
  funcionando.

Por eso un pod puede aparecer temporalmente como `Running` y `0/1`: el proceso
existe, pero Kubernetes todavía no lo considera listo para recibir tráfico.

### Manejo seguro de `API_KEY`

El Deployment obtiene `API_KEY` desde el Secret `inventario-app-secret` mediante
`secretKeyRef`. El valor no aparece en el manifiesto ni en ningún archivo
versionado. La aplicación únicamente informa en `/version` si la variable está
configurada, sin devolver la credencial.

Crear o actualizar una credencial ficticia directamente en el clúster, sin
escribirla en un archivo:

```powershell
$apiKeyLocal = "api-$(New-Guid)"
kubectl create secret generic inventario-app-secret --from-literal="API_KEY=$apiKeyLocal" --dry-run=client -o yaml | kubectl apply -f -
```

Antes de eliminar la variable local, comprobar que su valor no aparece en
ningún archivo rastreado por Git:

```powershell
$foundInGit = git grep -l --fixed-strings "$apiKeyLocal"
if ($foundInGit) {
  Write-Output "ERROR: la credencial aparece en $foundInGit"
} else {
  Write-Output "OK: la credencial no aparece en archivos versionados"
}
Remove-Variable apiKeyLocal
```

Aplicar el Deployment después de crear el Secret y verificar su consumo sin
imprimir el valor:

```powershell
kubectl apply -f .\k8s\deployment.yaml
kubectl rollout status deployment/inventario-app --timeout=120s
$podBase = kubectl get pods -l 'app=inventario-app,!slot' -o jsonpath="{.items[0].metadata.name}"
kubectl exec "pod/$podBase" -- node -e "console.log('API_KEY configurada:', Boolean(process.env.API_KEY))"
kubectl port-forward "pod/$podBase" 8084:3000
curl.exe -s http://localhost:8084/version
```

La respuesta de `/version` debe contener `"apiKeyConfigured":true`. Aunque los
datos de un Secret se almacenen codificados en Base64 dentro de Kubernetes,
Base64 no es cifrado; por eso tampoco se imprime el Secret con `kubectl get
secret -o yaml`. Los nombres `k8s/secret.yaml` y `k8s/secret.local.yaml` están
ignorados como protección adicional frente a un commit accidental.

Se selecciona un pod sin la etiqueta `slot` porque, si los ambientes de las
demostraciones base y Blue-Green continúan activos al mismo tiempo, el selector
general `app=inventario-app` también coincide con los pods `blue` y `green`.
Usar el nombre exacto evita que `kubectl exec deployment/inventario-app` elija
uno de esos pods históricos.

### Incidente real: `runAsNonRoot`

El primer despliegue quedó en `CreateContainerConfigError`. La imagen declara
`USER node`, pero Kubernetes recibió un nombre no numérico y no pudo verificar
que fuera distinto de `root`:

```text
container has runAsNonRoot and image has non-numeric user (node)
```

La identidad había sido verificada dentro del contenedor como
`uid=1000(node) gid=1000(node)`. Se corrigió el pod security context declarando
explícitamente `runAsUser: 1000` y `runAsGroup: 1000`, conservando
`runAsNonRoot: true`.

### Persistencia de datos al recrear un pod

Cada réplica escribe en su propio archivo `data/products.json`, dentro de la
capa efímera del contenedor. Para comprobarlo se creó el producto `POD-001`
directamente en un pod y luego se eliminó ese mismo pod:

```powershell
$podOriginal = kubectl get pods -l app=inventario-app -o jsonpath="{.items[0].metadata.name}"
kubectl port-forward "pod/$podOriginal" 8081:3000
# Crear POD-001 desde http://localhost:8081 y detener el port-forward.
kubectl delete pod $podOriginal
kubectl get pods -l app=inventario-app -w
```

El pod de reemplazo se inició únicamente con los tres productos semilla; el
producto `POD-001` desapareció. No es un error de Kubernetes: demuestra que el
archivo local no es almacenamiento compartido ni persistente entre pods.

## Estrategia Blue-Green

Se eligió Blue-Green porque la aplicación ya expone versión, color y hostname
en `/version`. Esto permite validar Green antes del corte y comprobar de forma
determinista qué versión recibe el tráfico. El rollback consiste únicamente en
devolver el selector del Service a Blue. Frente a Canary, evita depender de un
reparto probabilístico de peticiones y reduce la confusión producida por la base
JSON independiente de cada pod. El costo es mantener temporalmente ambos
ambientes, algo aceptable para esta aplicación pequeña en Minikube.

Los recursos están en `k8s/blue-green/`:

- `inventario-app-blue`: imagen `05684102...`, versión y color Blue.
- `inventario-app-green`: imagen `117567a...`, versión y color Green.
- `inventario-app-bg`: Service cuyo selector decide el ambiente activo.

Desplegar y validar ambos ambientes:

```powershell
kubectl apply --dry-run=client -f .\k8s\blue-green\
kubectl apply -f .\k8s\blue-green\
kubectl rollout status deployment/inventario-app-blue --timeout=120s
kubectl rollout status deployment/inventario-app-green --timeout=120s
kubectl get pods -l app=inventario-app -L slot
```

Validar Green directamente antes de exponerlo:

```powershell
kubectl port-forward deployment/inventario-app-green 8083:3000
curl.exe -i http://localhost:8083/health
curl.exe -s http://localhost:8083/version
```

Comprobar que el Service comienza en Blue:

```powershell
kubectl get service inventario-app-bg -o jsonpath="{.spec.selector}"
kubectl port-forward service/inventario-app-bg 8082:80
curl.exe -s http://localhost:8082/version
```

Detener el `port-forward`, cambiar el selector a Green y volver a iniciarlo:

```powershell
kubectl patch service inventario-app-bg --type merge --patch-file .\k8s\blue-green\patches\service-green.yaml
kubectl get service inventario-app-bg -o jsonpath="{.spec.selector}"
kubectl get endpointslices -l kubernetes.io/service-name=inventario-app-bg
kubectl port-forward service/inventario-app-bg 8082:80
curl.exe -s http://localhost:8082/version
```

Rollback inmediato a Blue:

```powershell
kubectl patch service inventario-app-bg --type merge --patch-file .\k8s\blue-green\patches\service-blue.yaml
```

Restaurar Green como ambiente activo:

```powershell
kubectl patch service inventario-app-bg --type merge --patch-file .\k8s\blue-green\patches\service-green.yaml
```

El `port-forward` debe reiniciarse después de cada cambio porque queda conectado
al pod seleccionado cuando se inicia; dentro del clúster, el Service actualiza
sus endpoints al cambiar el selector.

## Endpoints

| Método y ruta | Qué hace |
|---|---|
| `GET /health` | Estado de salud: `503` durante el arranque configurado, `200` cuando está listo y `500` si ocurre un fallo posterior (o si `SIMULATE_FAILURE=true`). |
| `GET /version` | Devuelve `version`, `color`, `hostname` y el booleano `apiKeyConfigured`; nunca devuelve la credencial. |
| `GET /api/products` | Lista todos los productos. |
| `GET /api/products/:id` | Devuelve un producto por id. |
| `POST /api/products` | Crea un producto (`name`, `sku`, `stock`, `price`). |
| `PATCH /api/products/:id` | Actualiza campos de un producto. |
| `DELETE /api/products/:id` | Elimina un producto. |
| `GET /` | Sirve la interfaz web. |

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `PORT` | `3000` | Puerto del servidor. |
| `APP_VERSION` | `v1` | Se muestra en `/version` y en el encabezado de la interfaz. |
| `APP_COLOR` | `blue` | Color del encabezado — útil para distinguir versiones en un despliegue. |
| `STARTUP_DELAY_SECONDS` | `0` | Segundos durante los que `/health` responde `503` para simular una inicialización lenta. |
| `API_KEY` | Sin valor | Credencial suministrada por un Secret; `/version` solo informa si está configurada. |
| `SIMULATE_FAILURE` | `false` | Si es `true`, `/health` responde siempre `500`. |
| `DB_PATH` | `./data/products.json` | Ruta del archivo de base de datos local. |
