import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def inspect_dataset(dataset_name):
    url = f"{BASE_URL}/{dataset_name}/stream"

    print(f"\nChecking dataset: {dataset_name}")

    try:
        response = requests.get(url, timeout=30)

        print(f"HTTP status: {response.status_code}")
        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):
            print(f"Records returned: {len(data)}")

            if data:
                print("Available fields:", list(data[0].keys()))
                print("\nSample record:")
                print(data[0])
            else:
                print("No records returned.")

        elif isinstance(data, dict):
            print("Response fields:", list(data.keys()))
            print(data)

        else:
            print("Unexpected response format:", type(data).__name__)

    except requests.RequestException as error:
        print(f"Request failed: {error}")

    except ValueError as error:
        print(f"Could not parse JSON: {error}")


if __name__ == "__main__":
    inspect_dataset("FUELHH")
    inspect_dataset("WINDFOR")