import sys
from datetime import datetime, timedelta
from app import app, db, User, SolvedProblem, bcrypt, DATA

def seed_srs_alerts():
    """
    Creates a specific state where a user has 'decaying' memory fragments
    (Review overdue), triggering the SRS Alert system in the dashboard.
    """
    print("--- 🟢 INITIALIZING SRS SEED SEQUENCE ---")

    # Ensure Data is loaded (needed to check if Problem IDs exist)
    if DATA.empty:
        print("❌ Error: CSV Data not loaded. Please run helper.py first.")
        return

    with app.app_context():
        # 1. SETUP TEST USER
        username = "neo"
        password = "matrix"
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"🧹 Clearing existing data for '{username}'...")
            SolvedProblem.query.filter_by(user_id=user.id).delete()
            db.session.commit()
        else:
            print(f"👤 Creating new user '{username}'...")
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            user = User(username=username, password=hashed_pw)
            db.session.add(user)
            db.session.commit()

        # 2. DEFINE SCENARIOS
        # We need IDs that definitely exist in your CSV. 
        # ID 1 (Two Sum) and ID 20 (Valid Parentheses) are usually safe bets in LeetCode data.
        
        scenarios = [
            {
                "id": 1, 
                "days_solved_ago": 5, 
                "review_due_days_ago": 2, # Negative means in the past (Overdue)
                "desc": "Severely Overdue (CRITICAL)"
            },
            {
                "id": 20, 
                "days_solved_ago": 3, 
                "review_due_days_ago": 1, # Overdue by 1 day
                "desc": "Moderately Overdue (WARNING)"
            },
            {
                "id": 217, # Contains Duplicate
                "days_solved_ago": 0,
                "review_due_days_ago": -1, # Due in future (Tomorrow)
                "desc": "Safe (No Alert)"
            }
        ]

        print("💉 Injecting memory fragments...")

        for s in scenarios:
            # Calculate dates
            solved_date = datetime.utcnow() - timedelta(days=s["days_solved_ago"])
            
            # If review_due_days_ago is positive, it was due in the past.
            # If negative, it is due in the future.
            # Example: due 2 days ago = Now - 2 days.
            due_date = datetime.utcnow() - timedelta(days=s["review_due_days_ago"])

            problem = SolvedProblem(
                user_id=user.id,
                problem_id=s["id"],
                solved_at=solved_date,
                srs_interval=1.0, # Standard starting interval
                next_review_at=due_date
            )
            
            db.session.add(problem)
            print(f"   -> Problem ID {s['id']}: {s['desc']} | Next Review: {due_date.strftime('%Y-%m-%d %H:%M')}")

        db.session.commit()
        print("--- ✅ SEQUENCE COMPLETE ---")
        print(f"👉 Login with User: {username} | Pass: {password}")
        print("👉 You should see 2 Red Alert Missions on the Dashboard right away.")

if __name__ == "__main__":
    seed_srs_alerts()