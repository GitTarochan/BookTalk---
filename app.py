import streamlit as st
import os
import streamlit.components.v1 as components  # ← ★これを追加！
from book_search import BookSearchError, search_books

# ページ設定（ブラウザのタブ名などを設定）
st.set_page_config(page_title="BookTalk", page_icon="📚")


def google_books_api_key():
    key = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")
        except FileNotFoundError:
            pass
    return key.strip()

# --- 🧠 セッションステート（記憶）の初期化 ---
if "search_results" not in st.session_state:
    st.session_state["search_results"] = None
if "search_source" not in st.session_state:
    st.session_state["search_source"] = ""

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

    with st.form("book_search"):
        query = st.text_input("検索したい本やキーワードを入力してください")
        search_button = st.form_submit_button("検索する")

    if search_button:
        query = " ".join(query.split())
        st.session_state["search_results"] = None
        st.session_state["search_source"] = ""
        if not query:
            st.warning("本のタイトルやキーワードを入力してください。")
        else:
            try:
                with st.spinner("本を検索しています…"):
                    items, source = search_books(query, google_books_api_key())
                st.session_state["search_results"] = items
                st.session_state["search_source"] = source
                if items:
                    st.success(f"{len(items)} 件見つかりました！")
                else:
                    st.warning("本が見つかりませんでした。別のキーワードを試してください。")
            except BookSearchError as error:
                st.error(str(error))

    source = st.session_state["search_source"]
    if source == "Open Library":
        st.caption("書籍情報：[Open Library](https://openlibrary.org/)")
    elif source == "国立国会図書館サーチ":
        st.caption("書籍情報：国立国会図書館サーチAPI（国立国会図書館作成書誌）。"
                   "[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。"
                   "表示形式をBookTalk向けに変更しています。")
    elif source:
        st.caption(f"書籍情報：{source}")

    # 結果表示
    if st.session_state["search_results"]:
        if len(st.session_state["search_results"]) == 0:
            st.error("本が見つかりませんでした💦")
        else:
            st.divider()
            for item in st.session_state["search_results"][:5]:
                book = dict(item["volumeInfo"])
                book_id = item["id"]
                # ★ここを追加！ (IDを本の情報の中に無理やり入れ込む)
                book["id"] = book_id
                
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
                        if book.get("sourceUrl"):
                            st.link_button("書籍情報を見る", book["sourceUrl"])
                        
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
