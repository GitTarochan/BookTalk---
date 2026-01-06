import streamlit as st
import requests
import streamlit.components.v1 as components  # ← ★これを追加！

# ページ設定（ブラウザのタブ名などを設定）
st.set_page_config(page_title="BookTalk", page_icon="📚")

# --- 🧠 セッションステート（記憶）の初期化 ---
if "search_results" not in st.session_state:
    st.session_state["search_results"] = None

# 「今どのページにいるか」を覚える変数（初期値は 'search'）
if "page" not in st.session_state:
    st.session_state["page"] = "search"

# 「どの本を選んだか」を覚える変数
if "selected_book" not in st.session_state:
    st.session_state["selected_book"] = None


# ==========================================
# 🏠 1. 検索画面（pageが 'search' のとき表示）
# ==========================================
if st.session_state["page"] == "search":
    st.title("📚 BookTalk - 本でつながる")
    st.write("読んだ本の感想を、ビデオ通話で今すぐ語り合おう。")

    # 検索バー
    query = st.text_input("検索したい本やキーワードを入力してください")
    search_button = st.button("検索する")

    # 検索処理（ここを書き換える！）
    if search_button and query:
       # 末尾に &country=JP を追加
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&country=JP"
        
        try:
            # 通信を試みる
            response = requests.get(url, timeout=10)
            
            # ステータスコード（通信の結果）を表示してみる！
            if response.status_code != 200:
                st.error(f"通信エラー発生！ エラーコード: {response.status_code}")
                st.write(response.text) # 詳しいエラー内容を表示
            else:
                data = response.json()
                if "items" in data:
                    st.session_state["search_results"] = data["items"]
                    st.success(f"{len(data['items'])} 件見つかりました！") # 成功したらメッセージを出す
                else:
                    st.session_state["search_results"] = []
                    st.warning("通信は成功したけど、本が見つかりませんでした。")
                    
        except Exception as e:
            st.error(f"予期せぬエラーが発生しました: {e}")

    # 結果表示
    if st.session_state["search_results"]:
        if len(st.session_state["search_results"]) == 0:
            st.error("本が見つかりませんでした💦")
        else:
            st.divider()
            for item in st.session_state["search_results"][:5]:
                book = item["volumeInfo"]
                book_id = item["id"]
                
                title = book.get("title", "タイトル不明")
                authors = book.get("authors", ["著者不明"])
                image_url = book.get("imageLinks", {}).get("thumbnail", "")
                
                # レイアウト
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if image_url:
                            st.image(image_url, width=80)
                    with col2:
                        st.subheader(title)
                        st.write(f"✍️ {', '.join(authors)}")
                        
                        # ★ここが変更点！
                        # ボタンを押したら「部屋」モードに切り替える
                        if st.button(f"🔥 語る", key=book_id):
                            st.session_state["selected_book"] = book  # 本の情報を保存
                            st.session_state["page"] = "room"         # ページを「room」に変更
                            st.rerun()                                # 画面を強制更新！
                st.divider()

# ==========================================
# 🚪 2. 待機部屋画面（pageが 'room' のとき表示）
# ==========================================
elif st.session_state["page"] == "room":
    # 保存しておいた本の情報を取り出す
    book = st.session_state["selected_book"]
    
    # 戻るボタン（サイドバーに配置）
    if st.sidebar.button("← 検索に戻る"):
        st.session_state["page"] = "search"
        st.session_state["selected_book"] = None
        st.rerun()

    # 部屋のデザイン
    st.title("🍵 対話ルーム")
    
    # 選んだ本の情報を表示
    col1, col2 = st.columns([1, 2])
    with col1:
        image_url = book.get("imageLinks", {}).get("thumbnail", "")
        if image_url:
            st.image(image_url, width=150)
    with col2:
        st.header(book.get("title", ""))
        st.write(f"著者: {', '.join(book.get('authors', []))}")
    
    st.divider()

    # --- 🎥 ビデオ通話機能 (Jitsi Meet) ---
    st.subheader("参加準備ができました！")
    
    # 本のIDを使って、ユニークな部屋名を作る（例: BookTalk-Room-xxxxxxxx）
    # これにより、同じ本を選んだ人同士だけが同じ部屋に入れます！
    room_name = f"BookTalk-Room-{book['id']}"
    jitsi_url = f"https://meet.jit.si/{room_name}"

    st.info(f"現在の部屋ID: {room_name}")
    st.write("カメラとマイクを許可して、会話に参加しましょう。")

    # 1. 埋め込み画面（アプリの中で表示）
    # ※ ブラウザの設定によっては、ここだとカメラが動かないことがあります
    components.iframe(jitsi_url, height=600, scrolling=True)

    # 2. 救済用のボタン（別タブで開く）
    # 埋め込みでうまくいかない時は、こっちを押してもらう
    st.markdown(f'''
        <a href="{jitsi_url}" target="_blank" style="
            display: inline-block;
            padding: 10px 20px;
            background-color: #FF4B4B;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        ">🚀 もし繋がらない場合は、ここを押して別タブで参加</a>
    ''', unsafe_allow_html=True)
