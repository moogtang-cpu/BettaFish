
# Get Company Information Tool

This tool crawls the web to retrieve information about a specified company.

## Function: `get_company_info(company_name)`

### Parameters

- `company_name` (str): The name of the company to search for.

### Returns

- A string containing the title of the search result page, or an error message if the request fails.

### Example Usage

```python
from company_info_crawler import get_company_info

company_name = "Apple Inc."
info = get_company_info(company_name)
print(f"Information about {company_name}: {info}")
```
