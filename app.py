from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import os
import pytesseract
from pdf2image import convert_from_path
from openpyxl import Workbook
import re
from subprocess import check_output

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ Tesseract path NOT needed on Render (Linux has it globally installed)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return render_template('message.html', message="No file uploaded")

    file = request.files['file']
    if file.filename == '':
        return render_template('message.html', message="No selected file")

    # Sanitize the filename to prevent directory traversal
    filename = secure_filename(file.filename)
    if filename == "":
        return render_template('message.html', message="Invalid filename")

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        # ✅ Get total pages using pdfinfo (Poppler tool)
        info = check_output(['pdfinfo', filepath]).decode("utf-8")
        total_pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
    except Exception as e:
        return render_template('message.html', message=f"❌ Could not read PDF: {e}")

    # ✅ Create Excel workbook
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Check-Invoice Mapping"
    sheet.append(["Payment Serial Number", "Invoice Number(s)"])

    # ✅ Loop through PDF in 3-page batches
    for start_page in range(1, total_pages + 1, 3):
        end_page = min(start_page + 2, total_pages)
        try:
            images = convert_from_path(
                filepath,
                dpi=300,
                first_page=start_page,
                last_page=end_page
            )
        except Exception as e:
            print(f"❌ Failed to convert pages {start_page}-{end_page}: {e}")
            continue

        serial_number = None
        invoice_numbers = []

        # Page 1 of batch → Serial Number
        if len(images) >= 1:
            text1 = pytesseract.image_to_string(images[0])
            match = re.search(r'Payment Serial Number\s*:\s*(\d+)', text1)
            if match:
                serial_number = match.group(1)

        # Page 3 of batch → Invoice Numbers
        if len(images) >= 3:
            text3 = pytesseract.image_to_string(images[2])
            invoice_matches = re.findall(r'\b\d{5,}\b', text3)
            invoice_numbers = invoice_matches

        if serial_number:
            sheet.append([serial_number, ", ".join(invoice_numbers)])

    # ✅ Save Excel file
    output_filename = os.path.splitext(filename)[0] + "_output.xlsx"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    workbook.save(output_path)

    return send_file(output_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
