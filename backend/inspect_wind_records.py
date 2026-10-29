
import requests
from collections import Counter

URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream"

params = {
    "publishDateTimeFrom": "2026-01-01T00:00:00Z",
    "publishDateTimeTo": "2026-01-01T06:00:00Z",
    "fuelType": "WIND",
}

response = requests.get(URL, params=params, timeout=30)
response.raise_for_status()

records = response.json()

print("Total records:", len(records))
print("\nFuel types:", Counter(r.get("fuelType") for r in records))
print("\nDelivery timestamps:", Counter(r.get("startTime") for r in records))

print("\nRecords:")
for record in records:
    print(record)