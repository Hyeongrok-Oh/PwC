"""
텍스트 추출 파이프라인
PDF (한경 컨센서스)와 XML (DART)에서 텍스트를 추출합니다.
"""

import os
import json
import glob
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import re
import config

try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber not installed. Run: pip install pdfplumber")
    exit(1)

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False
    print("[WARN] lxml not available, will use standard XML parser")


class TextExtractor:
    def __init__(self):
        self.setup_directories()
        self.stats = {
            'consensus': {'total': 0, 'success': 0, 'failed': 0},
            'dart': {'total': 0, 'success': 0, 'failed': 0}
        }

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(config.EXTRACTED_DIR, exist_ok=True)
        os.makedirs(config.EXTRACTED_CONSENSUS_DIR, exist_ok=True)
        os.makedirs(config.EXTRACTED_DART_DIR, exist_ok=True)
        print(f"Output directory: {os.path.abspath(config.EXTRACTED_DIR)}")

    def extract_pdf_text(self, pdf_path):
        """
        Extract text and tables from PDF using pdfplumber

        Args:
            pdf_path: Path to PDF file

        Returns:
            dict: Extracted content with text, tables, and metadata
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract filename components
                filename = os.path.basename(pdf_path)
                parts = filename.replace('.pdf', '').split('_')

                company = parts[0] if len(parts) > 0 else "Unknown"
                date_str = parts[1] if len(parts) > 1 else ""

                # Format date
                if len(date_str) == 8:
                    date = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                else:
                    date = date_str

                # Extract text from each page
                pages_text = {}
                all_text = []
                all_tables = []

                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        pages_text[f"page_{page_num}"] = page_text
                        all_text.append(page_text)

                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            all_tables.append({
                                'page': page_num,
                                'table_index': table_idx,
                                'data': table
                            })

                # Combine all text
                full_text = "\n\n".join(all_text)

                result = {
                    'source': 'consensus',
                    'filename': filename,
                    'company': company,
                    'date': date,
                    'page_count': len(pdf.pages),
                    'text': full_text,
                    'pages': pages_text,
                    'tables': all_tables,
                    'char_count': len(full_text),
                    'extracted_at': datetime.now().isoformat()
                }

                return result

        except Exception as e:
            print(f"    [ERROR] Failed to extract: {str(e)}")
            return None

    def extract_xml_text(self, zip_path):
        """
        Extract text and data from DART XML files

        Args:
            zip_path: Path to ZIP file containing XML documents

        Returns:
            dict: Extracted content from main document and audit reports
        """
        try:
            # Extract filename components
            filename = os.path.basename(zip_path)
            parts = filename.replace('.zip', '').split('_')

            company = parts[0] if len(parts) > 0 else "Unknown"
            rcept_no = parts[1] if len(parts) > 1 else ""
            report_type = parts[2] if len(parts) > 2 else ""

            results = []

            with zipfile.ZipFile(zip_path, 'r') as z:
                xml_files = [f for f in z.namelist() if f.endswith('.xml')]

                for xml_file in xml_files:
                    with z.open(xml_file) as f:
                        try:
                            # Use lxml with recovery mode if available
                            if LXML_AVAILABLE:
                                parser = etree.XMLParser(recover=True, encoding='utf-8')
                                content = f.read()
                                root = etree.fromstring(content, parser=parser)
                            else:
                                tree = ET.parse(f)
                                root = tree.getroot()

                            # Determine document type
                            is_main_doc = not any(x in xml_file for x in ['_00760', '_00761'])
                            doc_type = 'main' if is_main_doc else 'audit'

                            # Extract text from BODY section (main document)
                            text_parts = []

                            if is_main_doc:
                                # Extract all text from P tags and TD tags
                                for elem in root.iter():
                                    tag = elem.tag if not isinstance(elem.tag, str) else elem.tag
                                    if isinstance(tag, str):
                                        if tag == 'P' or tag == 'TD':
                                            if elem.text:
                                                text_parts.append(elem.text.strip())
                                        # Also check for text in SECTION elements
                                        elif 'SECTION' in tag and elem.text:
                                            text_parts.append(elem.text.strip())

                            # Extract SUMMARY data (all documents)
                            summary_data = {}
                            if LXML_AVAILABLE:
                                summary_list = root.xpath('.//SUMMARY')
                                if summary_list:
                                    summary = summary_list[0]
                                    for extraction in summary.xpath('.//EXTRACTION'):
                                        acode = extraction.get('ACODE', '')
                                        value = extraction.text if extraction.text else ''
                                        if acode:
                                            summary_data[acode] = value
                            else:
                                summary = root.find('.//SUMMARY')
                                if summary is not None:
                                    for extraction in summary.findall('EXTRACTION'):
                                        acode = extraction.get('ACODE', '')
                                        value = extraction.text if extraction.text else ''
                                        if acode:
                                            summary_data[acode] = value

                            # Extract metadata
                            if LXML_AVAILABLE:
                                doc_name_list = root.xpath('.//DOCUMENT-NAME')
                                doc_name = doc_name_list[0].text if doc_name_list and doc_name_list[0].text else report_type
                                company_list = root.xpath('.//COMPANY-NAME')
                                company_name = company_list[0].text if company_list and company_list[0].text else company
                            else:
                                doc_name_elem = root.find('.//DOCUMENT-NAME')
                                doc_name = doc_name_elem.text if doc_name_elem is not None else report_type
                                company_elem = root.find('.//COMPANY-NAME')
                                company_name = company_elem.text if company_elem is not None else company

                            full_text = "\n".join([t for t in text_parts if t])

                            result = {
                                'source': 'dart',
                                'document_type': doc_type,
                                'filename': xml_file,
                                'zip_file': filename,
                                'rcept_no': rcept_no,
                                'company': company_name,
                                'report_type': doc_name,
                                'text': full_text,
                                'char_count': len(full_text),
                                'summary_data': summary_data,
                                'extracted_at': datetime.now().isoformat()
                            }

                            results.append(result)

                        except ET.ParseError as e:
                            print(f"    [WARN] XML parse error in {xml_file}: {str(e)}")
                            continue

            return results if results else None

        except Exception as e:
            print(f"    [ERROR] Failed to extract: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def process_consensus_pdfs(self):
        """Process all PDF files from consensus directory"""
        print("\n" + "="*60)
        print("Extracting Text from Consensus PDFs")
        print("="*60)

        pdf_files = glob.glob(f"{config.CONSENSUS_DIR}/*.pdf")
        self.stats['consensus']['total'] = len(pdf_files)

        if not pdf_files:
            print("[WARN] No PDF files found")
            return

        print(f"Found {len(pdf_files)} PDF files\n")

        for idx, pdf_path in enumerate(pdf_files, 1):
            filename = os.path.basename(pdf_path)
            print(f"[{idx}/{len(pdf_files)}] {filename}")

            # Check if already extracted
            output_name = filename.replace('.pdf', '_text.json')
            output_path = os.path.join(config.EXTRACTED_CONSENSUS_DIR, output_name)

            if os.path.exists(output_path):
                print(f"  [SKIP] Already extracted")
                self.stats['consensus']['success'] += 1
                continue

            # Extract text
            result = self.extract_pdf_text(pdf_path)

            if result:
                # Save result
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                self.stats['consensus']['success'] += 1
                print(f"  [OK] Extracted: {result['char_count']} chars, {result['page_count']} pages")
            else:
                self.stats['consensus']['failed'] += 1

        print(f"\n{'='*60}")
        print(f"Consensus PDF Summary")
        print(f"{'='*60}")
        print(f"Total:   {self.stats['consensus']['total']}")
        print(f"Success: {self.stats['consensus']['success']}")
        print(f"Failed:  {self.stats['consensus']['failed']}")
        print(f"{'='*60}")

    def process_dart_xmls(self):
        """Process all XML files from DART ZIP archives"""
        print("\n" + "="*60)
        print("Extracting Text from DART XML Documents")
        print("="*60)

        zip_files = glob.glob(f"{config.DART_DIR}/*.zip")
        self.stats['dart']['total'] = len(zip_files)

        if not zip_files:
            print("[WARN] No ZIP files found")
            return

        print(f"Found {len(zip_files)} ZIP files\n")

        for idx, zip_path in enumerate(zip_files, 1):
            filename = os.path.basename(zip_path)
            print(f"[{idx}/{len(zip_files)}] {filename}")

            # Extract rcept_no from filename
            parts = filename.replace('.zip', '').split('_')
            rcept_no = parts[1] if len(parts) > 1 else filename.replace('.zip', '')

            # Check if already extracted
            output_name = f"{rcept_no}_extracted.json"
            output_path = os.path.join(config.EXTRACTED_DART_DIR, output_name)

            if os.path.exists(output_path):
                print(f"  [SKIP] Already extracted")
                self.stats['dart']['success'] += 1
                continue

            # Extract text
            results = self.extract_xml_text(zip_path)

            if results:
                # Save all results for this ZIP file
                combined_result = {
                    'zip_file': filename,
                    'rcept_no': rcept_no,
                    'documents': results,
                    'extracted_at': datetime.now().isoformat()
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(combined_result, f, ensure_ascii=False, indent=2)

                total_chars = sum(r['char_count'] for r in results)
                self.stats['dart']['success'] += 1
                print(f"  [OK] Extracted {len(results)} documents: {total_chars} total chars")
            else:
                self.stats['dart']['failed'] += 1

        print(f"\n{'='*60}")
        print(f"DART XML Summary")
        print(f"{'='*60}")
        print(f"Total:   {self.stats['dart']['total']}")
        print(f"Success: {self.stats['dart']['success']}")
        print(f"Failed:  {self.stats['dart']['failed']}")
        print(f"{'='*60}")

    def create_index(self):
        """Create an index of all extracted documents"""
        print("\n" + "="*60)
        print("Creating Index")
        print("="*60)

        index = {
            'created_at': datetime.now().isoformat(),
            'consensus': [],
            'dart': [],
            'statistics': self.stats
        }

        # Index consensus documents
        consensus_files = glob.glob(f"{config.EXTRACTED_CONSENSUS_DIR}/*_text.json")
        for file_path in consensus_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                index['consensus'].append({
                    'filename': data['filename'],
                    'company': data['company'],
                    'date': data['date'],
                    'page_count': data['page_count'],
                    'char_count': data['char_count'],
                    'extracted_file': os.path.basename(file_path)
                })

        # Index DART documents
        dart_files = glob.glob(f"{config.EXTRACTED_DART_DIR}/*_extracted.json")
        for file_path in dart_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                total_chars = sum(doc['char_count'] for doc in data['documents'])
                index['dart'].append({
                    'zip_file': data['zip_file'],
                    'rcept_no': data['rcept_no'],
                    'document_count': len(data['documents']),
                    'total_chars': total_chars,
                    'extracted_file': os.path.basename(file_path)
                })

        # Save index
        index_path = os.path.join(config.EXTRACTED_DIR, 'index.json')
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"Created index: {index_path}")
        print(f"  Consensus documents: {len(index['consensus'])}")
        print(f"  DART documents: {len(index['dart'])}")
        print("="*60)


def main():
    """Main function"""
    import time
    start_time = time.time()

    print("="*60)
    print("Text Extraction Pipeline")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    extractor = TextExtractor()

    try:
        # Process PDFs
        extractor.process_consensus_pdfs()

        # Process XMLs
        extractor.process_dart_xmls()

        # Create index
        extractor.create_index()

        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)

        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"Consensus PDFs:")
        print(f"  Success: {extractor.stats['consensus']['success']}/{extractor.stats['consensus']['total']}")
        print(f"  Failed:  {extractor.stats['consensus']['failed']}")
        print(f"\nDART XMLs:")
        print(f"  Success: {extractor.stats['dart']['success']}/{extractor.stats['dart']['total']}")
        print(f"  Failed:  {extractor.stats['dart']['failed']}")
        print(f"\n{'='*60}")
        print(f"Total time: {minutes}m {seconds}s")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print("\n[OK] Text extraction completed!")

    except Exception as e:
        print(f"\n[ERROR] Error during extraction: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
