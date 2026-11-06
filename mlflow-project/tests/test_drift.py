import numpy as np
import pandas as pd
import pytest

from datos import OBJETIVO, VARIABLES, particiones
from drift import (
    aplicar_regla_nueva,
    comparar_lote,
    hay_data_drift,
    linea_temporal,
    pesos_verano,
    primer_sostenido,
    psi,
    revisar,
    umbral_metrica,
)


@pytest.fixture(scope="module")
def partes():
    return particiones()


def test_psi_es_casi_cero_con_la_misma_distribucion():
    serie = pd.Series(["a"] * 60 + ["b"] * 40)
    assert psi(serie, serie) == pytest.approx(0, abs=1e-9)


def test_psi_detecta_cambio_y_tolera_categorias_nuevas():
    referencia = pd.Series(["a"] * 80 + ["b"] * 20)
    assert psi(referencia, pd.Series(["a"] * 20 + ["b"] * 80)) > 0.25
    assert psi(referencia, pd.Series(["nueva"] * 100)) > 0.25


def test_compara_las_nueve_variables(partes):
    train, _, produccion = partes
    filas = comparar_lote(train, produccion.head(1000))
    assert [f["variable"] for f in filas] and len(filas) == len(VARIABLES)
    assert {f["prueba"] for f in filas} == {"KS (p-valor)", "PSI"}


def test_detector_ve_el_verano_y_no_el_lote_limpio(partes):
    train, _, produccion = partes
    limpio = produccion.sample(1000, random_state=42)
    verano = produccion.sample(1000, weights=pesos_verano(produccion), random_state=42)
    assert not hay_data_drift(train, limpio)
    assert hay_data_drift(train, verano)


def test_regla_nueva_no_altera_las_entradas(partes):
    _, _, produccion = partes
    lote = produccion.head(1000)
    nuevo = aplicar_regla_nueva(lote, 1.0, np.random.default_rng(0))
    pd.testing.assert_frame_equal(lote[VARIABLES], nuevo[VARIABLES])
    casados = lote["marital_status"] == "Married-civ-spouse"
    assert (nuevo.loc[casados, OBJETIVO] == 1 - lote.loc[casados, OBJETIVO]).all()
    assert (nuevo.loc[~casados, OBJETIVO] == lote.loc[~casados, OBJETIVO]).all()


def test_linea_temporal_tiene_doce_lotes_sin_repetir_filas(partes):
    _, _, produccion = partes
    lotes = linea_temporal(produccion, "regla_nueva")
    assert len(lotes) == 12 and all(len(lote) == 1000 for lote, _ in lotes)
    assert lotes[0][1] == 0 and lotes[-1][1] == 1


def test_alarma_exige_lotes_consecutivos():
    assert primer_sostenido([True, True, False, True, True, False]) is None
    assert primer_sostenido([False, True, True, True, True]) == 4


def test_umbral_usa_la_caida_minima_si_el_ruido_es_pequeno():
    assert umbral_metrica([0.90, 0.90, 0.90])[2] == pytest.approx(0.87)
    mu, sigma, umbral = umbral_metrica([0.8, 0.9, 1.0])
    assert umbral == pytest.approx(mu - 2 * sigma)


@pytest.mark.parametrize("data_drift, alarma, accion", [
    (False, False, "todo bien"),
    (True, False, "vigilar"),
    (False, True, "REENTRENAR"),
    (True, True, "REENTRENAR"),
])
def test_revisor(data_drift, alarma, accion):
    assert revisar(data_drift, alarma) == accion
