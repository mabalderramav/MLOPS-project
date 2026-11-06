"""Genera los lotes de la prueba de data drift, con semilla fija, a partir de `produccion`."""
from pathlib import Path

from datos import SEMILLA, particiones
from drift import TAMANO_LOTE, pesos_verano

CARPETA = Path(__file__).parent / "lotes"


def main() -> None:
    _, _, produccion = particiones()
    CARPETA.mkdir(exist_ok=True)
    lotes = {
        "mismo_origen": produccion.sample(TAMANO_LOTE, random_state=SEMILLA),
        "verano": produccion.sample(
            TAMANO_LOTE, weights=pesos_verano(produccion), random_state=SEMILLA
        ),
    }
    for nombre, lote in lotes.items():
        lote.to_csv(CARPETA / f"{nombre}.csv", index=False)
        print(f"lotes/{nombre}.csv: {len(lote)} filas")


if __name__ == "__main__":
    main()
