"""
Possession State Flow — Sankey Diagram Visualizer
Renders a Sankey diagram showing how a team's possessions flow from
Start State -> Play Type -> Outcome.
"""

import json
import plotly.graph_objects as go
import sys

# Color scheme
COLORS = {
    # Start nodes (left)
    'Defensive Rebound': 'rgba(88, 166, 255, 0.7)',
    'Live-Ball Steal': 'rgba(57, 211, 83, 0.7)',
    'After Made Basket': 'rgba(210, 168, 255, 0.7)',
    'Dead Ball': 'rgba(139, 148, 158, 0.7)',
    'Offensive Rebound': 'rgba(255, 166, 87, 0.7)',
    'After Opponent TO': 'rgba(255, 218, 68, 0.7)',
    # Middle nodes
    'Assisted': 'rgba(57, 211, 83, 0.6)',
    'Unassisted': 'rgba(210, 168, 255, 0.6)',
    'Contested': 'rgba(248, 81, 73, 0.5)',
    'Ball Handling': 'rgba(255, 166, 87, 0.5)',
    'Drawn Foul': 'rgba(88, 166, 255, 0.5)',
    # Outcome nodes (right)
    '2PT Make': 'rgba(57, 211, 83, 0.8)',
    '3PT Make': 'rgba(39, 233, 115, 0.8)',
    '2PT Miss': 'rgba(248, 81, 73, 0.6)',
    '3PT Miss': 'rgba(220, 60, 60, 0.6)',
    'Turnover': 'rgba(255, 100, 50, 0.7)',
    'FT Make': 'rgba(88, 166, 255, 0.7)',
    'FT Miss': 'rgba(180, 100, 100, 0.5)',
}

LINK_COLORS = {
    '2PT Make': 'rgba(57, 211, 83, 0.25)',
    '3PT Make': 'rgba(39, 233, 115, 0.25)',
    '2PT Miss': 'rgba(248, 81, 73, 0.15)',
    '3PT Miss': 'rgba(220, 60, 60, 0.15)',
    'Turnover': 'rgba(255, 100, 50, 0.2)',
    'FT Make': 'rgba(88, 166, 255, 0.2)',
    'FT Miss': 'rgba(180, 100, 100, 0.15)',
    'Assisted': 'rgba(57, 211, 83, 0.2)',
    'Unassisted': 'rgba(210, 168, 255, 0.2)',
    'Contested': 'rgba(248, 81, 73, 0.15)',
    'Ball Handling': 'rgba(255, 166, 87, 0.15)',
    'Drawn Foul': 'rgba(88, 166, 255, 0.15)',
}


def create_sankey(team_code):
    with open('possession_flow.json', 'r') as f:
        all_data = json.load(f)
        
    if team_code not in all_data:
        print(f"Team {team_code} not found. Available: {list(all_data.keys())}")
        return
        
    data = all_data[team_code]
    total = data['total_possessions']
    s2m = data['start_to_middle']
    m2o = data['middle_to_outcome']
    
    # Collect all unique node names (in order: Start -> Middle -> Outcome)
    start_nodes = set()
    middle_nodes = set()
    outcome_nodes = set()
    
    for key in s2m:
        s, m = key.split(' -> ')
        start_nodes.add(s)
        middle_nodes.add(m)
    for key in m2o:
        m, o = key.split(' -> ')
        middle_nodes.add(m)
        outcome_nodes.add(o)
        
    # Order nodes: Start | Middle | Outcome
    start_list = sorted(start_nodes)
    middle_list = sorted(middle_nodes)
    outcome_list = sorted(outcome_nodes)
    
    all_nodes = start_list + middle_list + outcome_list
    node_idx = {n: i for i, n in enumerate(all_nodes)}
    
    # Build links
    sources = []
    targets = []
    values = []
    link_colors = []
    
    # Start -> Middle links
    for key, val in s2m.items():
        s, m = key.split(' -> ')
        sources.append(node_idx[s])
        targets.append(node_idx[m])
        values.append(val)
        link_colors.append(LINK_COLORS.get(m, 'rgba(150,150,150,0.15)'))
        
    # Middle -> Outcome links
    for key, val in m2o.items():
        m, o = key.split(' -> ')
        sources.append(node_idx[m])
        targets.append(node_idx[o])
        values.append(val)
        link_colors.append(LINK_COLORS.get(o, 'rgba(150,150,150,0.15)'))
    
    # Node colors
    node_colors = []
    for n in all_nodes:
        node_colors.append(COLORS.get(n, 'rgba(139, 148, 158, 0.6)'))
    
    # Create figure
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color='rgba(30, 40, 50, 0.8)', width=1),
            label=[f"{n}\n({sum(v for s,t,v in zip(sources,targets,values) if t==node_idx[n] or s==node_idx[n])//2})" 
                   if n in middle_nodes else n for n in all_nodes],
            color=node_colors,
            hovertemplate='%{label}<extra></extra>',
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate='%{source.label} → %{target.label}: %{value} possessions<extra></extra>',
        )
    )])
    
    fig.update_layout(
        title=dict(
            text=f"Possession State Flow — {team_code} (Euroleague 2025-26)<br>"
                 f"<span style='font-size:14px;color:#8b949e'>{total} Total Possessions | "
                 f"Start State → Play Type → Outcome</span>",
            font=dict(size=20, color='#e6edf3'),
            x=0.5,
        ),
        font=dict(size=12, color='#e6edf3'),
        paper_bgcolor='#0d1117',
        plot_bgcolor='#0d1117',
        height=700,
        width=1200,
        margin=dict(l=20, r=20, t=80, b=40),
    )
    
    output_file = f'sankey_{team_code}.png'
    fig.write_image(output_file, scale=2)
    print(f"Saved Sankey diagram to {output_file}")
    
    # Also save interactive HTML
    html_file = f'sankey_{team_code}.html'
    fig.write_html(html_file)
    print(f"Saved interactive HTML to {html_file}")


if __name__ == '__main__':
    team = sys.argv[1] if len(sys.argv) > 1 else 'OLY'
    create_sankey(team)
