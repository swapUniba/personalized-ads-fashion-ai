import sqlite3
import csv
import numpy as np
import pandas as pd
from pathlib import Path
# Utili per grafici
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns

DATABASE_PATH = "fashion_database.db"
CSV_FOLDER = Path(".")  # da modificare se i CSV sono in un'altra cartella
ID_SET = 1

css = """
.gr-row {
    margin: 10px 0 !important;
}

.plot-container {
    height: 300px !important;
    width: 95% !important;
    margin: 5px auto !important;
}

.question-row {
    border-bottom: 1px solid #eee;
    padding: 10px 0;
}

.question-text p {
    font-size: 14px !important;  /* Aumentato da 12px */
    color: #444 !important;       /* Colore più scuro */
    margin-top: -8px !important;
    margin-bottom: 12px !important;
    line-height: 1.4 !important;
}

/* Aggiungi stile per la domanda 6 */
.likert-text p {
    font-size: 14px !important;
    color: #444 !important;
    margin: 10px 0 15px 0 !important;
}
"""

def create_tables(cursor):
    # Crea le tabelle se non esistono già
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS registrazioni (
        idUtente INTEGER PRIMARY KEY,
        nome TEXT,
        cognome TEXT,
        eta INTEGER,
        nazione TEXT,
        genere TEXT,
        corrente_artistica_preferita TEXT,
        professione TEXT,
        colori_preferiti TEXT,
        generi_musicali_preferiti TEXT,
        cosa_cerchi_nei_capi TEXT,
        marchi_preferiti TEXT,
        competenza_moda TEXT,
        interesse_moda TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questionario (
        idQuestionario INTEGER PRIMARY KEY,
        idUtente INTEGER REFERENCES registrazioni(idUtente),
        id_immagine_generata INTEGER UNIQUE REFERENCES immagini_generate(idGenerazione),
        id_set_domande INTEGER REFERENCES domande(id_set),
        domanda1 TEXT,
        domanda2 TEXT,
        domanda3 TEXT,
        domanda4 TEXT,
        domanda5 TEXT,
        domanda6 TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS immagini_generate (
        idGenerazione INTEGER PRIMARY KEY,
        id_immagine_baseline INTEGER REFERENCES immagini_baseline(idImmagine),
        prompt_text_to_image TEXT,
        data_ora TEXT,
        path_immagine_generata TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS domande (
        id_set INTEGER PRIMARY KEY,
        domanda1 TEXT,
        domanda2 TEXT,
        domanda3 TEXT,
        domanda4 TEXT,
        domanda5 TEXT,
        domanda6 TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS immagini_baseline (
        idImmagine INTEGER PRIMARY KEY,
        genere_del_capo TEXT,
        path_immagine TEXT
    )''')

# Funzione per preferenze e grafici
def analyze_preferences():
    conn = get_db_connection()
    try:
        figures = []
        domande_testi = {}

        # Recupera i testi delle domande
        query_domande = f'''SELECT * FROM domande WHERE id_set = {ID_SET}'''  # Usiamo il primo set
        df_domande = pd.read_sql_query(query_domande, conn)
        
        # Crea un dizionario con i testi
        if not df_domande.empty:
            domande_testi = {
                1: df_domande['domanda1'].iloc[0],
                2: df_domande['domanda2'].iloc[0],
                3: df_domande['domanda3'].iloc[0],
                4: df_domande['domanda4'].iloc[0],
                5: df_domande['domanda5'].iloc[0],
                6: df_domande['domanda6'].iloc[0]
            }
        
        # Analisi per domande 1-5
        for domanda in range(1, 6):
            query = f'''
            SELECT 
                q.domanda{domanda} as risposta,
                COUNT(*) as totale,
                r.genere
            FROM questionario q
            JOIN registrazioni r ON q.idUtente = r.idUtente
            JOIN immagini_generate ig ON q.id_immagine_generata = ig.idGenerazione
            GROUP BY q.domanda{domanda}, r.genere
            '''
            
            df = pd.read_sql_query(query, conn)
            
            fig = px.bar(df,
                        x='risposta',
                        y='totale',
                        color='genere',
                        title=f'Domanda {domanda} - Distribuzione Risposte',
                        labels={'totale': 'Numero Risposte', 'risposta': 'Opzione'},
                        barmode='group')
            
            fig.update_layout(
                height=300,
                width=500,
                margin=dict(l=20, r=20, t=40, b=20),
                title_font_size=14
            )
            figures.append(fig)
        
        # Analisi per domanda 6 (Likert)
        query_likert = '''
        SELECT 
            q.domanda6 as valutazione,
            COUNT(*) as totale,
            r.genere
        FROM questionario q
        JOIN registrazioni r ON q.idUtente = r.idUtente
        JOIN immagini_generate ig ON q.id_immagine_generata = ig.idGenerazione
        GROUP BY q.domanda6, r.genere
        '''
        
        df_likert = pd.read_sql_query(query_likert, conn)
        
        # Grafico a torta
        fig_pie = px.pie(df_likert,
                        values='totale',
                        names='valutazione',
                        title='Distribuzione Valutazioni (Likert)')
        
        # Grafico a barre per genere
        fig_bar = px.bar(df_likert,
                        x='valutazione',
                        y='totale',
                        color='genere',
                        title='Valutazioni per Genere (Likert)',
                        barmode='group')

        fig_pie.update_layout(height=300, width=400)
        fig_bar.update_layout(height=300, width=600)

        figures.extend([fig_pie, fig_bar])
        
        return figures, domande_testi
    
    except Exception as e:
        print(f"Errore nell'analisi: {e}")
        return [None] * 7  # Ritorna 7 elementi vuoti
    finally:
        conn.close()

def load_data(cursor):
    # Funzione generica per il caricamento CSV
    def load_csv(table, filename, converter=None):
        file_path = CSV_FOLDER / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                if converter:
                    try:
                        row = converter(row)
                    except Exception as e:
                        print(f"Errore conversione riga {row} in {table}: {e}")
                        continue
                placeholders = ','.join('?' * len(row))
                cursor.execute(f'INSERT OR IGNORE INTO {table} VALUES ({placeholders})', row)

    # Caricamento dati con conversione tipi
    load_csv('registrazioni', 'registrazioni.csv',
        lambda r: [
            int(r[0]), r[1], r[2], int(r[3]), r[4], r[5], r[6], r[7],
            r[8], r[9], r[10], r[11], int(r[12]), int(r[13]) 
        ])
    load_csv('questionario', 'questionario.csv', 
         lambda r: [int(r[0]), int(r[1]), int(r[2])] + r[3:10])
    
    load_csv('immagini_generate', 'immagini_generate.csv', 
             lambda r: [int(r[0]), int(r[1])] + r[2:5])
    
    load_csv('domande', 'domande.csv')
    load_csv('immagini_baseline', 'immagini_baseline.csv')

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)

def init_db():
    # Elimina il database se esiste e lo ricrea
    #if Path(DATABASE_PATH).exists():
        #Path(DATABASE_PATH).unlink()
    # Perchè? Al momento il database viene creato e ad ogni avvio di questo script
    # vengono AGGIUNTE le cose nuove presenti nei file "csv" ma non vengono inserite 
    # le MODIFICHE e le ELIMINAZIONI.
    # -> NOTA che il sistema attuale però NON permette le eliminazioni o le modifiche 
    # quindi non c'è problema ma se dovesse essere implementata questa funzionalità, 
    # allora bisognerebbe scommentare le due righe sopra che ad ogni esecuzione tolgono
    # e ricreano il database. Al contrario, se questo dovesse essere troppo pesante,
    # bisognerebbe prevedere una costruzione "incrementale" del database.

    conn = get_db_connection()
    cursor = conn.cursor()
    create_tables(cursor)
    load_data(cursor)
    conn.commit()
    conn.close()

def run_query(query):
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn)
        
        # Inizio gestione nome colonne duplicate
        # Gestione colonne duplicate
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            # Trova gli indici delle colonne duplicate
            dup_indices = cols[cols == dup].index.tolist()
            # Rinomina con suffisso _1, _2, ecc., mantenendo la prima colonna intatta
            for i, idx in enumerate(dup_indices):
                if i > 0:  # Lascia la prima occorrenza come originale
                    cols[idx] = f"{dup}_{i}"
        
        df.columns = cols  # Applica i nuovi nomi
        # Fine gestione nome colonne duplicate
        
        return df
    except Exception as e:
        return str(e)
    finally:
        conn.close()

def create_interface():
    # Interfaccia Gradio
    import gradio as gr

    with gr.Blocks(title="Fashion Analytics Dashboard", css=css) as demo:
        gr.Markdown("# Fashion Analytics Dashboard")
        
        with gr.Tab("🔍 SQL Query"):
            gr.Markdown("### Esegui query personalizzate")
            sql_input = gr.Textbox(lines=10, placeholder="Inserisci la tua query SQL...")
            run_btn = gr.Button("Esegui", variant="primary")
            sql_output = gr.Dataframe(label="Risultati", wrap=True)
            
            run_btn.click(
                fn=run_query,
                inputs=sql_input,
                outputs=sql_output
            )

        with gr.Tab("📊 Analisi Predefinite"):
            gr.Markdown("### Report preconfigurati")
            
            with gr.Row():
                age_analysis = gr.Button("Distribuzione per Età")
                country_analysis = gr.Button("Utenti per Nazione")
                style_analysis = gr.Button("Preferenze Stilistiche")

            with gr.Row():  # Aggiunto nuovo row
                competence_analysis = gr.Button("Competenza in Moda")
                interest_analysis = gr.Button("Interesse in Moda")

            analysis_output = gr.Dataframe(label="Risultati", wrap=True)

            def predefined_query(query_type):
                queries = {
                    "age": "SELECT eta, COUNT(*) as Occorrenze FROM registrazioni GROUP BY eta ORDER BY eta",
                    "country": "SELECT nazione, COUNT(*) as Occorrenze FROM registrazioni GROUP BY nazione ORDER BY Occorrenze DESC",
                    "style": '''SELECT corrente_artistica_preferita, COUNT(*) as Occorrenze 
                                FROM registrazioni GROUP BY corrente_artistica_preferita ORDER BY Occorrenze DESC''',
                    "competenza": "SELECT competenza_moda AS 'Valutazione Competenza Moda', COUNT(*) as Occorrenze FROM registrazioni GROUP BY competenza_moda ORDER BY competenza_moda",
                    "interesse": "SELECT interesse_moda AS 'Valutazione Interesse Moda', COUNT(*) as Occorrenze FROM registrazioni GROUP BY interesse_moda ORDER BY interesse_moda"
                }
                return run_query(queries[query_type])

            age_analysis.click(lambda: predefined_query("age"), outputs=analysis_output)
            country_analysis.click(lambda: predefined_query("country"), outputs=analysis_output)
            style_analysis.click(lambda: predefined_query("style"), outputs=analysis_output)
            competence_analysis.click(lambda: predefined_query("competenza"), outputs=analysis_output)
            interest_analysis.click(lambda: predefined_query("interesse"), outputs=analysis_output)
            
        with gr.Tab("📈 Analisi Dettagliata"):
            gr.Markdown("""
                        #### Di seguito ci sono due sezioni:

                        - **Analisi delle singole domande** con annessi grafici di valutazione  
                        - **Analisi delle performance delle singole immagini di baseline** con grafici di valutazione basati sui questionari degli utenti  
                        """)
            gr.Markdown("---")

            gr.Markdown("## SEZ. 1 - Analisi per Domanda e Valutazioni")
            update_btn = gr.Button("Aggiorna Analisi", variant="primary")
            
            # Memorizzare i testi delle domande
            domande_state = gr.State({})

            plot_components = []
            text_components = []
            
            with gr.Column():
                for i in range(0, 4, 2):
                    with gr.Row(variant="panel"):
                        for j in range(2):
                            domanda_num = i + j + 1
                            with gr.Column():
                                gr.Markdown(f"**Domanda {domanda_num}**", elem_classes=["question-header"])
                                md_text = gr.Markdown("", elem_classes=["question-text"])
                                plot = gr.Plot(elem_classes=["plot-container"])
                                text_components.append(md_text)
                                plot_components.append(plot)
                
                # Domanda 5
                with gr.Row(variant="panel"):
                    with gr.Column():
                        gr.Markdown("**Domanda 5**", elem_classes=["question-header"])
                        md_text5 = gr.Markdown("", elem_classes=["question-text"])
                        plot5 = gr.Plot(elem_classes=["plot-container"])
                        text_components.append(md_text5)
                        plot_components.append(plot5)
            
            # Sezione Likert
            gr.Markdown("### Valutazioni Domanda 6", elem_classes=["likert-title"])
            md_text6 = gr.Markdown("", elem_classes=["likert-text"])
            with gr.Row():
                likert_pie = gr.Plot(elem_classes=["plot-container"])
                likert_genere = gr.Plot(elem_classes=["plot-container"])
                plot_components.extend([likert_pie, likert_genere])
                text_components.append(md_text6)

            # Nuova sezione per le immagini baseline
            gr.Markdown("---")
            gr.Markdown("## SEZ. 2 - Analisi Performances Immagini Baseline")
            
            # Recupera le immagini baseline dal database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM immagini_baseline")
            baseline_images = cursor.fetchall()

            for img in baseline_images:
                with gr.Row(variant="panel"):
                    with gr.Column(scale=1):
                        gr.Image(value=img[2], label=f"Baseline {img[0]} - {img[1]}", height=300)
                    
                    with gr.Column(scale=2):
                        # Query per ottenere i dati reali
                        query = f'''
                            SELECT 
                                'Baseline' as scelta,
                                SUM(
                                    (CASE WHEN TRIM(q.domanda1) = 'Baseline' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda2) = 'Baseline' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda3) = 'Baseline' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda4) = 'Baseline' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda5) = 'Baseline' THEN 1 ELSE 0 END)
                                ) as totale
                            FROM questionario q
                            JOIN immagini_generate ig ON q.id_immagine_generata = ig.idGenerazione
                            WHERE ig.id_immagine_baseline = {img[0]}
                            AND q.id_set_domande = {ID_SET}

                            UNION ALL

                            SELECT 
                                'Generated' as scelta,
                                SUM(
                                    (CASE WHEN TRIM(q.domanda1) = 'Generated' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda2) = 'Generated' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda3) = 'Generated' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda4) = 'Generated' THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda5) = 'Generated' THEN 1 ELSE 0 END)
                                ) as totale
                            FROM questionario q
                            JOIN immagini_generate ig ON q.id_immagine_generata = ig.idGenerazione
                            WHERE ig.id_immagine_baseline = {img[0]}
                            AND q.id_set_domande = {ID_SET}

                            UNION ALL

                            SELECT 
                                'Indifferente' as scelta,
                                SUM(
                                    (CASE WHEN TRIM(q.domanda1) NOT IN ('Baseline', 'Generated') THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda2) NOT IN ('Baseline', 'Generated') THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda3) NOT IN ('Baseline', 'Generated') THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda4) NOT IN ('Baseline', 'Generated') THEN 1 ELSE 0 END) +
                                    (CASE WHEN TRIM(q.domanda5) NOT IN ('Baseline', 'Generated') THEN 1 ELSE 0 END)
                                ) as totale
                            FROM questionario q
                            JOIN immagini_generate ig ON q.id_immagine_generata = ig.idGenerazione
                            WHERE ig.id_immagine_baseline = {img[0]}
                            AND q.id_set_domande = {ID_SET}
                        '''
                        
                        df = pd.read_sql_query(query, conn)
                        
                        # Processa i dati per il grafico
                        categories = ['Baseline', 'Generated', 'Indifferente']

                        if not df.empty:
                            # Crea un dataframe completo con tutte le categorie
                            final_df = df.set_index('scelta').reindex(categories, fill_value=0).reset_index()
                            
                            # Converti i valori nulli a 0 e poi a interi
                            final_df['totale'] = pd.to_numeric(final_df['totale'], errors='coerce').fillna(0).astype(int)
                        else:
                            final_df = pd.DataFrame({
                                'scelta': categories,
                                'totale': [0, 0, 0]
                            })

                        # Calcola la percentuale
                        total = final_df['totale'].sum()
                        final_df['percentuale'] = (final_df['totale'] / total * 100).round(1) if total > 0 else 0

                        # Crea il grafico
                        fig = px.pie(
                            final_df,
                            names='scelta',
                            values='totale',
                            color='scelta',
                            color_discrete_map={
                                'Baseline': '#EE553D  ',
                                'Generated': '#626DF9  ',
                                'Indifferente': '#05CA94  '
                            },
                            title=f"Scelte per {img[1]} (ID: {img[0]})",
                            hover_data=['percentuale'],
                            height = 300, 
                            width = 700
                        )

                        # Personalizza l'hover
                        fig.update_traces(
                            hovertemplate="<br>".join([
                                "Scelta: %{label}",
                                "Risposte totali: %{value}",
                                "Percentuale: %{customdata[0]}%"
                            ])
                        )
                        
                        gr.Plot(fig)
            
            conn.close()

            # Callback
            def update_analysis():
                figures, domande_testi = analyze_preferences()
                updates = []
                
                # Testi per domande 1-5
                for i in range(5):
                    text = domande_testi.get(i+1, "Testo della domanda non disponibile")
                    updates.append(f"<div style='margin-bottom: 10px'>{text}</div>")  # margine
                
                # Testo per domanda 6
                text6 = domande_testi.get(6, "Testo della domanda 6 non disponibile")
                updates.append(f"<div style='margin-bottom: 15px'>{text6}</div>")

                return figures + updates

            update_btn.click(
                fn=update_analysis,
                outputs=plot_components + text_components
            )

        # Tab analisi performance baseline
        with gr.Tab("🖼️ Performance Baseline"):
            gr.Markdown("## Efficacia Immagini Baseline")
            gr.Markdown("""
            Analizza quanto efficacemente ogni immagine baseline genera preferenze rispetto alle sue varianti generate
            - **Metrica**: % preferenze per immagini generate rispetto alla baseline corrispondente
            """)
            
            update_baseline_btn = gr.Button("Aggiorna Analisi", variant="primary")
            baseline_output = gr.DataFrame(label="Risultati Performance", wrap=True)
            baseline_plot = gr.Plot()

            def analyze_baseline_performance():
                conn = get_db_connection()
                try:
                    # Query per ottenere tutte le baseline con informazioni complete
                    query = '''
                    SELECT 
                        ib.idImmagine,
                        ib.genere_del_capo,
                        ib.path_immagine,
                        COUNT(q.idQuestionario) AS total_valutazioni,
                        SUM(
                            (CASE WHEN TRIM(q.domanda1) = 'Generated' THEN 1 ELSE 0 END) +
                            (CASE WHEN TRIM(q.domanda2) = 'Generated' THEN 1 ELSE 0 END) +
                            (CASE WHEN TRIM(q.domanda3) = 'Generated' THEN 1 ELSE 0 END) +
                            (CASE WHEN TRIM(q.domanda4) = 'Generated' THEN 1 ELSE 0 END) +
                            (CASE WHEN TRIM(q.domanda5) = 'Generated' THEN 1 ELSE 0 END)
                        ) AS generated_wins
                    FROM immagini_baseline ib
                    LEFT JOIN immagini_generate ig ON ib.idImmagine = ig.id_immagine_baseline
                    LEFT JOIN questionario q ON ig.idGenerazione = q.id_immagine_generata
                    GROUP BY ib.idImmagine
                    '''
                    
                    df = pd.read_sql_query(query, conn)
                    
                    # Calcola la percentuale di successo
                    df['success_rate'] = np.where(
                        df['total_valutazioni'] > 0,
                        (df['generated_wins'] / (df['total_valutazioni'] * 5)).round(2),
                        0
                    )
                    
                    # Ordina per performance
                    df = df.sort_values('success_rate', ascending=False)
                    
                    # Crea il grafico
                    fig = px.bar(df,
                                x='idImmagine',
                                y='success_rate',
                                color='genere_del_capo',
                                title='Performance per Immagine Baseline',
                                labels={'idImmagine': 'ID Baseline', 
                                        'success_rate': '% Preferenze Generate',
                                        'genere_del_capo': 'Genere'},
                                hover_data=['path_immagine', 'total_valutazioni'])
                    
                    fig.update_layout(
                        yaxis_tickformat=".0%",
                        height=300,
                        width=600,
                        xaxis_title="ID Immagine Baseline",
                        yaxis_title="% Preferenze per Generate"
                    )
                    fig.update_xaxes(tickmode='linear')
                    
                    return df[['idImmagine', 'genere_del_capo', 'success_rate', 'total_valutazioni']], fig
                
                except Exception as e:
                    print(f"Errore analisi baseline: {str(e)}")
                    return pd.DataFrame(), None
                finally:
                    conn.close()

            update_baseline_btn.click(
                fn=analyze_baseline_performance,
                outputs=[baseline_output, baseline_plot]
            )

        # Sezione correlazioni semplici
        with gr.Tab("📉 Correlazioni Semplici"):
            gr.Markdown("## 📉 Correlazioni Semplici con % Preferenza Generate")
            gr.Markdown("""
            Questa tabella mostra le **correlazioni lineari semplici** tra la preferenza per immagini generate (`preference_rate`)  
            e le caratteristiche utente (`età`, `competenza_moda`, `interesse_moda`).
            """)

            correlation_btn = gr.Button("Calcola Correlazioni", variant="secondary")
            correlation_output = gr.DataFrame(label="Correlazioni", wrap=True)
            correlation_plot = gr.Plot()

            def compute_correlations():
                conn = get_db_connection()
                try:
                    users = pd.read_sql_query("SELECT * FROM registrazioni", conn, dtype={
                        'eta': 'float64',
                        'competenza_moda': 'float64', 
                        'interesse_moda': 'float64'
                    })

                    quest = pd.read_sql_query('''
                        SELECT 
                            idUtente,
                            SUM(
                                (CASE WHEN TRIM(domanda1) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda2) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda3) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda4) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda5) = 'Generated' THEN 1 ELSE 0 END)
                            ) AS generated_count,
                            COUNT(*) * 5 AS total_questions
                        FROM questionario
                        GROUP BY idUtente
                    ''', conn)

                    merged = pd.merge(users, quest, on='idUtente', how='inner').dropna()
                    merged['preference_rate'] = np.where(
                        merged['total_questions'] > 0,
                        merged['generated_count'] / merged['total_questions'],
                        0
                    )

                    corr = merged[['preference_rate', 'eta', 'competenza_moda', 'interesse_moda']].corr()
                    result_df = corr.loc[['preference_rate'], ['eta', 'competenza_moda', 'interesse_moda']].T
                    result_df.columns = ['Correlazione']
                    result_df.index.name = 'Variabile'
                    result_df.reset_index(inplace=True)
                    result_df['Correlazione'] = result_df['Correlazione'].round(3)

                    # Heatmap
                    fig, ax = plt.subplots(figsize=(3.5, 2.8))
                    sns.heatmap(
                        corr,
                        annot=True,
                        fmt=".2f",
                        cmap="coolwarm",
                        vmin=-1,
                        vmax=1,
                        ax=ax,
                        annot_kws={"size": 8}
                    )
                    ax.set_title("Matrice di Correlazione", fontsize=9)
                    plt.xticks(fontsize=7, rotation=45)
                    plt.yticks(fontsize=7, rotation=0)
                    plt.tight_layout()

                    return result_df, fig

                except Exception as e:
                    return pd.DataFrame({'Errore': [str(e)]})
                finally:
                    conn.close()

            correlation_btn.click(
            fn=compute_correlations,
            outputs=[correlation_output, correlation_plot]
        )

        # Tab regressione lineare
        with gr.Tab("🧮 Regressione Lineare"):
            gr.Markdown("## Regressione Lineare - Preferenze Generate")
            gr.Markdown("""
            Analizza come le caratteristiche utente (età, competenza, interesse) influenzano il tasso di preferenza verso le immagini generate.
            - **Variabili indipendenti**: Età, Competenza moda, Interesse moda
            - **Variabile dipendente**: % preferenze per immagini generate
            """)
            
            # Pulsante e output
            run_regression_btn = gr.Button("Esegui Analisi", variant="primary")
            regression_output = gr.DataFrame(label="Risultati Regressione", wrap=True)
            model_summary = gr.Textbox(label="Dettagli Modello", interactive=False)
            r2_info = gr.Markdown(label="Spiegazione R²")

            # Funzione adattata per il database
            import statsmodels.api as sm
            def logistic_regression_analysis_db():
                conn = get_db_connection()
                try:
                    # Recupera dati utenti con conversione esplicita dei tipi
                    users = pd.read_sql_query("SELECT * FROM registrazioni", conn, dtype={
                        'eta': 'float64',
                        'competenza_moda': 'float64', 
                        'interesse_moda': 'float64'
                    })
                    
                    # Conversione sicurezza per le colonne numeriche
                    numeric_cols = ['eta', 'competenza_moda', 'interesse_moda']
                    for col in numeric_cols:
                        users[col] = pd.to_numeric(users[col], errors='coerce')
                    
                    # Recupera e processa i questionari
                    quest = pd.read_sql_query('''
                        SELECT 
                            idUtente,
                            SUM(
                                (CASE WHEN TRIM(domanda1) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda2) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda3) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda4) = 'Generated' THEN 1 ELSE 0 END) +
                                (CASE WHEN TRIM(domanda5) = 'Generated' THEN 1 ELSE 0 END)
                            ) AS generated_count,
                            COUNT(*) * 5 AS total_questions
                        FROM questionario
                        GROUP BY idUtente
                    ''', conn)

                    if quest.empty:
                        return pd.DataFrame(), "Nessun dato disponibile per l'analisi"
                    
                    # Unisci i dati e pulizia finale
                    merged = pd.merge(users, quest, on='idUtente', how='inner').dropna()
                    
                    # Calcola tasso preferenza con controllo divisione zero
                    merged['preference_rate'] = np.where(
                        merged['total_questions'] > 0,
                        merged['generated_count'] / merged['total_questions'],
                        0
                    )
                    
                    # Verifica dati finali
                    if merged.empty:
                        return pd.DataFrame(), "Nessun dato valido per l'analisi dopo la pulizia"
                    
                    # Preparazione variabili con controllo esplicito
                    X = merged[["eta", "competenza_moda", "interesse_moda"]].astype('float64')
                    X = sm.add_constant(X, has_constant='add')
                    y = merged['preference_rate'].clip(0, 1)  # Forza valori tra 0 e 1
                    
                    # Verifica dimensioni
                    if X.shape[0] != y.shape[0]:
                        return pd.DataFrame(), "Errore di dimensioni tra X e y"
                    
                    # Esegui regressione
                    model = sm.OLS(y, X)
                    result = model.fit()
                    
                    # Formatta risultati
                    results_df = pd.DataFrame({
                        'Variabile': result.params.index,
                        'Coefficiente': result.params.values.round(4),
                        'P-value': result.pvalues.values.round(4),
                        'Significatività': ['***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '' for p in result.pvalues]
                    })
                    
                    r2 = result.rsquared
                    r2_adj = result.rsquared_adj

                    explanation = f"""
                    **R² = {r2:.3f}**  
                    **Adjusted R² = {r2_adj:.3f}**

                    R² (coefficiente di determinazione) rappresenta la proporzione della varianza nella variabile dipendente  
                    (`preference_rate`) che è spiegata dalle variabili indipendenti (`età`, `competenza_moda`, `interesse_moda`).  
                    Un valore pari a 1 indica una perfetta spiegazione del modello, mentre 0 indica che il modello non spiega nulla della varianza.

                    L'**Adjusted R²** è una versione corretta di R² che tiene conto del numero di predittori nel modello:  
                    è utile nei test statistici perché penalizza l'aggiunta di variabili irrilevanti.  
                    Un valore di **{r2_adj:.3f}** suggerisce che, tenendo conto del numero di variabili, circa il **{r2_adj*100:.1f}% della varianza** è spiegata dal modello.
                    """

                    return results_df, result.summary().as_text(), explanation

                
                except Exception as e:
                    print(f"Debug error: {str(e)}")  # Log dettagliato
                    return pd.DataFrame(), f"Errore: {str(e)}"
                finally:
                    conn.close()
            
            run_regression_btn.click(
                fn=logistic_regression_analysis_db,
                outputs=[regression_output, model_summary, r2_info]
            )

        # Tenta prima con ilsr_pairwise() con regolarizzazione alpha=0.01
        # Se fallisce, passa automaticamente a mm_pairwise() come fallback
        with gr.Tab("🥇 Modello Bradley-Terry"):
            from choix import ilsr_pairwise
            gr.Markdown("## Modello Bradley-Terry - Confronto Globale")
            gr.Markdown("""
            **Cosa misura**: 
            - La probabilità che un'immagine generata sia preferita alla baseline
            - Tiene conto di tutte le valutazioni comparative (domande 1-5)
            - Le risposte "Indifferente" vengono ignorate per evitare ambiguità
            """)

            bt_analyze_btn = gr.Button("Esegui Analisi", variant="primary")
            bt_output = gr.Dataframe(label="Risultati")
            bt_plot = gr.Plot()
            bt_status = gr.Markdown()

            def bradley_terry_analysis():
                conn = get_db_connection()
                try:
                    # 1. Estrai dati da DB
                    df = pd.read_sql_query('''
                        SELECT 
                            q.idUtente, q.domanda1, q.domanda2, q.domanda3, q.domanda4, q.domanda5,
                            r.competenza_moda, r.interesse_moda
                        FROM questionario q
                        JOIN registrazioni r ON q.idUtente = r.idUtente
                        WHERE 
                            q.domanda1 IS NOT NULL AND
                            q.domanda2 IS NOT NULL AND
                            q.domanda3 IS NOT NULL AND
                            q.domanda4 IS NOT NULL AND
                            q.domanda5 IS NOT NULL
                    ''', conn)

                    indexed_data = []
                    indifferenti = 0

                    # 2. Ciclo sui confronti
                    for _, row in df.iterrows():
                        for domanda in [f"domanda{i}" for i in range(1, 6)]:
                            risposta = str(row[domanda]).strip().capitalize()
                            if risposta == "Generated":
                                indexed_data.append((1, 0))
                            elif risposta == "Baseline":
                                indexed_data.append((0, 1))
                            elif risposta == "Indifferente":
                                indifferenti += 1

                    if not indexed_data:
                        return (
                            pd.DataFrame(columns=['Tipologia', 'Punteggio Bradley-Terry (λ)', 'Probabilità Vittoria']),
                            None,
                            "⚠️ Nessun dato comparativo valido trovato"
                        )

                    # 3. Confronti senza pesi
                    expanded = [(winner, loser) for winner, loser in indexed_data]

                    # 4. Calcolo parametri BT
                    params = ilsr_pairwise(n_items=2, data=expanded, alpha=0.01)
                    exp_params = np.exp(params)
                    probs = exp_params / exp_params.sum()

                    # 5. Risultati finali
                    results_df = pd.DataFrame({
                        'Tipologia': ['baseline', 'generated'],
                        'Punteggio Bradley-Terry (λ)': np.round(params, 4),
                        'Probabilità Vittoria': np.round(probs, 4)
                    })

                    fig = px.bar(
                        results_df,
                        x='Tipologia',
                        y='Probabilità Vittoria',
                        color='Tipologia',
                        title="Probabilità Preferenza Globale (BT Standard)",
                        text_auto='.1%',
                        category_orders={'Tipologia': ['generated', 'baseline']}
                    )
                    fig.update_layout(
                        yaxis=dict(tickformat=".0%", range=[0, 1]),
                        height=300,
                        width=600,
                        showlegend=True,
                        margin=dict(t=100),
                        title_x=0.5
                    )

                    fig.add_annotation(
                        x=0.5, y=1.1,
                        xref="paper", yref="paper",
                        text=f"Generated: {probs[1]:.1%}",
                        showarrow=False,
                        font=dict(size=14)
                    )

                    status_msg = f"{len(indexed_data)} confronti pesati - {indifferenti} risposte 'Indifferente' ignorate"

                    return results_df, fig, status_msg

                except Exception as e:
                    return (
                        pd.DataFrame(columns=['Tipologia', 'Punteggio Bradley-Terry (λ)', 'Probabilità Vittoria']),
                        None,
                        f"Errore: {str(e)}"
                    )
                finally:
                    conn.close()

            bt_analyze_btn.click(
                fn=bradley_terry_analysis,
                outputs=[bt_output, bt_plot, bt_status]
            )

        with gr.Tab("⚖️ BT: Pesato vs Non Pesato"):
            from choix import ilsr_pairwise
            gr.Markdown("## Confronto Bradley-Terry Pesato vs Non Pesato")
            gr.Markdown("""
            Questa sezione confronta l'effetto del **peso utente (competenza e interesse)** nel modello Bradley-Terry.  
            - Il modello **non pesato** tratta tutte le risposte allo stesso modo.  
            - Il modello **pesato** replica i confronti in base al punteggio combinato dell'utente.
            """)

            compare_btn = gr.Button("Esegui Confronto", variant="primary")
            compare_df = gr.DataFrame(label="Risultati a Confronto")
            compare_plot = gr.Plot()
            compare_msg = gr.Markdown()

            def compare_bt_models():
                conn = get_db_connection()
                try:
                    df = pd.read_sql_query('''
                        SELECT 
                            q.idUtente, q.domanda1, q.domanda2, q.domanda3, q.domanda4, q.domanda5,
                            r.competenza_moda, r.interesse_moda
                        FROM questionario q
                        JOIN registrazioni r ON q.idUtente = r.idUtente
                        WHERE 
                            q.domanda1 IS NOT NULL AND
                            q.domanda2 IS NOT NULL AND
                            q.domanda3 IS NOT NULL AND
                            q.domanda4 IS NOT NULL AND
                            q.domanda5 IS NOT NULL
                    ''', conn)

                    raw_data = []
                    weighted_data = []
                    indifferenti = 0

                    for _, row in df.iterrows():
                        try:
                            competenza = float(row["competenza_moda"])
                            interesse = float(row["interesse_moda"])
                            peso = 0.65 * competenza + 0.35 * interesse
                        except:
                            continue

                        for domanda in [f"domanda{i}" for i in range(1, 6)]:
                            risposta = str(row[domanda]).strip().capitalize()
                            if risposta == "Generated":
                                raw_data.append((1, 0))
                                weighted_data.extend([(1, 0)] * max(1, int(round(peso))))
                            elif risposta == "Baseline":
                                raw_data.append((0, 1))
                                weighted_data.extend([(0, 1)] * max(1, int(round(peso))))
                            elif risposta == "Indifferente":
                                indifferenti += 1

                    if not raw_data or not weighted_data:
                        return pd.DataFrame(), None, "⚠️ Nessun dato comparativo valido"

                    # Calcola entrambi i modelli
                    params_raw = ilsr_pairwise(n_items=2, data=raw_data, alpha=0.01)
                    exp_raw = np.exp(params_raw)
                    prob_raw = exp_raw / exp_raw.sum()

                    params_weighted = ilsr_pairwise(n_items=2, data=weighted_data, alpha=0.01)
                    exp_weighted = np.exp(params_weighted)
                    prob_weighted = exp_weighted / exp_weighted.sum()

                    results = pd.DataFrame({
                        'Modello': ['Non Pesato', 'Pesato'],
                        'Prob. Generated': [np.round(prob_raw[1], 4), np.round(prob_weighted[1], 4)],
                        'Prob. Baseline': [np.round(prob_raw[0], 4), np.round(prob_weighted[0], 4)],
                        'λ Generated': [np.round(params_raw[1], 4), np.round(params_weighted[1], 4)],
                        'λ Baseline': [np.round(params_raw[0], 4), np.round(params_weighted[0], 4)]
                    })

                    fig = px.bar(
                        results.melt(id_vars='Modello', value_vars=['Prob. Generated', 'Prob. Baseline']),
                        x='Modello',
                        y='value',
                        color='variable',
                        barmode='group',
                        title="Probabilità di Vittoria (Generated vs Baseline)",
                        text_auto='.1%'
                    )

                    fig.update_layout(
                        yaxis_tickformat=".0%",
                        height=300,
                        width=600,
                        title_x=0.5,
                        showlegend=True
                    )

                    msg = f"Confronti totali: {len(raw_data)} – Indifferenti ignorati: {indifferenti}"
                    return results, fig, msg

                except Exception as e:
                    return pd.DataFrame(), None, f"Errore: {str(e)}"
                finally:
                    conn.close()

            compare_btn.click(
                fn=compare_bt_models,
                outputs=[compare_df, compare_plot, compare_msg]
            )

        return demo

if __name__ == '__main__':
    init_db()  # Inizializza il database all'avvio
    app = create_interface()  # 2. Costruisci l'interfaccia con i dati aggiornati
    app.launch(server_port=7860, share=True) #, share=True (per mettere la pagina online)