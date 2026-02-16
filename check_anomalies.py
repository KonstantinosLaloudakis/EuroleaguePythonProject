import json
import glob
import os

REPORT_FILE = "anomaly_report.txt"

def check_file(file_path, report_lines):
    """Check a single JSON file for anomalies."""
    report_lines.append(f"\n{'='*70}")
    report_lines.append(f"FILE: {os.path.basename(file_path)}")
    report_lines.append(f"{'='*70}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        report_lines.append("  ERROR: Data is not a list.")
        return
    
    report_lines.append(f"  Total entries: {len(data)}")
    
    # Determine key name
    sample = data[0] if data else {}
    name_key = 'Duo' if 'Duo' in sample else ('Lineup' if 'Lineup' in sample else 'Player')
    is_anchor = 'Player' in sample
    
    anomalies = []
    
    for entry in data:
        name = entry.get(name_key, 'Unknown')
        
        if is_anchor:
            # Anchor files have different structure
            on_min = entry.get('On_Minutes', 0)
            off_min = entry.get('Off_Minutes', 0)
            on_net = entry.get('On_NetRtg', 0)
            off_net = entry.get('Off_NetRtg', 0)
            diff = entry.get('Net_Diff', 0)
            
            if abs(diff) > 50 and on_min > 50:
                anomalies.append({
                    'name': name,
                    'type': 'EXTREME ANCHOR DIFF',
                    'detail': f"Diff={diff:.1f}, OnMin={on_min:.0f}, OffMin={off_min:.0f}, OnNet={on_net:.1f}, OffNet={off_net:.1f}"
                })
        else:
            minutes = entry.get('Minutes', 0)
            net_rtg = entry.get('NetRating', 0)
            off_rtg = entry.get('OffRating', 0)
            def_rtg = entry.get('DefRating', 0)
            pf = entry.get('PF', 0)
            pa = entry.get('PA', 0)
            
            # Rule 1: Extreme Net Rating (> ±60) with meaningful minutes
            if minutes > 30 and abs(net_rtg) > 60:
                anomalies.append({
                    'name': name,
                    'type': 'EXTREME NET RATING',
                    'detail': f"Net={net_rtg:.1f}, Min={minutes:.1f}, Off={off_rtg:.1f}, Def={def_rtg:.1f}"
                })
            
            # Rule 2: Impossible Offensive Rating (> 180 or < 30) with minutes
            if minutes > 20 and (off_rtg > 180 or off_rtg < 30):
                anomalies.append({
                    'name': name,
                    'type': 'IMPOSSIBLE OFF RATING',
                    'detail': f"Off={off_rtg:.1f}, Min={minutes:.1f}, PF={pf}"
                })
            
            # Rule 3: Impossible Defensive Rating (> 180 or < 30) with minutes
            if minutes > 20 and (def_rtg > 180 or def_rtg < 30):
                anomalies.append({
                    'name': name,
                    'type': 'IMPOSSIBLE DEF RATING',
                    'detail': f"Def={def_rtg:.1f}, Min={minutes:.1f}, PA={pa}"
                })
            
            # Rule 4: Ghost Check - known bad pairs
            if "KURUCS" in name and "SIMMONS" in name:
                anomalies.append({
                    'name': name,
                    'type': 'GHOST PAIR STILL PRESENT',
                    'detail': f"Net={net_rtg:.1f}, Min={minutes:.1f}"
                })
            
            # Rule 5: Suspiciously high minutes for 5-man (> 500 min)
            if '5man' in file_path and minutes > 500:
                anomalies.append({
                    'name': name,
                    'type': 'SUSPICIOUSLY HIGH MINUTES (5-man)',
                    'detail': f"Min={minutes:.1f}, Net={net_rtg:.1f}"
                })
            
            # Rule 6: Suspiciously high minutes for 2-man (> 800 min)
            if '2man' in file_path and minutes > 800:
                anomalies.append({
                    'name': name,
                    'type': 'SUSPICIOUSLY HIGH MINUTES (2-man)',
                    'detail': f"Min={minutes:.1f}, Net={net_rtg:.1f}"
                })
    
    if anomalies:
        report_lines.append(f"  ANOMALIES FOUND: {len(anomalies)}")
        for a in anomalies:
            report_lines.append(f"    [{a['type']}] {a['name']}")
            report_lines.append(f"      {a['detail']}")
    else:
        report_lines.append(f"  STATUS: CLEAN - No anomalies detected.")
    
    # Always show top 3 and bottom 3 by Net Rating for context
    if not is_anchor and data:
        sorted_data = sorted(data, key=lambda x: x.get('NetRating', 0))
        report_lines.append(f"\n  --- Bottom 3 Net Ratings ---")
        for entry in sorted_data[:3]:
            n = entry.get(name_key, '?')
            report_lines.append(f"    {n[:60]} | Net={entry.get('NetRating',0):.1f} | Min={entry.get('Minutes',0):.1f}")
        report_lines.append(f"  --- Top 3 Net Ratings ---")
        for entry in sorted_data[-3:]:
            n = entry.get(name_key, '?')
            report_lines.append(f"    {n[:60]} | Net={entry.get('NetRating',0):.1f} | Min={entry.get('Minutes',0):.1f}")


def main():
    report_lines = ["LINEUP ANOMALY REPORT", f"{'='*70}"]
    
    files = sorted(glob.glob("lineup_stats_*.json"))
    report_lines.append(f"Scanning {len(files)} files...\n")
    
    for f in files:
        try:
            check_file(f, report_lines)
        except Exception as e:
            report_lines.append(f"\n  ERROR processing {f}: {e}")
    
    report_lines.append(f"\n{'='*70}")
    report_lines.append("END OF REPORT")
    
    report = "\n".join(report_lines)
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report written to {REPORT_FILE}")
    print(report)

if __name__ == "__main__":
    main()
