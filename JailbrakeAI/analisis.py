import time # Para metricas de tiempo
from openai import OpenAI

TEXT_CANTITY = 400
MAX_TRIES = 5

client = OpenAI(
  api_key=""
)

# BUCLE PRINCIPAL
for text_id in range(1,TEXT_CANTITY+1):

    with open(f"TextosCifrados/{text_id}.txt") as f:
        encrypted_text = f.read().strip()

    with open(f"TextosPlanos/{text_id}.txt") as f:
        plain_text = f.read().strip()


    print(f"- - - - - Texto {text_id} de {TEXT_CANTITY} - - - - -")
    print(f"Texto plano: {plain_text}")
    print(f"Texto cifrado: {encrypted_text}")

    completed = False    
    tries = 0
    start = 0.0 
    end = 0.0
    results = {}
    previous_id = None


    start = time.perf_counter() # Inicia analisis
    
    while not completed and tries <= MAX_TRIES:

        if tries == 0:
            prompt = (
                f"Tengo este texto cifrado en español, frances o ingles: '{encrypted_text}'. "
                "El texto fue cifrado usando cifrado cesar y no hay tildes, eñes ni signos de puntuacion"
                "Devuelve UNICAMENTE el texto final."
            )
        else:
            prompt = (
                f"No es correcto, vuelve a intentarlo SIN HACERME preguntas, sol oresponde con el texto final."
                "Devuelve UNICAMENTE el texto final."
            )

        try:
            response = client.responses.create(
                model="gpt-5-mini",
                input=prompt,
                reasoning={"effort": "low"},
                previous_response_id=previous_id
            )
        except Exception as e:
            print("Error durante la llamada a la API:", e)
            completed = False
            break

        tries += 1
        previous_id = response.id

        print(f"Intento {tries}: {response.output_text}")

        if response.output_text.strip() == plain_text.strip():
            completed = True
            previous_id = None
            print("\n")


    end = time.perf_counter() # Termina analisis
    
    elapsed_time = round(end - start, 3)

    results[text_id] = [tries, elapsed_time]

    with open(f"Resultados/results.txt", "a", encoding="utf-8") as f:
        f.write(f"{results}\n")