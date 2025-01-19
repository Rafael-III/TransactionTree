from datetime import datetime
import re
import sys
from io import StringIO
import json
from backend.script.db import GetTransaction 
import time

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

# patron (36. TotalAmount)
#ej: <line>          **** BALANCE         81.08  </line>
totalAmountPattern = re.compile(r'<line> +\*{4} BALANCE +(\d*\.\d*) +</line>')

# patron (38. DetailedTransactionDataPattern ) 38, 39, 40, 41, 42, 44 & 45
#ej: <line>        SANTA CRUZ LIME         5.99 B</line>
detailedTransactionDataPattern = re.compile(r'<line>(WT|) +(\S(?:.*?\S)?) +(\d*\.\d{2}) (B|F|T)</line>')

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
productExtDollarAmountMapping = {}

# Static
tTDRVersion = 'TTDRV33' # 1.	TTDRVersion
applicationID = 'Toshiba' # 2.	ApplicationID
locationType = 'purchasepickupLocation' #10.	LocationType
countryCode = 'US' #17.	CountryCode
storePhoneType = 'Work' #18.	StorePhoneType
clerkRole = 'Sale' #23.	ClerkRole
recipientType = 'Recipient' #24.	RecipientType
customerID = '[INSERT_PARTYID]' #30.	CustomerID
SYSTEM_REFERENCE = 'POS_ID' #31.	AlternateIDs a.	CROSS_REFERENCE i.	SYSTEM_REFERENCE
languageSelection = 'eng' #32.	LanguageSelection
currencyType = 'USD' #34.	CurrencyType
outputLanguage = 'eng' #35.	OutputLanguage
productIdType = 'SKU' #39.	ProductIdType
itemReceivedType = 'Pickedup' #44.	ItemReceivedType
discountingMethod = 'DollarOff' #49.	ItemDiscounts vii.	DiscountingMethod
taxType = 'StateOrProvince' #50.	ItemTax ii.	TaxType
attributeType = 'Other' #51.	ItemAttributes a.	Attribute i.	AttributeType
attributeDescription = 'foodstampable' #51.	ItemAttributes a.	Attribute ii.	AttributeDescription
documentType = 'E-RECEIPT' #55.	TransactionDocument a.	Document ii.	DocumentType
documentMediaType = 'HTML' #55.	TransactionDocument a.	Document iv.	DocumentMediaType
mimeContentType = 'text/html' #55.	TransactionDocument a.	Document v.	MimeContentType

# Unknown
merchantNumber = '*** Source unknown' #3.	MerchantNumber
entryType = '*** Source unknown' # 6.	EntryType
transId = '*** Source unknown' #7.	TransId
transactionType = '*** Source unknown' #8.	TransactionType
storeNumber = '*** Source unknown' #9.	StoreNumber
registerNumber = '*** Source unknown' #11.	RegisterNumber
registerType = '*** Source unknown' #12.	RegisterType
clerkIdType = '*** Source unknown' #20.	ClerkIdType
clerkId = '*** Source unknown' #21.	ClerkId
clerkName = '*** Source unknown' #22.	ClerkName
firstName = '*** Source unknown' #25.	FirstName
lastName = '*** Source unknown' #26.	LastName
emailAddress = '*** Source unknown' #27.	EmailAddress
loyaltyCardNumber = '*** Source unknown' #28.	LoyaltyCardNumber
loyaltyLevel = '*** Source unknown' #29.	LoyaltyLevel
SYSTEM_REFERENCE_ID = '*** Source unknown' #31.	AlternateIDs a.	CROSS_REFERENCE ii.	SYSTEM_REFERENCE_ID
rawTextReceipt = '*** Source unknown' #33.	RawTextReceipt
echoData = '*** Source unknown' #52.	TenderTypeDate vii.	PaymentResponse 8.	EchoData
documentName = '*** Source unknown' #55.	TransactionDocument a.	Document i.	DocumentName
documentRefId = '*** Source unknown' #55.	TransactionDocument a.	Document iii.	DocumentRefId
docuCaptureDateTime = '*** Source unknown' #55.	TransactionDocument a.	Document vi.	DocuCaptureDateTime
documentDate = '*** Source unknown' #55.	TransactionDocument a.	Document vii.	DocumentDate

# Other
productId = '*** Transformation unclear' #40.	ProductId
returnAmount = '*** Extraction unclear' #48.	ReturnAmount
discountPercent = '*** Transformation unclear' #49.	ItemDiscounts iii.	DiscountPercent

# print(f"1. TTDR Version: {tTDRVersion}")
# print(f"2. Application ID: {applicationID}")
# print(f"10. Location Type: {locationType}")
# print(f"23. Clerk Role: {clerkRole}")
# print(f"24. Recipient Type: {recipientType}")
# print(f"30. Customer ID: {customerID}")
# print(f"31. Alternate IDs\n     a.CROSS REFERENCE\n          i.SYSTEM REFERENCE: {SYSTEM_REFERENCE}")
# print(f"32. Language Selection: {languageSelection}")
# print(f"34. Currency Type: {currencyType}")
# print(f"35. Output Language: {outputLanguage}")
# print(f"55. Transaction Document\n     a. Document\n          ii. Document Type: {documentType}")
# print(f"          iv. Document Media Type: {documentMediaType}")
# print(f"          v. Mime Content Type: {mimeContentType}")

# print(f"3. Merchant Number: {merchantNumber}")
# print(f"6. Entry Type: {entryType}")
# print(f"7. Trans Id: {transId}")
# print(f"8. Transaction Type: {transactionType}")
# print(f"9. Store Number: {storeNumber}")
# print(f"11. Register Number: {registerNumber}")
# print(f"12. Register Type: {registerType}")
# print(f"20. ClerkId Type: {clerkIdType}")
# print(f"21. Clerk Id: {clerkId}")
# print(f"22. Clerk Name: {clerkName}")
# print(f"25. First Name: {firstName}")
# print(f"26. Last Name: {lastName}")
# print(f"27. Email Address: {emailAddress}")
# print(f"28. Loyalty Card Number: {loyaltyCardNumber}")
# print(f"29. Loyalty Level: {loyaltyLevel}")
# print(f"31. Alternate IDs\n     a.CROSS REFERENCE\n          i.SYSTEM REFERENCE ID: {SYSTEM_REFERENCE_ID}")
# print(f"33. Raw Text Receipt: {rawTextReceipt}")
# print(f"52. Echo Data: {echoData}")
# print(f"55. Transaction Document\n     a. Document\n          i. Document Name: {documentName}")
# print(f"          iii. Document Ref Id: {documentRefId}")
# print(f"          vi. Docu Capture Date Time: {docuCaptureDateTime}")
# print(f"          vii.	Document Date: {documentDate}")

# print(f"40. Product Id: {productId}")
# print(f"48. Return Amount: {returnAmount}")

def ReadTransaction(receipt_text, checkboxes):
        itemSold = 0
        totalDescuento = 0
        taxDetailNumber = 0
        totalTax = 0      

        if not receipt_text:
            print("Error: No se proporcionó ningún texto para procesar.")
            return

        result = {}  # Diccionario para almacenar los resultados según las reglas

        lines = receipt_text.splitlines()
        try:
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

                elif detailedTransactionData := detailedTransactionDataPattern.search(line): # Verificar si la línea corresponde a un itemsSold 37, 38, 39, 40, 41, 42, 43, 44 & 45
                    quantitySoldType = 'LBS' if detailedTransactionData.group(1) == 'WT' else 'EACH'
                    quantitySold = itemsSoldWeightPattern.search(lines[i-1]).group(1) if detailedTransactionData.group(1) == 'WT' else '1'
                    description = detailedTransactionData.group(2)
                    dollarAmount = float(detailedTransactionData.group(3))
                    taxFlag = detailedTransactionData.group(4)

                    itemSold += dollarAmount
                    productMapping[description] = dollarAmount

                    # Asegurarse de que "itemsSold" sea una lista
                    if "detailedTransactionData" not in result:
                        result["detailedTransactionData"] = []

                    # Agregar el producto a la lista
                    result["detailedTransactionData"].append({
                        "description": description,
                        "quantitySoldType": quantitySoldType,
                        "quantitySold": quantitySold,
                        "dollarAmount": dollarAmount,
                        "taxFlag": taxFlag
                    })

                elif discount := itemDiscountsPattern.search(line): # Verificar si la línea corresponde a 46. DiscountDollarAmount & 49. ItemDiscounts
                    discountReasonCode = discount.group(1)
                    discountDescription = discount.group(2)
                    discountAmount = discountDollarAmount = float(discount.group(3))
                    printLine = discount.group(4)
                    
                    extDollarAmount = productMapping.get(discountDescription, 0) - discountDollarAmount
                    productExtDollarAmountMapping[discountDescription] = extDollarAmount

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

                elif finalTaxLinesMatch := finalTaxLinesPattern.search(line): #Verificar si la línea corresponde 53. FinalTaxLines
                    taxDetailNumber += 1
                    taxDescription = finalTaxLinesMatch.group(1)
                    taxRuleCode = finalTaxLinesMatch.group(2)
                    taxPercent = finalTaxLinesMatch.group(3)
                    taxAmount = finalTaxLinesMatch.group(4)

                    totalTax += float(taxAmount)

                    if "itemTax" not in result:
                        result["itemTax"] = []

                    for item in result["detailedTransactionData"]:
                        dollarAmount = float(item["dollarAmount"])
                        taxAmount = round(dollarAmount * (float(taxPercent) / 100), 2)

                        result["itemTax"].append({
                            "taxAmount": taxAmount,
                            "taxFlag": item["taxFlag"],
                            "taxPercent": taxPercent,
                            "taxDescription": taxDescription,
                            "taxAuthority": taxRuleCode,
                            "taxableAmount": productExtDollarAmountMapping.get(item["description"], dollarAmount)
                        })

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

            
            print(f"1. TTDR Version: {tTDRVersion}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"2. Application ID: {applicationID}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"3. Merchant Number: {merchantNumber}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"4. Transaction Date: {result.get('transactionDate', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"5. Transaction Time: {result.get('transactionTime', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"6. Entry Type: {entryType}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"7. Trans Id: {transId}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"8. Transaction Type: {transactionType}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"9. Store Number: {storeNumber}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"10. Location Type: {locationType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"11. Register Number: {registerNumber}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"12. Register Type: {registerType}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"13. Address 1: {result.get('address1', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"14. City: {result.get('city', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"15. State Code: {result.get('stateCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"16. Store Zip: {result.get('storeZip', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"17. Country Code: {countryCode}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"18. Store Phone Type: {storePhoneType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"19. Store Phone Number: {result.get('storePhoneNumber', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"20. ClerkId Type: {clerkIdType}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"21. Clerk Id: {clerkId}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"22. Clerk Name: {clerkName}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"23. Clerk Role: {clerkRole}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"24. Recipient Type: {recipientType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"25. First Name: {firstName}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"26. Last Name: {lastName}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"27. Email Address: {emailAddress}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"28. Loyalty Card Number: {loyaltyCardNumber}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"29. Loyalty Level: {loyaltyLevel}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"30. Customer ID: {customerID}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            
            print(f"31. Alternate IDs\n     a.CROSS REFERENCE") if not (checkboxes.get('withoutStaticDataCheckbox', True) and checkboxes.get('withoutUnknownDataCheckbox', True)) else None
            print(f"          i.SYSTEM REFERENCE: {SYSTEM_REFERENCE}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"          i.SYSTEM REFERENCE ID: {SYSTEM_REFERENCE_ID}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            
            print(f"32. Language Selection: {languageSelection}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"33. Raw Text Receipt: {rawTextReceipt}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"34. Currency Type: {currencyType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"35. Output Language: {outputLanguage}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"36. Total Amount: {result.get('totalAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"36. Items Soldt: {itemSold}") if checkboxes.get('extractDataCheckbox', True) else None
            
            if "detailedTransactionData" in result and (checkboxes.get('extractDataCheckbox', True) or not checkboxes.get('withoutStaticDataCheckbox', True)):
                for id, item in enumerate(result["detailedTransactionData"], start=1):
                    print(f"38. detailedTransactionData {id}:")
                    print(f"     39. Product Id Type: {productIdType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     40. Product Id: {productId}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     41. Description: {item.get('description', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     42. Quantity Sold Type: {item.get('quantitySoldType', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     43. Quantity Sold: {item.get('quantitySold', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     44. Item Received Type: {itemReceivedType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     45. Dollar Amount: {item.get('dollarAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            # else:
            #     print(f"38. Detailed Transaction Data: *** Not found")

            if "discount" in result:
                for id, item in enumerate(result["discount"], start=1):
                    #print(f"46. Discounts {id}:")
                    print(f"46. Discount Dollar Amount: {item.get('discountDollarAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"47. Ext Dollar Amount: {item.get('extDollarAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"48. Return Amount: {item.get('extDollarAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"49. Item Discounts") if checkboxes.get('extractDataCheckbox', True) or not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     iii. Discount Percent: {item.get('discountPercent', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     iv. Discount Amount: {item.get('discountAmount', '*** Not found'):.2f}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     v. Discount Description: {item.get('discountDescription', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     vi. Discount Reason Code: {item.get('discountReasonCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     vii. Discounting Method: {discountingMethod}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     viii. PrintLine: {item.get('printLine', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            else:
                print(f"46. Discounts: *** Not implemented")
            
            if "itemTax" in result and (checkboxes.get('extractDataCheckbox', True) or not checkboxes.get('withoutStaticDataCheckbox', True)):
                for id, item in enumerate(result["itemTax"], start=1):
                    print(f"50. Item Tax {id}:")
                    print(f"     ii. Tax Type: {taxType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     iii. Tax Amount: {item.get('taxAmount', '*** Not found'):.2f}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     iv. Tax Flag: {item.get('taxFlag', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     v. Tax Percent: {item.get('taxPercent', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     vi. Tax Description: {item.get('taxDescription', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     vii. Tax Authority: {item.get('taxAuthority', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     viii. Taxable Amount: {item.get('taxableAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            # else:
            #     print(f"50. Item Tax: *** Not implemented")
            
            if "detailedTransactionData" in result and not (checkboxes.get('withoutStaticDataCheckbox', True)):
                for id, item in enumerate(result["detailedTransactionData"], start=1):
                    print(f"51. Detailed TransactionData {id}:")
                    print(f"     i. Attribute Type: {attributeType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     ii. Attribute Description: {attributeDescription}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
                    print(f"     iii. AttributeData: {'true' if item.get('taxFlag') in ['B', 'F'] else 'false'}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            # else:
            #     print(f"51 Item Attributes: *** Not found")
        
            print("52. Tender Type Date:") if checkboxes.get('extractDataCheckbox', True) or not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"     i. Tender Entry Method: {result.get('tenderEntryMethod', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"     ii. Tender Type: {result.get('tenderType', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"     iii. Account Number: {result.get('accountNumber', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"     iv. Auth Code: {result.get('authCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"     v. Total Amount: {result.get('tenderAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"     vi. Tender Reference: {result.get('tenderReference', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print("     vii. Payment Response:") if checkboxes.get('extractDataCheckbox', True) or not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"          1. Response IDe: {result.get('tenderReference', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          2. Card Type: {result.get('cardType', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          3. ISO Res Code: {result.get('isoResCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          4. Aux Response: {result.get('auxResponse', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          5. Response Code: {result.get('responseCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          6. Response Message: {result.get('responseMessage', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          7. Display Message: {result.get('displayMessage', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            print(f"          8. Echo Data: {echoData}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            
            if "finalTaxLines" in result and checkboxes.get('extractDataCheckbox', True):
                for id, item in enumerate(result["finalTaxLines"], start=1):
                    print(f"53. FinalTaxLines {id}:")
                    print(f"     i. Tax Amount: {item.get('taxAmount', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     ii. Tax Percent: {item.get('taxPercent', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     iii. Tax Description: {item.get('taxDescription', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     iv. Tax Detail Number: {item.get('taxDetailNumber', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
                    print(f"     v. Tax Rule Code: {item.get('taxRuleCode', '*** Not found')}") if checkboxes.get('extractDataCheckbox', True) else None
            
            if checkboxes.get('extractDataCheckbox', True):
                print("54. Totals Transaction Data:")
                print(f"     i. Sub Total Amount: {result.get('totalAmount', 0)} - {(totalTax):.2f} = {(float(result.get('totalAmount', 0)) - totalTax):.2f}")
                print(f"     ii. Discount Total: {result.get('discountTotal', '*** Not found')}")
                print(f"     iii. Discount Total Amount: {(float(result.get('totalAmount', 0)) - totalTax):.2f}")
                print(f"     iv. Total Amount: {result.get('totalAmount', '*** Not found')}")
                print(f"     v. Change: {result.get('change', '*** Not found')}")
            
            print(f"55. Transaction Document") if not (checkboxes.get('withoutStaticDataCheckbox', True) and checkboxes.get('withoutUnknownDataCheckbox', True)) else None
            print(f"          i. Document Name: {documentName}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"          ii. Document Type: {documentType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"          iii. Document Ref Id: {documentRefId}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"          iv. Document Media Type: {documentMediaType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"          v. Mime Content Type: {mimeContentType}") if not checkboxes.get('withoutStaticDataCheckbox', True) else None
            print(f"          vi. Docu Capture Date Time: {docuCaptureDateTime}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            print(f"          vii.	Document Date: {documentDate}") if not checkboxes.get('withoutUnknownDataCheckbox', True) else None
            
            # print('\n\n-------------------------------------------------')
            # print(f"Total venta: {itemSold:.2f}")
            # print(f"Descuento total: {totalDescuento:.2f}")
            # print('-------------------------------------------------')
            # for id, (description, dollarAmount) in enumerate(productMapping.items(), start=1):
            #     print(f"FinalTaxLines {id}: {description} {dollarAmount}")
        except Exception as e:
            print(f"Error general en ReadTransaction: {str(e)}")

if __name__ == "__main__":
    output_file = "output.txt"
    qty = 100

    original_stdout = sys.stdout  
    captured_output = StringIO() 
    sys.stdout = captured_output 

    checkboxes_json = sys.argv[2] 
    mode = sys.argv[3]
    
    checkboxes = json.loads(checkboxes_json) 
    
    try: 
        if mode == 'onlyOne':
            receipt_text = sys.argv[1]
            
            start_processing = time.time()
            print(f"*******************************************************************")
            print(f"                        TRANSACTION id: N?A                        ")
            print(f"*******************************************************************")
            result = ReadTransaction(receipt_text, checkboxes)  
            end_processing = time.time()  

            print(f"*******************************************************************")
            print(f"                               TIMES                               ")
            print(f"*******************************************************************")
            processing_time = end_processing - start_processing
            print(f"Record processing time: {processing_time:.3f} seconds")
            
        elif mode == 'database':  
            start_db = time.time()
            data = GetTransaction(qty)  # Llama a la función para traer los registros
            end_db = time.time()

            start_processing = time.time()
            for item in data:
                if '<line>' in item['param_value']:
                    print(f"*******************************************************************")
                    print(f"                         TRANSACTION id: {item['id']}              ")
                    print(f"*******************************************************************")
                    result = ReadTransaction(item['param_value'], checkboxes)   
            
            print(f"*******************************************************************")
            print(f"                               TIMES                               ")
            print(f"*******************************************************************")
            db_time = end_db - start_db
            print(f"Database reading time: {db_time:.3f} seconds")
            processing_time = end_processing - start_processing
            print(f"Record processing time: {processing_time:.3f} seconds")
            end_processing = time.time()  

    finally:
        sys.stdout = original_stdout

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(captured_output.getvalue())
    print(captured_output.getvalue())
