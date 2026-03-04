"""
Possession State Flow — Sunburst Visualization
Replaces the Sankey diagram with a cleaner concentric-ring chart.
Inner ring = Start State | Outer ring = Outcome
"""

import json
import plotly.graph_objects as go
import sys

# Rich, saturated color palette on light background
START_COLORS = {
    'Defensive Rebound': '#3b82f6',   # Blue
    'After Made Basket': '#a855f7',   # Purple
    'Offensive Rebound': '#f97316',   # Orange
    'Live-Ball Steal': '#22c55e',     # Green
    'After Opponent TO': '#eab308',   # Yellow
    'Dead Ball': '#6b7280',           # Gray
}

OUTCOME_COLORS = {
    '2PT Make': '#16a34a',
    '3PT Make': '#4ade80',
    '2PT Miss': '#ef4444',
    '3PT Miss': '#f87171',
    'Turnover': '#f59e0b',
    'FT Make': '#3b82f6',
    'FT Miss': '#93c5fd',
}


def create_sunburst(team_code):
    with open('possession_flow.json', 'r') as f:
        all_data = json.load(f)

    if team_code not in all_data:
        print(f"Team {team_code} not found. Available: {list(all_data.keys())}")
        return

    data = all_data[team_code]
    total = data['total_possessions']
    s2m = data['start_to_middle']

    # Rebuild: Start -> Outcome directly (collapsing the middle layer)
    start_to_outcome = {}
    for key_sm, count_sm in s2m.items():
        start, middle = key_sm.split(' -> ')
        # Map middle+outcome from middle_to_outcome proportionally
        m2o = data['middle_to_outcome']
        middle_total = sum(v for k, v in m2o.items() if k.startswith(f"{middle} -> "))
        if middle_total == 0:
            continue
        for key_mo, count_mo in m2o.items():
            if key_mo.startswith(f"{middle} -> "):
                _, outcome = key_mo.split(' -> ')
                # Proportionally distribute
                proportion = count_sm * (count_mo / middle_total)
                combo = (start, outcome)
                start_to_outcome[combo] = start_to_outcome.get(combo, 0) + proportion

    # Build sunburst data
    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    text_info = []

    # Root node
    ids.append(team_code)
    labels.append(team_code)
    parents.append('')
    values.append(total)
    colors.append('#ffffff')
    text_info.append(f'{total} poss')

    # Start State nodes (inner ring)
    start_totals = {}
    for (start, outcome), count in start_to_outcome.items():
        start_totals[start] = start_totals.get(start, 0) + count

    for start, count in sorted(start_totals.items(), key=lambda x: -x[1]):
        node_id = f"{team_code}-{start}"
        ids.append(node_id)
        labels.append(start)
        parents.append(team_code)
        values.append(int(count))
        colors.append(START_COLORS.get(start, '#6b7280'))
        pct = count / total * 100
        text_info.append(f'{int(count)} ({pct:.0f}%)')

    # Outcome nodes (outer ring)
    for (start, outcome), count in sorted(start_to_outcome.items(), key=lambda x: -x[1]):
        if count < 5:  # Skip tiny slices
            continue
        node_id = f"{team_code}-{start}-{outcome}"
        parent_id = f"{team_code}-{start}"
        ids.append(node_id)
        labels.append(outcome)
        parents.append(parent_id)
        values.append(int(count))
        colors.append(OUTCOME_COLORS.get(outcome, '#9ca3af'))
        pct = count / start_totals.get(start, 1) * 100
        text_info.append(f'{int(count)} ({pct:.0f}%)')

    fig = go.Figure(go.Sunburst(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            line=dict(width=2, color='#ffffff'),
        ),
        branchvalues='total',
        textinfo='label+percent parent',
        hovertext=text_info,
        hoverinfo='text',
        insidetextorientation='radial',
        maxdepth=3,
    ))

    fig.update_layout(
        title=dict(
            text=(f"<b>Possession DNA — {team_code}</b><br>"
                  f"<span style='font-size:14px;color:#6b7280'>"
                  f"Euroleague 2025-26 | {total} Possessions<br>"
                  f"Inner Ring: How possession started | Outer Ring: How it ended</span>"),
            font=dict(size=22, color='#1f2937'),
            x=0.5,
        ),
        font=dict(size=13, color='#374151', family='Inter, Segoe UI, sans-serif'),
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        height=800,
        width=900,
        margin=dict(l=30, r=30, t=110, b=30),
    )

    # Add legend annotation
    legend_lines = []
    legend_lines.append("<b>START STATES (Inner Ring)</b>")
    for name, color in START_COLORS.items():
        if name in start_totals:
            pct = start_totals[name] / total * 100
            legend_lines.append(f"<span style='color:{color}'>●</span> {name}: {pct:.0f}%")

    fig.add_annotation(
        text="<br>".join(legend_lines),
        xref="paper", yref="paper",
        x=0.01, y=0.02,
        showarrow=False,
        font=dict(size=11, color='#374151'),
        align='left',
        bgcolor='rgba(249,250,251,0.9)',
        bordercolor='#e5e7eb',
        borderwidth=1,
        borderpad=8,
    )

    output_file = f'possession_dna_{team_code}.png'
    fig.write_image(output_file, scale=2)
    print(f"Saved to {output_file}")

    html_file = f'possession_dna_{team_code}.html'
    fig.write_html(html_file)
    print(f"Saved interactive to {html_file}")


if __name__ == '__main__':
    team = sys.argv[1] if len(sys.argv) > 1 else 'OLY'
    create_sunburst(team)
