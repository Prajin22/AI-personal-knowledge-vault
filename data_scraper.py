#!/usr/bin/env python3
"""
Comprehensive AI/ML Data Scraping System
Scrapes high-quality content from multiple sources to improve AI knowledge base
"""

import requests
import json
import time
import re
import os
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, quote
from typing import List, Dict, Optional, Set
import hashlib
import random
from bs4 import BeautifulSoup
import feedparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import wikipediaapi
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIDataScraper:
    """Comprehensive scraper for AI/ML educational content"""

    def __init__(self, output_dir: str = "scraped_data", rate_limit: float = 2.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit  # seconds between requests
        self.last_request_time = 0
        self.session = self._create_session()

        # Track scraped URLs to avoid duplicates
        self.scraped_urls_file = self.output_dir / "scraped_urls.json"
        self.scraped_urls = self._load_scraped_urls()

        # Quality filters
        self.min_content_length = 500
        self.max_content_length = 50000
        self.required_keywords = ['artificial intelligence', 'machine learning', 'ai', 'ml', 'deep learning']

    def _create_session(self) -> requests.Session:
        """Create a session with proper headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session

    def _load_scraped_urls(self) -> Set[str]:
        """Load previously scraped URLs to avoid duplicates"""
        if self.scraped_urls_file.exists():
            try:
                with open(self.scraped_urls_file, 'r') as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_scraped_urls(self):
        """Save scraped URLs to avoid future duplicates"""
        with open(self.scraped_urls_file, 'w') as f:
            json.dump(list(self.scraped_urls), f, indent=2)

    def _rate_limit(self):
        """Implement rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _is_relevant_content(self, content: str, title: str) -> bool:
        """Check if content is relevant to AI/ML"""
        content_lower = content.lower()
        title_lower = title.lower()

        # Check for AI/ML keywords in title or content
        ai_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
            'computer vision', 'natural language processing', 'reinforcement learning',
            'supervised learning', 'unsupervised learning', 'data science', 'ai', 'ml'
        ]

        title_relevant = any(keyword in title_lower for keyword in ai_keywords)
        content_relevant = any(keyword in content_lower for keyword in ai_keywords)

        return title_relevant or content_relevant

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        if not content:
            return ""

        # Remove excessive whitespace
        content = re.sub(r'\n+', '\n', content)
        content = re.sub(r'\s+', ' ', content)

        # Remove common noise patterns
        content = re.sub(r'©.*?\d{4}', '', content)  # Copyright notices
        content = re.sub(r'All rights reserved\.?', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Cookie Policy|Privacy Policy|Terms of Service', '', content, flags=re.IGNORECASE)

        # Remove navigation and menu items
        content = re.sub(r'\b(Home|About|Contact|Blog|News|Menu|Navigation)\b', '', content, flags=re.IGNORECASE)

        return content.strip()

    def scrape_arxiv_papers(self, max_papers: int = 100) -> List[Dict]:
        """Scrape AI/ML papers from arXiv"""
        logger.info(f"Scraping up to {max_papers} AI/ML papers from arXiv...")

        papers = []
        base_url = "http://export.arxiv.org/api/query"

        categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE", "stat.ML"]
        papers_per_category = max_papers // len(categories)

        for category in categories:
            logger.info(f"Scraping category: {category}")

            for start in range(0, papers_per_category, 100):
                params = {
                    "search_query": f"cat:{category}",
                    "start": start,
                    "max_results": min(100, papers_per_category - start),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }

                try:
                    self._rate_limit()
                    response = self.session.get(base_url, params=params, timeout=30)

                    if response.status_code == 200:
                        papers.extend(self._parse_arxiv_xml(response.text))
                    else:
                        logger.warning(f"Failed to fetch arXiv data for {category}: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error scraping arXiv {category}: {e}")

                if len(papers) >= max_papers:
                    break

            if len(papers) >= max_papers:
                break

        # Save papers
        self._save_data(papers, "arxiv_papers.json")
        logger.info(f"Scraped {len(papers)} papers from arXiv")
        return papers

    def _parse_arxiv_xml(self, xml_content: str) -> List[Dict]:
        """Parse arXiv XML response"""
        papers = []
        # Simple XML parsing (in production, use proper XML parser)
        entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)

        for entry in entries:
            try:
                title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                authors_match = re.findall(r'<name>(.*?)</name>', entry)
                link_match = re.search(r'<id>(.*?)</id>', entry)

                if title_match and summary_match:
                    title = self._clean_html(title_match.group(1))
                    summary = self._clean_html(summary_match.group(1))

                    if len(summary) > 200 and self._is_relevant_content(summary, title):
                        paper = {
                            'title': title,
                            'content': summary,
                            'authors': authors_match,
                            'url': link_match.group(1) if link_match else '',
                            'source': 'arxiv',
                            'scraped_at': datetime.now().isoformat(),
                            'type': 'research_paper'
                        }
                        papers.append(paper)

            except Exception as e:
                logger.warning(f"Error parsing arXiv entry: {e}")

        return papers

    def scrape_wikipedia_articles(self, topics: List[str]) -> List[Dict]:
        """Scrape comprehensive Wikipedia articles"""
        logger.info(f"Scraping {len(topics)} Wikipedia articles...")

        articles = []
        wiki_wiki = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent='AI Knowledge Scraper/1.0 (Educational Research)'
        )

        for topic in topics:
            try:
                logger.info(f"Scraping Wikipedia: {topic}")
                page = wiki_wiki.page(topic)

                if page.exists() and len(page.text) > 1000:
                    # Split long articles into sections
                    sections = self._split_wikipedia_content(page.text, page.title)

                    for section_title, section_content in sections.items():
                        if len(section_content) > 500:
                            article = {
                                'title': f"{page.title} - {section_title}",
                                'content': section_content,
                                'url': page.fullurl,
                                'section': section_title,
                                'source': 'wikipedia',
                                'scraped_at': datetime.now().isoformat(),
                                'type': 'educational_content'
                            }
                            articles.append(article)

                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"Error scraping Wikipedia {topic}: {e}")

        self._save_data(articles, "wikipedia_articles.json")
        logger.info(f"Scraped {len(articles)} Wikipedia sections")
        return articles

    def _split_wikipedia_content(self, content: str, title: str) -> Dict[str, str]:
        """Split Wikipedia content into logical sections"""
        sections = {}

        # Split by section headers (== Section ==)
        section_pattern = r'(==+)\s*([^=]+)\s*\1'
        parts = re.split(section_pattern, content)

        current_section = "Introduction"
        current_content = ""

        for i, part in enumerate(parts):
            if i % 3 == 0:  # Content part
                current_content += part
            elif i % 3 == 2:  # Section title
                if current_content.strip():
                    sections[current_section] = current_content.strip()
                current_section = part.strip()
                current_content = ""

        # Add the last section
        if current_content.strip():
            sections[current_section] = current_content.strip()

        return sections

    def scrape_tech_blogs(self, sources: List[Dict]) -> List[Dict]:
        """Scrape articles from tech blogs and news sites"""
        logger.info(f"Scraping {len(sources)} tech blog sources...")

        articles = []

        for source in sources:
            try:
                logger.info(f"Scraping {source['name']}")

                if 'rss_url' in source:
                    # RSS feed scraping
                    articles.extend(self._scrape_rss_feed(source))
                else:
                    # Website scraping
                    articles.extend(self._scrape_website(source))

                time.sleep(2)  # Rate limiting between sources

            except Exception as e:
                logger.error(f"Error scraping {source.get('name', 'unknown source')}: {e}")

        self._save_data(articles, "tech_blog_articles.json")
        logger.info(f"Scraped {len(articles)} blog articles")
        return articles

    def _scrape_rss_feed(self, source: Dict) -> List[Dict]:
        """Scrape articles from RSS feed"""
        articles = []

        try:
            feed = feedparser.parse(source['rss_url'])

            for entry in feed.entries[:20]:  # Limit articles per feed
                title = getattr(entry, 'title', '').strip()
                content = getattr(entry, 'content', [{}])[0].get('value', '')
                if not content:
                    content = getattr(entry, 'summary', '')

                content = self._clean_html(content)

                if (len(content) > self.min_content_length and
                    len(content) < self.max_content_length and
                    self._is_relevant_content(content, title)):

                    article = {
                        'title': title,
                        'content': content,
                        'url': getattr(entry, 'link', ''),
                        'source': source['name'],
                        'published': getattr(entry, 'published', datetime.now().isoformat()),
                        'scraped_at': datetime.now().isoformat(),
                        'type': 'blog_article'
                    }
                    articles.append(article)

        except Exception as e:
            logger.error(f"Error parsing RSS feed {source['name']}: {e}")

        return articles

    def _scrape_website(self, source: Dict) -> List[Dict]:
        """Scrape articles from website"""
        articles = []

        try:
            self._rate_limit()
            response = self.session.get(source['url'], timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Find article containers (customize selectors based on site structure)
                article_selectors = source.get('article_selectors', [
                    'article', '.post', '.entry', '.article', '[class*="post"]', '[class*="article"]'
                ])

                for selector in article_selectors:
                    article_elements = soup.select(selector)
                    if article_elements:
                        break

                for article_elem in article_elements[:10]:  # Limit articles per site
                    try:
                        # Extract title
                        title_elem = article_elem.select_one('h1, h2, h3, .title, .headline')
                        title = title_elem.get_text().strip() if title_elem else "Untitled"

                        # Extract content
                        content_elem = article_elem.select_one('p, .content, .entry-content, .post-content')
                        if not content_elem:
                            # Fallback: get all paragraph text
                            paragraphs = article_elem.find_all('p')
                            content = ' '.join(p.get_text() for p in paragraphs)
                        else:
                            content = content_elem.get_text()

                        content = self._clean_content(content)

                        # Extract URL
                        url = ""
                        link_elem = article_elem.find('a', href=True)
                        if link_elem:
                            url = urljoin(source['url'], link_elem['href'])

                        if (len(content) > self.min_content_length and
                            len(content) < self.max_content_length and
                            self._is_relevant_content(content, title)):

                            article = {
                                'title': title,
                                'content': content,
                                'url': url or source['url'],
                                'source': source['name'],
                                'scraped_at': datetime.now().isoformat(),
                                'type': 'website_article'
                            }
                            articles.append(article)

                    except Exception as e:
                        logger.warning(f"Error parsing article from {source['name']}: {e}")

        except Exception as e:
            logger.error(f"Error scraping website {source['name']}: {e}")

        return articles

    def scrape_official_docs(self, sources: List[Dict]) -> List[Dict]:
        """Scrape official documentation sites"""
        logger.info(f"Scraping {len(sources)} documentation sites...")

        articles = []

        for source in sources:
            try:
                logger.info(f"Scraping docs: {source['name']}")

                # Use Selenium for JavaScript-heavy sites
                docs_content = self._scrape_docs_with_selenium(source)
                articles.extend(docs_content)

                time.sleep(3)  # Longer delay for documentation sites

            except Exception as e:
                logger.error(f"Error scraping docs {source['name']}: {e}")

        self._save_data(articles, "official_docs.json")
        logger.info(f"Scraped {len(articles)} documentation sections")
        return articles

    def _scrape_docs_with_selenium(self, source: Dict) -> List[Dict]:
        """Use Selenium to scrape documentation sites"""
        articles = []

        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            driver = webdriver.Chrome(options=options)
            driver.get(source['url'])

            # Wait for content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, source.get('content_selector', 'body')))
            )

            # Get main content
            content_elem = driver.find_element(By.CSS_SELECTOR, source.get('content_selector', 'body'))
            content = content_elem.text

            # Split into sections if possible
            sections = self._split_documentation_content(content, source['name'])

            for section_title, section_content in sections.items():
                if len(section_content) > self.min_content_length:
                    article = {
                        'title': f"{source['name']} - {section_title}",
                        'content': section_content,
                        'url': source['url'],
                        'source': source['name'],
                        'scraped_at': datetime.now().isoformat(),
                        'type': 'documentation'
                    }
                    articles.append(article)

            driver.quit()

        except Exception as e:
            logger.error(f"Selenium scraping failed for {source['name']}: {e}")

        return articles

    def _split_documentation_content(self, content: str, source_name: str) -> Dict[str, str]:
        """Split documentation content into sections"""
        sections = {}

        # Try different splitting strategies
        if source_name.lower() == 'tensorflow':
            # TensorFlow docs have specific structure
            parts = re.split(r'(?=^[A-Z][^a-z]*$)', content, flags=re.MULTILINE)
        elif source_name.lower() == 'pytorch':
            # PyTorch docs structure
            parts = re.split(r'(?=^\d+\.\s)', content, flags=re.MULTILINE)
        else:
            # Generic splitting by headers
            parts = re.split(r'(?=^[A-Z][^a-z]*.*?:?$)', content, flags=re.MULTILINE)

        current_section = "Overview"
        current_content = ""

        for part in parts:
            if len(part.strip()) < 50:  # Likely a header
                if current_content.strip():
                    sections[current_section] = current_content.strip()
                current_section = part.strip() or "Section"
                current_content = ""
            else:
                current_content += part

        if current_content.strip():
            sections[current_section] = current_content.strip()

        return sections

    def scrape_github_repos(self, topics: List[str]) -> List[Dict]:
        """Scrape GitHub repositories and README files"""
        logger.info(f"Scraping GitHub repos for {len(topics)} topics...")

        repos_data = []

        for topic in topics:
            try:
                logger.info(f"Scraping GitHub: {topic}")

                # GitHub API search
                query = f"{topic} AI machine learning"
                url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=stars&order=desc&per_page=20"

                self._rate_limit()
                response = self.session.get(url, headers={'Accept': 'application/vnd.github.v3+json'})

                if response.status_code == 200:
                    data = response.json()

                    for repo in data.get('items', []):
                        # Get README content
                        readme_content = self._get_github_readme(repo['full_name'])

                        if readme_content and len(readme_content) > self.min_content_length:
                            repo_data = {
                                'title': f"{repo['name']} - {repo['description'] or 'AI/ML Project'}",
                                'content': readme_content,
                                'url': repo['html_url'],
                                'stars': repo['stargazers_count'],
                                'language': repo['language'],
                                'source': 'github',
                                'topic': topic,
                                'scraped_at': datetime.now().isoformat(),
                                'type': 'code_repository'
                            }
                            repos_data.append(repo_data)

                time.sleep(2)  # Rate limiting

            except Exception as e:
                logger.error(f"Error scraping GitHub {topic}: {e}")

        self._save_data(repos_data, "github_repos.json")
        logger.info(f"Scraped {len(repos_data)} GitHub repositories")
        return repos_data

    def _get_github_readme(self, repo_name: str) -> Optional[str]:
        """Get README content from GitHub repository"""
        try:
            # Try different README file names
            readme_names = ['README.md', 'README.rst', 'README.txt', 'readme.md']

            for readme_name in readme_names:
                url = f"https://raw.githubusercontent.com/{repo_name}/master/{readme_name}"
                response = self.session.get(url)

                if response.status_code == 200:
                    content = response.text
                    # Clean markdown and return text content
                    content = re.sub(r'[#*`~\[\]]', '', content)  # Remove markdown symbols
                    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # Remove images
                    content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)  # Remove links but keep text
                    return self._clean_content(content)

        except Exception as e:
            logger.debug(f"Error getting README for {repo_name}: {e}")

        return None

    def scrape_youtube_transcripts(self, video_ids: List[str]) -> List[Dict]:
        """Scrape YouTube video transcripts (if available)"""
        logger.info(f"Attempting to scrape transcripts for {len(video_ids)} videos...")

        transcripts = []

        for video_id in video_ids:
            try:
                # Note: YouTube transcript scraping requires additional libraries
                # This is a placeholder for transcript scraping functionality
                logger.info(f"Transcript scraping for video {video_id} - requires additional setup")

            except Exception as e:
                logger.error(f"Error scraping transcript {video_id}: {e}")

        return transcripts

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content"""
        if not html_content:
            return ""

        # Remove HTML tags
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_content)

        # Decode HTML entities
        import html
        text = html.unescape(text)

        return self._clean_content(text)

    def _save_data(self, data: List[Dict], filename: str):
        """Save scraped data to JSON file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Update scraped URLs
        for item in data:
            if 'url' in item:
                self.scraped_urls.add(item['url'])
        self._save_scraped_urls()

    def create_knowledge_base_import(self) -> Dict:
        """Create import-ready data for the knowledge base"""
        logger.info("Creating knowledge base import file...")

        all_content = []

        # Load all scraped data
        for json_file in self.output_dir.glob("*.json"):
            if json_file.name != "scraped_urls.json":
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            all_content.extend(data)
                except Exception as e:
                    logger.error(f"Error loading {json_file}: {e}")

        # Filter and clean content for import
        import_ready = []
        for item in all_content:
            if (isinstance(item, dict) and
                'content' in item and
                len(item.get('content', '')) > self.min_content_length and
                len(item.get('content', '')) < self.max_content_length):

                # Create import format
                import_item = {
                    'title': item.get('title', 'Untitled'),
                    'content': item['content'],
                    'tags': self._generate_tags(item),
                    'category': self._determine_category(item),
                    'source_url': item.get('url', ''),
                    'source_type': item.get('type', 'scraped_content'),
                    'metadata': {
                        'scraped_at': item.get('scraped_at'),
                        'source': item.get('source'),
                        'quality_score': self._calculate_quality_score(item)
                    }
                }
                import_ready.append(import_item)

        # Save import file
        import_file = self.output_dir / "knowledge_base_import.json"
        with open(import_file, 'w', encoding='utf-8') as f:
            json.dump(import_ready, f, indent=2, ensure_ascii=False)

        logger.info(f"Created import file with {len(import_ready)} items: {import_file}")
        return import_ready

    def _generate_tags(self, item: Dict) -> List[str]:
        """Generate relevant tags for content"""
        tags = []

        content = item.get('content', '').lower()
        title = item.get('title', '').lower()

        # AI/ML related tags
        ai_tags = {
            'artificial intelligence': ['AI', 'artificial-intelligence'],
            'machine learning': ['ML', 'machine-learning'],
            'deep learning': ['deep-learning', 'neural-networks'],
            'computer vision': ['computer-vision', 'image-processing'],
            'natural language processing': ['NLP', 'natural-language-processing'],
            'reinforcement learning': ['reinforcement-learning'],
            'supervised learning': ['supervised-learning'],
            'unsupervised learning': ['unsupervised-learning'],
            'data science': ['data-science', 'analytics'],
            'neural network': ['neural-networks', 'deep-learning']
        }

        for keyword, tag_list in ai_tags.items():
            if keyword in content or keyword in title:
                tags.extend(tag_list)

        # Add source-based tags
        source = item.get('source', '').lower()
        if 'arxiv' in source:
            tags.append('research-paper')
        elif 'wikipedia' in source:
            tags.append('encyclopedia')
        elif 'github' in source:
            tags.append('code')
        elif 'tensorflow' in source or 'pytorch' in source:
            tags.append('framework')

        # Add type-based tags
        item_type = item.get('type', '')
        if item_type:
            tags.append(item_type.replace('_', '-'))

        return list(set(tags))  # Remove duplicates

    def _determine_category(self, item: Dict) -> str:
        """Determine content category"""
        content = item.get('content', '').lower()
        title = item.get('title', '').lower()
        source = item.get('source', '').lower()

        if 'tutorial' in title or 'guide' in title:
            return 'Tutorial'
        elif 'research' in title or 'arxiv' in source:
            return 'Research'
        elif 'documentation' in source or 'docs' in source:
            return 'Documentation'
        elif 'wikipedia' in source:
            return 'Reference'
        elif 'blog' in title or any(word in content for word in ['blog', 'article', 'post']):
            return 'Article'
        elif 'github' in source:
            return 'Code'
        else:
            return 'Educational'

    def _calculate_quality_score(self, item: Dict) -> float:
        """Calculate content quality score (0-1)"""
        score = 0.5  # Base score

        content = item.get('content', '')
        title = item.get('title', '')

        # Length bonus
        content_length = len(content)
        if content_length > 2000:
            score += 0.2
        elif content_length < 500:
            score -= 0.1

        # Title quality
        if len(title) > 10 and not title.startswith('Untitled'):
            score += 0.1

        # Source reputation
        reputable_sources = ['arxiv', 'wikipedia', 'tensorflow', 'pytorch', 'scikit-learn']
        source = item.get('source', '').lower()
        if any(rep_source in source for rep_source in reputable_sources):
            score += 0.2

        # Content structure (has sections/headings)
        if re.search(r'\n[A-Z][^a-z]*:', content) or '==' in content:
            score += 0.1

        return max(0.0, min(1.0, score))

    def run_full_scraping_pipeline(self) -> Dict:
        """Run the complete scraping pipeline"""
        logger.info("🚀 Starting comprehensive AI/ML data scraping pipeline...")

        results = {
            'arxiv_papers': 0,
            'wikipedia_articles': 0,
            'tech_articles': 0,
            'documentation': 0,
            'github_repos': 0,
            'total_items': 0,
            'import_ready': 0
        }

        # Define scraping targets
        ai_topics = [
            'Artificial intelligence', 'Machine learning', 'Deep learning',
            'Neural network', 'Natural language processing', 'Computer vision',
            'Reinforcement learning', 'Supervised learning', 'Unsupervised learning',
            'Transfer learning', 'Generative AI', 'Large language model',
            'Computer science', 'Data science', 'Algorithm'
        ]

        tech_sources = [
            {'name': 'MIT Technology Review', 'url': 'https://www.technologyreview.com', 'rss_url': 'https://www.technologyreview.com/topnews.rss'},
            {'name': 'Towards Data Science', 'url': 'https://towardsdatascience.com', 'rss_url': 'https://towardsdatascience.com/feed'},
            {'name': 'AI News', 'url': 'https://artificialintelligence-news.com', 'rss_url': 'https://artificialintelligence-news.com/feed/'},
            {'name': 'Machine Learning Mastery', 'url': 'https://machinelearningmastery.com', 'article_selectors': ['.post', '.entry']},
            {'name': 'KDnuggets', 'url': 'https://www.kdnuggets.com', 'article_selectors': ['.post-content', '.entry-content']}
        ]

        doc_sources = [
            {'name': 'TensorFlow', 'url': 'https://www.tensorflow.org/guide', 'content_selector': '.devsite-article-body'},
            {'name': 'PyTorch', 'url': 'https://pytorch.org/tutorials/', 'content_selector': '.tutorial-content'},
            {'name': 'scikit-learn', 'url': 'https://scikit-learn.org/stable/user_guide.html', 'content_selector': '.section'}
        ]

        github_topics = ['machine-learning', 'deep-learning', 'artificial-intelligence', 'neural-network']

        try:
            # 1. Scrape arXiv papers
            logger.info("📄 Phase 1: Scraping arXiv research papers...")
            papers = self.scrape_arxiv_papers(50)
            results['arxiv_papers'] = len(papers)

            # 2. Scrape Wikipedia articles
            logger.info("📚 Phase 2: Scraping Wikipedia articles...")
            wiki_articles = self.scrape_wikipedia_articles(ai_topics)
            results['wikipedia_articles'] = len(wiki_articles)

            # 3. Scrape tech blogs
            logger.info("📰 Phase 3: Scraping tech blog articles...")
            blog_articles = self.scrape_tech_blogs(tech_sources)
            results['tech_articles'] = len(blog_articles)

            # 4. Scrape documentation
            logger.info("📖 Phase 4: Scraping official documentation...")
            docs = self.scrape_official_docs(doc_sources)
            results['documentation'] = len(docs)

            # 5. Scrape GitHub repositories
            logger.info("💻 Phase 5: Scraping GitHub repositories...")
            repos = self.scrape_github_repos(github_topics)
            results['github_repos'] = len(repos)

            # 6. Create import file
            logger.info("🎯 Phase 6: Creating knowledge base import...")
            import_data = self.create_knowledge_base_import()
            results['import_ready'] = len(import_data)

            results['total_items'] = sum(results.values())

            # Summary
            logger.info("✅ Scraping pipeline completed successfully!")
            logger.info(f"📊 Total items scraped: {results['total_items']}")
            logger.info(f"🎯 Import-ready items: {results['import_ready']}")
            logger.info(f"💾 Data saved in: {self.output_dir}")
            logger.info(f"📁 Import file: {self.output_dir}/knowledge_base_import.json")

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise

        return results

def main():
    """Main scraping function"""
    scraper = AIDataScraper()

    print("🤖 AI/ML Data Scraping System")
    print("=" * 50)
    print("This will scrape comprehensive AI/ML content from:")
    print("• arXiv research papers")
    print("• Wikipedia articles")
    print("• Tech blog posts")
    print("• Official documentation")
    print("• GitHub repositories")
    print()
    print("⚠️  Note: This process may take 30-60 minutes")
    print("🔄 Rate limiting is applied to be respectful to websites")
    print()

    try:
        results = scraper.run_full_scraping_pipeline()

        print("\n" + "=" * 50)
        print("📊 SCRAPING RESULTS:")
        print(f"📄 arXiv Papers: {results['arxiv_papers']}")
        print(f"📚 Wikipedia Articles: {results['wikipedia_articles']}")
        print(f"📰 Tech Articles: {results['tech_articles']}")
        print(f"📖 Documentation: {results['documentation']}")
        print(f"💻 GitHub Repos: {results['github_repos']}")
        print(f"🎯 Total Items: {results['total_items']}")
        print(f"📁 Import Ready: {results['import_ready']}")

        print("\n" + "=" * 50)
        print("🎉 Scraping completed successfully!")
        print(f"📂 Data saved in: {scraper.output_dir}")
        print(f"📄 Import file: {scraper.output_dir}/knowledge_base_import.json")
        print()
        print("🚀 Next steps:")
        print("1. Review the scraped data quality")
        print("2. Import data into your knowledge base:")
        print("   python import_scraped_data.py")
        print("3. Run accuracy evaluation:")
        print("   python evaluate_accuracy.py")

    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        raise

if __name__ == "__main__":
    main()
