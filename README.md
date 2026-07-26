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

## Despliegue base en Kubernetes

Los manifiestos `k8s/deployment.yaml` y `k8s/service.yaml` crean:

- Un Deployment con dos réplicas.
- Una estrategia `RollingUpdate` con `maxUnavailable: 1` y `maxSurge: 1`.
- Readiness y liveness probes contra `/health`.
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

## Endpoints

| Método y ruta | Qué hace |
|---|---|
| `GET /health` | Estado de salud: `200` si el proceso y el archivo de base de datos son accesibles, `500` si no (o si `SIMULATE_FAILURE=true`). |
| `GET /version` | Devuelve `version`, `color` y `hostname` — configurables por variables de entorno `APP_VERSION` / `APP_COLOR`. |
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
| `SIMULATE_FAILURE` | `false` | Si es `true`, `/health` responde siempre `500`. |
| `DB_PATH` | `./data/products.json` | Ruta del archivo de base de datos local. |
