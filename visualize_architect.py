"""
The Architect's Blueprint — Shot Creation Network Visualizer
Generates a network graph for a team showing Who Creates Shots For Whom.
Node size = Points scored from assists
Edge thickness = Volume of assists
Edge color = xFG% (Shot Quality created)
"""

import json
import math
import sys
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def generate_network(team_code):
    filename = f'shot_network_{team_code}.json'
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Data not found for {team_code}. Run shot_creation_network.py first.")
        return
        
    edges_data = data['edges']
    passer_stats = data['passer_stats']
    scorer_stats = data['scorer_stats']
    
    # 1. Identify valid nodes and calculate their sizes based on involvement
    players = set()
    node_weights = {} # rough proxy for how much they are involved
    
    # We want to filter out the noise and only show the meaningful core identity
    MIN_AST = 5 
    MAX_PLAYERS = 10
    
    for e in edges_data:
        if e['Assists'] < MIN_AST: continue 
        p, s = e['Passer'], e['Scorer']
        players.add(p)
        players.add(s)
        node_weights[p] = node_weights.get(p, 0) + e['Assists']
        node_weights[s] = node_weights.get(s, 0) + e['Assists']
        
    players = sorted(list(players), key=lambda x: -node_weights.get(x, 0))
    # Limit to top core players for a cleaner web
    if len(players) > MAX_PLAYERS:
        players = players[:MAX_PLAYERS]
        
    node_idx = {p: i for i, p in enumerate(players)}
    n = len(players)
    
    # Position nodes in a circle
    pos_x = []
    pos_y = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi/2  # start at top
        pos_x.append(math.cos(angle))
        pos_y.append(math.sin(angle))
        
    # Calculate color for an edge based on xFG%
    # xFG < 45 = Red, ~50-52 = Yellow/Gray, >55 = Green
    def get_color(xfg):
        if xfg >= 55: return f'rgba(34, 197, 94, 0.7)' # Green
        elif xfg >= 50: return f'rgba(234, 179, 8, 0.7)' # Yellow
        else: return f'rgba(239, 68, 68, 0.7)' # Red
        
    # 2. Pre-calculate Node Sizes and hover text so we can use them for arrow standoff
    node_sizes = []
    hover_texts = []
    for p in players:
        w = node_weights.get(p, 0)
        size = math.sqrt(w) * 6 + 10
        node_sizes.append(size)
        
        created = passer_stats.get(p, {}).get('total_assists', 0)
        xfg_c = passer_stats.get(p, {}).get('weighted_xfg', 0)
        received = scorer_stats.get(p, {}).get('total_assisted', 0)
        hover_texts.append(
            f"<b>{p}</b><br>Shot Creation: {created} AST ({xfg_c:.1f}% Avg xFG)<br>Shots Finished: {received} Assisted FGs"
        )
        
    fig = go.Figure()
    
    # 3. Draw Edges with actual arrows
    for e in edges_data:
        p = e['Passer']
        s = e['Scorer']
        if p not in node_idx or s not in node_idx:
            continue
        if e['Assists'] < MIN_AST: 
            continue
            
        idx_p = node_idx[p]
        idx_s = node_idx[s]
        
        x0, y0 = pos_x[idx_p], pos_y[idx_p]
        x1, y1 = pos_x[idx_s], pos_y[idx_s]
        
        mx, my = (x0+x1)/2, (y0+y1)/2
        dx, dy = x1-x0, y1-y0
        norm = math.sqrt(dx**2 + dy**2)
        if norm > 0:
            nx, ny = -dy/norm, dx/norm
            # bend offset
            offset = 0.1
            cx, cy = mx + nx*offset, my + ny*offset
        else:
            cx, cy = mx, my
            
        edge_x = [x0, cx, x1]
        edge_y = [y0, cy, y1]
        
        width = min(max(e['Assists'] / 2, 1), 15)
        color = get_color(e['AvgXFG'])
        
        hover_text = f"<b>{p} &rarr; {s}</b><br>Assists: {e['Assists']}<br>Quality (xFG%): {e['AvgXFG']}%<br>2PTs: {e['TwoPT']} | 3PTs: {e['ThreePT']}"
        
        # Transparent invisible line for hover
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=width*2, color='rgba(0,0,0,0)', shape='spline'),
            mode='lines',
            hoverinfo='text',
            text=hover_text,
            showlegend=False
        ))
        
        # Draw the actual directed arrow with annotation so it points perfectly
        fig.add_annotation(
            x=x1, y=y1,
            ax=cx, ay=cy,
            axref='x', ayref='y',
            xref='x', yref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=0.8,  # Reduced from 1.5
            arrowwidth=min(width, 4),  # Cap arrowhead width so high-volume lines don't have massive arrows
            arrowcolor=color,
            standoff=node_sizes[idx_s] / 2 + 1,
            startstandoff=0
        )
        
        # Draw the first half of the line using standard smooth spline
        fig.add_trace(go.Scatter(
            x=[x0, cx], y=[y0, cy],
            line=dict(width=width, color=color, shape='spline', smoothing=1.3),
            mode='lines',
            hoverinfo='skip',
            showlegend=False,
            opacity=0.8
        ))

    # 4. Draw Nodes
    fig.add_trace(go.Scatter(
        x=pos_x, y=pos_y,
        mode='markers+text',
        text=[p.split(',')[0].title() for p in players], # Just last name
        textposition='top center',
        marker=dict(
            size=node_sizes,
            color='#ffffff',
            line=dict(color='#111827', width=3),
        ),
        hoverinfo='text',
        textfont=dict(size=14, color='#111827', family='Inter, sans-serif'),
        hovertext=hover_texts,
        showlegend=False
    ))
    
    # 4. Layout formatting
    fig.update_layout(
        title=dict(
            text=f"<b>The Architect's Blueprint — {team_code}</b><br>"
                 f"<span style='font-size:14px;color:#4b5563'>"
                 f"Shot Creation Network | Connecting Passer to Scorer | Edges colored by Expected FG% (Shot Quality)</span>",
            font=dict(size=22, color='#111827'),
            x=0.5,
        ),
        paper_bgcolor='#f9fafb',
        plot_bgcolor='#f9fafb',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=800,
        width=1000,
        margin=dict(l=40, r=40, t=100, b=40),
    )
    
    # Annotations for legend
    legend_html = (
        "<b>Edge Color = Shot Quality (xFG%)</b><br>"
        "<span style='color:#22c55e'>&#9679;</span> Green: Elite Looks (>55%)<br>"
        "<span style='color:#eab308'>&#9679;</span> Yellow: Avg Looks (50-55%)<br>"
        "<span style='color:#ef4444'>&#9679;</span> Red: Tough Looks (<50%)<br><br>"
        "<b>Edge Thickness</b> = Volume of Assists"
    )
    fig.add_annotation(
        x=1.1, y=1.0, xref="paper", yref="paper",
        text=legend_html,
        showarrow=False, align="left",
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#d1d5db", borderwidth=1, borderpad=10
    )
    
    out_png = f'architect_network_{team_code}.png'
    fig.write_image(out_png, scale=2)
    print(f"Saved PNG to {out_png}")
    
    out_html = f'architect_network_{team_code}.html'
    fig.write_html(out_html)
    print(f"Saved HTML to {out_html}")

if __name__ == '__main__':
    tgt = sys.argv[1] if len(sys.argv) > 1 else 'ALL'
    if tgt == 'ALL':
        teams = ['OLY', 'PAM', 'PAN', 'MAD', 'MCO', 'MUN', 'BAR', 'ZAL', 'TEL']
        for t in teams:
            generate_network(t)
    else:
        generate_network(tgt)
