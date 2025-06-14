# std libraries
import asyncio
import sqlite3
import logging
import re
import tomllib
import random
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple

# 3rd party libraries
import httpx
from selectolax.parser import HTMLParser
from tqdm.asyncio import tqdm

# --- Configuration Loading ---

def load_config(path: str = "config.toml") -> Dict[str, Any]:
    """
    Loads and validates the configuration from a TOML file.

    This function reads the specified TOML file and returns it as a dictionary.
    It includes error handling for a missing file or malformed TOML content.

    Args:
        path (str): The path to the configuration file. Defaults to "config.toml".

    Returns:
        Dict[str, Any]: A dictionary containing the application configuration.

    Raises:
        FileNotFoundError: If the config file cannot be found at the specified path.
        tomllib.TOMLDecodeError: If the file is not valid TOML.
    """
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        logging.error(f"Configuration file not found at {path}. Please ensure it exists.")
        raise
    except tomllib.TOMLDecodeError as e:
        logging.error(f"Error decoding TOML file '{path}': {e}")
        raise

# --- Logging Setup ---

def setup_logging(log_path: str) -> None:
    """
    Sets up structured, rotating logging for the application.

    This configures logging to output messages at the INFO level and above to a
    rotating log file. A separate handler for the console is set to WARNING
    level to avoid cluttering the terminal progress bars.

    Args:
        log_path (str): The path to the log file.
    """
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler for detailed logging
    log_handler = RotatingFileHandler(log_path, maxBytes=10*1024*1024, backupCount=5)
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(logging.INFO)

    # Console handler for important messages (errors, warnings)
    # This prevents INFO messages from interfering with the tqdm progress bars
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.WARNING)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set root to INFO to capture everything
    root_logger.addHandler(log_handler)
    root_logger.addHandler(stream_handler)


# --- Database Operations ---

def init_db(db_path: str) -> sqlite3.Connection:
    """
    Initializes the SQLite database and creates tables and indexes if they don't exist.

    This function establishes a connection to the SQLite database file. It then
    ensures that two tables, `properties` and `html_blobs`, are created.
    It also adds indexes on `postcode` and `sale_date` to improve query performance.

    Args:
        db_path (str): The path to the SQLite database file.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create properties table for structured data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_type TEXT,
        sale_date TEXT,
        price INTEGER,
        address TEXT,
        postcode INTEGER,
        bedrooms INTEGER,
        baths INTEGER,
        parking INTEGER,
        area INTEGER,
        sales_page_url TEXT UNIQUE
    )
    """)

    # Create html_blobs table for raw HTML content
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS html_blobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sales_page_url TEXT UNIQUE,
        html_content TEXT,
        FOREIGN KEY (sales_page_url) REFERENCES properties (sales_page_url)
    )
    """)

    # Add indexes to speed up common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_postcode ON properties (postcode)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sale_date ON properties (sale_date)")

    conn.commit()
    return conn

def insert_data(conn: sqlite3.Connection, property_data: Dict[str, Any], html_content: str) -> None:
    """
    Inserts a single property's data and its raw HTML into the database.

    This function uses a transaction to insert the parsed property data into the `properties`
    table and the corresponding raw HTML into the `html_blobs` table.
    The `UNIQUE` constraint on `sales_page_url` prevents duplicate entries. If an
    IntegrityError occurs (indicating a duplicate), it's logged and skipped.

    Args:
        conn (sqlite3.Connection): The database connection object.
        property_data (Dict[str, Any]): A dictionary of the parsed property data.
        html_content (str): The raw HTML string of the property's sales page.
    """
    cursor = conn.cursor()
    try:
        # Insert parsed data into the main properties table
        cursor.execute("""
            INSERT INTO properties (sale_type, sale_date, price, address, postcode, bedrooms, baths, parking, area, sales_page_url)
            VALUES (:sale_type, :sale_date, :price, :address, :postcode, :bedrooms, :baths, :parking, :area, :sales_page_href)
        """, property_data)

        # Insert the raw HTML blob, linking it via the unique URL
        cursor.execute("""
            INSERT INTO html_blobs (sales_page_url, html_content)
            VALUES (?, ?)
        """, (property_data.get('sales_page_href'), html_content))

        conn.commit()
        logging.info(f"Successfully inserted: {property_data.get('sales_page_href')}")
    except sqlite3.IntegrityError:
        # This is expected if we re-run the scraper; it means the property is already in the DB.
        logging.warning(f"Record already exists, skipping: {property_data.get('sales_page_href')}")
    except Exception as e:
        # Catch any other potential database errors
        logging.error(f"Database error inserting {property_data.get('sales_page_href')}: {e}")
        conn.rollback()

# --- HTML Parsing ---

def parse_address(address: str) -> Tuple[str, Optional[int]]:
    """Parses a raw address string to extract the postcode."""
    address = address.replace("Â", "").strip()
    postcode_match = re.search(r"\b(\d{4})\b$", address)
    postcode = int(postcode_match.group(1)) if postcode_match else None
    return address, postcode

def parse_sale_info(html: HTMLParser) -> Tuple[Optional[str], Optional[str]]:
    """Parses sale type and date from the property page."""
    sale_info_elem = html.css_first("div.css-rxp4mi div.css-1h8fpgv div.css-tmtv67 span.css-1nj9ymt")
    if sale_info_elem:
        sale_info_text = sale_info_elem.text(strip=True)
        date_match = re.search(r"(\d{1,2}\s\w{3}\s\d{4})", sale_info_text)
        if date_match:
            sale_date = date_match.group(1)
            sale_type = sale_info_text.replace(sale_date, "").strip()
            return sale_type, sale_date
        return sale_info_text, None
    return None, None

def parse_price(html: HTMLParser) -> Optional[int]:
    """Parses the property price from the page."""
    price_elem = html.css_first("div.css-rxp4mi div.css-1gkcyyc div.css-qrqvvg p.css-mgq8yx")
    if price_elem:
        price_text = re.sub(r'[$,]', '', price_elem.text()).strip()
        if price_text.isdigit():
            return int(price_text)
    return None

def parse_property_details(html: HTMLParser) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """Extracts bedrooms, baths, parking, and area from property features."""
    features = {"bedrooms": None, "baths": None, "parking": None, "area": None}
    feature_elements = html.css("div[data-testid='property-features-wrapper'] span[data-testid='property-features-feature']")
    for feature in feature_elements:
        text = feature.text()
        value = re.search(r"\d+", text)
        if value:
            val = int(value.group(0))
            if "Bed" in text: features["bedrooms"] = val
            elif "Bath" in text: features["baths"] = val
            elif "Parking" in text: features["parking"] = val
            elif "m²" in text: features["area"] = val
    return features["bedrooms"], features["baths"], features["parking"], features["area"]

def parse_sales_page_url(html: HTMLParser) -> Optional[str]:
    """Parses the individual property listing URL from a search results item."""
    link = html.css_first("div.css-qrqvvg a.address.is-two-lines.css-1y2bib4")
    return link.attributes.get("href") if link else None

def parse_html(html_content: str, url: str) -> Optional[Dict[str, Any]]:
    """
    Top-level parser for a single property page's HTML content.
    Orchestrates calls to more specific parsing functions.
    """
    html = HTMLParser(html_content)
    address_elem = html.css_first("div.css-qrqvvg a.address.is-two-lines.css-1y2bib4 h2.css-bqbbuf")
    if not address_elem:
        logging.warning(f"Could not find address element on {url}, skipping parse.")
        return None

    address, postcode = parse_address(address_elem.text(strip=True))
    bedrooms, baths, parking, area = parse_property_details(html)
    sale_type, sale_date = parse_sale_info(html)
    price = parse_price(html)

    return {
        "sale_type": sale_type, "sale_date": sale_date, "price": price,
        "address": address, "postcode": postcode, "bedrooms": bedrooms,
        "baths": baths, "parking": parking, "area": area, "sales_page_href": url,
    }

# --- Web Scraping ---

async def fetch_page(client: httpx.AsyncClient, url: str, retries: int, backoff_factor: float) -> Optional[str]:
    """
    Fetches the content of a single URL with robust error handling.

    This function performs an async GET request. It implements an exponential
    backoff retry mechanism to handle transient network errors or server-side
    issues (like rate limiting).

    Args:
        client: The httpx.AsyncClient instance.
        url: The URL to fetch.
        retries: Maximum number of retry attempts.
        backoff_factor: The base factor for calculating retry delay.

    Returns:
        The page's HTML content as a string, or None if all retries fail.
    """
    for attempt in range(retries):
        try:
            # The client will use a randomly selected User-Agent for this request
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            logging.warning(f"Request error for {url}: {e}. Attempt {attempt + 1}/{retries}.")
        except httpx.HTTPStatusError as e:
            logging.warning(f"HTTP {e.response.status_code} for {url}. Attempt {attempt + 1}/{retries}.")
            if e.response.status_code == 404:
                return None  # Don't retry on "Not Found" errors

        if attempt < retries - 1:
            wait_time = backoff_factor * (2 ** attempt)
            await asyncio.sleep(wait_time)

    logging.error(f"Failed to fetch {url} after {retries} retries.")
    return None

async def process_page(url: str, client: httpx.AsyncClient, db_conn: sqlite3.Connection, retries: int, backoff_factor: float):
    """
    High-level task for processing one property: fetch, parse, and store.
    """
    html_content = await fetch_page(client, url, retries, backoff_factor)
    if not html_content:
        return

    parsed_data = parse_html(html_content, url)
    if parsed_data:
        insert_data(db_conn, parsed_data, html_content)

async def scrape_postcode(postcode: int, client: httpx.AsyncClient, db_conn: sqlite3.Connection, config: Dict[str, Any]):
    """
    Manages the entire scraping process for a single postcode.

    It iterates through all combinations of bedrooms, bathrooms, and parking spaces,
    and then pages through the search results for each combination until no more
    listings are found. A progress bar shows the progress through these combinations.
    """
    logging.info(f"--- Starting scrape for postcode: {postcode} ---")
    retries = config['retries']['max_retries']
    backoff = config['retries']['backoff_factor']

    # Create a list of all bed/bath/park configurations to iterate through
    configs = [(b, ba, p) for b in range(1, 6) for ba in range(6) for p in range(6)]

    # Iterate through configurations with a dedicated progress bar for this postcode
    for beds, bath, park in tqdm(configs, desc=f"Postcode {postcode}", leave=False, unit="config"):
        page = 1
        while True:
            search_url = f"https://www.domain.com.au/sold-listings/?ptype=free-standing&bedrooms={beds}&bathrooms={bath}&carspaces={park}&ssubs=0&postcode={postcode}&page={page}"

            html = await fetch_page(client, search_url, retries, backoff)
            if not html or "No exact matches" in html:
                logging.debug(f"[{postcode}] No results for beds={beds}, bath={bath}, park={park} at page {page}.")
                break # Break from the page loop, move to next config

            parser = HTMLParser(html)
            listing_urls = [url for elem in parser.css("li[data-testid^='listing-']") if (url := parse_sales_page_url(elem))]

            if not listing_urls:
                logging.warning(f"[{postcode}] Found no listing URLs on page {page} despite no 'exact matches' text.")
                break

            # Create and run tasks for each property on the current search page
            tasks = [process_page(link, client, db_conn, retries, backoff) for link in listing_urls]
            await asyncio.gather(*tasks)

            page += 1
            await asyncio.sleep(config['scraper']['crawl_delay'])
    logging.info(f"--- Finished scrape for postcode: {postcode} ---")

# --- Main Execution ---

async def main():
    """
    The main asynchronous function that orchestrates the entire scraping process.
    It sets up configuration, logging, and the database, then creates and runs
    scraping tasks for all specified postcodes with an overall progress bar.
    """
    config = load_config()
    setup_logging(config['logging']['file_path'])
    db_conn = init_db(config['database']['path'])

    # Set headers with a randomly chosen User-Agent
    user_agents = config['scraper'].get('user_agents', [])
    if not user_agents:
        logging.error("No user_agents found in config.toml. Please add some.")
        return

    headers = {"User-Agent": random.choice(user_agents)}

    # Use a semaphore to limit the number of concurrent requests
    semaphore = asyncio.Semaphore(config['scraper']['max_concurrency'])

    async def run_with_semaphore(coro):
        async with semaphore:
            return await coro

    # The main async block to run the scraper
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        postcode_tasks = [
            run_with_semaphore(scrape_postcode(postcode, client, db_conn, config))
            for postcode in config['scraper']['postcodes']
        ]

        # Use tqdm.gather to display an overall progress bar for all postcodes
        print(f"Starting scraper for {len(postcode_tasks)} postcodes...")
        results = await tqdm.gather(*postcode_tasks, desc="Overall Progress")

        for i, result in enumerate(results):
             if isinstance(result, Exception):
                 failed_postcode = config['scraper']['postcodes'][i]
                 logging.error(f"Scraping failed for postcode {failed_postcode} with exception: {result}")

    db_conn.close()
    print("--- Scraping process has completed. ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        logging.critical("Scraper could not start due to a configuration error.")
    except Exception as e:
        logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
