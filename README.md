# Nifty VWAP Strategy Trading Terminal

This is a web-based trading terminal that implements a simple VWAP (Volume Weighted Average Price) crossover strategy for Nifty futures. It connects to the Kite Connect API to fetch real-time data and account information.

**Disclaimer:** This is a proof-of-concept application for educational purposes. It is not intended for live trading without thorough testing and understanding of the risks involved.

## Features

-   **Web-based UI:** A clean and simple web interface to monitor the strategy and your account.
-   **Kite Connect Integration:** Connects to your Kite account to fetch your funds, holdings, positions, and orders.
-   **VWAP Crossover Strategy:** A simulated trading strategy based on the VWAP indicator.
-   **Real-time Updates:** The UI polls the backend periodically to display the latest market and account data.

## Requirements

-   Python 3.6+
-   pip

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Run the web application:
    ```bash
    python web_app.py
    ```

2.  Open your web browser and navigate to `http://127.0.0.1:8080`.

3.  You will be prompted to log in with your Kite API Key and API Secret.

4.  After entering your credentials, you will be redirected to the Kite login page to authorize the application.

5.  Once authorized, you will be redirected back to the trading terminal, where you can see your account details and the strategy status.
