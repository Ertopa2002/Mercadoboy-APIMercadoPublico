# 0009 – Índice de procesos vigentes como archivo en S3

- Estado: aceptada
- Fecha: 2026-10-26

## Contexto
Las búsquedas del agente filtran sobre ~5.100 licitaciones y ~9.000 Compras Ágiles vigentes. Un registro de DynamoDB admite máximo 400 KB y consultar miles de registros por búsqueda sería lento y caro.

## Decisión
La precarga construye un índice único (JSON comprimido con gzip, `indice/procesos.json.gz`) con el resumen de cada proceso y el detalle disponible. Se guarda en S3 (en local, en `exploracion/blobs/`). El conector lo carga en memoria al arrancar y filtra localmente. DynamoDB queda para la caché de detalles puntuales y el contador de cupo.

## Consecuencias
- Búsquedas en milisegundos y sin gastar cupo.
- Lambda necesita memoria para el índice (estimado: decenas de MB en memoria; 1 GB es suficiente).
- Los datos tienen el atraso de la última precarga (2–3 h); el detalle puntual se puede refrescar en línea.
- En Etapa 2 el índice se reemplaza por PostgreSQL.
