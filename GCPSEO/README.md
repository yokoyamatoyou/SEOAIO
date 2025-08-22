### GCP（Cloud Run）デプロイ手順（初心者向け）

前提:
- GCP プロジェクト作成済み・課金有効化済み
- `gcloud` CLI をインストールし `gcloud init` 済み
- OpenAI の API キーを用意済み

手順:
1. ビルド（Cloud Build）
   - ルート（`core/` と `seo_aio_streamlit.py` がある階層）で実行
   - `gcloud builds submit -f GCPSEO/Dockerfile --tag gcr.io/$(gcloud config get-value project)/aio2-seo-aio .`
2. デプロイ（Cloud Run Fully Managed）
   - `gcloud run deploy aio2-seo-aio \
       --image gcr.io/$(gcloud config get-value project)/aio2-seo-aio \
       --platform managed \
       --region asia-northeast1 \
       --allow-unauthenticated \
       --set-env-vars OPENAI_API_KEY=YOUR_API_KEY`

2. 動作確認
   - デプロイ完了後に表示される URL をブラウザで開く

メモ:
- アプリは `streamlit` を 0.0.0.0:8080 で待ち受けます（Cloud Run の PORT に合わせています）。
- 依存関係は プロジェクトルートの `requirements.txt` で固定。Dockerfile はプロジェクト全体をコピーしてから `requirements.txt` をインストールします。

