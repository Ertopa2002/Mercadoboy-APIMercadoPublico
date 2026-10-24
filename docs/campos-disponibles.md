# Campos disponibles por fuente

Inventario de lo que se puede obtener hoy (exploración 23–24-10-2026). Detalle técnico en `docs/matriz-campos.md`.

Leyenda de "Cómo": **API** = viene directo · **Calc** = lo calculamos · **IA-texto** = la IA lo extrae de un texto que sí trae la API · **Docs** = solo en adjuntos (subida manual, ADR 0008).

## 1. Licitaciones (API v1, detalle por código)

| Grupo | Campos | Cómo |
| --- | --- | --- |
| Identificación | Código (`CodigoExterno`), nombre, descripción, tipo (L1, LE, LP, LR, LQ, O1, CO…), código de tipo, estado y código de estado, código BIP, si usa bases tipo | API |
| Montos | Monto estimado, moneda, visibilidad del monto, justificación del monto, si es estimación | API |
| Comprador | Organismo (código y nombre), unidad (código, nombre, RUT, dirección, comuna, **región**), usuario comprador (nombre, cargo) | API |
| Fechas | Creación, publicación, **cierre**, fin de preguntas (`FechaFinal`, a validar), publicación de respuestas, visita a terreno, entrega de antecedentes, soporte físico, apertura técnica, apertura económica, adjudicación y adjudicación estimada, firma estimada, tiempo de evaluación | API |
| Plazos | Días de duración de la publicación, **días restantes al cierre** | API / Calc |
| Ítems | Por producto: correlativo, **código ONU** (categoría y producto), categoría, nombre, descripción, **cantidad**, unidad de medida, adjudicación | API |
| Contrato | Si hay contrato, duración y unidad, si es renovable y período de renovación, si permite subcontratación, tipo de pago, si requiere toma de razón, si es obra | API |
| Responsables | Nombre, correo y teléfono del responsable del contrato y del pago; dirección de entrega y de visita | API (suelen venir vacíos) |
| Proceso | Número de etapas (1 o 2) y estado, tipo de convocatoria, modalidad, publicidad de ofertas y su justificación, extensión de plazo, cantidad de reclamos del organismo, fuente de financiamiento, prohibición de contratación | API |
| Adjudicación | Datos de adjudicación (cuando existe) | API |

## 2. Compras Ágiles (API v2)

| Grupo | Campos | Cómo |
| --- | --- | --- |
| Identificación | Código (ej. 3287-534-COT26), nombre, descripción, estado (id, código, glosa) | API |
| Convocatoria | Primer o segundo llamado, cierre del primer y del segundo llamado | API |
| Fechas | Publicación, **cierre**, último cambio, cancelación | API |
| Montos | Moneda, monto disponible, monto en CLP, presupuesto estimado, tipo (disponible o estimado), tipo de cambio | API |
| Comprador | Organismo, RUT, unidad de compra, **región** (código 1–16 y nombre) | API |
| Entrega | **Dirección de entrega**, **plazo de entrega en días** | API (detalle) |
| Productos | Por producto: **código ONU**, nombre, descripción, **cantidad**, unidad de medida | API (detalle) |
| Marca / "o similar" / vencimiento | Desde la descripción del producto o de la compra | IA-texto |
| Documentos | Nombre e identificador de cada adjunto (sin descarga) | API |
| Competencia | Total de ofertas recibidas; por proveedor que cotiza: RUT, razón social, si es empresa de menor tamaño, montos (neto, impuesto, despacho, total), vigencia, productos cotizados con precio unitario | API (detalle; según la doc, algunos sin confirmar) |
| Resultado | Proveedor seleccionado y motivo, motivo de cancelación o de desierta, orden de compra emitida (id) | API |
| Otros | Multa o sanción, total de demandas, si considera requisitos medioambientales o de impacto social | API |

## 3. Organismos compradores

| Campos | Cómo |
| --- | --- |
| Código y nombre de los 899 organismos | API (1 llamada) |

## 4. Desde los adjuntos (bases, anexos, formularios)

Solo cuando el usuario sube los documentos. La IA llena la ficha de análisis:

Seriedad de la oferta · vigencia de la oferta · requisitos administrativos · requisitos técnicos · muestras (cantidad, lugar, encargado, fecha) · formularios a llenar · programa de integridad · criterios de evaluación y ponderaciones · garantía de fiel cumplimiento · patente y resoluciones SEREMI · informes comerciales · certificados · marca y vencimiento exigidos · otros requisitos.

## 5. Calculados o derivados

Días restantes al cierre · si calza con "mis rubros" (código ONU del ítem contra el perfil) · si calza con palabras clave (nombre, descripción, ítems) · tipo de proceso por sufijo del código · alerta de cierre próximo · historial de compras de un organismo (con lo precargado).
