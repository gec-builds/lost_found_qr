from flask import Flask, render_template, request, send_file
import qrcode
import os
from urllib.parse import quote

app = Flask(__name__)
app.config['QR_FOLDER'] = 'qr_codes'
os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    college_id = request.form.get('collegeId', '').strip()
    phone_number = request.form.get('phoneNumber', '').strip()
    custom_message = request.form.get('customMessage', '').strip()

    if not college_id or not phone_number:
        return "Error: College ID and Phone number required", 400

    # Only digits for phone number
    phone_number = ''.join(filter(str.isdigit, phone_number))

    # Use custom message if provided, else default
    if custom_message:
        message = custom_message
    else:
        message = f"Hello, I found the item for College ID: {college_id}"

    from urllib.parse import quote
    whatsapp_link = f"https://wa.me/{phone_number}?text={quote(message)}"

    import os, qrcode
    path = os.path.join(app.config['QR_FOLDER'], f'{college_id}.png')
    img = qrcode.make(whatsapp_link)
    img.save(path)

    return send_file(path, mimetype='image/png')



if __name__ == '__main__':
    app.run(debug=True)
