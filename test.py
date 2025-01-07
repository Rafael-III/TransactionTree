import sys

def process_text(text):
    # Aquí puedes realizar cualquier transformación
    return text[::-1]  # Ejemplo: invierte el texto

if __name__ == "__main__":
    input_text = sys.argv[1]  # Obtiene el texto como argumento
    result = process_text(input_text)
    print(result)  # Devuelve el resultado al backend
