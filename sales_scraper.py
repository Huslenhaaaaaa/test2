import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
import time
import pandas as pd
import os
import logging
import random
import hashlib

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"sales_scraper_{date.today().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BASE_DELAY = 2  # Base delay between requests in seconds
JITTER = 1  # Random jitter to add to delays
CACHE_FILE = "scraped_sales_urls.txt"  # Changed cache file for sales

class UneguiScraper:
    def __init__(self, base_url, max_pages=90):
        self.base_url = base_url
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        self.scraped_urls = self.load_scraped_urls()
        
    def load_scraped_urls(self):
        """Load previously scraped URLs from cache file"""
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f)
        return set()
        
    def save_scraped_url(self, url):
        """Save URL to cache file after successful scraping"""
        with open(CACHE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
        self.scraped_urls.add(url)
    
    def make_request(self, url, retry_count=0):
        """Make an HTTP request with retry logic"""
        try:
            # Add randomized delay to be respectful to the server
            time.sleep(BASE_DELAY + random.random() * JITTER)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response
        except (requests.RequestException, requests.Timeout) as e:
            if retry_count < MAX_RETRIES:
                backoff_time = (2 ** retry_count) + random.random()
                logger.warning(f"Request failed for {url}: {str(e)}. Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
                return self.make_request(url, retry_count + 1)
            else:
                logger.error(f"Failed to retrieve {url} after {MAX_RETRIES} attempts: {str(e)}")
                return None

    def scrape_page(self, url):
        """Scrape all ad links from a single page"""
        response = self.make_request(url)
        if not response:
            return []
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all ad links based on the class "mask"
            ad_links = soup.find_all('a', class_='mask')
            
            # Extract the href attributes (the links)
            links = [link['href'] for link in ad_links if 'href' in link.attrs]
            
            logger.info(f"Found {len(links)} links on page {url}")
            return links
        except Exception as e:
            logger.error(f"Error parsing page {url}: {str(e)}")
            return []

    def get_value_chars(self, soup, key):
        """Extract value from elements with class='value-chars'"""
        element = soup.find('span', text=key)
        if element:
            value_chars = element.find_next('a', class_='value-chars')
            if value_chars:
                return value_chars.text.strip()
        return 'N/A'

    def get_text_value(self, soup, key):
        """Extract value from next span after key"""
        value = soup.find('span', text=key)
        if value:
            next_span = value.find_next('span')
            if next_span and not next_span.find('a', class_='value-chars'):
                return next_span.text.strip()
        return 'N/A'

    def scrape_ad(self, url):
        """Scrape detailed information from a single ad page"""
        # Check if URL has already been scraped
        if url in self.scraped_urls:
            logger.info(f"Skipping already scraped ad: {url}")
            return None
        
        response = self.make_request(url)
        if not response:
            return None
        
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Use dictionary instead of indexed list for better maintainability
            ad_data = {
                'Шал': self.get_text_value(soup, 'Шал:'),
                'Тагт': self.get_text_value(soup, 'Тагт:'),
                'Гараж': self.get_text_value(soup, 'Гараж:'),
                'Цонх': self.get_text_value(soup, 'Цонх:'),
                'Хаалга': self.get_text_value(soup, 'Хаалга:'),
                'Цонхнытоо': self.get_value_chars(soup, 'Цонхны тоо:'),
                'Барилгынявц': self.get_text_value(soup, 'Барилгынявц'),
                'Ашиглалтандорсонон': self.get_text_value(soup, 'Ашиглалтандорсонон:'),
                'Барилгындавхар': self.get_value_chars(soup, 'Барилгын давхар:'),
                'Талбай': self.get_value_chars(soup, 'Талбай:'),
                'Хэдэндавхарт': self.get_value_chars(soup, 'Хэдэн давхарт:'),
                'Лизингээравахболомж': self.get_text_value(soup, 'Лизингээравахболомж:'),
                'Дүүрэг': 'N/A',  # Will be populated below
                'Байршил': 'N/A',  # Will be populated below
                'Үзсэн': 'N/A',  # Will be populated below
                'Scraped_date': date.today().strftime("%d/%m/%Y"),
                'link': url,
                'Үнэ': 'N/A',  # Will be populated below
                'ӨрөөнийТоо': 'N/A',  # Will be populated below
                'Зарыг гарчиг': 'N/A',  # Will be populated below
                'Зарын тайлбар': 'N/A',  # Will be populated below
                'Нийтэлсэн': 'N/A',  # Will be populated below
                'ad_id': self.generate_ad_id(url)  # Unique identifier for the ad
            }
            
            # Handle address
            try:
                address = soup.find('span', itemprop="address")
                if address and '—' in address.text:
                    parts = address.text.split('—')
                    ad_data['Дүүрэг'] = parts[0].strip()
                    ad_data['Байршил'] = parts[1].strip()
            except Exception as e:
                logger.warning(f"Error extracting address from {url}: {str(e)}")
            
            # Extract views count
            views_element = soup.find('span', class_='counter-views')
            if views_element:
                ad_data['Үзсэн'] = views_element.text.strip().replace(' ', '')
            
            # Extract price from meta tag
            price_meta = soup.find('meta', {'itemprop': 'price'})
            if price_meta:
                price = price_meta.get('content', 'N/A')
                # Convert to integer if possible (remove .00)
                try:
                    price = str(int(float(price)))
                except:
                    pass
                ad_data['Үнэ'] = price
            
            # Extract room count
            location_div = soup.find('div', class_='wrap js-single-item__location')
            if location_div and location_div.find_all('span'):
                ad_data['ӨрөөнийТоо'] = location_div.find_all('span')[-1].text.strip()
            
            # Extract title
            title_element = soup.find('h1', class_='title-announcement')
            if title_element:
                ad_data['Зарыг гарчиг'] = title_element.text.strip().replace('\n', '')
            
            # Extract description
            desc_element = soup.find('div', class_='announcement-description')
            if desc_element:
                ad_data['Зарын тайлбар'] = desc_element.text.strip().replace('\n', '')
            
            # Extract posted date
            date_element = soup.find('span', class_='date-meta')
            if date_element:
                ad_data['Нийтэлсэн'] = date_element.text.strip().replace('Нийтэлсэн: ', '')
            
            # Mark as successfully scraped
            self.save_scraped_url(url)
            
            return ad_data
        except Exception as e:
            logger.error(f"Error scraping ad {url}: {str(e)}", exc_info=True)
            return None
    
    def generate_ad_id(self, url):
        """Generate a unique ID for each ad based on URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def run(self):
        """Main scraping process"""
        all_data = []
        existing_data = self.load_existing_data()
        
        # Start with existing data if available
        if not existing_data.empty:
            all_data = existing_data.to_dict('records')
            logger.info(f"Loaded {len(all_data)} existing records")
        
        # Scrape links from all pages
        all_links = []
        for page_num in range(1, self.max_pages + 1):
            logger.info(f"Scraping page {page_num}...")
            page_url = self.base_url if page_num == 1 else f"{self.base_url}?page={page_num}"
            
            links = self.scrape_page(page_url)
            if not links:
                logger.info("No more links found.")
                break
            
            all_links.extend(links)
        
        logger.info(f"Found {len(all_links)} links. Starting to scrape individual ads...")
        
        # Scrape each individual ad
        for i, link in enumerate(all_links, 1):
            full_url = f"https://www.unegui.mn{link}"
            logger.info(f"Scraping ad {i}/{len(all_links)}: {full_url}")
            
            ad_data = self.scrape_ad(full_url)
            if ad_data:
                all_data.append(ad_data)
            
            # Save periodically
            if i % 20 == 0:
                self.save_data(all_data)
                logger.info(f"Progress saved: {i}/{len(all_links)} ads processed")
        
        # Save final results
        if all_data:
            self.save_data(all_data)
            logger.info(f"Scraping completed. Total ads: {len(all_data)}")
        else:
            logger.warning("No data was collected.")
    
    def load_existing_data(self):
        """Load existing data from most recent CSV file if available"""
        try:
            # Find most recent CSV file
            files = [f for f in os.listdir('.') if f.startswith('unegui_sales_data_') and f.endswith('.csv')]
            if not files:
                return pd.DataFrame()
            
            latest_file = max(files)
            df = pd.read_csv(latest_file, encoding='utf-8-sig')
            logger.info(f"Loaded existing data from {latest_file}: {len(df)} records")
            return df
        except Exception as e:
            logger.warning(f"Could not load existing data: {str(e)}")
            return pd.DataFrame()
    
    def save_data(self, all_data):
        """Save data to CSV file"""
        df = pd.DataFrame(all_data)
        output_file = f"unegui_sales_data_{date.today().strftime('%Y%m%d')}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"Data saved to {output_file}: {len(df)} records")

def main():
    """Main entry point"""
    try:
        # Configuration - Updated for apartment sales listings
        base_url = "https://www.unegui.mn/l-hdlh/l-hdlh-zarna/oron-suuts-zarna/"
        max_pages = 165
        
        # Create and run scraper
        start_time = datetime.now()
        logger.info(f"Starting apartment sales scraper at {start_time}")
        
        scraper = UneguiScraper(base_url, max_pages)
        scraper.run()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Scraping completed in {duration}")
        
    except Exception as e:
        logger.error(f"Failed to load existing data: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    main()