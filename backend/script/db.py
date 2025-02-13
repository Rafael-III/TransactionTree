import mysql.connector
from mysql.connector import Error

class Database:
    def __init__(self):
        try:
            self.connection = mysql.connector.connect(
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

            if self.connection.is_connected():
                # print("Conectado a la base de datos.")
                self.cursor = self.connection.cursor(dictionary=True)
        except Error as e:
            print(f"Error al conectar a la base de datos: {e}")
            self.connection = None
            self.cursor = None

    def InsertTransactionSource(self, _transactionDateTime, _trans_id, _terminalID, _storeID, _rawTransaction, _idOriginalTransaction):
        if not self.cursor:
            return None

        try:
            query = """
            INSERT INTO transaction_source (transactionDateTime, trans_id, terminalID, storeID, rawTransaction, idOriginalTransaction)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (_transactionDateTime, _trans_id, _terminalID, _storeID, _rawTransaction, _idOriginalTransaction)

            self.cursor.execute(query, values)
            self.connection.commit()

            return self.cursor.lastrowid  # Devuelve el ID insertado

        except Error as e:
            print(f"Error al insertar en transaction_source: {e}")
            return None

    def GetTransaction(self, qty):
        if not self.cursor:
            return []

        try:
            query = "SELECT id, param_value FROM customer_60_trans_data_tbl LIMIT %s"
            self.cursor.execute(query, (qty,))
            rows = self.cursor.fetchall()
            return rows
        except Error as e:
            print(f"Error al obtener transacciones: {e}")
            return []

    def InsertTransaction(self, _transactionDate, _transactionTime, _totalAmount, _change, _savingTotal, _processedDate, _isCompleted, _idStore, _idTransactionSource):
        if not self.cursor:
            return None

        try:
            query = """
            INSERT INTO transaction (
                transactionDate, transactionTime, totalAmount, `change`, savingTotal, processedDate, isCompleted, idStore, idTransactionSource
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                _transactionDate,
                _transactionTime,
                _totalAmount,
                _change,
                _savingTotal,
                _processedDate,
                _isCompleted,
                _idStore,
                _idTransactionSource
            )

            self.cursor.execute(query, values)
            self.connection.commit()

            inserted_id = self.cursor.lastrowid

            print(">> InsertTransaction: transaccion insertada correctamente.")

            return inserted_id
        except Error as e:
            print(f">> InsertTransaction: Error al insertar transaccion: {e}")
            return None


    def Insert_nn_Error_Transaction(self, _idError, _idTransaction, _errorDetail):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO nn_error_transaction (idError, idTransaction, errorDetail)
            VALUES (%s, %s, %s)
            """
            values = (_idError, _idTransaction, _errorDetail)

            self.cursor.execute(query, values)
            self.connection.commit()
            
            print(f">> InsertError: Error registrado correctamente en la transaccion {_idTransaction}.")
        except Error as e:
            print(f" >> InsertError: Error al insertar en nn_error_transaction: {e}")
    
    def InsertStore(self, _name, _address, _city, _stateCode, _storeZip, _storePhoneNumber):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO store (name, address, city, state, zip, phone)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (_name, _address, _city, _stateCode, _storeZip, _storePhoneNumber)

            self.cursor.execute(query, values)
            self.connection.commit()

            last_id = self.cursor.lastrowid 
            print(f">> Store insertado correctamente con ID: {last_id}")
            return last_id  

        except Error as e:
            print(f">> Error al insertar store: {e}")
            return None

    def InsertProduct(self, _description):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO product (description)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE idProduct=LAST_INSERT_ID(idProduct);
            """  
            # Si el producto ya existe, recuperamos su ID en lugar de duplicarlo

            values = (_description,)

            self.cursor.execute(query, values)
            self.connection.commit()

            last_id = self.cursor.lastrowid 
            print(f">> Producto registrado con ID: {last_id}")
            return last_id  

        except Error as e:
            print(f">> Error al insertar producto: {e}")
            return None

    def Insert_nn_Product_Transaction(self, _idProduct, _idTransaction, _quantitySoldType, _quantitySold, _dollarAmount, _taxFlag):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO nn_product_transaction (idProduct, idTransaction, quantitySoldType, quantitySold, dollarAmount, taxFlag)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (_idProduct, _idTransaction, _quantitySoldType, _quantitySold, _dollarAmount, _taxFlag)

            self.cursor.execute(query, values)
            self.connection.commit()

            print(f">> Producto { _idProduct } registrado en transaccion { _idTransaction }")
            return True

        except Error as e:
            print(f">> Error al insertar en nn_product_transaction: {e}")
            return False
        
    def InsertDiscount(self, _discountDollarAmount, _extDollarAmount, _discountPercent, _discountAmount, _discountReasonCode, _printLine):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO discount (discountDollarAmount, extDollarAmount, discountPercent, discountAmount, discountReasonCode, printLine)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE idDiscount=LAST_INSERT_ID(idDiscount);
            """
            values = (_discountDollarAmount, _extDollarAmount, _discountPercent, _discountAmount, _discountReasonCode, _printLine)

            self.cursor.execute(query, values)
            self.connection.commit()

            return self.cursor.lastrowid

        except Error as e:
            print(f"Error al insertar descuento: {e}")
            return None
        
    def Insert_nn_Discount_Product_Transaction(self, _idDiscount, _idProduct, _idTransaction):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO nn_discount_product_transaction (idDiscount, idProduct, idTransaction)
            VALUES (%s, %s, %s)
            """
            values = (_idDiscount, _idProduct, _idTransaction)

            self.cursor.execute(query, values)
            self.connection.commit()

            print(f">> Descuento { _idDiscount } registrado en transaccion { _idTransaction } para producto { _idProduct }")
            return True

        except Error as e:
            print(f">> Error al insertar en nn_discount_product_transaction: {e}")
            return False
        
    def InsertTax(self, _taxAmount, _taxPercent, _taxDescription, _taxDetailNumber, _taxRuleCode, _idTransaction):
        if not self.cursor:
            return

        try:
            query = """
            INSERT INTO tax (taxAmount, taxPercent, taxDescription, taxDetailNumber, taxRuleCode, idTransaction)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (_taxAmount, _taxPercent, _taxDescription, _taxDetailNumber, _taxRuleCode, _idTransaction)

            self.cursor.execute(query, values)
            self.connection.commit()

            last_id = self.cursor.lastrowid 
            print(f">> TAX registrado con ID: {last_id}")
            return last_id

        except Error as e:
            print(f"Error al insertar impuesto: {e}")
            return None

    def InsertTender(self, _tenderType, _tenderAmount, _tenderEntryMethod, _accountNumber, _authCode, _tenderReference, _cardType, _isoResCode, _auxResponse, _responseCode, _responseMessage, _displayMessage, _idTransaction):
        if not self.cursor:
            return None

        try:
            query = """
            INSERT INTO tender (tenderType, tenderAmount, tenderEntryMethod, accountNumber, authCode, tenderReference, cardType, isoResCode, auxResponse, responseCode, responseMessage, displayMessage, idTransaction)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (_tenderType, _tenderAmount, _tenderEntryMethod, _accountNumber, _authCode, _tenderReference, _cardType, _isoResCode, _auxResponse, _responseCode, _responseMessage, _displayMessage, _idTransaction)

            self.cursor.execute(query, values)
            self.connection.commit()

            return self.cursor.lastrowid

        except Error as e:
            print(f"Error al insertar tender: {e}")
            return None
        
    def InsertCustomer(self, _name, _account, _earnings, _rewardsBalance, _nextReward, _rewardsCard, _expiring, _idTransaction):
        if not self.cursor:
            return None

        try:
            query = """
            INSERT INTO customer (name, account, earnings, rewardsBalance, nextReward, rewardsCard, expiring, idTransaction)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (_name, _account, _earnings, _rewardsBalance, _nextReward, _rewardsCard, _expiring, _idTransaction)

            self.cursor.execute(query, values)
            self.connection.commit()

            return self.cursor.lastrowid 

        except Error as e:
            print(f"Error al insertar cliente: {e}")
            return None



    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Conexión a la base de datos cerrada.")
