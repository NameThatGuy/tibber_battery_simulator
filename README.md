# ⚡ Tibber Battery Optimization Simulator

This Python script retrieves hourly energy consumption data from the Tibber API and simulates cost savings by using a battery to shift energy usage to the two cheapest hours of each day.

## 🚀 Purpose

The goal is to evaluate how much energy cost can be saved by using a battery of different capacities. The simulation compares two scenarios:

1. **Option 1:** Energy is sourced exclusively from the grid.
2. **Option 2:** A battery is used to cover consumption and is only charged during the two cheapest hours of the day.

The script supports batch testing with various battery capacities and outputs the results in separate CSV files.

---

## 🔧 Features

- ✅ Fetch hourly consumption data from Tibber via GraphQL
- ✅ Supports paging with `after` cursors to collect >30 days of data
- ✅ Limits data to a defined date range (e.g., July to December 2024)
- ✅ Identifies the 2 cheapest hours each day to charge the battery
- ✅ Simulates grid-only and battery-optimized scenarios
- ✅ Calculates energy costs for both scenarios
- ✅ Saves all results (including intermediate battery states and cost breakdowns) to CSV
- ✅ Compares results across different battery sizes

---

## 🧠 Requirements

- Python 3.9+
- A Tibber account and a valid [Tibber API token](https://developer.tibber.com/)
- Libraries:
  - `requests`
  - `csv`
  - `datetime`

You can install requirements using:

```bash
pip install requests
```

---

## ⚙️ Configuration

Edit the following variables at the top of the script:

```python
API_TOKEN = 'YOUR_TIBBER_API_TOKEN'
START_DATE = datetime.datetime(2024, 7, 1, tzinfo=datetime.timezone.utc)
END_DATE = datetime.datetime(2024, 12, 31, 23, 59, tzinfo=datetime.timezone.utc)
BATTERY_CONFIGURATIONS = [2, 4, 8, 16, 24]  # in kWh
BATTERY_CHARGE_POWER_KW = 12.0  # max charge per hour
```

---

## 📊 Output

The script generates CSV files in the current directory:

- `tibber_battery_simulation_2kWh.csv`
- `tibber_battery_simulation_4kWh.csv`
- ...
- `tibber_battery_simulation_24kWh.csv`

Each file contains hourly consumption, unit prices, battery charge/discharge status, and total cost calculations.

At the end, the terminal displays a cost comparison for each battery size:

```
Battery Capacity: 8 kWh
Option 1 (Grid Only): 422.55 €
Option 2 (With Battery): 371.12 €
```

---

## 📈 Optimization Ideas (Future Work)

- Integrate weather forecasts and solar production predictions.
- Implement predictive charging (e.g., charging ahead of price spikes).
- Visualize results with graphs.
- Run as a scheduled cron job to track live savings.
