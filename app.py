@app.route('/notify/<college_id>', methods=['POST'])
def notify_owner(college_id):
    item = Item.query.filter_by(college_id=college_id).first_or_404()

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM]):
        print("ERROR: Twilio environment variables are not set.")
        return "Error: Notification system is not configured.", 500

    # Get optional message from the finder
    finder_message = request.form.get('finder_message', '').strip()

    # Construct the message to the owner
    owner_message_body = f"🎉 Good news! Someone found your item ({item.college_id})."
    if finder_message:
        owner_message_body += f"\n\nThey left this message:\n'{finder_message}'"
    else:
        owner_message_body += "\n\n(The finder did not leave a message)."

    # --- NEW: Robust phone number formatting ---
    phone_to = item.phone_number.strip()

    # Add '91' if it's a 10-digit number
    if len(phone_to) == 10 and not phone_to.startswith('91'):
        print(f"Notice: Adding '91' to 10-digit number: {phone_to}")
        phone_to = f"91{phone_to}"

    # Ensure it has the full whatsapp:+ prefix
    phone_to_formatted = f"whatsapp:+{phone_to}"
    # --- End of new logic ---

    try:
        print(f"Attempting to send message from {TWILIO_WHATSAPP_FROM} to {phone_to_formatted}")
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        message = client.messages.create(
            body=owner_message_body,
            from_=TWILIO_WHATSAPP_FROM,
            to=phone_to_formatted  # Use the new formatted number
        )

        print(f"Message sent successfully! SID: {message.sid}")
        return "Message sent successfully! The owner has been notified."

    except Exception as e:
        print(f"--- TWILIO ERROR ---: {e}")
        return "Error: Could not send notification.", 500
