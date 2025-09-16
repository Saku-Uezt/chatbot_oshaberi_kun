import os
import streamlit as st
from openai import AzureOpenAI, BadRequestError, APIConnectionError
from dotenv import load_dotenv
from datetime import datetime 

load_dotenv()


#認証情報の設定
endpoint = os.getenv("ENDPOINT_URL")
deployment = os.getenv("DEPLOYMENT_NAME")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

# Azure OpenAIのクライアントを作成
client = AzureOpenAI(
    azure_endpoint = endpoint,
    api_key = subscription_key,
    #LLMモデルによって書き換える(コードはGPT-4oの場合)
    api_version = "2024-12-01-preview"
)

# 方言切り替え用のプロンプト設定
LOCAL_LANG_PROMPT = {
 "標準語": "あなたはフレンドリーで標準語を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、カジュアルに返答してください。" ,
 "関西弁": "あなたはフレンドリーで関西弁を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、カジュアルに返答してください。" ,
 "うちなーぐち": "あなたはフレンドリーで沖縄方言（本島地方準拠）を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、カジュアルに返答してください。"
}

# 初期メッセージの定義
INIT_GREETING = {
 "標準語": "こんにちは！調子はどうですか？なんでも気軽に話しかけてね！" ,  
 "関西弁": "まいど！調子はどですか？なんでも気軽に話しかけてね～" ,
 "うちなーぐち": "ハイサイ！調子はどうね？なんでも気軽に話しかけてね～"
}

# チャット履歴の初期状態メソッド
# streamlitのsession_state処理を使い、チャットの履歴を保持するリストを用意する
def init_history(style: str):
    st.session_state.chat_history = [
        {
            "role": "system",
            "content":  LOCAL_LANG_PROMPT[style]
        },
        # 初回メッセージ（assistantから話しかける）
        {
            "role": "assistant",
            "content": INIT_GREETING[style]
        }
    ]

# セッション中にリスト"style"が無ければ初期状態を呼び出す（初期のデフォルトは標準語）
if "style" not in st.session_state:
    st.session_state.style = "標準語"

# セッション中にリスト"chat_history"が存在しなければ初期状態を呼び出す
if "chat_history" not in st.session_state:
    init_history(st.session_state.style)

# サイドバーに設定項目
st.sidebar.header("設定")

# 方言切り替えのラジオボタンの実装
with st.sidebar:
    selected_style = st.radio("話し方を選ぶ",list(LOCAL_LANG_PROMPT.keys()), # 方言の辞書のキーをリスト化する
                              index= list(LOCAL_LANG_PROMPT.keys()).index(st.session_state.style), #リスト化した辞書のキーに該当するインデックスをstyleの中から選んで設定する
                              key="loc_lang_radio" #streamlitのラジオボタンの引数（ラジオボタンのID定義、別のラジオボタン定義に備えて念のため設定）
                              )

# selected_styleに変更があれば履歴を初期化し、口調を変更させる
if selected_style != st.session_state.style:
    st.session_state.style = selected_style
    init_history(selected_style)

# temperatureの調整（サイドバーにスライダーを実装する）
temperature = st.sidebar.slider(
    "温度 (応答の創造性) ※高くするとよりユニークに、低くすると比較的定型的な回答をします。",  # ラベル
    min_value=0.0, 
    max_value=1.0, 
    value=0.5, 
    step=0.1
)

# 会話履歴リセットボタン（サイドバーにボタンを用意し、押下時にクリアする）
# 履歴消去確認用フラグを設定（confirm_resetフラグを定義し、Falseの場合には消去せず、Trueの場合に消去確認処理を行う）
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False

#リセット時に引数styleを渡す必要があるので変数定義
if "style" not in st.session_state:
    st.session_state.style = list(LOCAL_LANG_PROMPT.keys())[0] #デフォルトの場合はこれ（実質動かないが変数定義のため記述）

with st.sidebar:
    #ボタン押下時の確認（リセットフラグON）
    if not st.session_state.confirm_reset:
        #ボタン押下時にフラグをTrueにし確認ダイアログを出す
        if st.button("💬 チャット履歴をリセット"):
            st.session_state.confirm_reset = True
            st.rerun()  # リレンダリングで確認UIに即切り替え
    #ボタン押下時の挙動（リセットフラグがTrue後の挙動）
    else:
        st.warning("⚠ 本当に会話履歴をリセットしますか？")
        chat_delete, chat_keep = st.columns(2)
        #「はい」ボタンが押下されたときに会話履歴を初期状態にし、フラグをFalseに戻す
        with chat_delete:
            if st.button("はい"):
                init_history(st.session_state.style) #定義したstyleをここで渡す
                st.session_state.confirm_reset = False
                st.rerun()  # リレンダリングで初期表示に戻す
        #「キャンセル」ボタンが押下されたときはフラグをFalseに戻すだけで何もしない
        with chat_keep:
            if st.button("キャンセル"):
                st.session_state.confirm_reset = False
                st.rerun()  # リレンダリングで初期表示に戻す


def get_response(prompt: str):

    # 履歴をAPI形式に変換（systemは初期状態で組み込み済み）
    chat_messages = [
        {"role": m["role"], "content": m["content"]}
        # ループ処理で上記のAPI入力dictをリストに追加していく
        for m in st.session_state.chat_history
    ]


    # API呼び出し（UIに返すためのreturn処理、APIが返すエラーハンドリングを実装）
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=chat_messages, #サンプルコードではsystem_messageと連結させているが前処理で履歴に追加していることからchat_messagesのみでOK
            stream=True,
            temperature=temperature
        )
        return response
    
    # Azure OpenAI上でコンテンツフィルタにかかったときの例外処理
    except BadRequestError as e:
        import traceback
        print("=== AzureOpenAI Error ===")
        traceback.print_exc() #コンソールにエラーログを出力する
        #UI上にエラーを出力
        return "⚠ システムエラー: 使用できない単語が含まれています。質問内容を変更して、もう一度お試しください。"
    
    # API通信エラーのときの例外処理
    except APIConnectionError as e:
        import traceback
        print("=== AzureOpenAI Connection Error ===")
        traceback.print_exc() #コンソールにエラーログを出力する
        #UI上にエラーを出力
        return "⚠ 通信エラーが発生しました。ネットワーク環境をご確認のうえ、再度お試しください。"

# returnしたAPI呼び出し情報をUIに反映
def add_history(response):
    st.session_state.chat_history.append({"role": "assistant", "content": response}) 

# streamlitのUI構築
st.title("チャットボットおしゃべりくん")

# assistantの発話段落下がりを防止する、ページレイアウト用のcssの設定を変更する （markdownを使ってcss/htmlを直接いじる裏技コード）
# 参考：XSS対策として固定CSS以外は"unsafe_allow_html=True"を使用しないこと
st.markdown("""
<style>
/* 吹き出し内：最初の段落の上マージンを無くす */
.stChatMessage .stMarkdown p:first-child {
  margin-top: 0 !important;
}
/* 吹き出し内：直後に来るブロック要素（ul, pre, blockquote など）も上マージンをゼロに */
.stChatMessage .stMarkdown > *:first-child {
  margin-top: 0 !important;
}

/* エラーバナー（st.error など）も段落の上下マージンを詰める */
.stAlert p {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}

/* assistantの吹き出しの色変更 */
div[aria-label="Chat message from assistant"] {
    background: linear-gradient(135deg, #fef9c3, #fde68a) !important;  /* 薄い黄色を適用、左上から右下へのグラデ */
    border-radius: 16px;  /* 吹き出しの丸み設定 */
    padding: 10px;  /* 外枠のパディング設定 */ 
    box-shadow: 2px 2px 6px rgba(0,0,0,0.1);  /* 外枠の色と影の設定、灰色、透明度0.1 */
}

/* userの吹き出しの色変更 */
div[aria-label="Chat message from user"] {
    background: linear-gradient(135deg, #dbeafe, #93c5fd) !important;  /* 薄い水色を適用、左上から右下へのグラデ */
    border-radius: 16px;  /* 吹き出しの丸み設定 */
    padding: 10px;  /* 外枠のパディング設定 */ 
    box-shadow: 2px 2px 6px rgba(0,0,0,0.1);  /* 外枠の色と影の設定、灰色、透明度0.1 */ 
}
            
/* チャット文字の色変更（モバイル版のダークテーマが適用されると白文字になって見づらくなるため強制的に文字色を黒に） */
div[aria-label="Chat message from assistant"] .stMarkdown p,
div[aria-label="Chat message from user"] .stMarkdown p {
    color: #111827 !important; /* ほぼ黒のグレー */
}
</style>
""", unsafe_allow_html=True)

# チャット履歴を表示する
for chat in st.session_state.chat_history:
    # roleがsystemの場合はUI上に表示させない
    if chat["role"] != "system":
        with st.chat_message(chat['role']):
            st.markdown(chat['content'].lstrip())

# ストリーム内のチャンクから安全にテキスト(content)だけを取り出すジェネレータメソッド
def content_stream(stream):
    
    for chunk in stream:
        # チャンクにchoicesが無い場合はcontinue処理を実施してスキップし存在するチャンクを取り出す
        # 空のチャンクを取り出そうとするとエラーになるのでその対策処理
        choices = getattr(chunk, "choices", None)  
        if not choices:
            continue
        # delta = 今回追加された差分（content, role, tool_calls などが入る）
        delta = getattr(choices[0], "delta", None)
        # 同様にオブジェクトが無い場合は処理をスキップして取り出す
        if not delta :
            continue

        # content 取得（dict/obj両対応）
        content = delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
        # contentが存在する場合yieldして逐次UIに返す
        if content:
            yield content


# 先頭行の空白や改行をトリミングするメソッド（チャット欄の見栄えを整えるメソッド）
def trim_leading_whitespace(gen):
    started = False 
    #結合用空文字列を用意する
    buffer = ""
    #取り出したチャンクに対してループ処理を行う（初回処理（startedフラグがFalseの場合））
    for piece in gen: 
        if not started:
            #チャンクを足し合わせていく 
            buffer += piece
            #足し合わせたチャンクの先頭の改行コード \n やスペースを除去
            stripped = buffer.lstrip() 
            #空白や改行だけのチャンクは無視して次のチャンク処理に移る
            if stripped == "":
                continue  
            #startedフラグをTrueにする          
            started = True
            #トリミングしたチャンクをyieldする
            yield stripped
        #二回目の処理以降はそのままyieldして出力する
        else:
            yield piece


# ユーザーの入力を受け取る  
if prompt := st.chat_input("なんでも話してみてね～"):
    # ユーザー発話を履歴に追加
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # ユーザーの発話履歴をUI上に表示させる
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        #インスタンスのレスポンスを定義
        instance_res = get_response(prompt)

        # インスタンスオブジェクトの型チェック
        # （正常時はストリーム型を返し、エラー時はstr型で返ってくるためハンドリングする必要がある）
        if isinstance(instance_res, str):
            # 例外時はエラーメッセージ（str）なので赤帯で表示
            st.error(instance_res)
        else:
        # 先頭の空白/改行を除去してから表示
            # 先頭の改行/空白を“ストリーム前処理メソッド”で除去してから write_streamメソッドに渡す
            sanitized_stream = trim_leading_whitespace(content_stream(instance_res))
            text = st.write_stream(sanitized_stream)
            add_history(text.lstrip())   # 保存時も念のためlstrip