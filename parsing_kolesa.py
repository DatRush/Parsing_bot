import time
import random
import playwright
from utils import setup_logging, connect_db, insert_ad, clean_comment, convert_to_boolean, try_load_page, is_url_in_set, extract_id_from_url, fetch_existing_ids
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from config import BASE_URL, SLEEP_INTERVAL
import datetime


def main(logger):
    # Connect to the database and fetch already known car IDs
    conn = connect_db()
    cur = conn.cursor()
    existing_ids = fetch_existing_ids(cur)
    current_page = 2
    ad_data_buffer = []

    while True:
        with sync_playwright() as p:
            # Launch the browser and configure it
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.set_default_navigation_timeout(60000) 
            # Block loading of images to save bandwidth and speed up loading
            context.route("**/*", lambda route: route.abort() if 'image' in route.request.resource_type else route.continue_())       

            try:
                while True:
                    known_count = 0
                    page_url = f"{BASE_URL}/cars/?page={current_page}"
                    page = context.new_page()
                     # Try to load the page and check if it fails
                    if not try_load_page(page, page_url, logger):
                        logger.error("Не удалось загрузить страницу: " + page_url)
                        return
                    # Wait for the specific element to ensure the page has loaded
                    page.wait_for_selector('.a-card__title')
                    
                    # Collect all links from the current page
                    links = page.query_selector_all('.a-card__title a')
                    links_data = []
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            # Construct the full URL of the ad
                            if href:
                                full_url = href if href.startswith('http') else BASE_URL + href
                                id_car = extract_id_from_url(full_url)  
                                # Check if the car ID is already known
                                if id_car:  
                                    if id_car and not is_url_in_set(id_car, existing_ids):
                                        existing_ids.add(id_car)
                                    else:
                                        logger.info(f"URL already exists in database: {full_url}")
                                        known_count += 1
                                else:
                                    logger.error(f"Failed to extract ID from URL: {full_url}")
                        except Exception as e:
                            logger.error(f"Failed to retrieve href attribute: {e}")
                        
                        # Random delay to mimic human behavior
                        time.sleep(random.randint(1, 5))
                        
                        # Open the ad page and extract data
                        page1 = browser.new_page()
                        page1.goto(full_url, timeout=60000, wait_until="domcontentloaded")
                        page1.wait_for_selector('.offer__title')

                        content = page1.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        
                        # Extract data from the page using BeautifulSoup
                        car_data = soup.find('h1', class_='offer__title')
                        price_data = soup.find('div', class_='offer__price')

                        car = car_data.text.strip() if car_data else 'Недоступно'
                        year = car_data.find('span', class_='year').text.strip() if car_data and car_data.find('span', class_='year') else 'Недоступно'
                        price = price_data.get_text(strip=True).replace('\xa0', '').replace('₸', '').strip() if price_data else 'Недоступно'
                        
                        comment_div = soup.find('div', class_='offer__content-block offer__description')
                        comment_html = str(comment_div) if comment_div else ''
                        comment = clean_comment(comment_html)

                        details = {dl.find('dt', class_='value-title').get('title'): dl.find('dd', class_='value').text.strip() for dl in soup.find_all('dl')}
                        
                        # Structure the ad data to prepare for database insertion
                        ad_data = {
                            "title": car,
                            "year": year,
                            "price": price,
                            "city": details.get('Город', 'Недоступно'),
                            "seller_comment": comment,
                            "generation": details.get('Поколение', 'Недоступно'),
                            "body_type": details.get('Кузов', 'Недоступно'),
                            "engine_volume": details.get('Объем двигателя, л', 'Недоступно'),
                            "transmission": details.get('Коробка передач', 'Недоступно'),
                            "drive_type": details.get('Привод', 'Недоступно'),
                            "wheel_side": details.get('Руль', 'Недоступно'),
                            "color": details.get('Цвет', 'Недоступно'),
                            "customs_cleared": convert_to_boolean(details.get('Растаможен в Казахстане', 'Нет')),
                            "url": full_url,
                            "insert_date": datetime.datetime.now()
                        }
                        ad_data_buffer.append(ad_data)
                        # Insert collected data into the database when buffer is full
                        if len(ad_data_buffer) >= 20:
                            insert_ad(ad_data_buffer, conn)
                            ad_data_buffer.clear()
                            logger.info("")

                        page1.close()                        
                        
                    logger.info(f'Known ads count: {known_count}')
                        
                    # Reset page counter if all ads are known
                    if known_count == len(links):
                        logger.info("All ads on page already known.")
                        time.sleep(SLEEP_INTERVAL)
                        current_page = 2
                        continue
                    else:
                        current_page += 1
                        logger.info(f"Moving to next page: {page_url}.")
                        
                    if ad_data_buffer:
                        insert_ad(ad_data_buffer, conn)
                        ad_data_buffer.clear()
                        logger.info("Remaining data packet has been sent.")
            
            except playwright._impl._errors.TimeoutError as e:
                logger.error(f"TimeoutError when loading {full_url}: {e}")
                continue

            finally:
                # Clean up database connections and close browser
                cur.close()
                conn.close()
                try:
                    browser.close()
                except Exception as e:
                    logger.error(f"Error when closing the browser: {e}")
                cur.close()
                conn.close()

if __name__ == "__main__":
    # Setup logging and start the main process loop
    logger = setup_logging()  
    while True:
        try:
            main(logger)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)  
            time.sleep(30)  
            logger.info("Restarting")  

