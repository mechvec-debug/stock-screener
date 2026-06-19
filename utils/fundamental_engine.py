def calculate_fundamental_score(row):

    score = 0

    if row.get("ROE", 0) > 12:
        score += 1

    if row.get("ROCE", 0) > 15:
        score += 1

    if row.get("DebtToEquity", 999) < 0.5:
        score += 1

    if row.get("PromoterHolding", 0) > 35:
        score += 1

    if row.get("SalesGrowth3Y", 0) > 8:
        score += 1

    if row.get("ProfitGrowth3Y", 0) > 8:
        score += 1

    if row.get("OperatingCashFlow", 0) > 0:
        score += 1

    return score
