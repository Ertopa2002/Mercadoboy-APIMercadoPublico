# 0002 – Conector MCP con FastMCP sobre AWS Lambda

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
La POC (Fase 0) no debe tener servidores 24x7 ni ALB, WAF o CloudWatch más allá de lo mínimo.

## Decisión
Servidor MCP con el SDK oficial de Python (v2, clase MCPServer, antes FastMCP), transporte Streamable HTTP en modo sin estado, desplegado como función Lambda (zip, sin ECR) expuesta con URL de función HTTPS.

## Consecuencias
Costo cercano a cero. Límites: 15 min por invocación, arranque en frío de 1–3 s. Validar en S1 que funcione con conectores personalizados de Claude. En Etapa 2 se migra a ECS Fargate + ALB sin cambiar `mp_core`.
