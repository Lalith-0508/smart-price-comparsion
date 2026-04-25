from flask import Flask, render_template, request
import sqlite3
import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect('database.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amazon_price INTEGER,
            flipkart_price INTEGER
        )
    ''')
    conn.close()

init_db()

# -------- FAKE DATA (SAFE FOR DEPLOYMENT) --------
def get_prices(product):
    import random
    return {
        "Amazon": random.randint(1000, 5000),
        "Flipkart": random.randint(1000, 5000)
    }

# -------- AI PREDICTION --------
def predict_price(product):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amazon_price FROM products WHERE name=?", (product,))
    data = cursor.fetchall()
    conn.close()

    prices = [row[0] for row in data if row[0] != 0]

    if len(prices) < 5:
        return None, "Not enough data"

    X = np.array(range(len(prices))).reshape(-1, 1)
    y = np.array(prices)

    poly = PolynomialFeatures(degree=2)
    model = LinearRegression()
    model.fit(poly.fit_transform(X), y)

    next_day = np.array([[len(prices)]])
    predicted = int(model.predict(poly.transform(next_day))[0])

    trend = "Stable"
    if len(prices) > 1:
        if prices[-1] > prices[-2]:
            trend = "Increasing 📈"
        elif prices[-1] < prices[-2]:
            trend = "Decreasing 📉"

    return predicted, trend

# -------- GRAPH --------
def generate_graph(product):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amazon_price FROM products WHERE name=?", (product,))
    data = cursor.fetchall()
    conn.close()

    prices = [row[0] for row in data if row[0] != 0]

    if len(prices) < 2:
        return None

    plt.figure()
    plt.plot(prices)
    plt.title("Price Trend")
    plt.savefig("static/graph.png")
    plt.close()

    return "graph.png"

# -------- ROUTES --------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    product = request.form['product']
    prices = get_prices(product)

    lowest_site = min(prices, key=prices.get)
    lowest_price = prices[lowest_site]

    conn = sqlite3.connect('database.db')
    conn.execute('''
        INSERT INTO products (name, amazon_price, flipkart_price)
        VALUES (?, ?, ?)
    ''', (product, prices["Amazon"], prices["Flipkart"]))
    conn.commit()
    conn.close()

    predicted_price, trend = predict_price(product)

    advice = "Not enough data"
    if predicted_price:
        advice = "Wait! Price may drop 📉" if predicted_price < lowest_price else "Buy now! Price may increase 📈"

    graph = generate_graph(product)

    return render_template('result.html',
                           product=product,
                           prices=prices,
                           lowest_site=lowest_site,
                           lowest_price=lowest_price,
                           predicted_price=predicted_price,
                           trend=trend,
                           advice=advice,
                           graph=graph)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
