# 0007 – Precarga programada del detalle de licitaciones

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
El listado por fecha de la API trae solo código, nombre, estado y cierre. Región, monto, tipo e ítems (código ONU) requieren una llamada de detalle por proceso. Un día tiene ~280 licitaciones publicadas: ~280 llamadas (3% del cupo) y ~10 minutos con la pausa de 2 s entre llamadas. No cabe en una llamada del agente.

## Decisión
Una segunda función Lambda (`mp-precarga`), disparada por EventBridge Scheduler cada 2–3 horas, consulta lo publicado y guarda en DynamoDB el detalle de los códigos que aún no están en caché (incremental). Las herramientas de búsqueda del conector filtran sobre lo precargado.

## Carga inicial
`estado=activas` devuelve todas las vigentes (~5.100) en una llamada. La primera carga del detalle se reparte en 2 noches (~2.500 llamadas por noche); luego solo se piden los códigos nuevos.

## Compra Ágil
El listado ya trae región, monto, organismo y fechas. La búsqueda `q` y la sincronización incremental de la API no funcionan (504 y 0 resultados). Por eso:
- Cada 2–3 horas: listado ordenado por `FechaPublicacion` descendente, paginando hasta encontrar códigos ya guardados (nuevas publicaciones).
- Una vez por noche: barrido completo del listado de publicadas (~182 llamadas) para actualizar estados y cierres.
- Detalle (productos con código ONU) solo de las compras nuevas que calzan con el perfil (palabra clave en nombre) y a pedido del agente: hay ~1.170 nuevas al día y cada detalle tarda ~8 s.
- La palabra clave se busca localmente sobre lo precargado.

## Consecuencias
- Búsquedas del agente inmediatas y sin consumir cupo.
- Costo cercano a cero (Scheduler y Lambda dentro de la capa gratuita).
- Los datos pueden tener hasta 2–3 horas de atraso; el detalle de un código puntual se puede pedir en línea.
- Es el primer paso de la ingesta de la Etapa 2, que lo reemplaza por carga a PostgreSQL.
