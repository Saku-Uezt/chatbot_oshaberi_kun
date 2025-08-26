import os
import streamlit as st
from openai import AzureOpenAI
from dotenv import load_dotenv

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
 "標準語": "あなたはフレンドリーで標準語を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、丁寧に返答してください。" ,
 "関西弁": "あなたはフレンドリーで関西弁を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、丁寧に返答してください。" ,
 "うちなーぐち": "あなたはフレンドリーで沖縄方言（本島地方準拠）を使うアシスタントです。あなたの名前はおしゃべりくんです。過去の会話の流れもきちんと覚えて、丁寧に返答してください。"
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

# セッション中にリスト"style"が無ければ初期状態を呼び出す（初期のデフォルトは関西弁）
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
    st.session_state.style.list(LOCAL_LANG_PROMPT.keys())[0] #デフォルトの場合はこれ（実質動かないが変数定義のため記述）

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

    # API呼び出し（UIに返すためのreturn処理）
    response = client.chat.completions.create(
        model=deployment,
        messages=chat_messages, #サンプルコードではsystem_messageと連結させているが前処理で履歴に追加していることからchat_messagesのみでOK
        stream=True,
        temperature=temperature
    )
    return response

# returnしたAPI呼び出し情報をUIに反映
def add_history(response):
    st.session_state.chat_history.append({"role": "assistant", "content": response}) 

# streamlitのUI構築
st.title("チャットボットおしゃべりくん")

# チャット履歴を表示する
for chat in st.session_state.chat_history:
    # roleがsystemの場合はUI上に表示させない
    if chat["role"] != "system":
        with st.chat_message(chat['role']):
            st.markdown(chat['content'])

# ユーザーの入力を受け取る  
if prompt := st.chat_input("なんでも話してみてね～"):
    # ユーザー発話を履歴に追加
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # ユーザーの発話履歴をUI上に表示させる
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = get_response(prompt)
        response = st.write_stream(stream)
        add_history(response)

