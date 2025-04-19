#!/usr/bin/env python3
import csv
import argparse
from datetime import datetime

def escape_js(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

def find_column(row, possible_names):
    for name in possible_names:
        if name in row:
            return row[name]
    raise KeyError(f"None of {possible_names} found in CSV headers")

def parse_freq(val):
    val = val.strip().lower()
    if val.endswith("ghz"):
        return float(val[:-3].strip()) * 1000
    elif val.endswith("mhz"):
        return float(val[:-3].strip())
    else:
        return float(val)

def hex_to_rgba(hex_color, alpha=0.5):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

# Full rocket-like palette (25-step), with brightest end removed
ROCKET_HEX = [
    "#03051A", "#100C3F", "#211151", "#351556", "#491857",
    "#5E1956", "#741A51", "#8A1B49", "#9F1F3E", "#B52831",
    "#C93728", "#DA481F", "#E75B16", "#F26F14", "#F7831A",
    "#F8972D", "#F8AA46", "#F6BC61", "#F2CD7E", "#EDD099"
]

def map_freq_to_color(freq, fmin, fmax):
    if fmax == fmin:
        return ROCKET_HEX[len(ROCKET_HEX) // 2]
    norm = (freq - fmin) / (fmax - fmin)
    idx = int(norm * (len(ROCKET_HEX) - 1))
    return ROCKET_HEX[max(0, min(idx, len(ROCKET_HEX) - 1))]

# CLI
parser = argparse.ArgumentParser(description='Generate battery level plot')
parser.add_argument('-i', '--input', default='battery-log.csv', help='Input CSV file path')
args = parser.parse_args()

# Read CSV
data = []
with open(args.input, "r") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        try:
            data.append({
                "Time": row["Timestamp"],
                "Battery": float(find_column(row, ["Battery level (%)", "Battery level", "Battery"])),
                "Processes": find_column(row, ["Most CPU intensive processes", "Top processes", "Processes"]),
                "Freq": parse_freq(find_column(row, ["CPU freq (MHz)", "CPU frequency", "Frequency"]))
            })
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            print(row)

# Enrich
freqs = [d["Freq"] for d in data]
fmin, fmax = min(freqs), max(freqs)
label_points = []
prev_processes = None
for i, d in enumerate(data):
    d["Time"] = datetime.strptime(d["Time"], "%Y-%m-%dT%H:%M:%S%z")
    d["TimeDisplay"] = d["Time"].strftime("%H:%M:%S")
    processes = d['Processes'].replace(", ", "<br>")
    d["HoverText"] = f"<b>{d['TimeDisplay']}</b><br><b>Battery:</b> {d['Battery']}%<br><b>CPU:</b> {d['Freq']} MHz<br><b>Top-5:</b><br>{processes}"
    hex_col = map_freq_to_color(d["Freq"], fmin, fmax)
    d["Color"] = hex_col
    d["HoverBG"] = hex_to_rgba(hex_col, 0.5)
    if i == 0 or d["Processes"] != prev_processes:
        label_points.append(d)
    prev_processes = d["Processes"]

# JS data
time_data = ",".join(f'"{d["Time"].isoformat()}"' for d in data)
battery_data = ",".join(str(d["Battery"]) for d in data)
hover_texts = ",".join(f'"{escape_js(d["HoverText"])}"' for d in data)
colors = ",".join(f'"{d["Color"]}"' for d in data[:-1])
hover_bgcolors = ",".join(f'"{d["HoverBG"]}"' for d in data[:-1])
annotations = ",".join(
    (
        "{{x: \"{x}\", y: {y}, text: \"↙\", showarrow: false, "
        "xanchor: 'left', yanchor: 'bottom', font: {{color: 'darkgrey', size: 22, family: 'monospace'}}}}"
    ).format(x=d["Time"].isoformat(), y=d["Battery"])
    for d in label_points
)

# HTML output
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>charge-control battery log</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            height: 100%;
            overflow: hidden;
            font-family: monospace;
        }}
        #plot {{
            width: 100%;
            height: 100%;
            position: relative;
        }}
        #toggle-btn {{
            position: absolute;
            left: 90px;
            bottom: 90px;
            background: rgba(255,255,255,0.5);
            border: 1px solid #ccc;
            padding: 5px 10px;
            font-size: 10px;
            border-radius: 4px;
            cursor: pointer;
            z-index: 1000;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div id="plot">
        <div id="toggle-btn">Toggle top-5 change markers</div>
    </div>

    <script>
        const data = {{
            time: [{time_data}],
            battery: [{battery_data}],
            hoverTexts: [{hover_texts}],
            colors: [{colors}],
            customdata: [{hover_bgcolors}]
        }};

        const segments = [];
        for (let i = 1; i < data.time.length; i++) {{
            segments.push({{
                x: [data.time[i - 1], data.time[i]],
                y: [data.battery[i - 1], data.battery[i]],
                text: [data.hoverTexts[i - 1], data.hoverTexts[i]],
                customdata: [data.customdata[i - 1], data.customdata[i]],
                mode: 'lines',
                line: {{
                    width: 3,
                    color: data.colors[i - 1]
                }},
                hovertemplate: '%{{text}}<extra></extra>',
                hoverinfo: 'skip',
                showlegend: false
            }});
        }}

        let showAnnotations = true;

        const layout = {{
            title: 'Battery percentage and top-5 processes over time',
            font: {{ family: 'monospace' }},
            xaxis: {{
                title: 'Time',
                tickangle: 45,
                type: 'date',
                showspikes: true,
                spikemode: 'across',
                spikesnap: 'data',
                spikethickness: 1
            }},
            yaxis: {{
                title: 'Battery level (%)',
                range: [0, 100],
                dtick: 10,
                showspikes: true,
                spikemode: 'across',
                spikesnap: 'data',
                spikethickness: 1
            }},
            hovermode: 'closest',
            hoverlabel: {{
                align: 'left',
                font: {{ family: 'monospace', size: 11 }},
                namelength: 0
            }},
            margin: {{
                l: 60,
                r: 30,
                b: 60,
                t: 60
            }},
            annotations: [{annotations}]
        }};

        const config = {{
            displayModeBar: true,
            modeBarButtonsToRemove: ['hoverCompareCartesian', 'toggleHover'],
            displaylogo: false
        }};

        Plotly.newPlot('plot', segments, layout, config);

        // Tooltip background with previous segment color (50% alpha)
        document.getElementById('plot').on('plotly_hover', function(eventData) {{
            const bg = eventData.points[0].data.customdata?.[0];
            const tooltip = document.querySelector('.hoverlayer .hovertext');
            const rect = tooltip?.querySelector('rect');
            if (rect && bg) {{
                rect.setAttribute('fill', bg);
            }}
        }});

        // Toggle annotations
        document.getElementById("toggle-btn").addEventListener("click", () => {{
            showAnnotations = !showAnnotations;
            Plotly.relayout('plot', {{
                annotations: showAnnotations ? [{annotations}] : []
            }});
        }});
    </script>
</body>
</html>
"""

output_file = args.input.replace('.csv', '.html')
with open(output_file, "w") as f:
    f.write(html_content)

print(f"Interactive plot saved to {output_file}")
