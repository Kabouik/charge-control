#!/usr/bin/env python3
import csv
import argparse
from datetime import datetime

def escape_js(s):
    """Escape string for JavaScript"""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

def find_column(row, possible_names):
    """Find a column by trying multiple possible names"""
    for name in possible_names:
        if name in row:
            return row[name]
    raise KeyError(f"None of {possible_names} found in CSV headers")

# Set up argument parser
parser = argparse.ArgumentParser(description='Generate battery level plot')
parser.add_argument('-i', '--input', default='battery-log.csv', 
                    help='Input CSV file path (default: ./battery-log.csv)')
args = parser.parse_args()

# Read CSV data
data = []
with open(args.input, "r") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        data.append({
            "Time": row["Timestamp"],
            "Battery": float(find_column(row, ["Battery level (%)", "Battery level", "Battery"])),
            "Processes": find_column(row, ["Most CPU intensive processes", "Top processes", "Processes"])
        })

# Process data - detect process changes for points
prev_processes = None
label_points = []
for i, entry in enumerate(data):
    entry["Time"] = datetime.strptime(entry["Time"], "%Y-%m-%dT%H:%M:%S%z")
    entry["TimeDisplay"] = entry["Time"].strftime("%H:%M:%S")
    if i == 0 or entry["Processes"] != prev_processes:
        label_points.append(entry)
    prev_processes = entry["Processes"]
    entry["HoverText"] = f"{entry['TimeDisplay']}<br>{entry['Battery']}%<br>{entry['Processes']}"

# Generate JavaScript data strings
time_data = ",".join(f'"{d["Time"].isoformat()}"' for d in data)
battery_data = ",".join(str(d["Battery"]) for d in data)
hover_texts = ",".join(f'"{escape_js(d["HoverText"])}"' for d in data)
label_points_data = ",".join(
    f'{{x:"{d["Time"].isoformat()}",y:{d["Battery"]},text:"{escape_js(d["Processes"])}"}}'
    for d in label_points
)

# Generate HTML
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>charge-control battery log</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        #plot {{ width: 100%; height: 600px; }}
    </style>
</head>
<body>
    <div id="plot"></div>
    
    <script>
        const data = {{
            time: [{time_data}],
            battery: [{battery_data}],
            hoverTexts: [{hover_texts}],
            labelPoints: [{label_points_data}]
        }};

        // Main trace (line)
        const trace1 = {{
            x: data.time,
            y: data.battery,
            mode: 'lines',
            line: {{color: '#440154', width: 2}},
            hoverinfo: 'text',
            hovertext: data.hoverTexts,
            showlegend: false,
            name: 'toto'
        }};

        // Points trace (no hover info)
        const trace2 = {{
            x: data.labelPoints.map(p => p.x),
            y: data.labelPoints.map(p => p.y),
            mode: 'markers',
            marker: {{
                size: 6,
                color: data.labelPoints.map((_, i) => i),
                colorscale: 'Viridis',
                showscale: false
            }},
            hoverinfo: 'skip',
            showlegend: false,
            name: ''
        }};

        const layout = {{
            title: 'Battery percentage and top-5 processes over time',
            xaxis: {{ 
                title: 'Time', 
                tickangle: 45,
                type: 'date'
            }},
            yaxis: {{ 
                title: 'Battery Level (%)',
                range: [0, 100],
                dtick: 10
            }},
            hovermode: 'x unified',
            hoverlabel: {{
                align: 'left',
                bgcolor: 'white',
                font: {{size: 11}},
                namelength: 0
            }}
        }};

        Plotly.newPlot('plot', [trace1, trace2], layout);
    </script>
</body>
</html>
"""

# Save to HTML file
output_file = args.input.replace('.csv', '.html')
with open(output_file, "w") as f:
    f.write(html_content)

print(f"Interactive plot saved to {output_file}")
