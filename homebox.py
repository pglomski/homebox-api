#!/usr/bin/env python3
import requests
import logging
import argparse
import csv
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable

base_url = "http://localhost:3100/api/v1"
username="patrick.glomski@gmail.com"
with open('homebox.key', 'r', encoding='utf8') as ifile:
    password = ifile.read().strip('\n')

def get_client():
    return HomeboxClient(base_url, username, password)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

@dataclass
class Location:
    id: str
    name: str
    description: str
    parentId: Optional[str]
    client: 'HomeboxClient' = field(repr=False)

    @property
    def parent(self) -> Optional['Location']:
        if self.parentId is None:
            return None
        return next((l for l in self.client.get_all_locations() if l.id == self.parentId), None)

    def delete(self):
        res = requests.delete(f"{self.client.base_url}/locations/{self.id}", headers=self.client.headers)
        res.raise_for_status()
        logging.info(f"Deleted location '{self.name}'")

    def rename(self, new_name: str):
        data = {"name": new_name, "description": self.description, "parentId": self.parentId}
        res = requests.put(f"{self.client.base_url}/locations/{self.id}", headers=self.client.headers, json=data)
        res.raise_for_status()
        self.name = new_name

    def set_description(self, new_description: str):
        data = {"name": self.name, "description": new_description, "parentId": self.parentId}
        res = requests.put(f"{self.client.base_url}/locations/{self.id}", headers=self.client.headers, json=data)
        res.raise_for_status()
        self.description = new_description

    def set_parent(self, new_parent_name: str):
        parent = self.client.get_location(new_parent_name)
        if not parent:
            raise ValueError(f"Parent location '{new_parent_name}' not found.")
        data = {"name": self.name, "description": self.description, "parentId": parent["id"]}
        res = requests.put(f"{self.client.base_url}/locations/{self.id}", headers=self.client.headers, json=data)
        res.raise_for_status()
        self.parentId = parent["id"]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "parentId": self.parentId
        }

@dataclass
class Tag:
    id: str
    name: str
    client: 'HomeboxClient' = field(repr=False)

    def delete(self):
        res = requests.delete(f"{self.client.base_url}/tags/{self.id}", headers=self.client.headers)
        res.raise_for_status()

    def rename(self, new_name: str):
        res = requests.put(f"{self.client.base_url}/tags/{self.id}", headers=self.client.headers, json={"name": new_name})
        res.raise_for_status()
        self.name = new_name

    def to_dict(self):
        return {"id": self.id, "name": self.name}

@dataclass
class Item:
    id: str
    name: str
    description: str
    quantity: int
    locationId: Optional[str]
    tagIds: List[str]
    client: 'HomeboxClient' = field(repr=False)

    def delete(self):
        res = requests.delete(f"{self.client.base_url}/items/{self.id}", headers=self.client.headers)
        res.raise_for_status()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quantity": self.quantity,
            "locationId": self.locationId,
            "tagIds": self.tagIds
        }

class HomeboxClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Content-Type": "application/json"}
        self._authenticate(username, password)

    def _authenticate(self, username, password):
        res = requests.post(f"{self.base_url}/users/login", json={"username": username, "password": password}, headers=self.headers)
        res.raise_for_status()
        self.headers["Authorization"] = res.json()["token"]
        print(res.json()["token"])

    def get_all_locations(self) -> List[Location]:
        """
        Fetches all locations and enriches them with parentId by querying each /locations/{id}.
        """
        # Step 1: Fetch the reduced list
        res = requests.get(f"{self.base_url}/locations", headers=self.headers)
        res.raise_for_status()
        base_locs = res.json()
    
        locations = []
        for loc in base_locs:
            loc_id = loc["id"]
    
            # Step 2: Fetch full detail for each location
            detail_res = requests.get(f"{self.base_url}/locations/{loc_id}", headers=self.headers)
            detail_res.raise_for_status()
            detailed = detail_res.json()
    
            parent_obj = detailed.get("parent")
            parent_id = parent_obj["id"] if parent_obj else None
    
            location = Location(
                id=loc_id,
                name=detailed["name"],
                description=detailed.get("description", ""),
                parentId=parent_id,
                client=self
            )
            locations.append(location)
    
        return locations

    def get_location(self, name, parent_name=None) -> Optional[dict]:
        """
        Retrieves a location by name, optionally filtering by parent name.
        Uses /locations for fast match, then /locations/{id} for parent check.
        Returns full location dict with 'parentId' field populated.
        """
        res = requests.get(f"{self.base_url}/locations", headers=self.headers)
        res.raise_for_status()
        all_locs = res.json()
    
        candidates = [l for l in all_locs if l["name"] == name]
        for loc in candidates:
            loc_id = loc["id"]
            detail = requests.get(f"{self.base_url}/locations/{loc_id}", headers=self.headers).json()
            parent = detail.get("parent", {}).get("name")
            if parent_name is None or parent == parent_name:
                # Include parentId for downstream consistency
                detail["parentId"] = detail.get("parent", {}).get("id")
                return detail
    
        return None

    def create_location(self, name, description="", parent_name=None):
        if self.get_location(name, parent_name):
            logging.info(f"Location '{name}' (parent: '{parent_name}') already exists. Skipping.")
            return None
        parent_id = self.get_location(parent_name)["id"] if parent_name else None
        data = {"name": name, "description": description, "parentId": parent_id}
        res = requests.post(f"{self.base_url}/locations", headers=self.headers, json=data)
        res.raise_for_status()
        return res.json()

    def resolve_location_path(self, path: str):
        if not path:
            return None
        parts = path.strip().split('/')
        current_parent = None
        for part in parts:
            loc = self.get_location(part, current_parent)
            if not loc:
                raise ValueError(f"Location path '{path}' is invalid at '{part}'")
            current_parent = part
        return loc["id"]

    def get_tags(self) -> List[Tag]:
        res = requests.get(f"{self.base_url}/tags", headers=self.headers)
        res.raise_for_status()
        return [Tag(id=t["id"], name=t["name"], client=self) for t in res.json()]

    def get_or_create_tag(self, name: str) -> Tag:
        for tag in self.get_tags():
            if tag.name == name:
                return tag
        res = requests.post(f"{self.base_url}/tags", headers=self.headers, json={"name": name})
        res.raise_for_status()
        t = res.json()
        return Tag(id=t["id"], name=t["name"], client=self)

    def resolve_tag_names(self, tag_names_str: str) -> List[str]:
        if not tag_names_str:
            return []
        tag_names = [t.strip() for t in tag_names_str.split(',')]
        return [self.get_or_create_tag(name).id for name in tag_names]

    def get_items(self) -> List[Item]:
        res = requests.get(f"{self.base_url}/items", headers=self.headers)
        res.raise_for_status()
        return [
            Item(
                id=i["id"],
                name=i["name"],
                description=i.get("description", ""),
                quantity=i.get("quantity", 1),
                locationId=i.get("locationId"),
                tagIds=i.get("tagIds", []),
                client=self
            ) for i in res.json()
        ]

    def build_location_lookup_tree(self) -> Dict[str, str]:
        all_locations = self.get_all_locations()
        by_id = {loc.id: loc for loc in all_locations}
        full_paths = {}

        def get_path(loc):
            if loc.id in full_paths:
                return full_paths[loc.id]
            if not loc.parentId:
                full_paths[loc.id] = loc.name
            else:
                parent = by_id.get(loc.parentId)
                full_paths[loc.id] = (get_path(parent) + "/" + loc.name) if parent else loc.name
            return full_paths[loc.id]

        for loc in all_locations:
            get_path(loc)
        return full_paths

    def build_tag_lookup(self) -> Dict[str, str]:
        return {tag.id: tag.name for tag in self.get_tags()}

    def search_location(self, substring: str, ignore_case: bool = True) -> List[Location]:
        all_locations = self.get_all_locations()
        matches = []
        def match(a: str, b: str) -> bool:
            return b.lower() in a.lower() if ignore_case else b in a
        for loc in all_locations:
            if match(loc.name, substring):
                matches.append(loc)
        return matches

    def export_items_readable_csv(self, filepath: str):
        items = self.get_items()
        loc_map = self.build_location_lookup_tree()
        tag_map = self.build_tag_lookup()
        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "description", "quantity", "locationPath", "tags"])
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "quantity": item.quantity,
                    "locationPath": loc_map.get(item.locationId, ""),
                    "tags": ", ".join(tag_map.get(tid, "") for tid in item.tagIds)
                })

    def update_items_from_csv_readable(self, filepath: str, dry_run: bool = False):
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row.get("id")
                if not item_id:
                    logging.warning(f"Missing item id in row: {row}")
                    continue
                location_id = self.resolve_location_path(row.get("locationPath", ""))
                tag_ids = self.resolve_tag_names(row.get("tags", ""))
                data = {
                    "name": row["name"],
                    "description": row.get("description", ""),
                    "quantity": int(row.get("quantity", 1)),
                    "locationId": location_id,
                    "tagIds": tag_ids
                }
                if dry_run:
                    logging.info(f"[DRY RUN] Would update item {item_id}: {data}")
                else:
                    res = requests.put(f"{self.base_url}/items/{item_id}", headers=self.headers, json=data)
                    res.raise_for_status()
                    logging.info(f"Updated item '{row['name']}'")


def load_locations_from_csv(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [{"name": row["name"], "description": row.get("description", ""), "parent": row.get("parent", None)} for row in reader]

def cli():
    parser = argparse.ArgumentParser(description="Homebox CLI for managing locations, tags, and items.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dry-run", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    single_loc = subparsers.add_parser("create-location")
    single_loc.add_argument("--name", required=True)
    single_loc.add_argument("--description", default="")
    single_loc.add_argument("--parent")

    bulk_loc = subparsers.add_parser("import-locations")
    bulk_loc.add_argument("--csv", required=True)

    item_export = subparsers.add_parser("export-items")
    item_export.add_argument("--csv", required=True)

    item_update = subparsers.add_parser("update-items")
    item_update.add_argument("--csv", required=True)

    args = parser.parse_args()
    client = HomeboxClient(args.base_url, args.username, args.password)

    if args.command == "create-location":
        if args.dry_run:
            logging.info(f"[DRY RUN] Would create location '{args.name}' with parent '{args.parent}'")
        else:
            client.create_location(args.name, args.description, args.parent)

    elif args.command == "import-locations":
        for loc in load_locations_from_csv(args.csv):
            if args.dry_run:
                logging.info(f"[DRY RUN] Would create location '{loc['name']}' with parent '{loc['parent']}'")
            else:
                client.create_location(loc["name"], loc["description"], loc["parent"])

    elif args.command == "export-items":
        client.export_items_readable_csv(args.csv)

    elif args.command == "update-items":
        client.update_items_from_csv_readable(args.csv, dry_run=args.dry_run)

if __name__ == "__main__":
    cli()

