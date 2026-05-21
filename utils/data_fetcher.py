import yfinance as yf

def get_price_data(ticker):

    df = yf.download(ticker, period="6mo", progress=False)

    return df