"""Enlaces a la web de Mercado Público para que el usuario descargue adjuntos (ADR 0008).

Solo se lee la ficha pública de una licitación (no protegida) para obtener el enlace cifrado a
su página de adjuntos. Esa página exige reCAPTCHA: la abre el usuario en su navegador.
Una petición por proceso, a pedido, con caché de 24 h. Nunca se descarga ni se elude nada.
"""

import html
import re

import httpx

from mp_core.models import FICHA_LICITACION
from mp_core.store import Store

UA = "Mercadoboy-POC/0.1 (contacto pcisterna@aptivia.net)"
ATTACH = "https://www.mercadopublico.cl/Procurement/Modules/Attachment/ViewAttachment.aspx?enc="


def url_adjuntos_licitacion(
    codigo: str, store: Store, http: httpx.Client | None = None
) -> str | None:
    clave = f"web:adj:{codigo}"
    if (cache := store.get(clave)) is not None:
        return cache or None
    http = http or httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": UA})
    try:
        r = http.get(FICHA_LICITACION + codigo)
    except httpx.HTTPError:
        return None
    m = re.search(r"ViewAttachment\.aspx\?enc=([^'\"&]+)", html.unescape(r.text))
    url = ATTACH + m.group(1) if m else ""
    store.put(clave, url, ttl_s=86_400)
    return url or None
