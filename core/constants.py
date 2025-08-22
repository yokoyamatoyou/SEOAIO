# -*- coding: utf-8 -*-
"""Application-wide constants."""

APP_VERSION = "3.0.0"
APP_NAME = "SEO・AIO統合分析ツール"

# OpenAIモデル設定
OPENAI_MODEL = "gpt-4.1-mini-2025-04-14"
OPENAI_TEMPERATURE = 0.1

# インテル風カラースキーム
COLOR_PALETTE = {
    "primary": "#00C7FD",        # Intel Blue
    "secondary": "#00C7FD",      # unify blue shades
    "accent": "#00C7FD",
    "background": "#FFFFFF",
    "surface": "#F5F7FA",
    "text_primary": "#333333",
    "text_secondary": "#555555",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336",
    "info": "#2196F3",
    "gold": "#FF8C00",
    "dark_blue": "#00C7FD",
    "divider": "#E0E0E0",
}

# フォント設定
FONT_STACK = "'Noto Sans JP', 'Meiryo', 'Hiragino Kaku Gothic ProN', 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"

# AIOスコアマッピング
AIO_SCORE_MAP_JP_UPPER = {
    "experience": "経験 (Experience)",
    "expertise": "専門性 (Expertise)",
    "authoritativeness": "権威性 (Authoritativeness)",
    "trustworthiness": "信頼性 (Trustworthiness)",
    "structure": "構造化と整理",
    "qa_compatibility": "質問応答適合性",
    "citation_potential": "AIによる引用可能性",
    "multimodal": "マルチモーダル対応",
}

AIO_SCORE_MAP_JP_LOWER = {
    "search_intent": "検索意図マッチング",
    "personalization": "パーソナライズ可能性",
    "uniqueness": "情報の独自性",
    "completeness": "コンテンツの完全性",
    "readability": "読みやすさスコア",
    "mobile_friendly": "モバイル対応性",
    "page_speed": "ページ速度",
    "metadata": "メタデータ最適化",
}

AIO_SCORE_MAP_JP = {**AIO_SCORE_MAP_JP_UPPER, **AIO_SCORE_MAP_JP_LOWER}

# SEOスコア項目ラベル（日本語）
SEO_SCORE_LABELS = {
    "title_score": "タイトル",
    "meta_description_score": "メタディスクリプション",
    "headings_score": "見出し構造",
    "content_score": "コンテンツ",
    "links_score": "リンク",
    "images_score": "画像",
    "technical_score": "技術要素",
}
