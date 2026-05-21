from data.stock_list import NIFTY_50
from utils.signal_generator import generate_signals, format_signals
from utils.notifier import send_telegram

df, phase = generate_signals(NIFTY_50)

message = format_signals(df, phase)

print(message)

send_telegram(message)