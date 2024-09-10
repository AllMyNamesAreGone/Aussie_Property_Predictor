import pandas as pd
from selectolax.parser import HTMLParser
import sqlite3
import re


def parse_address(address):
    """
    Parses an address and extracts the postcode.

    Args:
        address (str): The address to be parsed.

    Returns:
        tuple: A tuple containing the original address and the extracted postcode.
               If the postcode is not found in the address, the postcode is set to None.
    """
    # Strip new line character from address
    address = address.replace("Â", "")

    # Extract the last 4 characters from the address
    last_four_chars = address[-4:]

    # Regex pattern to match a 4-digit number
    postcode_regex = re.compile(r"\b\d{4}\b$")

    # Search for the postcode in the address
    postcode_match = postcode_regex.search(address)

    # Extract the postcode if found, otherwise set it to None
    if last_four_chars.isdigit():
        postcode = last_four_chars
    elif postcode_match:
        postcode = postcode_match.group()
    else:
        postcode = None

    return address, postcode


def parse_sale_info(html):
    """
    Parses the sale information from the HTML and returns the sale type and sale date.

    Args:
        html (HTMLParser): The HTML parser object containing the HTML content.

    Returns:
        tuple: A tuple containing the sale type and sale date.
               If the sale date is not found in the HTML, sale date is set to None.
    """
    # Find the element containing the sale information
    sale_info_elem = html.css_first(
        "div.css-rxp4mi div.css-1h8fpgv div.css-tmtv67 span.css-1nj9ymt"
    )

    # Initialize variables for sale type and sale date
    sale_type = sale_date = None

    # Check if sale information element is found
    if sale_info_elem:
        # Get the text content of the sale information element
        sale_info_text = sale_info_elem.text().strip()

        # Regular expression pattern to match a date in the format DD MMM YYYY
        sale_date_regex = re.compile(r"\d{1,2} \w{3} \d{4}")

        # Search for the sale date in the sale information text
        sale_date_match = sale_date_regex.search(sale_info_text)

        # If sale date is found, extract it and remove it from the sale information text
        if sale_date_match:
            sale_date = sale_date_match.group()
            sale_type = sale_info_text.replace(sale_date, "").strip()
        else:
            # If sale date is not found, set sale type as the entire sale information text
            sale_type = sale_info_text

    # Return the sale type and sale date as a tuple
    return sale_type, sale_date


def parse_price(html):
    """
    Parses the price from the HTML and returns it as an integer.

    Args:
        html (HTMLParser): The HTML parser object containing the HTML content.

    Returns:
        int or None: The price as an integer, or None if the price is not found or invalid.
    """
    # Find the element containing the price
    price_elem = html.css_first(
        "div.css-rxp4mi div.css-1gkcyyc div.css-qrqvvg p.css-mgq8yx"
    )

    # Check if price element is found
    if price_elem:
        # Get the text content of the price element and remove unwanted characters
        price_text = price_elem.text().replace("$", "").replace(",", "").strip()

        # Check if the price text is a valid integer
        if price_text.isdigit():
            # Return the price as an integer
            return int(price_text)

    # Return None if the price is not found or invalid
    return None


def parse_property_details(html):
    """
    Extracts property details (bedrooms, baths, parking, area) from the HTML.

    Args:
        html (HTMLParser): The HTML parser object containing the HTML content.

    Returns:
        tuple: A tuple containing the extracted property details.
               If a detail is not found, it is set to None.
    """
    # Find the wrapper element containing the property features
    features_wrapper = html.css_first("div[data-testid='property-features-wrapper']")

    # Find all the feature elements within the wrapper
    feature_elements = (
        features_wrapper.css("span[data-testid='property-features-feature']")
        if features_wrapper
        else []
    )

    # Initialize variables for property details
    bedrooms = baths = parking = area = None

    # Iterate over each feature element
    for feature in feature_elements:
        # Get the text content of the feature element
        feature_text = feature.text()

        # Check if the feature is related to bedrooms
        if "Beds" in feature_text:
            # Extract the number of bedrooms if it is a valid integer
            bedrooms = (
                int(feature_text.split()[0])
                if feature_text.split()[0].isdigit()
                else None
            )

        # Check if the feature is related to baths
        elif "Bath" in feature_text:
            # Extract the number of baths if it is a valid integer
            baths = (
                int(feature_text.split()[0])
                if feature_text.split()[0].isdigit()
                else None
            )

        # Check if the feature is related to parking
        elif "Parking" in feature_text:
            # Extract the number of parking spaces if it is a valid integer
            parking = (
                int(feature_text.split()[0])
                if feature_text.split()[0].isdigit()
                else None
            )

        # Check if the feature is related to area
        elif "m²" in feature_text:
            # Extract the area if it is a valid integer
            area_search = re.search(r"\d+", feature_text)
            area = int(area_search.group()) if area_search else None

    # Return the extracted property details as a tuple
    return bedrooms, baths, parking, area


def parse_sales_page(html):
    """
    Parses the sales page href from the HTML and returns it as a string.

    Args:
        html (HTMLParser): The HTML parser object containing the HTML content.

    Returns:
        str or None: The sales page href as a string, or None if the href is not found.
    """
    # Find the element containing the sales page href
    sales_page_elem = html.css_first(
        "div.css-qrqvvg a.address.is-two-lines.css-1y2bib4"
    )

    # Check if the sales page element is found
    if sales_page_elem:
        # Get the href attribute of the sales page element
        return sales_page_elem.attributes.get("href", "N/A")

    # Return None if the sales page element is not found
    return None


def parse_html(html_content):
    """
    Parses HTML content and extracts relevant data.

    Args:
        html_content (str): The HTML content to be parsed.

    Returns:
        dict: A dictionary containing the extracted data.
               If a data is not found, it is set to None.
    """
    # Parse the HTML content
    html = HTMLParser(html_content)

    # Initialize a dictionary to store the extracted data
    extracted_data = {
        "sale_type": None,  # Sale type
        "sale_date": None,  # Sale date
        "price": None,  # Price
        "address": None,  # Address
        "postcode": None,  # Postcode
        "bedrooms": None,  # Bedrooms
        "baths": None,  # Bathrooms
        "parking": None,  # Parking spaces
        "area": None,  # Area
        "sales_page_href": None,  # Sales page href
    }

    try:
        # Extract sale information
        extracted_data["sale_type"], extracted_data["sale_date"] = parse_sale_info(html)

        # Extract price
        extracted_data["price"] = parse_price(html)

        # Extract address and postcode
        address_elem = html.css_first(
            "div.css-qrqvvg a.address.is-two-lines.css-1y2bib4 h2.css-bqbbuf"
        )
        if address_elem:
            address = address_elem.text()
            (
                extracted_data["address"],
                extracted_data["postcode"],
            ) = parse_address(address)

        # Extract property details
        (
            extracted_data["bedrooms"],
            extracted_data["baths"],
            extracted_data["parking"],
            extracted_data["area"],
        ) = parse_property_details(html)

        # Extract sales page href
        extracted_data["sales_page_href"] = parse_sales_page(html)

    except Exception as e:
        # Print error message if any exception occurs during parsing
        print(f"Error parsing HTML: {e}")

    return extracted_data


def create_table(cursor):
    """
    Creates the Domain table in the database if it does not already exist.

    Args:
        cursor (sqlite3.Cursor): The cursor object used to execute SQL commands.
    """

    # Create the Domain table if it does not exist
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS Domain (
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
        sales_page_href TEXT
    )
    """
    )


def insert_data(cursor, data):
    """
    Inserts data into the Domain table.

    Args:
        cursor (sqlite3.Cursor): The cursor object used to execute SQL commands.
        data (list): A list of dictionaries, each containing the data to be inserted.
    """

    # Execute the SQL to insert data into the Domain table
    cursor.executemany(
        """
        INSERT INTO Domain (
            sale_type, sale_date, price, address, postcode, bedrooms, baths, parking, area, sales_page_href
        ) VALUES (
            :sale_type, :sale_date, :price, :address, :postcode, :bedrooms, :baths, :parking, :area, :sales_page_href
        )
    """,
        data,
    )


def main():
    """
    Main function that connects to the SQLite database, parses data from CSV file, and inserts it into the Domain table.
    """
    # Connect to the SQLite database
    connection = sqlite3.connect(
        "NSW_Property_Projection_Personal_Project/property_data.db"
    )
    cursor = connection.cursor()

    # Create the Domain table if it doesn't exist
    create_table(cursor)
    connection.commit()

    # Initialize a list to store all the extracted data
    all_data = []

    # Define the chunk size for reading the CSV file
    chunk_size = 10000

    # Read the CSV file in chunks and process each chunk
    for chunk in pd.read_csv(
        "NSW_Property_Projection_Personal_Project/property_html.csv",
        chunksize=chunk_size,
    ):
        # Iterate over each row in the chunk and extract the data
        for index, row in chunk.iterrows():
            html_content = row["html"]
            extracted_data = parse_html(html_content)
            all_data.append(extracted_data)

        # Insert the extracted data into the Domain table
        insert_data(cursor, all_data)
        connection.commit()

        # Print the size of the processed chunk and clear the list
        print(f"Processed a chunk of size {chunk_size}")
        all_data.clear()

    # Close the connection to the database
    cursor.close()
    connection.close()


if __name__ == "__main__":
    main()
