import io
import urllib.parse
import time
import atexit
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, send_file, redirect, url_for, session

# Safely import the separate permanent data storage file
import booking_data
if not hasattr(booking_data, 'SAVED_BOOKINGS'):
    booking_data.SAVED_BOOKINGS = {}
if not hasattr(booking_data, 'SAVED_MOVIES'):
    booking_data.SAVED_MOVIES = {}
if not hasattr(booking_data, 'SAVED_CONCESSIONS'):
    booking_data.SAVED_CONCESSIONS = {}
if not hasattr(booking_data, 'SAVED_PROMOS'):
    booking_data.SAVED_PROMOS = {}
# Add this initialization line right where the other SAVED configurations load
if not hasattr(booking_data, 'SAVED_REVIEWS'):
    booking_data.SAVED_REVIEWS = []

REVIEWS = booking_data.SAVED_REVIEWS if booking_data.SAVED_REVIEWS else []


app = Flask(__name__)
app.secret_key = "cinema_vault_session_protection_string"

# ==========================================
# MASTER SECRET SECURITY PASSPHRASE
# ==========================================
ADMIN_PASSWORD = "lazy_panda_66_admin"

# ==========================================
# MASTER PROGRAM CONFIGURATIONS & DATABASE
# ==========================================
NOW = datetime.now()

DEFAULT_MOVIES = {
    "m1": {"movie_title": "Interstellar: Special Edition", "show_time_str": "06:15 PM", "theatre": "Cinema 4 (IMAX)", "rows_str": "A,B,C,D,E", "seats_per_row": 23, "ticket_price": 150},
    "m2": {"movie_title": "Oppenheimer: 70mm Film", "show_time_str": "03:30 PM", "theatre": "Cinema 1 (IMAX)", "rows_str": "A,B,C,D", "seats_per_row": 17, "ticket_price": 150},
    "m3": {"movie_title": "Dune: Part Two", "show_time_str": "09:00 PM", "theatre": "Cinema 3 (Dolby)", "rows_str": "A,B,C,D,E,F", "seats_per_row": 19, "ticket_price": 150}
}

DEFAULT_CONCESSIONS = {
    "snack1": {"item_name": "🍿 Large Salted Popcorn", "item_price": 180},
    "snack2": {"item_name": "🥤 Ice Cold Drink", "item_price": 120},
    "snack3": {"item_name": "🍫 Crispy Nachos Combo", "item_price": 250}
}

DEFAULT_PROMOS = {
    "POPCORN20": {"discount_type": "percentage", "value": 20},
    "CINEMAFAN": {"discount_type": "flat", "value": 50}
}

MOVIES = booking_data.SAVED_MOVIES if booking_data.SAVED_MOVIES else DEFAULT_MOVIES
CONCESSIONS = booking_data.SAVED_CONCESSIONS if booking_data.SAVED_CONCESSIONS else DEFAULT_CONCESSIONS
PROMOS = booking_data.SAVED_PROMOS if booking_data.SAVED_PROMOS else DEFAULT_PROMOS
# ==========================================
# MASTER PROGRAM CONFIGURATIONS & DATABASE (FIXED FOR ALERTS)
# ==========================================
MASTER_DB = {
    "active_bookings": booking_data.SAVED_BOOKINGS,
    "seats_cache": {"m1": [], "m2": [], "m3": []},
    "assistance_queue": [],
    "live_chats_database": {},
    # 🟢 FIXED: Add this line to prevent the admin dashboard KeyError crash!
    "live_assistance_alerts": {}
}


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
    with open("booking_data.py", "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write(f"SAVED_BOOKINGS = {repr(MASTER_DB['active_bookings'])}\n")
        file.write(f"SAVED_MOVIES = {repr(MOVIES)}\n")
        file.write(f"SAVED_CONCESSIONS = {repr(CONCESSIONS)}\n")
        file.write(f"SAVED_PROMOS = {repr(PROMOS)}\n")
        # ADD THIS LINE INSIDE THE SHUTDOWN WRITER:
        file.write(f"SAVED_REVIEWS = {repr(REVIEWS)}\n")


atexit.register(save_data_on_shutdown)


def get_rows_list(movie_dict_item):
    return [r.strip() for s in [movie_dict_item.get("rows_str", "A")] for r in s.split(",") if r.strip()]


def get_total_seats(movie_dict_item):
    return len(get_rows_list(movie_dict_item)) * int(movie_dict_item.get("seats_per_row", 10))

# ==========================================
# ROUTE 1: HOMEPAGE (MOVIE GRID LISTING WITH AI SUPPORT BUTTON)
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
                        <p style="color:#E50914; font-size:13px; font-weight:bold; margin:5px 0;">&#128338; Showtime: {{ m.show_time_str }}</p>
                        <p style="color:#25D366; font-size:13px; font-weight:bold; margin:5px 0;">&#128176; Base Rate: &#8377;{{ m.ticket_price }}</p>
                        <p style="font-size:13px; margin:5px 0;">&#127919; Seats Available: <strong>{{ remaining }}</strong> / {{ total_seats }}</p>
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
            
            <!-- 🤖 ADDED FRONTEND LINK LINK: This renders the AI Concierge shortcut directly on the main site -->
            <a href="/support" style="display:inline-block; padding:12px 24px; background:#262626; color:#25D366; border:1px solid #25D366; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px; transition: 0.2s;">
                🤖 Open Customer Support AI
            </a>

            <br><br>
            <!-- Add this link directly beside your Open AI link button box -->
            <a href="/reviews" style="display:inline-block; padding:12px 24px; background:#262626; color:#FFD700; border:1px solid #FFD700; border-radius:4px; text-decoration:none; font-weight:bold; font-size:13px; transition: 0.2s; margin-left:10px;">
                ⭐ Audience Reviews Board
            </a>

            
            <br><br>
            <a href="/admin" style="color: #666; text-decoration: none; font-size: 13px;">&#128274; Access Admin Dashboard</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, movies=MOVIES, cache=MASTER_DB["seats_cache"], calc_total=get_total_seats)

# ==========================================
# ROUTE 2: VISUAL SEAT SELECTION & CONCESSIONS CART
# ==========================================


@app.route('/select/<movie_id>')
def select_seats(movie_id):
    if movie_id not in MOVIES:
        return redirect(url_for('home'))
    movie = MOVIES[movie_id]
    already_booked_seats = MASTER_DB["seats_cache"][movie_id]
    movie_rows = get_rows_list(movie)
    seats_per_row = int(movie.get("seats_per_row", 10))
    base_price = int(movie.get("ticket_price", 150))
    premium_price = base_price + 100

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Select Seats & Snacks</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 20px 10px; margin: 0; text-align: center; }
            .container { background: #1F1F1F; width: 100%; max-width: 850px; margin: 0 auto; padding: 25px; border-radius: 8px; border-top: 4px solid #E50914; box-sizing: border-box; }
            input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #333; background: #333; color: white; box-sizing: border-box; font-size:16px; }
            .screen { width: 80%; height: 8px; background: #555; margin: 20px auto 40px auto; border-radius: 4px; }
            .seating-chart { display: flex; flex-direction: column; gap: 12px; margin-bottom: 30px; overflow-x: auto; padding-bottom: 15px; }
            .seat-row { display: flex; justify-content: center; align-items: center; gap: 6px; min-width: 650px; }
            .row-label { width: 35px; font-weight: bold; color: #888; font-size: 13px; text-align: left; }
            .seat-container { position: relative; width: 26px; height: 26px; }
            .seat-container input { position: absolute; opacity: 0; height: 0; width: 0; }
            .seat-design { position: absolute; top: 0; left: 0; height: 26px; width: 26px; background-color: #1F1F1F; font-size: 10px; font-weight: bold; line-height: 24px; text-align: center; border-radius: 4px; }
            .tier-vip .seat-design { border: 1px solid #FFD700; color: #FFD700; }
            .tier-vip input:checked ~ .seat-design { background-color: #FFD700; color: black; }
            .tier-classic .seat-design { border: 1px solid #25D366; color: #25D366; }
            .tier-classic input:checked ~ .seat-design { background-color: #25D366; color: black; }
            .seat-container input:disabled ~ .seat-design { background-color: #333 !important; border-color: #444 !important; color: #555 !important; cursor: not-allowed; }
            .legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 15px; margin-bottom: 25px; font-size: 13px; color: #aaa; }
            .legend-item { display: flex; align-items: center; gap: 6px; }
            
            .snack-box { background: #141414; padding: 15px; border-radius: 6px; margin: 25px auto; max-width: 500px; text-align: left; border: 1px solid #333; }
            .snack-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #222; }
            button { width: 100%; max-width: 400px; padding: 14px; background: #444; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>{{ m.movie_title }}</h2>
            <p style="color: #aaa; font-size: 14px;">&#128205; {{ m.theatre }} | &#128338; {{ m.show_time_str }}</p>
            <div class="screen"></div>
            
            <div class="legend">
                <div class="legend-item"><div style="width:14px; height:14px; border:1px solid #FFD700; border-radius:2px;"></div> VIP Recliner (&#8377;{{ p_price }})</div>
                <div class="legend-item"><div style="width:14px; height:14px; border:1px solid #25D366; border-radius:2px;"></div> Classic Row (&#8377;{{ b_price }})</div>
                <div class="legend-item"><div style="width:14px; height:14px; background:#333; border-radius:2px;"></div> Booked</div>
            </div>

            <form action="/simulate-payment" method="POST">
                <input type="hidden" name="movie_id" value="{{ mid }}">
                
                <div class="seating-chart">
                    {% for row in rows_list %}
                    {% set is_vip = row in ['A', 'B'] %}
                    <div class="seat-row">
                        <div class="row-label">{{ row }} {{ '(VIP)' if is_vip else '' }}</div>
                        {% for col in range(1, seats_count + 1) %}
                            {% set seat_id = row ~ (col | string) %}
                            {% set is_booked = seat_id in booked_list %}
                            <label class="seat-container {{ 'tier-vip' if is_vip else 'tier-classic' }}">
                                <input type="checkbox" name="selected_seats" value="{{ seat_id }}" data-price="{{ p_price if is_vip else b_price }}" {{ 'disabled' if is_booked }}>
                                <span class="seat-design">{{ "%02d" | format(col) }}</span>
                            </label>
                            {% if col == 7 or col == 17 %}<div style="width: 25px;"></div>{% endif %}
                        {% endfor %}
                    </div>
                    {% endfor %}
                </div>

                <div class="snack-box">
                    <h3 style="margin-top:0; color:#E50914; font-size:16px;">&#127839; Food & Beverages Counter Add-ons</h3>
                    {% for sid, snack in concessions.items() %}
                    <div class="snack-item">
                        <label><input type="checkbox" name="selected_snacks" value="{{ sid }}" data-price="{{ snack.item_price }}"> {{ snack.item_name }}</label>
                        <span style="color:#25D366; font-weight:bold;">+&#8377;{{ snack.item_price }}</span>
                    </div>
                    {% endfor %}
                </div>

                <div style="margin: 20px auto; max-width: 500px; text-align: left;">
                    <label style="font-weight:bold; font-size:14px; color:#aaa;">Apply Promo Coupon Code:</label>
                    <input type="text" name="coupon_code" placeholder="e.g., POPCORN20" style="max-width:200px; text-transform:uppercase;">
                </div>
                
                <div style="margin-top:20px;">
                    <label style="display:block; font-size:14px; font-weight:bold; margin-bottom:5px;">Enter Your Full Name:</label>
                    <input type="text" name="customer_name" placeholder="John Doe" required style="max-width:400px;"><br>
                    <label style="display:block; font-size:14px; font-weight:bold; margin-bottom:5px; margin-top:10px;">WhatsApp Phone Number:</label>
                    <input type="text" name="phone_number" placeholder="919876543210" required style="max-width:400px;"><br>
                </div>
                
                <button type="submit" id="submit-btn" disabled>Select seats above first</button>
            </form>
        </div>

        <script>
        const checkboxes = document.querySelectorAll('input[name="selected_seats"]');
        const snackboxes = document.querySelectorAll('input[name="selected_snacks"]');
        const submitBtn = document.getElementById('submit-btn');

        function calculateCart() {
            let totalCost = 0;
            let checkedSeats = 0;
            
            checkboxes.forEach(box => { if (box.checked) { totalCost += parseInt(box.getAttribute('data-price')); checkedSeats++; } });
            snackboxes.forEach(box => { if (box.checked) { totalCost += parseInt(box.getAttribute('data-price')); } });

            if (checkedSeats > 0) {
                submitBtn.removeAttribute('disabled');
                submitBtn.innerText = "Proceed to Pay \u20b9" + totalCost + " for " + checkedSeats + " Ticket(s)";
                submitBtn.style.background = "#25D366";
                submitBtn.style.color = "black";
            } else {
                submitBtn.setAttribute('disabled', 'true');
                submitBtn.innerText = "Select seats above first";
                submitBtn.style.background = "#444";
                submitBtn.style.color = "white";
            }
        }
        checkboxes.forEach(cb => cb.addEventListener('change', calculateCart));
        snackboxes.forEach(sb => sb.addEventListener('change', calculateCart));
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, m=movie, mid=movie_id, booked_list=already_booked_seats, rows_list=movie_rows, seats_count=seats_per_row, b_price=base_price, p_price=premium_price, concessions=CONCESSIONS)

# ==========================================
# ROUTE 3: SIMULATED SECURE PAYMENT GATEWAY (FIXED VARIABLE NAME)
# ==========================================


@app.route('/simulate-payment', methods=['POST'])
def simulate_payment():
    movie_id = request.form.get('movie_id')
    customer_name = request.form.get('customer_name').strip()
    user_phone = request.form.get(
        'phone_number').strip().replace("+", "").replace(" ", "")
    coupon_entered = request.form.get('coupon_code', '').strip().upper()

    selected_seats = request.form.getlist('selected_seats')
    selected_snacks = request.form.getlist('selected_snacks')

    movie_data = MOVIES.get(movie_id, {"ticket_price": 150})
    base_price = int(movie_data.get("ticket_price", 150))
    premium_price = base_price + 100

    subtotal = 0
    for seat in selected_seats:
        subtotal += premium_price if seat.upper() in ['A', 'B'] else base_price

    snack_names_list = []
    for sid in selected_snacks:
        if sid in CONCESSIONS:
            subtotal += int(CONCESSIONS[sid]["item_price"])
            snack_names_list.append(CONCESSIONS[sid]["item_name"])

    # FIXED: This matches the string variable token loaded below [1.1]
    seats_str = ", ".join(selected_seats)
    snacks_string = ", ".join(snack_names_list) if snack_names_list else "None"

    discount_applied = 0
    promo_msg = "None"
    if coupon_entered in PROMOS:
        rules = PROMOS[coupon_entered]
        if rules["discount_type"] == "percentage":
            discount_applied = int(subtotal * (rules["value"] / 100))
            promo_msg = f"{coupon_entered} (-{rules['value']}% Code Applied)"
        else:
            discount_applied = int(rules["value"])
            promo_msg = f"{coupon_entered} (-&#8377;{rules['value']} Flat Code Applied)"

    final_payable_amount = max(0, subtotal - discount_applied)

    payment_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Secure Payment Sandbox</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; color: #333; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .gateway-card { background: white; width: 100%; max-width: 420px; padding: 25px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-top: 5px solid #25D366; text-align: left; box-sizing: border-box; }
            .header { border-bottom: 2px solid #f0f0f0; padding-bottom: 15px; margin-bottom: 15px; }
            .row-cost { display:flex; justify-content:space-between; font-size:14px; color:#555; margin-bottom:6px; }
            .option { padding: 12px 15px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; display: flex; align-items: center; font-weight: 500; }
            .spinner { width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #25D366; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="gateway-card" id="box">
            <div class="header">
                <h3 style="margin:0; color:#111;">Checkout Payment Summary</h3>
                <small style="color:#888;">Seats: {{ seats_str }} | Snacks: {{ snacks_str }}</small>
            </div>
            
            <div class="row-cost"><span>Cart Subtotal:</span><span>&#8377;{{ subtotal }}</span></div>
            <div class="row-cost" style="color:#FF4A4A;"><span>Coupon Reduction:</span><span>-&#8377;{{ discount }} ({{ p_msg | safe }})</span></div>
            <div class="row-cost" style="font-weight:bold; font-size:18px; color:black; border-top:1px dashed #ddd; padding-top:8px; margin-top:8px;">
                <span>Total Amount:</span><span>&#8377;{{ final_amount }}</span>
            </div>
            <br>
            <p style="font-size:13px; color:#555; margin-bottom:10px; font-weight:bold;">Select Wallet Gateway:</p>
            <div class="option"><input type="radio" checked style="margin-right:10px;"> 📱 UPI (GPay, PhonePe, Paytm)</div>
            <div class="option"><input type="radio" style="margin-right:10px;"> 💳 Credit / Debit Card</div>
            
            <button style="width:100%; padding:14px; background:#25D366; border:none; color:black; font-weight:bold; border-radius:6px; cursor:pointer; font-size:16px; margin-top:10px;" onclick="pay()">Complete Simulation Payment</button>
        </div>
        <div class="gateway-card" id="load" style="display:none; text-align:center;"><div class="spinner"></div><h3>Processing Simulation...</h3></div>
        <script>
        function pay() {
            document.getElementById('box').style.display = 'none';
            document.getElementById('load').style.display = 'block';
            setTimeout(function() {
                window.location.href = "/success?mid=" + "{{ mid }}" + "&seats=" + encodeURIComponent("{{ seats_str }}") + "&snacks=" + encodeURIComponent("{{ snacks_str }}") + "&name=" + encodeURIComponent("{{ name }}") + "&phone=" + encodeURIComponent("{{ phone }}");
            }, 2500);
        }
        </script>
    </body>
    </html>
    """
    return render_template_string(payment_template, subtotal=subtotal, discount=discount_applied, p_msg=promo_msg, final_amount=final_payable_amount, seats_str=seats_str, snacks_str=snacks_string, name=customer_name, mid=movie_id, phone=user_phone)

# ==========================================
# ROUTE 4: CONFIRMATION PREVIEW
# ==========================================


@app.route('/success')
def success():
    movie_id = request.args.get('mid', 'm1')
    seats_string = request.args.get('seats', 'A1')
    snacks_string = request.args.get('snacks', 'None')
    customer_name = request.args.get('name', 'Guest')
    user_phone = request.args.get('phone', 'N/A')

    incoming_seats_list = [s.strip()
                           for s in seats_string.split(",") if s.strip()]
    MASTER_DB["seats_cache"][movie_id].extend(incoming_seats_list)
    booking_id = f"BKID{int(time.time())}"

    MASTER_DB["active_bookings"][booking_id] = {
        "movie_id": movie_id, "name": customer_name, "seats": seats_string, "snacks": snacks_string, "phone": user_phone, "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M %p")
    }

    img_src = f"/download-ticket?seats={urllib.parse.quote(seats_string)}&snacks={urllib.parse.quote(snacks_string)}&name={urllib.parse.quote(customer_name)}&mid={movie_id}&bkid={booking_id}"
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
            .btn { display: inline-block; width: 100%; max-width: 280px; padding: 14px; background-color: #E50914; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 20px; font-size: 16px; }
            .ticket-preview { width: 100%; max-width: 480px; height: auto; margin-top: 15px; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.6); display: block; margin: 15px auto; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1 style="color: #25D366; font-size: 24px;">&#127881; Seats Confirmed!</h1>
            <p>Thank you <strong>{{ name }}</strong>. Your configuration is locked layout.</p>
            <img src="{{ img_src }}" alt="Movie Ticket" class="ticket-preview">
            <hr style="border-color: #333; margin: 20px 0;">
            <a href="{{ dl_src }}" class="btn">&#128131; Download Ticket Image</a><br><br>
            <a href="/" style="color:#888; text-decoration:none; font-size:14px;">&larr; Back to Home</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(success_template, name=customer_name, img_src=img_src, dl_src=dl_src)

# ==========================================
# ROUTE 5: THE TICKET IMAGE COMPILER (WITH SNACK PRINT SUPPORT)
# ==========================================


@app.route('/download-ticket')
def download_ticket_route():
    from PIL import Image, ImageDraw, ImageFont
    import qrcode

    seats_param = request.args.get('seats', 'Standard Pass')
    snacks_param = request.args.get('snacks', 'None')
    name_param = request.args.get('name', 'Guest')
    movie_id = request.args.get('mid', 'm1')
    bkid_param = request.args.get('bkid', 'UNKNOWN')
    should_download = request.args.get('download', 'false') == 'true'

    movie_title = MOVIES.get(movie_id, {}).get("movie_title", "Cinema Ticket")
    theatre_name = MOVIES.get(movie_id, {}).get("theatre", "Cinema Arena")
    show_time_str = MOVIES.get(movie_id, {}).get("show_time_str", "Today")

    ticket = Image.new("RGB", (750, 360), "#1A1A1A")
    draw = ImageDraw.Draw(ticket)

    try:
        font_title = ImageFont.truetype("Apple_Chancery.ttf", 34)
        font_body = ImageFont.truetype("Arial.ttf", 15)
        font_label = ImageFont.truetype("Arial.ttf", 11)
    except IOError:
        try:
            font_title = ImageFont.truetype("georgia.ttf", 30)
            font_body = ImageFont.truetype("arial.ttf", 15)
            font_label = ImageFont.truetype("arial.ttf", 11)
        except IOError:
            font_title = font_body = font_label = ImageFont.load_default()

    draw.rectangle([(0, 0), (750, 15)], fill="#E50914")
    draw.text((40, 35), movie_title, fill="#FFFFFF", font=font_title)
    draw.text((40, 95), "TICKET HOLDER", fill="#888888", font=font_label)
    draw.text((40, 115), name_param, fill="#FFFFFF", font=font_body)
    draw.text((40, 155), "DATE, TIME & CINEMA",
              fill="#888888", font=font_label)
    draw.text((40, 175), f"{show_time_str} | {theatre_name}",
              fill="#FFFFFF", font=font_body)
    draw.text((40, 215), "SEATS SELECTED", fill="#888888", font=font_label)
    draw.text((40, 235), seats_param, fill="#E50914", font=font_body)

    # Draw Concession food orders on the ticket file pass [1.1]
    draw.text((40, 275), "SNACK BAR RELEASES COUNTER",
              fill="#888888", font=font_label)
    draw.text((40, 295), snacks_param, fill="#25D366", font=font_body)

    validation_url = f"{request.url_root}verify/{bkid_param}"
    qr = qrcode.QRCode(
        version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(validation_url)
    qr.make(fit=True)
    qr_img = qr.make_image(
        fill_color="black", back_color="white").convert('RGB')
    ticket.paste(qr_img, (510, (360 - qr_img.height) // 2))

    img_io = io.BytesIO()
    ticket.convert("RGB").save(img_io, 'JPEG')
    img_io.seek(0)

    if should_download:
        return send_file(img_io, mimetype='image/jpeg', as_attachment=True, download_name='movie_ticket.jpg')
    return send_file(img_io, mimetype='image/jpeg')

# ==========================================
# ROUTE 6: SECURE GATEKEEPER SCAN CHECKER (ONE-TIME VERIFIER)
# ==========================================


@app.route('/verify/<booking_id>', methods=['GET', 'POST'])
def verify_ticket_route(booking_id):
    if request.method == 'POST' and 'login_password' in request.form:
        if request.form.get('login_password').strip() == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('verify_ticket_route', booking_id=booking_id))
        else:
            return render_template_string(admin_login_template(), error="Incorrect password! Try again.")

    if not session.get('admin_logged_in'):
        return render_template_string(admin_login_template())

    active_records = MASTER_DB["active_bookings"]
    if booking_id in active_records:
        t = active_records[booking_id]
        m_title = MOVIES.get(t.get("movie_id", "m1"), {}).get(
            "movie_title", "Unknown Show")
        ticket_status = t.get("status", "Active")
        checkin_time = t.get("checked_in_at", "")

        if ticket_status == "Checked In":
            denied_template = """
            <body style="background:#141414; color:white; font-family:Arial, sans-serif; text-align:center; padding-top:40px;">
                <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #FFCC00; text-align:left;">
                    <div style="background:#FFCC00; color:black; font-weight:bold; padding:5px 10px; display:inline-block; border-radius:4px; margin-bottom:15px; font-size:13px;">&#9888; TICKET ALREADY USED</div>
                    <h3>Fraud Alert: Access Denied</h3>
                    <p><strong style="color:#888;">Holder:</strong> {{ t.name }}</p>
                    <p><strong style="color:#888;">Seats:</strong> <span style="color:#E50914;">{{ t.seats }}</span></p>
                    <p><strong style="color:#888;">Snacks Pack:</strong> {{ t.get('snacks','None') }}</p>
                    <p style="color:#FF4A4A; border-top:1px solid #333; padding-top:10px; font-weight:bold;">&#128680; Scanned and entry locked at: {{ checkin_time }}</p>
                </div>
            </body>
            """
            return render_template_string(denied_template, t=t)

        current_scan_time = datetime.now().strftime("%I:%M:%S %p")
        t["status"] = "Checked In"
        t["checked_in_at"] = current_scan_time

        approved_template = """
        <body style="background:#141414; color:white; font-family:Arial, sans-serif; text-align:center; padding-top:40px;">
            <div style="background:#1F1F1F; max-width:400px; margin:0 auto; padding:30px; border-radius:8px; border-top:5px solid #25D366; text-align:left;">
                <div style="background:#25D366; color:black; font-weight:bold; padding:5px 10px; display:inline-block; border-radius:4px; margin-bottom:15px;">&nbsp; APPROVED ENTRY</div>
                <h3>{{ title }}</h3>
                <p><strong style="color:#888;">Holder:</strong> {{ t.name }}</p>
                <p><strong style="color:#888;">Seats:</strong> <span style="color:#E50914; font-weight:bold;">{{ t.seats }}</span></p>
                <p><strong style="color:#888;">Snacks Pack:</strong> <span style="color:#25D366;">{{ t.get('snacks','None') }}</span></p>
                <p style="color:#25D366; border-top:1px solid #333; padding-top:10px; font-weight:bold;">&#9989; Check-in Complete at: {{ current_scan_time }}</p>
            </div>
        </body>
        """
        return render_template_string(approved_template, t=t, title=m_title, current_scan_time=current_scan_time)
    return "Ticket Not Found", 404

# ==========================================
# ROUTE 7: DYNAMIC ADMIN PANEL (ALL EDITORS CONSOLIDATED)
# ==========================================


@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    # 1. ENFORCE SECURITY LOGIN PROMPT PASSWORD GATE
    if request.method == 'POST' and 'login_password' in request.form:
        if request.form.get('login_password').strip() == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template_string(admin_login_template(), error="Incorrect password! Try again.")

    if not session.get('admin_logged_in'):
        return render_template_string(admin_login_template())

    # 2. DETECT AND EXECUTE ACTIVE POST SUBMISSIONS FROM WORKSPACE FORMS
    if request.method == 'POST':
        action_type = request.form.get("action_type")

        if action_type == "update_movie":
            mid = request.form.get("update_movie_id")
            if mid in MOVIES:
                MOVIES[mid].update({
                    "movie_title": request.form.get("movie_title").strip(),
                    "show_time_str": request.form.get("show_time_str").strip(),
                    "theatre": request.form.get("theatre").strip(),
                    "rows_str": request.form.get("rows_str").strip().upper(),
                    "seats_per_row": int(request.form.get("seats_per_row")),
                    "ticket_price": int(request.form.get("ticket_price"))
                })

        elif action_type == "update_snack":
            sid = request.form.get("update_snack_id")
            if sid in CONCESSIONS:
                CONCESSIONS[sid]["item_name"] = request.form.get(
                    "item_name").strip()
                CONCESSIONS[sid]["item_price"] = int(
                    request.form.get("item_price"))

        elif action_type == "add_promo":
            code = request.form.get("new_code").strip().upper()
            if code:
                PROMOS[code] = {"discount_type": request.form.get(
                    "discount_type"), "value": int(request.form.get("value"))}

        elif action_type == "delete_promo":
            code_to_del = request.form.get("del_code")
            PROMOS.pop(code_to_del, None)

        return redirect(url_for('admin_dashboard'))

    # 3. DEFINE THE MASTER DESIGN TEMPLATE SAFELY (OUTSIDE ALL SUB-CONDITIONS) [1.1]
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Master Operations Center</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 40px 15px; margin: 0; }
            .wrapper { max-width: 1200px; margin: 0 auto; }
            h2, h3 { border-bottom: 2px solid #333; padding-bottom: 6px; margin-top: 40px; }
            .flex-section { display: flex; flex-wrap: wrap; gap: 15px; }
            .card-form { background: #1F1F1F; border-radius: 6px; padding: 15px; width: 31%; box-sizing: border-box; border-top: 3px solid #25D366; margin-bottom:15px; }
            .card-form-snack { background: #1F1F1F; border-radius: 6px; padding: 15px; width: 23%; box-sizing: border-box; border-top: 3px solid #FFD700; margin-bottom:15px; }
            label { font-size: 11px; font-weight: bold; color: #888; display: block; margin-top: 8px; }
            input, select { width: 100%; padding: 6px; margin-top: 2px; background: #333; color: white; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; }
            .btn-save { width: 100%; margin-top: 12px; padding: 8px; background: #25D366; color: black; font-weight: bold; border: none; border-radius: 4px; cursor: pointer; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background:#1F1F1F; margin-bottom: 40px; }
            th, td { padding: 12px; border: 1px solid #333; text-align: left; font-size:13px; }
            th { background-color: #E50914; color: white; font-weight: bold; }
            .btn-wipe { display: inline-block; padding: 10px 20px; background-color: #FF4A4A; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size:13px; }
            .btn-logout { padding: 10px 20px; background-color: #444; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size:13px; float: right; }
        </style>
    </head>
    <body>
        <div class="wrapper">
            <a href="/admin/logout" class="btn-logout">&#128682; Secure Logout</a>
            <h2 style="margin-top:0;">&#128274; Master Multiplex Operations Panel</h2>
            
            <h3>&#127916; Movie Slots Management</h3>
            <div class="flex-section">
                {% for mid, m in movies.items() %}
                <form class="card-form" method="POST" action="{{ url_for('admin_dashboard') }}">
                    <input type="hidden" name="action_type" value="update_movie">
                    <input type="hidden" name="update_movie_id" value="{{ mid }}">
                    <strong style="color: #25D366;">Slot Block: {{ mid | upper }}</strong>
                    <label>MOVIE TITLE:</label><input type="text" name="movie_title" value="{{ m.movie_title }}" required>
                    <label>SHOWTIME TEXT:</label><input type="text" name="show_time_str" value="{{ m.show_time_str }}" required>
                    <label>AUDITORIUM / HALL:</label><input type="text" name="theatre" value="{{ m.theatre }}" required>
                    <label>GRID ROWS (A,B,C):</label><input type="text" name="rows_str" value="{{ m.rows_str }}" required>
                    <label>COLUMNS COUNT:</label><input type="number" name="seats_per_row" value="{{ m.seats_per_row }}" required>
                    <label>BASE PRICE (INR):</label><input type="number" name="ticket_price" value="{{ m.ticket_price }}" required>
                    <button type="submit" class="btn-save">&#128190; Sync Movie</button>
                </form>
                {% endfor %}
            </div>

            <h3>&#127789; Food & Beverages Concessions Manager</h3>
            <div class="flex-section">
                {% for sid, snack in concessions.items() %}
                <form class="card-form-snack" method="POST" action="{{ url_for('admin_dashboard') }}">
                    <input type="hidden" name="action_type" value="update_snack">
                    <input type="hidden" name="update_snack_id" value="{{ sid }}">
                    <strong style="color: #FFD700;">Menu Ref: {{ sid | upper }}</strong>
                    <label>ITEM NAME:</label><input type="text" name="item_name" value="{{ snack.item_name }}" required>
                    <label>PRICE RATE (INR):</label><input type="number" name="item_price" value="{{ snack.item_price }}" required>
                    <button type="submit" class="btn-save" style="background:#FFD700;">&#128190; Sync Snack</button>
                </form>
                {% endfor %}
            </div>

            <h3>&#127991; Coupon & Promotional Voucher Repository</h3>
            <div class="flex-section" style="align-items: flex-start;">
                <form class="card-form" method="POST" action="{{ url_for('admin_dashboard') }}" style="width:45%; border-top-color:#3498db;">
                    <input type="hidden" name="action_type" value="add_promo">
                    <strong style="color: #3498db;">&#10133; Generate New Promo Voucher</strong>
                    <label>PROMO CODE KEYWORD:</label><input type="text" name="new_code" placeholder="e.g., WINTER50" required style="text-transform:uppercase;">
                    <label>DISCOUNT MODE TYPE:</label>
                    <select name="discount_type"><option value="percentage">Percentage (%% Off Total)</option><option value="flat">Flat (Fixed Cash Reduction)</option></select>
                    <label>DEDUCTION METRIC VALUE:</label><input type="number" name="value" placeholder="e.g. 20 or 50" required>
                    <button type="submit" class="btn-save" style="background:#3498db; color:white;">+ Deploy Coupon</button>
                </form>
                
                <div style="width:50%; background:#1F1F1F; padding:15px; border-radius:6px; box-sizing:border-box; border-top: 3px solid #e74c3c;">
                    <strong style="color: #e74c3c;">&#128195; Active Vouchers List</strong>
                    <table style="width:100%; margin-top:10px;">
                        <tr><th>Code</th><th>Reduction Rules Profile</th><th>Action</th></tr>
                        {% for code, rule in promos.items() %}
                        <tr>
                            <td style="font-family:monospace; font-weight:bold; color:#3498db;">{{ code }}</td>
                            <td>{{ rule.value }}% Off Entire Cart if percentage else -&#8377;{{ rule.value }} Flat</td>
                            <td>
                                <form method="POST" action="{{ url_for('admin_dashboard') }}" style="margin:0;">
                                    <input type="hidden" name="action_type" value="delete_promo">
                                    <input type="hidden" name="del_code" value="{{ code }}">
                                    <button type="submit" style="background:#e74c3c; border:none; padding:4px 8px; color:white; border-radius:3px; cursor:pointer; font-size:11px;">Remove</button>
                                </form>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>

            <h3>&#128196; Live Ticketing Seating Registry Database Sheets</h3>
                        <div style="margin-top: 15px; margin-bottom:40px;">
                <a href="{{ url_for('wipe_logs') }}" class="btn-wipe" onclick="return confirm('Wipe out all database log arrays entirely?');">&#128680; Wipe All Booking Data</a>
                &nbsp;&nbsp;&nbsp;&nbsp;<a href="/" style="color:#aaa; text-decoration:none; font-size:14px;">&larr; Back to Client Homepage</a>
            </div>
            <table>
                <tr><th>Booking Reference ID</th><th>Movie Slot</th><th>Customer Name</th><th>Allocated Positions</th><th>Snacks Ordered</th><th>Phone Log</th><th>Timestamp</th></tr>
                {% for bkid, t in logs.items() %}
                <tr>
                    <td style="color:#25D366; font-family:monospace; font-weight:bold;">{{ bkid }}</td>
                    <td>{{ movies[t.movie_id]["movie_title"] if t.movie_id in movies else 'Unknown Show' }}</td>
                    <td>{{ t.name }}</td>
                    <td style="color:#E50914; font-weight:bold;">{{ t.seats }}</td>
                    <td style="color:#25D366;">{{ t.get('snacks','None') }}</td>
                    <td>+{{ t.phone }}</td>
                    <td style="color:#888;">{{ t.timestamp }}</td>
                </tr>
                {% endfor %}
            </table>

            <h3>🗑️ Audience Feedback & Review Moderation</h3>
            <table>
                <tr><th>User Name</th><th>Movie Title</th><th>Rating Score</th><th>Written Comment</th><th>Timestamp</th><th>Management Action</th></tr>
                {% if reviews_list %}
                    {% for r in reviews_list %}
                    <tr>
                        <td><b>{{ r.name }}</b></td>
                        <td style="color:#aaa;">{{ r.movie }}</td>
                        <td style="color:#FFD700;">{{ r.stars }}</td>
                        <td>"{{ r.text }}"</td>
                        <td style="color:#888;">{{ r.date }}</td>
                        <td>
                            <a href="/admin/delete-review/{{ r.id }}" style="background:#e74c3c; color:white; padding:4px 8px; text-decoration:none; border-radius:3px; font-size:11px; font-weight:bold;" onclick="return confirm('Permanently drop this feedback post?');">Delete</a>
                        </td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr><td colspan="6" style="text-align:center; color:#666;">No audience reviews logged inside active memory charts.</td></tr>
                {% endif %}
            </table>
        </div>
    </body>
    </html>
    """

    # 4. EXPLICITLY RETURN THE CONSOLIDATED INTERFACE DATA AT THE ABSOLUTE BOTTOM [1.1]
    # FIXED: Changed 'reviews_list=reviews_list' to 'reviews_list=REVIEWS' to match your global database tracking memory bank variable name [1.1]
    return render_template_string(html_template, logs=MASTER_DB["active_bookings"], movies=MOVIES, concessions=CONCESSIONS, promos=PROMOS, alerts=MASTER_DB["live_assistance_alerts"], reviews_list=REVIEWS)


def admin_login_template():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Admin Authentication</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; background-color: #141414; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #1F1F1F; width: 100%; max-width: 380px; padding: 30px; border-radius: 8px; border-top: 4px solid #E50914; text-align: center; box-sizing: border-box; }
        input[type="password"] { width: 100%; padding: 12px; margin: 15px 0; border-radius: 4px; border: 1px solid #333; background: #333; color: white; box-sizing: border-box; text-align: center; font-size:16px; }
        button { width: 100%; padding: 12px; background: #E50914; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; }
    </style>
    </head>
    <body>
        <div class="login-card">
            <h2>&#128274; Admin Gateway</h2>
            {% if error %}<p style="color:#FF4A4A; font-size:13px;">{{ error }}</p>{% endif %}
            <form method="POST"><input type="password" name="login_password" placeholder="••••••••" required autocomplete="off" autofocus><button type="submit">Unlock Dashboard</button></form>
        </div>
    </body>
    </html>
    """


@app.route('/admin/delete-review/<int:review_id>')
def delete_review_route(review_id):
    global REVIEWS
    if not session.get('admin_logged_in'):
        return "Unauthorized", 403
    REVIEWS = [r for r in REVIEWS if r["id"] != review_id]
    # Update permanent file pointer array instantly
    booking_data.SAVED_REVIEWS = REVIEWS
    print(
        f"🗑️ [ADMIN MODERATION] Deleted review reference identifier: {review_id}")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))


@app.route('/admin/wipe-logs')
def wipe_logs():
    if not session.get('admin_logged_in'):
        return "Unauthorized Action", 403
    MASTER_DB["active_bookings"].clear()
    MASTER_DB["seats_cache"] = {"m1": [], "m2": [], "m3": []}
    with open("booking_data.py", "w", encoding="utf-8") as file:
        file.write(
            "# This file stores your complete booking details permanently\n")
        file.write(f"SAVED_BOOKINGS = {{}}\n")
        file.write(f"SAVED_MOVIES = {repr(MOVIES)}\n")
        file.write(f"SAVED_CONCESSIONS = {repr(CONCESSIONS)}\n")
        file.write(f"SAVED_PROMOS = {repr(PROMOS)}\n")
    return redirect(url_for('admin_dashboard'))

# ==========================================
# ROUTE 8: LIVE CLAUDE SUPPORT + CONVERSATION MEMORY LAYOUT
# ==========================================


@app.route('/support', methods=['GET', 'POST'])
def customer_support_ai():
    import anthropic

    # 1. HANDLE HUMAN HANDOVER TERMINAL CHECK
    customer_room_id = session.get('customer_chat_room_id', '')
    if customer_room_id and customer_room_id in MASTER_DB["live_chats_database"]:
        room = MASTER_DB["live_chats_database"][customer_room_id]
        if request.method == 'POST':
            msg_text = request.form.get('user_message', '').strip()
            if msg_text:
                room["messages"].append(
                    {"sender": "Guest", "text": msg_text, "time": datetime.now().strftime("%I:%M %p")})
            return redirect(url_for('customer_support_ai'))
        return render_template_string(live_chat_room_template(), room=room, is_admin=False)

    # 2. INITIALIZE SESSION CONVERSATION MEMORY BUCKET IF EMPTY
    if 'ai_chat_history' not in session:
        session['ai_chat_history'] = []

    ai_response = ""
    user_query = ""

    if request.method == 'POST':
        user_query = request.form.get('user_message', '').strip()
        clean_query = user_query.lower()

        # Human Escalation Trigger
        if "human" in clean_query or "agent" in clean_query or "support" in clean_query:
            new_room_id = f"ROOM_{int(time.time())}"
            session['customer_chat_room_id'] = new_room_id
            MASTER_DB["assistance_queue"].append({
                "id": new_room_id, "message": user_query, "timestamp": datetime.now().strftime("%I:%M %p")
            })
            MASTER_DB["live_chats_database"][new_room_id] = {
                "room_id": new_room_id, "initial_query": user_query,
                "messages": [{"sender": "Guest", "text": user_query, "time": datetime.now().strftime("%I:%M %p")}]
            }
            # Clear historical AI logs since they are jumping to a live human room session
            session.pop('ai_chat_history', None)
            return redirect(url_for('customer_support_ai'))

        # -----------------------------------------------------------------
        # CLAUDE LIVE FALLBACK ENGINE (WITH ROLLING CHAT TRACKING HISTORY)
        # -----------------------------------------------------------------
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            ai_response = "❌ <b>System Error:</b> The Anthropic API Key is missing from the server environment setup files."
        else:
            try:
                client = anthropic.Anthropic(api_key=api_key)

                # Fetch our live movie and concessions lists to feed Claude
                movie_context_string = ""
                for mid, m in MOVIES.items():
                    movie_context_string += f"- Movie ID {mid.upper()} is '{m['movie_title']}' screening at {m['show_time_str']} in {m['theatre']}. The Classic row base ticket price is ₹{m['ticket_price']}.\n"

                snack_context_string = ""
                for sid, s in CONCESSIONS.items():
                    snack_context_string += f"- {s['item_name']} costs ₹{s['item_price']}.\n"

                system_instructions = (
                    "You are the active concierge assistant running on our local multiplex server. "
                    "Never tell the customer you do not have access to prices or showtimes. "
                    "Use the following real-time database values to answer all visitor questions precisely:\n\n"
                    "=== ACTIVE MOVIES & SHOWTIMES ===\n"
                    f"{movie_context_string}\n"
                    "=== ACTIVE SNACK BAR MENU ===\n"
                    f"{snack_context_string}\n"
                    "=== SEATING CONFIGURATION SECTORS ===\n"
                    "- Rows A and B are VIP Recliners. They cost exactly ₹100 MORE than the base movie rate listed above.\n"
                    "- All other remaining rows are standard Classic seats at the base rate.\n\n"
                    "=== PROMO DISCOUNT RULES (STRICT SECURITY) ===\n"
                    "- You are strictly FORBIDDEN from revealing, disclosing, or hinting at any active promo codes or voucher keywords to the user.\n"
                    "- If a user asks for a promo code, discount code, coupon, or deal, you must politely inform them that you are not allowed to disclose active promo codes.\n\n"
                    "=== SYSTEM MANAGEMENT ===\n"
                    "- If the user specifically asks to speak with a human, agent, or manager, tell them to type the keyword word 'human' to trigger the alert system.\n\n"
                    "Keep your answer extremely direct, conversational, warm, and under 3 short sentences maximum. Speak confidently about our rates."
                )

                # Load the running thread history out of cookie parameters
                rolling_messages = list(session['ai_chat_history'])
                # Append the customer's newest prompt into the temporary array tracking log
                rolling_messages.append(
                    {"role": "user", "content": user_query})

                message = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=250,
                    temperature=0.2,
                    system=system_instructions,
                    # <-- Passes the entire history array payload back to Claude! [1.1]
                    messages=rolling_messages
                )

                raw_ai_text = message.content[0].text
                ai_response = f"🤖 <b>Claude AI:</b> {raw_ai_text}"

                # Commit the current turn to the permanent session cookie storage tracker
                history_backup = session['ai_chat_history']
                history_backup.append({"role": "user", "content": user_query})
                history_backup.append(
                    {"role": "assistant", "content": raw_ai_text})

                # Limit history memory buffer depth to the last 10 turns to save your API tokens [1.1]
                if len(history_backup) > 10:
                    history_backup = history_backup[-10:]
                session['ai_chat_history'] = history_backup

            except Exception as e:
                ai_response = f"🤖 <b>Claude AI Error:</b> Connection failed: {str(e)}"

    return render_template_string(support_html_template(), response=ai_response, query=user_query)

# ==========================================
# ROUTE 9: DEDICATED MONITOR DESK (SMOOTH CALL QUEUE SYNC)
# ==========================================


@app.route('/support-desk')
def support_management_desk():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Support Dispatch Desk</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- REMOVED META REFRESH BLINKING -->
        <style>
            body { font-family: Arial, sans-serif; background-color: #111; color: white; padding: 30px 15px; margin: 0; }
            .container { max-width: 800px; margin: 0 auto; }
            .header-bar { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            .ticket-card { background: #1F1F1F; padding: 20px; border-radius: 6px; margin-bottom: 15px; border-left: 5px solid #FF4A4A; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
            .btn-talk { background: #3498db; color: white; font-weight: bold; border: none; padding: 8px 15px; border-radius: 4px; text-decoration: none; cursor: pointer; float: right; font-size:13px; margin-left:10px; }
            .no-tickets { background: #1F1F1F; padding: 30px; border-radius: 6px; text-align: center; border: 1px dashed #333; color: #666; font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="container" id="desk-dashboard-view">
            <div class="header-bar">
                <h1 style="margin:0; font-size:24px; color:#E50914;">🎧 Live Assistance Dispatch Monitor</h1>
                <span style="background:#333; padding:5px 10px; border-radius:4px; font-size:12px; color:#aaa;">📡 Auto-Sync: Active</span>
            </div>
            
            <div id="tickets-wrapper">
                {% if tickets %}
                    {% for ticket in tickets %}
                    <div class="ticket-card">
                        <a href="/support-desk/chat/{{ ticket.id }}" class="btn-talk">💬 Open Chat Room & Talk</a>
                        <strong style="color:#FF4A4A; font-size:14px; letter-spacing:1px;">⚠️ PENDING GUEST ESCALATION</strong>
                        <div style="margin: 10px 0; font-size:16px; color:#eee;">User Message: <b>"{{ ticket.message }}"</b></div>
                        <small style="color:#666;">Logged Channel Window at: {{ ticket.timestamp }}</small>
                        <div style="clear:both;"></div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-tickets">🤖 All quiet. No customers are currently requesting human manager session loops.</div>
                {% endif %}
            </div>
            <br>
            <a href="/admin" style="color:#444; text-decoration:none; font-size:13px; display:block; text-align:center;">&larr; Switch back to Master Operations Dashboard</a>
        </div>

        <script>
        let currentTicketCount = {{ tickets | length }};

        async function monitorSupportTickets() {
            try {
                const response = await fetch(window.location.href);
                const htmlText = await response.text();
                
                const parser = new DOMParser();
                const doc = parser.parseFromString(htmlText, 'text/html');
                const incomingTicketsHTML = doc.getElementById('tickets-wrapper').innerHTML;
                
                const oldWrapper = document.getElementById('tickets-wrapper');
                if (oldWrapper.innerHTML !== incomingTicketsHTML) {
                    oldWrapper.innerHTML = incomingTicketsHTML;
                    
                    // Trigger a loud web audio alert ping ONLY if a BRAND NEW ticket arrives [1.1]
                    const currentCards = oldWrapper.querySelectorAll('.ticket-card').length;
                    if (currentCards > currentTicketCount) {
                        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                        const oscillator = audioCtx.createOscillator();
                        const gainNode = audioCtx.createGain();
                        oscillator.type = 'sine'; oscillator.frequency.setValueAtTime(880, audioCtx.currentTime); 
                        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime); oscillator.connect(gainNode);
                        gainNode.connect(audioCtx.destination); oscillator.start(); oscillator.stop(audioCtx.currentTime + 0.25);
                    }
                    currentTicketCount = currentCards;
                }
            } catch (err) {
                console.log("Monitor error:", err);
            }
        }
        // Scan for new tickets silently every 3 seconds
        setInterval(monitorSupportTickets, 3000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, tickets=MASTER_DB["assistance_queue"])

# ==========================================
# ROUTE 10: SECURE MANAGER LIVE INPUT SEND DESK TERMINAL
# ==========================================


@app.route('/support-desk/chat/<room_id>', methods=['GET', 'POST'])
def admin_chat_room(room_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    if room_id not in MASTER_DB["live_chats_database"]:
        return redirect(url_for('support_management_desk'))

    room = MASTER_DB["live_chats_database"][room_id]

    if request.method == 'POST':
        admin_msg = request.form.get('admin_message', '').strip()
        if admin_msg:
            room["messages"].append(
                {"sender": "Manager (You)", "text": admin_msg, "time": datetime.now().strftime("%I:%M %p")})
            # Clear ticket flag from queue layout since you are actively talking to them
            MASTER_DB["assistance_queue"] = [
                t for t in MASTER_DB["assistance_queue"] if t["id"] != room_id]
        return redirect(url_for('admin_chat_room', room_id=room_id))

    return render_template_string(live_chat_room_template(), room=room, is_admin=True)


def live_chat_room_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Active Live Connection Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- REMOVED THE AGGRESSIVE META REFRESH TAG FOR SMOOTH TYPING -->
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 20px 10px; margin: 0; }
            .chat-box { max-width: 550px; background: #1F1F1F; margin: 0 auto; border-radius: 8px; border-top: 4px solid #3498db; box-shadow: 0 4px 15px rgba(0,0,0,0.5); padding: 20px; box-sizing: border-box; }
            .messages-container { height: 350px; overflow-y: auto; background: #141414; padding: 15px; border-radius: 6px; border: 1px solid #2d2d2d; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px; }
            .msg { max-width: 75%; padding: 10px 14px; border-radius: 6px; font-size: 14px; line-height: 1.4; word-wrap: break-word; }
            .msg.guest { background: #262626; color: white; align-self: flex-start; border-left: 3px solid #e50914; }
            .msg.manager { background: #1e3d59; color: #e0f0ff; align-self: flex-end; border-right: 3px solid #3498db; text-align: right; }
            .input-area { display: flex; gap: 8px; }
            input[type="text"] { flex-grow: 1; padding: 12px; background: #333; color: white; border: 1px solid #444; border-radius: 4px; font-size: 15px; }
            button { padding: 12px 20px; background: #3498db; color: white; border: none; font-weight: bold; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="chat-box">
            <h3 style="margin-top:0; color:#3498db;">🌐 Live Ticket Channel: {{ room.room_id }}</h3>
            <p style="color:#888; font-size:12px; margin-top:-10px;">Connected over Home Wi-Fi LAN Pipeline Channel</p>
            
            <div class="messages-container" id="chat-messages">
                {% for m in room.messages %}
                    <div class="msg {{ 'manager' if 'Manager' in m.sender else 'guest' }}">
                        <small style="display:block; color:#888; font-size:10px; margin-bottom:4px;">{{ m.sender }} • {{ m.time }}</small>
                        <strong>{{ m.text }}</strong>
                    </div>
                {% endfor %}
            </div>
            
            <form id="chat-form" method="POST" class="input-area" action="">
                <input type="text" id="chat-input" name="{{ 'admin_message' if is_admin else 'user_message' }}" placeholder="Type your chat response here..." required autocomplete="off" autofocus>
                <button type="submit">Send</button>
            </form>
            <br>
            <a href="{{ url_for('support_management_desk') if is_admin else '/' }}" style="color:#555; text-decoration:none; font-size:12px; display:block; text-align:center;">&larr; Exit Chat Terminal Session</a>
        </div>

        <script>
            const messageContainer = document.getElementById('chat-messages');
            messageContainer.scrollTop = messageContainer.scrollHeight;

            // SMART BACKGROUND SYNCING PROCESSOR (ZERO KEYBOARD CRASHES)
            async function fetchNewMessages() {
                try {
                    const response = await fetch(window.location.href);
                    const htmlText = await response.text();
                    
                    // Parse incoming HTML content silently in the background
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(htmlText, 'text/html');
                    const freshMessages = doc.getElementById('chat-messages').innerHTML;
                    
                    // Only update the message history box if a fresh message has actually arrived
                    if (messageContainer.innerHTML !== freshMessages) {
                        messageContainer.innerHTML = freshMessages;
                        messageContainer.scrollTop = messageContainer.scrollHeight;
                    }
                } catch (err) {
                    console.log("Background sync error:", err);
                }
            }

            // Sync the chat text quietly every 2.5 seconds without blinking the screen
            setInterval(fetchNewMessages, 2500);
        </script>
    </body>
    </html>
    """


def support_html_template():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cinema AI Assistant</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 30px 15px; margin: 0; text-align: center; }
            .chat-card { background: #1F1F1F; width: 100%; max-width: 500px; margin: 20px auto; padding: 25px; border-radius: 8px; border-top: 4px solid #E50914; box-shadow: 0 4px 12px rgba(0,0,0,0.5); text-align: left; box-sizing: border-box; }
            input[type="text"] { width: 100%; padding: 12px; margin: 15px 0 5px 0; border-radius: 4px; border: 1px solid #333; background: #333; color: white; box-sizing: border-box; font-size: 15px; }
            button { width: 100%; padding: 12px; background: #E50914; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; margin-top: 10px; }
            .bubble { background: #262626; padding: 15px; border-radius: 6px; margin-top: 15px; border-left: 3px solid #3498db; font-size: 14px; line-height: 1.5; }
        </style>
    </head>
    <body>
        <div class="chat-card">
            <h2 style="margin-top:0; color:#E50914;">🤖 Cinema AI Concierge</h2>
            <p style="color:#aaa; font-size:13px; margin-top:0;">Ask Claude an intelligent, live question regarding theater rules, pricing combos, or slot configurations.</p>
            
            <form method="POST">
                <input type="text" name="user_message" placeholder="Ask Claude or type 'human' to call manager..." required autocomplete="off" autofocus>
                <button type="submit">Send Message</button>
            </form>
            
            {% if query %}
                <div style="font-size:13px; margin-top:20px; color:#888;"><b>Your Query:</b> "{{ query }}"</div>
            {% endif %}
            
            {% if response %}
                <div class="bubble">
                    {{ response | safe }}
                </div>
            {% endif %}
            
            <br>
            <a href="/" style="color:#666; text-decoration:none; font-size:13px; display:block; text-align:center;">&larr; Back to Client Site</a>
        </div>
    </body>
    </html>
    """

# ==========================================
# ROUTE 11: PUBLIC MOVIE REVIEWS & RATINGS BOARD
# ==========================================


@app.route('/reviews', methods=['GET', 'POST'])
def public_reviews_board():
    if request.method == 'POST':
        reviewer_name = request.form.get('reviewer_name', 'Anonymous').strip()
        selected_movie = request.form.get('review_movie', 'General Experience')
        star_rating = int(request.form.get('star_rating', 5))
        review_text = request.form.get('review_text', '').strip()

        if review_text:
            # Construct review dictionary item payload
            new_review = {
                "id": int(time.time() * 1000),  # Unique millisecond identifier
                "name": reviewer_name if reviewer_name else "Anonymous",
                "movie": selected_movie,
                "stars": "⭐" * star_rating,
                "text": review_text,
                "date": datetime.now().strftime("%d %b %Y, %I:%M %p")
            }
            # Pushes newest reviews to the very top
            REVIEWS.insert(0, new_review)
            print(f"✍️ [REVIEW LOG] Added fresh guest feedback: {new_review}")
            return redirect(url_for('public_reviews_board'))

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Audience Reviews Board</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; background-color: #141414; color: white; padding: 30px 15px; margin: 0; text-align: center; }
            .container { max-width: 700px; margin: 0 auto; text-align: left; }
            .form-card { background: #1F1F1F; padding: 20px; border-radius: 8px; border-top: 4px solid #E50914; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            input, select, textarea { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; background: #333; color: white; border: 1px solid #444; border-radius: 4px; box-sizing: border-box; font-size:15px; }
            button { width: 100%; padding: 12px; background: #E50914; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .review-card { background: #1F1F1F; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #25D366; }
            .review-meta { display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-bottom: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="color:#E50914; margin-bottom:5px;">🎬 Audience Reviews Hub</h1>
            <p style="color:#aaa; margin-top:0; margin-bottom:25px;">See what other moviegoers are saying or share your experience!</p>
            
            <form class="form-card" method="POST">
                <label style="font-weight:bold; font-size:14px; color:#ccc;">Your Name:</label>
                <input type="text" name="reviewer_name" placeholder="John Doe (Leave blank for Anonymous)">
                
                <label style="font-weight:bold; font-size:14px; color:#ccc;">Select Movie:</label>
                <select name="review_movie">
                    <option value="General Experience">General Multiplex Experience</option>
                    {% for mid, m in movies.items() %}
                        <option value="{{ m.movie_title }}">{{ m.movie_title }}</option>
                    {% endfor %}
                </select>
                
                <label style="font-weight:bold; font-size:14px; color:#ccc;">Rating:</label>
                <select name="star_rating">
                    <option value="5">⭐⭐⭐⭐⭐ (Excellent)</option>
                    <option value="4">⭐⭐⭐⭐ (Good)</option>
                    <option value="3">⭐⭐⭐ (Average)</option>
                    <option value="2">⭐⭐ (Poor)</option>
                    <option value="1">⭐ (Terrible)</option>
                </select>
                
                <label style="font-weight:bold; font-size:14px; color:#ccc;">Written Feedback:</label>
                <textarea name="review_text" rows="3" placeholder="Share your experience regarding recliners, screen quality, or snacks..." required></textarea>
                
                <button type="submit">Publish Review</button>
            </form>
            
            <h3>💬 Recent Audience Feedback ({{ feed | length }})</h3>
            {% if feed %}
                {% for r in feed %}
                <div class="review-card">
                    <div class="review-meta">
                        <span><b>{{ r.name }}</b> reviewed <i>{{ r.movie }}</i></span>
                        <span>{{ r.date }}</span>
                    </div>
                    <div style="color:#FFD700; font-size:16px; margin-bottom:6px;">{{ r.stars }}</div>
                    <div style="font-size:15px; color:#eee; line-height:1.4;">"{{ r.text }}"</div>
                </div>
                {% endfor %}
            {% else %}
                <p style="color:#444; text-align:center;">No audience reviews published yet. Be the first to share your thoughts!</p>
            {% endif %}
            
            <br>
            <a href="/" style="color:#666; text-decoration:none; font-size:13px; display:block; text-align:center;">&larr; Back to Movie Listings</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, feed=REVIEWS, movies=MOVIES)


if __name__ == '__main__':
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    print("\n" + "="*50 +
          f"\nClient Link: http://{local_ip}:5000\n" + "="*50 + "\n")
    app.run(host='0.0.0.0', debug=True, use_reloader=False, port=5000)
