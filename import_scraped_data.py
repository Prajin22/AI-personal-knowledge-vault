#!/usr/bin/env python3
"""
Import Scraped Data into AI Knowledge Base
Adds scraped content to the knowledge base system
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict
import logging

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.note_manager import NoteManager
from services.vector_store import VectorStore
from services.summarizer import Summarizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataImporter:
    """Import scraped data into the knowledge base"""

    def __init__(self):
        # Initialize services
        self.vector_store = VectorStore()
        self.summarizer = Summarizer()
        self.note_manager = NoteManager(self.vector_store, self.summarizer)

        # Data directories
        self.scraped_data_dir = Path("scraped_data")
        self.import_file = self.scraped_data_dir / "knowledge_base_import.json"

    def load_import_data(self) -> List[Dict]:
        """Load the scraped data ready for import"""
        if not self.import_file.exists():
            logger.error(f"Import file not found: {self.import_file}")
            logger.info("Run data_scraper.py first to generate scraped data")
            return []

        try:
            with open(self.import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} items for import")
                return data
        except Exception as e:
            logger.error(f"Error loading import data: {e}")
            return []

    def validate_import_item(self, item: Dict) -> bool:
        """Validate that an import item has required fields"""
        required_fields = ['title', 'content']

        for field in required_fields:
            if field not in item or not item[field].strip():
                logger.warning(f"Item missing required field '{field}': {item.get('title', 'Unknown')}")
                return False

        # Check content quality
        content = item['content']
        if len(content) < 100:
            logger.warning(f"Content too short for '{item['title']}' ({len(content)} chars)")
            return False

        if len(content) > 50000:
            logger.warning(f"Content too long for '{item['title']}' ({len(content)} chars)")
            # Truncate long content
            item['content'] = content[:50000] + "... [content truncated]"

        return True

    def deduplicate_content(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar content"""
        seen_titles = set()
        seen_content_hashes = set()
        unique_items = []

        for item in items:
            title = item['title'].strip().lower()
            content = item['content'].strip()

            # Simple content hash (first 500 chars)
            content_hash = hash(content[:500])

            # Skip if title or content hash already seen
            if title in seen_titles or content_hash in seen_content_hashes:
                logger.debug(f"Skipping duplicate: {item['title']}")
                continue

            seen_titles.add(title)
            seen_content_hashes.add(content_hash)
            unique_items.append(item)

        logger.info(f"Removed {len(items) - len(unique_items)} duplicates")
        return unique_items

    def categorize_content(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize content by type and quality"""
        categories = {
            'high_quality': [],
            'medium_quality': [],
            'educational': [],
            'research': [],
            'code': [],
            'documentation': []
        }

        for item in items:
            # Determine category based on metadata and content
            source_type = item.get('metadata', {}).get('source_type', '')
            quality_score = item.get('metadata', {}).get('quality_score', 0.5)

            # Categorize by type
            if source_type == 'research_paper':
                categories['research'].append(item)
            elif source_type in ['code_repository', 'github']:
                categories['code'].append(item)
            elif source_type == 'documentation':
                categories['documentation'].append(item)
            elif quality_score > 0.7:
                categories['high_quality'].append(item)
            elif quality_score > 0.4:
                categories['medium_quality'].append(item)
            else:
                categories['educational'].append(item)

        # Log category counts
        for category, items_list in categories.items():
            if items_list:
                logger.info(f"{category}: {len(items_list)} items")

        return categories

    def import_batch(self, items: List[Dict], batch_size: int = 10, dry_run: bool = False) -> Dict:
        """Import items in batches to avoid overwhelming the system"""
        results = {
            'total_attempted': len(items),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1} ({len(batch)} items)")

            for item in batch:
                try:
                    if not self.validate_import_item(item):
                        results['skipped'] += 1
                        continue

                    if dry_run:
                        logger.info(f"[DRY RUN] Would import: {item['title']}")
                        results['successful'] += 1
                        continue

                    # Create the note
                    note_data = {
                        'title': item['title'],
                        'content': item['content'],
                        'tags': item.get('tags', []),
                        'category': item.get('category', 'Educational'),
                        'metadata': item.get('metadata', {})
                    }

                    note_id = self.note_manager.create_note(**note_data)

                    if note_id:
                        logger.info(f"✓ Imported: {item['title']}")
                        results['successful'] += 1
                    else:
                        logger.warning(f"✗ Failed to import: {item['title']}")
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Error importing '{item.get('title', 'Unknown')}': {e}")
                    results['errors'].append(str(e))
                    results['failed'] += 1

        return results

    def run_import_pipeline(self, dry_run: bool = True, batch_size: int = 5) -> Dict:
        """Run the complete import pipeline"""
        logger.info("🚀 Starting data import pipeline...")
        logger.info(f"Dry run mode: {dry_run}")

        # Load data
        import_data = self.load_import_data()
        if not import_data:
            return {'error': 'No import data found'}

        # Deduplicate
        unique_data = self.deduplicate_content(import_data)

        # Categorize
        categories = self.categorize_content(unique_data)

        # Import by priority (high quality first)
        import_order = ['high_quality', 'research', 'documentation', 'educational', 'medium_quality', 'code']
        all_results = {}

        for category in import_order:
            if category in categories and categories[category]:
                logger.info(f"\n📂 Importing category: {category} ({len(categories[category])} items)")
                results = self.import_batch(categories[category], batch_size, dry_run)
                all_results[category] = results

                # Log results
                logger.info(f"  ✅ Successful: {results['successful']}")
                logger.info(f"  ❌ Failed: {results['failed']}")
                logger.info(f"  ⏭️  Skipped: {results['skipped']}")

        # Summary
        total_successful = sum(r['successful'] for r in all_results.values())
        total_failed = sum(r['failed'] for r in all_results.values())
        total_skipped = sum(r['skipped'] for r in all_results.values())

        summary = {
            'total_input': len(import_data),
            'after_deduplication': len(unique_data),
            'successful_imports': total_successful,
            'failed_imports': total_failed,
            'skipped_imports': total_skipped,
            'dry_run': dry_run,
            'category_results': all_results
        }

        logger.info("\n" + "=" * 60)
        logger.info("📊 IMPORT SUMMARY:")
        logger.info(f"📥 Input items: {summary['total_input']}")
        logger.info(f"🔄 After deduplication: {summary['after_deduplication']}")
        logger.info(f"✅ Successfully imported: {summary['successful_imports']}")
        logger.info(f"❌ Failed imports: {summary['failed_imports']}")
        logger.info(f"⏭️  Skipped: {summary['skipped_imports']}")

        if dry_run:
            logger.info("\n🔍 This was a DRY RUN - no data was actually imported")
            logger.info("Run with dry_run=False to perform actual import:")
            logger.info("python import_scraped_data.py --no-dry-run")

        return summary

def main():
    """Main import function"""
    import argparse

    parser = argparse.ArgumentParser(description='Import scraped data into AI knowledge base')
    parser.add_argument('--no-dry-run', action='store_true', help='Actually perform the import (default is dry run)')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of items to import per batch')
    parser.add_argument('--category', type=str, help='Import only specific category')

    args = parser.parse_args()

    dry_run = not args.no_dry_run

    print("📥 AI Knowledge Base Data Import")
    print("=" * 50)
    print(f"Mode: {'DRY RUN (safe)' if dry_run else 'LIVE IMPORT (will add data)'}")
    print(f"Batch size: {args.batch_size}")
    print()

    if not dry_run:
        print("⚠️  WARNING: This will add data to your knowledge base!")
        confirm = input("Are you sure you want to proceed? (type 'yes' to continue): ")
        if confirm.lower() != 'yes':
            print("Import cancelled.")
            return

    try:
        importer = DataImporter()
        results = importer.run_import_pipeline(dry_run=dry_run, batch_size=args.batch_size)

        if results.get('error'):
            print(f"❌ Error: {results['error']}")
            return

        print("\n" + "=" * 50)
        print("🎉 Import process completed!")

        if dry_run:
            print("\n🔍 DRY RUN RESULTS:")
            print(f"Would import {results['after_deduplication']} unique items")
            print(f"Estimated success rate: {results['successful_imports']/max(1, results['successful_imports']+results['failed_imports'])*100:.1f}%")
            print("\n💡 To perform actual import, run:")
            print("python import_scraped_data.py --no-dry-run")

        else:
            print("
✅ LIVE IMPORT COMPLETED:"            print(f"Successfully imported: {results['successful_imports']} items")
            print(f"Failed: {results['failed_imports']} items")
            print(f"Skipped: {results['skipped_imports']} items")

            if results['successful_imports'] > 0:
                print("\n🎯 Next steps:")
                print("1. Restart your Flask app to refresh the knowledge base")
                print("2. Test AI accuracy with: python evaluate_accuracy.py")
                print("3. Ask questions to verify improvements")

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
