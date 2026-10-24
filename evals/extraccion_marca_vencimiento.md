# Prueba de extracción: marca, "o similar" y vencimiento desde la descripción

Muestra: `evals/muestra_productos_ca.json` · 20 Compras Ágiles publicadas el 23–24-10-2026 · 99 productos. Esquema: `analysis/esquema_producto.json`. Extracción hecha por IA y pendiente de validación humana.

## Resumen

| Resultado | Productos |
| --- | --- |
| Marca exacta | 16 |
| Una de varias marcas (alternativas) | 5 |
| "o similar" explícito | 4 |
| Marca referencial ("tipo X") | 5 |
| Exigencia de vencimiento | 4 (sin meses: "fecha extendida de vencimiento" + carta de canje) |
| Remite a archivo adjunto | 9 |
| Sin marca | 69 |

## Productos con hallazgos

| Compra | Producto | Marca | Exigencia | Vencimiento / condiciones |
| --- | --- | --- | --- | --- |
| 4894-341-COT26 | Endulzante líquido Daily Stevia 270 ml | Daily | exacta | — |
| 4894-341-COT26 | Azúcar Iansa 1 kg | Iansa | exacta | — |
| 4894-341-COT26 | Azúcar Iansa sachet 5 g (500 un) | Iansa | exacta | — |
| 4894-341-COT26 | Endulzante Stevia sachet 100 un - Iansa Cero K | Iansa Cero K | exacta | — |
| 4894-341-COT26 | Galletas Mckay 40 g surtidas | McKay | exacta | — |
| 4894-341-COT26 | Galletas dulces surtidas (Costa Frac, Tritón, Mackay…) | Costa, McKay | alternativas | — |
| 4894-341-COT26 | Café Haití molido 250 g | Haití | exacta | — |
| 4894-341-COT26 | Café Haití en granos 250 g | Haití | exacta | — |
| 4894-341-COT26 | Café Nescafé stick caja 96 un | Nescafé | exacta | — |
| 4894-341-COT26 | Jugos néctar Watts 200 ml | Watts | exacta | — |
| 4894-341-COT26 | Agua mineral sin gas Cachantún 600 ml | Cachantún | exacta | — |
| 2107-314-COT26 | Galletas Tritón vainilla 116 g | Tritón | exacta | — |
| 1480972-756-COT26 | Sándwich jamón queso 175 g tipo Daily Frech | Daily Frech | referencial | envasado |
| 1480972-756-COT26 | Barra de cereal 30 g tipo Quaker | Quaker | referencial | sin sellos |
| 1480972-756-COT26 | Agua mineral 500 ml tipo Cachantún | Cachantún | referencial | — |
| 1480972-756-COT26 | Jugo 200 ml tipo Livean | Livean | referencial | sin sello |
| 1480972-756-COT26 | Compota 90 g tipo Vivo | Vivo | referencial | sin sello |
| 617807-2444-COT26 | Fresubin 2kcal HP 500 ml | Fresubin | exacta | carta de canje y fecha extendida de vencimiento |
| 617807-2444-COT26 | Survimed OPD HN 500 ml | Survimed | exacta | carta de canje y fecha extendida de vencimiento |
| 617807-2444-COT26 | Nepro AP | Nepro | exacta | carta de canje y fecha extendida de vencimiento |
| 617807-2444-COT26 | Enterex espesante | Enterex | exacta | carta de canje y fecha extendida de vencimiento |
| 617807-2444-COT26 | Proteinex o Enterex en polvo | Proteinex, Enterex | alternativas | — |
| 4894-334-COT26 | Toalla de papel / papel higiénico | Tork, Elite | alternativas (2 productos) | marca solicitada en cotización |
| 4894-330-COT26 | Bolsa de basura 80x110 | Superior | o_similar | — |
| 4894-330-COT26 | Escobillón grandes superficies | Virutex | o_similar | — |
| 4894-330-COT26 | Cloro bidón 5 L | AIS | o_similar | — |
| 4894-330-COT26 | Raid Max sin olor | SC Johnson (Raid) | exacta | — |
| 4894-330-COT26 | Desodorante ambiental | Winnex World, Arom | alternativas | — |
| 1057539-4706-COT26 | Asistente de voz | Alexa | o_similar | — |

Remiten a adjunto: agua mineral 600 ml (2432-846), los 5 productos de carnes blancas (1057547-2402), colaciones HPV (1658-1614), traslado de escolares (2432-845) y transporte (867990-730).

## Hallazgos para el diseño

1. **La marca sí aparece en el texto** en ~1 de cada 4 productos, y el matiz importa: "tipo Cachantún" (referencial) no es lo mismo que "Cachantún" (exacta) ni que "AIS o similar". El esquema distingue los cuatro casos.
2. **El vencimiento casi nunca viene en la descripción** (solo 4 de 99, sin plazo en meses). En alimentos suele estar en las especificaciones adjuntas → depende de la subida manual.
3. **Condiciones útiles que salen gratis:** sin sellos, sin gluten, carta de canje, ficha técnica, cotización formal, despacho pagado, horario de recepción en bodega.
4. **Los códigos ONU vienen mal asignados con frecuencia:** colaciones bajo "Jugos y néctar concentrados", leche en polvo y té bajo "papas, arroz o pastas congeladas", esencia de vainilla bajo "semillas de vainilla". El filtro por rubro no puede depender solo del código ONU.
5. **El filtro por palabra en el nombre es ruidoso:** 9 de las 20 compras no eran de alimentos (traslado, asistente de voz, papel, aseo, lentes). Mejor filtro: segmento ONU 50 (alimentos) **o** palabras clave en las descripciones de productos, combinados.
