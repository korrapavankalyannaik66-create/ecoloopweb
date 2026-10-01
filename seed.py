from app import app, db  # Import your Flask app and SQLAlchemy instance
# Import your models (update these names based on your actual models in app.py)
# from app import User, RecyclingCompany, EwasteProduct, Transaction

def reset_and_seed():
    with app.app_context():
        print("🗑️ Dropping all existing tables...")
        db.drop_all()
        
        print("🏗️ Creating fresh database tables...")
        db.create_all()
        
        print("🌱 Seeding initial data...")

        # 1. Create a Default Admin Account
        # (Make sure to hash passwords if your app requires hashed passwords!)
        # admin = User(name="Admin", email="admin@demo.com", role="Admin", status="Active")
        # admin.set_password("admin123") # or password="admin123" depending on your setup
        # db.session.add(admin)

        # 2. Seed Default E-Waste Products & Rates
        default_rates = [
            {"name": "Mobile phones", "unit": "unit", "rate": 120},
            {"name": "Laptops", "unit": "unit", "rate": 1500},
            {"name": "Monitors / TVs", "unit": "unit", "rate": 350},
            {"name": "Printers", "unit": "unit", "rate": 250},
            {"name": "Hard drives", "unit": "unit", "rate": 80},
            {"name": "Chargers & adapters", "unit": "kg", "rate": 40},
            {"name": "Circuit boards (PCB)", "unit": "kg", "rate": 120},
            {"name": "Cables & wires", "unit": "kg", "rate": 30},
        ]
        
        # for item in default_rates:
        #     product = EwasteProduct(name=item["name"], unit=item["unit"], rate=item["rate"])
        #     db.session.add(product)

        db.session.commit()
        print("✨ Database successfully reset and seeded with fresh data!")

if __name__ == "__main__":
    reset_and_seed()