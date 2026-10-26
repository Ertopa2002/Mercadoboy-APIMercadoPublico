# Matriz de campos – API de Licitaciones

Fuente: exploración del 23-10-2026 (`scripts/probe_licitaciones.py`): 281 licitaciones publicadas ese día, detalle de 3 procesos, 89 campos distintos en el detalle.

## Hallazgos

- **El listado por fecha trae solo 4 campos:** `CodigoExterno`, `Nombre`, `CodigoEstado`, `FechaCierre`. Región, monto, tipo, organismo e ítems solo vienen en el **detalle por código** (1 llamada por proceso).
- Un día típico tiene ~280 licitaciones publicadas: cargar el detalle de todas cuesta ~280 llamadas (3% del cupo diario), pero toma ~10 minutos con la pausa de 2 s. No cabe en una llamada del agente: requiere precarga programada.
- Tipos observados por sufijo del código: LE 149, LP 54, L1 42, LR 19, O1 11, CO 3, B2 2, E2 1.
- `Comprador.RegionUnidad` viene con espacio al final (normalizar). En un caso la región/comuna de la unidad no calza con el nombre del organismo: la región es la que declara la unidad compradora.
- `Fechas.FechaCierre` es la fecha útil de cierre; `FechaCierre` de primer nivel viene en `None` en el detalle.
- **No hay adjuntos ni garantías** en la API: confirma que bases, anexos, seriedad de la oferta y garantías salen de la ficha web y de los documentos.

## Requerimiento → campo

| Req. | Dato | Campo API | Estado |
| --- | --- | --- | --- |
| 3a / 5a | ID | `CodigoExterno` | OK |
| 3b / 5b | Nombre | `Nombre` | OK |
| 3c / 5d | Monto | `MontoEstimado` + `Moneda` + `VisibilidadMonto` | OK, puede venir oculto |
| 3d | Fecha publicación | `Fechas.FechaPublicacion` | OK |
| 3e / 5f | Fecha cierre | `Fechas.FechaCierre` | OK |
| 5c | Solicitante | `Comprador.NombreOrganismo`, `Comprador.NombreUnidad` | OK |
| 5e | Fecha apertura | `Fechas.FechaActoAperturaTecnica`, `Fechas.FechaActoAperturaEconomica` | OK |
| 5g | Descripción | `Descripcion` | OK |
| 5h | Días al cierre | Calculado desde `Fechas.FechaCierre` (`DiasCierreLicitacion` no sirve: es la duración total) | Calcular |
| 5i | Adjuntos | — | Ficha web |
| 2b | Palabra clave | `Nombre` (listado); `Descripcion`, `Items.Listado[].Descripcion` (detalle) | OK |
| 2c | Región | `Comprador.RegionUnidad` | Solo detalle |
| 2e | Tipo licitación | `Tipo` (L1, LE, LP, LR…) y sufijo de `CodigoExterno` | OK |
| 2f | Monto | `MontoEstimado` | Solo detalle |
| 2g | Mis rubros | `Items.Listado[].CodigoCategoria` / `CodigoProducto` (código ONU de 8 dígitos) | Solo detalle |
| 2h | Organismo | Parámetro `CodigoOrganismo`; `Comprador.CodigoOrganismo` | OK |
| 2i | Solo publicadas | Parámetro `estado=publicada`; `Estado` | OK |
| IA-k | Etapas | `Etapas` (1 o 2), `EstadoEtapas` | Parcial: completar con bases |
| IA-m | Contrato | `Contrato` (0/1), `TiempoDuracionContrato`, `EsRenovable` | Parcial |
| IA-h | Plazo preguntas | `Fechas.FechaFinal` (a validar que sea fin de preguntas) | A validar |
| IA-i | Plazo respuestas | `Fechas.FechaPubRespuestas` | OK |
| IA-n | Productos | `Items.Listado[]` (producto, descripción, cantidad, unidad) | OK |
| IA-e | Visita / muestras | `Fechas.FechaVisitaTerreno`, `DireccionVisita` (muestras: bases) | Parcial |
| Resto IA | Seriedad, garantía fiel cumplimiento, requisitos, formularios, integridad, criterios, patente/SEREMI, informes, certificados | — | Bases (adjuntos) |

## Exploración complementaria (23-10-2026, `scripts/probe_organismos.py`)

- **`estado=activas` sin fecha** devuelve todas las vigentes en una sola llamada: 5.086 licitaciones en 0,2 s, con los mismos 4 campos del listado. Cierre más lejano: 23-02-2027. Algunas vienen sin `FechaCierre`.
- Tipos en activas: LE 2.143, LP 1.352, LR 665, L1 426, O1 350, CO 63, B2 37, LS 19, E2 15, I2 15, O2 1.
- **`Empresas/BuscarComprador`** devuelve los 899 organismos compradores en una llamada (`listaEmpresas[]` con `CodigoEmpresa` y `NombreEmpresa`). `buscar_organismo` puede buscar sobre esa lista guardada en caché (1 llamada al día).
- **`CodigoOrganismo` + `estado=activas`** funciona: 48 licitaciones activas del organismo 7202 (DGAC). Ojo: el prefijo de `CodigoExterno` (ej. 1116005) es la unidad compradora, no el código del organismo.

## Consecuencia para la precarga (ADR 0007)

Precargar el detalle de las 5.086 activas cuesta ~5.100 llamadas y ~2,8 horas con la pausa de 2 s. Se reparte en 2 noches (≈2.500 llamadas por noche, dentro del presupuesto interno de 8.000). Después, la precarga incremental solo pide lo nuevo (~280 al día).

## Pendiente de explorar

- Significado exacto de `Fechas.FechaFinal` y de los sufijos O1, O2, CO, B2, E2, I2, LS
- Por qué algunas activas vienen sin `FechaCierre`

# Matriz de campos – API de Compra Ágil v2

Fuente: `scripts/probe_compra_agil.py` y `probe_compra_agil_2.py` (23-10-2026). Base `https://api2.mercadopublico.cl`, ticket en header `ticket`.

## Hallazgos

- **9.076 Compras Ágiles publicadas** (182 páginas de 50). Región 10 (Los Lagos) sola: 704.
- **El listado ya trae región, monto, organismo, fechas y documentos** (`documentos[].id`, `nombre`): filtrar no requiere detalle. Precargar todo el listado cuesta ~182 llamadas (~4 s cada una).
- **Detalle:** `/v2/compra-agil/{codigo}` responde (~8 s); `/v2/compraagil/{codigo}` devuelve 403. Trae `productos_solicitados[]` con código ONU, nombre, descripción, cantidad y unidad; `entrega.direccion_entrega` y `plazo_entrega_dias`.
- **No trae marca ni vencimiento** (habrá que buscarlos en la descripción del producto o en los documentos) **ni URL de descarga** de documentos (solo id y nombre).
- **`q` (palabra clave) no funciona:** 504 a los ~30 s, sola o con región. → la búsqueda por palabra clave se hace localmente sobre lo precargado.
- **Sincronización incremental no funciona:** `ttl_cambio_ms` (1 h y 3 h) y `cambio_desde` en UTC devuelven 0, aunque hay compras modificadas minutos antes. → no se usa.
- Fechas sin zona horaria (`2026-10-26 10:00`), se asumen America/Santiago. `institucion.nombre_region` con espacio al final.
- La respuesta no trae encabezados de cuota.

## Requerimiento → campo

| Req. | Dato | Campo | Estado |
| --- | --- | --- | --- |
| 3a | ID | `codigo` (ej. 3287-534-COT26) | OK |
| 3b | Nombre | `nombre` | OK |
| 3c | Monto | `montos.monto_disponible_clp` (listado), `presupuesto.*` (detalle) | OK |
| 3d / 3e | Publicación / cierre | `fechas.fecha_publicacion`, `fechas.fecha_cierre` (+ primer/segundo llamado) | OK |
| 2c | Región | `institucion.region` (1–16) y parámetro `region` | OK |
| 2h | Organismo | `institucion.organismo_comprador`, `institucion.rut` (sin parámetro: filtro local) | Local |
| 2b | Palabra clave | `nombre`, `descripcion`, `productos_solicitados[].descripcion` | Local (q da 504) |
| 2g | Mis rubros | `productos_solicitados[].codigo_producto` (solo detalle) | Solo detalle |
| 4a | Adjuntos | `documentos[].id`, `nombre` | Sin descarga: ficha web |
| 4b | Productos / marca | `productos_solicitados[]`; marca: texto libre | Parcial |
| 4c | Vencimiento | — | Documentos / texto |
| 4d | Cantidad | `productos_solicitados[].cantidad`, `unidad_medida` | OK |

# API de datos abiertos OCDS

- Endpoint que responde: `https://apis.mercadopublico.cl/OCDS/data/record/{codigo}` y `/OCDS/data/tender/{codigo}` (sin ticket).
- Para licitaciones activas (1705-26-L126 publicada hoy y 1116005-7-LE26 más antigua) responde `{"status": 404, "detail": "No se encontraron resultados."}`.
- Conclusión provisional: OCDS no cubre procesos vigentes (o usa otro identificador). No sirve para obtener adjuntos en la POC. Queda incluido en la consulta formal a ChileCompra (`docs/consulta-chilecompra.md`, pregunta 2).

# Códigos ONU por giro (24-10-2026, `scripts/codigos_onu_giro.py`)

| Giro | Códigos | Observación |
| --- | --- | --- |
| Venta Alimentos | segmento `50` + `90101603` (catering) | Códigos mal asignados con frecuencia: siempre combinar con palabras clave |
| Baños químicos | `30201706` (Baños portátiles) | `71131103` (limpieza general) también aparece en servicios de limpieza de baños químicos, pero es genérico: se cubre con palabras clave. Volumen bajo: 2 Compras Ágiles en 1.500 recientes y 1 licitación entre 5.141 activas |
