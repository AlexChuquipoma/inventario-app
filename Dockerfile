FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY server.js db.js server.test.js ./
COPY public ./public
COPY data ./data

# El build se detiene inmediatamente si alguna prueba falla.
RUN npm test

# La imagen final solo necesita dependencias de produccion.
RUN npm prune --omit=dev


FROM node:24-alpine AS runtime

ENV NODE_ENV=production
ENV PORT=3000

WORKDIR /app

COPY --from=build --chown=node:node /app/package.json /app/package-lock.json ./
COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/server.js /app/db.js ./
COPY --from=build --chown=node:node /app/public ./public
COPY --from=build --chown=node:node /app/data ./data

USER node

EXPOSE 3000

CMD ["node", "server.js"]
