import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

PARAMS = {
    "publishDateTimeFrom": "2026-01-01T00:00:00Z",
    "publishDateTimeTo": "2026-02-01T00:00:00Z",
}


def inspect_dataset(dataset_name):
    url = f"{BASE_URL}/{dataset_name}/stream"

    print(f"\nChecking {dataset_name} with historical parameters...")

    try:
        response = requests.get(url, params=PARAMS, timeout=30)

        print("Request URL:", response.url)
        print("HTTP status:", response.status_code)
        print("Response preview:", response.text[:500])

    except requests.RequestException as error:
        print("Request failed:", error)


if __name__ == "__main__":
    inspect_dataset("FUELHH")
    inspect_dataset("WINDFOR")