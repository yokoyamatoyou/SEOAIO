import os
import sys
import json
import time
import requests
from bs4 import BeautifulSoup
import tldextract
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
import io
import base64

# Streamlit関連（ImportError時もモジュールimportを継続）
try:
    import streamlit as st
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
except ImportError as e:
    print(f"[WARN] Streamlit/Plotlyインポートエラー: {e}")
    st = None
    go = None
    px = None
    make_subplots = None

# データ可視化関連（ImportError時も継続）
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')
except ImportError as e:
    print(f"[WARN] Matplotlibインポートエラー: {e}")
    plt = None
    matplotlib = None

# 日本語フォント対応（matplotlib利用可能時のみ）
if 'plt' in globals() and plt is not None:
    plt.rcParams['font.family'] = 'sans-serif'
    if os.name == 'nt':
        if os.path.exists('C:/Windows/Fonts/meiryo.ttc'):
            plt.rcParams['font.sans-serif'] = ['Meiryo', 'MS Gothic', 'Yu Gothic', 'sans-serif']
        elif os.path.exists('C:/Windows/Fonts/msgothic.ttc'):
            plt.rcParams['font.sans-serif'] = ['MS Gothic', 'sans-serif']
    elif sys.platform == 'darwin':
        plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'AppleGothic', 'sans-serif']
    else:
        plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'sans-serif']

# PDF生成関連（ImportError時も継続）
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
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError as e:
    print(f"[WARN] ReportLabインポートエラー: {e}")
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
    TA_CENTER = TA_LEFT = TA_RIGHT = None
    pdfmetrics = None
    TTFont = None

# 日本語フォント登録（ReportLab利用可能時のみ）
if 'pdfmetrics' in globals() and pdfmetrics is not None and 'TTFont' in globals() and TTFont is not None:
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
            font_paths_mac = [
                '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
                '/System/Library/Fonts/PingFang.ttc'
            ]
            found_font_mac = False
            for p in font_paths_mac:
                if os.path.exists(p):
                    try:
                        font_name_in_pdf = 'HiraginoSansW3'
                        if 'PingFang' in p:
                            font_name_in_pdf = 'PingFang'
                        pdfmetrics.registerFont(TTFont(font_name_in_pdf, p))
                        DEFAULT_PDF_FONT = font_name_in_pdf
                        found_font_mac = True
                        break
                    except Exception as e_font_mac:
                        print(f"macOSフォント登録試行エラー ({p}): {e_font_mac}")
            if not found_font_mac:
                DEFAULT_PDF_FONT = 'Helvetica'
        else:
            font_paths_noto = [
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.otf',
            ]
            found_font_linux = False
            for p in font_paths_noto:
                if os.path.exists(p):
                    try:
                        pdfmetrics.registerFont(TTFont('NotoSansJP', p))
                        DEFAULT_PDF_FONT = 'NotoSansJP'
                        found_font_linux = True
                        break
                    except Exception as e_font_linux:
                        print(f"Notoフォント登録試行エラー ({p}): {e_font_linux}")
            if not found_font_linux:
                DEFAULT_PDF_FONT = 'Helvetica'
    except Exception as font_error:
        print(f"日本語フォントの登録に失敗しました: {font_error}")
        DEFAULT_PDF_FONT = 'Helvetica'
else:
    DEFAULT_PDF_FONT = 'Helvetica'

try:
    from openai import OpenAI
except ImportError as e:
    print(f"[WARN] OpenAIライブラリインポートエラー: {e}")
    OpenAI = None

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"[WARN] python-dotenvインポートエラー: {e}")
    def load_dotenv(*args, **kwargs):
        return None

# 最初に.envファイルを読み込み（存在する場合）
try:
    if load_dotenv:
        load_dotenv()
        print("[DEBUG] .envファイル読み込み完了")
except Exception as e:
    print(f"[DEBUG] .envファイル読み込みエラー（無視）: {e}")

from core.constants import (
    APP_VERSION,
    APP_NAME,
    COLOR_PALETTE,
    FONT_STACK,
    AIO_SCORE_MAP_JP,
    AIO_SCORE_MAP_JP_UPPER,
    AIO_SCORE_MAP_JP_LOWER,
    SEO_SCORE_LABELS,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
)
from core.ui_components import load_global_styles, primary_button, text_input
from core.industry_detector import IndustryDetector, IndustryAnalysis
from core.visualization import create_aio_score_chart_vertical
from core.text_utils import detect_mojibake

# Streamlitアプリケーション
from core.analysis_engine import AnalysisEngine as CoreAnalysisEngine
SEOAIOAnalyzer = CoreAnalysisEngine

def add_corner(canvas, doc_obj) -> None:
    """Draw a small blue square on page corners."""
    canvas.saveState()
    canvas.setFillColor(colors.HexColor(COLOR_PALETTE["primary"]))
    x = doc_obj.pagesize[0] - 25
    y = doc_obj.pagesize[1] - 25
    canvas.rect(x, y, 15, 15, fill=1, stroke=0)
    canvas.restoreState()


def section_break(story, width) -> None:
    """Insert a thin divider line."""
    line = Table(
        [[""]],
        colWidths=[width],
        style=TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor(COLOR_PALETTE["divider"]))
            ]
        ),
    )
    story.append(Spacer(1, 2 * mm))
    story.append(line)
    story.append(Spacer(1, 2 * mm))



class SEOAIOAnalyzer:
    def __init__(self):
        # 環境変数から直接取得（システム環境変数優先）
        try:
            self.api_key = os.getenv("OPENAI_API_KEY")
            print(f"[DEBUG] システム環境変数からAPIキー取得: {'✓' if self.api_key else '✗'}")
            
            # システム環境変数にない場合は.envファイルからフォールバック
            if not self.api_key:
                try:
                    load_dotenv()
                    self.api_key = os.getenv("OPENAI_API_KEY")
                    print(f"[DEBUG] .envファイルからAPIキー取得: {'✓' if self.api_key else '✗'}")
                except Exception as e:
                    print(f"[DEBUG] .envファイル読み込みエラー: {e}")
            
            if not self.api_key:
                raise ValueError("APIキーが設定されていません。システム環境変数または.envファイルにOPENAI_API_KEYを設定してください。")
            
            print(f"[DEBUG] APIキー長: {len(self.api_key) if self.api_key else 0} 文字")
            
        except Exception as e:
            print(f"[ERROR] APIキー取得エラー: {e}")
            raise ValueError(f"APIキーの初期化に失敗しました: {str(e)}")

        try:
            self.client = OpenAI(api_key=self.api_key)
            print("[DEBUG] OpenAIクライアント初期化成功")
        except Exception as e:
            print(f"[ERROR] OpenAIクライアント初期化エラー: {e}")
            raise ValueError(f"OpenAIクライアントの初期化に失敗しました: {str(e)}")
        
        try:
            self.industry_detector = IndustryDetector()
            print("[DEBUG] 業界検出器初期化成功")
        except Exception as e:
            print(f"[ERROR] 業界検出器初期化エラー: {e}")
            raise ValueError(f"業界検出器の初期化に失敗しました: {str(e)}")
        
        self.last_analysis_results = None
        self.seo_results = None
        self.aio_results = None

    def _scale_to_100(self, value: float) -> float:
        """Normalize a score to 0-100 range."""
        if not isinstance(value, (int, float)):
            return 0.0
        if 0 <= value <= 10:
            return value * 10
        if value > 100:
            return 100.0
        return float(value)

    def analyze_url(self, url, user_industry, balance=50):
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            # API接続テスト
            try:
                self.client.models.list(timeout=10)
                print("API接続テスト成功")
            except Exception as api_error:
                raise Exception(f"OpenAI APIへの接続に失敗しました。APIキーと接続を確認してください。詳細: {str(api_error)}")

            # Webコンテンツ取得
            response = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }, timeout=15)
            response.raise_for_status()
            html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')

            # 業界分析
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag and meta_tag.get('content'):
                meta_desc = meta_tag['content'].strip()
            
            main_content = self._extract_main_content(soup)
            industry_analysis = self.industry_detector.analyze_industries(title, main_content, meta_desc)

            # 最終業界決定
            final_industry = self._determine_final_industry(user_industry, industry_analysis)

            # 分析実行
            self.seo_results = self._analyze_seo(soup, url)
            self.aio_results = self._analyze_aio(soup, url, final_industry, industry_analysis)

            # 統合結果
            seo_weight = (100 - balance) / 100
            aio_weight = balance / 100
            integrated_results = self._integrate_results(
                self.seo_results, self.aio_results, seo_weight, aio_weight
            )

            self.last_analysis_results = {
                "url": url, 
                "user_industry": user_industry,
                "final_industry": final_industry,
                "industry_analysis": industry_analysis,
                "balance": balance,
                "seo_results": self.seo_results, 
                "aio_results": self.aio_results,
                "integrated_results": integrated_results, 
                "timestamp": datetime.now().isoformat()
            }
            return self.last_analysis_results

        except requests.exceptions.Timeout:
            raise Exception(f"URLの取得がタイムアウトしました: {url}")
        except requests.exceptions.RequestException as req_err:
            raise Exception(f"URLの取得に失敗しました ({url}): {str(req_err)}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception(f"分析中に予期せぬエラーが発生しました: {str(e)}")

    def _determine_final_industry(self, user_industry: str, auto_analysis: IndustryAnalysis) -> Dict:
        """最終業界を決定"""
        result = {
            "primary": user_industry if user_industry else auto_analysis.primary_industry,
            "source": "",
            "confidence": 0.0,
            "secondary_detected": auto_analysis.secondary_industries,
            "auto_primary": auto_analysis.primary_industry,
            "auto_confidence": auto_analysis.confidence_score
        }
        
        if user_industry and auto_analysis.confidence_score > 50:
            if user_industry.lower() in auto_analysis.primary_industry.lower():
                result["source"] = "ユーザー入力（自動判定で確認済み）"
                result["confidence"] = 95.0
            else:
                result["source"] = f"ユーザー入力（自動判定: {auto_analysis.primary_industry}）"
                result["confidence"] = 85.0
        elif user_industry:
            result["source"] = "ユーザー入力"
            result["confidence"] = 80.0
        elif auto_analysis.confidence_score > 70:
            result["source"] = f"自動判定（信頼度: {auto_analysis.confidence_score:.1f}%）"
            result["confidence"] = auto_analysis.confidence_score
        else:
            result["primary"] = "指定なし"
            result["source"] = "判定困難"
            result["confidence"] = auto_analysis.confidence_score
            
        return result

    def _extract_main_content(self, soup):
        """メインコンテンツ抽出"""
        for tag in soup.find_all(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form', 'iframe']):
            tag.decompose()

        main_selectors = ['article', 'main', '.main-content', '#content', '#main', '.post-content']
        content_parts = []

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
        """SEO分析"""
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
        heading_texts = {
            f'h{i}': [h.get_text(strip=True) for h in soup.find_all(f'h{i}')][:3]
            for i in range(1, 4)
        }

        # リンク分析
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

        # 画像分析
        images = soup.find_all('img')
        images_with_alt = sum(1 for img in images if img.get('alt', '').strip())
        images_without_alt = len(images) - images_with_alt

        # 技術的要素
        structured_data_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        has_structured_data = len(structured_data_scripts) > 0
        structured_data_types = []
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

        tech_stack = []
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
        stop_words = {
            'the','and','for','with','that','this','you','your','from','are','was','were','have','has','not','but','can','will','his','her','its','she','him','our','out','use','using'
        }
        filtered = [w for w in words if w not in stop_words]
        freq = Counter(filtered)
        top_keywords = freq.most_common(10)

        text_content_all = soup.get_text(separator=' ', strip=True)
        text_html_ratio = (len(text_content_all) / max(len(html_code), 1)) * 100 if html_code else 0

        meta_tags_count = len(soup.find_all('meta'))
        page_size_kb = len(html_code.encode('utf-8', errors='ignore')) / 1024 if html_code else 0

        personalization = {
            "meta": {
                "description": description,
                "keywords": meta_keywords,
                "author": meta_author,
            },
            "ogp": {"title": og_title, "description": og_description, "image": og_image},
            "headings_content": heading_texts,
            "structured_data_types": structured_data_types,
            "top_keywords": top_keywords,
            "tech_stack": tech_stack,
        }

        # スコア計算
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
            "basics": {"title": title, "title_length": len(title), "meta_description": description,
                       "meta_description_length": len(description), "og_title": og_title, "og_description": og_description},
            "structure": {"headings": headings, "internal_links_count": len(internal_links),
                          "external_links_count": len(external_links), "images_count": len(images),
                          "images_with_alt": images_with_alt, "images_without_alt": images_without_alt},
            "technical": {"has_structured_data": has_structured_data, "structured_data_count": len(structured_data_scripts),
                          "canonical_url": canonical_url, "has_viewport": has_viewport,
                          "meta_tags_count": meta_tags_count, "page_size_kb": page_size_kb},
            "content": {"word_count": word_count, "text_html_ratio": text_html_ratio},
            "personalization": personalization,
            "scores": scores, "total_score": total_score,
            "garbled": {"title": garbled_title, "meta_description": garbled_description},
        }

    # SEOスコア計算メソッド群
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
        """AIO分析（GPT-4.1-mini-search-preview使用）"""
        title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
        main_content = self._extract_main_content(soup)
        content_preview = main_content[:7000]

        # 業界情報の整理
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

        try:
            # 固定モデル
            model_name = OPENAI_MODEL
            print(f"[DEBUG] 使用モデル: {model_name}")
            
            # JSON形式を強制
            system_message = """あなたはSEOとAIO（生成AI検索最適化）の専門家です。
必要に応じて最新の市場トレンドを検索して分析結果に含めてください。

**重要**: 回答は必ず有効なJSON形式でのみ返してください。
JSON以外のテキストや説明は一切含めないでください。
回答の最初と最後に```json や ``` などのマークダウンも不要です。
純粋なJSONオブジェクトのみを返してください。"""
            
            # モデル基本パラメータ
            base_params = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": aio_prompt}
                ],
                "timeout": 180,
                "temperature": OPENAI_TEMPERATURE,
                "response_format": {"type": "json_object"}
            }
            
            response = self.client.chat.completions.create(**base_params)

            aio_analysis_str = response.choices[0].message.content
            print(f"[DEBUG] APIレスポンス長: {len(aio_analysis_str) if aio_analysis_str else 0}")
            print(f"[DEBUG] レスポンス最初の200文字: {aio_analysis_str[:200] if aio_analysis_str else 'None'}")
            
            # 空のレスポンスチェック
            if not aio_analysis_str or aio_analysis_str.strip() == "":
                raise Exception("APIから空のレスポンスが返されました")
            
            # JSONパース前の前処理
            aio_analysis_str = aio_analysis_str.strip()
            
            # マークダウンのコードブロックを除去（```json ``` で囲まれている場合）
            if aio_analysis_str.startswith("```json"):
                aio_analysis_str = aio_analysis_str.replace("```json", "").replace("```", "").strip()
            elif aio_analysis_str.startswith("```"):
                aio_analysis_str = aio_analysis_str.replace("```", "").strip()
            
            # JSONオブジェクトの開始を探す
            start_idx = aio_analysis_str.find('{')
            end_idx = aio_analysis_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                aio_analysis_str = aio_analysis_str[start_idx:end_idx+1]
                print(f"[DEBUG] JSON抽出後長: {len(aio_analysis_str)}")
            else:
                print(f"[DEBUG] JSON構造が見つかりません。全レスポンス: {aio_analysis_str}")
                raise Exception("APIレスポンスにJSONオブジェクトが見つかりません")
            
            aio_analysis = json.loads(aio_analysis_str)

        except Exception as model_error:
            print(f"[ERROR] モデル呼出しに失敗: {model_error}")
            raise
        
        try:

            # 結果の正規化
            normalized_result = {
                "basic_info": aio_analysis.get("basic_info", {"url": url, "industry": final_industry['primary'], "title": title}),
                "scores": {},
                "category_scores": aio_analysis.get("category_scores", {}),
                "total_score": aio_analysis.get("total_score", 0.0),
                "immediate_actions": aio_analysis.get("immediate_actions", []),
                "medium_term_strategies": aio_analysis.get("medium_term_strategies", []),
                "competitive_advantages": aio_analysis.get("competitive_advantages", []),
                "market_trend_strategies": aio_analysis.get("market_trend_strategies", []),
                "industry_analysis": aio_analysis.get("industry_analysis", {})
            }

            # スコアの検証
            default_score_advice = {"score": 0, "advice": "APIからのデータなし"}
            for key_score in AIO_SCORE_MAP_JP.keys():
                normalized_result["scores"][key_score] = aio_analysis.get("scores", {}).get(key_score, default_score_advice.copy())

            # total_scoreの検証
            ts = normalized_result["total_score"]
            if not isinstance(ts, (int, float)):
                try:
                    ts = float(ts)
                except (ValueError, TypeError):
                    ts = 0.0
            normalized_result["total_score"] = self._scale_to_100(ts)

            # category_scoresのスケール調整
            categories = {}
            for cat, val in normalized_result.get("category_scores", {}).items():
                categories[cat] = self._scale_to_100(val)
            normalized_result["category_scores"] = categories

            return normalized_result

        except json.JSONDecodeError as json_err:
            print(f"AIO分析結果のJSONパースエラー: {json_err}")
            print(f"[DEBUG] JSONパース失敗したテキスト: {aio_analysis_str[:500] if 'aio_analysis_str' in locals() else 'None'}")
            error_message = f"AI分析結果の形式が不正です: {str(json_err)}"
        except Exception as e:
            import traceback
            print(f"AIO分析中に詳細エラーが発生しました: {str(e)}")
            print(f"[DEBUG] エラー詳細: {traceback.format_exc()}")
            error_message = str(e)

        # エラー時のフォールバックデータ
        default_scores = {key: {"score": 1, "advice": f"APIエラーのため評価できません: {error_message}"} for key in AIO_SCORE_MAP_JP.keys()}
        return {
            "basic_info": {"url": url, "industry": final_industry['primary'], "title": title},
            "scores": default_scores,
            "category_scores": {cat: 10.0 for cat in ["eeat_score", "ai_search_score", "user_experience_score", "technical_score"]},
            "total_score": 10.0,
            "immediate_actions": [{"action": "OpenAI APIの接続と設定を確認してください。", "method": "APIキーとネットワーク設定の確認", "expected_impact": "分析機能の回復"}],
            "medium_term_strategies": [{"strategy": "モデル互換性の確認", "timeline": "即座", "expected_outcome": "search-previewモデルまたは通常モデルでの動作確認"}],
            "competitive_advantages": [],
            "market_trend_strategies": [],
            "industry_analysis": {},
            "error": error_message
        }

    def _integrate_results(self, seo_results, aio_results, seo_weight, aio_weight):
        """統合結果の計算"""
        seo_score = seo_results.get("total_score", 0.0)
        aio_total_score = aio_results.get("total_score", 0.0)

        if not isinstance(aio_total_score, (int, float)):
            try:
                aio_total_score = float(aio_total_score)
            except (ValueError, TypeError):
                aio_total_score = 0.0
        aio_total_score = self._scale_to_100(aio_total_score)

        integrated_score = seo_score * seo_weight + aio_total_score * aio_weight

        # 改善ポイントの統合
        improvements = []
        if aio_total_score < seo_score:
            immediate_actions = aio_results.get("immediate_actions", [])
            improvements.extend([f"AIO優先: {action.get('action', 'N/A')}" for action in immediate_actions[:3]])
            
            if seo_score < 70:
                improvements.append(f"SEO補完: タイトル最適化（現在スコア: {seo_results.get('scores', {}).get('title_score', 0):.1f}/10）")
        else:
            seo_scores = seo_results.get('scores', {})
            low_seo_items = [(k, v) for k, v in seo_scores.items() if v < 7]
            low_seo_items.sort(key=lambda x: x[1])
            
            for item_name, score in low_seo_items[:2]:
                readable_name = item_name.replace("_score", "").replace("_", " ").title()
                improvements.append(f"SEO優先: {readable_name}の改善（現在スコア: {score:.1f}/10）")
            
            immediate_actions = aio_results.get("immediate_actions", [])
            if immediate_actions:
                improvements.append(f"AIO補完: {immediate_actions[0].get('action', 'N/A')}")

        # 推奨バランスの計算
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
            "recommended_balance": {
                "seo_focus": recommended_seo_focus,
                "aio_focus": recommended_aio_focus
            }
        }

    def _validate_score_consistency(self):
        """SEO/AIO/統合スコアの整合性を簡易検証して返す。"""
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
            # SEO expected
            seo_scores = (self.seo_results or {}).get("scores", {})
            if seo_scores:
                seo_expected = (sum(seo_scores.values()) / max(len(seo_scores), 1)) * 10.0
            else:
                seo_expected = 0.0
            seo_reported = (self.seo_results or {}).get("total_score", 0.0)
            results["seo_total_expected"], results["seo_total_reported"] = seo_expected, seo_reported
            results["seo_delta"] = float(seo_reported) - float(seo_expected)

            # AIO observed average (各項目0-10の平均×10 => 0-100換算)
            aio_scores_map = (self.aio_results or {}).get("scores", {})
            aio_item_scores = [v.get("score", 0) for v in aio_scores_map.values()] if aio_scores_map else []
            aio_observed = (sum(aio_item_scores) / max(len(aio_item_scores), 1)) * 10.0 if aio_item_scores else 0.0
            aio_reported = (self.aio_results or {}).get("total_score", 0.0)
            results["aio_total_observed"], results["aio_total_reported"] = aio_observed, aio_reported
            results["aio_delta"] = float(aio_reported) - float(aio_observed)

            # Integrated expected (balanceに基づく重み)
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

    def generate_enhanced_pdf_report(self, output_path, logo_path=None):
        """強化版PDF生成（グラフ含む）"""
        if not self.last_analysis_results:
            raise ValueError("分析結果がありません。分析を先に実行してください。")

        def safe_str(value, default=""):
            return str(value) if value is not None else default

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )


        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['h1'],
            fontName=DEFAULT_PDF_FONT,
            fontSize=22,
            alignment=TA_CENTER,
            spaceAfter=6*mm,
            textColor=colors.HexColor(COLOR_PALETTE["secondary"]),
        )
        h1_style = ParagraphStyle(
            'DocH1',
            parent=styles['h1'],
            fontName=DEFAULT_PDF_FONT,
            fontSize=16,
            spaceBefore=6*mm,
            spaceAfter=3*mm,
            textColor=colors.HexColor(COLOR_PALETTE["primary"]),
        )
        h2_style = ParagraphStyle(
            'DocH2',
            parent=styles['h2'],
            fontName=DEFAULT_PDF_FONT,
            fontSize=14,
            spaceBefore=4*mm,
            spaceAfter=2*mm,
            textColor=colors.HexColor(COLOR_PALETTE["secondary"]),
        )
        normal_style = ParagraphStyle(
            'DocNormal',
            parent=styles['Normal'],
            fontName=DEFAULT_PDF_FONT,
            fontSize=10,
            spaceAfter=2*mm,
            leading=14,
            textColor=colors.HexColor(COLOR_PALETTE["text_primary"]),
        )
        centered_style = ParagraphStyle('DocCentered', parent=normal_style, alignment=TA_CENTER, fontName=DEFAULT_PDF_FONT)

        story = []


        # ロゴ
        if logo_path and os.path.exists(logo_path):
            try:
                img = ReportLabImage(logo_path, width=40*mm, height=15*mm)
                story.append(img)
                story.append(Spacer(1, 2*mm))
            except Exception as e:
                print(f"ロゴ画像の読み込みに失敗: {e}")

        # タイトル
        story.append(Paragraph(f"{APP_NAME} 詳細分析レポート", title_style))
        story.append(Paragraph(f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}", centered_style))
        story.append(Spacer(1, 6*mm))

        # 1. エグゼクティブサマリー
        story.append(Paragraph("<u>1. エグゼクティブサマリー</u>", h1_style))
        section_break(story, doc.width)
        story.append(Paragraph(f"<b>対象URL:</b> {self.last_analysis_results['url']}", normal_style))
        
        final_industry = self.last_analysis_results['final_industry']
        industry_analysis = self.last_analysis_results['industry_analysis']
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

        # スコア整合性チェック
        consistency = self._validate_score_consistency()
        story.append(Paragraph("<u>スコア整合性チェック</u>", h2_style))
        try:
            seo_msg = f"SEO: reported {consistency['seo_total_reported']:.1f} vs expected {consistency['seo_total_expected']:.1f} (Δ {consistency['seo_delta']:.1f})"
            aio_msg = f"AIO: reported {consistency['aio_total_reported']:.1f} vs observed {consistency['aio_total_observed']:.1f} (Δ {consistency['aio_delta']:.1f})"
            integ_msg = f"Integrated: reported {consistency['integrated_reported']:.1f} vs expected {consistency['integrated_expected']:.1f} (Δ {consistency['integrated_delta']:.1f})"
            story.append(Paragraph(seo_msg, normal_style))
            story.append(Paragraph(aio_msg, normal_style))
            story.append(Paragraph(integ_msg, normal_style))
            # しきい値超過時の注意
            warn = []
            if abs(consistency.get('seo_delta') or 0) > 2.0:
                warn.append("SEOスコアに再計算値とのズレがあります。")
            if abs(consistency.get('aio_delta') or 0) > 2.0:
                warn.append("AIOスコア（AI出力）と観測平均にズレがあります。")
            if abs(consistency.get('integrated_delta') or 0) > 2.0:
                warn.append("統合スコアと重み付き再計算にズレがあります。")
            for w in warn:
                story.append(Paragraph(f"<b>注意:</b> {w}", normal_style))
            story.append(Spacer(1, 5*mm))
        except Exception:
            pass

        # スコア分布グラフの追加
        story.append(Paragraph("<u>2. スコア分析（視覚化）</u>", h1_style))
        section_break(story, doc.width)
        
        # SEOスコアグラフを生成
        seo_graph_path = self._create_seo_score_graph()
        if seo_graph_path:
            story.append(Paragraph("SEOスコア分布", h2_style))
            try:
                seo_img = ReportLabImage(seo_graph_path, width=16*cm, height=8*cm)
                story.append(seo_img)
                story.append(PageBreak())
            except Exception as e:
                print(f"SEOグラフ挿入エラー: {e}")

        # AIOスコアグラフを生成
        aio_graph_path = self._create_aio_score_graph()
        if aio_graph_path:
            story.append(Paragraph("AIOスコア分布", h2_style))
            try:
                aio_img = ReportLabImage(aio_graph_path, width=16*cm, height=20*cm)
                story.append(aio_img)
                story.append(PageBreak())
            except Exception as e:
                print(f"AIOグラフ挿入エラー: {e}")

        story.append(Spacer(1, 5*mm))

        # 3. SEO分析結果
        story.append(Paragraph("<u>3. SEO分析結果</u>", h1_style))
        section_break(story, doc.width)
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
        story.append(Paragraph(
            "これらのスコアは検索結果での表示最適化に影響します。値が低い項目は優先的に調整してください。",
            normal_style))

        story.append(PageBreak())

        # 4. 業界特化分析
        story.append(Paragraph("<u>4. 業界特化分析</u>", h1_style))
        section_break(story, doc.width)
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

        # 5. 即効改善施策（詳細版）
        story.append(Paragraph("<u>5. 即効改善施策（1-2週間）</u>", h1_style))
        section_break(story, doc.width)
        immediate_actions = aio_res.get("immediate_actions", [])
        for i, action in enumerate(immediate_actions, 1):
            story.append(Paragraph(f"<b>{i}. {safe_str(action.get('action'))}</b>", h2_style))
            story.append(Paragraph(f"<b>実装方法:</b> {safe_str(action.get('method'))}", normal_style))
            story.append(Paragraph(f"<b>期待効果:</b> {safe_str(action.get('expected_impact'))}", normal_style))
            story.append(Spacer(1, 3*mm))

        # 6. 中期戦略施策
        story.append(Paragraph("<u>6. 中期戦略施策（1-3ヶ月）</u>", h1_style))
        section_break(story, doc.width)
        medium_term_strategies = aio_res.get("medium_term_strategies", [])
        for i, strategy in enumerate(medium_term_strategies, 1):
            story.append(Paragraph(f"<b>{i}. {safe_str(strategy.get('strategy'))}</b>", h2_style))
            story.append(Paragraph(f"<b>実装期間:</b> {safe_str(strategy.get('timeline'))}", normal_style))
            story.append(Paragraph(f"<b>期待成果:</b> {safe_str(strategy.get('expected_outcome'))}", normal_style))
            story.append(Spacer(1, 3*mm))

        story.append(PageBreak())

        # 7. 競合差別化ポイント（詳細版）
        story.append(Paragraph("<u>7. 競合差別化ポイント</u>", h1_style))
        section_break(story, doc.width)
        competitive_advantages = aio_res.get("competitive_advantages", [])
        for i, advantage in enumerate(competitive_advantages, 1):
            story.append(Paragraph(f"<b>{i}. {safe_str(advantage.get('advantage'))}</b>", h2_style))
            story.append(Paragraph(f"<b>実装方法:</b> {safe_str(advantage.get('implementation'))}", normal_style))
            story.append(Spacer(1, 3*mm))

        # 8. 市場トレンド対応戦略（新機能）
        story.append(Paragraph("<u>8. 市場トレンド対応戦略</u>", h1_style))
        section_break(story, doc.width)
        market_trend_strategies = aio_res.get("market_trend_strategies", [])
        if market_trend_strategies:
            for i, trend_strategy in enumerate(market_trend_strategies, 1):
                story.append(Paragraph(f"<b>{i}. トレンド: {safe_str(trend_strategy.get('trend'))}</b>", h2_style))
                story.append(Paragraph(f"<b>対応戦略:</b> {safe_str(trend_strategy.get('strategy'))}", normal_style))
                story.append(Paragraph(f"<b>優先度:</b> {safe_str(trend_strategy.get('priority'))}", normal_style))
                story.append(Spacer(1, 3*mm))
        else:
            story.append(Paragraph("市場トレンド分析データが利用できません。", normal_style))

        # 9. 詳細スコア分析
        story.append(Paragraph("<u>9. 詳細スコア分析</u>", h1_style))
        section_break(story, doc.width)
        
        # AIOスコア詳細
        story.append(Paragraph("AIO評価項目詳細", h2_style))
        scores_data = aio_res.get("scores", {})
        
        # 上位8項目
        story.append(Paragraph("【E-E-A-T及びAI検索最適化項目】", normal_style))
        for key_eng, label_jp in AIO_SCORE_MAP_JP_UPPER.items():
            score_item = scores_data.get(key_eng, {"score":0, "advice":"N/A"})
            story.append(Paragraph(f"<b>{label_jp}: {score_item.get('score',0)}/10</b>", normal_style))
            story.append(Paragraph(f"{score_item.get('advice','N/A')}", normal_style))
            story.append(Spacer(1, 2*mm))

        story.append(Spacer(1, 3*mm))
        
        # 下位8項目
        story.append(Paragraph("【ユーザー体験・技術項目】", normal_style))
        for key_eng, label_jp in AIO_SCORE_MAP_JP_LOWER.items():
            score_item = scores_data.get(key_eng, {"score":0, "advice":"N/A"})
            story.append(Paragraph(f"<b>{label_jp}: {score_item.get('score',0)}/10</b>", normal_style))
            story.append(Paragraph(f"{score_item.get('advice','N/A')}", normal_style))
            story.append(Spacer(1, 2*mm))

        story.append(PageBreak())

        # 10. 結論と次のステップ
        story.append(Paragraph("<u>10. 結論と次のステップ</u>", h1_style))
        section_break(story, doc.width)
        story.append(Paragraph(
            "本レポートではSEOとAIOの両面から課題を抽出しました。以下の優先アクションに沿って改善を進めてください。",
            normal_style))

        all_actions = integrated_results.get('improvements', [])
        if all_actions:
            bullet_items = [ListItem(Paragraph(act, normal_style)) for act in all_actions]
            story.append(ListFlowable(bullet_items, bulletType='bullet'))

        story.append(Paragraph(
            "施策実施後は再度分析を行い、数値改善を確認することを推奨します。",
            normal_style))

        # フッター
        story.append(Spacer(1, 10*mm))
        story.append(Paragraph(f"このレポートは{APP_NAME} v{APP_VERSION}によって生成されました。", centered_style))
        story.append(Paragraph("最新の市場トレンドと業界動向を反映した分析結果です。", centered_style))

        try:
            doc.build(story, onFirstPage=add_corner, onLaterPages=add_corner)
            return output_path
        except Exception as e_build:
            print(f"PDFのビルド中にエラーが発生しました: {str(e_build)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"PDFのビルドエラー: {str(e_build)}")

    def _create_seo_score_graph(self):
        """SEOスコアグラフ生成"""
        try:
            if not self.seo_results:
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
                ax.text(value + 0.1, bar.get_y() + bar.get_height()/2., f"{value:.1f}",
                        va='center', ha='left', fontsize=10)

            plt.tight_layout()
            
            graph_path = "temp_seo_graph.png"
            plt.savefig(graph_path, dpi=300, bbox_inches='tight')
            plt.close()
            return graph_path
            
        except Exception as e:
            print(f"SEOグラフ生成エラー: {e}")
            return None

    def _create_aio_score_graph(self):
        """AIOスコアグラフ生成（縦長・拡大版）"""
        try:
            if not self.aio_results:
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
                ax.text(value + 0.1, bar.get_y() + bar.get_height()/2., f"{value:.1f}",
                        va='center', ha='left', fontsize=9)

            plt.tight_layout()
            
            graph_path = "temp_aio_graph.png"
            plt.savefig(graph_path, dpi=300, bbox_inches='tight')
            plt.close()
            return graph_path
            
        except Exception as e:
            print(f"AIOグラフ生成エラー: {e}")
            return None

# Streamlitアプリケーション
def set_custom_css():
    """Apply global design CSS."""
    load_global_styles()
    st.markdown(
        f"""
        <style>
        .css-1d391kg {{
            background-color: {COLOR_PALETTE['surface']};
            border-right: 1px solid {COLOR_PALETTE['divider']};
        }}
        [data-testid='metric-container'] {{
            background-color: {COLOR_PALETTE['surface']};
            border: 1px solid {COLOR_PALETTE['divider']};
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .stTabs [data-baseweb='tab-list'] {{
            background-color: {COLOR_PALETTE['surface']};
            gap: 8px;
        }}
        .stTabs [data-baseweb='tab'] {{
            background-color: {COLOR_PALETTE['primary']};
            color: {COLOR_PALETTE['background']};
            border-radius: 8px 8px 0 0;
        }}
        .stTabs [aria-selected='true'] {{
            background-color: {COLOR_PALETTE['accent']} !important;
            color: #fff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    # ページ設定
    st.set_page_config(
        page_title="SEO・AIO統合分析ツール",
        page_icon="◻",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # カスタムCSS適用
    set_custom_css()
    
    # タイトル
    st.title("SEO・AIO統合分析ツール")
    st.markdown(f"*{APP_NAME} v{APP_VERSION} - モダンUIデザイン*")
    with st.expander("アプリ説明"):
        st.markdown(
            "<div class='explanation-section'>本ツールはSEOとAIOの視点からサイト\n分析を行い、改善ポイントを提示します。\nサイドバーで設定を入力し、結果を確認してください。</div>",
            unsafe_allow_html=True,
        )
    
    # Analyzerの初期化
    if 'analyzer' not in st.session_state:
        try:
            st.session_state.analyzer = SEOAIOAnalyzer()
            
            # APIキーの取得確認（初期化後）
            if hasattr(st.session_state.analyzer, 'api_key') and st.session_state.analyzer.api_key:
                # APIキーの取得元を確認
                try:
                    sys_env_key = os.getenv("OPENAI_API_KEY")
                    if sys_env_key and sys_env_key == st.session_state.analyzer.api_key:
                        api_source = "システム環境変数"
                    else:
                        api_source = ".envファイル"
                except Exception:
                    api_source = "不明"
                
                st.success(f"APIキーを{api_source}から正常に取得しました (文字数: {len(st.session_state.analyzer.api_key)})")
                st.info(f"使用モデル: gpt-4o-mini-search-preview (自動フォールバック: gpt-4o-mini)")
                st.info(f"両モデル対応: temperature・response_formatパラメータ自動調整")
            else:
                st.warning("APIキーが設定されていません")
                
        except ValueError as e:
            st.error(f"初期化エラー: {str(e)}")
            st.stop()
        except Exception as e:
            st.error(f"予期しないエラー: {str(e)}")
            st.stop()
    
    # サイドバー: 入力フォーム
    with st.sidebar:
        st.header("分析設定")
        
        # URL入力
        url = text_input(
            "分析対象URL",
            placeholder="https://www.example.com",
            help="分析したいウェブサイトのURLを入力してください"
        )
        
        # 業界/分野入力
        industry = text_input(
            "業界/分野（オプション）",
            placeholder="例: IT, 教育, 不動産",
            help="空白の場合は自動判定されます"
        )
        
        # 分析バランス
        balance = st.slider(
            "分析バランス（SEO ← → AIO）",
            min_value=0,
            max_value=100,
            value=50,
            help="SEO重視(0)からAIO重視(100)までの比重"
        )
        
        st.markdown(f"**現在の設定:** SEO {100-balance}% - AIO {balance}%")
        
        # 業界判定ボタン
        if primary_button("業界判定のみ"):
            if url:
                with st.spinner("業界を判定中..."):
                    try:
                        # 簡易業界判定
                        response = requests.get(url if url.startswith(('http://', 'https://')) else 'https://' + url, 
                                              headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title = soup.title.string.strip() if soup.title and soup.title.string else ""
                        meta_desc = ""
                        meta_tag = soup.find('meta', attrs={'name': 'description'})
                        if meta_tag and meta_tag.get('content'):
                            meta_desc = meta_tag['content'].strip()
                        
                        main_content = st.session_state.analyzer._extract_main_content(soup)
                        industry_analysis = st.session_state.analyzer.industry_detector.analyze_industries(title, main_content, meta_desc)
                        
                        st.success(f"**判定結果:** {industry_analysis.primary_industry}")
                        st.info(f"**信頼度:** {industry_analysis.confidence_score:.1f}%")
                        if industry_analysis.secondary_industries:
                            st.info(f"**副業界:** {', '.join(industry_analysis.secondary_industries[:2])}")
                            
                    except Exception as e:
                        st.error(f"業界判定エラー: {str(e)}")
            else:
                st.warning("URLを入力してください")
        
        # 分析実行ボタン
        analyze_clicked = primary_button("分析開始")
    
    # メインエリア
    if analyze_clicked and url:
        with st.spinner("詳細分析を実行中... しばらくお待ちください"):
            try:
                # 分析実行
                results = st.session_state.analyzer.analyze_url(url, industry, balance)
                st.session_state.analysis_results = results
                st.success("分析が完了しました！")
                
            except Exception as e:
                st.error(f"❌ 分析エラー: {str(e)}")
                st.stop()
    
    # 結果表示
    if 'analysis_results' in st.session_state:
        results = st.session_state.analysis_results
        
        # タブ作成
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["概要", "AIO分析", "SEO分析", "業界分析", "統合レポート"])
        
        with tab1:  # 概要
            st.markdown("<div class='function-section'>", unsafe_allow_html=True)
            st.header("分析概要")
            
            # スコア表示（メーター削除）
            col1, col2, col3 = st.columns(3)

            integrated_results = results.get("integrated_results", {})

            with col1:
                st.metric("SEOスコア", f"{integrated_results.get('seo_score', 0):.1f}/100")

            with col2:
                st.metric("AIOスコア", f"{integrated_results.get('aio_score', 0):.1f}/100")

            with col3:
                st.metric("総合スコア", f"{integrated_results.get('integrated_score', 0):.1f}/100")
            
            # 推奨改善ポイント
            st.subheader("推奨改善ポイント")
            for i, improvement in enumerate(integrated_results.get("improvements", []), 1):
                st.write(f"{i}. {improvement}")
            
            # 推奨バランス
            rec_balance = integrated_results.get('recommended_balance', {})
            st.subheader("推奨分析バランス")
            st.write(f"SEO {rec_balance.get('seo_focus', 50)}% - AIO {rec_balance.get('aio_focus', 50)}%")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab2:  # AIO分析
            st.header("AIO（生成AI検索最適化）分析")
            
            aio_results = results.get("aio_results", {})
            scores_data = aio_results.get("scores", {})
            
            # 上位8項目
            st.subheader("E-E-A-T & AI検索最適化項目")
            fig_upper = create_aio_score_chart_vertical(scores_data, AIO_SCORE_MAP_JP_UPPER, "E-E-A-T & AI検索最適化スコア")
            st.plotly_chart(fig_upper, use_container_width=True)
            
            # 上位8項目のコメント
            with st.expander("E-E-A-T & AI検索最適化項目 詳細コメント"):
                for key_eng, label_jp in AIO_SCORE_MAP_JP_UPPER.items():
                    score_item = scores_data.get(key_eng, {"score": 0, "advice": "N/A"})
                    st.write(f"**{label_jp} ({score_item.get('score', 0)}/10)**")
                    st.write(score_item.get('advice', 'N/A'))
                    st.write("---")
            
            # 下位8項目
            st.subheader("ユーザー体験 & 技術項目")
            fig_lower = create_aio_score_chart_vertical(scores_data, AIO_SCORE_MAP_JP_LOWER, "ユーザー体験 & 技術スコア")
            st.plotly_chart(fig_lower, use_container_width=True)
            
            # 下位8項目のコメント
            with st.expander("ユーザー体験 & 技術項目 詳細コメント"):
                for key_eng, label_jp in AIO_SCORE_MAP_JP_LOWER.items():
                    score_item = scores_data.get(key_eng, {"score": 0, "advice": "N/A"})
                    st.write(f"**{label_jp} ({score_item.get('score', 0)}/10)**")
                    st.write(score_item.get('advice', 'N/A'))
                    st.write("---")
            
            # 改善施策
            st.subheader("即効改善施策")
            for i, action in enumerate(aio_results.get("immediate_actions", []), 1):
                with st.expander(f"{i}. {action.get('action', 'N/A')}"):
                    st.write(f"**実装方法:** {action.get('method', 'N/A')}")
                    st.write(f"**期待効果:** {action.get('expected_impact', 'N/A')}")
            
            # 市場トレンド対応
            if aio_results.get("market_trend_strategies"):
                st.subheader("市場トレンド対応戦略")
                for i, trend in enumerate(aio_results.get("market_trend_strategies", []), 1):
                    with st.expander(f"{i}. {trend.get('trend', 'N/A')}"):
                        st.write(f"**対応戦略:** {trend.get('strategy', 'N/A')}")
                        st.write(f"**優先度:** {trend.get('priority', 'N/A')}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with tab3:  # SEO分析
            st.markdown("<div class='function-section'>", unsafe_allow_html=True)
            st.header("SEO分析")
            
            seo_results = results.get("seo_results", {})
            
            # SEOスコア分布グラフ
            seo_scores = seo_results.get("scores", {})
            if seo_scores:
                labels = [SEO_SCORE_LABELS.get(k, k.replace("_score", "").title()) for k in seo_scores.keys()]
                values = list(seo_scores.values())
                
                fig_seo_detail = go.Figure(data=[go.Bar(
                    x=labels,
                    y=values,
                    marker=dict(color=COLOR_PALETTE["primary"]),
                    text=[f'{v:.1f}' for v in values],
                    textposition='outside',
                    hovertemplate='%{x}：%{y:.1f}点'
                )])
                
                fig_seo_detail.update_layout(
                    title="SEOスコア詳細分布",
                    title_font_color=COLOR_PALETTE["dark_blue"],
                    paper_bgcolor=COLOR_PALETTE["background"],
                    plot_bgcolor=COLOR_PALETTE["background"],
                    font={'color': COLOR_PALETTE["text_primary"]},
                    hoverlabel=dict(font_size=12),
                    yaxis=dict(range=[0, 10], title="スコア (/10)"),
                    xaxis=dict(title="評価項目")
                )
                
                st.plotly_chart(fig_seo_detail, use_container_width=True)
            
            # SEO詳細情報
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("基本SEO情報")
                basics = seo_results.get("basics", {})
                garbled = seo_results.get("garbled", {})
                title_txt = basics.get('title', 'N/A')
                if garbled.get('title'):
                    st.error("タイトルが文字化けしている可能性があります")
                st.write(f"**タイトル:** {title_txt} ({basics.get('title_length', 0)}文字)")

                desc_txt = basics.get('meta_description', 'N/A')
                if garbled.get('meta_description'):
                    st.error("メタディスクリプションが文字化けしている可能性があります")
                st.write(f"**メタディスクリプション:** {desc_txt} ({basics.get('meta_description_length', 0)}文字)")
                
            with col2:
                st.subheader("ページ構造")
                structure = seo_results.get("structure", {})
                st.write(f"**内部リンク数:** {structure.get('internal_links_count', 0)}")
                st.write(f"**外部リンク数:** {structure.get('external_links_count', 0)}")
                st.write(f"**画像数:** {structure.get('images_count', 0)}")
                st.write(f"**Alt属性付き画像:** {structure.get('images_with_alt', 0)}")
            
            # 技術的SEO
            st.subheader("技術的SEO")
            technical = seo_results.get("technical", {})
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("構造化データ", "あり" if technical.get('has_structured_data') else "なし")
            with col2:
                st.metric("ビューポートタグ", "あり" if technical.get('has_viewport') else "なし")  
            with col3:
                st.metric("ページサイズ", f"{technical.get('page_size_kb', 0):.1f} KB")

            # パーソナライズ情報
            personalization = seo_results.get("personalization", {})
            if personalization:
                st.subheader("パーソナライズ情報")
                meta = personalization.get("meta", {})
                st.write(f"**Meta Description:** {meta.get('description', 'N/A')}")
                if meta.get('keywords'):
                    st.write(f"**Meta Keywords:** {meta.get('keywords')}")
                if meta.get('author'):
                    st.write(f"**Author:** {meta.get('author')}")

                ogp = personalization.get("ogp", {})
                if any(ogp.values()):
                    st.write("**OGP情報**")
                    st.write(f"Title: {ogp.get('title','N/A')}")
                    st.write(f"Description: {ogp.get('description','N/A')}")
                    st.write(f"Image: {ogp.get('image','N/A')}")

                headings_c = personalization.get("headings_content", {})
                for h, texts in headings_c.items():
                    if texts:
                        st.write(f"**{h.upper()}例:** " + ", ".join(texts))

                if personalization.get("top_keywords"):
                    st.write("**主要キーワード頻度**")
                    for w,c in personalization["top_keywords"]:
                        st.write(f"{w}: {c}")

                if personalization.get("tech_stack"):
                    st.write("**使用技術の手がかり:** " + ", ".join(personalization["tech_stack"]))
            st.markdown("</div>", unsafe_allow_html=True)

        with tab4:  # 業界分析
            st.markdown("<div class='function-section'>", unsafe_allow_html=True)
            st.header("業界特化分析")
            
            final_industry = results.get('final_industry', {})
            industry_analysis = results.get('industry_analysis', {})
            
            # 業界判定結果
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("主要業界", final_industry.get('primary', 'N/A'))
                st.metric("判定信頼度", f"{final_industry.get('confidence', 0):.1f}%")
                
            with col2:
                st.markdown(f"**判定根拠:** {final_industry.get('source', 'N/A')}")
                if final_industry.get('secondary_detected'):
                    st.write(f"**副業界:** {', '.join(final_industry['secondary_detected'][:3])}")
            
            # 業界特化分析詳細
            aio_industry_analysis = aio_results.get("industry_analysis", {})
            if aio_industry_analysis:
                st.subheader("業界適合度分析")
                st.write(aio_industry_analysis.get('industry_fit', 'N/A'))
                
                st.subheader("市場トレンド分析")
                st.write(aio_industry_analysis.get('market_trends', 'N/A'))
                
                st.subheader("業界特化改善提案")
                st.write(aio_industry_analysis.get('specialized_improvements', 'N/A'))
                
                st.subheader("規制・コンプライアンス対応")
                st.write(aio_industry_analysis.get('compliance_check', 'N/A'))
            st.markdown("</div>", unsafe_allow_html=True)

        with tab5:  # 統合レポート
            st.markdown("<div class='function-section'>", unsafe_allow_html=True)
            st.header("統合レポート")
            
            # レポート概要
            st.subheader("レポート概要")
            st.write(f"**分析URL:** {results.get('url', 'N/A')}")
            st.write(f"**業界:** {final_industry.get('primary', 'N/A')} ({final_industry.get('source', 'N/A')})")
            st.write(f"**分析バランス:** SEO {100-results.get('balance', 50)}% - AIO {results.get('balance', 50)}%")
            st.write(f"**総合スコア:** {integrated_results.get('integrated_score', 0):.1f}/100")
            
            # PDF生成ボタン
            if st.button("詳細PDFレポート生成", use_container_width=True):
                try:
                    with st.spinner("PDFレポートを生成中..."):
                        # 一時ファイル名
                        pdf_filename = f"seo_aio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        
                        # PDF生成
                        pdf_path = st.session_state.analyzer.generate_enhanced_pdf_report(pdf_filename)
                        
                        # PDFファイルの読み込み
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_data = pdf_file.read()
                        
                        # ダウンロードボタン
                        st.download_button(
                            label="PDFレポートをダウンロード",
                            data=pdf_data,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
                        
                        st.success("PDFレポートが生成されました！")
                        
                        # 一時ファイル削除
                        import os
                        if os.path.exists(pdf_path):
                            os.remove(pdf_path)
                            
                except Exception as e:
                    st.error(f"❌ PDFレポート生成エラー: {str(e)}")
            
            # 競合差別化ポイント
            st.subheader("競合差別化ポイント")
            for i, advantage in enumerate(aio_results.get("competitive_advantages", []), 1):
                st.write(f"{i}. **{advantage.get('advantage', 'N/A')}**")
                st.write(f"   実装方法: {advantage.get('implementation', 'N/A')}")
            
            # 中期戦略
            st.subheader("中期戦略（1-3ヶ月）")
            for i, strategy in enumerate(aio_results.get("medium_term_strategies", []), 1):
                st.write(f"{i}. **{strategy.get('strategy', 'N/A')}**")
                st.write(f"   期間: {strategy.get('timeline', 'N/A')}")
                st.write(f"   期待成果: {strategy.get('expected_outcome', 'N/A')}")
            st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        # 初期状態の表示
        st.info("サイドバーからURLを入力して分析を開始してください")

        # 機能説明
        with st.expander("ツール概要"):
            st.markdown("<div class='explanation-section'>", unsafe_allow_html=True)
            st.markdown("""
        ## SEO・AIO統合分析ツールについて
        
        このツールは、従来のSEO分析と最新のAIO（生成AI検索最適化）分析を統合した
        次世代のウェブサイト分析プラットフォームです。
        
        ### 主な機能
        
        - **業界自動判定**: コンテンツから業界を自動識別
        - **SEO分析**: 従来のSEO指標を詳細分析
        - **AIO分析**: 生成AI検索エンジンに最適化された分析
        - **市場トレンド分析**: 最新の業界動向を反映 (GPT-4o-mini-search-preview)
        - **詳細PDFレポート**: グラフ付きの包括的レポート生成
        - **モダンUI**: グレー基調の洗練されたデザイン
        
        ### 分析項目
        
        **SEO分析**
        - タイトル・メタディスクリプション最適化
        - 見出し構造・リンク分析
        - 画像最適化・技術的SEO
        
        **AIO分析（16項目）**
        - E-E-A-T評価（Experience, Expertise, Authoritativeness, Trustworthiness）
        - AI検索最適化（構造化、質問応答適合性、引用可能性）
        - ユーザー体験（検索意図マッチング、独自性、完全性）
        - 技術指標（モバイル対応、ページ速度、メタデータ）
        
        ### デザインテーマ
        グレー基調のモダンテーマを採用し、
        視認性が高く洗練されたユーザーインターフェースを提供します。
        
        ### 技術的特徴
        - **環境変数優先**: システム環境変数からAPIキーを取得（.envファイルもサポート）
        - **マルチモデル対応**: GPT-4o-mini-search-preview（市場トレンド分析）+ GPT-4o-mini（フォールバック）
        - **自動パラメータ調整**: モデル特性に応じてtemperature・response_format自動調整
        - **エラーハンドリング**: 詳細なデバッグ情報とエラー回復機能
        - **JSON応答処理**: マークダウン除去・構造抽出による堅牢な解析
        """)

            st.markdown("""
        ### 使用方法
        1. **URL入力**: 分析したいウェブサイトのURLを入力
        2. **業界指定**: 業界を手動入力するか、自動判定を利用
        3. **バランス調整**: SEOとAIOの分析比重を調整
        4. **分析実行**: 「分析開始」ボタンをクリック
        5. **結果確認**: タブ別に詳細結果を確認
        6. **レポート生成**: PDFで詳細レポートをダウンロード
            """)
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    # 環境変数チェック（システム環境変数優先）
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            st.error("OpenAI APIキーが設定されていません。\n\n以下のいずれかの方法で設定してください：\n\n1. **システム環境変数** (推奨)\n   - コンピュータのシステム環境変数にOPENAI_API_KEYを設定\n\n2. **.envファイル**\n   - プロジェクトフォルダに.envファイルを作成してOPENAI_API_KEYを設定")
            st.stop()
        
        main()
        
    except Exception as e:
        st.error(f"アプリケーション起動エラー: {str(e)}")
        st.error("詳細: APIキーの設定を確認し、必要な依存関係がインストールされているか確認してください。")
        import traceback
        st.code(traceback.format_exc())
        st.stop()