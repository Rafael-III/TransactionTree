import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json

def GetTransaction(qty):
    try:
        # Conexión a la base de datos
        connection = mysql.connector.connect(
            host='localhost',
            database='transaction_tree',
            user='root',
            password=''
        )

        # connection = mysql.connector.connect(
        #     host='35.237.43.215',
        #     database='openemm',
        #     user='rafaelguanipa',
        #     password='foGMPAhRxous#$|-'
        # )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            
            # Usa el parámetro quantity en la consulta
            query = "SELECT id, param_value FROM customer_60_trans_data_tbl LIMIT %s"
            cursor.execute(query, (qty,))
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

# Pruebas rápidas con `if __name__ == "__main__"`
if __name__ == "__main__":
    # Cambia el valor de `quantity` para probar diferentes cantidades de registros
    quantity = 5
    print(f"Obteniendo {quantity} registros de la tabla...")

    # Llama a la función y muestra los resultados
    data = GetTransaction(quantity)
    print(json.dumps(data, indent=4))  # Muestra los resultados formateados como JSON
