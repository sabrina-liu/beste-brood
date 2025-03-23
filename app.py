from flask import Flask, render_template, request, jsonify
import pandas as pd
import random
import unicodedata
import os

app = Flask(__name__)

# Load data
if os.path.exists("results.csv"):
    df = pd.read_csv("results.csv")
else:
    df = pd.read_excel("static/beste_brood_ah.xlsx")
    df['id'] = range(1, len(df) + 1)
    df['rating'] = 1500
    df['matches'] = 0
    df['wins'] = 0

    def slugify(name):
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ascii', 'ignore').decode('ascii')
        name = name.lower().replace("'", "")
        name = ''.join(c if c.isalnum() else '_' for c in name)
        return 'ah_' + name.strip('_') + '.jpg'

    df['filename'] = df['Naam'].apply(slugify)

df['matches'] = 0
df['wins'] = 0

products = df.to_dict(orient='records')

# --- Helper functions ---
def get_two_random_products():
    return random.sample(products, 2)

def update_elo(winner, loser, k=32):
    expected_win = 1 / (1 + 10 ** ((loser['rating'] - winner['rating']) / 400))
    expected_loss = 1 / (1 + 10 ** ((winner['rating'] - loser['rating']) / 400))
    winner['rating'] += k * (1 - expected_win)
    loser['rating'] += k * (0 - expected_loss)

@app.route('/')
def index():
    p1, p2 = get_two_random_products()
    return render_template('index.html', product1=p1, product2=p2)

@app.route('/vote', methods=['POST'])
def vote():
    winner_id = int(request.form['winner_id'])
    loser_id = int(request.form['loser_id'])

    winner = next((p for p in products if p['id'] == winner_id), None)
    loser = next((p for p in products if p['id'] == loser_id), None)

    if not winner or not loser:
        return jsonify({"error": "Invalid product IDs"}), 400

    update_elo(winner, loser)
    winner['matches'] += 1
    winner['wins'] += 1
    loser['matches'] += 1

    # 🔐 Save to CSV
    pd.DataFrame(products).to_csv("results.csv", index=False)

    new1, new2 = get_two_random_products()

    def clean(p):
        return {
            "id": int(p["id"]),
            "filename": str(p["filename"]),
            "Naam": str(p["Naam"]),
            "Prijs": float(p["Prijs"])
        }

    return jsonify({
        "product1": clean(new1),
        "product2": clean(new2)
    })


@app.route('/leaderboard')
def leaderboard():
    MIN_MATCHES = 3
    C = 5  # confidence weight
    M = 1500  # average rating baseline

    def bayesian(p):
        return ((C * M) + (p['rating'] * p['matches'])) / (C + p['matches']) if p['matches'] > 0 else 0

    ranked = sorted(
        [p for p in products if p['matches'] >= MIN_MATCHES],
        key=lambda p: bayesian(p),
        reverse=True
    )

    return render_template('leaderboard.html', products=ranked)

if __name__ == '__main__':
    app.run(debug=True)
