import requests
def fetch_currency_data():
    API_KEY = "freedKUooRvZgPcXI1amFxNGda4OJMzO"
    API_URL = f"http://api.navasan.tech/latest/?api_key={API_KEY}"

    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()

        # Extract numeric fields and convert to float
        required_fields = ["usd_sell", "gbp", "eur"]
        currency_data = {}
        for field in required_fields:
            value = data.get(field)
            if isinstance(value, dict) and "value" in value:  # Handle nested structure
                currency_data[field] = float(value["value"]) / 1000
            elif isinstance(value, (int, float, str)) and value:  # Fallback for flat structure
                currency_data[field] = float(value) / 1000
            else:
                currency_data[field] = None  # Handle missing data gracefully

        # Add fixed conversion for IRTT
        currency_data["irtt"] = 1  # Assume a fixed value for demonstration
        currency_data["usd"] = currency_data.pop("usd_sell")
        return currency_data

    except requests.exceptions.RequestException as e:
        print(f"API Request Error: {e}")
        return None
    except ValueError as e:
        print(f"Data Processing Error: {e}")
        return None

# testing:
# print(fetch_currency_data())

def convert_currency( amount, from_currency, info, to_currency):
    """
    Converts the given amount from one currency to another.
    """
    if from_currency == to_currency:
        return float(amount)

    currency_data = info # fetch_currency_data()
    # currency_data["irtt"] = "1000"

    # print(currency_data)

    if not currency_data:
        raise ValueError("Failed to fetch currency data.")

    # Ensure currencies exist in the fetched data
    if from_currency not in currency_data or to_currency not in currency_data:
        raise ValueError(f"Currency {from_currency} or {to_currency} not supported.")

    # Extract rates
    base_rate_from = float(currency_data[from_currency])
    base_rate_to = float(currency_data[to_currency])

    # if not isinstance(base_rate_from, (int, float)) or not isinstance(base_rate_to, (int, float)):
    #     raise ValueError("Currency rates must be numeric values.")

    # Conversion logic
    converted_amount = (float(amount) / base_rate_to) * base_rate_from

    return converted_amount


# print(f"{val:,}")
# print(convert_currency(10, "usd", info, "gbp"))
#
# fetch_currency_data()