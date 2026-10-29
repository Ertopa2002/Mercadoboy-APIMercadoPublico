# Ficha de análisis de bases

La ficha es la salida del agente cuando el usuario sube las bases y anexos de un proceso. Siempre
tiene los mismos 18 campos (`evals/ficha/campos.json`) y se valida contra el set de referencia
antes del piloto (meta: ≥ 90% de acierto por campo, hito H2).

## Reglas

1. **Cita obligatoria.** Cada dato lleva `fuente: {documento, pagina}`.
2. **"No indicado".** Si el dato no aparece en los documentos, el campo es exactamente
   `"No indicado"`. Prohibido inferir o completar con conocimiento general.
3. **Discrepancias.** Si el documento y la ficha del portal difieren (plazos, montos, cantidades),
   se informa en `discrepancias_portal` y en el campo se usa el valor del documento.
4. **Revisión humana.** La ficha termina siempre con el aviso: *"Ficha generada por IA: revisa las
   bases antes de ofertar."*
5. **Calidad de lectura.** Si el PDF es escaneado o hay páginas ilegibles, `calidad_lectura =
   parcial` y se indican las páginas afectadas.
6. **Compras Ágiles.** Suelen traer un solo documento (requerimiento o cotización); los campos de
   licitación que no aplican (seriedad, etapas, contrato…) quedan "No indicado".

## Campos

| # | Campo | Qué se registra |
|---|---|---|
| 1 | Garantía de seriedad de la oferta | Si se exige; monto, forma (boleta, vale vista, póliza…) y vigencia |
| 2 | Vigencia de la oferta | Días o fecha |
| 3 | Requisitos administrativos | Lista completa |
| 4 | Requisitos técnicos | Lista completa |
| 5 | Muestras | Si se exigen; cantidad, lugar, encargado y fecha |
| 6 | Formularios y anexos | Lista de anexos que el oferente debe presentar |
| 7 | Programa de integridad | Sí / no |
| 8 | Plazos de preguntas y respuestas | Fin de preguntas y publicación de respuestas |
| 9 | Criterios de evaluación | Criterio y ponderación |
| 10 | Etapas | Una o dos etapas, con fechas de apertura |
| 11 | Garantía de fiel cumplimiento | Si se exige; monto (o %) y vigencia |
| 12 | Contrato | Si se firma contrato; duración |
| 13 | Productos solicitados | Producto, cantidad, unidad, especificación, marca, exigencia de marca (exacta / o similar / sin marca), vencimiento mínimo |
| 14 | Patente y resoluciones SEREMI | Si se exigen y cuáles |
| 15 | Informes comerciales y certificados | Cuáles se exigen |
| 16 | Plazo y lugar de entrega | Según documento |
| 17 | Condiciones de pago y multas | Forma y plazo de pago, multas y sanciones |
| 18 | Otros requisitos | Lo que no calce en los campos anteriores |

## Glosario

- **Seriedad de la oferta:** garantía que asegura que el oferente mantiene su oferta; se devuelve
  al adjudicar.
- **Fiel cumplimiento:** garantía que entrega el adjudicado para asegurar la ejecución del contrato.
- **Programa de integridad:** programa de cumplimiento ético del oferente (Ley 21.634); puede dar
  puntaje.
- **Una o dos etapas:** apertura técnica y económica en el mismo acto o en actos separados.
- **"O similar":** se acepta otra marca de características equivalentes.
- **UTM / UF:** unidades de cuenta chilenas; se registran tal como aparecen.

## Set de evaluación

- `evals/esperados/<codigo>.json`: respuesta esperada, validada por una persona con experiencia en
  licitaciones (`"validado_por"` y fecha).
- `evals/salidas/<codigo>.json`: ficha generada por el agente (no se versiona).
- `uv run python scripts/evaluar_fichas.py`: acierto por campo y total, y citas correctas.

Criterio de acierto por tipo de campo: sí/no exacto; texto por similitud (≥ 0,75 tras normalizar);
listas por F1 de ítems emparejados (≥ 0,8); objetos por su campo clave (`exige`) más los
subcampos con valor; productos por emparejamiento de nombre y cantidad igual.
