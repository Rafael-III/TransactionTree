from datetime import datetime
import re
import sys
from io import StringIO

# <line> 0.75 lb @ 1.79 /lb                   </line>
# <line>WT      YELLOW ONIONS           1.34 B</line>

# receipt_text = """
# <line>    Family-Owned &amp; Carolinas-Based    </line>
# <line>            120 Forum Drive           </line>
# <line>          Columbia, SC 29229          </line>
# <line>             803-828-6836             </line>
# <line></line>
# <line>YOUR REWARDS CARD #XXXXXXX7677        </line>
# <line>        SPRITE ZERO             8.49 B</line>
# <line> 1 @ 2.49                             </line>
# <line>SC      SPRITE ZERO             2.49-B</line>
# <line>        SPRITE ZERO             8.49 B</line>
# <line> 1 @ 2.49                             </line>
# <line>SC      SPRITE ZERO             2.49-B</line>
# <line>        SANTA CRUZ LIME         5.99 B</line>
# <line>        SANTA CRUZ LIME         5.99 B</line>
# <line>        KRAFT DRESSING          3.79 B</line>
# <line> 1 @ 1.29                             </line>
# <line>SC      KRAFT DRESSING          1.29-B</line>
# <line>        MENTOS GUM TROPI        4.99 B</line>
# <line>        FRITOS CORN CHP         5.89 B</line>
# <line>        FRITOS CORN CHP         5.89 B</line>
# <line>        MAIN ST.BISTRO B        6.29 B</line>
# <line>        FR X AMER BLEND         4.99 B</line>
# <line>        ATKINS ENDULGE          6.99 B</line>
# <line>        ATKINS ENDULGE          6.99 B</line>
# <line>        ATKINS BARS 5CT         6.99 B</line>
# <line>        CUCUMBER                3.99 B</line>
# <line>   **** SC 2% TAX         1.59        </line>
# <line>          **** BALANCE         81.08  </line>
# <line></line>
# <line>VF      Debit     USD$         81.08  </line>
# <line>        Acct # ************9005       </line>
# <line>        Authorization # 180365        </line>
# <line>        Sequence # 180365             </line>
# <line>        APPROVED                      </line>
# <line>Contactless                           </line>
# <line>* * * PURCHASE * * * PURCHASE * * *   </line>
# <line>PIN Verified                          </line>
# <line>    Application Label: US Debit       </line>
# <line>    AID: A0000000042203               </line>
# <line>    TVR: 0000048001                   </line>
# <line>    IAD: 0110A040012200000000000000000</line>
# <line>    ARC: 3030                         </line>
# <line><strong></strong></line>
# <line>        CHANGE                   .00  </line>
# <line></line>
# <line>FRESH REWARDS SAVINGS                 </line>
# <line>        Regular Coupons      .00      </line>
# <line>        Other Rewards       6.27      </line>
# <line><strong>TODAY'S SAVINGS TOTAL:      6.27      </strong></line>
# <line></line>
# <line></line>
# <line></line>
# <line></line>
# <line>Family-Owned &amp; Carolinas-Based        </line>
# <line>We want you to have the best          </line>
# <line>homegrown experience around, so       </line>
# <line>please tell us about today's          </line>
# <line>experience at                         </line>
# <line>www.lowesfoods.com/experience         </line>
# <line>and then enter our monthly drawing    </line>
# <line>to win 1 of 5, $100 LFS gift cards!   </line>
# <line>  **************************          </line>
# <line>11/13/24 11:02 0276 01 0011 197398    </line>
# <line></line>
# <line>  Store #276  Manager Jason Torrence  </line>
# <line>      Open Daily 6:00am - 10:00pm     </line>
# <line></line>
# <line></line>
# <line></line>
# """
########################################################
###################### PATTERNS ########################
########################################################
# patron (13. Address1)
#ej: <line>            120 Forum Drive           </line>
addressPattern = re.compile(r'<line>\s+(.*?)\s+</line>')

# patron (14. City & 15. StateCode & 16. StoreZip)
#ej: <line>          Columbia, SC 29229          </line>
cityStateZipPattern = re.compile(r'<line>\s+(\w+?),\s([A-Z]{2})\s(\d{5})\s+</line>')

# patron (19. StorePhoneNumber)
#ej: <line>             803-828-6836             </line>
storePhoneNumberPattern = re.compile(r'<line> +([\d-]+) +</line>')

# patron (4. TransactionDate & 5 transactionTime)
#ej: <line>11/13/24 11:02 0276 01 0011 197398    </line><line>(\d{2}/\d{2}/\d{2})[\d|\s|:]+</line>
transactionDateTimePattern = re.compile(r'<line>(\d{2}/\d{2}/\d{2})\s(\d{2}:\d{2})\s\d{2}[\d|\s]+</line>')

# patron (37. itemsSold ) 37, 38, 39, 40, 41, 42, 44 & 45
#ej: <line>        SANTA CRUZ LIME         5.99 B</line>
itemsSoldPattern = re.compile(r'<line>(WT|)\s*(\S(?:.*?\S)?)\s+(\d+\.\d{2})\s(B|F|T)</line>')

# patron (43. QuantitySold)
#ej: <line> 0.75 lb @ 1.79 /lb                   </line>
itemsSoldWeightPattern = re.compile(r'<line>.+?lb\s@\s((?:\d*\.\d{1,2}))\s.+</line>')

# patron (46. DiscountDollarAmount & 49. ItemDiscounts) 
#ej: <line>SC      KRAFT DRESSING          1.29-B</line>
itemDiscountsPattern = re.compile(r'<line>(SC|MC)\s{6}(.*?)\s*(\d+\.\d{2})(-[A-Z])</line>')

# patron INICIO DESCUENTO (no se usa)
#ej: <line> 1 @ 1.29                             </line>
inicio_descuento_pattern = re.compile(r'<line>\s\d\s@\s\d+\.\d{2}\s*</line>')

# pattern (52. TenderTypeDate i. TenderEntryMethod) 
#ej: <line>Contactless                           </line>
tenderEntryMethodPattern = re.compile(r'<line>(CHIP|Contactless|S<line>(WT|)\s*(\S(?:.*?\S)?)\s+(\d+\.\d{2})\s(B|F|T)</line>wiped) +</line>')

# pattern (52. TenderTypeDate ii. TenderType & v. TotalAmount) T
#ej: <line>VF      Debit     USD$         81.08  </line>
tenderTypeAndAmountPattern = re.compile(r'<line>(VF      MasterCd CR|VF      WIC Tender|VF      EBT FS|VF      Debit|        PAYEEZY|        OUTSIDE CREDIT|VF      Visa CR|VF MO   Visa CR|VF      AMEX CR|VF MO   Debit|   MO   CASH|        CASH) +USD\$ +(\d+\.\d{1,2}|\d+) +</line>')

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
displayMessagePattern = re.compile(r'<line> {8}(APPROVED|DECLINED) +</line>')

# patron (53.	FinalTaxLines)
#ej: <line>   **** SC 2% TAX         1.59        </line>
finalTaxLinesPattern = re.compile(r'<line> +(\*{4} (SC|NC) (\d+\.\d{1,2}|\d+)% TAX) +(\d+\.\d{1,2}|\d+) +</line>')

# patron (54. TotalsTransactionData)
#ej: <line>          **** BALANCE         81.08  </line>
totalsTransactionDataPattern = re.compile(r'<line> +\*{4} BALANCE +(\d*\.\d*) +</line>')

# patron (54. TotalsTransactionData ii.	DiscountTotal)
#ej: <line><strong>TODAY'S SAVINGS TOTAL:      6.27      </strong></line>
discountTotalPattern = re.compile(r'<line><strong>TODAY\'S SAVINGS TOTAL: +(\d*\.\d*) +</strong></line>')

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

# inicializacion variables
productMapping  = {}
countryCode = 'US'
storePhoneType = 'Work'
taxType = 'StateOrProvince’'
discountingMethod = 'DollarOff'
taxtype = 'StateOrProvince'
productIdType = 'SKU'
itemReceivedType = 'Pickedup'
tenderEntryMethod = 'Manual' 
tenderType = 'OTHER'
taxDetailNumber = 0

totalTax = 0
descuento = 0
totalVenta = 0    

city = None
stateCode = None
storeZip = None
address1 = None
transactionDate = None
transactionTime = None
storePhoneNumber = None
        
# Ejemplo de cómo podrías mostrar los resultados
# print(f"4. Transaction Date: {transactionDate}")
# print(f"5. Transaction Time: {transactionTime}")
# print(f"13. Address 1: {address1}")
# print(f"14. City: {city}")
# print(f"15. State Code: {stateCode}")
# print(f"16. Store Zip: {storeZip}")
# print(f"17. Country Code: {countryCode}")
# print(f"18. Store Phone Type: {storePhoneType}")
# print(f"19. Store Phone Number: {storePhoneNumber}")
# print("52. Tender Type Date:")
# print(f"     i. Tender Entry Method: {tenderEntryMethod}")
# print(f"     ii. Tender Type: {tenderType}")
# print(f"     iii. Account Number: {accountNumber}")
# print(f"     iv. Auth Code: {authCode}")
# print(f"     v. Total Amount: {tenderAmount}")
# print(f"     vi. Tender Reference: {tenderReference}")
# print("     vii. Payment Response:")
# print(f"          1. Response IDe: {responseID}")
# print(f"          2. Card Type: {cardType}")
# print(f"          3. ISO Res Code: {isoResCode}")
# print(f"          4. Aux Response: {auxResponse}")
# print(f"          5. Response Code: {responseCode}")
# print(f"          6. Response Message: {responseMessage}")
# print(f"          7. Display Message: {displayMessage}")
# print("53. FinalTaxLines:")
# print(f"     ii. Tax Type: {taxtype}")
# print(f"     iii. Tax Amount: {taxAmount}")
# print(f"     iv. Tax Detail Number: {taxDetailNumber}")
# print(f"     v. Tax Percent: {taxPercent}")
# print(f"     vi. Tax Description: {taxDescription}")
# print(f"     vii. Tax Rule Code: {taxRuleCode}")
# print("54. TotalsTransactionData:")
# print(f"     i. Sub Total Amount: {subTotalAmount}")
# print(f"     ii. Discount Total: {discountTotal}")
# print(f"     iii. Discount Total Amount: {discountTotalAmount}")
# print(f"     iv. Total Amount: {totalAmount}")
# print(f"     v.	Change: {change}")
# print('-------------------------------------------------')
# print(f"Total venta: {totalVenta:.2f}")
# print(f"Descuento total: {descuento:.2f}")
# print('-------------------------------------------------')
if __name__ == "__main__":
    receipt_text = sys.argv[1]
    if not receipt_text:
        print("Error: No se proporcionó ningún texto para procesar.")
        sys.exit(1)

    lines = receipt_text.splitlines()
    for i, line in enumerate(lines):
            
        if transactionDateTimeMatch := transactionDateTimePattern.search(line): #Verifica si la línea corresponde al 4. TransactionDate & 5. TransactionTime
            transactionDate = datetime.strptime(transactionDateTimeMatch.group(1), '%m/%d/%y').strftime('%Y-%m-%d')
            transactionTime = datetime.strptime(transactionDateTimeMatch.group(2), '%H:%M').strftime('%H:%M:00')
        
        elif i == 2:
            if addressMatch := addressPattern.search(line): #Verifica si la línea corresponde al 13. address1
                address1 = addressMatch.group(1)

        elif i == 3: 
            if cityStateZipPatternMatch := cityStateZipPattern.search(line): #Verificar si la línea corresponde a 14. City & 15. StateCode & 16. StoreZip
                city = cityStateZipPatternMatch.group(1)
                stateCode = cityStateZipPatternMatch.group(2)
                storeZip = cityStateZipPatternMatch.group(3)
        
        elif i == 4:
            if storePhoneNumberMatch := storePhoneNumberPattern.search(line): #Verificar si la línea corresponde al 19. StorePhoneNumber
                storePhoneNumber = storePhoneNumberMatch.group(1)

        elif itemsSold := itemsSoldPattern.search(line): # Verificar si la línea corresponde a un itemsSold 37, 38, 39, 40, 41, 42, 43, 44 & 45
            quantitySoldType = 'LBS' if itemsSold.group(1) == 'WT' else 'EACH'
            quantitySold = itemsSoldWeightPattern.search(lines[i-1]).group(1) if itemsSold.group(1) == 'WT' else '1'
            description = itemsSold.group(2)
            dollarAmount = float(itemsSold.group(3))
            itemsSoldType = itemsSold.group(4)  # Recuperado sin cambios adicionales

            totalVenta += dollarAmount
            productMapping[description] = dollarAmount

        # elif itemsSold := itemsSoldPattern.search(line): 
        #     #quantitySoldType = quantitySoldTypeMapping.get(itemsSold.group(1), 'EACH')
        #     quantitySoldType = 'EACH'
        #     quantitySold = '1'

        #     if itemsSold.group(1) == 'WT':
        #         quantitySoldType = 'LBS'
        #         line = lines[i-1]
        #         if itemsSoldweightMatch := itemsSoldWeightPattern.search(line):
        #             quantitySold = itemsSoldweightMatch.group(1)

        #     description = itemsSold.group(2)
        #     dollarAmount = float(itemsSold.group(3))
        #     itemsSoldType = itemsSold.group(4)

        #     totalVenta += dollarAmount
        #     productMapping[description] = dollarAmount

            

        elif discount := itemDiscountsPattern.search(line): # Verificar si la línea corresponde a 46. DiscountDollarAmount & 49. ItemDiscounts
            discountReasonCode = discount.group(1)
            discountDescription = discount.group(2)
            discountAmount = discountDollarAmount = float(discount.group(3))
            printLine = discount.group(4)
            
            extDollarAmount = productMapping.get(discountDescription, 0) - discountDollarAmount
            discountPercent = discountDollarAmount / productMapping.get(discountDescription, 0)

            descuento += discountDollarAmount 
            
            print(f"46. Discount Dollar Amount: {discountDollarAmount}")
            print(f"47. Ext Dollar Amount: {extDollarAmount}")
            print(f"49.	ItemDiscounts")
            print(f"     iii. Discount Percent: {discountPercent:.2f}")
            print(f"     iv. Discount Amount: {discountAmount}")
            print(f"     v. Discount Description: {discountDescription}")
            print(f"     vi. Discount Reason Code: {discountReasonCode}")
            print(f"     vii. Discount Ing Method: {discountingMethod}")
            print(f"     viii. PrintLine: {printLine}")
            print(f"46. Discount Dollar Amount: {discountDollarAmount}")
            print(f" ")

        elif tenderEntryMethodMatch := tenderEntryMethodPattern.search(line): #Verifica si la línea corresponde al tender type method 52 i
            tenderEntryMethod = tenderEntryMethodMapping.get(tenderEntryMethodMatch.group(1), 'Manual')

        elif tenderTypeAndAmountMatch := tenderTypeAndAmountPattern.search(line): #Verifica si la línea corresponde al tender type 52 ii & amount v
            tenderType = tenderTypeMapping.get(tenderTypeAndAmountMatch.group(1), 'OTHER')
            tenderAmount = tenderTypeAndAmountMatch.group(2)
        
        elif accountNumberMatch := accountNumberPattern.search(line): #Verifica si la línea corresponde al account number type 52 iii
            accountNumber = accountNumberMatch.group(1)

        elif authCodeMatch := authCodePattern.search(line): #Verifica si la línea corresponde al tender type 52 iV
            authCode = authCodeMatch.group(1)

        elif tenderReferenceMatch := tenderReferencePattern.search(line): #Verifica si la línea corresponde al tender reference 52 vi
            responseID = tenderReference = tenderReferenceMatch.group(1)

        elif cardTypeMatch := cardTypePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 2
            cardType = cardTypeMatch.group(1)

        elif isoResCodeMatch := isoResCodePattern.search(line):
            isoResCode = isoResCodeMatch.group(1)

        elif auxResponseMatch := auxResponsePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 4
            auxResponse = auxResponseMatch.group(1)

        elif responseCodeMatch := responseCodePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 5
            responseCode = responseCodeMatch.group(1)

        elif responseMessageMatch := responseMessagePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 5
            responseMessage = responseMessageMatch.group(1)

        elif displayMessageMatch := displayMessagePattern.search(line): #Verifica si la línea corresponde al tender type 52 vii 7
            displayMessage = displayMessageMatch.group(1)

        elif finalTaxLinesMatch := finalTaxLinesPattern.search(line): #Verificar si la línea corresponde a 53. FinalTaxLines
            taxDetailNumber += 1
            taxDescription = finalTaxLinesMatch.group(1)
            taxRuleCode = finalTaxLinesMatch.group(2)
            taxPercent = finalTaxLinesMatch.group(3)
            taxAmount = finalTaxLinesMatch.group(4)

            totalTax += float(taxAmount)

        elif totalsTransactionDataMatch := totalsTransactionDataPattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData
            totalAmount = totalsTransactionDataMatch.group(1)

            discountTotalAmount = subTotalAmount = float(totalAmount) - totalTax

        elif discountTotalMatch := discountTotalPattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData ii. DiscountTotal
            discountTotal = discountTotalMatch.group(1)

        elif changeMatch := changePattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData v. Change
            change = changeMatch.group(1)

    # Redirige la salida estándar para capturar los prints
    original_stdout = sys.stdout  # Guarda la salida estándar original
    captured_output = StringIO()  # StringIO para capturar el texto
    sys.stdout = captured_output  # Redirige los prints a StringIO

    try:
        # Aquí ejecutamos tu lógica completa que ya tienes con todos los prints
        # Esto capturará exactamente lo que se imprime
        print(f"4. Transaction Date: {transactionDate}")
        print(f"5. Transaction Time: {transactionTime}")
        print(f"13. Address 1: {address1}")
        print(f"14. City: {city}")
        print(f"15. State Code: {stateCode}")
        print(f"16. Store Zip: {storeZip}")
        print(f"17. Country Code: {countryCode}")
        print(f"18. Store Phone Type: {storePhoneType}")
        print(f"19. Store Phone Number: {storePhoneNumber}")
        print("52. Tender Type Date:")
        print(f"     i. Tender Entry Method: {tenderEntryMethod}")
        print(f"     ii. Tender Type: {tenderType}")
        print(f"     iii. Account Number: {accountNumber}")
        print(f"     iv. Auth Code: {authCode}")
        print(f"     v. Total Amount: {tenderAmount}")
        print(f"     vi. Tender Reference: {tenderReference}")
        print("     vii. Payment Response:")
        print(f"          1. Response IDe: {responseID}")
        print(f"          2. Card Type: {cardType}")
        print(f"          3. ISO Res Code: {isoResCode}")
        print(f"          4. Aux Response: {auxResponse}")
        print(f"          5. Response Code: {responseCode}")
        print(f"          6. Response Message: {responseMessage}")
        print(f"          7. Display Message: {displayMessage}")
        print("53. FinalTaxLines:")
        print(f"     ii. Tax Type: {taxtype}")
        print(f"     iii. Tax Amount: {taxAmount}")
        print(f"     iv. Tax Detail Number: {taxDetailNumber}")
        print(f"     v. Tax Percent: {taxPercent}")
        print(f"     vi. Tax Description: {taxDescription}")
        print(f"     vii. Tax Rule Code: {taxRuleCode}")
        print("54. TotalsTransactionData:")
        print(f"     i. Sub Total Amount: {subTotalAmount}")
        print(f"     ii. Discount Total: {discountTotal}")
        print(f"     iii. Discount Total Amount: {discountTotalAmount}")
        print(f"     iv. Total Amount: {totalAmount}")
        print(f"     v.	Change: {change}")
        print('-------------------------------------------------')
        print(f"Total venta: {totalVenta:.2f}")
        print(f"Descuento total: {descuento:.2f}")
        print('-------------------------------------------------')

    finally:
        # Restaura la salida estándar original
        sys.stdout = original_stdout

    # Envía la salida capturada al backend
    print(captured_output.getvalue())