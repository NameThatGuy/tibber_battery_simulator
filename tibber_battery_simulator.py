import requests
import csv
import datetime
from collections import defaultdict

# Tibber API configuration
API_TOKEN = 'YOUR_TIBBER_API_TOKEN'
API_URL = 'https://api.tibber.com/v1-beta/gql'
HEADERS = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json'
}

# Time range for data retrieval
START_DATE = datetime.datetime(2024, 10, 1, tzinfo=datetime.timezone.utc)
END_DATE = datetime.datetime(2025, 3, 29, 23, 59, tzinfo=datetime.timezone.utc)

# Battery configuration
BATTERY_CONFIGURATIONS = [2, 4, 8, 16, 24]  # kWh
BATTERY_CHARGE_POWER_KW = 12.0

def create_query(first=744, after_cursor=None):
    after_str = f', after: "{after_cursor}"' if after_cursor else ''
    return {
        "query": f"""
        query {{
          viewer {{
            homes {{
              consumption(resolution: HOURLY, first: {first}{after_str}) {{
                pageInfo {{
                  endCursor
                  hasNextPage
                }}
                nodes {{
                  from
                  to
                  unitPrice
                  unitPriceVAT
                  consumption
                  consumptionUnit
                }}
              }}
            }}
          }}
        }}
        """
    }

def fetch_data():
    all_data = []
    after_cursor = None
    reached_end_date = False

    while not reached_end_date:
        query = create_query(after_cursor=after_cursor)
        response = requests.post(API_URL, headers=HEADERS, json=query)

        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            break

        json_data = response.json()
        homes = json_data.get('data', {}).get('viewer', {}).get('homes', [])
        if not homes or not homes[0].get('consumption'):
            break

        nodes = homes[0]['consumption'].get('nodes', [])
        page_info = homes[0]['consumption'].get('pageInfo', {})

        if not nodes:
            break

        for node in nodes:
            ts = node.get("from")
            if ts:
                dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt < START_DATE:
                    continue
                if dt > END_DATE:
                    reached_end_date = True
                    break
                all_data.append(node)

        print(f"{len(nodes)} entries loaded.")

        if not page_info.get('hasNextPage'):
            break

        after_cursor = page_info.get('endCursor')

    return all_data

def simulate_battery(data, battery_capacity):
    battery_level = battery_capacity
    day_to_prices = defaultdict(list)
    total_cost_option1 = 0.0
    total_cost_option2 = 0.0

    for row in data:
        ts = row.get("from")
        unit_price = row.get("unitPrice")
        unit_price_vat = row.get("unitPriceVAT")
        if ts and unit_price is not None and unit_price_vat is not None:
            date_key = ts.split("T")[0]
            full_price = unit_price + unit_price_vat
            day_to_prices[date_key].append((ts, full_price))

    cheapest_hours = {
        day: sorted(hours, key=lambda x: x[1])[:2]
        for day, hours in day_to_prices.items()
    }

    simulated_data = []

    for row in data:
        row = row.copy()
        ts = row.get("from")
        unit_price = row.get("unitPrice")
        unit_price_vat = row.get("unitPriceVAT")
        consumption = row.get("consumption")

        if ts is None or unit_price is None or unit_price_vat is None or consumption is None:
            row.update({
                'real_consumption': '',
                'real_cost': '',
                'battery_used': '',
                'grid_usage': '',
                'battery_cost': '',
                'battery_level_before': '',
                'battery_level_after': '',
                'battery_recharged': '',
                'battery_recharge_cost': '',
                'note': 'invalid entry'
            })
            simulated_data.append(row)
            continue

        full_price = unit_price + unit_price_vat
        date_key = ts.split("T")[0]
        hour_ts = ts

        row['real_consumption'] = consumption
        row['real_cost'] = full_price * consumption
        row['battery_level_before'] = battery_level
        total_cost_option1 += full_price * consumption

        # Dynamic minimum limit: 20% of capacity or 2 kWh, whichever is higher
        dynamic_min_kwh = max(2.0, 0.2 * battery_capacity)

        # Smart discharging: only discharge if price is above daily median
        prices_today = [p[1] for p in day_to_prices.get(date_key, [])]
        price_median = sorted(prices_today)[len(prices_today) // 2] if prices_today else full_price
        only_discharge_if_profitable = full_price > price_median

        if battery_level >= consumption and only_discharge_if_profitable:
            battery_used = consumption
            grid_usage = 0.0
            battery_cost = 0.0
            battery_level -= battery_used
        elif battery_level > dynamic_min_kwh and only_discharge_if_profitable:
            usable_energy = max(0, battery_level - dynamic_min_kwh)
            battery_used = min(consumption, usable_energy)
            grid_usage = consumption - battery_used
            battery_cost = grid_usage * full_price
            battery_level -= battery_used
        else:
            battery_used = 0.0
            grid_usage = consumption
            battery_cost = grid_usage * full_price

        row['battery_used'] = battery_used
        row['grid_usage'] = grid_usage
        row['grid_cost'] = full_price * grid_usage

        # Charging during cheapest hours
        is_cheapest_hour = any(hour_ts == ch[0] for ch in cheapest_hours.get(date_key, []))
        battery_recharged = 0.0
        battery_recharge_cost = 0.0
        note = ''

        if is_cheapest_hour:
            if battery_level < battery_capacity:
                possible_recharge = min(BATTERY_CHARGE_POWER_KW, battery_capacity - battery_level)
                battery_recharged = possible_recharge
                battery_recharge_cost = battery_recharged * full_price
                battery_level += battery_recharged
                note = 'charged'

        row['battery_recharged'] = battery_recharged
        row['battery_recharge_cost'] = battery_recharge_cost
        row['battery_level_after'] = battery_level
        row['note'] = note
        row['total_cost_battery_and_grid'] = battery_recharge_cost + full_price * grid_usage

        total_cost_option2 += battery_cost + battery_recharge_cost
        simulated_data.append(row)

    print(f"Battery capacity: {battery_capacity} kWh")
    print(f"Cost Option 1 (grid only): {total_cost_option1:.2f} €")
    print(f"Cost Option 2 (with battery):  {total_cost_option2:.2f} €\n")
    return simulated_data

def save_data(data, suffix):
    filename = f'tibber_battery_simulation_{suffix}.csv'
    if not data:
        print("No data available, CSV will not be created.")
        return

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        for row in data:
            formatted_row = {
                k: (f"{v:.6f}".replace('.', ',') if isinstance(v, float) else v)
                for k, v in row.items()
            }
            writer.writerow(formatted_row)

    print(f"CSV file created successfully: {filename}")

def main():
    data = fetch_data()
    if data:
        print(f"{len(data)} data points loaded.")
        for capacity in BATTERY_CONFIGURATIONS:
            simulated = simulate_battery(data, capacity)
            save_data(simulated, f"{int(capacity)}kWh")
    else:
        print("No consumption data found.")

if __name__ == '__main__':
    main()