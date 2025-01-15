import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime

def get_data_from_db():
    try:
        # Conexión a la base de datos
        connection = mysql.connector.connect(
            host='localhost',
            database='transaction_tree',
            user='root',
            password=''
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT id, param_value FROM customer_60_trans_data_tbl LIMIT 10")  # Ajusta la consulta según tus datos
            rows = cursor.fetchall()

            # Convertir objetos datetime en cadenas
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, datetime):  # Si es un objeto datetime
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')  # Formatea como texto

            return rows

    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return {"error": str(e)}

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    # Llama a la función y convierte los datos a JSON
    data = get_data_from_db()
    print(json.dumps(data, indent=4))  # Formatea la salida con indentación para mejor lectura
