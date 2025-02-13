from datetime import datetime
import re
import sys
from io import StringIO
import json
from backend.script.db import Database
import time
import logging

db = Database()

logging.basicConfig(filename="missing_data.log", level=logging.WARNING, format="%(asctime)s - %(message)s")

########################################################
###################### PATTERNS ########################
########################################################
# patron (4. TransactionDate & 5 transactionTime)
#ej: <line>11/13/24 11:02 0276 01 0011 197398    </line><line>(\d{2}/\d{2}/\d{2})[\d|\s|:]+</line>
#transactionDateTimePattern = re.compile(r'<line>(\d{1,2}/\d{1,2}/\d{2,4})\s(\d{2}:\d{2})\s\d{2}[\d|\s]+</line>')
transactionDateTimePattern = re.compile(r'<line> *(\d{1,2}/\d{1,2}/\d{2,4}) +(\d{2}:\d{2}) +\d{2}.*</line>')

# patron (??. Name)
#ej: <line>    Family-Owned &amp; Carolinas-Based    </line>
namePattern = re.compile(r'<line>\s+(.*?) +</line>')

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
totalAmountPattern = re.compile(r'<line> +\*{4} BALANCE +([\d,]*\.\d{2}-?) +</line>')

# patron (38. DetailedTransactionDataPattern ) 38, 39, 40, 41, 42, 44 & 45
#ej: <line>        SANTA CRUZ LIME         5.99 B</line>
detailedTransactionDataPattern = re.compile(r'<line>(WT|) +(\S(?:.*?\S)?) +(\d*\.\d{2}) (B|F|T)</line>')
#detailedTransactionDataPattern = re.compile(r'<line>(MR) +(PICKUP FEE) +(\d*\.\d{2}) *</line>|<line>(WT|) +(\S(?:.*?\S)?) +(\d*\.\d{2}) (B|F|T)</line>')

# patron (38. DetailedTransactionDataPatternAUX ) 38, 39, 40, 41, 42, 44 & 45
#ej: <line>MR      PICKUP FEE              4.95  </line>
detailedTransactionDataPatternAUX = re.compile(r'<line>(MR) +(PICKUP FEE) +(\d*\.\d{2}) *</line>')

# patron (43. QuantitySold)
#ej: <line> 0.75 lb @ 1.79 /lb                   </line>
itemsSoldWeightPattern = re.compile(r'<line>.+?lb @ ((?:\d*\.\d{1,2})) .+</line>')

# patron (46. DiscountDollarAmount & 49. ItemDiscounts) 
#ej: <line>SC      KRAFT DRESSING          1.29-B</line>
#    <line>CL      PORK BONELESS           4.85-B</line>
#    <line>SC MO   GROCERY                  .75 B</line>
itemDiscountsPattern = re.compile(r'<line> *(SC|MC|MP|CL|[A-Z]{2})[A-Z ]{6}(.*?) *(\d*\.\d{2}) *(-?[BFT])</line>')
# itemDiscountsPattern = re.compile(r'<line> *(SC|MC|MP|CL|[A-Z]{2})[A-Z ]{6}(.*?) *(\d*\.\d{2})(-(?:[A-Z]| ))</line>')
#itemDiscountsPattern = re.compile(r'<line> *(?:SC|MC|MP|CL|[A-Z]{2})\s{6}(?:.*?) *(\d*\.\d{2})(?:-[A-Z])</line>')

# patron INICIO DESCUENTO (no se usa)
#ej: <line> 1 @ 1.29                             </line>
inicio_descuento_pattern = re.compile(r'<line> +\d\s@\s\d+\.\d{2}\s*</line>')

# pattern (52. TenderTypeDate i. TenderEntryMethod) 
#ej: <line>Contactless                           </line>
tenderEntryMethodPattern = re.compile(r'<line> *(CHIP|Contactless|Swiped) +</line>')

# pattern (52. TenderTypeDate ii. TenderType & v. TotalAmount) T
#ej: <line>VF      Debit     USD$         81.08  </line>
tenderTypeAndAmountPattern = re.compile(r'<line>.*?(?:<strong> )?(VF      MasterCd CR|VF      WIC Tender|VF      EBT FS|VF      Debit|        PAYEEZY|        OUTSIDE CREDIT|VF      Visa CR|VF MO   Visa CR|VF      AMEX CR|VF MO   Debit|   MO   CASH|        CASH|VF      Gift Card|VF MO   Gift Card|VF MO   EBT FS) +(?:USD\$)? +(\d*\.\d{1,2}|\d+) *(?:</strong>)?.*?</line>')

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
displayMessagePattern = re.compile(r'<line> *(APPROVED|DECLINED) +</line>')

# patron (53.	FinalTaxLines)
#ej: <line>   **** SC 2% TAX         1.59        </line>
#    <line>   **** NC 7% SALES TAX   9.19        </line>
#    <line>   **** NC 7% SALES TAX   -.16        </line>
finalTaxLinesPattern1 = re.compile(r'<line> +(\*{4} (SC|NC) (\d*\.\d{1,2}|\d+)% (?:[\w\s]+?)) +(-?\d*\.\d{1,2}|-?\d+) +</line>')
#finalTaxLinesPattern1 = re.compile(r'<line> +(\*{4} (SC|NC) (\d*\.\d{1,2}|\d+)% (?:[\w\s]+?)) +(\d*\.\d{1,2}|\d+) +</line>')
#    <line>   **** 2% NC TAX         5.28        </line>
#    <line>   **** 2% NC TAX         -.28        </line>
finalTaxLinesPattern2 = re.compile(r'<line> +(\*{4} (\d*\.\d{1,2}|\d+)% (SC|NC) (?:[\w\s]+?)) +(-?\d*\.\d{1,2}|-?\d+) +</line>')
# finalTaxLinesPattern2 = re.compile(r'<line> +(\*{4} (\d*\.\d{1,2}|\d+)% (SC|NC) (?:[\w\s]+?)) +(\d*\.\d{1,2}|\d+) +</line>')

# patron (54. TotalsTransactionData ii.	DiscountTotal)
#ej: <line><strong>TODAY'S SAVINGS TOTAL:      6.27      </strong></line>
savingTotalPattern = re.compile(r'<line> *<strong>TODAY\'S SAVINGS TOTAL: +(\d*\.\d*) +</strong> *</line>')

# patron (54. TotalsTransactionData v.	Change)
#ej: <line>        CHANGE                   .00  </line>
changePattern = re.compile(r'<line> +CHANGE +(\d*\.\d*) +</line>')

# patron (55. customer i. Name)
#ej: <line>                      Name: James                           </line>
customerNamePattern = re.compile(r'<line> *Name: *(.*?) +</line>')

# patron (55. customer ii. Account)
#ej: <line>                      Account: XXXXXXX6788                  </line>
customerAccountPattern = re.compile(r'<line> *Account: *(.*?) +</line>')

# patron (55. customer iii. Earnings This Transaction)
#ej: <line>                      Earnings This Transaction: 0.00       </line>
customerEarningsPattern = re.compile(r'<line> *Earnings This Transaction: *(\d*\.\d*) +</line>')

# patron (55. customer iv. Current Gas Rewards Balance)
#ej: <line>                      Current Gas Rewards Balance: 0.00       </line>
customerRewardsBalancePattern = re.compile(r'<line> *Current Gas Rewards Balance: *(\d*\.\d*) +</line>')

# patron (55. customer v. Spend To Get Your Next Reward)
#ej: <line>                      Spend To Get Your Next Reward: 0.00       </line>
customerNextRewardPattern = re.compile(r'<line> *Spend To Get Your Next Reward: *(\d*\.\d*) +</line>')

# patron (55. customer vi. rewards card)
#ej: <line>                      YOUR REWARDS CARD #XXXXXXX6788        </line>
customerRewardsCardPattern = re.compile(r'<line> *YOUR REWARDS CARD *(.*?) +</line>')

# patron (55. customer vii. Expiring On)
#ej: <line>                      Expiring On: 02/06/2021               </line>
customerExpiringPattern = re.compile(r'<line> *Expiring On: *(\d+/\d+/\d+) +</line>')

# patternB = r"<line>.*?(\d*\.\d{2}) (?:B|F|T)</line>"
# pattern_B = r"<line>.*?(\d*\.\d{2})-(?:B|F|T)</line>"

########################################################
###################### MAPPING #########################
########################################################
quantitySoldTypeMapping = {
    'WT': 'LBS'
}

tenderEntryMethodMapping = {
    'CHIP': 'IntegratedChipCard',
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
    '        CASH': 'CASH',
    'VF      Gift Card': 'GIFT CARD',
    'VF MO   Gift Card': 'GIFT CARD',
    #'VF MO   EBT FS' : '??????????'
}

########################################################
############ INICIALIZACION DE VARIABLES ###############
########################################################
error = []

result = {}
productMapping  = {}
productExtDollarAmountMapping = {}
tenderMapping  = {}

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
    
def ReadTransaction(trasnsaction, checkboxes, idTrasaccionOriginal):
    found_name = found_address = False
    item_data = {"item": []} 
    itemSold = 0
    discount_data = {"discount": []} 
    total_discount = 0
    taxDetailNumber = 0
    tax_data = {"tax": []} 
    total_tax = 0
    tender_data = {"tender": []} 
    total_tender = 0
    tender_wic = False
    error = []

    store_data = {}
    totalAmount = 0.0
    change = None
    savingTotal = None
    transactionDate = None
    transactionTime = None
    customerName = None
    customerAccount = None
    customerEarnings = None
    customerRewardsBalance = None
    customerNextReward = None
    customerRewardsCard = None
    customerExpiring = None

    balanceCorrect = True
    tenderCorrect = True
    
    trasnsaction = trasnsaction.replace("&amp;", "&")
    lines = trasnsaction.splitlines()
    
    try:
        for line_index, line in enumerate(lines):

            #---------------------------- START STORE ----------------------------------
            if not found_name and (nameMatch := namePattern.search(line)):  
                store_data["name"] = nameMatch.group(1)
                found_name = True
            elif not found_address and (addressMatch := addressPattern.search(line)): #Verifica si la línea corresponde al 13. address1
                store_data["address"] = addressMatch.group(1)
                found_address = True
            elif cityStateZipPatternMatch := cityStateZipPattern.search(line): #Verificar si la línea corresponde a 14. City & 15. StateCode & 16. StoreZip
                store_data["city"] = cityStateZipPatternMatch.group(1)
                store_data["stateCode"] = cityStateZipPatternMatch.group(2)
                store_data["storeZip"] = cityStateZipPatternMatch.group(3)
            elif storePhoneNumberMatch := storePhoneNumberPattern.search(line): #Verificar si la línea corresponde al 19. StorePhoneNumber
                store_data["storePhoneNumber"] = storePhoneNumberMatch.group(1)
            #----------------------------- END STORE ------------------------------------

            #---------------------------- START PRODUCT ---------------------------------
            elif detailedTransactionData := detailedTransactionDataPattern.search(line): # Verificar si la línea corresponde a un itemsSold 37, 38, 39, 40, 41, 42, 43, 44 & 45
                quantitySoldType = 'LBS' if detailedTransactionData.group(1) == 'WT' else 'EACH'
                quantitySold = itemsSoldWeightPattern.search(lines[line_index-1]).group(1) if detailedTransactionData.group(1) == 'WT' else '1'
                description = detailedTransactionData.group(2)
                dollarAmount = float(detailedTransactionData.group(3))
                taxFlag = detailedTransactionData.group(4)

                itemSold += dollarAmount
                productMapping[description] = dollarAmount

                item = {
                    "description": description,
                    "quantitySoldType": quantitySoldType,
                    "quantitySold": quantitySold,
                    "dollarAmount": dollarAmount,
                    "taxFlag": taxFlag
                }

                item_data["item"].append(item)
            
            elif detailedTransactionData := detailedTransactionDataPatternAUX.search(line): # Verificar si la línea corresponde a un itemsSold 37, 38, 39, 40, 41, 42, 43, 44 & 45
                quantitySoldType = detailedTransactionData.group(1)
                quantitySold = '1'
                description = detailedTransactionData.group(2)
                dollarAmount = float(detailedTransactionData.group(3))
                taxFlag = ''

                itemSold += dollarAmount
                productMapping[description] = dollarAmount

                item = {
                    "description": description,
                    "quantitySoldType": quantitySoldType,
                    "quantitySold": quantitySold,
                    "dollarAmount": dollarAmount,
                    "taxFlag": taxFlag
                }

                item_data["item"].append(item)

            elif discount := itemDiscountsPattern.search(line): # Verificar si la línea corresponde a 46. DiscountDollarAmount & 49. ItemDiscounts
                discountReasonCode = discount.group(1)
                discountDescription = discount.group(2)
                discountAmount = discountDollarAmount = float(discount.group(3))
                printLine = discount.group(4)
                
                #hay descuentos que no son negativos
                if "-" not in printLine:
                    discountAmount = discountDollarAmount = -abs(discountAmount)

                if(discountReasonCode == 'SC' or discountReasonCode == 'CL' or discountReasonCode == 'RF'):
                    discountPercent = round(discountDollarAmount / productMapping.get(discountDescription,1), 2)
                    
                    extDollarAmount = productMapping.get(discountDescription,0) - discountDollarAmount
                    productExtDollarAmountMapping[discountDescription] = extDollarAmount #arreglo de descuentos por nombre de producto
                # elif(discountReasonCode == 'MC'):
                #     discountPercent = "N/A"
                #     extDollarAmount = "N/A"
                # elif(discountReasonCode == 'MP'):
                #     discountPercent = "N/A"
                #     extDollarAmount = "N/A"
                else:
                    discountPercent = 0.0
                    extDollarAmount = 0.0

                total_discount += discountDollarAmount

                discount = {
                    "discountDollarAmount": discountDollarAmount,
                    "extDollarAmount": extDollarAmount,
                    "discountPercent": discountPercent,
                    "discountAmount": discountAmount,
                    "discountDescription": discountDescription,
                    "discountReasonCode": discountReasonCode,
                    "printLine": printLine     
                }

                discount_data["discount"].append(discount)
            #----------------------------- END PRODUCT ----------------------------------

            #------------------------------- START TAX ----------------------------------
            elif (finalTaxLinesMatch := finalTaxLinesPattern1.search(line)) or (finalTaxLinesMatch := finalTaxLinesPattern2.search(line)): #Verificar si la línea corresponde 53. FinalTaxLines
                taxDetailNumber += 1
                taxDescription = finalTaxLinesMatch.group(1)
                taxRuleCode = finalTaxLinesMatch.group(2) if finalTaxLinesMatch.group(2).isalpha() else finalTaxLinesMatch.group(3)
                taxPercent = finalTaxLinesMatch.group(2) if finalTaxLinesMatch.group(2).isnumeric() else finalTaxLinesMatch.group(3)
                taxAmount = finalTaxLinesMatch.group(4)

                total_tax += float(taxAmount) 
                
                tax = {
                    "taxAmount": taxAmount,
                    "taxPercent": taxPercent,
                    "taxDescription": taxDescription,
                    "taxDetailNumber": taxDetailNumber,
                    "taxRuleCode": taxRuleCode,
                }

                tax_data["tax"].append(tax)
            #-------------------------------- END TAX -----------------------------------

            #----------------------------- START BALANCE ---------------------------------
            elif totalAmountMatch := totalAmountPattern.search(line): #Verifica si la línea corresponde 36. TotalAmount
                totalAmount = totalAmountMatch.group(1).replace(',', '')
                if totalAmount.endswith("-"):
                    totalAmount =  -float(totalAmount[:-1]) 
                else:
                    totalAmount = float(totalAmount)
            #------------------------------ END BALANCE ----------------------------------

            #------------------------------ START TENDER ---------------------------------
            elif tenderTypeAndAmountMatch := tenderTypeAndAmountPattern.search(line):  
                tenderType = tenderTypeMapping.get(tenderTypeAndAmountMatch.group(1), 'OTHER')
                tenderAmount = tenderTypeAndAmountMatch.group(2)

                total_tender += float(tenderAmount) 
                if(tenderType == 'WICCheck'):
                    tender_wic = True
                            
                new_tender = {
                    "tenderType": tenderType,
                    "tenderAmount": tenderAmount
                }

                if "tender" not in tender_data:
                    tender_data["tender"] = []  # Si no existe la lista, la creamos

                tender_data["tender"].append(new_tender)  # Agregamos el nuevo pago

            # No dependemos de un pago previo, cada campo se agrega si aparece en la entrada
            if tenderEntryMethodMatch := tenderEntryMethodPattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]  # Si no hay pagos, inicializamos con un diccionario vacío

                tender_data["tender"][-1]["tenderEntryMethod"] = tenderEntryMethodMapping.get(tenderEntryMethodMatch.group(1), 'Manual')

            if accountNumberMatch := accountNumberPattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["accountNumber"] = accountNumberMatch.group(1)

            if authCodeMatch := authCodePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["authCode"] = authCodeMatch.group(1)

            if tenderReferenceMatch := tenderReferencePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["tenderReference"] = tenderReferenceMatch.group(1)

            if cardTypeMatch := cardTypePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["cardType"] = cardTypeMatch.group(1)

            if isoResCodeMatch := isoResCodePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["isoResCode"] = isoResCodeMatch.group(1)

            if auxResponseMatch := auxResponsePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["auxResponse"] = auxResponseMatch.group(1)

            if responseCodeMatch := responseCodePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["responseCode"] = responseCodeMatch.group(1)

            if responseMessageMatch := responseMessagePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["responseMessage"] = responseMessageMatch.group(1)

            if displayMessageMatch := displayMessagePattern.search(line):  
                if "tender" not in tender_data or not tender_data["tender"]:  
                    tender_data["tender"] = [{}]

                tender_data["tender"][-1]["displayMessage"] = displayMessageMatch.group(1)
            #------------------------------- END TENDER ----------------------------------

            #------------------------------ START CHANGE ---------------------------------
            elif changeMatch := changePattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData v. Change
                change = changeMatch.group(1)
            #-------------------------------- END CHANGE ---------------------------------

            #------------------------------ START REWARD ---------------------------------
            elif savingTotalMatch := savingTotalPattern.search(line): #Verifica si la línea corresponde 54. TotalsTransactionData ii. DiscountTotal
                savingTotal = savingTotalMatch.group(1)
            #------------------------------- END REWARD ----------------------------------

            #------------------------------ START CUSTOMER ---------------------------------
            elif  customerNameMatch := customerNamePattern.search(line):  # Verifica si la línea corresponde 55. customer i. Name
                customerName =  customerNameMatch.group(1)

            elif  customerAccountMatch :=  customerAccountPattern.search(line):  # Verifica si la línea corresponde 55. customer ii. Account
                customerAccount =  customerAccountMatch.group(1)

            elif  customerEarningsMatch :=  customerEarningsPattern.search(line):  # Verifica si la línea corresponde 55. customer iii. Earnings
                customerEarnings =  customerEarningsMatch.group(1)

            elif customerRewardsBalanceMatch := customerRewardsBalancePattern.search(line):  # Verifica si la línea corresponde 55. customer iv. Rewards Balance
                customerRewardsBalance = customerRewardsBalanceMatch.group(1)

            elif customerNextRewardMatch := customerNextRewardPattern.search(line):  # Verifica si la línea corresponde 55. customer v. Next Reward
                customerNextReward = customerNextRewardMatch.group(1)

            elif customerRewardsCardMatch := customerRewardsCardPattern.search(line):  # Verifica si la línea corresponde 55. customer vi. Rewards Card
                customerRewardsCard = customerRewardsCardMatch.group(1)

            elif customerExpiringMatch := customerExpiringPattern.search(line):  # Verifica si la línea corresponde 55. customer vii. Expiring
                customerExpiring = customerExpiringMatch.group(1)
            #------------------------------ END CUSTOMER ---------------------------------

            #------------------------------ START DATE --------------------------------
            elif transactionDateTimeMatch := transactionDateTimePattern.search(line): #Verifica si la línea corresponde al 4. TransactionDate & 5. TransactionTime
                transactionDate = datetime.strptime(transactionDateTimeMatch.group(1), '%m/%d/%y').strftime('%Y-%m-%d')
                transactionTime = datetime.strptime(transactionDateTimeMatch.group(2), '%H:%M').strftime('%H:%M:00')
            #------------------------------- END DATE ---------------------------------
        #-> Termina el for (lectura de la transaccion)

    #------------------------------ START ERROR -------------------------------
    
        idClient = None
        isComplete = True

        #se crea el registro de la trasaccion para empezar a almacenar los valores
        idtransactionSource = db.InsertTransactionSource('2024-02-12 14:30:00', 'TXN123456test', 'TEST', 'TEST', trasnsaction, idTrasaccionOriginal)
        idtransaction = db.InsertTransaction(None, None, None, None, None, datetime.now(), False, None, idtransactionSource)

        # Validamos si totalAmount está vacío o no 
        print("===================")
        print("===== BALANCE =====")
        print("===================")
        if totalAmount in [None, ""]:
            isComplete = False 
            
            error_message = "The BALANCE value could not be extracted"
            
            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return  
        else:
            balanceCalculed = round((itemSold - total_discount) + float(total_tax), 2)
            if(float(totalAmount) != balanceCalculed):
                isComplete = False 
            
                error_message = f"The extracted sales amount {(itemSold):.2f} - discounts {(total_discount):.2f} + taxes {(total_tax):.2f} = {balanceCalculed} does not match the extracted balance {totalAmount}."
                
                db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

                print(error_message)

                error_log = {
                    "transaction_id": idTrasaccionOriginal,
                    "error_type": "MISSING_FIELD",
                    "error_detail": error_message,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                return
            else:
                print(f"> {totalAmount}")

        # Validamos si el bloque de tender_data está vacío o no  y si lo pagado es igual al balance
        print("==================")
        print("===== TENDER =====")
        print("==================")
        if "tender" not in tender_data or not tender_data["tender"] or "tenderType" not in tender_data["tender"][0]:
            isComplete = False  # Marcar la transacción como incompleta

            error_message = "No tender was extracted from the tender_data block"
            
            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            print(f"> tender {(total_tender):.2f} (calculado) =? balance {totalAmount} (extraido)")

            if float(total_tender) != float(totalAmount):
                print(f"{tender_wic}> tender {tender_wic}: total tender {(total_tender):.2f} (calculado) =? balance {(totalAmount):.2f} (extraído) - tax {(total_tax):.2f}")
                
                if (tender_wic and float(total_tender) != (float(totalAmount) - float(total_tax))):
                    print(f">>>>> Error: Data TENDER extraction failed1")
                    
                    error_message = f"The calculated amount of the WIC tender {(total_tender):.2f} != the extracted balance {(totalAmount):.2f} - tax {(total_tax):.2f}, they do not match"
                elif not tender_wic:
                    print(f">>>>> Error: Data TENDER extraction failed2")

                    error_message = f"The calculated amount of the tenders {(total_tender):.2f} != the extracted balance {totalAmount}, they do not match"

                db.Insert_nn_Error_Transaction(2, idtransaction, error_message)

                error_log = {
                    "transaction_id": idTrasaccionOriginal,
                    "error_type": "VALUE_MISMATCH",
                    "error_detail": error_message,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                return
            else:
                for idx, tender in enumerate(tender_data["tender"], start=1):
                    db.InsertTender(
                        tender["tenderType"], 
                        tender["tenderAmount"],
                        tender.get("tenderEntryMethod", None),  
                        tender.get("accountNumber", None),
                        tender.get("authCode", None),
                        tender.get("tenderReference", None),
                        tender.get("cardType", None),
                        tender.get("isoResCode", None),
                        tender.get("auxResponse", None),
                        tender.get("responseCode", None),
                        tender.get("responseMessage", None),
                        tender.get("displayMessage", None),
                        idtransaction  
                    )

                    print(f"> Pago {idx}:")
                    for key, value in tender.items():
                        print(f">     {key}: {value}")

        # #validamos si falta algun campo correspondiente a store_data
        print("=================")
        print("===== STORE =====")
        print("=================")
        fields_to_check = ["name", "address", "city", "stateCode", "storeZip", "storePhoneNumber"]
        missing_fields = [field for field in fields_to_check if not store_data.get(field)]
        if missing_fields:
            isComplete = False
            
            error_message = f"Missing fields in store_data block: {', '.join(missing_fields)}"

            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)
            
            print(error_message)
            
            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            idClient = db.InsertStore(store_data["name"], store_data["address"], store_data["city"], store_data["stateCode"], store_data["storeZip"], store_data["storePhoneNumber"])

            for key, value in store_data.items():
                print(f"> {key}: {value}")

        # Validamos si el bloque item_data está vacío o no 
        print("================")
        print("===== ITEM =====")
        print("================")
        if "item" not in item_data or not item_data["item"]:
            isComplete = False  

            error_message = "No products were extracted from the item_data block"
                                              
            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            for idx, item in enumerate(item_data["item"], start=1):
                print(f"> Producto {idx}:")
                
                idProduct = db.InsertProduct(item["description"])
                db.Insert_nn_Product_Transaction(
                    idProduct,
                    idtransaction,
                    item["quantitySoldType"],
                    item["quantitySold"],
                    item["dollarAmount"],
                    item["taxFlag"]
                )

                for key, value in item.items():
                    print(f">     {key}: {value}")

        # Validamos si el bloque discount_data está vacío o no 
        print("====================")
        print("===== DISCOUNT =====")
        print("====================")
        for idx, item in enumerate(discount_data["discount"], start=1):
            print(f"> Descuento {idx}:")

            idProduct = db.InsertProduct(item["discountDescription"])

            idDiscount = db.InsertDiscount(
                item["discountDollarAmount"],
                item["extDollarAmount"],
                item["discountPercent"],
                item["discountAmount"],
                item["discountReasonCode"],
                item["printLine"]
            )

            db.Insert_nn_Discount_Product_Transaction(idDiscount, idProduct, idtransaction)

            for key, value in item.items():
                print(f"     {key}: {value}")

        # Validamos si el bloque tax_data está vacío o no 
        #if (not balanceCorrect and not tenderCorrect and ("tax" not in tax_data or tax_data["tax"] is None or not tax_data["tax"])):
        print("===============")
        print("===== TAX =====")
        print("===============")
        if "tax" not in tax_data or tax_data["tax"] is None or not tax_data["tax"]:
            isComplete = False  

            error_message = "No tax was extracted from the tax_data block"

            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            for idx, item in enumerate(tax_data["tax"], start=1):
                print(f"> Tax {idx}:")

                idTax = db.InsertTax(
                    item["taxAmount"],
                    item["taxPercent"],
                    item["taxDescription"],
                    item["taxDetailNumber"],
                    item["taxRuleCode"],
                    idtransaction
                )

                for key, value in item.items():
                    print(f"     {key}: {value}")

        # Validamos si change está vacío o no 
        print("==================")
        print("===== CHANGE =====")
        print("==================")
        if change in [None, ""]:
            isComplete = False  

            error_message = f"The CHANGE value could not be extracted"
            
            db.Insert_nn_Error_Transaction(2, idtransaction, error_message) 

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "INVALID_DATA_VALUES",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            print(f"> {change}")

        # Validamos si savingTotal está vacío o no 
        print("=========================")
        print("===== SAVINGS TOTAL =====")
        print("=========================")
        if savingTotal in [None, ""]:
            isComplete = False  

            error_message = "The SAVINGS TOTAL value could not be extracted"

            db.Insert_nn_Error_Transaction(3, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            print(f"> {savingTotal}")

        # Validamos si transactionDate y transactionTime está vacío o no 
        print("=================================")
        print("===== TRANSACTION DATE/TIME =====")
        print("=================================")
        if transactionDate in [None, ""] or transactionTime in [None, ""]:
            isComplete = False  

            error_message = "The TRANSACTION DATE/TIME value could not be extracted"

            db.Insert_nn_Error_Transaction(2, idtransaction, error_message)  

            print(error_message)

            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            return
        else:
            print(f"> {transactionDate}")
            print(f"> {transactionTime}")


        # validamos si falta algun campo correspondiente a customer_data esta vacio
        print("====================")
        print("===== CUSTOMER =====")
        print("====================")
        customer_data = {
            "name":  customerName,
            "account":  customerAccount,
            "earnings":  customerEarnings,
            "rewardsBalance": customerRewardsBalance,
            "nextReward": customerNextReward,
            "rewardsCard": customerRewardsCard,
            "expiring": customerExpiring
        }  
        missing_customer = []
        has_valid_data = False

        for key, value in customer_data.items():
            if value in [None, ""]:
                missing_customer.append(key)
            else:
                has_valid_data = True

        if missing_customer:
            error_message = f"Missing fields in customer block: {', '.join(missing_customer)}"

            db.Insert_nn_Error_Transaction(3, idtransaction, error_message)  
            
            print(error_message)
            
            error_log = {
                "transaction_id": idTrasaccionOriginal,
                "error_type": "MISSING_FIELD",
                "error_detail": error_message,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        if has_valid_data:
            idCustomer = db.InsertCustomer(
                customer_data["name"],
                customer_data["account"],
                customer_data["earnings"],
                customer_data["rewardsBalance"],
                customer_data["nextReward"],
                customer_data["rewardsCard"],
                customer_data["expiring"],
                idtransaction  # Relación con la transacción
            )
        
        for key, value in customer_data.items():
            print(f"> {key}: {value}")

        print("==================")
        print("===== RESULT =====")
        print("==================")
        if error:
            print(">>> Hubo errores en algunas transacciones. Revisa 'missing_data.log'.")
            for detail in error:
                logging.warning(f"ERROR {detail['error_type']} en transaccion {detail['transaction_id']}: {detail['error_detail']}")
        else:
            print(">>> No hubo errores en ninguna transaccion.")

    except Exception as error:
        db.Insert_nn_Error_Transaction(1, idtransaction, error)
        print(f"Unknown error try 1: {error}")
        logging.error(f"Unknown error try 1 transaction_id: {idTrasaccionOriginal}: {error}")

 

    
        

   
   

if __name__ == "__main__":
    output_file = "output.txt"  # Manteniendo la salida a archivo
    captured_output = StringIO()  # Capturar la salida estándar
    sys.stdout = captured_output  # Redirigir salida estándar
    
    try: 
        # Leer datos desde stdin
        input_data = sys.stdin.read()
        data = json.loads(input_data)

        # Extraer valores del JSON
        mode = data.get("mode")
        checkboxes = data.get("checkboxes", {})
        
        qty = int(data.get("qty"))
        # qty = 5 #data.get("qty", 100)
        receipt_text = data.get("text", "")

        if mode == 'onlyOne':
            start_processing = time.time()
            print(f"*******************************************************************")
            print(f"                        TRANSACTION id: N/A                        ")
            print(f"*******************************************************************")
            result = ReadTransaction(receipt_text, checkboxes, 'N/A')
            end_processing = time.time()

            print(f"*******************************************************************")
            print(f"                               TIMES                               ")
            print(f"*******************************************************************")
            processing_time = end_processing - start_processing
            print(f"Record processing time: {processing_time:.3f} seconds")
            
        elif mode == 'database':  
            start_db = time.time()
            transactions = db.GetTransaction(qty)
            end_db = time.time()

            start_processing = time.time()
            for item in transactions:
                if '<line>' in item['param_value']:
                    print(f"*******************************************************************")
                    print(f"                         TRANSACTION id: {item['id']}              ")
                    print(f"*******************************************************************")
                    result = ReadTransaction(item['param_value'], checkboxes, item['id'])
            end_processing = time.time()

            print(f"*******************************************************************")
            print(f"                               TIMES                               ")
            print(f"*******************************************************************")
            db_time = end_db - start_db
            print(f"Database reading time: {db_time:.3f} seconds")
            processing_time = end_processing - start_processing
            print(f"Record processing time: {processing_time:.3f} seconds")
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

    finally:
        sys.stdout = sys.__stdout__

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(captured_output.getvalue())
    
    print(captured_output.getvalue())