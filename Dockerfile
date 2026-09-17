FROM node:22-bookworm-slim
WORKDIR /app
COPY --chown=node:node agent-utilities-mcp.mjs THIRD-PARTY-NOTICES.txt LICENSE ./
USER node
ENTRYPOINT ["node", "/app/agent-utilities-mcp.mjs"]
