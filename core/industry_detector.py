# -*- coding: utf-8 -*-
"""Industry detection utilities."""
from dataclasses import dataclass
from typing import List

@dataclass
class IndustryAnalysis:
    """業界分析結果"""
    primary_industry: str
    secondary_industries: List[str]
    confidence_score: float
    industry_keywords: List[str]
    specialized_terms: List[str]
    regulatory_indicators: List[str]
    target_audience_clues: List[str]

class IndustryDetector:
    """業界自動判定システム"""

    def __init__(self):
        self.industry_keywords = {
            "IT・テクノロジー": {
                "primary": ["API", "SDK", "SaaS", "クラウド", "データベース", "システム開発", "ソフトウェア", "アプリ"],
                "secondary": ["DX", "デジタル変革", "IT導入", "クラウド移行", "セキュリティ", "AI", "IoT"],
                "specialized": ["React", "Python", "AWS", "Docker", "kubernetes", "GitHub", "DevOps"],
            },
            "医療・ヘルスケア": {
                "primary": ["診療", "治療", "医師", "看護師", "病院", "クリニック", "薬事法", "医療"],
                "secondary": ["予防医療", "遠隔診療", "電子カルテ", "医療DX", "健康管理"],
                "specialized": ["ICD-10", "レセプト", "診療報酬", "薬機法", "PMDA"],
            },
            "不動産": {
                "primary": ["物件", "賃貸", "売買", "マンション", "戸建て", "土地", "不動産投資"],
                "secondary": ["リノベーション", "住宅ローン", "仲介手数料", "賃貸管理"],
                "specialized": ["重要事項説明", "宅建士", "建ぺい率", "容積率", "登記"],
            },
            "教育・人材": {
                "primary": ["学習", "教育", "講座", "スクール", "研修", "資格", "eラーニング", "人材"],
                "secondary": ["オンライン授業", "学習管理", "教材開発", "採用", "転職"],
                "specialized": ["LMS", "アダプティブラーニング", "学習分析", "HRtech"],
            },
            "金融・保険": {
                "primary": ["融資", "投資", "保険", "資産運用", "金利", "リスク管理", "銀行"],
                "secondary": ["フィンテック", "ロボアドバイザー", "仮想通貨", "決済"],
                "specialized": ["AML", "KYC", "Basel III", "Solvency II", "PCI DSS"],
            },
            "製造業": {
                "primary": ["製造", "生産", "工場", "品質管理", "サプライチェーン", "設備"],
                "secondary": ["IoT", "スマートファクトリー", "予知保全", "自動化"],
                "specialized": ["QMS", "ISO9001", "TPM", "5S", "カイゼン", "JIT"],
            },
            "小売・EC": {
                "primary": ["商品", "販売", "店舗", "顧客", "在庫", "決済", "配送", "EC"],
                "secondary": ["オムニチャネル", "CRM", "ポイント", "レコメンド"],
                "specialized": ["SKU", "GMV", "LTV", "CAC", "CVR", "ROAS"],
            },
            "飲食・食品": {
                "primary": ["メニュー", "レストラン", "食材", "調理", "衛生管理", "栄養"],
                "secondary": ["テイクアウト", "デリバリー", "食品ロス", "フードテック"],
                "specialized": ["HACCP", "食品表示法", "トレーサビリティ"],
            },
            "建設・建築": {
                "primary": ["建設", "建築", "施工", "設計", "リフォーム", "住宅"],
                "secondary": ["BIM", "建築DX", "省エネ", "耐震"],
                "specialized": ["建築基準法", "一級建築士", "施工管理", "構造計算"],
            },
            "コンサルティング": {
                "primary": ["コンサル", "戦略", "業務改善", "経営", "支援"],
                "secondary": ["DXコンサル", "ITコンサル", "人事コンサル"],
                "specialized": ["フレームワーク", "ベストプラクティス", "KPI"],
            },
        }

    def analyze_industries(self, title: str, content: str, meta_description: str = "") -> IndustryAnalysis:
        combined_text = f"{title} {meta_description} {content}".lower()
        industry_scores = {}
        matched_keywords = {}

        for industry, keywords in self.industry_keywords.items():
            score = 0
            matched = []
            for keyword in keywords["primary"]:
                count = combined_text.count(keyword.lower())
                score += count * 3
                if count > 0:
                    matched.append(keyword)
            for keyword in keywords["secondary"]:
                count = combined_text.count(keyword.lower())
                score += count * 2
                if count > 0:
                    matched.append(keyword)
            for keyword in keywords["specialized"]:
                count = combined_text.count(keyword.lower())
                score += count * 5
                if count > 0:
                    matched.append(keyword)
            industry_scores[industry] = score
            matched_keywords[industry] = matched

        sorted_industries = sorted(industry_scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_industries or sorted_industries[0][1] == 0:
            return IndustryAnalysis(
                primary_industry="指定なし（自動判定不可）",
                secondary_industries=[],
                confidence_score=0.0,
                industry_keywords=[],
                specialized_terms=[],
                regulatory_indicators=[],
                target_audience_clues=[],
            )

        primary_industry = sorted_industries[0][0]
        primary_score = sorted_industries[0][1]
        secondary_industries = []
        threshold = primary_score * 0.3
        for industry, score in sorted_industries[1:6]:
            if score >= threshold and score > 0:
                secondary_industries.append(f"{industry}({score:.0f})")

        total_words = len(combined_text.split())
        confidence = min(100, (primary_score / max(total_words * 0.1, 1)) * 100)

        target_clues = self._detect_target_audience(combined_text)
        regulatory_indicators = self._detect_regulatory_terms(combined_text)

        return IndustryAnalysis(
            primary_industry=primary_industry,
            secondary_industries=secondary_industries,
            confidence_score=confidence,
            industry_keywords=matched_keywords[primary_industry],
            specialized_terms=matched_keywords[primary_industry],
            regulatory_indicators=regulatory_indicators,
            target_audience_clues=target_clues,
        )

    def _detect_target_audience(self, text: str) -> List[str]:
        audience_patterns = {
            "法人向け": ["企業", "会社", "法人", "ビジネス", "B2B"],
            "個人向け": ["個人", "家庭", "一般", "消費者", "B2C"],
            "専門職向け": ["医師", "弁護士", "税理士", "エンジニア", "専門家"],
            "経営者向け": ["経営者", "社長", "CEO", "役員", "管理職"],
        }
        detected = []
        for audience_type, patterns in audience_patterns.items():
            if any(pattern in text for pattern in patterns):
                detected.append(audience_type)
        return detected

    def _detect_regulatory_terms(self, text: str) -> List[str]:
        regulatory_terms = [
            "薬機法", "医療法", "金融商品取引法", "宅建業法", "建築基準法",
            "個人情報保護法", "食品衛生法", "労働基準法", "GDPR", "ISO",
        ]
        detected = []
        for term in regulatory_terms:
            if term.lower() in text:
                detected.append(term)
        return detected
