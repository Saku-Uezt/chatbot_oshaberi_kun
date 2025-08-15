# 関西弁チャットボット「おしゃべりくん」

## 概要
Azure OpenAI API と Streamlit を使って作成した、関西弁で会話できるチャットボットです。  
過去の会話履歴を保持しながら、フレンドリーに応答します。  
サイドバーから温度パラメータ（temperature）の調整や履歴リセットが可能です。

---

## 主な機能
- 💬 関西弁での応答
- 🔄 会話履歴の保持（`st.session_state` を使用）
- 🎛 Temperature 調整スライダー
- 🗑 2段階確認付き履歴リセット
- 🌐 Azure OpenAI API 連携

---

## 必要環境
- Python 3.9 以上
- Azure OpenAI API の利用権限
- Streamlit インストール環境

---

## インストール手順

```bash
# リポジトリのクローン
git clone https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
cd <リポジトリ名>

# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate  # Windowsは .venv\Scripts\activate

# 必要パッケージのインストール
pip install -r requirements.txt


# 環境変数設定

ルートディレクトリに .env ファイルを作成し、以下を記載してください。

ENDPOINT_URL=あなたのAzureエンドポイントURL
DEPLOYMENT_NAME=デプロイ名
AZURE_OPENAI_API_KEY=あなたのAPIキー


# 実行方法
streamlit run oshaberi_kun.py

```

# 今後の改善予定
-  関西弁/標準語　の切り替え機能
-  Azure OpenAIのコンテンツフィルター例外処理
