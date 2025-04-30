# Trivandrum Bar Association Lawyer Data Scraper

This project contains scripts to scrape lawyer data from the Trivandrum Bar Association website, including names, contact information, enrollment numbers, and addresses.

## Files Included

- `pagination_scraper.py`: Main Selenium-based scraper with robust pagination and error handling
- `README.md`: This documentation file

## Setup & Installation

1. Ensure you have Python 3.11+ installed
2. Create virtual environment and Install required dependencies:

```bash
# Create virtual environment
python3 -m virtualenv .venv

# Activate the environment
.venv\scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

3. You need Chrome browser installed for the Selenium WebDriver to work(already there in this repository)

## Usage

### Running the Scraper

```bash
python pagination_scraper.py
```

## Output Files

The scrapers generate the following CSV files:

- `lawyers_data_complete.csv`: Output from the main updated scraper

## How It Works

The scrapers work by:

1. Navigating to the lawyer directory pages
2. For each lawyer card, clicking the "View profile" button
3. Extracting the detailed information from the modal that appears
4. Saving all data to CSV files

The scrapers include extensive error handling, pagination support, and resumability features.

## Troubleshooting

- **WebDriver Issues**: If you encounter errors with Chrome WebDriver, make sure Chrome is updated to the latest version
- **Website Structure Changes**: If the website structure changes, the scrapers may need to be updated
- **Connection Issues**: The scripts include retry mechanisms for network issues

## Data Fields Collected

The scrapers collect the following information for each lawyer:

- Name
- Mobile Number
- Email
- Enrollment Number
- Office Address
- Residence Address
