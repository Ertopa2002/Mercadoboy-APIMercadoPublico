# 0008 – Adjuntos: subida manual en la POC

- Estado: aceptada
- Fecha: 2026-10-23

## Contexto
Ninguna API (Licitaciones ni Compra Ágil v2) permite descargar adjuntos: Compra Ágil solo entrega id y nombre de cada documento. En la web, la página de adjuntos de licitaciones (`ViewAttachment.aspx`) exige reCAPTCHA Enterprise y redirige a 403 si no se supera, y el buscador de Compra Ágil responde 403 a peticiones automáticas. Las políticas de uso de ChileCompra permiten bloquear BOT que comprometan la plataforma.

## Decisión
- No se automatiza la descarga de adjuntos ni se elude ningún control (captcha, 403).
- En la POC el usuario descarga las bases y anexos desde su navegador y los sube al chat; el agente los analiza y llena la ficha.
- Las herramientas muestran qué documentos tiene cada proceso (Compra Ágil: nombre e id vía API) y el enlace a la ficha web.
- Se envía consulta formal a ChileCompra por una vía oficial de acceso a documentos y se explora la API de datos abiertos (OCDS).

## Consecuencias
- Los puntos 4.a y 5.i del requerimiento quedan parciales: se informa qué adjuntos hay, pero la descarga es manual.
- `obtener_adjuntos` pasa a: listar documentos conocidos + procesar archivos entregados por el usuario.
- En Etapa 2 la plataforma tendrá un botón para subir adjuntos, salvo que ChileCompra habilite una vía oficial.
