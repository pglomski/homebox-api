# Homebox Python API & CLI

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-GPLv3-blue)

A Python 3.8+ wrapper and command-line interface for the [Homebox](https://github.com/hay-kot/homebox) inventory system.

This tool enables you to **programmatically manage Homebox locations, items, and tags** and automate bulk operations via CSV — all with full type safety and API abstraction.

---

## 🚀 Features

- 🔐 Authenticates securely with your Homebox instance
- 📦 Full CRUD support for Locations, Tags, and Items
- 📁 Import/export inventory via human-readable CSV
- 🔎 Recursive location search with optional case insensitivity
- 📂 Nested location resolution by path (`Attic/Box 1/Shelf A`)
- 🧪 Type-annotated Pythonic classes (`Location`, `Item`, `Tag`)
- 💻 CLI for automation in scripts and terminals

---

## 📦 Installation

```bash
pip install requests
# or if using as CLI
chmod +x homebox.py
```

---

## 🛠 Setup

Copy the sample file and update with your credentials:

```
cp creds.json.sample creds.json
```

---

## 🐍 Python Usage

```python
from homebox import get_client

client = get_client()

# Create a new location
client.create_location("Office", "My work storage area")

# Get all items
items = client.get_items()

# Export to CSV
client.export_items_readable_csv("items.csv")
```

---

## 🧰 CLI Usage

```bash
# Create one location
./homebox.py create-location --name "Kitchen" --description "Food storage" --parent "Pantry"

# Bulk import locations from CSV
./homebox.py import-locations --csv locations.csv

# Export all items to CSV
./homebox.py export-items --csv items.csv

# Update items from edited CSV
./homebox.py update-items --csv items.csv
```

---

## 📄 CSV Format

**Locations Import:**

```csv
name,description,parent
Box 1,Tools,Garage
Drawer A,Screws,Box 1
```

**Items Export/Update:**

```csv
id,name,description,quantity,locationPath,tags
...,Hammer,Steel claw hammer,1,Garage/Box 1,"tools,hand"
```

---

## 🔍 Searching

Use the Python API to search locations:

```python
matches = client.search_location("drawer", ignore_case=True)
```

---

## 🧪 Requirements

- Python 3.8+
- [Homebox](https://github.com/hay-kot/homebox) server running (tested with API v1)

---

## 📚 License

Licensed under the terms of the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

---

## 👨‍💻 Author

Maintained by [pglomski](https://github.com/pglomski) with ❤️.
