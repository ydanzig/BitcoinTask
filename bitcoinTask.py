import json
import time
import pytz
import logging
import requests
import emailCred
import numpy as np
import emailBodyGen
from email import encoders
from smtplib import SMTP_SSL
from datetime import datetime
import matplotlib.pyplot as plt
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Scanning parameters
TOTAL_RUN_TIME_MIN = 60  # Total runtime in minutes
SAMPLING_TIME_MIN = 1    # Sampling interval in minutes

# Define constants
LOG_FILE_NAME = "bitcoin_price_log.log"
JSON_FILE_NAME = "bitcoin_prices.json"
GRAPH_FILE_NAME = "bitcoin_price_graph.png"
TIMEZONE = "Asia/Jerusalem"  # Your local timezone
COINDESK_API = "https://api.coindesk.com/v1/bpi/currentprice.json"

# Logger definition
logging.basicConfig(filename=LOG_FILE_NAME,
                    level=logging.INFO,
                    format="%(asctime)s | %(levelname)-5s | %(funcName)-15s | %(message)s")
logger = logging.getLogger()

# Fetch Bitcoin price in USD and the corresponding ISO date from the given API URL.
# Args: url (str): API endpoint.
# Returns: dict with 'date'(ISO string) and 'price'(float), or None on error.
def fetch_bpi(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # Raises HTTPError for 4xx/5xx
        data = response.json()
        price = data["bpi"]["USD"]["rate_float"]
        date = data["time"]["updatedISO"] #date ISO format
        logger.info(f"Fetched Bitcoin price from API: price = {price}, USD, date = {date}")
        return {"date":date, "price":price}
    except Exception as e:
        logger.error(f"Error fetching Bitcoin price: {e}")
        return None, None

# Save data to a JSON file.
# Args - data (any): Data to save.
# file_name (str): File path to save the JSON.
# Returns: True on success, None on failure.
def save_to_json(data, file_name):
    try:
        with open(file_name, "w") as f:
            json.dump(data, f, default=str)
        logger.info(f"Data saved to {file_name}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to JSON file: {e}")
        return None

# Send an email using SMTP.
# Args:
#    msg (MIMEMultipart): The email message object.
#    email_user (str): Sender's email address.
#    email_app_pass (str): Sender's app-specific password.
#    recipient (str): Recipient's email address.
# Returns: True on success, None on failure.
def send_email(msg, email_user, email_app_pass, recipient):
    try:

        with SMTP_SSL("smtp.gmail.com", 465) as server:
            server.ehlo()
            server.login(email_user, email_app_pass)
            logger.info(f"connected to e-mail {email_user} server successfully")
            server.sendmail(email_user, recipient, msg.as_string())

        logger.info(f"Email sent successfully to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return None

# Convert UTC time to a specified time zone.
# Args:
#    utc_time_str (str): Time in ISO 8601 format (UTC).
#    target_timezone (str): Desired target time zone.
# Returns:
#    datetime: Converted local time or None on failure.
def convert_utc_to_timezone(utc_time_str, target_timezone):
    try:
        # Parse the ISO timestamp
        utc_time = datetime.fromisoformat(utc_time_str)
        # Convert UTC to the target time zone
        local_time = utc_time.astimezone(pytz.timezone(target_timezone))
        return local_time

    except Exception as e:
        logger.error(f"Failed to convert time: {e}")
        return None


# Collect Bitcoin price data at regular intervals.
# Args:
#    sleetInMin (int): Sampling interval in minutes.
#    runTimeMin (int): Total duration to collect data, in minutes.
#    target_timezone (str): Time zone for data conversion.
#    url (str): API endpoint to fetch price data.
# Returns:
#    list: List of dictionaries with 'time' (localized) and 'price'. None on failure.
def collect_data(sleet_in_min, run_time_min, target_timezone, url):
    try:
        data = []
        print(f"Collection data for {run_time_min} minutes...")
        logger.info(f"starting to collect data for {run_time_min} minutes. sampling every {sleet_in_min} minutes...")
        start_time = time.time()
        total_time = run_time_min * 60  # Total runtime in seconds

        while time.time() - start_time < total_time:
            time_passed = time.time() - start_time
            time_left = total_time - time_passed

            # Print the time remaining, overwriting the line
            print(f"\rTime remaining for scan: {time_left/60:,.2f} minutes", end="", flush=True)

            # Fetch and process data
            result = fetch_bpi(url)
            date, price = result["date"], result["price"]
            if price is not None:
                data.append({"time": convert_utc_to_timezone(date, target_timezone), "price": price})

            # Sleep before the next sample
            time.sleep(sleet_in_min * 60)

        print()
        print("Collection completed. Finalizing data...")
        logger.info(f"Finished collecting data for {run_time_min} minutes.")
        return data

    except Exception as e:
        logger.error(f"Failed collect data: {e}")
        return None


# Plot Bitcoin price data with optional mean, std, and price annotations.
# Args:
#    times (list): Timestamps of price samples.
#    prices (list): Bitcoin prices.
#    totalRunTimeMin (int): Duration of the data in minutes.
#    png_file_name (str): File name to save the graph.
#    writePriceValues (bool): Attach price values near all points.
#    addMeanStd (bool): Add mean and std lines to the graph.
# Returns:
#    Ture on printing success, None on failure.
def graph_plot(times, prices, total_run_time_min, png_file_name, write_price_values=False, add_mean_std=False):
    try:
        # change log level to disable unwanted matplotlib log messages
        plt.set_loglevel('WARNING')

        # Find the lowest and highest prices and their indices
        min_price = min(prices)
        max_price = max(prices)
        min_index = prices.index(min_price)
        max_index = prices.index(max_price)

        # other statistics calculations.
        mean_price = float(np.mean(prices))
        std_price = float(np.std(prices))

        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(times, prices, marker=".", linestyle="-", label="Bitcoin Price")

        # Highlight the minimum and maximum price
        plt.scatter(times[min_index], min_price, color="red", s=50,
                    label=f"Lowest: {min_price:,.2f}")  # color the minimum point
        plt.scatter(times[max_index], max_price, color="green", s=50,
                    label=f"Highest: {max_price:,.2f}")  # color the maximum point
        plt.text(times[min_index], min_price, f" {min_price:,.2f}", color="red",
                 fontsize=9)  # write text next to the point
        plt.text(times[max_index], max_price, f" {max_price:,.2f}", color="green",
                 fontsize=9)  # write text next to the point

        # Add price values near every point
        if write_price_values:
            pairs = zip(times, prices)
            for i in list(pairs):
                if i[1] not in (min_price, max_price):
                    plt.text(i[0], i[1], f"{i[1]:,.2f}", color="black", fontsize=9)

        # Add mean and standard deviation lines
        if add_mean_std:
            plt.axhline(y=mean_price, color="purple", linestyle="--", label=f"Mean: {mean_price:,.2f}")
            plt.axhline(y=mean_price + std_price, color="orange", linestyle="--",
                        label=f"Mean + Std: {mean_price + std_price:,.2f}")
            plt.axhline(y=mean_price - std_price, color="orange", linestyle="--",
                        label=f"Mean - Std: {mean_price - std_price:,.2f}")

        # Add labels and titles
        plt.title(f"Bitcoin Price Index (BPI) Over the Last {total_run_time_min} minutes")
        plt.xlabel("Time")
        plt.ylabel("Price (USD)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.grid()

        # Add legend
        plt.legend()

        # Save the graph as a file
        plt.savefig(png_file_name)
        logger.info(f"Graph generated and saved as {png_file_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to generate and save the graph: {e}")
        return None


# Main function
def main():
    #configuration parameters
    coin_desk_api =  COINDESK_API
    json_file_name = JSON_FILE_NAME
    graph_file_name = GRAPH_FILE_NAME
    timezone = TIMEZONE #your local timezone (effects json timing and graph x-axis)

    # scanning parameters:
    total_run_time_min = TOTAL_RUN_TIME_MIN
    sampling_time_min = SAMPLING_TIME_MIN

    # Collect data into a list.
    data = collect_data(run_time_min=total_run_time_min,
                        sleet_in_min=sampling_time_min,
                        target_timezone=timezone,
                        url=coin_desk_api)

    # Save collected data to a JSON file
    save_to_json(data, file_name=json_file_name)

    # Generate a graph of Bitcoin prices
    times = [entry["time"] for entry in data]
    prices = [entry["price"] for entry in data]
    graph_plot(times, prices, total_run_time_min, graph_file_name, add_mean_std=True)

    # create e-mail message.
    subject = "Bitcoin price analysis"
    body = emailBodyGen.get_email_body(total_run_time_min,times, prices)
    msg = MIMEMultipart()
    msg["From"] = emailCred.EMAIL_USER
    msg["To"] = emailCred.RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    # Add JSON and graph attachments to mail
    attachments = [json_file_name, graph_file_name]
    for attachment in attachments:
        try:
            with open(attachment, "rb") as file:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment.split('/')[-1]}",
                )
                msg.attach(part)
        except Exception as e:
            logger.error(f"Error attaching file {attachment}: {e}")

    # Send an email with the statistical details after scan
    send_email(msg, emailCred.EMAIL_USER, emailCred.EMAIL_APP_PASS, emailCred.RECIPIENT)

if __name__ == "__main__":
    main()