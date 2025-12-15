
import requests
from bs4 import BeautifulSoup

def get_company_info(company_name):
    """
    Crawls the web to get company information.
    """
    # This is a placeholder for a more sophisticated implementation.
    # You might want to use a search engine API or a more robust crawling framework.
    url = f"https://www.google.com/search?q={company_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # This is a very simple way to extract information and might not work for all companies.
        # You would need to parse the search results more intelligently.
        # For demonstration purposes, we'll just return the title of the search page.
        return soup.title.string
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    company_name = "Apple Inc."
    info = get_company_info(company_name)
    print(f"Information about {company_name}: {info}")
