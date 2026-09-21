import random
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template_string
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUEST_COUNT = Counter('app_requests_total', 'Total requests', ['endpoint'])
DELAYED_TRAINS = Gauge('delayed_trains_current', 'Number of currently delayed trains')

STATIONS = [
    {"code": "KBH", "name": "København H"},
    {"code": "AAR", "name": "Aarhus H"},
    {"code": "ODE", "name": "Odense"},
    {"code": "AAL", "name": "Aalborg"},
    {"code": "ESB", "name": "Esbjerg"},
]

DESTINATIONS = ["København H", "Aarhus H", "Odense", "Aalborg", "Esbjerg", "Randers", "Roskilde"]


def generate_departures(station_code, count=6):
    """
    Simulated live departures so the dashboard works with zero setup.
    Swap this out for a real call to the Rejseplanen or DSB Open Data API
    once you have an API key — see README.md for how.
    """
    now = datetime.now()
    station_name = next((s["name"] for s in STATIONS if s["code"] == station_code), None)
    departures = []
    delayed = 0
    for _ in range(count):
        dep_time = now + timedelta(minutes=random.randint(2, 90))
        delay_min = random.choice([0, 0, 0, 0, 2, 5, 12])
        if delay_min > 0:
            delayed += 1
        destination = random.choice([d for d in DESTINATIONS if d != station_name])
        departures.append({
            "destination": destination,
            "scheduled": dep_time.strftime("%H:%M"),
            "delay_minutes": delay_min,
            "platform": random.randint(1, 12),
        })
    DELAYED_TRAINS.set(delayed)
    return sorted(departures, key=lambda d: d["scheduled"])


DASHBOARD_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Denmark Railway Dashboard</title>
  <style>
    body { font-family: -apple-system, Arial, sans-serif; background:#0b1d3a; color:#f5f5f5; margin:0; padding:2rem; }
    h1 { color:#c60c30; }
    .station { background:#12274d; border-radius:8px; padding:1rem 1.5rem; margin-bottom:1.5rem; }
    table { width:100%; border-collapse: collapse; margin-top:0.5rem; }
    th, td { text-align:left; padding:0.4rem 0.6rem; border-bottom:1px solid #23345c; }
    .on-time { color:#7CFC98; }
    .delayed { color:#FFB020; }
  </style>
</head>
<body>
  <h1>Denmark Railway — Live Departures (Demo Data)</h1>
  {% for station in stations %}
    <div class="station">
      <h2>{{ station.name }} ({{ station.code }})</h2>
      <table>
        <tr><th>Destination</th><th>Scheduled</th><th>Delay</th><th>Platform</th></tr>
        {% for dep in departures[station.code] %}
          <tr class="{{ 'delayed' if dep.delay_minutes > 0 else 'on-time' }}">
            <td>{{ dep.destination }}</td>
            <td>{{ dep.scheduled }}</td>
            <td>{{ dep.delay_minutes }} min{{ 's' if dep.delay_minutes != 1 else '' }}</td>
            <td>{{ dep.platform }}</td>
          </tr>
        {% endfor %}
      </table>
    </div>
  {% endfor %}
</body>
</html>
"""


@app.route('/')
def dashboard():
    REQUEST_COUNT.labels(endpoint='/').inc()
    departures = {s["code"]: generate_departures(s["code"]) for s in STATIONS}
    return render_template_string(DASHBOARD_TEMPLATE, stations=STATIONS, departures=departures)


@app.route('/api/departures/<station_code>')
def api_departures(station_code):
    REQUEST_COUNT.labels(endpoint='/api/departures').inc()
    station_code = station_code.upper()
    if station_code not in [s["code"] for s in STATIONS]:
        return jsonify({"error": "unknown station code"}), 404
    return jsonify(generate_departures(station_code))


@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
