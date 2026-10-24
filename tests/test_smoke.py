from mp_core import config


def test_base_url():
    assert config.BASE_URL.startswith("https://api.mercadopublico.cl")


def test_timezone():
    assert str(config.TZ) == "America/Santiago"
