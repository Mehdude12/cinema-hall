import io
import urllib.parse
import time
import atexit
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, send_file, redirect, url_for

# Safely import the separate permanent data storage file
import booking_data
if not hasattr(booking_data, 'SAVED_BOOKINGS'):
    booking_data.SAVED_BOOKINGS = {}
if not hasattr(booking_data, 'SAVED_MOVIES'):
    booking_data.SAVED_MOVIES = {}

app = Flask(__name__)
app.secret_key = "cinema_vault_session_protection_string"

# ==========================================
# DEVICE GATEKEEPER MONITOR CONFIGURATION
# ==========================================
# Make sure your phone user-agent signature goes right between these quotes:
MY_PHONE_SIGNATURE = "Mozilla/5.0"

# ==========================================
# MULTI-MOVIE SCHEDULING MASTER DATABASE
# ==========================================
NOW = datetime.now()

# DEFAULT MASTER BACKUP DICTIONARY
DEFAULT_MOVIES = {
    "m1": {
        "movie_title": "Interstellar: Special Edition",
        "show_time_str": (NOW + timedelta(hours=2)).strftime("%I:%M %p"),
        "theatre": "Cinema 4 - Screen 2 (IMAX)",
        "rows_str": "A,B,C,D,E",
        "seats_per_row": 23,
        "ticket_price": 150
    },
    "m2": {
        "movie_title": "Oppenheimer: 70mm Film",
        "show_time_str": (NOW + timedelta(hours=3, minutes=30)).strftime("%I:%M %p"),
        "theatre": "Cinema 1 - Screen 1 (IMAX)",
        "rows_str": "A,B,C,D",
        "seats_per_row": 17,
        "ticket_price": 150
    },
    "m3": {
        "movie_title": "Dune: Part Two",
        "show_time_str": (NOW + timedelta(hours=5)).strftime("%I:%M %p"),
        "theatre": "Cinema 3 - Screen 4 (Dolby)",
        "rows_str": "A,B,C,D,E,F",
        "seats_per_row": 19,
        "ticket_price": 150
    }
}

# Load saved movie configurations from disk if they exist; otherwise use defaults
MOVIES = booking_data.SAVED_MOVIES if booking_data.SAVED_MOVIES else DEFAULT_MOVIES

MASTER_DB = {
    "active_bookings": booking_data.SAVED_BOOKINGS,
    "seats_cache": {"m1": [], "m2": [], "m3": []}
}

# Re-populate local seat cache arrays from storage logs on startup
for bkid, details in MASTER_DB["active_bookings"].items():
    m_id = details.get("movie_id", "m1")
    if m_id in MASTER_DB["seats_cache"]:
        seats_split = [s.strip()
                       for s in details["seats"].split(",") if s.strip()]
        MASTER_DB["seats_cache"][m_id].extend(seats_split)

# ==========================================
# AUTOMATED DISK BACKUP ENGINE
# ==========================================


def save_data_on_shutdown():
    data_file_path = "booking_data.py"
    print(
        "\n💾 [SYSTEM LOG] Closing server safely... Exporting data dictionary structures.")
    with open(data_file_path, "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write(f"SAVED_BOOKINGS = {repr(MASTER_DB['active_bookings'])}\n")
        file.write(f"SAVED_MOVIES = {repr(MOVIES)}\n")
    print("✅ [SYSTEM LOG] Data written successfully to booking_data.py!")


atexit.register(save_data_on_shutdown)

# Helper function to generate clean structural list rows for Jinja compiler templates


def get_rows_list(movie_dict_item):
    return [r.strip() for s in [movie_dict_item.get("rows_str", "A")] for r in s.split(",") if r.strip()]

# Helper function to compute dynamic total seat limitations metric profiles


def get_total_seats(movie_dict_item):
    return len(get_rows_list(movie_dict_item)) * int(movie_dict_item.get("seats_per_row", 10))

# ==========================================
# ROUTE 1: HOMEPAGE (MOVIE GRID LISTING)
# ==========================================


@app.route('/')
def home():
    print(
        f"\n📱 [DEVICE TRACKER] Current phone signature is:\n{request.headers.get('User-Agent')}\n")

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
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="font-size: 28px; margin-bottom: 5px;">&#127887; Cinema Ticket Vault</h1>
            <p style="color:#aaa; margin-top:0;">Select a showtime to proceed with seat selections</p>
            
            <div class="movie-grid">
                {% for mid, m in movies.items() %}
                {% set total_seats = calc_total(m) %}
                {% set remaining = total_seats - cache[mid]|length %}
                
                <div class="movie-card">
                    <div>
                        <h3 style="margin:0 0 10px 0; min-height:50px;">{{ m.movie_title }}</h3>
                        <p style="color:#aaa; font-size:13px; margin:5px 0;">&#128205; {{ m.theatre }}</p>
                        <p style="color:#E50914; font-size:13px; font-weight:bold; margin:5px 0;">&#128338; {{ m.show_time_str }}</p>
                        <p style="color:#25D366; font-size:13px; font-weight:bold; margin:5px 0;">&#128176; &#8377;{{ m.ticket_price }}</p>
                        <p style="font-size:13px; margin:5px 0;">&#127919; Seats: <strong>{{ remaining }}</strong> / {{ total_seats }}</p>
                    </div>
                    
                    {% if remaining <= 0 %}
                        <div class="btn disabled" style="background:#333;">Sold Out</div>
                    {% else %}
                        <a href="/select/{{ mid }}" class="btn">Select Seats</a>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            <br><br>
            <a href="/admin" style="color: #666; text-decoration: none; font-size: 13px;">&#128274; Access Admin Dashboard</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, movies=MOVIES, cache=MASTER_DB["seats_cache"], calc_total=get_total_seats)

# ==========================================
# ROUTE 2: VISUAL SEAT SELECTION SECTOR
# ==========================================


@app.route('/select/<movie_id>')
def select_seats(movie_id):
    if movie_id not in MOVIES:
        return redirect(url_for('home'))

    movie = MOVIES[movie_id]
    already_booked_seats = MASTER_DB["seats_cache"][movie_id]

    movie_rows = get_rows_list(movie)
    seats_per_row = int(movie.get("seats_per_row", 10))
    ticket_price = movie.get("ticket_price", 150)
    remaining_count = get_total_seats(movie) - len(already_booked_seats)

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Select Your Seats</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 20px 10px; margin: 0; text-align: center; }
            .container { background: #1F1F1F; width: 100%; max-width: 850px; margin: 0 auto; padding: 25px; border-radius: 8px; border-top: 4px solid #E50914; box-sizing: border-box; }
            input[type="text"] { width: 100%; max-width: 300px; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #333; background: #333; color: white; box-sizing: border-box; }
            .screen { width: 80%; height: 8px; background: #555; margin: 20px auto 40px auto; border-radius: 4px; box-shadow: 0 4px 10px rgba(255,255,255,0.1); }
            .seating-chart { display: flex; flex-direction: column; gap: 12px; margin-bottom: 30px; overflow-x: auto; padding-bottom: 15px; }
            .seat-row { display: flex; justify-content: center; align-items: center; gap: 6px; min-width: 650px; }
            .row-label { width: 30px; font-weight: bold; color: #888; font-size: 14px; text-align: left; }
            .seat-container { position: relative; width: 26px; height: 26px; }
            .seat-container input { position: absolute; opacity: 0; cursor: pointer; height: 0; width: 0; }
            .seat-design { position: absolute; top: 0; left: 0; height: 26px; width: 26px; background-color: #1F1F1F; border: 1px solid #25D366; color: #25D366; font-size: 10px; font-weight: bold; line-height: 24px; text-align: center; border-radius: 4px; transition: 0.2s; }
            .seat-container:hover input ~ .seat-design { background-color: rgba(37, 211, 102, 0.2); }
            .seat-container input:checked ~ .seat-design { background-color: #25D366; color: black; box-shadow: 0 0 8px #25D366; }
            .seat-container input:disabled ~ .seat-design { background-color: #333 !important; border-color: #444 !important; color: #555 !important; cursor: not-allowed; box-shadow: none; }
            .legend { display: flex; justify-content: center; gap: 20px; margin-bottom: 25px; font-size: 13px; color: #aaa; }
            .legend-item { display: flex; align-items: center; gap: 6px; }
            button { width: 100%; max-width: 300px; padding: 14px; background: #E50914; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 15px; }
            button:disabled { background: #555; cursor: not-allowed; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2 style="margin-bottom:5px;">{{ m.movie_title }}</h2>
            <p style="color: #aaa; font-size: 14px; margin-top:0;">&#128205; {{ m.theatre }}</p>
            
            <div class="screen"></div>
            <p style="font-size:11px; color:#666; margin-top:-30px; margin-bottom:40px; letter-spacing:2px;">SCREEN THIS WAY</p>
            
            <div class="legend">
                <div class="legend-item"><div style="width:14px; height:14px; border:1px solid #25D366; border-radius:2px;"></div> Available</div>
                <div class="legend-item"><div style="width:14px; height:14px; background:#25D366; border-radius:2px;"></div> Selected</div>
                <div class="legend-item"><div style="width:14px; height:14px; background:#333; border-radius:2px;"></div> Booked</div>
            </div>

            <form action="/simulate-payment" method="POST">
                <input type="hidden" name="movie_id" value="{{ mid }}">
                
                <div class="seating-chart">
                    {% for row in rows_list %}
                    <div class="seat-row">
                        <div class="row-label">{{ row }}</div>
                        
                        {% for col in range(1, seats_count + 1) %}
                            {% set seat_id = row ~ (col | string) %}
                            {% set is_booked = seat_id in booked_list %}
                            
                            <label class="seat-container">
                                <input type="checkbox" name="selected_seats" value="{{ seat_id }}" {{ 'disabled' if is_booked }}>
                                <span class="seat-design">{{ "%02d" | format(col) }}</span>
                            </label>
                            
                            {% if col == 7 or col == 17 %}
                                <div style="width: 25px;"></div>
                            {% endif %}
                        {% endfor %}
                    </div>
                    {% endfor %}
                </div>
                
                <label style="display:block; font-size:14px; font-weight:bold; margin-bottom:5px;">Enter Your Full Name:</label>
                <input type="text" name="customer_name" placeholder="John Doe" required><br>

                <label style="display:block; font-size:14px; font-weight:bold; margin-bottom:5px; margin-top:10px;">WhatsApp Phone Number:</label>
                <input type="text" name="phone_number" placeholder="919876543210" required><br>
                
                <button type="submit" id="submit-btn" disabled>Select seats above first</button>
                <br><br>
                <a href="/" style="color:#888; text-decoration:none; font-size:14px;">&larr; Change Movie</a>
            </form>
        </div>

        <script>
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        const submitBtn = document.getElementById('submit-btn');
        const tPrice = {{ price_int }};

        checkboxes.forEach(cb => {
            cb.addEventListener('change', () => {
                const checkedCount = document.querySelectorAll('input[type="checkbox"]:checked').length;
                if (checkedCount > 0) {
                    submitBtn.removeAttribute('disabled');
                    submitBtn.innerText = "Proceed to Pay \u20b9" + (checkedCount * tPrice) + " for " + checkedCount + " Seat(s)";
                    submitBtn.style.background = "#25D366";
                } else {
                    submitBtn.setAttribute('disabled', 'true');
                    submitBtn.innerText = "Select seats above first";
                    submitBtn.style.background = "#E50914";
                }
            });
        });
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, m=movie, mid=movie_id, booked_list=already_booked_seats, rows_list=movie_rows, seats_count=seats_per_row, price_int=ticket_price, remaining=remaining_count, min=min)

# ==========================================
# ROUTE 3: SIMULATED SECURE PAYMENT GATEWAY
# ==========================================


@app.route('/simulate-payment', methods=['POST'])
def simulate_payment():
    movie_id = request.form.get('movie_id')
    customer_name = request.form.get('customer_name').strip()
    user_phone = request.form.get(
        'phone_number').strip().replace("+", "").replace(" ", "")

    selected_seats_list = request.form.getlist('selected_seats')
    ticket_count = len(selected_seats_list)
    seats_comma_string = ", ".join(selected_seats_list)

    ticket_price = MOVIES.get(
        movie_id, {"ticket_price": 150}).get("ticket_price", 150)
    total_price = int(ticket_price) * ticket_count

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
            .option { padding: 12px 15px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; display: flex; align-items: center; font-weight: 500; }
            .option:hover { background-color: #f9f9f9; border-color: #25D366; }
            .spinner { width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #25D366; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="gateway-card" id="box">
            <div class="header">
                <div><h3 style="margin:0; font-size:16px; color:#666;">Cinema Checkout</h3><small style="color:#999;">Seats: {{ seats_str }}</small></div>
                <div style="font-size:22px; font-weight:bold;">&#8377;{{ price }}</div>
            </div>
            
            <p style="font-size:14px; color:#555; margin-bottom:15px; font-weight:bold;">Choose Payment Method:</p>
            <div class="option"><input type="radio" name="pay-method" checked style="margin-right:10px;"> &#128241; UPI (GPay, PhonePe, Paytm)</div>
            <div class="option"><input type="radio" name="pay-method" style="margin-right:10px;"> &#128179; Credit / Debit Card</div>
            <div class="option"><input type="radio" name="pay-method" style="margin-right:10px;"> &#127974; Net Banking</div>
            
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
                window.location.href = "/success?mid=" + "{{ mid }}" + "&seats=" + encodeURIComponent("{{ seats_str }}") + "&name=" + encodeURIComponent("{{ name }}") + "&phone=" + encodeURIComponent("{{ phone }}");
            }, 2500);
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(payment_template, price=total_price, seats_str=seats_comma_string, name=customer_name, mid=movie_id, phone=user_phone)

# ==========================================
# ROUTE 4: CONFIRMATION PREVIEW
# ==========================================


@app.route('/success')
def success():
    movie_id = request.args.get('mid', 'm1')
    seats_string = request.args.get('seats', 'A1')
    customer_name = request.args.get('name', 'Guest')
    user_phone = request.args.get('phone', 'N/A')

    incoming_seats_list = [s.strip()
                           for s in seats_string.split(",") if s.strip()]
    MASTER_DB["seats_cache"][movie_id].extend(incoming_seats_list)

    booking_id = f"BKID{int(time.time())}"

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
            <h1 style="color: #25D366; font-size: 24px;">&#127881; Seats Confirmed!</h1>
            <p>Thank you <strong>{{ name }}</strong>. Your positions (<strong>{{ seats }}</strong>) are locked.</p>
            <img src="{{ img_src }}" alt="Movie Ticket" class="ticket-preview">
            <hr style="border-color: #333; margin: 20px 0;">
            <a href="{{ dl_src }}" class="btn">&#128131; Download Ticket Image</a><br><br>
            <a href="/" style="color:#888; text-decoration:none; font-size:14px;">&larr; Back to Home</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(success_template, seats=seats_string, name=customer_name, img_src=img_src, dl_src=dl_src)

# ==========================================
# ROUTE 5: THE CORE TICKET COMPILER ENGINE
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

    movie_title = MOVIES.get(movie_id, {}).get("movie_title", "Cinema Ticket")
    theatre_name = MOVIES.get(movie_id, {}).get("theatre", "Cinema Arena")
    show_time_str = MOVIES.get(movie_id, {}).get("show_time_str", "Today")

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
# ROUTE 6: SECURE GATEKEEPER TICKET SCAN CHECKER (ONE-TIME SCAN LOCK)
# ==========================================


@app.route('/verify/<booking_id>')
def verify_ticket_route(booking_id):
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()

    # Strict hardware device signature fingerprint checker framework
    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        print(
            f"Blocked scan attempt from unauthorized device: {scanned_device_user_agent}")
        return """
        <body style="background:#141414; color:#FF4A4A; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #FF4A4A; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2>&#128274; ACCESS DENIED</h2>
                <p style="color:#aaa; font-size:14px; line-height:1.5;">This scanner device does not possess authorized admin credentials framework.</p>
            </div>
        </body>
        """, 403

    active_records = MASTER_DB["active_bookings"]
    if booking_id in active_records:
        t = active_records[booking_id]
        m_title = MOVIES.get(t.get("movie_id", "m1"), {}).get(
            "movie_title", "Unknown Show")

        # Grab the ticket's current scanning state (defaults to 'Active' if newly booked)
        ticket_status = t.get("status", "Active")
        checkin_time = t.get("checked_in_at", "")

        # 🛑 FRAUD WARNING GATE: If the status is already 'Checked In', block entry immediately!
        if ticket_status == "Checked In":
            denied_template = """
            <body style="background:#141414; color:white; font-family:Arial, sans-serif; text-align:center; padding-top:40px;">
                <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #FFCC00; text-align:left; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                    <div style="background:#FFCC00; color:black; font-weight:bold; padding:5px 10px; display:inline-block; border-radius:4px; margin-bottom:15px; font-size:13px;">&#9888; TICKET ALREADY USED</div>
                    <h3 style="margin:0 0 15px 0; font-size:20px; color:#FFCC00;">Fraud Alert: Access Denied</h3>
                    <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Holder:</strong> {{ t.name }}</p>
                    <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Seats:</strong> <span style="color:#E50914; font-weight:bold;">{{ t.seats }}</span></p>
                    <p style="margin:15px 0 0 0; font-size:12px; color:#FF4A4A; border-top:1px solid #333; padding-top:10px; font-weight:bold;">
                        &#128680; Used Entry Pass Scanned at: {{ checkin_time }}
                    </p>
                </div>
            </body>
            """
            return render_template_string(denied_template, t=t)

        #  VALID FIRST-TIME ENTRY HANDSHAKE: Flip status tokens inside database mapping profiles
        current_scan_time = datetime.now().strftime("%I:%M:%S %p")
        t["status"] = "Checked In"
        t["checked_in_at"] = current_scan_time

        approved_template = """
        <body style="background:#141414; color:white; font-family:Arial, sans-serif; text-align:center; padding-top:40px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #25D366; text-align:left; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <div style="background:#25D366; color:black; font-weight:bold; padding:5px 10px; display:inline-block; border-radius:4px; margin-bottom:15px; font-size:13px;">&nbsp; APPROVED ENTRY</div>
                <h3 style="margin:0 0 15px 0; font-size:20px;">{{ title }}</h3>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Holder:</strong> {{ t.name }}</p>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Seats:</strong> <span style="color:#E50914; font-weight:bold;">{{ t.seats }}</span></p>
                <p style="margin:8px 0; font-size:14px;"><strong style="color:#888;">Phone:</strong> +{{ t.phone }}</p>
                <p style="margin:15px 0 0 0; font-size:12px; color:#25D366; border-top:1px solid #333; padding-top:10px; font-weight:bold;">
                    &#9989; Check-in Log Locked at: {{ current_scan_time }}
                </p>
            </div>
        </body>
        """
        return render_template_string(approved_template, t=t, title=m_title, current_scan_time=current_scan_time)

    return """
    <body style="background:#141414; color:#E50914; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
        <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #E50914; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
            <h2>&nbsp; ACCESS DENIED</h2>
            <p style="color:#aaa; font-size:14px;">The scanned log reference code was not registered in our database catalog files.</p>
        </div>
    </body>
    """, 404

# ==========================================
# ROUTE 7: HIDDEN ADMIN SEATING DASHBOARD + LIVE CONFIG EDITOR
# ==========================================


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()

    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        print(
            f"Blocked unauthorized dashboard access attempt from: {scanned_device_user_agent}")
        return """
        <body style="background:#141414; color:#FF4A4A; font-family:Arial, sans-serif; text-align:center; padding-top:100px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:35px; border-radius:8px; border-top:5px solid #FF4A4A; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h2>&#128274; ACCESS DENIED</h2>
                <p style="color:#aaa; font-size:14px; line-height:1.6;">Your device signature does not match administrator credentials.</p>
            </div>
        </body>
        """, 403

    if request.method == 'POST':
        m_id = request.form.get("update_movie_id")
        if m_id in MOVIES:
            MOVIES[m_id]["movie_title"] = request.form.get(
                "movie_title").strip()
            MOVIES[m_id]["show_time_str"] = request.form.get(
                "show_time_str").strip()
            MOVIES[m_id]["theatre"] = request.form.get("theatre").strip()
            MOVIES[m_id]["rows_str"] = request.form.get(
                "rows_str").strip().upper()
            MOVIES[m_id]["seats_per_row"] = int(
                request.form.get("seats_per_row"))
            MOVIES[m_id]["ticket_price"] = int(
                request.form.get("ticket_price"))
            print(f"✨ [ADMIN CONFIG] Updated settings for {m_id} instantly!")
            return redirect(url_for('admin_dashboard'))

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Registry & Config Control</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 40px 15px; margin: 0; }
            .wrapper { max-width: 1100px; margin: 0 auto; }
            h2, h3 { color: white; border-bottom: 2px solid #333; padding-bottom: 8px; }
            .config-section { display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 40px; justify-content: space-between; }
            .config-form { background: #1F1F1F; border-radius: 6px; padding: 15px; width: 31%; box-sizing: border-box; border-top: 3px solid #25D366; }
            label { font-size: 11px; font-weight: bold; color: #888; display: block; margin-top: 8px; }
            input { width: 100%; padding: 6px; margin-top: 2px; background: #333; color: white; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; }
            .btn-save { width: 100%; margin-top: 12px; padding: 8px; background: #25D366; color: black; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 25px; background:#1F1F1F; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }
            th, td { padding: 14px; border: 1px solid #333; text-align: left; font-size:14px; }
            th { background-color: #E50914; color: white; font-weight: bold; }
            .btn-wipe { display: inline-block; padding: 10px 20px; background-color: #FF4A4A; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size:13px; }
        </style>
    </head>
    <body>
        <div class="wrapper">
            <h2>&#128274; Master Theater Settings Configuration</h2>
            <p style="color:#aaa; margin-top:0;">Modify active slot parameters, naming fields, and layout row charts directly from your device.</p>
            
            <div class="config-section">
                {% for mid, m in movies.items() %}
                <form class="config-form" method="POST">
                    <input type="hidden" name="update_movie_id" value="{{ mid }}">
                    <strong style="color: #25D366;">Slot: {{ mid | upper }}</strong>
                    
                    <label>MOVIE TITLE:</label>
                    <input type="text" name="movie_title" value="{{ m.movie_title }}" required>
                    
                    <label>SHOWTIME TEXT:</label>
                    <input type="text" name="show_time_str" value="{{ m.show_time_str }}" required>
                    
                    <label>AUDITORIUM / HALL:</label>
                    <input type="text" name="theatre" value="{{ m.theatre }}" required>
                    
                    <label>GRID ROWS (Comma Separated):</label>
                    <input type="text" name="rows_str" value="{{ m.rows_str }}" required>
                    
                    <label>SEATS PER ROW (Columns Count):</label>
                    <input type="number" name="seats_per_row" value="{{ m.seats_per_row }}" required>
                    
                    <label>TICKET RATE (INR):</label>
                    <input type="number" name="ticket_price" value="{{ m.ticket_price }}" required>
                    
                    <button type="submit" class="btn-save">&#128190; Update Slot</button>
                </form>
                {% endfor %}
            </div>

            <h3>&#128196; Active Seating Registry & Logs</h3>
            <div style="margin-top: 20px;">
                <a href="/admin/wipe-logs" class="btn-wipe" onclick="return confirm('Wipe out all database log arrays entirely?');">&#128680; Wipe All Booking Data</a>
                &nbsp;&nbsp;&nbsp;&nbsp;<a href="/" style="color:#aaa; text-decoration:none; font-size:14px;">&larr; Back to Client Homepage</a>
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
                    <td>{{ movies[t.movie_id]["movie_title"] if t.movie_id in movies else 'Unknown Show' }}</td>
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
    return render_template_string(html_template, logs=MASTER_DB["active_bookings"], movies=MOVIES)


@app.route('/admin/wipe-logs')
def wipe_logs():
    scanned_device_user_agent = request.headers.get('User-Agent', '').lower()
    if MY_PHONE_SIGNATURE.lower() not in scanned_device_user_agent:
        return "Unauthorized", 403

    MASTER_DB["active_bookings"].clear()
    MASTER_DB["seats_cache"] = {"m1": [], "m2": [], "m3": []}
    with open("booking_data.py", "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write(f"SAVED_BOOKINGS = {{}}\n")
        file.write(f"SAVED_MOVIES = {repr(MOVIES)}\n")
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
    print(f"MULTI-MOVIE SYSTEM ACTIVE ON LOCAL WI-FI PORTAL!")
    print(f"Client Homepage Link: http://{local_ip}:5000")
    print(f"Secret Admin Control Dashboard: http://{local_ip}:5000/admin")
    print("="*50 + "\n")

    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=5000)
