
# 📘 `db.py` Reference Documentation

> A lightweight SQLite3 interface for logging and reporting food donations by type, weight, source, and time.

---

## 🔧 Database Initialization

### `initialize_db()`
Initializes the SQLite database with three tables:
- `sources`
- `types`
- `logs`

Also calls `seed_sources()` and `seed_types()` to populate default values.

---

## 🌱 Seed Data

### `seed_sources()`
Inserts a set of default food donation sources (e.g., “Trader Joe’s”, “Wegmans”) if they don’t already exist.

### `seed_types()`
Inserts default food type categories (`Produce`, `Dry`, `Meat`, etc.) with a defined sort order.

---

## 📋 Data Access: Lists

### `get_sources() -> List[str]`
Returns an alphabetically sorted list of all source names.

### `get_types() -> List[str]`
Returns a list of type names sorted by `sort_order`.

---

## 🔍 Lookup Helpers

### `get_id_by_name(table: str, name: str) -> int | None`
Returns the `id` for a given name in the specified table (`sources` or `types`). Returns `None` if not found.

---

## 📥 Logging Entries

### `log_entry(weight: float, dtype: str, source: str)`
Inserts a new entry into the `logs` table with:
- `weight_lb`
- type and source (looked up by name)
- timestamp = current time
- action = `'record'`

**Alias:** This is equivalent to calling `insert_log(...)` in the GUI.

---

## 🔁 Undo Operations

### `delete_last_entry()`
Marks the most recent `'record'` entry as deleted by inserting a new entry with the same info but `action='delete'`.

### `undelete_last_entry()`
Removes the most recent `'delete'` entry (restoring the prior `'record'`).

---

## 📄 Reporting

### `create_report(source: str, start_date: str = None, end_date: str = None) -> (Dict[str, float], float, List[Tuple])`

Returns:
- `cat_totals`: dict mapping category names to weight totals
- `total_weight`: float, sum of all weights
- `rows`: list of all matching log records

Date range is interpreted as inclusive. If `start_date` is omitted, today’s date is used.

---

## 📜 Full Log Retrieval

### `get_all_logs(include_deleted: bool = False) -> List[Tuple[str, float, str, str, str]]`
Returns a list of all logs in the format:
```
(timestamp, weight_lb, source_name, type_name, action)
```

Set `include_deleted=True` to show `'delete'` entries as well.

---

## 💾 DB Path Constant

### `DB_PATH`
Hardcoded path: `"scale_logger/foodlog.db"`

Change this if you want to point to a different location.
