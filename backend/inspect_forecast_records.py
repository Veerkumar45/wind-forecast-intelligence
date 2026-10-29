
import requests
from collections import Counter

URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream"

params = {
    "publishDateTimeFrom": "2026-01-01T00:00:00Z",
    "publishDateTimeTo": "2026-01-01T06:00:00Z",
}

response = requests.get(URL, params=params, timeout=60)
response.raise_for_status()

records = response.json()

print("Total forecast records:", len(records))

print("\nRecords per publication time:")
for publish_time, count in sorted(
    Counter(r["publishTime"] for r in records).items()
):
    print(f"{publish_time}: {count} records")

print("\nFirst 10 records:")
for record in records[:10]:
    print(record)

print("\nPublication time range:")
if records:
    print(min(r["publishTime"] for r in records))
    print(max(r["publishTime"] for r in records))

print("\nDelivery time range:")
if records:
    print(min(r["startTime"] for r in records))
    print(max(r["startTime"] for r in records))