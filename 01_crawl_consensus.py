"""
한경 컨센서스 애널리스트 리포트 크롤러
LG전자, 삼성전자 리포트를 수집합니다.
"""

import os
import time
import json
import urllib.parse
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import config


class HankyungConsensusCrawler:
    def __init__(self, headless=True):
        self.setup_directories()
        self.setup_driver(headless)

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(config.RAW_DIR, exist_ok=True)
        os.makedirs(config.CONSENSUS_DIR, exist_ok=True)
        os.makedirs(config.FILTERED_DIR, exist_ok=True)
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)

    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver with PDF download settings"""
        chrome_options = Options()

        # PDF auto-download settings
        prefs = {
            "download.default_directory": os.path.abspath(config.CONSENSUS_DIR),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # Force PDF download instead of viewing
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)

        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 20)

    def get_date_range(self):
        """Get date range for crawling (last N days)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=config.CRAWL_DATE_RANGE_DAYS)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

    def crawl_company_reports(self, company_name, company_code=None):
        """
        Crawl analyst reports for a specific company with pagination support

        Args:
            company_name: 회사명 (e.g., "LG전자")
            company_code: 종목코드 (optional, not used in new URL format)
        """
        print(f"\n{'='*60}")
        print(f"Crawling reports for {company_name}")
        print(f"{'='*60}")

        # Get date range
        start_date, end_date = self.get_date_range()

        all_reports = []
        page = 1
        max_pages = (config.MAX_REPORTS_PER_COMPANY // 50) + 1  # 50 reports per page

        while len(all_reports) < config.MAX_REPORTS_PER_COMPANY:
            print(f"\nFetching page {page}...")

            # Build URL with proper encoding and pagination
            search_text_encoded = urllib.parse.quote(company_name)
            url = (f"{config.HANKYUNG_CONSENSUS_URL}/analysis/list?"
                   f"sdate={start_date}&edate={end_date}&"
                   f"search_text={search_text_encoded}&pagenum=50&now_page={page}")

            print(f"URL: {url}")
            if page == 1:
                print(f"Date range: {start_date} ~ {end_date}")

            self.driver.get(url)

            # Wait for page to load
            time.sleep(3)

            # Try to wait for table to load
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.table_style01 table")))
            except:
                print("Table not found with wait, continuing...")

            # Get page source
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Find the main table
            table = soup.select_one('div.table_style01 table')

            if not table:
                print(f"Warning: Report table not found on page {page}.")
                if page == 1:
                    print(f"Saving raw HTML for inspection...")
                    self.save_raw_html(company_name, "", html)
                break

            # Find all report rows (skip header)
            report_rows = table.select('tbody tr')

            if not report_rows:
                print(f"No more reports found on page {page}. Stopping pagination.")
                break

            print(f"Found {len(report_rows)} report rows on page {page}")

            # Process each report
            page_reports = []
            for idx, row in enumerate(report_rows, 1):
                try:
                    # Extract cells
                    cells = row.find_all('td')

                    if len(cells) < 6:
                        continue

                    # Parse report data based on actual HTML structure
                    date_cell = cells[0]  # td.first.txt_number
                    category_cell = cells[1]
                    title_cell = cells[2]  # td.text_l
                    author_cell = cells[3]
                    source_cell = cells[4]
                    file_cell = cells[5]

                    # Extract title and link
                    title_link = title_cell.select_one('a')
                    if not title_link:
                        continue

                    title = title_link.get_text(strip=True)
                    report_link = title_link.get('href', '')

                    # Extract PDF download link
                    pdf_link_elem = file_cell.select_one('a[href*="downpdf"]')
                    pdf_link = pdf_link_elem.get('href', '') if pdf_link_elem else ''

                    # Build full PDF URL
                    if pdf_link and not pdf_link.startswith('http'):
                        pdf_link = config.HANKYUNG_CONSENSUS_URL + pdf_link

                    report_data = {
                        'company_name': company_name,
                        'date': date_cell.get_text(strip=True),
                        'category': category_cell.get_text(strip=True),
                        'title': title,
                        'author': author_cell.get_text(strip=True),
                        'source': source_cell.get_text(strip=True),
                        'report_link': report_link,
                        'pdf_link': pdf_link,
                        'crawled_at': datetime.now().isoformat()
                    }

                    page_reports.append(report_data)
                    print(f"  [{len(all_reports) + idx}] {report_data['date']} - {report_data['title'][:50]}...")

                except Exception as e:
                    print(f"  Error processing row {idx}: {str(e)}")
                    continue

            if not page_reports:
                print(f"No valid reports found on page {page}. Stopping pagination.")
                break

            all_reports.extend(page_reports)

            # Check if we have enough reports or reached max pages
            if len(all_reports) >= config.MAX_REPORTS_PER_COMPANY:
                all_reports = all_reports[:config.MAX_REPORTS_PER_COMPANY]
                print(f"\nReached maximum report limit ({config.MAX_REPORTS_PER_COMPANY})")
                break

            if page >= max_pages:
                print(f"\nReached maximum page limit ({max_pages})")
                break

            # Check if there are fewer reports than pagenum (last page)
            if len(page_reports) < 50:
                print(f"\nLast page reached (fewer than 50 reports)")
                break

            page += 1

        print(f"\nSuccessfully extracted {len(all_reports)} reports across {page} page(s)")

        # Save reports metadata
        self.save_reports(company_name, all_reports)

        # Download PDFs
        self.download_pdfs(company_name, all_reports)

        return all_reports

    def download_pdfs(self, company_name, reports):
        """Download PDF files by clicking download button in PDF viewer"""
        print(f"\n{'='*60}")
        print(f"Downloading PDFs for {company_name}")
        print(f"{'='*60}")
        print(f"Total reports to download: {len(reports)}")
        print(f"{'='*60}\n")

        success_count = 0
        skip_count = 0
        fail_count = 0

        for idx, report in enumerate(reports, 1):
            if not report.get('pdf_link'):
                continue

            try:
                pdf_url = report['pdf_link']

                # Create safe filename
                date_str = report['date'].replace('-', '').replace('/', '')
                safe_title = "".join(c for c in report['title'][:30] if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_title = safe_title.replace(' ', '_')

                filename = f"{company_name}_{date_str}_{safe_title}.pdf"
                filepath = os.path.join(config.CONSENSUS_DIR, filename)

                # Skip if already exists and has content
                if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:  # More than 1KB
                    skip_count += 1
                    print(f"  [{idx}/{len(reports)}] SKIP: {filename}")
                    print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
                    continue

                # Download PDF
                print(f"  [{idx}/{len(reports)}] Downloading: {filename}")
                print(f"           URL: {pdf_url}")

                # Navigate to PDF viewer page
                self.driver.get(pdf_url)
                time.sleep(2)  # Wait for PDF viewer to load

                # Wait for and click download button
                try:
                    # Try multiple selectors for download button
                    download_button = None
                    selectors = [
                        'cr-icon-button#save',
                        'cr-icon-button[title="다운로드"]',
                        'cr-icon-button[aria-label="다운로드"]',
                        '#save',
                        '[title="다운로드"]'
                    ]

                    for selector in selectors:
                        try:
                            download_button = self.wait.until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            break
                        except:
                            continue

                    if download_button:
                        download_button.click()
                        print(f"      Clicked download button")

                        # Wait for file to be downloaded
                        download_wait_time = 0
                        downloaded_file = None

                        while download_wait_time < 15:
                            # Check for our expected filename
                            if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                                success_count += 1
                                file_size_kb = os.path.getsize(filepath) / 1024
                                print(f"           [OK] Downloaded: {file_size_kb:.1f} KB")
                                print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
                                downloaded_file = filepath
                                break

                            # Check for default downloaded files (report_idx.pdf)
                            # Extract report_idx from URL
                            import re
                            match = re.search(r'report_idx=(\d+)', pdf_url)
                            if match:
                                report_idx = match.group(1)
                                default_filename = f"{report_idx}.pdf"
                                default_filepath = os.path.join(config.CONSENSUS_DIR, default_filename)

                                if os.path.exists(default_filepath) and os.path.getsize(default_filepath) > 1000:
                                    # Rename to our format
                                    os.rename(default_filepath, filepath)
                                    success_count += 1
                                    file_size_kb = os.path.getsize(filepath) / 1024
                                    print(f"           [OK] Downloaded (renamed): {file_size_kb:.1f} KB")
                                    print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
                                    downloaded_file = filepath
                                    break

                            time.sleep(1)
                            download_wait_time += 1
                        else:
                            fail_count += 1
                            print(f"           [FAIL] Timeout waiting for download")
                            print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
                    else:
                        print(f"      Download button not found")

                        # Alternative: Auto-download might have worked
                        # Check for default downloaded files
                        import re
                        match = re.search(r'report_idx=(\d+)', pdf_url)
                        if match:
                            report_idx = match.group(1)
                            default_filename = f"{report_idx}.pdf"
                            default_filepath = os.path.join(config.CONSENSUS_DIR, default_filename)

                            time.sleep(3)  # Wait a bit for download

                            if os.path.exists(default_filepath) and os.path.getsize(default_filepath) > 1000:
                                os.rename(default_filepath, filepath)
                                success_count += 1
                                file_size_kb = os.path.getsize(filepath) / 1024
                                print(f"           [OK] Auto-downloaded: {file_size_kb:.1f} KB")
                                print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")

                except Exception as e:
                    fail_count += 1
                    print(f"           [FAIL] Error clicking download button: {str(e)}")
                    print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")

                # Be polite
                time.sleep(2)

            except Exception as e:
                fail_count += 1
                print(f"  [{idx}/{len(reports)}] [FAIL] Error: {str(e)}")
                print(f"           Progress: {success_count} downloaded, {skip_count} skipped, {fail_count} failed")
                continue

        print(f"\n{'='*60}")
        print(f"PDF Download Summary for {company_name}")
        print(f"{'='*60}")
        print(f"Total reports:    {len(reports)}")
        print(f"Downloaded:       {success_count}")
        print(f"Skipped (exists): {skip_count}")
        print(f"Failed:           {fail_count}")
        print(f"{'='*60}")

    def save_reports(self, company_name, reports):
        """Save crawled reports metadata to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{config.RAW_DIR}/{company_name}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        print(f"\nSaved metadata: {filename}")

    def save_raw_html(self, company_name, company_code, html):
        """Save raw HTML for inspection"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{config.RAW_DIR}/{company_name}_{timestamp}_raw.html"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"Saved raw HTML: {filename}")

    def crawl_all_companies(self):
        """Crawl reports for all configured companies"""
        all_reports = {}

        for company_name, company_code in config.COMPANIES.items():
            try:
                reports = self.crawl_company_reports(company_name, company_code)
                all_reports[company_name] = reports
                time.sleep(2)  # Wait between companies
            except Exception as e:
                print(f"Error crawling {company_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        return all_reports

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("\nBrowser closed.")


def main():
    """Main function to run the crawler"""
    import time
    start_time = time.time()

    print("="*60)
    print("Hankyung Consensus Crawler")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Companies: {', '.join(config.COMPANIES.keys())}")
    print(f"Date range: Last {config.CRAWL_DATE_RANGE_DAYS} days")
    print("="*60)

    crawler = HankyungConsensusCrawler(headless=True)

    try:
        all_reports = crawler.crawl_all_companies()

        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        for company, reports in all_reports.items():
            print(f"{company}: {len(reports)} reports collected")
        print("="*60)
        print(f"Total time: {minutes}m {seconds}s")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print("\n[OK] Crawling completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Error during crawling: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        crawler.close()


if __name__ == "__main__":
    main()
