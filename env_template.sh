# OpenAI API Configuration
# 推奨：システム環境変数を使用してください
# システム環境変数に設定する場合、このファイルは不要です

# ローカルファイル設定（代替案）
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Set organization ID if you have one
# OPENAI_ORG_ID=your_organization_id_here

# システム環境変数の設定方法（Windows）:
# 1. Windowsキー + R → sysdm.cpl
# 2. [詳細設定] タブ → [環境変数] ボタン
# 3. [ユーザー環境変数] で [新規] をクリック
# 4. 変数名: OPENAI_API_KEY
# 5. 変数値: sk-your-actual-api-key
# 6. OK を押して保存、コマンドプロンプトを再起動

# Note: 
# 1. システム環境変数が設定されている場合、このファイルより優先されます
# 2. システム環境変数の方がより安全で永続的です
# 3. Never commit the .env file to version control
# 4. Make sure your API key has sufficient credits
# 5. The app uses GPT-4o-mini-search-preview model