"""Validate and pool route/day counts shared by descriptive analyses."""

COUNTS = ("records", "low_floor_records", "regular_records", "unknown_records")


def aggregate_routes(rows):
    routes = {}
    seen = set()
    for row in rows:
        key = (row["route_id"], row["date"])
        if not all(key) or key in seen:
            raise ValueError("Empty or duplicate route/date")
        seen.add(key)
        if any(type(row[field]) is not int or row[field] < 0 for field in COUNTS):
            raise ValueError("Record counts must be nonnegative integers")
        if row["records"] != sum(row[field] for field in COUNTS[1:]):
            raise ValueError("Classification counts do not sum to route records")
        name = row.get("route_name", row["route_id"])
        route = routes.setdefault(row["route_id"], {
            "route_name": name,
            **dict.fromkeys(COUNTS, 0),
            "dates": [],
        })
        if route["route_name"] != name:
            raise ValueError("Inconsistent route name")
        for field in COUNTS:
            route[field] += row[field]
        route["dates"].append(row["date"])
    for route in routes.values():
        total = route["records"]
        route["lower"] = route["low_floor_records"] / total if total else None
        route["upper"] = (route["low_floor_records"] + route["unknown_records"]) / total if total else None
        route["dates"].sort()
    return routes
