'''
--> image-text-to-text <--
modello: google/gemini-2.0-flash-exp:free 
link: https://openrouter.ai/google/gemini-2.0-flash-exp:free
'''

from openai import OpenAI
import base64
import mimetypes

def get_image_as_base64(file_path: str) -> str:
    """Convert a local image file to base64 data URI."""
    # Legge il file immagine come dati binari
    with open(file_path, "rb") as image_file:
        image_data = image_file.read()
    
    # Determina il tipo MIME dal percorso del file
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "image/jpeg"  # Default a JPEG
    
    # Converte in base64
    base64_data = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{base64_data}"

def generate_fashion_prompt(image_path: str, user_description: str) -> str:
    # Converti immagine in base64
    data_uri = get_image_as_base64(image_path)
    
    # Configurazione client OpenAI con parametri fissi
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="INSERIRE API KEY di OPEN ROUTER" # Rimossa per motivi di sicurezza
    )
    
    vlm_prompt = """
    Your task is to generate a detailed and visually compelling prompt to create an advertising (fashion editorial) image.

    Instructions:
    1. Analyze the Image: Identify the clothing item’s key details—style, color, fabric, fit, and unique elements.
    2. Personalize the Description: Adapt the description to match the user's fashion preferences and needs. Ensure it aligns with their preferred colors, styles, and occasions. Never explicitly mention the user characteristics, just use them as inspiration for the textual description.
    3. Ensure that the model is representative of the user: it should match the user age and gender.
    4. Craft a Standalone Prompt: Write an engaging, detailed text prompt as if describing an idealized version of the clothing piece. Do not reference the original image—make the prompt independent for text-to-image generation.
    5. Ensure a Full-Body Shot: The prompt must specify a **full-body view** of the model wearing the outfit, avoiding close-ups. Use terms like "full-body portrait," "standing pose," or "showing the entire outfit" to reinforce this.
    6. Ensure that the prompt is not excessively verbose. It should be detailed enough to guide the image generation process effectively: it should specify the style of the image, the subject and action, the composition and framing, the lightning and color, and the background.
    7. Output Only the Textual Prompt: No explanations, metadata, or additional commentary—only the generated description. \n
    """

    # Creazione messaggio
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": vlm_prompt + user_description
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_uri
                    }
                }
            ]
        }
    ]

    # Chiamata API
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "<YOUR_SITE_URL>",
            "X-Title": "<YOUR_SITE_NAME>"
        },
        model="google/gemini-2.0-flash-exp:free",
        messages=messages,
        seed=42,
        temperature=0,
        top_p=0.8
    )
    
    # Pulizia del risultato (elimino \n)
    testo_pulito = completion.choices[0].message.content.replace("\n", " ").replace("\r", " ")

    # Ritorna il risultato pulito
    return testo_pulito

'''
usage in another python file:

from models import generate_fashion_prompt

image_path = r"D:\Scrivania\Desktop\Altri Esami\Tesi\baseline_uomo_1.jpg"
user_desc = """A man, 35 years old, resident in France, painter, salary of 30,000 euros per month, single, 
lover of art deco, favorite brands: Ralph Lauren and Halston, favorite music genre: jazz, 
in the clothes he wears he looks for: audacity and seduction, favorite colors: red and blue."""

# Chiamata alla funzione
prompt = generate_fashion_prompt(image_path, user_desc)
print(prompt)
'''





'''
--> text-to-image <--
modello: stable diffusion 3.5 large
link: 
'''
import requests
import os

def generate_adv_image(generated_prompt: str, generation_id: int) -> str:
    try:
        # Configurazione fissa dell'API
        STABILITY_API_KEY = "INSERIRE API KEY di STABILITY AI" # Rimossa per motivi di sicurezza
        API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "image/*"
        }

        # Create multipart/form-data payload
        files = {
            "model": (None, "sd3.5-large"),
            "mode": (None, "text-to-image"),
            "seed": (None, "42"),
            "prompt": (None, generated_prompt),
            "output_format": (None, "jpeg"),
            "steps": (None, "40"),
            "width": (None, 1024),
            "height": (None, 1024),
        }

        # Invio richiesta
        response = requests.post(API_URL, headers=headers, files=files)
        
        # Verifica che la risposta contenga effettivamente un'immagine
        if not response.content:
            raise ValueError("La risposta API è vuota")

        # Verifica che il file sia un'immagine valida
        from PIL import Image
        from io import BytesIO
        try:
            Image.open(BytesIO(response.content)).verify()
        except Exception as e:
            raise ValueError(f"Contenuto immagine non valido: {str(e)}")

        # Inizio Salvataggio:
        # Creazione cartella se non esiste
        output_folder = "Immagini Generate"
        os.makedirs(output_folder, exist_ok=True)

        # Nome immagine
        nome = os.path.join(output_folder, f"immagine_adv_{generation_id}.jpg")

        # Gestione risposta
        if response.status_code == 200:
            with open(nome, 'wb') as file:
                file.write(response.content)
            print("Immagine salvata come " + nome)
        else:
            print(f"Errore: {response.status_code}, {response.text}")
        # Fine Salvataggio.

        # Verifica finale del file salvato
        if not os.path.exists(nome) or os.path.getsize(nome) == 0:
            raise IOError("Il file non è stato salvato correttamente")

        return nome

    except Exception as e:
        print(f"Errore grave durante la generazione: {str(e)}")
        # Pulizia eventuali file parziali
        if 'nome' in locals() and os.path.exists(nome):
            os.remove(nome)
        raise  # Rilancia l'eccezione

'''
usage in another python file: 
prompt = """A portrait of Elara, a 58-year-old Dutch secretary..."""  # prompt completo
generate_adv_image(prompt)
'''