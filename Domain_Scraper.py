import httpx
import time
from random import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd


def fetch_property_data(client, url, retries=5):
    """
    Fetches property data from a given URL using an HTTP client.

    Args:
        client (httpx.Client): The HTTP client to use for fetching the data.
        url (str): The URL to fetch the data from.
        retries (int, optional): The number of times to retry the fetch in case of failure. Defaults to 5.

    Returns:
        str or None: The fetched data as a string, or None if the fetch failed after the specified number of retries.
    """
    # Initialize the attempt counter
    attempt = 0

    # Try to fetch the data until the maximum number of retries is reached
    while attempt < retries:
        try:
            # Send a GET request to the URL and raise an exception if the request fails
            response = client.get(url)
            response.raise_for_status()

            # Return the fetched data if the request was successful
            return response.text
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            # Increment the attempt counter and calculate the wait time for the next retry
            attempt += 1
            wait = (2**attempt) + (random() * 0.1)  # Exponential backoff with jitter

            # Print a message indicating the retry and the wait time
            print(f"Retry {attempt} for {url} in {wait:.2f} seconds due to {exc}")

            # Wait for the calculated wait time before retrying the fetch
            time.sleep(wait)

    # Print a message indicating that the fetch failed after the maximum number of retries
    print(f"Failed to fetch {url} after {retries} retries.")

    # Return None to indicate that the fetch failed
    return None


def fetch_postcode_data(postcode, client):
    """
    Fetches property HTML data for a given postcode, number of bedrooms, number of bathrooms, and number of parking spaces.

    Args:
        postcode (str): The postcode to fetch data for.
        client (httpx.Client): The HTTP client to use for fetching the data.

    Returns:
        list: A list of property HTML data.
    """
    # Initialize an empty list to store property HTML data
    property_html = []

    # Iterate over different bedroom, bathroom, and parking space configurations
    for beds in range(1, 6):
        for bath in range(6):
            for park in range(6):
                found_no_matches = False  # Flag to break the page loop

                # Iterate over different pages of search results
                for page in range(1, 50):
                    if found_no_matches:
                        break

                    # Construct the search URL with the current configuration
                    url = f"https://www.domain.com.au/sold-listings/?ptype=free-standing&bedrooms={beds}&bathrooms={bath}&carspaces={park}&ssubs=0&postcode={postcode}&page={page}"

                    # Fetch the HTML data from the URL
                    response_text = fetch_property_data(client, url)

                    # Check if the response contains the "No exact matches" message
                    if response_text:
                        if "No exact matches" in response_text:
                            print(
                                f"No more matches for {postcode} with {beds} beds, {bath} baths, {park} parking spaces @ page {page}"
                            )
                            found_no_matches = True  # Set flag to break page loop
                            break
                        else:
                            # Append the property HTML data to the list
                            property_html.append(response_text)

    # Return the list of property HTML data
    return property_html


def main():
    """
    Main function that fetches property HTML data for each postcode in SydneyPostcodes
    and saves it to a CSV file.
    """
    # Initialize an empty list to store property HTML data
    property_html = []

    # Create an HTTP client with specific headers and timeout
    with httpx.Client(headers=headers, timeout=300) as client:
        # Create a thread pool executor to fetch postcode data concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit a task for each postcode to fetch property HTML data
            futures = [
                executor.submit(fetch_postcode_data, postcode, client)
                for postcode in SydneyPostcodes
            ]

            # Extend the property HTML list with the results of each task
            for future in as_completed(futures):
                property_html.extend(future.result())

    # Create a DataFrame from the property HTML list and save it to a CSV file
    df = pd.DataFrame(property_html, columns=["html"])
    df["html"].to_csv(
        "NSW_Property_Projection_Personal_Project/property_html.csv",
        index=False,
        header="html",
    )


# fmt: off
SydneyPostcodes = [
    2000, 2006, 2007, 2008, 2009, 2010, 2011, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036, 2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048, 2049, 2050, 2052, 2060, 2061, 2062, 2063, 2064, 2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072, 2073, 2074, 2075, 2076, 2077, 2079, 2080, 2081, 2082, 2083, 2084, 2085, 2086, 2087, 2088, 2089, 2090, 2092, 2093, 2094, 2095, 2096, 2097, 2099, 2100, 2101, 2102, 2103, 2104, 2105, 2106, 2107, 2108, 2109, 2110, 2111, 2112, 2113, 2114, 2115, 2116, 2117, 2118, 2119, 2120, 2121, 2122, 2123, 2125, 2126, 2127, 2128, 2129, 2130, 2131, 2132, 2133, 2134, 2135, 2136, 2137, 2138, 2139, 2140, 2141, 2142, 2143, 2144, 2145, 2146, 2147, 2148, 2150, 2151, 2152, 2153, 2154, 2155, 2156, 2157, 2158, 2159, 2160, 2161, 2162, 2163, 2164, 2165, 2166, 2167, 2168, 2170, 2171, 2172, 2173, 2174, 2175, 2176, 2177, 2178, 2179, 2190, 2191, 2192, 2193, 2194, 2195, 2196, 2197, 2198, 2199, 2200, 2203, 2204, 2205, 2206, 2207, 2208, 2209, 2210, 2211, 2212, 2213, 2214, 2216, 2217, 2218, 2219, 2220, 2221, 2222, 2223, 2224, 2225, 2226, 2227, 2228, 2229, 2230, 2231, 2232, 2233, 2234, 2555, 2556, 2557, 2558, 2559, 2560, 2563, 2564, 2565, 2566, 2567, 2568, 2569, 2570, 2571, 2572, 2573, 2574, 2745, 2747, 2748, 2749, 2750, 2752, 2753, 2754, 2755, 2756, 2757, 2758, 2759, 2760, 2761, 2762, 2763, 2765, 2766, 2767, 2768, 2769, 2770, 2773, 2774, 2775, 2776, 2777, 2778, 2779, 2780, 2782, 2783, 2784, 2785, 2786, 2787, 2790
]
# fmt: on

if __name__ == "__main__":
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"
    }
    main()
