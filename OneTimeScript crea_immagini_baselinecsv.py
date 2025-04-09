import os
import pandas as pd
from pathlib import Path

BASELINE_FOLDER = "Immagini Baseline"
OUTPUT_FILE = "immagini_baseline.csv"

def genera_csv_immagini_baseline():
    dati = []
    id_immagine = 1

    for genere in ["uomo", "donna"]:
        sotto_cartella = Path(BASELINE_FOLDER) / genere
        if not sotto_cartella.is_dir():
            continue

        for nome_file in sorted(os.listdir(sotto_cartella)):
            if nome_file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                path_completo = (sotto_cartella / nome_file).as_posix()
                dati.append({
                    "idImmagine": id_immagine,
                    "genere_del_capo": genere.capitalize(),
                    "path_immagine": path_completo
                })
                id_immagine += 1

    df = pd.DataFrame(dati)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"File '{OUTPUT_FILE}' creato con successo! ({len(df)} immagini)")

if __name__ == "__main__":
    genera_csv_immagini_baseline()