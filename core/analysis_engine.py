# -*- coding: utf-8 -*-
"""Core analysis engine separating logic from Streamlit UI.

This module encapsulates URL fetching, SEO analysis, AIO (LLM-based) analysis,
result integration, score validation, chart image generation, and PDF report
export. It is designed to be UI-agnostic so it can be imported from a CLI,
web UI, or tests.
"""

import os
import sys
import json
import requests
from bs4 import BeautifulSoup
import tldextract
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List

# Matplotlib (optional)
try:
	import matplotlib.pyplot as plt
	import matplotlib
	matplotlib.use('Agg')
except Exception:  # pragma: no cover - optional dependency
	plt = None
	matplotlib = None

# ReportLab (optional)
try:
	from reportlab.lib.pagesizes import A4
	from reportlab.lib import colors
	from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
	from reportlab.platypus import (
		SimpleDocTemplate,
		Paragraph,
		Spacer,
		Image as ReportLabImage,
		Table,
		TableStyle,
		PageBreak,
		ListFlowable,
		ListItem,
	)
	from reportlab.lib.units import mm, cm
	from reportlab.lib.enums import TA_CENTER
	from reportlab.pdfbase import pdfmetrics
	from reportlab.pdfbase.ttfonts import TTFont
except Exception:  # pragma: no cover - optional dependency
	A4 = None
	colors = None
	getSampleStyleSheet = None
	ParagraphStyle = None
	SimpleDocTemplate = None
	Paragraph = None
	Spacer = None
	ReportLabImage = None
	Table = None
	TableStyle = None
	PageBreak = None
	ListFlowable = None
	ListItem = None
	mm = None
	cm = None
	TA_CENTER = None
	pdfmetrics = None
	TTFont = None

# OpenAI
try:
	from openai import OpenAI
except Exception:  # pragma: no cover
	OpenAI = None

from .constants import (
	APP_NAME,
	APP_VERSION,
	COLOR_PALETTE,
	AIO_SCORE_MAP_JP,
	AIO_SCORE_MAP_JP_UPPER,
	AIO_SCORE_MAP_JP_LOWER,
	SEO_SCORE_LABELS,
	OPENAI_MODEL,
	OPENAI_TEMPERATURE,
)
from .industry_detector import IndustryDetector, IndustryAnalysis
from .text_utils import detect_mojibake


# PDF helper decorations
def _add_corner(canvas, doc_obj) -> None:
	if colors is None:
		return
	canvas.saveState()
	canvas.setFillColor(colors.HexColor(COLOR_PALETTE["primary"]))
	x = doc_obj.pagesize[0] - 25
	y = doc_obj.pagesize[1] - 25
	canvas.rect(x, y, 15, 15, fill=1, stroke=0)
	canvas.restoreState()


def _section_break(story, width) -> None:
	if Table is None or TableStyle is None or colors is None or Spacer is None or mm is None:
		return
	line = Table(
		[[""]],
		colWidths=[width],
		style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(COLOR_PALETTE["divider"]))]),
	)
	story.append(Spacer(1, 2 * mm))
	story.append(line)
	story.append(Spacer(1, 2 * mm))


# Default PDF font registration (optional)
if pdfmetrics is not None and TTFont is not None:
	try:
		if os.name == 'nt':
			if os.path.exists('C:/Windows/Fonts/msgothic.ttc'):
				pdfmetrics.registerFont(TTFont('MSGothic', 'C:/Windows/Fonts/msgothic.ttc'))
				DEFAULT_PDF_FONT = 'MSGothic'
			elif os.path.exists('C:/Windows/Fonts/meiryo.ttc'):
				pdfmetrics.registerFont(TTFont('Meiryo', 'C:/Windows/Fonts/meiryo.ttc'))
				DEFAULT_PDF_FONT = 'Meiryo'
			else:
				DEFAULT_PDF_FONT = 'Helvetica'
		elif sys.platform == 'darwin':
			candidates = [
				'/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
				'/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
				'/System/Library/Fonts/Hiragino Sans GB.ttc',
				'/System/Library/Fonts/PingFang.ttc',
			]
			DEFAULT_PDF_FONT = 'Helvetica'
			for p in candidates:
				if os.path.exists(p):
					try:
						font_name = 'HiraginoSansW3'
						if 'PingFang' in p:
							font_name = 'PingFang'
						pdfmetrics.registerFont(TTFont(font_name, p))
						DEFAULT_PDF_FONT = font_name
						break
					except Exception:
						pass
		else:
			candidates = [
				'/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
				'/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.otf',
			]
			DEFAULT_PDF_FONT = 'Helvetica'
			for p in candidates:
				if os.path.exists(p):
					try:
						pdfmetrics.registerFont(TTFont('NotoSansJP', p))
						DEFAULT_PDF_FONT = 'NotoSansJP'
						break
					except Exception:
						pass
	except Exception:
		DEFAULT_PDF_FONT = 'Helvetica'
else:
	DEFAULT_PDF_FONT = 'Helvetica'


class AnalysisEngine:
	"""Headless analysis engine (no Streamlit dependency)."""

	def __init__(self):
		api_key = os.getenv("OPENAI_API_KEY")
		if not api_key:
			raise ValueError("OPENAI_API_KEY is not set in environment")
		if OpenAI is None:
			raise ValueError("openai library is not available")
		self.client = OpenAI(api_key=api_key)
		self.industry_detector = IndustryDetector()
		self.last_analysis_results = None
		self.seo_results = None
		self.aio_results = None

	def _scale_to_100(self, value: float) -> float:
		if not isinstance(value, (int, float)):
			return 0.0
		if 0 <= value <= 10:
			return value * 10
		if value > 100:
			return 100.0
		return float(value)

	def analyze_url(self, url: str, user_industry: str, balance: int = 50) -> Dict:
		if not url.startswith(('http://', 'https://')):
			url = 'https://' + url

		# Probe API connectivity (fail-fast)
		self.client.models.list(timeout=10)

		# Fetch HTML
		response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}, timeout=15)
		response.raise_for_status()
		html_content = response.text
		soup = BeautifulSoup(html_content, 'html.parser')

		# Industry analysis
		title = soup.title.string.strip() if soup.title and soup.title.string else ""
		meta_desc = ""
		meta_tag = soup.find('meta', attrs={'name': 'description'})
		if meta_tag and meta_tag.get('content'):
			meta_desc = meta_tag['content'].strip()

		main_content = self._extract_main_content(soup)
		industry_analysis = self.industry_detector.analyze_industries(title, main_content, meta_desc)
		final_industry = self._determine_final_industry(user_industry, industry_analysis)

		# Run SEO/AIO analysis
		self.seo_results = self._analyze_seo(soup, url)
		self.aio_results = self._analyze_aio(soup, url, final_industry, industry_analysis)

		# Integrate
		seo_weight = (100 - balance) / 100
		aio_weight = balance / 100
		integrated_results = self._integrate_results(self.seo_results, self.aio_results, seo_weight, aio_weight)

		self.last_analysis_results = {
			"url": url,
			"user_industry": user_industry,
			"final_industry": final_industry,
			"industry_analysis": industry_analysis,
			"balance": balance,
			"seo_results": self.seo_results,
			"aio_results": self.aio_results,
			"integrated_results": integrated_results,
			"timestamp": datetime.now().isoformat(),
		}
		return self.last_analysis_results

	def _determine_final_industry(self, user_industry: str, auto: IndustryAnalysis) -> Dict:
		result = {
			"primary": user_industry if user_industry else auto.primary_industry,
			"source": "",
			"confidence": 0.0,
			"secondary_detected": auto.secondary_industries,
			"auto_primary": auto.primary_industry,
			"auto_confidence": auto.confidence_score,
		}
		if user_industry and auto.confidence_score > 50:
			if user_industry.lower() in auto.primary_industry.lower():
				result["source"] = "ユーザー入力（自動判定で確認済み）"
				result["confidence"] = 95.0
			else:
				result["source"] = f"ユーザー入力（自動判定: {auto.primary_industry}）"
				result["confidence"] = 85.0
		elif user_industry:
			result["source"] = "ユーザー入力"
			result["confidence"] = 80.0
		elif auto.confidence_score > 70:
			result["source"] = f"自動判定（信頼度: {auto.confidence_score:.1f}%）"
			result["confidence"] = auto.confidence_score
		else:
			result["primary"] = "指定なし"
			result["source"] = "判定困難"
			result["confidence"] = auto.confidence_score
		return result

	def _extract_main_content(self, soup):
		for tag in soup.find_all(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'iframe']):
			tag.decompose()
		main_selectors = ['article', 'main', '.main-content', '#content', '#main', '.post-content']
		content_parts: List[str] = []
		for selector in main_selectors:
			elements = soup.select(selector)
			for element in elements:
				if element:
					for child in element.find_all(class_=['comments', 'social-sharing', 'related-posts']):
						child.decompose()
					text = element.get_text(separator=' ', strip=True)
					if len(text) > 200:
						content_parts.append(text)
						if len(" ".join(content_parts)) > 5000:
							return " ".join(content_parts)
		if content_parts:
			return " ".join(content_parts)
		body = soup.find('body')
		return body.get_text(separator=' ', strip=True) if body else soup.get_text(separator=' ', strip=True)

	def _analyze_seo(self, soup, url):
		title_tag = soup.find('title')
		title = title_tag.string.strip() if title_tag and title_tag.string else ""
		meta_description_tag = soup.find('meta', attrs={'name': 'description'})
		description = meta_description_tag['content'].strip() if meta_description_tag and meta_description_tag.has_attr('content') else ""
		garbled_title = detect_mojibake(title)
		garbled_description = detect_mojibake(description)
		og_title_tag = soup.find('meta', attrs={'property': 'og:title'})
		og_title = og_title_tag['content'].strip() if og_title_tag and og_title_tag.has_attr('content') else ""
		og_description_tag = soup.find('meta', attrs={'property': 'og:description'})
		og_description = og_description_tag['content'].strip() if og_description_tag and og_description_tag.has_attr('content') else ""
		og_image_tag = soup.find('meta', attrs={'property': 'og:image'})
		og_image = og_image_tag['content'].strip() if og_image_tag and og_image_tag.has_attr('content') else ""
		canonical_tag = soup.find('link', attrs={'rel': 'canonical'})
		canonical_url = canonical_tag['href'].strip() if canonical_tag and canonical_tag.has_attr('href') else ""
		meta_keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
		meta_keywords = meta_keywords_tag['content'].strip() if meta_keywords_tag and meta_keywords_tag.has_attr('content') else ""
		meta_author_tag = soup.find('meta', attrs={'name': 'author'})
		meta_author = meta_author_tag['content'].strip() if meta_author_tag and meta_author_tag.has_attr('content') else ""
		headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}
		heading_texts = {f'h{i}': [h.get_text(strip=True) for h in soup.find_all(f'h{i}')][:3] for i in range(1, 4)}
		all_links = soup.find_all('a', href=True)
		internal_links, external_links = [], []
		try:
			base_domain_ext = tldextract.extract(url)
			base_domain = base_domain_ext.domain + '.' + base_domain_ext.suffix
		except Exception:
			base_domain = ""
		for link in all_links:
			href = link.get('href')
			if not href or href.startswith(('#', 'javascript:')):
				continue
			try:
				full_url = requests.compat.urljoin(url, href.strip())
				link_domain_ext = tldextract.extract(full_url)
				link_domain = link_domain_ext.domain + '.' + link_domain_ext.suffix
				if link_domain and base_domain and link_domain == base_domain:
					internal_links.append(full_url)
				elif link_domain and base_domain:
					external_links.append(full_url)
			except Exception:
				continue
		images = soup.find_all('img')
		images_with_alt = sum(1 for img in images if img.get('alt', '').strip())
		images_without_alt = len(images) - images_with_alt
		structured_data_scripts = soup.find_all('script', {'type': 'application/ld+json'})
		has_structured_data = len(structured_data_scripts) > 0
		structured_data_types: List[str] = []
		for sc in structured_data_scripts:
			try:
				data = json.loads(sc.string)
				if isinstance(data, dict) and '@type' in data:
					structured_data_types.append(data['@type'])
				elif isinstance(data, list):
					for item in data:
						if isinstance(item, dict) and '@type' in item:
							structured_data_types.append(item['@type'])
			except Exception:
				continue
		viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
		has_viewport = viewport_tag is not None
		tech_stack: List[str] = []
		generator = ""
		meta_generator_tag = soup.find('meta', attrs={'name': 'generator'})
		if meta_generator_tag and meta_generator_tag.has_attr('content'):
			generator = meta_generator_tag['content'].strip().lower()
		html_code = soup.prettify()
		html_lower = html_code.lower()
		if 'wordpress' in generator or 'wp-content' in html_lower:
			tech_stack.append('WordPress')
		if 'shopify' in generator or 'shopify' in html_lower:
			tech_stack.append('Shopify')
		if 'wix' in generator or 'wixsite' in html_lower:
			tech_stack.append('Wix')
		main_content_text = self._extract_main_content(soup)
		word_count = len(main_content_text.split())
		words = re.findall(r'[A-Za-z]{3,}', main_content_text.lower())
		stop_words = {'the','and','for','with','that','this','you','your','from','are','was','were','have','has','not','but','can','will','his','her','its','she','him','our','out','use','using'}
		filtered = [w for w in words if w not in stop_words]
		freq = Counter(filtered)
		top_keywords = freq.most_common(10)
		text_content_all = soup.get_text(separator=' ', strip=True)
		text_html_ratio = (len(text_content_all) / max(len(html_code), 1)) * 100 if html_code else 0
		meta_tags_count = len(soup.find_all('meta'))
		page_size_kb = len(html_code.encode('utf-8', errors='ignore')) / 1024 if html_code else 0
		personalization = {
			"meta": {"description": description, "keywords": meta_keywords, "author": meta_author},
			"ogp": {"title": og_title, "description": og_description, "image": og_image},
			"headings_content": heading_texts,
			"structured_data_types": structured_data_types,
			"top_keywords": top_keywords,
			"tech_stack": tech_stack,
		}
		scores = {
			"title_score": self._calculate_title_score(title),
			"meta_description_score": self._calculate_meta_description_score(description),
			"headings_score": self._calculate_headings_score(headings),
			"content_score": self._calculate_content_score(word_count, text_html_ratio),
			"links_score": self._calculate_links_score(len(internal_links), len(external_links)),
			"images_score": self._calculate_images_score(images_with_alt, images_without_alt),
			"technical_score": self._calculate_technical_score(has_structured_data, has_viewport, canonical_url),
		}
		total_score = sum(scores.values()) / len(scores) * 10 if scores else 0
		return {
			"basics": {"title": title, "title_length": len(title), "meta_description": description, "meta_description_length": len(description), "og_title": og_title, "og_description": og_description},
			"structure": {"headings": headings, "internal_links_count": len(internal_links), "external_links_count": len(external_links), "images_count": len(images), "images_with_alt": images_with_alt, "images_without_alt": images_without_alt},
			"technical": {"has_structured_data": has_structured_data, "structured_data_count": len(structured_data_scripts), "canonical_url": canonical_url, "has_viewport": has_viewport, "meta_tags_count": meta_tags_count, "page_size_kb": page_size_kb},
			"content": {"word_count": word_count, "text_html_ratio": text_html_ratio},
			"personalization": personalization,
			"scores": scores,
			"total_score": total_score,
			"garbled": {"title": garbled_title, "meta_description": garbled_description},
		}

	def _calculate_title_score(self, title):
		if not title: return 0
		l = len(title)
		if 30 <= l <= 60: return 10
		elif 20 <= l < 30 or 60 < l <= 70: return 8
		elif 10 <= l < 20 or 70 < l <= 80: return 6
		else: return 3 if l < 10 else 4

	def _calculate_meta_description_score(self, desc):
		if not desc: return 0
		l = len(desc)
		if 120 <= l <= 156: return 10
		elif 100 <= l < 120 or 156 < l <= 170: return 8
		elif 80 <= l < 100 or 170 < l <= 200: return 6
		else: return 3 if l < 80 else 4

	def _calculate_headings_score(self, headings):
		h1s, h2s = headings.get('h1', 0), headings.get('h2', 0)
		h1_sc = 10 if h1s == 1 else (5 if h1s > 1 else 0)
		h2_sc = 10 if h2s >= 1 else 0
		hier_sc = 5 if h1s > 0 and h2s == 0 and any(headings.get(f'h{i}', 0) > 0 for i in range(3, 7)) else 10
		return h1_sc * 0.4 + h2_sc * 0.3 + hier_sc * 0.3

	def _calculate_content_score(self, wc, tr):
		w_sc = 10 if wc >= 600 else (8 if wc >= 400 else (6 if wc >= 300 else (4 if wc >= 200 else 2)))
		r_sc = 10 if tr >= 25 else (8 if tr >= 20 else (6 if tr >= 15 else (4 if tr >= 10 else 2)))
		return w_sc * 0.7 + r_sc * 0.3

	def _calculate_links_score(self, int_l, ext_l):
		int_sc = 10 if int_l >= 5 else (8 if int_l >= 3 else (5 if int_l >= 1 else 0))
		ext_sc = 10 if ext_l >= 3 else (8 if ext_l >= 1 else 5)
		return int_sc * 0.7 + ext_sc * 0.3

	def _calculate_images_score(self, img_alt, img_no_alt):
		total = img_alt + img_no_alt
		if total == 0: return 5
		ratio = img_alt / total
		if ratio == 1: return 10
		elif ratio >= 0.8: return 8
		elif ratio >= 0.6: return 6
		elif ratio >= 0.4: return 4
		else: return 2 if ratio >= 0.2 else 0

	def _calculate_technical_score(self, struct_data, viewport, canon_url):
		sc = [(10 if struct_data else 0), (10 if viewport else 0), (10 if canon_url else 5)]
		return sum(sc) / len(sc) if sc else 0

	def _analyze_aio(self, soup, url, final_industry, industry_analysis):
		if OpenAI is None:
			raise ValueError("openai library is not available")
		title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
		main_content = self._extract_main_content(soup)
		content_preview = main_content[:7000]
		industry_info = f"""
主要業界: {final_industry['primary']} ({final_industry['source']})
信頼度: {final_industry['confidence']:.1f}%
検出された副業界: {', '.join(final_industry['secondary_detected'][:3]) if final_industry['secondary_detected'] else 'なし'}
専門用語: {', '.join(industry_analysis.specialized_terms[:5]) if industry_analysis.specialized_terms else 'なし'}
ターゲット層: {', '.join(industry_analysis.target_audience_clues) if industry_analysis.target_audience_clues else '不明'}
規制要件: {', '.join(industry_analysis.regulatory_indicators) if industry_analysis.regulatory_indicators else 'なし'}
		"""
		aio_prompt = f"""
あなたは最先端のAIO（生成AI検索最適化）専門家です。
以下のウェブページを、生成AI検索エンジン（ChatGPT Search、Claude、Gemini、Perplexity等）での
パフォーマンス向上の観点から専門的に分析してください。

**分析対象:**
URL: {url}
タイトル: {title}

**業界分析結果:**
{industry_info}

**コンテンツ:**
{content_preview}

## 評価項目（各10点満点）

### 1. E-E-A-T評価（40%）
- **Experience（経験）**: 実体験・一次情報の豊富さ、具体的事例の質
- **Expertise（専門性）**: 専門知識の深さ、最新情報への対応度  
- **Authoritativeness（権威性）**: 引用価値、業界認知度、信頼できる情報源との関連性
- **Trustworthiness（信頼性）**: 事実確認の容易さ、透明性、偏見のなさ

### 2. AI検索最適化（35%）
- **構造化・整理**: 論理的構造、AI理解しやすい情報階層
- **質問応答適合性**: ユーザーの質問に直接答える形式度
- **引用可能性**: AI回答での引用されやすさ、要約しやすさ
- **マルチモーダル対応**: 画像・表・図表とその説明の質

### 3. ユーザー体験（25%）
- **検索意図マッチング**: 様々な検索意図への対応度
- **パーソナライズ可能性**: 異なるユーザー層への適応性
- **情報の独自性**: オリジナルコンテンツ、独自視点の提供
- **コンテンツ完全性**: トピックの包括的カバー、深さ

## {final_industry['primary']}業界特化分析
現在の市場トレンドを踏まえて以下観点から評価してください：
- 業界専門用語の適切な使用と説明
- 2025年の業界トレンド・最新情報の反映度  
- ターゲットユーザーへの適合性
- 競合他社との差別化ポイント
- 業界特有の信頼性指標（資格、実績、認証等）
- 規制・コンプライアンス要素への対応

## 改善アクション
1. **即効改善施策**（1-2週間で実装可能）- 3つ以上
2. **中期戦略施策**（1-3ヶ月）- 3つ以上
3. **競合差別化施策** - 3つ以上
4. **市場トレンド対応施策** - 現在の{final_industry['primary']}業界トレンドに基づく具体的施策

## JSON出力形式
{{
  "basic_info": {{ "url": "{url}", "industry": "{final_industry['primary']}", "title": "{title}" }},
  "scores": {{
    "experience": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "expertise": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "authoritativeness": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "trustworthiness": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "structure": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "qa_compatibility": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "citation_potential": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "multimodal": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "search_intent": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "personalization": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "uniqueness": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "completeness": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "readability": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "mobile_friendly": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "page_speed": {{"score": 0, "advice": "具体的で実践的なアドバイス"}},
    "metadata": {{"score": 0, "advice": "具体的で実践的なアドバイス"}}
  }},
  "category_scores": {{
    "eeat_score": 0.0, "ai_search_score": 0.0, "user_experience_score": 0.0, "technical_score": 0.0
  }},
  "total_score": 0.0,
  "immediate_actions": [
    {{"action": "施策", "method": "具体的な実装方法", "expected_impact": "期待効果"}}
  ],
  "medium_term_strategies": [
    {{"strategy": "戦略", "timeline": "実装期間", "expected_outcome": "期待成果"}}
  ],
  "competitive_advantages": [
    {{"advantage": "差別化ポイント", "implementation": "具体的な実装方法"}}
  ],
  "market_trend_strategies": [
    {{"trend": "トレンド", "strategy": "対応戦略", "priority": "優先度"}}
  ],
  "industry_analysis": {{
    "industry_fit": "{final_industry['primary']}業界への適合度評価",
    "specialized_improvements": "業界特化改善提案",
    "compliance_check": "規制・コンプライアンス対応状況",
    "market_trends": "現在の市場トレンドと対応状況"
  }}
}}
"""
		model_name = OPENAI_MODEL
		base_params = {
			"model": model_name,
			"messages": [
				{"role": "system", "content": (
					"あなたはSEOとAIO（生成AI検索最適化）の専門家です。\n"
					"必要に応じて最新の市場トレンドを検索して分析結果に含めてください。\n\n"
					"重要: 回答は必ず有効なJSON形式でのみ返してください。"
				)},
				{"role": "user", "content": aio_prompt},
			],
			"timeout": 180,
			"temperature": OPENAI_TEMPERATURE,
			"response_format": {"type": "json_object"},
		}
		response = self.client.chat.completions.create(**base_params)
		aio_analysis_str = response.choices[0].message.content or ""
		aio_analysis_str = aio_analysis_str.strip()
		if aio_analysis_str.startswith("```json"):
			aio_analysis_str = aio_analysis_str.replace("```json", "").replace("```", "").strip()
		elif aio_analysis_str.startswith("```"):
			aio_analysis_str = aio_analysis_str.replace("```", "").strip()
		start_idx = aio_analysis_str.find('{')
		end_idx = aio_analysis_str.rfind('}')
		if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
			raise ValueError("APIレスポンスにJSONオブジェクトが見つかりません")
		aio_analysis_str = aio_analysis_str[start_idx:end_idx+1]
		aio_analysis = json.loads(aio_analysis_str)
		# Normalize
		normalized = {
			"basic_info": aio_analysis.get("basic_info", {"url": url, "industry": final_industry['primary'], "title": title}),
			"scores": {},
			"category_scores": aio_analysis.get("category_scores", {}),
			"total_score": self._scale_to_100(aio_analysis.get("total_score", 0.0)),
			"immediate_actions": aio_analysis.get("immediate_actions", []),
			"medium_term_strategies": aio_analysis.get("medium_term_strategies", []),
			"competitive_advantages": aio_analysis.get("competitive_advantages", []),
			"market_trend_strategies": aio_analysis.get("market_trend_strategies", []),
			"industry_analysis": aio_analysis.get("industry_analysis", {}),
		}
		default_score_advice = {"score": 0, "advice": "APIからのデータなし"}
		for key in AIO_SCORE_MAP_JP.keys():
			normalized["scores"][key] = aio_analysis.get("scores", {}).get(key, default_score_advice.copy())
			# Ensure 0-100 scale is applied to total_score only; item scores remain 0-10
		categories = {}
		for cat, val in normalized.get("category_scores", {}).items():
			categories[cat] = self._scale_to_100(val)
		normalized["category_scores"] = categories
		return normalized

	def _integrate_results(self, seo_results, aio_results, seo_weight, aio_weight):
		seo_score = seo_results.get("total_score", 0.0)
		aio_total_score = aio_results.get("total_score", 0.0)
		try:
			aio_total_score = float(aio_total_score)
		except Exception:
			aio_total_score = 0.0
		aio_total_score = self._scale_to_100(aio_total_score)
		integrated_score = seo_score * seo_weight + aio_total_score * aio_weight
		improvements: List[str] = []
		if aio_total_score < seo_score:
			immediate = aio_results.get("immediate_actions", [])
			improvements.extend([f"AIO優先: {a.get('action', 'N/A')}" for a in immediate[:3]])
			if seo_score < 70:
				improvements.append(f"SEO補完: タイトル最適化（現在スコア: {seo_results.get('scores', {}).get('title_score', 0):.1f}/10）")
		else:
			seo_scores = seo_results.get('scores', {})
			low_items = [(k, v) for k, v in seo_scores.items() if v < 7]
			low_items.sort(key=lambda x: x[1])
			for item_name, score in low_items[:2]:
				readable = item_name.replace("_score", "").replace("_", " ").title()
				improvements.append(f"SEO優先: {readable}の改善（現在スコア: {score:.1f}/10）")
			immediate = aio_results.get("immediate_actions", [])
			if immediate:
				improvements.append(f"AIO補完: {immediate[0].get('action', 'N/A')}")
		total_gap = (100 - seo_score) + (100 - aio_total_score)
		if total_gap == 0:
			recommended_seo_focus = 50
		else:
			recommended_seo_focus = round((100 - seo_score) / total_gap * 100) if total_gap > 0 else 50
		recommended_aio_focus = 100 - recommended_seo_focus
		return {
			"integrated_score": integrated_score,
			"seo_score": seo_score,
			"aio_score": aio_total_score,
			"primary_focus": "AIO" if aio_total_score < seo_score else "SEO",
			"improvements": improvements,
			"seo_score_distribution": {k: v for k, v in seo_results.get("scores", {}).items()},
			"aio_score_distribution": {k: v.get("score", 0) for k, v in aio_results.get("scores", {}).items()},
			"recommended_balance": {"seo_focus": recommended_seo_focus, "aio_focus": recommended_aio_focus},
		}

	def _validate_score_consistency(self):
		results = {
			"seo_total_expected": None,
			"seo_total_reported": None,
			"seo_delta": None,
			"aio_total_observed": None,
			"aio_total_reported": None,
			"aio_delta": None,
			"integrated_expected": None,
			"integrated_reported": None,
			"integrated_delta": None,
		}
		try:
			seo_scores = (self.seo_results or {}).get("scores", {})
			seo_expected = (sum(seo_scores.values()) / max(len(seo_scores), 1)) * 10.0 if seo_scores else 0.0
			seo_reported = (self.seo_results or {}).get("total_score", 0.0)
			results["seo_total_expected"], results["seo_total_reported"] = seo_expected, seo_reported
			results["seo_delta"] = float(seo_reported) - float(seo_expected)
			aio_scores_map = (self.aio_results or {}).get("scores", {})
			aio_item_scores = [v.get("score", 0) for v in aio_scores_map.values()] if aio_scores_map else []
			aio_observed = (sum(aio_item_scores) / max(len(aio_item_scores), 1)) * 10.0 if aio_item_scores else 0.0
			aio_reported = (self.aio_results or {}).get("total_score", 0.0)
			results["aio_total_observed"], results["aio_total_reported"] = aio_observed, aio_reported
			results["aio_delta"] = float(aio_reported) - float(aio_observed)
			seo_reported_100 = float(seo_reported)
			aio_reported_100 = float(aio_reported)
			balance = 50
			if self.last_analysis_results and isinstance(self.last_analysis_results.get("balance"), (int, float)):
				balance = self.last_analysis_results["balance"]
			seo_w = (100 - balance) / 100.0
			aio_w = balance / 100.0
			integrated_expected = seo_reported_100 * seo_w + aio_reported_100 * aio_w
			integrated_reported = ((self.last_analysis_results or {}).get("integrated_results", {}) or {}).get("integrated_score", 0.0)
			results["integrated_expected"], results["integrated_reported"] = integrated_expected, integrated_reported
			results["integrated_delta"] = float(integrated_reported) - float(integrated_expected)
		except Exception:
			pass
		return results

	def generate_enhanced_pdf_report(self, output_path: str, logo_path: str = None):
		if self.last_analysis_results is None:
			raise ValueError("分析結果がありません。分析を先に実行してください。")
		if SimpleDocTemplate is None:
			raise ValueError("ReportLabが利用できません")
		def safe_str(value, default=""):
			return str(value) if value is not None else default
		doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
		styles = getSampleStyleSheet()
		title_style = ParagraphStyle('DocTitle', parent=styles['h1'], fontName=DEFAULT_PDF_FONT, fontSize=22, alignment=TA_CENTER, spaceAfter=6*mm, textColor=colors.HexColor(COLOR_PALETTE["secondary"]))
		h1_style = ParagraphStyle('DocH1', parent=styles['h1'], fontName=DEFAULT_PDF_FONT, fontSize=16, spaceBefore=6*mm, spaceAfter=3*mm, textColor=colors.HexColor(COLOR_PALETTE["primary"]))
		h2_style = ParagraphStyle('DocH2', parent=styles['h2'], fontName=DEFAULT_PDF_FONT, fontSize=14, spaceBefore=4*mm, spaceAfter=2*mm, textColor=colors.HexColor(COLOR_PALETTE["secondary"]))
		normal_style = ParagraphStyle('DocNormal', parent=styles['Normal'], fontName=DEFAULT_PDF_FONT, fontSize=10, spaceAfter=2*mm, leading=14, textColor=colors.HexColor(COLOR_PALETTE["text_primary"]))
		centered_style = ParagraphStyle('DocCentered', parent=normal_style, alignment=TA_CENTER, fontName=DEFAULT_PDF_FONT)
		story: List = []
		if logo_path and os.path.exists(logo_path):
			try:
				img = ReportLabImage(logo_path, width=40*mm, height=15*mm)
				story.append(img)
				story.append(Spacer(1, 2*mm))
			except Exception:
				pass
		story.append(Paragraph(f"{APP_NAME} 詳細分析レポート", title_style))
		story.append(Paragraph(f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}", centered_style))
		story.append(Spacer(1, 6*mm))
		story.append(Paragraph("<u>1. エグゼクティブサマリー</u>", h1_style))
		_section_break(story, doc.width)
		story.append(Paragraph(f"<b>対象URL:</b> {self.last_analysis_results['url']}", normal_style))
		final_industry = self.last_analysis_results['final_industry']
		integrated_results = self.last_analysis_results["integrated_results"]
		story.append(Paragraph(f"<b>業界判定:</b> {final_industry['primary']} ({final_industry['source']})", normal_style))
		story.append(Paragraph(f"<b>総合スコア:</b> {integrated_results.get('integrated_score',0.0):.1f}/100", normal_style))
		story.append(Paragraph(f"<b>SEOスコア:</b> {integrated_results.get('seo_score',0.0):.1f}/100", normal_style))
		story.append(Paragraph(f"<b>AIOスコア:</b> {integrated_results.get('aio_score',0.0):.1f}/100", normal_style))
		story.append(Paragraph(f"<b>主要改善領域:</b> {integrated_results.get('primary_focus', 'N/A')}", normal_style))
		improvements = integrated_results.get('improvements', [])[:3]
		if improvements:
			bullet_items = [ListItem(Paragraph(imp, normal_style)) for imp in improvements]
			story.append(ListFlowable(bullet_items, bulletType='bullet'))
			story.append(Spacer(1, 5*mm))
		consistency = self._validate_score_consistency()
		story.append(Paragraph("<u>スコア整合性チェック</u>", h2_style))
		try:
			seo_msg = f"SEO: reported {consistency['seo_total_reported']:.1f} vs expected {consistency['seo_total_expected']:.1f} (Δ {consistency['seo_delta']:.1f})"
			aio_msg = f"AIO: reported {consistency['aio_total_reported']:.1f} vs observed {consistency['aio_total_observed']:.1f} (Δ {consistency['aio_delta']:.1f})"
			integ_msg = f"Integrated: reported {consistency['integrated_reported']:.1f} vs expected {consistency['integrated_expected']:.1f} (Δ {consistency['integrated_delta']:.1f})"
			story.append(Paragraph(seo_msg, normal_style))
			story.append(Paragraph(aio_msg, normal_style))
			story.append(Paragraph(integ_msg, normal_style))
		except Exception:
			pass
		story.append(Spacer(1, 5*mm))
		story.append(Paragraph("<u>2. スコア分析（視覚化）</u>", h1_style))
		_section_break(story, doc.width)
		seo_graph_path = self._create_seo_score_graph()
		if seo_graph_path:
			try:
				story.append(Paragraph("SEOスコア分布", h2_style))
				seo_img = ReportLabImage(seo_graph_path, width=16*cm, height=8*cm)
				story.append(seo_img)
				story.append(PageBreak())
			except Exception:
				pass
		aio_graph_path = self._create_aio_score_graph()
		if aio_graph_path:
			try:
				story.append(Paragraph("AIOスコア分布", h2_style))
				aio_img = ReportLabImage(aio_graph_path, width=16*cm, height=20*cm)
				story.append(aio_img)
				story.append(PageBreak())
			except Exception:
				pass
		story.append(Spacer(1, 5*mm))
		story.append(Paragraph("<u>3. SEO分析結果</u>", h1_style))
		_section_break(story, doc.width)
		seo_res = self.last_analysis_results.get("seo_results", {})
		basics = seo_res.get("basics", {})
		garbled = seo_res.get("garbled", {})
		title_txt = safe_str(basics.get('title'))
		if garbled.get('title'):
			title_txt += " (文字化けの可能性あり)"
		story.append(Paragraph(f"<b>タイトル:</b> {title_txt}", normal_style))
		desc_txt = safe_str(basics.get('meta_description'))
		if garbled.get('meta_description'):
			desc_txt += " (文字化けの可能性あり)"
		story.append(Paragraph(f"<b>メタディスクリプション:</b> {desc_txt}", normal_style))
		story.append(Paragraph(f"<b>タイトル文字数:</b> {basics.get('title_length',0)}", normal_style))
		story.append(Paragraph(f"<b>ディスクリプション文字数:</b> {basics.get('meta_description_length',0)}", normal_style))
		story.append(PageBreak())
		story.append(Paragraph("<u>4. 業界特化分析</u>", h1_style))
		_section_break(story, doc.width)
		aio_res = self.last_analysis_results.get("aio_results", {})
		industry_analysis_result = aio_res.get("industry_analysis", {})
		if industry_analysis_result:
			story.append(Paragraph(f"<b>業界適合度:</b>", h2_style))
			story.append(Paragraph(f"{safe_str(industry_analysis_result.get('industry_fit'))}", normal_style))
			story.append(Spacer(1, 3*mm))
			story.append(Paragraph(f"<b>市場トレンド分析:</b>", h2_style))
			story.append(Paragraph(f"{safe_str(industry_analysis_result.get('market_trends'))}", normal_style))
			story.append(Spacer(1, 3*mm))
			story.append(Paragraph(f"<b>業界特化改善提案:</b>", h2_style))
			story.append(Paragraph(f"{safe_str(industry_analysis_result.get('specialized_improvements'))}", normal_style))
			story.append(Spacer(1, 3*mm))
			story.append(Paragraph(f"<b>規制対応状況:</b>", h2_style))
			story.append(Paragraph(f"{safe_str(industry_analysis_result.get('compliance_check'))}", normal_style))
		story.append(Paragraph("<u>5. 即効改善施策（1-2週間）</u>", h1_style))
		_section_break(story, doc.width)
		for i, action in enumerate(aio_res.get("immediate_actions", []), 1):
			story.append(Paragraph(f"<b>{i}. {safe_str(action.get('action'))}</b>", h2_style))
			story.append(Paragraph(f"<b>実装方法:</b> {safe_str(action.get('method'))}", normal_style))
			story.append(Paragraph(f"<b>期待効果:</b> {safe_str(action.get('expected_impact'))}", normal_style))
			story.append(Spacer(1, 3*mm))
		story.append(Paragraph("<u>6. 中期戦略施策（1-3ヶ月）</u>", h1_style))
		_section_break(story, doc.width)
		for i, strategy in enumerate(aio_res.get("medium_term_strategies", []), 1):
			story.append(Paragraph(f"<b>{i}. {safe_str(strategy.get('strategy'))}</b>", h2_style))
			story.append(Paragraph(f"<b>実装期間:</b> {safe_str(strategy.get('timeline'))}", normal_style))
			story.append(Paragraph(f"<b>期待成果:</b> {safe_str(strategy.get('expected_outcome'))}", normal_style))
			story.append(Spacer(1, 3*mm))
		story.append(Paragraph("<u>7. 競合差別化ポイント</u>", h1_style))
		_section_break(story, doc.width)
		for i, advantage in enumerate(aio_res.get("competitive_advantages", []), 1):
			story.append(Paragraph(f"<b>{i}. {safe_str(advantage.get('advantage'))}</b>", h2_style))
			story.append(Paragraph(f"<b>実装方法:</b> {safe_str(advantage.get('implementation'))}", normal_style))
			story.append(Spacer(1, 3*mm))
		story.append(Paragraph("<u>8. 市場トレンド対応戦略</u>", h1_style))
		_section_break(story, doc.width)
		trend_strategies = aio_res.get("market_trend_strategies", [])
		if trend_strategies:
			for i, ts in enumerate(trend_strategies, 1):
				story.append(Paragraph(f"<b>{i}. トレンド: {safe_str(ts.get('trend'))}</b>", h2_style))
				story.append(Paragraph(f"<b>対応戦略:</b> {safe_str(ts.get('strategy'))}", normal_style))
				story.append(Paragraph(f"<b>優先度:</b> {safe_str(ts.get('priority'))}", normal_style))
				story.append(Spacer(1, 3*mm))
		else:
			story.append(Paragraph("市場トレンド分析データが利用できません。", normal_style))
		story.append(Paragraph("<u>9. 詳細スコア分析</u>", h1_style))
		_section_break(story, doc.width)
		story.append(Paragraph("AIO評価項目詳細", h2_style))
		scores_data = aio_res.get("scores", {})
		story.append(Paragraph("【E-E-A-T及びAI検索最適化項目】", normal_style))
		for key_eng, label_jp in AIO_SCORE_MAP_JP_UPPER.items():
			score_item = scores_data.get(key_eng, {"score":0, "advice":"N/A"})
			story.append(Paragraph(f"<b>{label_jp}: {score_item.get('score',0)}/10</b>", normal_style))
			story.append(Paragraph(f"{score_item.get('advice','N/A')}", normal_style))
			story.append(Spacer(1, 2*mm))
		story.append(Paragraph("【ユーザー体験・技術項目】", normal_style))
		for key_eng, label_jp in AIO_SCORE_MAP_JP_LOWER.items():
			score_item = scores_data.get(key_eng, {"score":0, "advice":"N/A"})
			story.append(Paragraph(f"<b>{label_jp}: {score_item.get('score',0)}/10</b>", normal_style))
			story.append(Paragraph(f"{score_item.get('advice','N/A')}", normal_style))
			story.append(Spacer(1, 2*mm))
		story.append(Paragraph("<u>10. 結論と次のステップ</u>", h1_style))
		_section_break(story, doc.width)
		all_actions = integrated_results.get('improvements', [])
		if all_actions:
			bullet_items = [ListItem(Paragraph(act, normal_style)) for act in all_actions]
			story.append(ListFlowable(bullet_items, bulletType='bullet'))
		story.append(Paragraph("施策実施後は再度分析を行い、数値改善を確認することを推奨します。", normal_style))
		story.append(Spacer(1, 10*mm))
		story.append(Paragraph(f"このレポートは{APP_NAME} v{APP_VERSION}によって生成されました。", centered_style))
		story.append(Paragraph("最新の市場トレンドと業界動向を反映した分析結果です。", centered_style))
		doc.build(story, onFirstPage=_add_corner, onLaterPages=_add_corner)
		return output_path

	def _create_seo_score_graph(self):
		if plt is None or not self.seo_results:
			return None
		scores = self.seo_results.get("scores", {})
		if not scores:
			return None
		labels = [SEO_SCORE_LABELS.get(k, k.replace("_score", "").title()) for k in scores.keys()]
		values = list(scores.values())
		fig, ax = plt.subplots(figsize=(10, 6))
		bars = ax.barh(labels, values, color=COLOR_PALETTE["primary"], height=0.6)
		ax.set_xlim(0, 10)
		ax.set_xlabel("スコア ( /10)", fontsize=12)
		ax.set_title("SEOスコア分布", fontsize=14, fontweight='bold')
		ax.tick_params(axis='y', labelsize=10)
		ax.tick_params(axis='x', labelsize=10)
		ax.invert_yaxis()
		for bar, value in zip(bars, values):
			ax.text(value + 0.1, bar.get_y() + bar.get_height()/2., f"{value:.1f}", va='center', ha='left', fontsize=10)
		plt.tight_layout()
		graph_path = "temp_seo_graph.png"
		plt.savefig(graph_path, dpi=300, bbox_inches='tight')
		plt.close()
		return graph_path

	def _create_aio_score_graph(self):
		if plt is None or not self.aio_results:
			return None
		scores_data = self.aio_results.get("scores", {})
		if not scores_data:
			return None
		labels = [AIO_SCORE_MAP_JP.get(k, k.title()) for k in AIO_SCORE_MAP_JP.keys()]
		values = [scores_data.get(k, {"score": 0}).get("score", 0) for k in AIO_SCORE_MAP_JP.keys()]
		fig, ax = plt.subplots(figsize=(10, 20))
		bars = ax.barh(labels, values, color=COLOR_PALETTE["primary"], height=0.6)
		ax.set_xlim(0, 10)
		ax.set_xlabel("スコア ( /10)", fontsize=12)
		ax.set_title("AIOスコア分布", fontsize=14, fontweight='bold')
		ax.tick_params(axis='y', labelsize=9)
		ax.tick_params(axis='x', labelsize=10)
		ax.invert_yaxis()
		for bar, value in zip(bars, values):
			ax.text(value + 0.1, bar.get_y() + bar.get_height()/2., f"{value:.1f}", va='center', ha='left', fontsize=9)
		plt.tight_layout()
		graph_path = "temp_aio_graph.png"
		plt.savefig(graph_path, dpi=300, bbox_inches='tight')
		plt.close()
		return graph_path