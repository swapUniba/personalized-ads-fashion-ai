import gradio as gr
import pandas as pd
from models import generate_fashion_prompt, generate_adv_image # funzioni usate per la generazione

# Inizializza i file e i dataset
data_file = "registrazioni.csv"
questionnaire_file = "questionario.csv"
IMMAGINI_GENERATE_FILE = "immagini_generate.csv"
IMMAGINI_BASELINE_FILE = "immagini_baseline.csv"
questions_file = "domande.csv"
QUESTION_SET_ID = 1

# Usata per memorizzare l'ordine casuale per ogni tab
DISPLAY_ORDERS = {}
# Usata per controllare le generazioni
GENERATED_TABS = {}

# Variabili globali id utente, immagini baseline
CURRENT_USER_ID = None  # Sarà impostato dopo la registrazione
CURRENT_USER_GENDER = None  # Utile per determinare le immagini da mostrare
BASELINE_IMAGES = {
    "Uomo": {
        1: "Immagini Baseline/uomo/baseline1.jpg",
        2: "Immagini Baseline/uomo/baseline2.jpg",
        3: "Immagini Baseline/uomo/baseline3.jpg",
        4: "Immagini Baseline/uomo/baseline4.jpg"
    },
    "Donna": {
        1: "Immagini Baseline/donna/baseline1.jpg",
        2: "Immagini Baseline/donna/baseline2.jpg",
        3: "Immagini Baseline/donna/baseline3.jpg",
        4: "Immagini Baseline/donna/baseline4.jpg"
    }
}

# Se immagini_baseline.csv non esiste lo crea altrimenti lo apre
try:
    df_baseline = pd.read_csv(IMMAGINI_BASELINE_FILE)
except FileNotFoundError:
    baseline_data = []
    idImmagine = 1
    for genere in ["Uomo", "Donna"]:
        for num in range(1, 5):
            path = BASELINE_IMAGES[genere][num]
            baseline_data.append({
                "idImmagine": idImmagine,
                "genere_del_capo": genere,
                "path_immagine": path
            })
            idImmagine += 1
    df_baseline = pd.DataFrame(baseline_data)
    df_baseline.to_csv(IMMAGINI_BASELINE_FILE, index=False)

# idem ma per questionario
try:
    questionnaire_data = pd.read_csv(questionnaire_file)
    if not questionnaire_data.empty and 'idQuestionario' in questionnaire_data.columns:
        next_questionnaire_id = questionnaire_data['idQuestionario'].max() + 1
    else:
        next_questionnaire_id = 1
except (FileNotFoundError, ValueError):
    next_questionnaire_id = 1
    
next_generation_id = 1

# idem ma per dataset utenti
try:
    # Legge il file esistente con encoding UTF-8
    dataset = pd.read_csv(data_file, encoding='utf-8', engine='python')
    # Calcola il prossimo ID
    next_id = dataset['idUtente'].max() + 1 if not dataset.empty else 1
except FileNotFoundError:
    # Crea nuovo dataset
    dataset = pd.DataFrame(columns=[
        "idUtente", "nome", "cognome", "eta", "nazione", "genere", 
        "corrente_artistica_preferita", "professione",
        "colori_preferiti", "generi_musicali_preferiti", 
        "cosa_cerchi_nei_capi", "marchi_preferiti",
        "competenza_moda", "interesse_moda"
    ])
    dataset.to_csv(data_file, index=False, encoding='utf-8-sig')
    next_id = 1  # Parte da 1 per il primo utente

# idem ma per dataset immagini generate
try:
    immagini_generate = pd.read_csv(IMMAGINI_GENERATE_FILE)
    if 'idGenerazione' in immagini_generate.columns:
        next_generation_id = immagini_generate['idGenerazione'].max() + 1
    else:
        next_generation_id = 1
except FileNotFoundError:
    next_generation_id = 1

# Caricamento Domande sul Sito
def load_questions(file_path, question_set_id=QUESTION_SET_ID):
    try:
        df = pd.read_csv(file_path)
        # Filtra per id_set e seleziona le colonne delle domande
        selected = df[df["id_set"] == question_set_id]
        if selected.empty:
            return ["Domanda 1", "Domanda 2", "Domanda 3"]  # Default
        
        # Estrai le domande (ignora la colonna id_set)
        questions = selected.iloc[0, 1:].dropna().tolist()
        return [q.strip() for q in questions if q.strip()]
        
    except FileNotFoundError:
        return ["Domanda 1", "Domanda 2", "Domanda 3"]
    except Exception as e:
        print(f"Errore nel caricamento delle domande: {str(e)}")
        return ["Domanda 1", "Domanda 2", "Domanda 3"]

# INIZIALIZZAZIONE DATASET QUESTIONARI CON DOMANDE DINAMICHE
max_questions = 6  # Numero massimo di domande per set (domanda1-domanda6)
required_columns = ["idQuestionario", "idUtente", "id_immagine_generata", "id_set_domande"]

try:
    questionnaire_data = pd.read_csv(questionnaire_file, encoding='utf-8')
    
    # Verifica struttura corretta
    if not all(col in questionnaire_data.columns for col in required_columns) or \
        not all(f"domanda{i}" in questionnaire_data.columns for i in range(1, max_questions + 1)):
        
        raise ValueError("Struttura modificata, rigenero il dataset")
        
except (FileNotFoundError, ValueError):
    # Crea colonne domanda1-domanda6
    question_columns = [f"domanda{i}" for i in range(1, max_questions + 1)]
    questionnaire_data = pd.DataFrame(columns=required_columns + question_columns)
    questionnaire_data.to_csv(questionnaire_file, index=False, encoding='utf-8-sig')

# Funzioni per la gestione
def handle_registration(name, cognome, eta, nazione, genere, corrente_artistica, 
                      professione, colori_preferiti, generi_musicali, cerca_nei_capi, 
                      marchi_preferiti, competenza_moda, interesse_moda):
    global CURRENT_USER_ID, CURRENT_USER_GENDER, next_id, dataset, GENERATED_TABS
    error_messages = []
    
    # Validazione campi obbligatori
    required_fields = {
        "Nome": name,
        "Cognome": cognome,
        "Età": eta,
        "Nazione": nazione,
        "Genere": genere,
        "Corrente Artistica Preferita": corrente_artistica,
        "Professione": professione,
        "Colori Preferiti": colori_preferiti,
        "Generi Musicali Preferiti": generi_musicali,
        "Cosa cerchi nei capi": cerca_nei_capi,
        "Marchi Preferiti": marchi_preferiti,
        "Competenza in moda": competenza_moda,
        "Interesse in moda": interesse_moda
    }
    
    # Controllo campi obbligatori
    for field, value in required_fields.items():
        if not value or (isinstance(value, list) and len(value) == 0):
            error_messages.append(f"Errore: Il campo '{field}' è obbligatorio")
    
    # Validazioni lunghezza selezioni
    validation_rules = {
        "Colori Preferiti": (colori_preferiti, 1, 2),
        "Generi Musicali Preferiti": (generi_musicali, 1, 2),
        "Cosa cerchi nei capi": (cerca_nei_capi, 1, 3),
        "Marchi Preferiti": (marchi_preferiti, 1, 2)
    }
    
    for field_name, (values, min_len, max_len) in validation_rules.items():
        if len(values) < min_len:
            error_messages.append(f"Errore: Seleziona almeno {min_len} opzione per {field_name}")
        elif len(values) > max_len:
            error_messages.append(f"Errore: Puoi selezionare al massimo {max_len} opzioni per {field_name}")
    
    if error_messages:
        return "\n".join(error_messages)
    
    # Creazione nuovo utente con ID
    new_entry = {
        "idUtente": next_id,
        "nome": name.strip(), 
        "cognome": cognome.strip(),
        "eta": int(eta),
        "nazione": nazione.strip(),
        "genere": genere,
        "corrente_artistica_preferita": corrente_artistica,
        "professione": professione.strip(),
        "colori_preferiti": ", ".join(colori_preferiti),
        "generi_musicali_preferiti": ", ".join(generi_musicali),
        "cosa_cerchi_nei_capi": ", ".join(cerca_nei_capi),
        "marchi_preferiti": ", ".join(marchi_preferiti),
        "competenza_moda": int(competenza_moda),
        "interesse_moda": int(interesse_moda)
    }
    
    # Memorizzazione dell'id utente corrente
    CURRENT_USER_ID = next_id
    CURRENT_USER_GENDER = genere # e del genere corrente

    # Resetta le generazioni per il nuovo utente
    GENERATED_TABS = {}

    # Salvataggio dati
    dataset = pd.concat([dataset, pd.DataFrame([new_entry])], ignore_index=True)
    dataset.to_csv(data_file, index=False, encoding='utf-8-sig')
    
    # Incrementa ID per prossimo utente
    next_id += 1
    
    # Stringa (ITA) Utente Globale per Essere Passata a Gemini
    # Stringa da rivedere togliendo le cose che sono superflue (es. salario, stato civile)
    descrizione_utente_ita = (
        "Genere: " + genere + "\n" +
        f"Età: {eta} \n" +
        "Nazione: " + nazione + "\n" +
        "Professione: " + professione + "\n" +
        "Corrente artistica preferita: " + corrente_artistica + "\n" +
        f"{'Marchi' if len(marchi_preferiti) > 1 else 'Marchio'} Preferit{'i' if len(marchi_preferiti) > 1 else 'o'}: {', '.join(marchi_preferiti)}" + "\n"+
        f"{'Generi' if len(generi_musicali) > 1 else 'Genere'} Musical{'i' if len(generi_musicali) > 1 else 'e'} Preferit{'i' if len(generi_musicali) > 1 else 'o'}: {', '.join(generi_musicali).lower()}" + "\n"+
        f"Cosa Ricerca nei Capi che Indossa: {', '.join(cerca_nei_capi).lower()}" + "\n"+
        f"{'Colori' if len(colori_preferiti) > 1 else 'Colore'} Preferit{'i' if len(colori_preferiti) > 1 else 'o'}: {', '.join(colori_preferiti).lower()}."
    )
        
    # Traduzione in Inglese (ENG) per agevolare il lavoro di Gemini
    from deep_translator import GoogleTranslator
    global descrizione_utente_eng
    descrizione_utente_eng = GoogleTranslator(source="it", target="en").translate(descrizione_utente_ita)

    # Messaggio di conferma
    return f"✅ Registrazione completata per {name} {cognome}!\n"


def clear_fields():
    return (
        gr.update(value=""), gr.update(value=""), gr.update(value=18), gr.update(value=""), gr.update(value=None),
        gr.update(value=None), gr.update(value=""), gr.update(value=[]), gr.update(value=[]), 
        gr.update(value=[]), gr.update(value=[]), gr.update(value=None), gr.update(value=None), 
        gr.update(value="")
    )

# FUNZIONE DI GESTIONE QUESTIONARIO
def handle_questionnaire(tab_number, generated_image_path, questions, *answers):
    global questionnaire_data, next_questionnaire_id, CURRENT_USER_ID, DISPLAY_ORDERS
    
    if not CURRENT_USER_ID:
        return "❌ Effettua prima la registrazione!"
    
    # Controlla se l'immagine è stata generata
    if not generated_image_path or generated_image_path == "":
        return f"❌ Genera prima l'immagine nella Tab {tab_number} prima di inviare il questionario!"

    # Controlla che tutte le domande siano state risposte
    for ans in answers:
        if ans is None or ans == "":
            return "❌ Completa tutte le domande prima di inviare!"
    
    # Recupera l'ordine di visualizzazione per questo tab
    display_order = DISPLAY_ORDERS.get(tab_number, 1)

    # Converti path generated -> ID
    df_generated = pd.read_csv(IMMAGINI_GENERATE_FILE)
    generated_row = df_generated[df_generated['path_immagine_generata'] == generated_image_path]
    if generated_row.empty:
        return "❌ Errore: Immagine generata non trovata!"
    generated_id = generated_row['idGenerazione'].values[0]

    # +++ INIZIO CONTROLLO DUPPLICATI +++
    # Carica il dataset aggiornato per evitare cache obsoleta
    try:
        current_questionnaire_data = pd.read_csv(questionnaire_file)
    except FileNotFoundError:
        current_questionnaire_data = pd.DataFrame()

    existing_entry = current_questionnaire_data[
        (current_questionnaire_data["idUtente"] == CURRENT_USER_ID) &
        (current_questionnaire_data["id_immagine_generata"] == generated_id)
    ]

    if not existing_entry.empty:
        return "❌ Hai già inviato questo questionario per questa immagine!"
    # +++ FINE CONTROLLO DUPPLICATI +++

    # Mappa le risposte ai path corretti
    processed_answers = []
    for i, ans in enumerate(answers):
        if i < 5:
            if ans == "Sinistra":
                processed = "Baseline" if display_order == 1 else "Generated"
            elif ans == "Destra":
                processed = "Generated" if display_order == 1 else "Baseline"
            else:
                processed = "Indifferente"
        else:
            processed = ans
        processed_answers.append(processed)

    # Crea nuovo record
    new_entry = {
        "idQuestionario": next_questionnaire_id,
        "idUtente": CURRENT_USER_ID,
        "id_immagine_generata": generated_id,
        "id_set_domande": QUESTION_SET_ID,
        **{f"domanda{i+1}": a for i, a in enumerate(processed_answers)}
    }
    
    # Aggiorna dataset
    questionnaire_data = pd.concat([questionnaire_data, pd.DataFrame([new_entry])], ignore_index=True)
    questionnaire_data.to_csv(questionnaire_file, index=False, encoding='utf-8-sig')
    
    # Incrementa l'ID per il prossimo questionario
    next_questionnaire_id += 1

    return "✅ Valutazione salvata correttamente!"

# Tab 1: Inserimento dati Utente
with gr.Blocks(theme=gr.themes.Soft()) as registration_tab:
    gr.Markdown("# Form di Inserimento Dati Utente")
    gr.Markdown("*I campi contrassegnati con * sono obbligatori*", elem_id="note")
    
    # Sezione informazioni base
    with gr.Row():
        name = gr.Textbox(label="Nome*", placeholder="Inserisci il tuo nome")
        cognome = gr.Textbox(label="Cognome*", placeholder="Inserisci il tuo cognome")
    with gr.Row():
        eta = gr.Slider(label="Età*", minimum=18, maximum=99, step=1, value=18)
        nazione = gr.Textbox(label="Nazione*", placeholder="Inserisci la tua nazione")
        genere = gr.Radio(label="Genere*", choices=["Uomo", "Donna"])
    
    # Sezione lavoro
    professione = gr.Textbox(label="Professione*", placeholder="Inserisci la tua professione")

    # Sezione preferenze artistiche
    corrente_artistica = gr.Dropdown(
        label="Corrente Artistica Preferita*",
        choices=sorted([
            "Avant-Garde", "Tradizionalismo", "Surrealismo", "Futurismo", "Minimalismo", "Barocco",
            "Decostruttivismo", "Pop-Art", "Neo-Classicismo", "Gothic", "Post-Modernismo",
            "Art Déco", "Romanticismo", "Tribalismo", "Eco-Fashion", "Streetwear"
        ])
    )
    
    # Preferenze personali
    with gr.Row():
        colori_preferiti = gr.CheckboxGroup(
            label="Colori Preferiti* (max 2)",
            choices=sorted([
                "Nero", "Bianco", "Rosso", "Verde", "Giallo", "Arancione", "Blu", "Rosa",
                "Celeste", "Magenta", "Marrone", "Bordeaux", "Turchese", "Viola"
            ]),
            scale=1
        )
    with gr.Row():
        generi_musicali = gr.CheckboxGroup(
            label="Generi Musicali Preferiti* (max 2)",
            choices=sorted(["Rock", "Rap", "RnB", "Pop", "House", "Techno", "Metal", "Jazz", "Country", "Blues", "Classica"]),
            scale=1
        )
    with gr.Row():
        cerca_nei_capi = gr.CheckboxGroup(
            label="Cosa cerchi nei capi che indossi?* (max 3)",
            choices=sorted(["Sicurezza", "Eleganza", "Audacia", "Originalità", "Comodità", 
                           "Versatilità", "Libertà", "Seduttività", "Misteriosità", "Tradizionalità"]),
            scale=1
        )
    with gr.Row():
        marchi_preferiti = gr.CheckboxGroup(
            label="Marchi Preferiti* (max 2)",
            choices=sorted([
                "Rick Owens", "Gucci", "Yves Saint Laurent", "Miu Miu", "Coperni",
                "Stella McCartney", "Isabel Marant", "Junya Watanabe", "Dior",
                "André Courrèges", "Jil Sander", "Ralph Lauren", "Bottega Veneta",
                "Giorgio Armani", "Louis Vuitton", "Versace"
            ]),
            scale=1
        )
    with gr.Row():
        gr.Markdown("1 = Molto Poco, 2 = Poco, 3 = Neutro, 4 = Abbastanza, 5 = Molto")

    with gr.Row():
        competenza_moda = gr.Radio(
            label="Quanto ti ritieni competente in ambito moda?*",
            choices=[1, 2, 3, 4, 5],
            type="value"
        )
        interesse_moda = gr.Radio(
            label="Quanto ti ritieni interessato all'ambito moda?*",
            choices=[1, 2, 3, 4, 5],
            type="value"
        )
    
    # Pulsanti finali
    with gr.Row():
        submit_btn = gr.Button("Registrati")
        clear_btn = gr.Button("Pulisci")
    output = gr.Textbox(label="Risultato")
    
    submit_btn.click(
        handle_registration, 
        inputs=[name, cognome, eta, nazione, genere, corrente_artistica, professione, 
            colori_preferiti, generi_musicali, cerca_nei_capi, marchi_preferiti,
            competenza_moda, interesse_moda],
        outputs=output
    )
    clear_btn.click(clear_fields, inputs=[], outputs=[
        name, cognome, eta, nazione, genere, corrente_artistica, 
        professione, colori_preferiti, generi_musicali, 
        cerca_nei_capi, marchi_preferiti, competenza_moda, interesse_moda, output
    ])

# Tab 2.*: Generazione Immagini
# Funzione per gestire le immagini generate
def save_generation_data(baseline_image_path, prompt_text_to_image, generated_image_path):
    global next_generation_id, CURRENT_USER_ID
    import datetime
    import os

    # Carica il dataset delle baseline
    df_baseline = pd.read_csv(IMMAGINI_BASELINE_FILE)
    
    # Trova l'ID corrispondente al path
    baseline_row = df_baseline[df_baseline['path_immagine'] == baseline_image_path]
    if baseline_row.empty:
        raise ValueError(f"Path baseline {baseline_image_path} non trovato nel database")

    id_immagine_baseline = baseline_row['idImmagine'].values[0]

    # Crea il nuovo record
    new_entry = {
        "idGenerazione": next_generation_id,
        "id_immagine_baseline": id_immagine_baseline,
        "prompt_text_to_image": prompt_text_to_image,
        "data_ora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "path_immagine_generata": generated_image_path
    }
    
    # Salvataggio
    try:
        df = pd.read_csv(IMMAGINI_GENERATE_FILE) if os.path.exists(IMMAGINI_GENERATE_FILE) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(IMMAGINI_GENERATE_FILE, index=False, encoding='utf-8-sig')
        next_generation_id += 1
    except Exception as e:
        if os.path.exists(generated_image_path):
            os.remove(generated_image_path)
        raise
    

# Gestione tab in base al genere
def get_baseline_image(tab_number):
    if not CURRENT_USER_GENDER:
        raise gr.Error("Effettua prima la registrazione!")
    
    try:
        df_baseline = pd.read_csv(IMMAGINI_BASELINE_FILE)
        expected_path = BASELINE_IMAGES[CURRENT_USER_GENDER][tab_number]
        
        # Cerca il path esatto nel database
        baseline_row = df_baseline[
            (df_baseline['genere_del_capo'] == CURRENT_USER_GENDER) &
            (df_baseline['path_immagine'] == expected_path)
        ]
        
        if not baseline_row.empty:
            return baseline_row['path_immagine'].values[0]
        else:
            raise gr.Error(f"Immagine baseline per {CURRENT_USER_GENDER} tab {tab_number} non trovata nel database")
            
    except KeyError as e:
        raise gr.Error(f"Configurazione baseline mancante: {str(e)}")
    except Exception as e:
        raise gr.Error(f"Errore nel recupero baseline: {str(e)}")

def get_baseline_from_generated(generated_id):
    df_generated = pd.read_csv(IMMAGINI_GENERATE_FILE)
    generated_row = df_generated[df_generated['idGenerazione'] == generated_id]
    
    if not generated_row.empty:
        baseline_id = generated_row['id_immagine_baseline'].values[0]
        df_baseline = pd.read_csv(IMMAGINI_BASELINE_FILE)
        return df_baseline[df_baseline['idImmagine'] == baseline_id]['path_immagine'].values[0]
    return None

def save_generated_image(tab_number):
    global next_generation_id, CURRENT_USER_ID, CURRENT_USER_GENDER, DISPLAY_ORDERS, GENERATED_TABS

    # Controlla se il tab è già stato generato
    if GENERATED_TABS.get(tab_number, False):
        raise gr.Error("Hai già generato un'immagine per questa tab. Procedi con la valutazione!")

    try:
        if not CURRENT_USER_ID:
            raise gr.Error("Effettua prima la registrazione!")
        
        # Controllo tab precedenti compilate per tab > 1
        if tab_number > 1:
            try:
                # Ottieni la baseline del tab precedente
                prev_baseline_path = get_baseline_image(tab_number - 1)
                
                # Cerca l'ID baseline corrispondente
                df_baseline = pd.read_csv(IMMAGINI_BASELINE_FILE)
                prev_baseline_row = df_baseline[df_baseline['path_immagine'] == prev_baseline_path]
                if prev_baseline_row.empty:
                    raise gr.Error("Baseline precedente non trovata")
                prev_baseline_id = prev_baseline_row['idImmagine'].values[0]

                # Recupera TUTTE le generazioni per questa baseline
                df_generated = pd.read_csv(IMMAGINI_GENERATE_FILE)
                prev_generations = df_generated[df_generated['id_immagine_baseline'] == prev_baseline_id]
                
                if prev_generations.empty:
                    raise gr.Error(f"Genera prima l'immagine nella Tab {tab_number - 1}!")

                # Cerca nei questionari se esiste una risposta per queste generazioni
                df_questionario = pd.read_csv(questionnaire_file)
                prev_completed = df_questionario[
                    (df_questionario['id_immagine_generata'].isin(prev_generations['idGenerazione'])) &
                    (df_questionario['idUtente'] == CURRENT_USER_ID)
                ]
                
                if prev_completed.empty:
                    raise gr.Error(f"Completa il questionario nella Tab {tab_number - 1}!")

            except Exception as e:
                raise gr.Error(f"Errore controllo tab precedente: {str(e)}")

        # Generazione Immagine
        baseline_path = get_baseline_image(tab_number)
        
        prompt_text_to_image = generate_fashion_prompt(
            image_path=baseline_path,
            user_description=descrizione_utente_eng
        )
        
        import random
        display_order = random.randint(1, 2)
        DISPLAY_ORDERS[tab_number] = display_order

        generated_path = generate_adv_image(prompt_text_to_image, next_generation_id)
        
        if display_order == 1:
            left_image, right_image = baseline_path, generated_path
        else:
            left_image, right_image = generated_path, baseline_path

        import os
        if not os.path.exists(generated_path):
            raise FileNotFoundError(f"Immagine generata non trovata: {generated_path}")

        save_generation_data(
            baseline_path,
            prompt_text_to_image,
            generated_path
        )

        # Dopo il salvataggio riuscito, segna il tab come generato
        GENERATED_TABS[tab_number] = True
        
        return left_image, right_image, generated_path
        
    except Exception as e:
        print(f"RIPROVA! Errore durante la generazione: {str(e)}")
        raise gr.Error(f"RIPROVA! Errore durante la generazione: {str(e)}")

def disable_generate():
            return gr.update(interactive=False)

# Funzione per creare le tab immagine con questionario integrato
def create_image_tab(tab_number):
    with gr.Blocks(theme=gr.themes.Soft()) as tab:
        gr.Markdown(f"# Immagine {tab_number}")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                img_left = gr.Image(label="Immagine Sinistra", interactive=False, height=600, width=600)
            with gr.Column(scale=1):
                img_right = gr.Image(label="Immagine Destra", interactive=False, height=600, width=600)
        
        generate_btn = gr.Button("Genera")
        generated_image_path = gr.State(value="")

        generate_btn.click(
            fn=lambda tn=tab_number: save_generated_image(tn),
            inputs=[],
            outputs=[img_left, img_right, generated_image_path],
            show_progress=True
        ).success(
            fn=disable_generate,
            inputs=[],
            outputs=[generate_btn]
        )

        # Sezione Questionario
        gr.Markdown("## Valutazione Immagini")
        questions = load_questions(questions_file, QUESTION_SET_ID)
        inputs = []
        
        # Genera i componenti del questionario
        likert_scale = [
        (1, "1 - Molto Poco"),
        (2, "2 - Poco"), 
        (3, "3 - Neutro"),
        (4, "4 - Abbastanza"),
        (5, "5 - Molto")
        ]

        # Messaggio per l'utente (cosa fare)
        with gr.Column(elem_id="compact_markdown"):
            gr.Markdown(
                "Rispondi alle seguenti domande:"
                "<ul>"
                "<li>Per le domande a risposta multipla, scegli una delle seguenti opzioni: <strong>Destra, Sinistra o Indifferente</strong>.</li>"
                "<li>Per le domande con valutazione numerica, utilizza la seguente scala Likert:<br>"
                "1 = Molto Poco, 2 = Poco, 3 = Neutro, 4 = Abbastanza, 5 = Molto</li>"
                "</ul>",
                elem_id="header_instructions"
            )
        
        for i, q in enumerate(questions):
            if i < 5:  # Prime 5 domande
                inputs.append(gr.Radio(
                    label=q,
                    choices=["Sinistra", "Destra", "Indifferente"],
                    type="value",
                    interactive=True
                ))
            else:
                inputs.append(gr.Radio(
                    label=q,
                    choices=likert_scale,
                    type="value",
                    interactive=True
                ))
        
        submit_btn = gr.Button("Invia Valutazione")
        output = gr.Textbox()

        # Validazione dinamica
        def validate_answers(*answers):
            all_answered = all(a not in [None, "", 0] for a in answers)
            return gr.update(interactive=all_answered)
        
        for component in inputs:
            component.change(
                fn=validate_answers,
                inputs=inputs,
                outputs=submit_btn
            )

        submit_btn.click(
            handle_questionnaire,
            [gr.State(tab_number), generated_image_path, gr.State(questions)] + inputs,  # Passa la variabile locale
            output
        )
    
    return tab

image_tabs = [
    create_image_tab(1),
    create_image_tab(2),
    create_image_tab(3),
    create_image_tab(4)
]

# Interfaccia principale con tab
demo = gr.TabbedInterface(
    [registration_tab] + image_tabs,
    ["Registrazione", "Immagine 1", "Immagine 2", "Immagine 3", "Immagine 4"]
)

if __name__ == "__main__":
    demo.launch(server_port=7860) #, share=True (per mettere la pagina online)