# 0003 – Autenticación de la POC con token en la URL

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Los datos de Mercado Público son públicos; el riesgo es el abuso del ticket. La POC tiene un solo usuario (cuenta Claude Pro).

## Decisión
URL de función con autenticación NONE y un token secreto en la ruta, validado en el código. Concurrencia reservada de la función limitada. Token en SSM Parameter Store.

## Consecuencias
Seguridad básica, solo apta para la POC. Antes del piloto con usuarios: OAuth 2.1 con Cognito (ADR futuro).
