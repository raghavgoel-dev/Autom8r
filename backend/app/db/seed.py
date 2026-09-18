"""Seed the database with demo leads.

ALL DATA IS FAKE — fictional people, fictional phone numbers, for a demo
project only (spec section 59: no real customer information, ever).

Run from the backend directory:
    python -m app.db.seed

Idempotent: if leads already exist, the seed does nothing.
"""
from app.db.database import create_all_tables
from app.db.session import SessionLocal
from app.logging_config import get_logger
from app.models.lead import Lead
from app.services.scoring import LeadSignals, compute_lead_score, priority_for_score

logger = get_logger(__name__)

# (name, phone, email, city, business_type, budget, requirement, timeline,
#  monthly_queries, status, source)
_DEMO_LEADS: list[tuple[str, str, str | None, str | None, str | None, str | None, str | None, str | None, int | None, str, str]] = [
    ("Rahul Sharma", "9876543210", "rahul.demo@example.com", "Mumbai", "real estate", "₹15k/month", "WhatsApp customer support automation", "within 2 months", 500, "qualified", "chat"),
    ("Aman Gupta", "9999999999", None, "Gurgaon", "retail", None, "customer support automation", None, 200, "new", "webhook"),
    ("Priya Nair", "9812345678", "priya.demo@example.com", "Bengaluru", "healthcare", "₹25k/month", "appointment booking bot", "this month", 800, "contacted", "chat"),
    ("Neha Verma", "9898989898", "neha.demo@example.com", "Pune", "education", None, "SMS campaign for admissions", None, 150, "new", "api"),
    ("Vikram Singh", "9765432109", None, "Jaipur", "hospitality", "₹8k/month", "voice bot for reservations", "within 3 months", 350, "qualified", "chat"),
    ("Ananya Iyer", "9654321098", "ananya.demo@example.com", "Chennai", "e-commerce", "₹50k/month", "WhatsApp order status automation", "ASAP", 2000, "converted", "api"),
    ("Karan Mehta", "9543210987", None, "Delhi", "automobile", None, "service reminder SMS", None, 90, "lost", "webhook"),
    ("Rohit Kulkarni", "9432109876", "rohit.demo@example.com", "Hyderabad", "logistics", "₹20k/month", "lead qualification agent", "next month", 600, "contacted", "chat"),
]


def seed() -> int:
    """Insert demo leads if the table is empty. Returns rows inserted."""
    create_all_tables()
    with SessionLocal() as db:
        existing = db.query(Lead).count()
        if existing:
            logger.info("seed skipped: %d leads already present", existing)
            return 0
        for (name, phone, email, city, business_type, budget, requirement,
             timeline, monthly_queries, status, source) in _DEMO_LEADS:
            signals = LeadSignals(
                phone=phone, email=email, requirement=requirement,
                business_type=business_type, city=city, timeline=timeline,
                monthly_queries=monthly_queries,
            )
            score = compute_lead_score(signals)
            db.add(Lead(
                name=name, phone=phone, email=email, city=city,
                business_type=business_type, budget=budget,
                requirement=requirement, timeline=timeline,
                monthly_queries=monthly_queries, lead_score=score,
                priority=priority_for_score(score), status=status, source=source,
            ))
        db.commit()
        logger.info("seeded %d demo leads (all fictional)", len(_DEMO_LEADS))
        return len(_DEMO_LEADS)


if __name__ == "__main__":
    inserted = seed()
    print(f"Seed complete: {inserted} demo leads inserted.")
