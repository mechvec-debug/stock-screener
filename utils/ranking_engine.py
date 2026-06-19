def calculate_final_rank(row):

    return (

        row.get("TrendScore", 0) * 0.40

        +

        row.get("MomentumScore", 0) * 0.30

        +

        row.get("VolumeRatio", 0) * 15

        +

        row.get("FundamentalScore", 0) * 10

    )
