from pymongo import MongoClient
from kiteconnect import KiteConnect
import pandas as pd

# MongoDB connection URI and details
mongo_uri = "mongodb://username:password@host:port/database"
db_name = "your_db_name"
collection_name = "your_collection_name"
document_id = "your_document_id"

# Function to fetch Zerodha credentials from MongoDB
def fetch_zerodha_credentials():
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]
    credentials_doc = collection.find_one({"_id": document_id})
    if credentials_doc:
        return credentials_doc['api_key'], credentials_doc['api_secret'], credentials_doc['request_token']
    else:
        raise Exception("Credentials not found in MongoDB")

# Function to authenticate with Zerodha and get access token
def authenticate(api_key, api_secret, request_token):
    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    kite.set_access_token(data["access_token"])
    return kite

# Function to dynamically fetch the instrument token
def fetch_instrument_token(kite, exchange, symbol_name):
    instruments = kite.instruments(exchange)
    for instrument in instruments:
        if instrument['tradingsymbol'] == symbol_name:
            return instrument['instrument_token']
    raise Exception(f"Instrument token for {symbol_name} not found")

# Function to fetch spot price
def fetch_spot_price(kite, instrument_token):
    ltp_data = kite.ltp(instrument_token)
    spot_price = ltp_data[instrument_token]['last_price']
    return spot_price

# Function to decide on call or put based on a simple moving average strategy
def decide_call_or_put_based_on_sma(kite, instrument_token):
    today = pd.Timestamp.now()
    from_date = (today - pd.Timedelta(days=30)).strftime('%Y-%m-%d')
    to_date = today.strftime('%Y-%m-%d')
    interval = 'day'
    historical_data = kite.historical_data(instrument_token, from_date, to_date, interval)
    df = pd.DataFrame(historical_data)
    sma_period = 14
    df['SMA'] = df['close'].rolling(sma_period).mean()
    last_close = df.iloc[-1]['close']
    last_sma = df.iloc[-1]['SMA']
    return 'CALL' if last_close > last_sma else 'PUT'

# Function to calculate potential exit price for a given profit target
def calculate_exit_price(entry_price, target_profit_percent, position_type):
    return entry_price * (1 + target_profit_percent / 100) if position_type == 'CALL' else entry_price * (1 - target_profit_percent / 100)

# Main execution
try:
    api_key, api_secret, request_token = fetch_zerodha_credentials()
    kite = authenticate(api_key, api_secret, request_token)

    nifty_token = fetch_instrument_token(kite, "NSE", "NIFTY 50")  # Update with exact Nifty symbol
    banknifty_token = fetch_instrument_token(kite, "NSE", "BANKNIFTY")  # Update with exact Banknifty symbol

    # Analysis for Nifty
    nifty_spot = fetch_spot_price(kite, nifty_token)
    position_type_nifty = decide_call_or_put_based_on_sma(kite, nifty_token)
    entry_price_nifty = nifty_spot
    target_profit_percent = 10
    exit_price_nifty = calculate_exit_price(entry_price_nifty, target_profit_percent, position_type_nifty)
    print(f"Nifty: Consider a {position_type_nifty} option. Entry Price: {entry_price_nifty}, Exit for {target_profit_percent}% profit at: {exit_price_nifty:.2f}")

    # Analysis for Banknifty
    banknifty_spot = fetch_spot_price(kite, banknifty_token)
    position_type_banknifty = decide_call_or_put_based_on_sma(kite, banknifty_token)
    entry_price_banknifty = banknifty_spot
    exit_price_banknifty = calculate_exit_price(entry_price_banknifty, target_profit_percent, position_type_banknifty)
    print(f"Banknifty: Consider a {position_type_banknifty} option. Entry Price: {entry_price_banknifty}, Exit for {target_profit_percent}% profit at: {exit_price_banknifty:.2f}")

except Exception as e:
    print(f"An error occurred: {e}")
