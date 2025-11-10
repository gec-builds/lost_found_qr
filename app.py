from flask import Flask, render_template, request, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from twilio.rest import Client
import qrcode
import os
import io
from urllib.parse import quote

app = Flask(__name__)

# --- NEW: Database Configuration for Vercel & Local ---
# Vercel will provide POSTGRES_URL environment variable
DATABASE_URL = os.environ.get('POSTGRES_URL')

if not DATABASE_URL:
    # Fallback to a local SQLite database if POSTGRES_URL is not set
    print("WARNING: POSTGRES_URL not set, falling back to local items.db")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
else:
    # Vercel uses 'postgres://' but SQLAlchemy needs 'postgresql://'
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Twilio Configuration (Get from Environment Variables) ---
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.environ.get('TWILIO_WHATSAPP_FROM')


# --- Database Model ---
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.String(50), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    custom_message = db.Column(db.String(300), nullable=True)

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    college_id = request.form.get('collegeId', '').strip()
    phone_number = request.form.get('phoneNumber', '').strip()
    custom_message_input = request.form.get('customMessage', '').strip()

    if not college_id or not phone_number:
        return "Error: College ID and Phone number required", 400

    phone_number = ''.join(filter(str.isdigit, phone_number))

    if custom_message_input:
        owner_message = custom_message_input
    else:
        owner_message = f"Hello, I found the item for College ID: {college_id}. Please let me know how I can return it."

    item = Item.query.filter_by(college_id=college_id).first()
    if not item:
        item = Item(college_id=college_id)

    item.phone_number = phone_number
    item.custom_message = owner_message
    db.session.add(item)
    db.session.commit()

    # --- Generate QR in memory ---
    found_url = url_for('found_item', college_id=college_id, _external=True)
    img = qrcode.make(found_url)

    # Save to an in-memory byte stream
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0) # Rewind the stream to the beginning

    return send_file(buf, mimetype='image/png')

# --- Page the QR code links to ---
@app.route('/found/<college_id>')
def found_item(college_id):
    item = Item.query.filter_by(college_id=college_id).first_or_404()
    return render_template('found.html', college_id=item.college_id)

# --- Backend route to send the WhatsApp message ---
@app.route('/notify/<college_id>', methods=['POST'])
def notify_owner(college_id):
    item = Item.query.filter_by(college_id=college_id).first_or_404()

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM]):
        print("ERROR: Twilio environment variables are not set.")
        return "Error: Notification system is not configured.", 500

    finder_message = request.form.get('finder_message', '').strip()

    owner_message_body = f"🎉 Good news! Someone found your item ({item.college_id})."
    if finder_message:
        owner_message_body += f"\n\nThey left this message:\n'{finder_message}'"
    else:
        owner_message_body += "\n\n(The finder did not leave a message)."

    phone_to = item.phone_number.strip()

    if len(phone_to) == 10 and not phone_to.startswith('91'):
        print(f"Notice: Adding '91' to 10-digit number: {phone_to}")
        phone_to = f"91{phone_to}"

    phone_to_formatted = f"whatsapp:+{phone_to}"

    try:
        print(f"Attempting to send message from {TWILIO_WHATSAPP_FROM} to {phone_to_formatted}")
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        message = client.messages.create(
            body=owner_message_body,
            from_=TWILIO_WHATSAPP_FROM,
            to=phone_to_formatted
        )

        print(f"Message sent successfully! SID: {message.sid}")
        return "Message sent successfully! The owner has been notified."

    except Exception as e:
        print(f"--- TWILIO ERROR ---: {e}")
        return "Error: Could not send notification.", 500
