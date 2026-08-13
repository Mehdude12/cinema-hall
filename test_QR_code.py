import io
import urllib.parse
import time
import atexit
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, send_file, redirect, url_for

# Safely import the separate permanent data data file
import booking_data
if not hasattr(booking_data, 'SAVED_BOOKINGS'):
    booking_data.SAVED_BOOKINGS = {}

app = Flask(__name__)
app.secret_key = "cinema_vault_session_protection_string"

# ==========================================
# DEVICE GATEKEEPER MONITOR CONFIGURATION
# ==========================================
# Change this to your exact phone signature string captured earlier
MY_PHONE_SIGNATURE = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Mobile Safari/537.36"

# ==========================================
# MULTI-MOVIE SCHEDULING DATABASE
# ==========================================
TICKET_PRICE_INR = 150
NOW = datetime.now()

MOVIES = {
    "m1": {
        "movie_title": "Interstellar: Special Edition",
        "show_time_obj": NOW + timedelta(hours=2),
        "theatre": "Cinema 4 - Screen 2 (IMAX)",
        "total_seats": 50,
    },
    "m2": {
        "movie_title": "Oppenheimer: 70mm Film",
        "show_time_obj": NOW + timedelta(hours=3, minutes=30),
        "theatre": "Cinema 1 - Screen 1 (IMAX)",
        "total_seats": 40,
    },
    "m3": {
        "movie_title": "Dune: Part Two",
        "show_time_obj": NOW + timedelta(hours=5),
        "theatre": "Cinema 3 - Screen 4 (Dolby)",
        "total_seats": 60,
    }
}

# Master runtime configuration matrix
MASTER_DB = {
    "active_bookings": booking_data.SAVED_BOOKINGS,
    "seats_cache": {"m1": [], "m2": [], "m3": []}
}

# Synchronize and sort seat arrays on startup from saved file logs
for bkid, details in MASTER_DB["active_bookings"].items():
    m_id = details.get("movie_id", "m1")
    if m_id in MASTER_DB["seats_cache"]:
        seats_split = [s.strip()
                       for s in details["seats"].split(",") if s.strip()]
        MASTER_DB["seats_cache"][m_id].extend(seats_split)

# ==========================================
# AUTOMATED DISK BACKUP SYSTEM
# ==========================================


def save_data_on_shutdown():
    data_file_path = "booking_data.py"
    print(
        "\n💾 [SYSTEM LOG] Closing server safely... Exporting data dictionary structures.")
    with open(data_file_path, "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write(f"SAVED_BOOKINGS = {repr(MASTER_DB['active_bookings'])}\n")
    print("✅ [SYSTEM LOG] Data written successfully to booking_data.py!")


atexit.register(save_data_on_shutdown)

# ==========================================
# ROUTE 1: MULTI-MOVIE HOMEPAGE
# ==========================================


@app.route('/')
def home():
    print(
        f"\n📱 [DEVICE TRACKER] Current phone signature is:\n{request.headers.get('User-Agent')}\n")
    current_time = datetime.now()

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cinema Ticket Vault</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; text-align: center; padding: 40px 10px; margin: 0; }
            .container { max-width: 900px; margin: 0 auto; }
            .movie-grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; margin-top: 30px; }
            .movie-card { background: #1F1F1F; width: 280px; padding: 20px; border-radius: 8px; border-top: 4px solid #E50914; text-align: left; box-shadow: 0 4px 10px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between; }
            .btn { display: block; text-align: center; padding: 10px; background: #E50914; color: white; font-weight: bold; text-decoration: none; border-radius: 4px; margin-top: 15px; }
            .btn:disabled, .btn.disabled { background: #555; cursor: not-allowed; }
            .closed { border-top-color: #555; opacity: 0.6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="font-size: 28px; margin-bottom: 5px;">🍿 Cinema Ticket Vault</h1>
            <p style="color:#aaa; margin-top:0;">Select a showtime to proceed with seat selections</p>
            
            <div class="movie-grid">
                {% for mid, m in movies.items() %}
                {% set closing_time = m.show_time_obj - timedelta(hours=1) %}
                {% set is_closed = current_time >= closing_time %}
                {% set remaining = m.total_seats - cache[mid]|length %}
                
                <div class="movie-card {{ 'closed' if is_closed or remaining <= 0 }}">
                    <div>
                        <h3 style="margin:0 0 10px 0; min-height:50px;">{{ m.movie_title }}</h3>
                        <p style="color:#aaa; font-size:13px; margin:5px 0;">📍 {{ m.theatre }}</p>
                        <p style="color:#E50914; font-size:13px; font-weight:bold; margin:5px 0;">🕒 {{ m.show_time_obj.strftime('%I:%M %p') }}</p>
                        <p style="font-size:13px; margin:5px 0;">🎟️ Seats: <strong>{{ remaining }}</strong> / {{ m.total_seats }}</p>
                    </div>
                    
                    {% if is_closed %}
                        <div class="btn disabled" style="background:#331212; color:#FF4A4A;">Closed</div>
                    {% elif remaining <= 0 %}
                        <div class="btn disabled" style="background:#333;">Sold Out</div>
                    {% else %}
                        <a href="/select/{{ mid }}" class="btn">Select Seats</a>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            <br><br>
            <a href="/admin" style="color: #666; text-decoration: none; font-size: 13px;">🔒 Access Admin Dashboard</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, movies=MOVIES, cache=MASTER_DB["seats_cache"], current_time=current_time, timedelta=timedelta)

# ==========================================
# ROUTE 2: SEAT SELECTION SECTOR
# ==========================================


@app.route('/select/<movie_id>')
def select_seats(movie_id):
    if movie_id not in MOVIES:
        return redirect(url_for('home'))

    movie = MOVIES[movie_id]
    remaining = movie["total_seats"] - len(MASTER_DB["seats_cache"][movie_id])

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Reserve Seats</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; text-align: center; padding: 50px 10px; margin: 0; }
            .card { background: #1F1F1F; width: 100%; max-width: 450px; margin: 0 auto; padding: 30px; border-radius: 8px; border-top: 4px solid #E50914; box-sizing: border-box; }
            input, select { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #333; background: #333; color: white; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #E50914; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>{{ m.movie_title }}</h2>
            <p style="color: #25D366; font-weight: bold;">💰 ₹150 per ticket</p>
            <hr style="border-color:#333;">
            <form action="/simulate-payment" method="POST">
                <input type="hidden" name="movie_id" value="{{ mid }}">
                
                <label>Select Ticket Quantity:</label>
                <select name="ticket_count">
                    {% for i in range(1, min(6, remaining + 1)) %}
                        <option value="{{ i }}">{{ i }} Ticket(s)</option>
                    {% endfor %}
                </select>
                
                <label>Your Name:</label>
                <input type="text" name="customer_name" placeholder="John Doe" required>

                <label>Phone Number (with Country Code):</label>
                <input type="text" name="phone_number" placeholder="919876543210" required>
                
                <button type="submit">Proceed to Payment</button>
                <br><br>
                <a href="/" style="color:#aaa; text-decoration:none; font-size:14px;">← Back to Movies</a>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, m=movie, mid=movie_id, remaining=remaining, min=min)

# ==========================================
# ROUTE 3: SIMULATED SECURE PAYMENT GATEWAY
# ==========================================
# ==========================================
# ROUTE 3: SIMULATED SECURE PAYMENT GATEWAY
# ==========================================


@app.route('/simulate-payment', methods=['POST'])
def simulate_payment():
    movie_id = request.form.get('movie_id')
    ticket_count = int(request.form.get('ticket_count'))
    customer_name = request.form.get('customer_name').strip()
    user_phone = request.form.get(
        'phone_number').strip().replace("+", "").replace(" ", "")
    total_price = TICKET_PRICE_INR * ticket_count

    payment_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure Payment Sandbox</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; color: #333; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .gateway-card { background: white; width: 100%; max-width: 400px; padding: 25px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-top: 5px solid #25D366; text-align: left; box-sizing: border-box; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom: 15px; margin-bottom: 20px; }
            .option { padding: 12px 15px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; cursor: pointer; display: flex; align-items: center; font-weight: 500; }
            .option:hover { background-color: #f9f9f9; border-color: #25D366; }
            .spinner { width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #25D366; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="gateway-card" id="box">
            <div class="header">
                <div><h3 style="margin:0; font-size:16px; color:#666;">Cinema Checkout</h3><small style="color:#999;">Tickets: {{ count }}</small></div>
                <div style="font-size:22px; font-weight:bold;">₹{{ price }}</div>
            </div>
            
            <p style="font-size:14px; color:#555; margin-bottom:15px; font-weight:bold;">Choose Payment Method:</p>
            <div class="option"><input type="radio" name="pay-method" checked style="margin-right:10px;"> 📱 UPI (GPay, PhonePe, Paytm)</div>
            <div class="option"><input type="radio" name="pay-method" style="margin-right:10px;"> 💳 Credit / Debit Card</div>
            <div class="option"><input type="radio" name="pay-method" style="margin-right:10px;"> 🏦 Net Banking</div>
            
            <button style="width:100%; padding:14px; background:#25D366; border:none; color:white; font-weight:bold; border-radius:6px; cursor:pointer; font-size:16px; margin-top:10px;" onclick="pay()">Complete Simulation Payment</button>
        </div>
        
        <div class="gateway-card" id="load" style="display:none; text-align:center;">
            <div class="spinner"></div><h3>Processing Simulation...</h3>
        </div>
        <script>
        function pay() {
            document.getElementById('box').style.display = 'none';
            document.getElementById('load').style.display = 'block';
            setTimeout(function() {
                window.location.href = "/success?mid=" + "{{ mid }}" + "&count=" + "{{ count }}" + "&name=" + encodeURIComponent("{{ name }}") + "&phone=" + encodeURIComponent("{{ phone }}");
            }, 2500);
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(payment_template, price=total_price, count=ticket_count, name=customer_name, mid=movie_id, phone=user_phone)

# ==========================================
# ROUTE 4: CONFIRMATION PREVIEW
# ==========================================


@app.route('/success')
def success():
    movie_id = request.args.get('mid', 'm1')
    ticket_count = int(request.args.get('count', 1))
    customer_name = request.args.get('name', 'Guest')
    user_phone = request.args.get('phone', 'N/A')

    # 1. Process explicit multi-movie sequential assignments
    start_seat = len(MASTER_DB["seats_cache"][movie_id]) + 1
    assigned_seats = [f"Seat {i}" for i in range(
        start_seat, start_seat + ticket_count)]
    MASTER_DB["seats_cache"][movie_id].extend(assigned_seats)
    seats_string = ", ".join(assigned_seats)

    booking_id = f"BKID{int(time.time())}"

    # 2. Append data values inside multi-movie mapping format profiles
    MASTER_DB["active_bookings"][booking_id] = {
        "movie_id": movie_id,
        "name": customer_name,
        "seats": seats_string,
        "phone": user_phone,
        "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p")
    }

    img_src = f"/download-ticket?seats={urllib.parse.quote(seats_string)}&name={urllib.parse.quote(customer_name)}&mid={movie_id}&bkid={booking_id}"
    dl_src = f"{img_src}&download=true"

    success_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Booking Confirmed</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; text-align: center; padding: 20px 10px; margin: 0; }
            .card { background: #1F1F1F; width: 100%; max-width: 520px; margin: 20px auto; padding: 25px; border-radius: 8px; border-top: 4px solid #25D366; box-shadow: 0 4px 10px rgba(0,0,0,0.5); box-sizing: border-box; }
            .btn { display: inline-block; width: 100%; max-width: 280px; padding: 14px; background-color: #E50914; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; font-size: 16px; box-sizing: border-box; }
            .btn:hover { background-color: #b80710; }
            .ticket-preview { width: 100%; max-width: 480px; height: auto; margin-top: 15px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.6); display: block; margin-left: auto; margin-right: auto; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="color: #25D366; font-size: 24px;">🎉 Seats Reserved!</h1>
            <p>Thank you <strong>{{ name }}</strong>. Your positions (<strong>{{ seats }}</strong>) are locked.</p>
            <img src="{{ img_src }}" alt="Movie Ticket" class="ticket-preview">
            <hr style="border-color: #333; margin: 20px 0;">
            <a href="{{ dl_src }}" class="btn">📥 Download Ticket Image</a><br><br>
            <a href="/" style="color:#888; text-decoration:none; font-size:14px;">← Back to Home</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(success_template, seats=seats_string, name=customer_name, img_src=img_src, dl_src=dl_src)

# ==========================================
# ROUTE 5: THE CORE PASS COMPILER
# ==========================================


@app.route('/download-ticket')
def download_ticket_route():
    from PIL import Image, ImageDraw, ImageFont
    import qrcode

    seats_param = request.args.get('seats', 'Standard Pass')
    name_param = request.args.get('name', 'Guest')
    movie_id = request.args.get('mid', 'm1')
    bkid_param = request.args.get('bkid', 'UNKNOWN')
    should_download = request.args.get('download', 'false') == 'true'

    movie_title = MOVIES.get(movie_id, MOVIES["m1"])["movie_title"]
    theatre_name = MOVIES.get(movie_id, MOVIES["m1"])["theatre"]
    show_time_str = MOVIES.get(movie_id, MOVIES["m1"])[
        "show_time_obj"].strftime("%A, %b %d | %I:%M %p")

    ticket = Image.new("RGB", (750, 350), "#1A1A1A")
    draw = ImageDraw.Draw(ticket)

    try:
        font_title = ImageFont.truetype("Apple_Chancery.ttf", 34)
        font_body = ImageFont.truetype("Arial.ttf", 16)
        font_label = ImageFont.truetype("Arial.ttf", 12)
    except IOError:
        try:
            font_title = ImageFont.truetype("georgia.ttf", 30)
            font_body = ImageFont.truetype("arial.ttf", 16)
            font_label = ImageFont.truetype("arial.ttf", 12)
        except IOError:
            font_title = font_body = font_label = ImageFont.load_default()

    draw.rectangle([(0, 0), (750, 15)], fill="#E50914")
    draw.text((40, 35), movie_title, fill="#FFFFFF", font=font_title)
    draw.text((40, 100), "TICKET HOLDER", fill="#888888", font=font_label)
    draw.text((40, 120), name_param, fill="#FFFFFF", font=font_body)
    draw.text((40, 165), "DATE, TIME & CINEMA",
              fill="#888888", font=font_label)
    draw.text((40, 185), f"{show_time_str} | {theatre_name}",
              fill="#FFFFFF", font=font_body)
    draw.text((40, 240), "SEATS ALLOCATED", fill="#888888", font=font_label)
    draw.text((40, 260), seats_param, fill="#E50914", font=font_body)

    validation_url = f"{request.url_root}verify/{bkid_param}"
    qr = qrcode.QRCode(
        version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(validation_url)
    qr.make(fit=True)
    qr_img = qr.make_image(
        fill_color="black", back_color="white").convert('RGB')
    ticket.paste(qr_img, (510, (350 - qr_img.height) // 2))

    img_io = io.BytesIO()
    ticket.convert("RGB").save(img_io, 'JPEG')
    img_io.seek(0)

    if should_download:
        return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='movie_ticket.jpg')
    return send_file(img_io, mimetype='image/jpeg')

# ==========================================
# ROUTE 6: SECURE GATEKEEPER TICKET SCAN CHECKER
# ==========================================


@app.route('/verify/<booking_id>')
def verify_ticket_route(booking_id):
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()

    # DEVICE FINGERPRINT SECURITY CHECKS [1.1]
    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        print(
            f"🛑 [SECURITY NOTICE] Blocked scan attempt from unauthorized device: {scanned_device_user_agent}")
        return """
        <body style="background:#141414; color:#FF4A4A; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #FF4A4A; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2>🔒 ACCESS DENIED</h2>
                <p style="color:#aaa; font-size:14px; line-height:1.5;">This scanner device does not possess authorized admin credentials framework.</p>
            </div>
        </body>
        """, 403

    active_records = MASTER_DB["active_bookings"]
    if booking_id in active_records:
        t = active_records[booking_id]
        m_title = MOVIES.get(t.get("movie_id", "m1"),
                             MOVIES["m1"])["movie_title"]

        approved_template = """
        <body style="background:#141414; color:white; font-family:Arial, sans-serif; text-align:center; padding-top:40px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #25D366; text-align:left; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <div style="background:#25D366; color:black; font-weight:bold; padding:5px 10px; display:inline-block; border-radius:4px; margin-bottom:15px; font-size:13px;">✓ APPROVED ENTRY</div>
                <h3 style="margin:0 0 15px 0; font-size:20px;">{{ title }}</h3>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Holder:</strong> {{ t.name }}</p>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Seats:</strong> <span style="color:#E50914; font-weight:bold;">{{ t.seats }}</span></p>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Phone:</strong> +{{ t.phone }}</p>
                <p style="margin:15px 0 0 0; font-size:12px; color:#666; border-top:1px solid #333; padding-top:10px;"><strong>Scanned Stamp:</strong> {{ t.timestamp }}</p>
            </div>
        </body>
        """
        return render_template_string(approved_template, t=t, title=m_title)

    return """
    <body style="background:#141414; color:#E50914; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
        <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #E50914; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
            <h2>❌ ACCESS DENIED</h2>
            <p style="color:#aaa; font-size:14px;">The scanned log reference code was not registered in our database catalog files.</p>
        </div>
    </body>
    """, 404
# ==========================================
# ROUTE 7: HIDDEN ADMIN SEATING DASHBOARD & WIPER (DEVICE LOCKED)
# ==========================================


@app.route('/admin')
def admin_dashboard():
    # 1. Grab the hidden incoming browser signature from the device loading the dashboard
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()

    # 2. ADMIN DEVICE SECURITY CHECK
    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        print(
            f"🛑 [ADMIN WARNING] Blocked unauthorized dashboard access attempt from: {scanned_device_user_agent}")
        return """
        <body style="background:#141414; color:#FF4A4A; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:35px; border-radius:8px; border-top:5px solid #FF4A4A; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2>🔒 ACCESS DENIED</h2>
                <p style="color:#aaa; font-size:14px; line-height:1.6;">
                    Your device signature does not match the master theater administrator credentials. This login attempt has been blocked and logged.
                </p>
            </div>
        </body>
        """, 403

    # 3. IF YOUR PHONE SCORES A VERIFIED HANDSHAKE, LOAD THE RENDERING SHEET
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Reporting Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 40px 15px; margin: 0; }
            .wrapper { max-width: 1100px; margin: 0 auto; }
            table { width: 100%; border-collapse: collapse; margin-top: 25px; background:#1F1F1F; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
            th, td { padding: 14px; border: 1px solid #333; text-align: left; font-size:14px; }
            th { background-color: #E50914; color: white; font-weight: bold; }
            .btn-wipe { display: inline-block; padding: 10px 20px; background-color: #FF4A4A; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size:13px; }
        </style>
    </head>
    <body>
        <div class="wrapper">
            <h2>🔒 Security Registry Control Dashboard</h2>
            <p style="color:#aaa; margin-top:0;">Tracks permanent transaction dictionaries stored within backend data layers.</p>
            <div style="margin-top: 20px;">
                <a href="/admin/wipe-logs" class="btn-wipe" onclick="return confirm('Wipe out all database log arrays entirely? This cannot be undone.');">🚨 Wipe All Booking Data</a>
                &nbsp;&nbsp;&nbsp;&nbsp;<a href="/" style="color:#aaa; text-decoration:none; font-size:14px;">← Back to Client Homepage</a>
            </div>
            <table>
                <tr>
                    <th>Booking Reference ID</th>
                    <th>Movie Segment</th>
                    <th>Customer Name</th>
                    <th>Allocated Seats Matrix</th>
                    <th>Phone Log</th>
                    <th>Timestamp Logs</th>
                </tr>
                {% for bkid, t in logs.items() %}
                <tr>
                    <td style="color:#25D366; font-family:monospace; font-weight:bold;">{{ bkid }}</td>
                    <td>{{ titles[t.movie_id] if t.movie_id in titles else 'Unknown Show' }}</td>
                    <td>{{ t.name }}</td>
                    <td style="color:#E50914; font-weight:bold;">{{ t.seats }}</td>
                    <td>+{{ t.phone }}</td>
                    <td style="color:#888;">{{ t.timestamp }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    movie_title_map = {mid: m["movie_title"] for mid, m in MOVIES.items()}
    return render_template_string(html_template, logs=MASTER_DB["active_bookings"], titles=movie_title_map)


@app.route('/admin/wipe-logs')
def wipe_logs():
    # 1. Protect the wipe route using the device signature check as well
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()

    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        print(
            f"🛑 [ADMIN WARNING] Blocked unauthorized wipe database command from: {scanned_device_user_agent}")
        return "Unauthorized Action", 403

    # 2. Proceed with wiping logs if it's your phone
    MASTER_DB["active_bookings"].clear()
    MASTER_DB["seats_cache"] = {"m1": [], "m2": [], "m3": []}
    with open("booking_data.py", "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write("SAVED_BOOKINGS = {}\n")
    return redirect(url_for('admin_dashboard'))


# ==========================================
# LAUNCH GATEWAYS
# ==========================================
if __name__ == '__main__':
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print("\n" + "="*50)
    print(f"🚀 MULTI-MOVIE SYSTEM ACTIVE ON LOCAL WI-FI PORTAL!")
    print(f"👉 Client Homepage Link: http://{local_ip}:5000")
    print(f"🔒 Secret Admin Control Dashboard: http://{local_ip}:5000/admin")
    print("="*50 + "\n")

    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=5000)
