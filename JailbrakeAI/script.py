import os

input_file = "textos.txt"
output_folder = "TextosPlanos"

# Crear carpeta si no existe
os.makedirs(output_folder, exist_ok=True)

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.split(" ", 1)  # Separar número del texto
            if len(parts) == 2:
                numero, texto = parts
                output_path = os.path.join(output_folder, f"{numero}.txt")
                
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(texto)

print("Archivos creados correctamente.")