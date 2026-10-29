# 0010 – Front web (buscador + dashboard) dentro de la POC

**Estado:** aceptado (27-10-2026)

## Contexto
El requerimiento inicial pide una plataforma multiusuario con filtros y ficha de cada proceso. La
propuesta lo dejaba en la Etapa 2; para la POC se decidió adelantar una versión mínima para
mostrar al cliente.

## Decisión
- Módulo `web/`: API de solo lectura sobre el índice precargado (`/api/buscar`,
  `/api/estadisticas`, `/api/opciones`, `/api/proceso/{c}`, `/api/adjuntos/{c}`) y una página
  estática con dos pestañas (Buscador y Dashboard) que comparten el panel de filtros.
- Se sirve desde la misma función del conector (`/<token>/`), sin infraestructura nueva: mismo
  token en la ruta que el MCP (ADR 0003). La página envía `no-referrer` para que el token no
  viaje a Mercado Público al abrir una ficha.
- No llama a la API de Mercado Público (no gasta cupo); el filtrado reutiliza `mp_core.filtros`
  y se cachea por filtro. Se ocultan procesos con cierre vencido.
- Sin análisis con IA en el front: seguiría la API de Claude (costo por uso, fuera de la
  propuesta). El análisis de bases sigue en Claude con el conector.

## Consecuencias
- Acceso por enlace con token (sin usuarios). El login y los perfiles por usuario quedan para la
  Etapa 2 (Cognito).
- El dashboard muestra solo procesos vigentes; las tendencias se acumulan desde la puesta en
  marcha.
- Procesos sin detalle (sin región ni organismo) no se cuentan en esos gráficos.
