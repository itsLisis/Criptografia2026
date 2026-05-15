TEXT_CANTITY = 400

# -----------------------CIFRADO DE TEXTO------------------------
def encrypt_text(text):
    text = text.upper()
    encrypted_text = ""

    for letter in text:
        if letter != " ":
            number = ord(letter)-65
            number += 22 # 22 es el desplazamiento
            number %= 26 # modulo 26
            encrypted_text += (chr(number+65))
        else:
            encrypted_text += " "
    
    return encrypted_text
# ---------------------------------------------------------------


# ----------------ESCRITURA DE ARCHIVOS CIFRADOS-----------------
def write_file(encrypted_text, text_id):
    with open(f"TextosCifrados/{text_id}.txt", "w", encoding="utf-8") as f:
        f.write(encrypted_text)
# ---------------------------------------------------------------


# ---------------LECTURA DE ARCHIVOS NO CIFRADOS-----------------
for text_id in range(1,TEXT_CANTITY+1):
    with open(f"TextosPlanos/{text_id}.txt") as f:
        plain_text = f.read()

    #print(encrypt_text(plain_text))
    write_file(encrypt_text(plain_text), text_id)
# ---------------------------------------------------------------