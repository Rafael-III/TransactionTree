from datetime import datetime
import re
import sys
from io import StringIO

########################################################
###################### PATTERNS ########################
########################################################
# patron (4. TransactionDate & 5 transactionTime)
#ej: <line>11/13/24 11:02 0276 01 0011 197398    </line><line>(\d{2}/\d{2}/\d{2})[\d|\s|:]+</line>
#transactionDateTimePattern = re.compile(r'<line>(\d{1,2}/\d{1,2}/\d{2,4})\s(\d{2}:\d{2})\s\d{2}[\d|\s]+</line>')
transactionDateTimePattern = re.compile(r'<line> *(\d{1,2}/\d{1,2}/\d{2,4}) +(\d{2}:\d{2}) +\d{2}.*</line>')

# patron (13. Address1)
#ej: <line>            120 Forum Drive           </line>
addressPattern = re.compile(r'<line>\s+(.*?) +</line>')

# patron (14. City & 15. StateCode & 16. StoreZip)
#ej: <line>          Columbia, SC 29229          </line>
cityStateZipPattern = re.compile(r'<line> +(\w+?), ([A-Z]{2}) (\d{5}) +</line>')

# patron (19. StorePhoneNumber)
#ej: <line>             803-828-6836             </line>
storePhoneNumberPattern = re.compile(r'<line> +([\d-]+) +</line>')

# patron (37. itemsSold ) 37, 38, 39, 40, 41, 42, 44 & 45
#ej: <line>        SANTA CRUZ LIME         5.99 B</line>
itemsSoldPattern = re.compile(r'<line>(WT|) +(\S(?:.*?\S)?) +(\d*\.\d{2}) (B|F|T)</line>')

# patron (43. QuantitySold)
#ej: <line> 0.75 lb @ 1.79 /lb                   </line>
itemsSoldWeightPattern = re.compile(r'<line>.+?lb @ ((?:\d*\.\d{1,2})) .+</line>')

# patron (46. DiscountDollarAmount & 49. ItemDiscounts) 
#ej: <line>SC      KRAFT DRESSING          1.29-B</line>
itemDiscountsPattern = re.compile(r'<line> *(SC|MC)\s{6}(.*?) *(\d*\.\d{2})(-[A-Z])</line>')

# patron INICIO DESCUENTO (no se usa)
#ej: <line> 1 @ 1.29                             </line>
inicio_descuento_pattern = re.compile(r'<line> +\d\s@\s\d+\.\d{2}\s*</line>')

# pattern (52. TenderTypeDate i. TenderEntryMethod) 
#ej: <line>Contactless                           </line>
tenderEntryMethodPattern = re.compile(r'<line> *(CHIP|Contactless|S<line>(WT|)\s*(\S(?:.*?\S)?)\s+(\d+\.\d{2})\s(B|F|T)</line>wiped) +</line>')

# pattern (52. TenderTypeDate ii. TenderType & v. TotalAmount) T
#ej: <line>VF      Debit     USD$         81.08  </line>
tenderTypeAndAmountPattern = re.compile(r'<line>.*(?:<strong>\s*)?(VF      MasterCd CR|VF      WIC Tender|VF      EBT FS|VF      Debit|        PAYEEZY|        OUTSIDE CREDIT|VF      Visa CR|VF MO   Visa CR|VF      AMEX CR|VF MO   Debit|   MO   CASH|        CASH)\s+(\d*\.\d{1,2}|\d+)\s*(?:</strong>)?.*</line>')

# pattern (52. TenderTypeDate iii. AccountNumber) 
#ej: <line>        Acct # ************9005       </line>
accountNumberPattern = re.compile(r'<line> +Acct # (\*{12}\d{4}) +</line>')

# pattern (52. TenderTypeDate iv. AuthCode) 
#ej: <line>        Authorization # 180365        </line>
authCodePattern = re.compile(r'<line> +Authorization # (\d+) +</line>')

# pattern (52. TenderTypeDate vi. TenderReference) 
#ej: <line>        Sequence # 180365             </line>
tenderReferencePattern = re.compile(r'<line> +Sequence # (\d+) +</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 2. CardType) 
#ej: <line>    Application Label: US Debit       </line>
cardTypePattern = re.compile(r'<line> +Application Label: (.+?) +</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 3. ISOResCode) 
#ej: <line>    AID: A0000000042203               </line>
isoResCodePattern = re.compile(r'<line> +AID: (.+?) +</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 4. AuxResponse) 
#ej: <line>    TVR: 0000048001                   </line>
auxResponsePattern = re.compile(r'<line> +TVR: (.+?) +</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 5. ResponseCode) 
#ej: <line>    IAD: 0110A040012200000000000000000</line>
responseCodePattern = re.compile(r'<line> +IAD: (.+?) *</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 6. ResponseMessage) 
#ej: <line>    ARC: 3030                         </line>
responseMessagePattern = re.compile(r'<line> +ARC: (.+?) +</line>')

# pattern (52. TenderTypeDate vii. PaymentResponse 7. DisplayMessage) 
#ej: <line>        APPROVED                      </line>
displayMessagePattern = re.compile(r'<line> +(APPROVED|DECLINED) +</line>')

# patron (53.	FinalTaxLines)
#ej: <line>   **** SC 2% TAX         1.59        </line>
finalTaxLinesPattern = re.compile(r'<line> +(\*{4} (SC|NC) (\d*\.\d{1,2}|\d+)% TAX) +(\d*\.\d{1,2}|\d+) +</line>')

# patron (36. TotalAmount)
#ej: <line>          **** BALANCE         81.08  </line>
totalAmountPattern = re.compile(r'<line> +\*{4} BALANCE +(\d*\.\d*) +</line>')

# patron (54. TotalsTransactionData ii.	DiscountTotal)
#ej: <line><strong>TODAY'S SAVINGS TOTAL:      6.27      </strong></line>
discountTotalPattern = re.compile(r'<line> *<strong>TODAY\'S SAVINGS TOTAL: +(\d*\.\d*) +</strong> *</line>')

# patron (54. TotalsTransactionData v.	Change)
#ej: <line>        CHANGE                   .00  </line>
changePattern = re.compile(r'<line> +CHANGE +(\d*\.\d*) +</line>')

########################################################
###################### MAPPING #########################
########################################################
quantitySoldTypeMapping = {
    'WT': 'LBS'
}

tenderEntryMethodMapping = {
    'VF      MasterCd CR': 'CREDIT-MC',
    'Contactless': 'Tapped',
    'Swiped': 'Manual'
}

tenderTypeMapping = {
    'VF      MasterCd CR': 'CREDIT-MC',
    'VF      WIC Tender': 'WICCheck',
    'VF      EBT FS': 'EBTFoodstamps',
    'VF      Debit': 'DEBIT-OTHER',
    '        PAYEEZY': 'OTHER',
    '        OUTSIDE CREDIT': 'CREDIT-OTHER',
    'VF      Visa CR': 'CREDIT-VISA',
    'VF MO   Visa CR': 'CREDIT-VISA',
    'VF      AMEX CR': 'CREDIT-AMEX',
    'VF MO   Debit': 'DEBIT-OTHER',
    '   MO   CASH': 'CASH',
    '        CASH': 'CASH'
}

########################################################
############ INICIALIZACION DE VARIABLES ###############
########################################################
result = {}
productMapping  = {}
countryCode = 'US'
storePhoneType = 'Work'
taxType = 'StateOrProvince'
discountingMethod = 'DollarOff'
productIdType = 'SKU'
itemReceivedType = 'Pickedup'
tenderEntryMethod = 'Manual' 
tenderType = 'OTHER'
taxDetailNumber = 0

totalTax = 0
totalDescuento = 0
totalVenta = 0    

# city = None
# stateCode = None
# storeZip = None
# address1 = None
transactionDate = None
transactionTime = None
storePhoneNumber = None

if __name__ == "__main__":
    original_stdout = sys.stdout  
    captured_output = StringIO() 
    sys.stdout = captured_output  
    receipt_text = sys.argv[1]

    if not receipt_text:
        print("Error: No se proporcionó ningún texto para procesar.")
        sys.exit(1)

    result = {}  # Diccionario para almacenar los resultados según las reglas

    lines = receipt_text.splitlines()
    for i, line in enumerate(lines):
        if transactionDateTimeMatch := transactionDateTimePattern.search(line): #Verifica si la línea corresponde al 4. TransactionDate & 5. TransactionTime
            transactionDate = datetime.strptime(transactionDateTimeMatch.group(1), '%m/%d/%y').strftime('%Y-%m-%d')
            transactionTime = datetime.strptime(transactionDateTimeMatch.group(2), '%H:%M').strftime('%H:%M:00')

            result["transactionDate"] = transactionDate
            result["transactionTime"] = transactionTime

        elif i == 1:
            if addressMatch := addressPattern.search(line): #Verifica si la línea corresponde al 13. address1
                result["address1"] = addressMatch.group(1)            

        elif i == 2: 
            if cityStateZipPatternMatch := cityStateZipPattern.search(line): #Verificar si la línea corresponde a 14. City & 15. StateCode & 16. StoreZip
                result["city"] = cityStateZipPatternMatch.group(1)
                result["stateCode"] = cityStateZipPatternMatch.group(2)
                result["storeZip"] = cityStateZipPatternMatch.group(3)

        elif i == 3:
            if storePhoneNumberMatch := storePhoneNumberPattern.search(line): #Verificar si la línea corresponde al 19. StorePhoneNumber
                result["storePhoneNumber"] = storePhoneNumberMatch.group(1)

        elif itemsSold := itemsSoldPattern.search(line): # Verificar si la línea corresponde a un itemsSold 37, 38, 39, 40, 41, 42, 43, 44 & 45
            quantitySoldType = 'LBS' if itemsSold.group(1) == 'WT' else 'EACH'
            quantitySold = itemsSoldWeightPattern.search(lines[i-1]).group(1) if itemsSold.group(1) == 'WT' else '1'
            description = itemsSold.group(2)
            dollarAmount = float(itemsSold.group(3))
            itemsSoldType = itemsSold.group(4)

            totalVenta += dollarAmount
            productMapping[description] = dollarAmount

            # Asegurarse de que "itemsSold" sea una lista
            if "itemsSold" not in result:
                result["itemsSold"] = []

            # Agregar el producto a la lista
            result["itemsSold"].append({
                "productIdType": productIdType,
                "description": description,
                "quantitySoldType": quantitySoldType,
                "quantitySold": quantitySold,
                "itemReceivedType": itemReceivedType,
                "dollarAmount": dollarAmount
            })

        elif discount := itemDiscountsPattern.search(line): # Verificar si la línea corresponde a 46. DiscountDollarAmount & 49. ItemDiscounts
            discountReasonCode = discount.group(1)
            discountDescription = discount.group(2)
            discountAmount = discountDollarAmount = float(discount.group(3))
            printLine = discount.group(4)
            
            extDollarAmount = productMapping.get(discountDescription, 0) - discountDollarAmount
            discountPercent = '???'
            if(discountReasonCode == 'SC'):
                discountPercent = round(discountDollarAmount / productMapping.get(discountDescription, 1), 2)

            totalDescuento += discountDollarAmount

            # Asegurarse de que "discounts" sea una lista
            if "discount" not in result:
                result["discount"] = []

            result["discount"].append({
                "discountDollarAmount": discountDollarAmount,
                "extDollarAmount": extDollarAmount,
                "discountPercent": discountPercent,
                "discountAmount": discountAmount,
                "discountDescription": discountDescription,
                "discountReasonCode": discountReasonCode,
                "discountingMethod": discountingMethod,
                "printLine": printLine     
            })

        elif tenderEntryMethodMatch := tenderEntryMethodPattern.search(line): #Verifica si la línea corresponde al tender type method 52 i
            result["tenderEntryMethod"] = tenderEntryMethodMapping.get(tenderEntryMethodMatch.group(1), 'Manual')

        elif tenderTypeAndAmountMatch := tenderTypeAndAmountPattern.search(line): #Verifica si la línea corresponde al tender type 52 ii & amount v
            result["tenderType"] = tenderTypeMapping.get(tenderTypeAndAmountMatch.group(1), 'OTHER')
            result["tenderAmount"] = tenderTypeAndAmountMatch.group(2)

        elif accountNumberMatch := accountNumberPattern.search(line): #Verifica si la línea corresponde al account number type 52 iii
            result["accountNumber"] = accountNumberMatch.group(1)

        elif authCodeMatch := authCodePattern.search(line): #Verifica si la línea corresponde al tender type 52 iV
            result["authCode"] = authCodeMatch.group(1)

        elif tenderReferenceMatch := tenderReferencePattern.search(line): #Verifica si la línea corresponde al tender reference 52 vi
            result["tenderReference"] = tenderReferenceMatch.group(1)

        elif cardTypeMatch := cardTypePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 2
            result["cardType"] = cardTypeMatch.group(1)

        elif isoResCodeMatch := isoResCodePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 3
            result["isoResCode"] = isoResCodeMatch.group(1)

        elif auxResponseMatch := auxResponsePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 4
            result["auxResponse"] = auxResponseMatch.group(1)

        elif responseCodeMatch := responseCodePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 5
            result["responseCode"] = responseCodeMatch.group(1)

        elif responseMessageMatch := responseMessagePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 6
            result["responseMessage"] = responseMessageMatch.group(1)

        elif displayMessageMatch := displayMessagePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 7
            result["displayMessage"] = displayMessageMatch.group(1)

        elif finalTaxLinesMatch := finalTaxLinesPattern.search(line): #Verificar si la línea corresponde a 53. FinalTaxLines
            taxDetailNumber += 1
            taxDescription = finalTaxLinesMatch.group(1)
            taxRuleCode = finalTaxLinesMatch.group(2)
            taxPercent = finalTaxLinesMatch.group(3)
            taxAmount = finalTaxLinesMatch.group(4)

            totalTax += float(taxAmount)

            # Asegurarse de que "itemsSold" sea una lista
            if "finalTaxLines" not in result:
                result["finalTaxLines"] = []

            # Agregar el producto a la lista
            result["finalTaxLines"].append({
                "taxAmount": taxAmount,
                "taxPercent": taxPercent,
                "taxDescription": taxDescription,
                "taxDetailNumber": taxDetailNumber,
                "taxRuleCode": taxRuleCode,
            })

        elif totalAmountMatch := totalAmountPattern.search(line): #Verifica si la línea corresponde 36. TotalAmount
            result["totalAmount"] = totalAmountMatch.group(1)
            #discountTotalAmount = subTotalAmount = float(totalAmount) - totalTax

            # result["totalsTransactionData"] = {
            #     "totalAmount": totalAmount,
            #     "discountTotalAmount": discountTotalAmount,
            #     "subTotalAmount": subTotalAmount
            # }

        elif discountTotalMatch := discountTotalPattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData ii. DiscountTotal
            result["discountTotal"] = discountTotalMatch.group(1)

        elif changeMatch := changePattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData v. Change
            result["change"] = changeMatch.group(1)

    try:
        print(f"4. Transaction Date: {result.get('transactionDate', '*** Not found')}")
        print(f"5. Transaction Time: {result.get('transactionTime', '*** Not found')}")
        print(f"13. Address 1: {result.get('address1', '*** Not found')}")
        print(f"14. City: {result.get('city', '*** Not found')}")
        print(f"15. State Code: {result.get('stateCode', '*** Not found')}")
        print(f"16. Store Zip: {result.get('storeZip', '*** Not found')}")
        print(f"19. Store Phone Number: {result.get('storePhoneNumber', '*** Not found')}")
        print(f"36. Total Amount: {result.get('totalAmount', '*** Not found')}")
        if "itemsSold" in result:
            for id, item in enumerate(result["itemsSold"], start=1):
                print(f"37. ItemsSold {id}:")
                print(f"     39. Product Id Type: {item.get('productIdType', '*** Not found')}")
                print(f"     40. Product Id: ?")
                print(f"     41. Description: {item.get('description', '*** Not found')}")
                print(f"     42. Quantity Sold Type: {item.get('quantitySoldType', '*** Not found')}")
                print(f"     43. Quantity Sold: {item.get('quantitySold', '*** Not found')}")
                print(f"     44. Item Received Type: {item.get('itemReceivedType', '*** Not found')}")
                print(f"     45. Dollar Amount: {item.get('dollarAmount', '*** Not found')}")
        else:
            print(f"37. ItemsSold: *** Not found")
        if "discount" in result:
            for id, item in enumerate(result["discount"], start=1):
                #print(f"46. Discounts {id}:")
                print(f"46. Discount Dollar Amount: {item.get('discountDollarAmount', '*** Not found')}")
                print(f"47. Ext Dollar Amount: {item.get('extDollarAmount', '*** Not found')}")
                print(f"49. Item Discounts")
                #print(f"     iii. Discount Percent: {item.get('discountPercent', '*** Not found'):.2f}")
                print(f"     iii. Discount Percent: {item.get('discountPercent', '*** Not found')}")
                print(f"     iv. Discount Amount: {item.get('discountAmount', '*** Not found'):.2f}")
                print(f"     v. Discount Description: {item.get('discountDescription', '*** Not found')}")
                print(f"     vi. Discount Reason Code: {item.get('discountReasonCode', '*** Not found')}")
                print(f"     vii. Discounting Method: {item.get('discountingMethod', '*** Not found')}")
                print(f"     viii. PrintLine: {item.get('printLine', '*** Not found')}")
        else:
            print(f"46. Discounts: *** Not implemented")
        print("52. Tender Type Date:")
        print(f"     i. Tender Entry Method: {result.get('tenderEntryMethod', '*** Not found')}")
        print(f"     ii. Tender Type: {result.get('tenderType', '*** Not found')}")
        print(f"     iii. Account Number: {result.get('accountNumber', '*** Not found')}")
        print(f"     iv. Auth Code: {result.get('authCode', '*** Not found')}")
        print(f"     v. Total Amount: {result.get('tenderAmount', '*** Not found')}")
        print(f"     vi. Tender Reference: {result.get('tenderReference', '*** Not found')}")
        print("     vii. Payment Response:")
        print(f"          1. Response IDe: {result.get('tenderReference', '*** Not found')}")
        print(f"          2. Card Type: {result.get('cardType', '*** Not found')}")
        print(f"          3. ISO Res Code: {result.get('isoResCode', '*** Not found')}")
        print(f"          4. Aux Response: {result.get('auxResponse', '*** Not found')}")
        print(f"          5. Response Code: {result.get('responseCode', '*** Not found')}")
        print(f"          6. Response Message: {result.get('responseMessage', '*** Not found')}")
        print(f"          7. Display Message: {result.get('displayMessage', '*** Not found')}")
        if "finalTaxLines" in result:
            for id, item in enumerate(result["finalTaxLines"], start=1):
                print(f"53. FinalTaxLines {id}:")
                print(f"     i. Tax Amount: {item.get('taxAmount', '*** Not found')}")
                print(f"     ii. Tax Percent: {item.get('taxPercent', '*** Not found')}")
                print(f"     iii. Tax Description: {item.get('taxDescription', '*** Not found')}")
                print(f"     iv. Tax Detail Number: {item.get('taxDetailNumber', '*** Not found')}")
                print(f"     v. Tax Rule Code: {item  .get('taxRuleCode', '*** Not found')}")
        else:
            print("53. FinalTaxLines: *** Not implemented")
        print("54. Totals Transaction Data:")
        print(f"     i. Sub Total Amount: {result.get('totalAmount', 0)} - {(totalTax):.2f} = {(float(result.get('totalAmount', 0)) - totalTax):.2f}")
        print(f"     ii. Discount Total: {result.get('discountTotal', '*** Not found')}")
        print(f"     iii. Discount Total Amount: {(float(result.get('totalAmount', 0)) - totalTax):.2f}")
        print(f"     iv. Total Amount: {result.get('totalAmount', '*** Not found')}")
        print(f"     v. Change: {result.get('change', '*** Not found')}")
        print('-------------------------------------------------')
        print(f"Total venta: {totalVenta:.2f}")
        print(f"Descuento total: {totalDescuento:.2f}")
        print('-------------------------------------------------')
        for id, (description, dollarAmount) in enumerate(productMapping.items(), start=1):
            print(f"FinalTaxLines {id}: {description} {dollarAmount}")


    finally:
        sys.stdout = original_stdout

    print(captured_output.getvalue())
