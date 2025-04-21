#!/usr/bin/env python3

import csv
import json
import argparse
from datetime import datetime

def escape_js(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")

def parse_freq(val):
    val = val.strip().lower()
    if val.endswith("ghz"):
        return float(val[:-3].strip()) * 1000
    elif val.endswith("mhz"):
        return float(val[:-3].strip())
    else:
        return float(val)

def find_column(row, possible_names):
    for name in possible_names:
        if name in row:
            return row[name]
    raise KeyError(f"None of {possible_names} found in CSV headers")

def hex_to_rgba(hex_color, alpha=0.5):
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"

PALETTE = [
    "#440154", "#481567", "#482677", "#453781", "#404788",
    "#39568C", "#33638D", "#2D708E", "#287D8E", "#238A8D",
    "#1F968B", "#20A387", "#29AF7F", "#3CBB75", "#55C667",
    "#73D055", "#95D840", "#B8DE29", "#DCE319", "#FDE725"
]

# CLI
parser = argparse.ArgumentParser(description='Generate interactive plot from battery log')
parser.add_argument('-i', '--input', default='battery-log.csv', help='input CSV file')
args = parser.parse_args()

# Read and parse CSV
data = []
with open(args.input, "r") as f:
    reader = csv.DictReader(f, delimiter=";")
    for row in reader:
        try:
            entry = {"Time": row["Timestamp"]}
            entry["Processes"] = find_column(row, ["Most CPU intensive processes", "Top processes", "Processes"])
            for k, v in row.items():
                key = k.strip()
                try:
                    if "freq" in key.lower():
                        entry[key] = parse_freq(v)
                    else:
                        entry[key] = float(v.strip().replace("%", ""))
                except:
                    continue
            data.append(entry)
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            print(row)

# Enrich data
freqs = [d.get("CPU freq (MHz)", d.get("Freq", 0)) for d in data]
fmin, fmax = min(freqs), max(freqs)
label_points = []
prev_processes = None
for d in data:
    d["Time"] = datetime.strptime(d["Time"], "%Y-%m-%dT%H:%M:%S%z")
    d["HoverText"] = f"<b>{d['Time'].strftime('%Y-%m-%d %H:%M:%S')}</b><br>" + "<br>".join(
        f"<b>{k}:</b> {round(v, 2)}" for k, v in d.items() if isinstance(v, float)
    ) + "<br><b>Top-5:</b><br>" + d["Processes"].replace(", ", "<br>")
    freq = d.get("CPU freq (MHz)", d.get("Freq", fmin))
    idx = int((freq - fmin) / (fmax - fmin) * (len(PALETTE) - 1)) if fmax != fmin else len(PALETTE) // 2
    d["Color"] = PALETTE[max(0, min(idx, len(PALETTE) - 1))]
    d["HoverBG"] = hex_to_rgba(d["Color"], 0.5)
    if d["Processes"] != prev_processes:
        label_points.append(d)
    prev_processes = d["Processes"]

# Convert to JSON serializable dicts
for d in data:
    d["Time"] = d["Time"].isoformat()

rows_js = json.dumps(data)
rocket_js = json.dumps(PALETTE)
annotations = ",".join(
    (
        "{{x: \"{x}\", y: {y}, text: \"↙\", showarrow: false, "
        "xanchor: 'left', yanchor: 'bottom', font: {{color: 'darkgrey', size: 22, family: 'monospace'}}}}"
    ).format(x=d["Time"], y = next((v for k, v in d.items() if isinstance(v, float) and "battery" in k.lower()), 0))
    for d in label_points
)

html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>batlog viewer</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        html, body {{
            margin: 0; padding: 0; height: 100%; overflow: hidden;
            font-family: monospace;
        }}
        #plot {{ width: 100%; height: 100%; position: relative; }}
        #controls {{
            position: absolute;
            bottom: 110px;
            left: 90px;
            background: rgba(255,255,255,0.8);
            padding: 6px;
            z-index: 1000;
            font-size: 10px;
            font-family: monospace;
            border: 1px solid #ccc;
            max-width: 260px;
        }}
        #extraVar div.selected {{
            background-color: rgba(225,225,225,0.4);
            font-weight: bold;
        }}
        select {{
            font-family: monospace;
            margin-bottom: 4px;
        }}
        #toggle-btn {{
            border: 1px solid #ccc;
            background: rgba(255,255,255,0.8);
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div id="plot">
        <div id="controls">
            <div style="display: grid; row-gap: 4px; font-size: 10px; font-family: monospace;">
                <div style="display: grid; grid-template-columns: 1fr 2fr; column-gap: 8px;">
                    <label for="mainVar"><b>Variable:</b></label>
                    <select id="mainVar" style="width: 100%; font-size:10px;"></select>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 2fr; column-gap: 8px;">
                    <label for="colorVar"><b>Gradient:</b></label>
                    <select id="colorVar" style="width: 100%; font-size:10px;"></select>
                </div>
                <div style="display: grid; grid-template-columns: 2fr 1fr; column-gap: 30px;">
                    <div>
                        <label for="extraVar"><b>Show extra variables:</b></label>
                        <div id="extraVar"
                             style="border:0px solid #ccc; padding:4px; width:100%; height:auto; overflow-y:auto;">
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; justify-content: flex-start; height: 100%;">
                        <br>
                        <button id="toggle-btn" title="Toggle arrows"
                                style="font-size:10px; padding:2px 4px; width:100%;">
                            Toggle<br>top-5<br>processes<br>arrows
                        </button>
                    </div>
                </div>
            </div>
    </div>
    <script>
    const rawData = {rows_js};
    console.log("Loaded data rows:", rawData.length);
    console.log("First row:", rawData[0]);
    console.log("Available keys:", Object.keys(rawData[0]));

    const rocket = {rocket_js};
    function buildAnnotations() {{
        const result = [];
        let prev = null;
        for (let d of rawData) {{
            if (d.Processes !== prev) {{
                result.push({{
                    x: d.Time,
                    y: normalizeValue(d[mainVar], mainVar),
                    text: "↙",
                    showarrow: false,
                    xanchor: "left",
                    yanchor: "bottom",
                    font: {{ color: "darkgrey", size: 22, family: "monospace" }}
                }});
            }}
            prev = d.Processes;
        }}
        return result;
    }}

    const variables = Object.keys(rawData[0]).filter(k => typeof rawData[0][k] === "number");
    let mainVar = variables.includes("Battery level (%)") ? "Battery level (%)" : variables[0];
    let colorVar = variables.includes("CPU frequency") ? "CPU frequency" : variables[0];
    let extraVars = [];

    function getColor(val) {{
        const vals = rawData.map(d => d[colorVar]);
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        if (min === max) return rocket[Math.floor(rocket.length / 2)];
        const norm = (val - min) / (max - min);
        const idx = Math.floor(norm * (rocket.length - 1));
        return rocket[Math.max(0, Math.min(idx, rocket.length - 1))];
    }}

    function drawPlot() {{
        try {{
            console.log("Drawing plot...");
            console.log("Loaded data rows:", rawData.length);
            if (rawData.length > 0) {{
                console.log("First row:", rawData[0]);
            }} else {{
                console.warn("No data available in rawData.");
            }}
    
            const segs = [];
            for (let i = 1; i < rawData.length; i++) {{
                segs.push({{
                    x: [rawData[i-1].Time, rawData[i].Time],
                    y: [normalizeValue(rawData[i-1][mainVar], mainVar), normalizeValue(rawData[i][mainVar], mainVar)],
                    text: [rawData[i-1].HoverText, rawData[i].HoverText],
                    customdata: [rawData[i-1].HoverBG, rawData[i].HoverBG],
                    mode: 'lines',
                    line: {{
                        width: 3,
                        color: getColor(rawData[i-1][colorVar])
                    }},
                    hovertemplate: '%{{text}}<extra></extra>',
                    hoverinfo: 'skip',
                    showlegend: false
                }});
            }}
    
            const extra = extraVars.map(v => ({{
                x: rawData.map(d => d.Time),
                y: rawData.map(d => normalizeValue(d[v], v)),
                mode: 'lines',
                name: v,
                line: {{ width: 1 }}
            }}));
    
            const layout = {{
                title: null,
                font: {{ family: 'monospace' }},
                xaxis: {{ type: 'date', title: 'Time', tickangle: 45 }},
                yaxis: {{ title: displayLabel(mainVar) }},
                annotations: showAnnotations ? buildAnnotations() : [],
                hovermode: 'closest',
                margin: {{ l: 60, r: 30, b: 60, t: 60 }}
            }};
    
            Plotly.newPlot('plot', segs.concat(extra), layout, {{
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['hoverCompareCartesian', 'toggleHover']
            }});
        }} catch (e) {{
            console.error("Error during plot draw:", e);
        }}
    }}

        const plotDiv = document.getElementById("plot");
        plotDiv.addEventListener('plotly_hover', function(ev) {{
        const bg = ev.points[0].data.customdata?.[0];
        const tooltip = document.querySelector('.hoverlayer .hovertext');
        const rect = tooltip?.querySelector('rect');
        if (rect && bg) rect.setAttribute('fill', bg);
    }});

    function displayLabel(v) {{
        return v === "CPU frequency" ? "CPU frequency (/100 MHz)" : v;
    }}

    function normalizeValue(v, key) {{
        return key === "CPU frequency" ? v / 100 : v;
    }}

    function populateSelectors() {{
        let m = document.getElementById("mainVar");
        let c = document.getElementById("colorVar");
        const extraDiv = document.getElementById("extraVar");
    
        m.innerHTML = "";
        c.innerHTML = "";
        extraDiv.innerHTML = "";
    
        for (let v of variables) {{
            // Populate main and color variable selectors
            m.innerHTML += `<option value="${{v}}">${{displayLabel(v)}}</option>`;
            c.innerHTML += `<option value="${{v}}">${{displayLabel(v)}}</option>`;
    
            // Custom extras dropdown (click toggle, no Ctrl)
            const div = document.createElement("div");
            div.textContent = displayLabel(v);
            div.dataset.key = v;
            div.style.cursor = "pointer";
            div.style.userSelect = "none";
            div.onclick = () => {{
                div.classList.toggle("selected");
                extraVars = Array.from(extraDiv.querySelectorAll(".selected")).map(d => d.dataset.key);
                drawPlot();
            }};
            div.onmouseenter = () => div.style.background = "#eee";
            div.onmouseleave = () => div.style.background = "";
            extraDiv.appendChild(div);
        }}
    
        m.value = mainVar;
        c.value = colorVar;
        m.onchange = e => {{ mainVar = e.target.value; drawPlot(); }};
        c.onchange = e => {{ colorVar = e.target.value; drawPlot(); }};
    }}

    let showAnnotations = true;
    document.getElementById("toggle-btn").onclick = () => {{
        showAnnotations = !showAnnotations;
        drawPlot();
    }};

    populateSelectors();
    drawPlot();
    </script>
</body>
</html>
"""

output_file = args.input.replace('.csv', '.html')
with open(output_file, "w") as f:
    f.write(html_content)

print(f"Interactive plot saved to {output_file}")
