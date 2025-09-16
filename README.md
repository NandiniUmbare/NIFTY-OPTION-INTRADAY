# Trading Terminal Application

This is a Flask-based web application for executing automated trading strategies. It is designed to use Alice Blue for market data and Kite for order execution.

## Features

- **Dual Broker Integration:** Uses Alice Blue for data feeds and Kite for order placement and portfolio management.
- **Strategy 2 (AVWAP Breakout):** An automated trading strategy that:
    - Selects stocks daily based on market sentiment and liquidity.
    - Executes trades on a 5-minute timeframe using an Anchored VWAP breakout system.
- **Web Interface:** A simple UI to monitor account status, positions, and strategy performance.

## Setup and Configuration

**1. Install Dependencies:**

Install the required Python packages using pip:
```bash
pip install -r requirements.txt
```

**2. Configure Credentials:**

Before running the application, you **must** add your API credentials to the `config.ini` file.

- Open the `config.ini` file in a text editor.
- Fill in your details for both `[KITE]` and `[ALICEBLUE]` sections.

```ini
[KITE]
api_key = YOUR_KITE_API_KEY
api_secret = YOUR_KITE_API_SECRET

[ALICEBLUE]
user_id = YOUR_ALICEBLUE_USER_ID
api_key = YOUR_ALICEBLUE_API_KEY

[strategy2]
LIQUIDITY_THRESHOLD = 10000000
CAPITAL_PER_TRADE = 10000
DAILY_STOP_LOSS = -3000
```

**3. Run the Application:**

Start the Flask web server by running:
```bash
python web_app.py
```
The application will be available at `http://127.0.0.1:8080`.

## Daily Login Procedure

For the application to work, you must authorize the API connections once per day for each broker:

1.  **Alice Blue:** Log in to the [Alice Blue web terminal](https://ant.aliceblueonline.com/) at least once.
2.  **Kite:**
    - Navigate to the application's login page in your browser.
    - Click the "Login with Kite" button.
    - This will redirect you to the Kite login page. Enter your Kite credentials to authorize the application.

After these steps, the application will be fully connected and the strategies will run as scheduled.
