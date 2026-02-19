import json
from chart_utils import plot_diverging_bar_chart_with_logos

def visualize_standings():
    try:
        with open('oracle_predicted_standings.json', 'r') as f:
            data = json.load(f)

        # Sort by Delta descending
        data.sort(key=lambda x: x['Delta'], reverse=False)
        
        teams = [d['Team'] for d in data]
        deltas = [d['Delta'] for d in data]
        act_ws = [d['ActualW'] for d in data]
        pred_ws = [d['PredictedW'] for d in data]
        
        context_texts = [f"Act: {aw} | Pred: {pw}" for aw, pw in zip(act_ws, pred_ws)]
        
        plot_diverging_bar_chart_with_logos(
            title="ORACLE'S BLIND SPOTS",
            subtitle="Wins Above Expectation (Actual Wins vs Predicted Wins)",
            teams=teams,
            values=deltas,
            context_texts=context_texts,
            x_label="Win Differential (Actual - Predicted)",
            filename="oracle_predicted_standings.png"
        )
        
    except Exception as e:
        print(f"Error generating chart: {e}")

if __name__ == "__main__":
    visualize_standings()
