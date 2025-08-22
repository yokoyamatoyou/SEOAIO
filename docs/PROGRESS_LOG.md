### 進捗ログ（時系列）

- 2025-08-19
  - 依存の固定化: `requirements.txt` を追加
  - フォルダ整備: `MVP/`（ローカル手順）、`GCPSEO/`（Dockerfile/README/.dockerignore）を追加
  - ルート `.dockerignore` 追加
  - テスト実行: 14件実行（OK=4, skip=10）。skipはUI依存による import 失敗に起因。フェーズ1で解消予定
  - 次アクション: フェーズ1（UI/ロジック分離、import副作用解消、skip削減）
  - PDF整合性: PDFにスコア整合性チェック（SEO/AIO/統合の再計算）を追加
  - 表記修正: `core/constants.py` の「パーソナライズ可能性」を修正

- 2025-08-19 (2)
  - モデル固定: `OPENAI_MODEL = gpt-4.1-mini-2025-04-14`、`OPENAI_TEMPERATURE = 0.1`
  - UI/依存寛容化: `seo_aio_streamlit.py` と `core/ui_components.py` をImportError耐性化（テスト時に強制終了しない）
  - 構造維持: シンプル構成（`core/`, `tests/`, `MVP/`, `GCPSEO/`, `docs/`）のまま進行
  - テスト状況: 14件実行（OK=4, skip=10）で不変。skip原因は `SEOAIOAnalyzer` がUIモジュール内にあるため
  - 次に行うべき内容:
    - `SEOAIOAnalyzer` を `core/analyzer.py` に移動（UI依存排除）
    - `seo_aio_streamlit.py` をUIラッパーへ限定し、`core` からAnalyzerを利用
    - テスト更新: `SEOAIOAnalyzer` を `core` から直接参照し、skip削減
    - 再テスト＆PDF生成の整合性確認（Δ表示含む）
    - `GCPSEO/README.md` 手順でCloud Build/Runの簡易動作確認（`OPENAI_API_KEY` 環境変数設定）
  - テキスト構成図: `docs/TEXT_STRUCTURE.md` を追加し完成予定構成を確定


