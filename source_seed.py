"""
source_seed.py – one-time source list initializer
"""

from scale_logger import db

DEFAULT_SOURCES = [
    "Food for Neighbors",
    "Trader Joe's",
    "Whole Foods",
    "Wegmans",
    "Safeway",
    "Good Shepherd donations",
    "FreshFarm St John Neumann"
]

def seed_sources():
    for src in DEFAULT_SOURCES:
        db.add_source(src)
    print("✅ Sources added.")

if __name__ == "__main__":
    db.initialize_db()
    seed_sources()
