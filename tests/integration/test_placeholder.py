import pytest


@pytest.mark.skip(
    reason=(
        "Placeholder: el escenario multi-peer real (3+ peers, should_forward, "
        "estado agregado del suscriptor) depende de las capas de Rol 1 y Rol 2. "
        "Ver issue #2 y #1 -- reemplazar este test cuando esas capas existan."
    )
)
def test_multi_peer_publish_subscribe_placeholder():
    pass
