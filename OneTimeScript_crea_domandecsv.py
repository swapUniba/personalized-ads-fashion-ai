import pandas as pd

def crea_file_domande():
    # Configurazione
    DOMANDE_FILE = "domande.csv"
    ID_SET = 1
    
    # Lista ordinata delle domande
    domande = [
        "Personalizzazione: Quale delle due immagini ritieni sia più vicina al tuo stile personale?",
        "Intenzione d'Acquisto: Quale immagine ti aiuterebbe di più a decidere se acquistare il capo?",
        "Realismo: Quale immagine appare più realistica come rappresentazione del capo?",
        "Appeal Visivo: Quale immagine trovi esteticamente più convincente per indossare il capo?",
        "Fiducia: Quale immagine ti dà maggiore sicurezza che questo capo ti donerebbe?",
        "Differenziazione: Le due immagini ti sembrano chiaramente distinguibili l'una dall'altra?"
    ]
    
    # Crea la struttura dati
    data = {"id_set": [ID_SET]}
    for i, domanda in enumerate(domande, 1):
        data[f"domanda{i}"] = [domanda]
    
    try:
        # Crea e salva il DataFrame
        df = pd.DataFrame(data)
        df.to_csv(DOMANDE_FILE, index=False, encoding='utf-8-sig')
        print(f"File {DOMANDE_FILE} creato con successo!")
        print("Struttura creata:")
        print(df.to_markdown(index=False))
        
    except Exception as e:
        print(f"Errore durante la creazione del file: {str(e)}")

if __name__ == "__main__":
    crea_file_domande()