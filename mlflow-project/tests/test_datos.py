import pandas as pd
import pytest

from datos import OBJETIVO, VARIABLES, particiones


@pytest.fixture(scope="module")
def partes():
    return particiones()


def test_tamanos(partes):
    train, test, produccion = partes
    assert (len(train), len(test), len(produccion)) == (24406, 9762, 14645)


def test_particiones_deterministas(partes):
    for original, repetida in zip(partes, particiones()):
        pd.testing.assert_frame_equal(original, repetida)


def test_particiones_sin_solapamiento(partes):
    train, test, produccion = partes
    assert not set(train.index) & set(test.index)
    assert not set(train.index) & set(produccion.index)
    assert not set(test.index) & set(produccion.index)


def test_sin_valores_faltantes_y_objetivo_binario(partes):
    train, _, _ = partes
    assert train[VARIABLES].notna().all().all()
    assert set(train[OBJETIVO].unique()) == {0, 1}
    # El objetivo se limpió bien: ninguna etiqueta de adult.test quedó sin normalizar.
    assert 0.2 < train[OBJETIVO].mean() < 0.3
