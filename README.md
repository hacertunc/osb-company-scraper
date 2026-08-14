# OSB Company Data Collection System

A Python-based data automation project developed to automatically collect, clean, standardize, and export company information from the websites of Organized Industrial Zones (OSBs) in Türkiye.

This project was developed during an internship to automate the process of collecting company data from different OSB websites instead of gathering the information manually.

## Features

* Company name extraction
* Industry/sector information extraction
* Phone number extraction
* Email address extraction
* Website information extraction
* Address information extraction
* Turkish character normalization
* CSV output generation
* Google Sheets integration
* HTTP session management
* Retry and timeout mechanisms
* Anti-bot and challenge page detection
* Modular scraper architecture

## How the System Works

The project generally follows the data flow below:

```text
OSB Website
      ↓
Company List Retrieval
      ↓
Company Detail Page Scraping
      ↓
Data Cleaning and Standardization
      ↓
Contact Information Validation
      ↓
CSV / Google Sheets Export
```

## Technologies Used

* Python
* Requests
* BeautifulSoup
* Google Sheets API
* Google Service Account

## Project Structure

```text
osb-company-scraper/
│
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py
│   └── sakarya3.py
│
├── data/
│   └── sample_companies.csv
│
├── scraper.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Scraper Architecture

Common scraping operations are handled through the `BaseScraper` class.

The `base_scraper.py` file is responsible for common functionality such as:

* HTTP session creation
* User-Agent management
* Retry mechanism
* Request timeout handling
* Anti-bot and challenge page detection
* Text cleaning
* Turkish character normalization
* Delays between requests

OSB-specific scraper modules are stored inside the `scrapers/` directory.

For example:

```text
scrapers/sakarya3.py
```

This structure makes it easier to add new OSB scrapers without repeating the same common logic in every module.

## Sample Data

The `data/sample_companies.csv` file contains sample records that demonstrate the structure of the data produced by the system.

Example columns:

```text
company_name
sector
phone
email
website
```

## Installation

After cloning or downloading the project, install the required Python packages with:

```bash
pip install -r requirements.txt
```

## Running the Project

Run the main scraper file with:

```bash
python scraper.py
```

## Project Goal

The main goal of this project is to reduce manual data entry by automatically collecting company information from OSB websites with different structures and converting it into a standardized format.

The modular architecture also makes the project easier to maintain and extend with additional OSB-specific scraper modules.

## Future Improvements

The project can be extended in the future with features such as:

* Additional OSB scraper modules
* More advanced data validation
* Centralized database support
* REST API integration
* Web-based management dashboard
* Automated scraper scheduling
