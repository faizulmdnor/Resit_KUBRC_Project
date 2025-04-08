import re
import gdown
import os
import logging
import pandas as pd
from pymongo import MongoClient
from fpdf import FPDF
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime

XLSX_GDRIVE_ID = os.getenv("XLSX_GDRIVE_ID", "1HKkJSE_zauenx7PB285Q8t44KvOwvwiwy4zeAJv_f3E")
XLSX_FILE = "KUBRC_PaymentDetails.xlsx"
MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "KUBRC_DB"
COLLECTION_NAME = "payments"

# Function to check if the database exists
def check_if_db_exists(db_name):
    existing_databases = client.list_database_names()
    if db_name in existing_databases:
        logging.info(f"Database '{db_name}' already exists.")
        return True
    else:
        logging.info(f"Database '{db_name}' does not exist. It will be created when data is inserted.")
        return False

# convert number to text
def number_to_text(num):
    units = ['', ' ribu', ' juta', ' bilion', ' trilion']
    ones = ['', 'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'lapan', 'sembilan']
    special = {10: 'sepuluh', 11: 'sebelas', 12: 'dua belas', 13: 'tiga belas', 14: 'empat belas', 15: 'lima belas',
               16: 'enam belas', 17: 'tujuh belas', 18: 'lapan belas', 19: 'sembilan belas'}

    def three_digit_to_text(n):
        text = ''
        hundreds = n // 100
        remainder = n % 100
        tens = remainder // 10
        ones_digit = remainder % 10

        if hundreds > 0:
            text += ones[hundreds] + ' ratus'
        if remainder > 0:
            if 10 <= remainder <= 19:
                text += ' ' + special[remainder]
            else:
                if tens > 0:
                    text += ' ' + ones[tens] + ' puluh'
                if ones_digit > 0:
                    text += ' ' + ones[ones_digit]
        return text.strip()

    if num == 0:
        return 'kosong'
    elif num == 1:
        return 'satu'

    if isinstance(num, float):
        whole = int(num)
        sen_str = str(num).split('.')[-1].ljust(2, '0')[:2]  # Ambil 2 digit tanpa pembundaran
        sen = int(sen_str)
        if sen > 0:
            return f"Ringgit Malaysia {number_to_text(whole)} dan {number_to_text(sen)} sen sahaja".strip()
        else:
            return f"Ringgit Malaysia {number_to_text(whole)} sahaja".strip()

    num_str = str(num)
    if '.' in num_str:
        num_str = num_str.split('.')[0]

    num_str = num_str[::-1]
    parts = [num_str[i:i + 3][::-1] for i in range(0, len(num_str), 3)]
    result = []

    for i, part in enumerate(parts):
        if part.isdigit() and int(part) > 0:
            result.append(three_digit_to_text(int(part)) + units[i])

    return ' '.join(reversed(result)).strip()

# send KUBRC receipt via email to payee and bendahari KUBRC, return datetime send.
def email_receipt(email, receipt_path, nama):
    EMAIL_BENDAHARI = 'suraiyaibrahim@gmail.com'
    EMAIL_SENDER = 'kubrc2023@gmail.com'
    SENDER_PASS = "vjmi kgcr tyfy qoan"
    EMAIL_TO = email


    msg = EmailMessage()
    msg['Subject'] = "Resit Pembayaran KUBRC"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_TO
    msg['Cc'] = EMAIL_BENDAHARI

    message_body = (f"Assalamualaikum dan Salam Sejahtera,\n"
                    f"Tuan/Puan {nama},\n"
                    f"Terima kasih atas pembayaran yang telah dibuat. Sokongan anda amat kami hargai demi "
                    f"kelangsungan persatuan, khususnya dalam membiayai perkhidmatan keselamatan komuniti kita.\n"
                    f"Dilampirkan bersama ini resit rasmi bagi pembayaran tersebut.\n"
                    f"Kami amat mengalu-alukan sebarang cadangan atau maklum balas demi penambahbaikan persatuan. "
                    f"Sila hubungi kami melalui emel di kubrc2023@gmail.com, kumpulan WhatsApp KUBRC Community, atau "
                    f"terus berhubung dengan mana-mana Ahli Jawatankuasa KUBRC.\n"
                    f"Sekian, terima kasih atas sokongan berterusan anda.\n\n"
                    f"Yang benar,\n"
                    f"AJK KUBRC.")
    msg.set_content(message_body)

    # attach receipt
    with open(receipt_path, 'rb') as f:
        file_data = f.read()
        file_name = os.path.basename(receipt_path)
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

    # send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, SENDER_PASS)
        smtp.send_message(msg)

    time_sent = datetime.now()
    return time_sent

class resit_pdf(FPDF):
    def __init__(self, receipt_date, reference_num, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.receipt_date = receipt_date
        self.reference_num = reference_num

    def receipt_header(self):
        self.image("kubrc_logo.png", x=10, y=5, w=130)
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "RESIT PEMBAYARAN KUBRC", ln=True, align="R")

        self.set_font("Arial", '', 10)
        self.cell(0, 5, f"No. Rujukan: {self.reference_num}", ln=True, align="R")
        self.cell(0, 5, f"Tarikh: {self.receipt_date}", ln=True, align="R")

    def receipt_bg(self):
        self.image("background_image.png", x=0, y=0, w=self.w, h=self.h)

    @staticmethod
    def generate_KUBRC_receipt(data):
        resit_folder = os.path.join("Resit KUBRC", data['month_year'])
        filename = f"{data['nama']}_{data['reference_num']}.pdf"
        fullpath = os.path.join(resit_folder, filename)

        if not os.path.exists(resit_folder):
            os.makedirs(resit_folder)

        pdf = resit_pdf(receipt_date=data['receipt_date'],
                        reference_num=data['reference_num'],
                        format=(220, 100))

        pdf.add_page()
        pdf.receipt_bg()
        pdf.receipt_header()

        pdf.set_font("Arial", "", 12)
        pdf.ln(10)
        pdf.cell(0, 5, f"Terima daripada: {data['payment_from']}", ln=True)
        pdf.cell(0, 5, f"Dengan jumlah: {data['total_text']}", ln=True)
        pdf.cell(0, 5, f"Bayaran untuk: {data['receipt_desc']}", ln=True)
        pdf.cell(0, 5, f"Jumlah: {data['total_paid']}", ln=True)
        pdf.cell(0, 5, f"Transaksi: {data['transaction_num']}", ln=True)

        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 4, "____________________________________________________________________", align='C', ln=True)
        pdf.cell(0, 4, 'Resit ini dijana secara elektronik dan tidak memerlukan tandatangan.', align='C', ln=True)
        pdf.cell(0, 4, 'This receipt is generated electronically and does not require a signature.', align='C', ln=True)

        pdf.output(fullpath)

        time_send = email_receipt(email=data['email_to'], receipt_path=fullpath, nama=data['nama'])
        return time_send


# Configure logging
logging.basicConfig(level=logging.INFO)

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Check if the database exists before proceeding
if check_if_db_exists(DB_NAME):
    # Database exists, proceed with the operations
    db = client[DB_NAME]
else:
    # Database does not exist, proceed with the operations and MongoDB will create it
    db = client[DB_NAME]

collection = db[COLLECTION_NAME]
try:
    logging.info("Downloading file from Google Drive...")
    gdown.download(f"https://drive.google.com/uc?id={XLSX_GDRIVE_ID}", XLSX_FILE, quiet=False)

    # Load the Excel file into a DataFrame
    df = pd.read_excel(XLSX_FILE)
    logging.info("File downloaded and loaded into DataFrame.")

    # Iterate through the DataFrame and insert data into MongoDB
    for index, row in df.iterrows():
        timestamp = row['Timestamp']
        email = row['Email Address']

        # Check for existing records based on Timestamp and Email
        existing_record = collection.find_one({"Timestamp": timestamp, "Email Address": email})

        if existing_record:
            logging.info(f"Existing record: {timestamp} - {email}. Skipping insertion.")
        else:
            # create new columns Reference Num, Receipt Date
            hse_num = re.sub(r'\D','', str(row['Nombor Rumah']))
            now = datetime.now()
            month_year = now.strftime("%b%Y")
            reference_num = f"{month_year}_{hse_num}_{index + 1}"
            receipt_date = now.strftime('%d-%b-%Y')



            # change number to text
            total_payment = re.sub(r"[^0-9.]", "", str(row['Jumlah']))
            total_payment_rm = f"RM {total_payment}"
            text_total = number_to_text(total_payment)
            text_number = f"Ringgit Malaysia {text_total} sahaja."

            # Receipt description
            received_from = f"{row['Nama']} - {hse_num}"
            receipt_desc = row['Keterangan']
            transaction_num = f"{row['Tarikh Transaksi']} - {row['Nombor Transaksi']}"

            # create receipt
            data_resit = {'payment_from': received_from,
                          'receipt_date': receipt_date,
                          'reference_num': reference_num,
                          'receipt_desc': receipt_desc,
                          'total_paid': total_payment_rm,
                          'total_text': text_number,
                          'transaction_num': transaction_num,
                          'month_year': month_year,
                          'nama': row['Nama'],
                          'email_to': email}

            send_datetime = resit_pdf.generate_KUBRC_receipt(data_resit)

            row['Jumlah (text)'] = text_number
            row['Reference Number'] = reference_num
            row['Receipt Date'] = receipt_date
            row['Receipt Sent'] = send_datetime

            # Insert the new record if not found
            new_record = row.to_dict()
            collection.insert_one(new_record)
            logging.info(f"Inserted new record: {timestamp} - {email}.")

except Exception as e:
    logging.error(f"Error downloading file or inserting data: {e}")
    exit(1)

