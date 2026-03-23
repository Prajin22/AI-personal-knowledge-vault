#!/usr/bin/env python3
"""
AI Education Data Collection Pipeline
Collects high-quality educational content for AI/ML training
"""

import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import logging
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AcademicDataCollector:
    """Collect educational content from various academic sources"""

    def __init__(self, output_dir: str = "data/training_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_delay = 1.0  # seconds between requests

    def collect_arxiv_papers(self, categories: List[str] = ["cs.AI", "cs.LG", "stat.ML"],
                           max_papers: int = 1000) -> List[Dict]:
        """Collect AI/ML papers from arXiv"""
        logger.info(f"Collecting up to {max_papers} papers from arXiv...")

        papers = []
        base_url = "http://export.arxiv.org/api/query"

        for category in categories:
            query = f"cat:{category}"
            start = 0
            batch_size = 100

            while len(papers) < max_papers // len(categories):
                params = {
                    "search_query": query,
                    "start": start,
                    "max_results": batch_size,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }

                try:
                    response = requests.get(base_url, params=params)
                    response.raise_for_status()

                    # Parse XML response (simplified)
                    content = response.text
                    paper_entries = self._parse_arxiv_xml(content)

                    if not paper_entries:
                        break

                    papers.extend(paper_entries)
                    start += batch_size

                    time.sleep(self.rate_limit_delay)

                except Exception as e:
                    logger.error(f"Error collecting arXiv papers: {e}")
                    break

        return papers[:max_papers]

    def collect_course_materials(self) -> List[Dict]:
        """Collect course materials from educational platforms"""
        logger.info("Collecting course materials...")

        courses = []

        # MIT OpenCourseWare AI courses
        mit_courses = [
            {"id": "6.036", "title": "Introduction to Machine Learning", "url": "https://ocw.mit.edu/courses/6-036-introduction-to-machine-learning-fall-2020/"},
            {"id": "6.345", "title": "Automatic Speech Recognition", "url": "https://ocw.mit.edu/courses/6-345-automatic-speech-recognition-spring-2003/"},
            {"id": "6.844", "title": "Artificial Intelligence", "url": "https://ocw.mit.edu/courses/6-034-artificial-intelligence-fall-2010/"},
        ]

        for course in mit_courses:
            try:
                course_data = self._scrape_course_content(course)
                if course_data:
                    courses.append(course_data)
                time.sleep(self.rate_limit_delay)
            except Exception as e:
                logger.error(f"Error collecting course {course['id']}: {e}")

        return courses

    def collect_tutorial_content(self) -> List[Dict]:
        """Collect tutorials from educational websites"""
        logger.info("Collecting tutorial content...")

        tutorials = []

        # Machine Learning Mastery articles
        mlm_urls = [
            "https://machinelearningmastery.com/",
            "https://machinelearningmastery.com/start-here/",
        ]

        for url in mlm_urls:
            try:
                content = self._scrape_tutorial_site(url)
                if content:
                    tutorials.extend(content)
                time.sleep(self.rate_limit_delay * 2)  # Extra delay for respect
            except Exception as e:
                logger.error(f"Error collecting from {url}: {e}")

        return tutorials

    def collect_documentation(self) -> List[Dict]:
        """Collect official library documentation"""
        logger.info("Collecting library documentation...")

        docs = []

        # Key AI/ML libraries
        libraries = [
            {
                "name": "scikit-learn",
                "url": "https://scikit-learn.org/stable/user_guide.html",
                "type": "machine_learning"
            },
            {
                "name": "TensorFlow",
                "url": "https://www.tensorflow.org/guide",
                "type": "deep_learning"
            },
            {
                "name": "PyTorch",
                "url": "https://pytorch.org/tutorials/",
                "type": "deep_learning"
            }
        ]

        for lib in libraries:
            try:
                doc_content = self._scrape_documentation(lib)
                if doc_content:
                    docs.extend(doc_content)
                time.sleep(self.rate_limit_delay)
            except Exception as e:
                logger.error(f"Error collecting {lib['name']} docs: {e}")

        return docs

    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict]:
        """Parse arXiv XML response (simplified version)"""
        papers = []

        # Simple regex-based parsing (in production, use proper XML parser)
        entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)

        for entry in entries:
            try:
                title = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                abstract = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                authors = re.findall(r'<name>(.*?)</name>', entry)

                if title and abstract:
                    papers.append({
                        "title": self._clean_text(title.group(1)),
                        "abstract": self._clean_text(abstract.group(1)),
                        "authors": authors,
                        "source": "arxiv",
                        "type": "research_paper",
                        "collected_at": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.warning(f"Error parsing paper entry: {e}")
                continue

        return papers

    def _scrape_course_content(self, course: Dict) -> Optional[Dict]:
        """Scrape course content from educational platforms"""
        try:
            response = requests.get(course['url'], timeout=10)
            response.raise_for_status()

            # Extract text content (simplified)
            text_content = self._extract_text_from_html(response.text)

            return {
                "title": course['title'],
                "course_id": course['id'],
                "content": text_content[:5000],  # Limit content length
                "url": course['url'],
                "source": "mit_ocw",
                "type": "course_material",
                "collected_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error scraping course {course['id']}: {e}")
            return None

    def _scrape_tutorial_site(self, url: str) -> List[Dict]:
        """Scrape tutorial content from educational websites"""
        tutorials = []

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Extract article links and content
            article_links = re.findall(r'href="([^"]*article[^"]*)"', response.text)

            for link in article_links[:10]:  # Limit to 10 articles per site
                if not link.startswith('http'):
                    link = urljoin(url, link)

                try:
                    article_response = requests.get(link, timeout=10)
                    article_content = self._extract_text_from_html(article_response.text)

                    tutorials.append({
                        "title": self._extract_title_from_html(article_response.text),
                        "content": article_content[:3000],
                        "url": link,
                        "source": "tutorial_site",
                        "type": "tutorial",
                        "collected_at": datetime.now().isoformat()
                    })

                    time.sleep(self.rate_limit_delay)
                except Exception as e:
                    logger.warning(f"Error scraping article {link}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error scraping tutorial site {url}: {e}")

        return tutorials

    def _scrape_documentation(self, library: Dict) -> List[Dict]:
        """Scrape library documentation"""
        docs = []

        try:
            response = requests.get(library['url'], timeout=15)
            response.raise_for_status()

            # Extract main content sections
            content_sections = self._extract_doc_sections(response.text)

            for section in content_sections[:5]:  # Limit sections
                docs.append({
                    "title": section.get('title', f"{library['name']} Documentation"),
                    "content": section.get('content', '')[:4000],
                    "section": section.get('section', 'general'),
                    "library": library['name'],
                    "type": library['type'],
                    "source": "official_docs",
                    "collected_at": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Error scraping docs for {library['name']}: {e}")

        return docs

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Decode HTML entities
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return text.strip()

    def _extract_text_from_html(self, html: str) -> str:
        """Extract readable text from HTML"""
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

        # Extract text from common content tags
        content_tags = ['p', 'div', 'span', 'li', 'h1', 'h2', 'h3', 'h4']
        text_parts = []

        for tag in content_tags:
            matches = re.findall(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.IGNORECASE)
            for match in matches:
                clean_text = self._clean_text(match)
                if len(clean_text) > 20:  # Only meaningful text
                    text_parts.append(clean_text)

        return ' '.join(text_parts)

    def _extract_title_from_html(self, html: str) -> str:
        """Extract page title from HTML"""
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            return self._clean_text(title_match.group(1))
        return "Untitled Article"

    def _extract_doc_sections(self, html: str) -> List[Dict]:
        """Extract documentation sections"""
        sections = []

        # Look for common documentation patterns
        section_patterns = [
            r'<h[1-6][^>]*>(.*?)</h[1-6]>(.*?)(?=<h[1-6]|$)',
            r'<section[^>]*>.*?<h[1-6][^>]*>(.*?)</h[1-6]>(.*?)</section>',
        ]

        for pattern in section_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            for title, content in matches:
                sections.append({
                    'title': self._clean_text(title),
                    'content': self._clean_text(content),
                    'section': 'documentation'
                })

        return sections

    def collect_all_data(self) -> Dict[str, List[Dict]]:
        """Collect data from all sources"""
        logger.info("Starting comprehensive data collection...")

        data = {
            "research_papers": self.collect_arxiv_papers(max_papers=500),
            "course_materials": self.collect_course_materials(),
            "tutorials": self.collect_tutorial_content(),
            "documentation": self.collect_documentation()
        }

        # Save collected data
        self.save_data(data)

        # Generate statistics
        stats = self.generate_statistics(data)
        self.save_statistics(stats)

        logger.info("Data collection completed!")
        return data

    def save_data(self, data: Dict[str, List[Dict]]) -> None:
        """Save collected data to files"""
        for data_type, items in data.items():
            output_file = self.output_dir / f"{data_type}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(items)} {data_type} to {output_file}")

    def generate_statistics(self, data: Dict[str, List[Dict]]) -> Dict:
        """Generate collection statistics"""
        stats = {
            "collection_date": datetime.now().isoformat(),
            "total_items": sum(len(items) for items in data.values()),
            "categories": {}
        }

        for category, items in data.items():
            stats["categories"][category] = {
                "count": len(items),
                "sources": list(set(item.get("source", "unknown") for item in items)),
                "types": list(set(item.get("type", "unknown") for item in items))
            }

        return stats

    def save_statistics(self, stats: Dict) -> None:
        """Save collection statistics"""
        stats_file = self.output_dir / "collection_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Saved statistics to {stats_file}")


if __name__ == "__main__":
    collector = AcademicDataCollector()
    data = collector.collect_all_data()

    print("Data collection completed!")
    print(f"Collected {sum(len(items) for items in data.values())} total items")
