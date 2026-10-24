# Cupo y presupuesto de llamadas

Datos medidos (23 y 24-10-2026): ~550 licitaciones publicadas al día; 5.086 licitaciones activas; 9.076 Compras Ágiles publicadas; 1.174 Compras Ágiles nuevas en 24 h.

## Consumo estimado

| Proceso | API | Llamadas/día |
| --- | --- | --- |
| Carga inicial del detalle de licitaciones activas (una vez, repartida en 2 noches) | Licitaciones | ~2.550 por noche |
| Listado de activas, cada 3 h | Licitaciones | 8 |
| Detalle de licitaciones nuevas | Licitaciones | ~550 |
| Lista de organismos | Licitaciones | 1 |
| Detalle a pedido del agente | Licitaciones | ~50 |
| Barrido nocturno del listado de publicadas | Compra Ágil | ~182 |
| Nuevas publicaciones cada 3 h | Compra Ágil | ~30 |
| Detalle (productos) de compras nuevas que calzan con el perfil | Compra Ágil | ~120 |
| Detalle a pedido del agente | Compra Ágil | ~50 |
| **Total régimen** | | **~1.000** |
| **Total noches de carga inicial** | | **~3.550** |

## Presupuesto y alertas

- Presupuesto interno: **8.000 llamadas/día** (80% del cupo de 10.000). Al llegarlo, el core deja de llamar hasta el día siguiente y responde "cupo diario agotado".
- Avisos al agente (y en logs) al **70%** (5.600) y **90%** (7.200).
- El contador se reinicia a las 00:00 America/Santiago (la cuota de Compra Ágil es por día calendario).
- Pausa entre llamadas: 2 s en la precarga; sin pausa en llamadas puntuales del agente.

## Supuestos a confirmar

- Que ambas APIs compartan el mismo cupo de 10.000 diario. La documentación de Compra Ágil habla de una cuota por ticket sin dar el número; se cuentan juntas por prudencia.
- El detalle de Compra Ágil tarda ~8 s: pedirlo para las ~1.170 nuevas diarias tomaría ~2,6 h, por eso solo se pide para las que calzan con el perfil y a pedido.
