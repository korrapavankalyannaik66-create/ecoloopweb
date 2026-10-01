import os
import sys
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ecoloop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ---------------------------------------------------------------------------
# GEMINI LIVE DYNAMIC AI INTEGRATION
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

ECO_SYSTEM_PROMPT = """
You are EcoLoop AI, a dynamic customer support assistant for the EcoLoop E-Waste Platform.
Platform Context & Rules:
- Purpose: Safe, government-regulated e-waste collection, inspection, and recycling.
- Roles: Seller, Govt Inspector, Company Admin.
- Workflow: Seller submits pickup -> Govt Inspector physically verifies -> Company Admin disburses payout via UPI/Bank/Card.

Answer concisely (under 3-4 sentences) with markdown formatting and emojis.
"""

user_chats = {}

# ---------------------------------------------------------------------------
# SQLALCHEMY DATABASE MODELS
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Seller, Inspector, Admin
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    gov_id = db.Column(db.String(100), nullable=True)
    doc_file = db.Column(db.String(200), nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    company_gst = db.Column(db.String(50), nullable=True)
    password = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Active")

class Company(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gst = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    bonus = db.Column(db.Integer, default=5)
    description = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    rate = db.Column(db.Integer, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    seller = db.Column(db.String(100), nullable=False)
    seller_email = db.Column(db.String(120), nullable=False)
    seller_phone = db.Column(db.String(20))
    items = db.Column(db.Text, nullable=False)
    payout = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="In Progress")
    payment_method = db.Column(db.String(50), default="-")
    txn_ref = db.Column(db.String(50), default="-")

# ---------------------------------------------------------------------------
# INITIAL SEED DATA
# ---------------------------------------------------------------------------

def seed_initial_data():
    if Company.query.count() == 0:
        db.session.add_all([
            Company(id="comp-1", name="EcoLoop Solutions", gst="37AAAAA1234A1Z1", location="Vijayawada, AP", bonus=5, description="Official E-Waste Processing Partner"),
            Company(id="comp-2", name="GreenCycle India", gst="36BBBBB5678B2Z2", location="Hyderabad, TS", bonus=10, description="Green Technology Recyclers")
        ])

    if Product.query.count() == 0:
        db.session.add_all([
            Product(id=1, name="Mobile phones", unit="unit", rate=120),
            Product(id=2, name="Laptops", unit="unit", rate=1500),
            Product(id=3, name="Monitors / TVs", unit="unit", rate=350),
            Product(id=4, name="Printers", unit="unit", rate=250),
            Product(id=5, name="Hard drives", unit="unit", rate=80),
            Product(id=6, name="Chargers & adapters", unit="kg", rate=40),
            Product(id=7, name="Circuit boards (PCB)", unit="kg", rate=120),
            Product(id=8, name="Cables & wires", unit="kg", rate=30)
        ])

    if User.query.count() == 0:
        db.session.add_all([
            User(name="Ramesh Kumar", role="Seller", email="seller@demo.com", phone="9876543210", location="Auto Nagar, Vijayawada", gov_id="1234-5678-9012", doc_file="id_proof_sample.pdf", password="password123"),
            User(name="Inspector Officer V. Rao", role="Inspector", email="inspector@demo.com", phone="9876543211", gov_id="GOV-INSP-9901", doc_file="govt_badge.pdf", password="password123"),
            User(name="Priya Sharma", role="Admin", email="admin@demo.com", phone="9876543212", location="Hyderabad, TS", company_name="EcoLoop Solutions", company_gst="37AAAAA1234A1Z1", password="password123")
        ])

    db.session.commit()

# ---------------------------------------------------------------------------
# CLI PRINT DATA FUNCTION
# ---------------------------------------------------------------------------

def print_database_data():
    with app.app_context():
        print("\n==================== REGISTERED USERS ====================", flush=True)
        users = User.query.all()
        if not users:
            print("No users found in database.", flush=True)
        for u in users:
            print(f"ID: {u.id} | Name: {u.name} | Role: {u.role} | Email: {u.email} | Location: {u.location} | Status: {u.status}", flush=True)

        print("\n==================== RECYCLING COMPANIES ====================", flush=True)
        companies = Company.query.all()
        if not companies:
            print("No companies found.", flush=True)
        for c in companies:
            print(f"ID: {c.id} | Name: {c.name} | GST: {c.gst} | Location: {c.location} | Bonus: +{c.bonus}%", flush=True)

        print("\n==================== E-WASTE PRODUCTS & RATES ====================", flush=True)
        products = Product.query.all()
        if not products:
            print("No products found.", flush=True)
        for p in products:
            print(f"ID: {p.id} | Name: {p.name} | Unit: {p.unit} | Rate: ₹{p.rate}", flush=True)

        print("\n==================== TRANSACTIONS ====================", flush=True)
        transactions = Transaction.query.all()
        if not transactions:
            print("No transactions found in queue.", flush=True)
        for t in transactions:
            print(f"Req ID: {t.id} | Date: {t.date} | Seller: {t.seller} ({t.seller_email}) | Company: {t.company} | Items: {t.items} | Payout: ₹{t.payout} | Status: {t.status} | Ref: {t.txn_ref}", flush=True)
        print("===========================================================\n", flush=True)

# ---------------------------------------------------------------------------
# HELPER FUNCTION FOR AUTHENTICATION
# ---------------------------------------------------------------------------

def get_current_user():
    if "user_id" not in session:
        return None
    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return None
    return user

# ---------------------------------------------------------------------------
# API ROUTES
# ---------------------------------------------------------------------------

@app.route("/api/ai_chat", methods=["POST"])
def ai_chat():
    data = request.get_json() or {}
    user_msg = data.get("message", "").strip()

    if not user_msg:
        return jsonify({"response": "I'm EcoLoop Live AI! Ask me anything about e-waste rates, pickup scheduling, or government inspection rules."})

    sess_id = session.get("user_id", request.remote_addr)

    if genai_client:
        try:
            if sess_id not in user_chats:
                user_chats[sess_id] = genai_client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        system_instruction=ECO_SYSTEM_PROMPT,
                        temperature=0.7
                    )
                )

            chat = user_chats[sess_id]
            response = chat.send_message(user_msg)
            return jsonify({"response": response.text})

        except Exception as e:
            print("Gemini API Error:", e)

    msg_lower = user_msg.lower()
    if "rate" in msg_lower or "price" in msg_lower or "cost" in msg_lower:
        res = "💡 **Current Base Rates:** Laptops ₹1,500/unit, Mobile phones ₹120/unit, Monitors ₹350/unit, PCB boards ₹120/kg. Verified recycling companies offer additional bonuses (+5% to +10%)!"
    elif "pickup" in msg_lower or "sell" in msg_lower or "schedule" in msg_lower:
        res = "🛍️ **Selling Steps:** Click **Recycle Today**, log in as a seller, choose a partner, and submit your request for physical inspector verification!"
    elif "inspect" in msg_lower or "verify" in msg_lower or "govt" in msg_lower:
        res = "🏛️ **Inspector Duties:** Government Officers verify material authenticity, ensure non-hazardous handling, and audit registered sellers and admins."
    elif "payment" in msg_lower or "payout" in msg_lower or "money" in msg_lower:
        res = "💳 **Payouts:** Disbursed directly to your account via UPI, Bank Transfer, or Card right after the inspector approves your request."
    else:
        res = f"🌱 I'm your EcoLoop Assistant. You asked: *\"{user_msg}\"*. Feel free to ask about e-waste rates, scheduling a pickup, or checking payout statuses!"

    return jsonify({"response": res})

@app.route("/api/update_location", methods=["POST"])
def update_location():
    user = get_current_user()
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    data = request.get_json() or {}
    lat = data.get("latitude")
    lng = data.get("longitude")

    user.location = f"{lat},{lng}"
    db.session.commit()
    return jsonify({"status": "success", "lat": lat, "lng": lng})

# ---------------------------------------------------------------------------
# MAIN PUBLIC HERO LANDING PAGE AND APP ROUTES
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html", page="landing")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "").strip()

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            # Flexible role check: validate only if role was provided in the form
            if role and user.role.lower() != role.lower():
                flash(f"❌ Account registered as {user.role}. Please select the correct tab/role.", "danger")
                return render_template("index.html", page="login")

            if user.status == "Suspended":
                flash("❌ Account Suspended by Government Inspector.", "danger")
                return render_template("index.html", page="login")

            session.clear()
            session["user_id"] = user.id
            flash(f"✅ Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid email or password. Please check your login credentials.", "danger")

    return render_template("index.html", page="login")

@app.route("/register/seller", methods=["GET", "POST"])
def register_seller():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("❌ Email already registered! Please login instead.", "danger")
            return redirect(url_for("login"))

        file = request.files.get("id_file")
        filename = file.filename if file else "Not Provided"
        if file and file.filename != "":
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_user = User(
            name=request.form.get("name"),
            email=email,
            phone=request.form.get("phone"),
            location=request.form.get("location"),
            gov_id=request.form.get("gov_id"),
            doc_file=filename,
            password=request.form.get("password"),
            role="Seller"
        )
        db.session.add(new_user)
        db.session.commit()

        session.clear()
        session["user_id"] = new_user.id
        flash("🎉 Seller Account Registered Successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("index.html", page="register_seller")

@app.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("❌ Email already registered! Please login instead.", "danger")
            return redirect(url_for("login"))

        company_name = request.form.get("company_name")
        company_gst = request.form.get("company_gst")

        new_comp = Company(
            id=f"comp-{Company.query.count() + 1}",
            name=company_name,
            gst=company_gst,
            location=request.form.get("location", "Corporate Hub"),
            bonus=6,
            description="Registered Recycler Partner"
        )
        db.session.add(new_comp)

        new_user = User(
            name=request.form.get("name"),
            email=email,
            phone=request.form.get("phone"),
            location=request.form.get("location", "Corporate Hub"),
            company_name=company_name,
            company_gst=company_gst,
            password=request.form.get("password"),
            role="Admin"
        )
        db.session.add(new_user)
        db.session.commit()

        session.clear()
        session["user_id"] = new_user.id
        flash("🎉 Company Admin Account Registered!", "success")
        return redirect(url_for("dashboard"))

    return render_template("index.html", page="register_admin")

@app.route("/register/inspector", methods=["GET", "POST"])
def register_inspector():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("❌ Inspector Email already exists!", "danger")
            return redirect(url_for("login"))

        file = request.files.get("id_file")
        filename = file.filename if file else "Govt_Badge.pdf"
        if file and file.filename != "":
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        new_user = User(
            name=request.form.get("name"),
            email=email,
            phone=request.form.get("phone"),
            gov_id=request.form.get("gov_id"),
            doc_file=filename,
            password=request.form.get("password"),
            role="Inspector"
        )
        db.session.add(new_user)
        db.session.commit()

        session.clear()
        session["user_id"] = new_user.id
        flash("🏛️ Govt Inspector Credential Created!", "success")
        return redirect(url_for("dashboard"))

    return render_template("index.html", page="register_inspector")

@app.route("/logout")
def logout():
    session.clear()
    flash("🔒 Logged out safely.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    # DATA PRIVACY FILTER: Sellers only see their own requests; Admin & Inspector see all
    if user.role == "Seller":
        transactions = Transaction.query.filter_by(seller_email=user.email).all()
    else:
        transactions = Transaction.query.all()

    companies = Company.query.all()
    return render_template("index.html", page="dashboard", user=user, transactions=transactions, companies=companies)

@app.route("/company_detail/<comp_id>")
def company_detail(comp_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    comp = Company.query.get(comp_id) or Company.query.first()
    products = Product.query.all()
    return render_template("index.html", page="company_detail", user=user, company=comp, products=products)

@app.route("/sell", methods=["GET", "POST"])
def sell():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        company_id = request.form.get("company_id")
        company = Company.query.get(company_id) or Company.query.first()
        products = Product.query.all()

        items_summary = []
        gross = 0
        for p in products:
            qty = int(request.form.get(f"qty_{p.id}", 0) or 0)
            if qty > 0:
                gross += qty * p.rate
                items_summary.append(f"{p.name} ({qty} {p.unit})")

        if gross == 0:
            flash("⚠️ Select a quantity for at least one item.", "warning")
            return redirect(url_for("company_detail", comp_id=company.id))

        bonus = round(gross * (company.bonus / 100))
        fee = round(gross * 0.08)
        payout = gross + bonus - fee

        new_tx = Transaction(
            id=f"REQ-{random.randint(1000, 9999)}",
            date=request.form.get("pickup_date"),
            company=company.name,
            seller=user.name,
            seller_email=user.email,
            seller_phone=user.phone or "N/A",
            items=", ".join(items_summary),
            payout=payout,
            status="In Progress"
        )
        db.session.add(new_tx)
        db.session.commit()

        flash(f"✅ Pickup request submitted to {company.name}! Request ID: {new_tx.id}", "success")
        return redirect(url_for("history"))

    companies = Company.query.all()
    return render_template("index.html", page="sell", user=user, companies=companies)

@app.route("/inspector")
def inspector():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if user.role != "Inspector":
        return redirect(url_for("dashboard"))

    users = User.query.all()
    transactions = Transaction.query.all()
    return render_template("index.html", page="inspector", user=user, users=users, transactions=transactions)

@app.route("/inspector/toggle_user/<int:user_id>")
def toggle_user(user_id):
    user = get_current_user()
    if not user or user.role != "Inspector":
        return redirect(url_for("login"))

    u = User.query.get(user_id)
    if u and u.role != "Inspector":
        u.status = "Suspended" if u.status == "Active" else "Active"
        db.session.commit()
        flash(f"⚠️ User {u.name} status updated to {u.status}.", "info")
    return redirect(url_for("inspector"))

@app.route("/inspector/verify/<req_id>")
def verify_request(req_id):
    user = get_current_user()
    if not user or user.role != "Inspector":
        return redirect(url_for("login"))

    t = Transaction.query.get(req_id)
    if t:
        t.status = "Verified"
        db.session.commit()
        flash(f"✅ Request {req_id} physical inspection approved!", "success")
    return redirect(url_for("inspector"))

@app.route("/payments", methods=["GET", "POST"])
def payments():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        req_id = request.form.get("req_id")
        method = request.form.get("method")
        t = Transaction.query.get(req_id)
        if t:
            t.status = "Paid"
            t.payment_method = method
            t.txn_ref = f"TXN-{random.randint(100000, 999999)}"
            db.session.commit()
            flash(f"💸 Payment Disbursed for {req_id}! Ref: {t.txn_ref}", "success")

    verified_tx = Transaction.query.filter_by(status="Verified").all()
    return render_template("index.html", page="payments", user=user, transactions=verified_tx)

@app.route("/products", methods=["GET", "POST"])
def products():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        prod_id = int(request.form.get("product_id"))
        p = Product.query.get(prod_id)
        if p:
            p.rate = int(request.form.get("rate"))
            db.session.commit()
            flash("✅ Product rate updated successfully in SQLite database!", "success")

    prods = Product.query.all()
    return render_template("index.html", page="products", user=user, products=prods)

@app.route("/sellers")
def sellers():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    seller_list = User.query.filter_by(role="Seller").all()
    return render_template("index.html", page="sellers", user=user, sellers=seller_list)

@app.route("/history")
def history():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if user.role == "Seller":
        tx_list = Transaction.query.filter_by(seller_email=user.email).all()
    else:
        tx_list = Transaction.query.all()

    return render_template("index.html", page="history", user=user, transactions=tx_list)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        user.name = request.form.get("name")
        user.phone = request.form.get("phone")
        if "location" in request.form:
            user.location = request.form.get("location")
        db.session.commit()
        flash("⚙️ Profile & Account Settings saved!", "success")

    return render_template("index.html", page="settings", user=user)

@app.route("/help")
def help_page():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    return render_template("index.html", page="help", user=user)

# ---------------------------------------------------------------------------
# ENTRYPOINT: CHECK FOR CLI COMMANDS BEFORE STARTING FLASK SERVER
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_initial_data()

    if len(sys.argv) > 1 and sys.argv[1] == "view-data":
        print_database_data()
    else:
        app.run(debug=True, port=8000)