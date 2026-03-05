from app import app
from models import db, User, Branch
import secrets

def create_customer():
    with app.app_context():
        # Ensure a branch exists
        branch = Branch.query.first()
        if not branch:
            branch = Branch(name="Main Branch", code="MAIN001")
            db.session.add(branch)
            db.session.commit()
            print("Created default branch.")

        # Check if customer user already exists
        username = "customer_user"
        customer = User.query.filter_by(username=username).first()
        
        if not customer:
            customer = User(
                username=username,
                email="customer@example.com",
                role="customer",
                branch_id=branch.id,
                phone="1234567890",
                address="123 Customer Lane",
                is_active=True
            )
            customer.set_password("customer123")
            db.session.add(customer)
            db.session.commit()
            print(f"Created customer: {username} with password: customer123")
        else:
            print(f"Customer {username} already exists.")

if __name__ == "__main__":
    create_customer()
