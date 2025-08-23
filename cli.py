"""
cli.py – Updated CLI interface for scale logger
"""

import argparse
from scale_logger import db


def parse_args():
    parser = argparse.ArgumentParser(description="Food Logger CLI")
    subparsers = parser.add_subparsers(dest="command")

    log = subparsers.add_parser("log", help="Log a new food entry")
    log.add_argument("--weight", type=float, required=True)
    log.add_argument("--type", required=True, help="Food type (Produce, Dry, etc.)")
    log.add_argument("--source", required=True, help="Donation source")

    subparsers.add_parser("delete-last", help="Mark the last entry as deleted")
    subparsers.add_parser("undelete-last", help="Unmark the most recently deleted entry")

    report = subparsers.add_parser("report", help="Generate report by source and date")
    report.add_argument("--source", required=True)
    report.add_argument("--start", help="Start date (YYYY-MM-DD)")
    report.add_argument("--end", help="End date (YYYY-MM-DD)")

    subparsers.add_parser("list-sources", help="List available sources")

    addsrc = subparsers.add_parser("add-source", help="Add a new donation source")
    addsrc.add_argument("--name", required=True)

    show = subparsers.add_parser("show", help="Show log entries")
    show.add_argument("--all", action="store_true", help="Include deleted entries")

    return parser.parse_args()


def main():
    args = parse_args()
    db.initialize_db()

    if args.command == "log":
        db.log_entry(args.weight, args.type, args.source)
        print("✅ Entry logged.")

    elif args.command == "delete-last":
        db.delete_last_entry()
        print("🗑️ Last entry marked deleted.")

    elif args.command == "undelete-last":
        db.undelete_last()
        print("♻️ Undeletion complete.")

    elif args.command == "report":
        totals, total_weight, rows = db.create_report(args.source, args.start, args.end)
        print(f"📊 Report for '{args.source}'")
        print(f"Total weight: {total_weight:.2f} lbs")
        for cat, weight in totals:
            print(f" - {cat}: {weight:.2f} lbs")
        print(" Entry breakdown:")
        for row in rows:
            print(row)

    elif args.command == "add-source":
        conn = db.get_connection()
        conn.execute("INSERT OR IGNORE INTO sources (name) VALUES (?)", (args.name,))
        conn.commit()
        print(f"✅ Source '{args.name}' added.")

    elif args.command == "list-sources":
        sources = db.get_sources()
        print("📚 Available Sources:")
        for s in sources:
            print(f" - {s}")

    elif args.command == "show":
        rows = db.get_all_logs(include_deleted=args.all)
        for row in rows:
            print(row)

    else:
        print("⚠️ No valid command provided. Use --help to see options.")


if __name__ == "__main__":
    main()
