"""
DART 원문 공시 문서 다운로드
메타데이터 JSON 파일에서 접수번호를 읽어 원문 문서를 다운로드합니다.
"""

import os
import json
import glob
import requests
import zipfile
from io import BytesIO
from datetime import datetime
import time
import config


class DartDocumentDownloader:
    def __init__(self):
        self.api_key = config.DART_API_KEY
        self.document_url = config.DART_DOCUMENT_URL
        self.docs_dir = config.DART_DIR
        self.setup_directories()

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.docs_dir, exist_ok=True)
        print(f"Documents will be saved to: {os.path.abspath(self.docs_dir)}")

    def load_dart_metadata(self, company_name):
        """
        Load DART metadata JSON file for a company

        Args:
            company_name: 회사명 (e.g., "LG전자", "삼성전자")

        Returns:
            list: 리포트 메타데이터 리스트
        """
        pattern = f"{config.RAW_DIR}/{company_name}_DART_*.json"
        files = glob.glob(pattern)

        if not files:
            print(f"[WARN] No DART metadata found for {company_name}")
            return []

        # Get the latest file
        latest_file = sorted(files)[-1]
        print(f"Loading metadata: {os.path.basename(latest_file)}")

        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data

    def download_document(self, company_name, report):
        """
        Download original DART document (ZIP file)

        Args:
            company_name: 회사명
            report: 리포트 메타데이터 dict

        Returns:
            str: 다운로드된 파일 경로 또는 None
        """
        rcept_no = report.get('rcept_no')
        report_type = report.get('report_type', 'Unknown')
        report_nm = report.get('report_nm', 'Unknown')

        if not rcept_no:
            print(f"  [SKIP] No rcept_no found")
            return None

        # Create filename
        safe_report_type = report_type.replace(' ', '_')
        filename = f"{company_name}_{rcept_no}_{safe_report_type}.zip"
        filepath = os.path.join(self.docs_dir, filename)

        # Skip if already exists
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  [SKIP] Already exists: {filename} ({file_size_mb:.2f} MB)")
            return filepath

        # Download document
        try:
            print(f"  Downloading: {report_nm}")
            print(f"    rcept_no: {rcept_no}")

            params = {
                'crtfc_key': self.api_key,
                'rcept_no': rcept_no
            }

            response = requests.get(self.document_url, params=params, timeout=60)
            response.raise_for_status()

            # Check if response is ZIP file
            content_type = response.headers.get('Content-Type', '')
            if 'zip' not in content_type and 'application' not in content_type:
                # Might be error message in XML
                print(f"    [ERROR] Unexpected content type: {content_type}")
                print(f"    Response (first 200 chars): {response.text[:200]}")
                return None

            # Save ZIP file
            with open(filepath, 'wb') as f:
                f.write(response.content)

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"    [OK] Downloaded: {file_size_mb:.2f} MB")

            # Extract ZIP file to subfolder
            extract_dir = os.path.join(self.docs_dir, f"{company_name}_{rcept_no}")
            if not os.path.exists(extract_dir):
                try:
                    with zipfile.ZipFile(filepath, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    print(f"    [OK] Extracted to: {os.path.basename(extract_dir)}")
                except zipfile.BadZipFile:
                    print(f"    [WARN] Not a valid ZIP file, keeping as-is")

            return filepath

        except requests.exceptions.RequestException as e:
            print(f"    [ERROR] Download failed: {str(e)}")
            return None
        except Exception as e:
            print(f"    [ERROR] Unexpected error: {str(e)}")
            return None

    def download_company_documents(self, company_name):
        """
        Download all DART documents for a company

        Args:
            company_name: 회사명

        Returns:
            dict: 다운로드 결과 통계
        """
        print("\n" + "="*60)
        print(f"Downloading DART Documents for {company_name}")
        print("="*60)

        # Load metadata
        reports = self.load_dart_metadata(company_name)

        if not reports:
            return {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

        print(f"Found {len(reports)} reports\n")

        stats = {
            "total": len(reports),
            "downloaded": 0,
            "skipped": 0,
            "failed": 0
        }

        # Download each document
        for idx, report in enumerate(reports, 1):
            print(f"[{idx}/{len(reports)}] {report.get('report_type', 'Unknown')}")

            result = self.download_document(company_name, report)

            if result:
                if "Already exists" in str(result):
                    stats["skipped"] += 1
                else:
                    stats["downloaded"] += 1
            else:
                stats["failed"] += 1

            # Be polite to API
            time.sleep(1)

        print(f"\n{'='*60}")
        print(f"Download Summary for {company_name}")
        print(f"{'='*60}")
        print(f"Total reports:  {stats['total']}")
        print(f"Downloaded:     {stats['downloaded']}")
        print(f"Skipped:        {stats['skipped']}")
        print(f"Failed:         {stats['failed']}")
        print(f"{'='*60}")

        return stats

    def download_all_companies(self):
        """Download DART documents for all companies"""
        all_stats = {}

        for company_name in config.COMPANIES.keys():
            try:
                stats = self.download_company_documents(company_name)
                all_stats[company_name] = stats
                time.sleep(2)  # Wait between companies
            except Exception as e:
                print(f"[ERROR] Failed to download documents for {company_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        return all_stats


def main():
    """Main function"""
    import time
    start_time = time.time()

    print("="*60)
    print("DART Document Downloader")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Companies: {', '.join(config.COMPANIES.keys())}")
    print("="*60)

    downloader = DartDocumentDownloader()

    try:
        all_stats = downloader.download_all_companies()

        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        for company, stats in all_stats.items():
            print(f"\n{company}:")
            print(f"  Downloaded: {stats['downloaded']}")
            print(f"  Skipped:    {stats['skipped']}")
            print(f"  Failed:     {stats['failed']}")

            total_downloaded += stats['downloaded']
            total_skipped += stats['skipped']
            total_failed += stats['failed']

        print(f"\n{'='*60}")
        print(f"Overall Total:")
        print(f"  Downloaded: {total_downloaded}")
        print(f"  Skipped:    {total_skipped}")
        print(f"  Failed:     {total_failed}")
        print(f"{'='*60}")
        print(f"Total time: {minutes}m {seconds}s")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print("\n[OK] Download completed!")

    except Exception as e:
        print(f"\n[ERROR] Error during download: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
