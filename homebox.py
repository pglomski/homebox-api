#!/usr/bin/env python3
import requests
import logging
import argparse
import csv

base_url = "http://localhost:3100/api/v1"
username="patrick.glomski@gmail.com"
with open('homebox.key', 'r') as ifile:
    password = ifile.read()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class HomeboxClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Content-Type": "application/json"}
        self._authenticate(username, password)

    def _authenticate(self, username, password):
        login_url = f"{self.base_url}/users/login"
        res = requests.post(login_url, json={"username": username, "password": password}, headers=self.headers)
        res.raise_for_status()
        token = res.json().get("token")
        self.headers["Authorization"] = token

    def get_all_locations(self):
        res = requests.get(f"{self.base_url}/locations", headers=self.headers)
        res.raise_for_status()
        return res.json()

    def get_location(self, name, parent_name=None):
        locations = self.get_all_locations()
        matches = [loc for loc in locations if loc["name"] == name]

        if parent_name is None:
            return matches[0] if matches else None

        for loc in matches:
            parent_id = loc.get("parentId")
            if parent_id:
                parent = next((p for p in locations if p["id"] == parent_id), None)
                if parent and parent["name"] == parent_name:
                    return loc
        return None

    def create_location(self, name, description="", parent_name=None):
        if self.get_location(name, parent_name):
            logging.info(f"Location '{name}' (parent: '{parent_name}') already exists. Skipping.")
            return None

        parent_id = None
        if parent_name:
            parent = self.get_location(parent_name)
            if not parent:
                raise ValueError(f"Parent location '{parent_name}' not found.")
            parent_id = parent["id"]

        data = {
            "name": name,
            "description": description,
            "parentId": parent_id
        }
        res = requests.post(f"{self.base_url}/locations", headers=self.headers, json=data)
        res.raise_for_status()
        logging.info(f"Created location '{name}' under parent '{parent_name}'")
        return res.json()

c = HomeboxClient(base_url, username, password)

def load_locations_from_csv(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        locations = []
        for row in reader:
            locations.append({
                "name": row["name"],
                "description": row.get("description", ""),
                "parent": row.get("parent", None)
            })
        return locations


def cli():
    parser = argparse.ArgumentParser(description="Create Homebox locations with optional parent.")
    parser.add_argument("--base-url", required=True, help="Base API URL, e.g. http://localhost:3100/api/v1")
    parser.add_argument("--username", required=True, help="Homebox username (email)")
    parser.add_argument("--password", required=True, help="Homebox password")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="Single location name to create")
    group.add_argument("--csv", help="Path to CSV file with multiple locations")

    parser.add_argument("--description", default="", help="Optional location description (single only)")
    parser.add_argument("--parent", help="Optional parent location name (single only)")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without making changes")

    args = parser.parse_args()

    client = HomeboxClient(args.base_url, args.username, args.password)

    if args.name:
        if args.dry_run:
            logging.info(f"Dry run: would create location '{args.name}' with parent '{args.parent}'")
        else:
            client.create_location(args.name, args.description, args.parent)
    else:
        locations = load_locations_from_csv(args.csv)
        for loc in locations:
            if args.dry_run:
                logging.info(f"Dry run: would create location '{loc['name']}' with parent '{loc['parent']}'")
            else:
                client.create_location(loc["name"], loc["description"], loc["parent"])


if __name__ == "__main__":
    cli()

