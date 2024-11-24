# Generate HTML email body with Bitcoin price analysis.
# This function calculates and formats the maximum, minimum, mean price,
# standard deviation, and time of occurrence for each, then generates an HTML table.
# Arguments:
#    totalRunTimeMin (int): Total runtime in minutes for analysis.
#    times (list): List of timestamps when prices were recorded.
#    prices (list): List of Bitcoin prices recorded during the period.
# Returns:
#    str: HTML formatted email body with price analysis summary.
def get_email_body(total_run_time_min, times, prices):
    import numpy as np

    # calculations for e-mail summary
    max_price, min_price = max(prices), min(prices)
    max_time, min_time = times[prices.index(max_price)], times[prices.index(min_price)]
    mean_price = np.mean(prices)
    std_price = np.std(prices)

    return f"""
    <html>
    <body>
        <p>Bitcoin price analysis for the last {total_run_time_min} minutes:</p>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Maximum Price</td><td>{round(max_price, 2):,} USD</td></tr>
            <tr><td>Time of Max Price</td><td>{max_time}</td></tr>
            <tr><td>Minimum Price</td><td>{round(min_price, 2):,} USD</td></tr>
            <tr><td>Time of Min Price</td><td>{min_time}</td></tr>
            <tr><td>Mean Price</td><td>{round(mean_price, 2):,} USD</td></tr>
            <tr><td>Standard Deviation</td><td>{round(std_price, 2):,} USD</td></tr>
            <tr><td>Price Variability (Mean ± Std)</td><td>{round(mean_price - std_price, 2):,} - {round(mean_price + std_price, 2):,} USD</td></tr>
        </table>
    </body>
    </html>
    """