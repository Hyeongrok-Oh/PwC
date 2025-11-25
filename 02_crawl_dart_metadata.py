"""
DART API를 사용한 사업보고서 크롤러
LG전자, 삼성전자의 분기, 반기, 사업보고서를 수집합니다.
"""

import os
import json
import zipfile
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
import config


class DartCrawler:
    def __init__(self):
        self.api_key = config.DART_API_KEY
        self.base_url = config.DART_API_BASE_URL
        self.corp_codes = {}  # {회사명: 고유번호}
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(config.RAW_DIR, exist_ok=True)
        os.makedirs(config.DART_DIR, exist_ok=True)

    def get_corp_codes(self):
        """
        DART에서 기업 고유번호 목록을 다운로드하고 파싱합니다.
        """
        print("\n" + "="*60)
        print("Downloading DART Corp Codes")
        print("="*60)

        try:
            # Download corp code XML (ZIP format) with API key
            params = {'crtfc_key': self.api_key}
            response = requests.get(config.DART_CORP_CODE_URL, params=params, timeout=30)
            response.raise_for_status()

            print(f"Downloaded: {len(response.content)} bytes")

            # Check if response is an error message
            if len(response.content) < 1000:
                try:
                    error_text = response.content.decode('utf-8')
                    print(f"API Response: {error_text}")
                except:
                    pass

            # Extract ZIP file
            with zipfile.ZipFile(BytesIO(response.content)) as z:
                xml_filename = z.namelist()[0]
                xml_content = z.read(xml_filename)

            print(f"Extracted: {xml_filename}")

            # Parse XML
            root = ET.fromstring(xml_content)

            # Find target companies
            for company_name, expected_stock_code in config.COMPANIES.items():
                found = False
                for corp in root.findall('.//list'):
                    corp_name = corp.find('corp_name').text
                    stock_code = corp.find('stock_code').text if corp.find('stock_code') is not None else ''

                    # Match by stock code (more accurate) or by exact company name
                    if (stock_code and stock_code.strip() == expected_stock_code) or \
                       (corp_name and corp_name.strip() == company_name):
                        corp_code = corp.find('corp_code').text
                        self.corp_codes[company_name] = {
                            'corp_code': corp_code,
                            'stock_code': stock_code.strip() if stock_code else '',
                            'corp_name': corp_name
                        }
                        print(f"  [OK] {company_name}: {corp_code} (종목코드: {stock_code.strip() if stock_code else 'N/A'})")
                        found = True
                        break

                if not found:
                    print(f"  [WARN] {company_name}: Not found")

            print("="*60)
            return self.corp_codes

        except Exception as e:
            print(f"[ERROR] Failed to get corp codes: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def get_date_range(self):
        """Get date range for searching (last N days)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=config.CRAWL_DATE_RANGE_DAYS)
        return start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')

    def search_reports(self, company_name, corp_code):
        """
        특정 회사의 사업보고서를 검색합니다.

        Args:
            company_name: 회사명
            corp_code: DART 고유번호 (8자리)
        """
        print("\n" + "="*60)
        print(f"Searching DART Reports for {company_name}")
        print("="*60)

        start_date, end_date = self.get_date_range()
        print(f"Date range: {start_date} ~ {end_date}")
        print(f"Corp code: {corp_code}")

        all_reports = []

        # Search each report type
        for report_name, report_code in config.DART_REPORT_TYPES.items():
            print(f"\nSearching {report_name} ({report_code})...")

            try:
                # Build API request
                params = {
                    'crtfc_key': self.api_key,
                    'corp_code': corp_code,
                    'bgn_de': start_date,
                    'end_de': end_date,
                    'pblntf_detail_ty': report_code,
                    'page_count': 100
                }

                url = f"{self.base_url}/list.json"
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                # Check status
                if data.get('status') != '000':
                    print(f"  [WARN] API Error: {data.get('message')}")
                    continue

                # Get reports
                reports = data.get('list', [])

                if not reports:
                    print(f"  No {report_name} found")
                    continue

                print(f"  Found {len(reports)} {report_name}")

                # Add report type to each report
                for report in reports:
                    report['report_type'] = report_name
                    report['report_type_code'] = report_code
                    all_reports.append(report)

                    # Print first few reports
                    if len([r for r in all_reports if r['report_type'] == report_name]) <= 3:
                        print(f"    - {report['rcept_dt']}: {report['report_nm']}")

            except Exception as e:
                print(f"  [ERROR] Failed to search {report_name}: {str(e)}")
                continue

        print(f"\n{'='*60}")
        print(f"Total reports found: {len(all_reports)}")
        for report_name in config.DART_REPORT_TYPES.keys():
            count = len([r for r in all_reports if r['report_type'] == report_name])
            print(f"  {report_name}: {count}")
        print("="*60)

        # Save reports metadata
        self.save_reports(company_name, all_reports)

        return all_reports

    def save_reports(self, company_name, reports):
        """Save DART reports metadata to JSON file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{config.RAW_DIR}/{company_name}_DART_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        print(f"\nSaved metadata: {filename}")

    def crawl_all_companies(self):
        """Crawl DART reports for all configured companies"""
        # First, get corp codes
        corp_codes = self.get_corp_codes()

        if not corp_codes:
            print("[ERROR] No corp codes found. Cannot proceed.")
            return {}

        all_reports = {}

        # Search reports for each company
        for company_name in config.COMPANIES.keys():
            if company_name not in corp_codes:
                print(f"[WARN] Corp code not found for {company_name}, skipping...")
                continue

            try:
                corp_code = corp_codes[company_name]['corp_code']
                reports = self.search_reports(company_name, corp_code)
                all_reports[company_name] = reports

            except Exception as e:
                print(f"[ERROR] Failed to crawl {company_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        return all_reports


def main():
    """Main function to run the DART crawler"""
    import time
    start_time = time.time()

    print("="*60)
    print("DART API Crawler")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Companies: {', '.join(config.COMPANIES.keys())}")
    print(f"Date range: Last {config.CRAWL_DATE_RANGE_DAYS} days")
    print(f"Report types: {', '.join(config.DART_REPORT_TYPES.keys())}")
    print("="*60)

    crawler = DartCrawler()

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
            for report_name in config.DART_REPORT_TYPES.keys():
                count = len([r for r in reports if r['report_type'] == report_name])
                if count > 0:
                    print(f"  - {report_name}: {count}")
        print("="*60)
        print(f"Total time: {minutes}m {seconds}s")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print("\n[OK] DART crawling completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Error during crawling: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
