def check_fundamentals(stock):
    # Placeholder logic (replace with real data later)

    dummy_data = {
        "roe": 18,
        "revenue_growth": 12,
        "profit_growth": 11,
        "de_ratio": 0.5
    }

    if (
        dummy_data["roe"] > 15 and
        dummy_data["revenue_growth"] > 10 and
        dummy_data["profit_growth"] > 10 and
        dummy_data["de_ratio"] < 1
    ):
        return True

    return False