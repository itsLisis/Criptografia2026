with open("Resultados/results.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

result = []

for line in lines:
    line = line.strip()
    
    start = line.find("[")
    end = line.find("]")
    
    if start != -1 and end != -1:
        content = line[start+1:end]
        result.append(content)

# Guardar resultado
with open("Resultados/analisis.txt", "a", encoding="utf-8") as f:
    for item in result:
        f.write(item + "\n")