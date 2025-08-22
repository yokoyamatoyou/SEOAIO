### ローカルMVPの実行手順

1. 仮想環境を作成（任意）
   - Windows (PowerShell): `python -m venv .venv && .venv\\Scripts\\Activate`
   - macOS/Linux: `python -m venv .venv && source .venv/bin/activate`

2. 依存関係を固定バージョンでインストール
   - `pip install -r ..\\requirements.txt`

3. 環境変数を設定
   - `OPENAI_API_KEY` をシステム環境変数または `.env` に設定

4. アプリ起動（プロジェクト内側ディレクトリで実行）
   - `cd ..`
   - `streamlit run seo_aio_streamlit.py`

備考:
- 共有モジュールは `core/` にまとめており、ローカル・クラウドの両方で共通利用します。
- 依存関係は `requirements.txt` に固定版で定義しています。


