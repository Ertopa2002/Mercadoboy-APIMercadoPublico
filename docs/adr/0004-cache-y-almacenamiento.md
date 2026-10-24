# 0004 – Caché en DynamoDB, archivos en S3, secretos en Parameter Store

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Lambda no tiene disco persistente compartido. EFS exigiría VPC y un contenedor 24x7.

## Decisión
- Caché y contador diario de llamadas: DynamoDB on-demand con TTL.
- Adjuntos y texto extraído: S3 (cifrado, sin acceso público, ciclo de vida 30 días).
- Ticket y token: SSM Parameter Store (SecureString estándar).
- El core accede a la caché por una interfaz con implementaciones intercambiables (memoria para tests, DynamoDB en AWS).

## Consecuencias
Costo < USD 2/mes. Registros de DynamoDB de máximo 400 KB: el texto largo va a S3.
