# BookTalk — 本の感想を語り合うためのWebアプリ

「読み終えた本について話したいけれど、身近に読んだ人がいない」
という場面を想定した、**書籍検索とビデオ通話ルームへの導線をつなぐプロトタイプ**です。

本を検索して選ぶと、書籍IDに対応するJitsi Meetのルームへ進みます。
同じ書籍IDを選んだ人が同じルームを開く仕組みです。

## 主な機能

- Google Books、Open Library、国立国会図書館サーチAPIによる書籍検索
- 検索結果のタイトル・著者・表紙の表示（画面には最大5件）
- 選んだ本の情報を表示する対話ルーム画面
- Jitsi Meetの埋め込みと、別タブで開くリンク
- 検索画面へ戻る操作とセッション内の画面状態管理

## 技術構成

| 用途 | 技術 |
|---|---|
| アプリ・画面 | Python、Streamlit |
| 書籍検索 | requests、Google Books / Open Library / 国立国会図書館サーチAPI |
| 通話 | Jitsi MeetのルームURLをiframeに埋め込み |
| 状態管理 | Streamlit session_state |

画面は [app.py](app.py)、検索処理は [book_search.py](book_search.py) にまとまっています。
通話基盤にはJitsi Meetを使用しています。

## 起動方法

必要なもの：Git、Python 3、インターネット接続。

```bash
git clone https://github.com/GitTarochan/BookTalk---.git
cd BookTalk---
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windowsでは仮想環境の有効化を `.venv\Scripts\activate` に置き換えてください。
起動時にターミナルへ表示されるLocal URLをブラウザで開きます。

依存ライブラリのバージョンは固定していません。
APIキーを設定せずに起動できます。外部サービス側の制限は適用されます。

## 書籍検索と429エラーへの対応

APIキーが未設定の場合はOpen Libraryで検索し、見つからない場合や通信に失敗した場合は
国立国会図書館サーチを利用します。国立国会図書館サーチでは、国立国会図書館作成書誌の図書に絞って検索します。

Google Booksを優先する場合は、Google CloudでBooks APIを有効化したプロジェクトのAPIキーを
Streamlit Community Cloudのアプリ設定 > Secretsに登録してください。

```toml
GOOGLE_BOOKS_API_KEY = "取得したAPIキー"
```

ローカルでは環境変数 `GOOGLE_BOOKS_API_KEY`、または `.streamlit/secrets.toml` に同じ設定を指定できます。
APIキーはGitHubにコミットしないでください。環境変数を優先して読み込みます。

Google Booksが429（利用枠の超過）などを返した場合も代替APIで検索を続けます。
成功した検索結果は1時間キャッシュし、同じ検索の通信を減らします。
全サービスの通信に失敗した場合は再検索の案内を表示し、失敗はキャッシュしません。
日次利用枠が0の場合、待機やリトライでは解消しないため、Google Cloud側のAPI有効化・利用枠を確認してください。
検索結果には情報の取得元を表示します。国立国会図書館サーチの結果には表紙がない場合があります。

動作確認：

```bash
python -m unittest discover -s tests -v
```

## 使い方

1. 本のタイトルやキーワードを入力して検索します。
2. 検索結果の「語る」ボタンを押します。
3. 本の情報を確認し、通話画面の案内に従います。
4. 埋め込み画面で接続できない場合は、別タブで開くリンクを使います。

通話にはカメラ・マイクの許可などが必要です。
開始・参加時の認証や利用条件はJitsi側の仕様に依存します。

## 実装のポイント

- **書籍とルームの対応：** `BookTalk-Room-{id}` という部屋名を作ります。Google Booksの既存IDを保持し、代替APIのIDには `ol-` / `ndl-` を付けて区別します。
- **画面遷移：** 選択した書籍と現在の画面をsession_stateで保持します。
- **接続への導線：** iframeで利用できない場合に備え、同じルームを別タブで開く方法を用意しています。

書籍検索からルーム表示までの導線を実装しています。
利用者数、通話成立率、複数端末での接続品質などの定量評価は掲載していません。

## 実装範囲と制約

- 通話相手の募集、自動マッチング、在室者の一覧表示はありません。
- 同じ作品でも版や取得元のAPIによってIDが異なると、別のルームになります。同じ検索結果を選んだ人は同じルームを開きます。
- 書籍ID由来のルーム名は予測可能です。招待制のプライベートルームとしての設計ではありません。
- 書籍検索と通話は外部サービスの可用性・仕様に依存します。
- 書籍検索語は利用する検索APIへ送信され、通話ではJitsi側の通信が発生します。
- ブラウザや端末によって、埋め込み通話の権限・動作が異なります。

## 今後の改善候補

- 複数端末での通話開始・参加手順の確認
- 相手を招待する導線と、ルームの公開範囲の設計
- 検索失敗・結果なしの場合の表示改善
- 依存バージョンの固定と、動作確認環境の記録

## 外部サービス・ライセンス

[Google Books API](https://developers.google.com/books) /
[Open Library API](https://openlibrary.org/developers/api) /
[国立国会図書館サーチAPI](https://ndlsearch.ndl.go.jp/help/api) /
[Jitsi Meet](https://meet.jit.si/)

国立国会図書館サーチから取得する国立国会図書館作成書誌のメタデータは
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) に基づき利用し、
BookTalk向けに表示形式を変更しています。テスト用XMLはAPI応答から必要な項目を抜き出しています。

コードのライセンスは [LICENSE](LICENSE) を参照してください。
外部サービス・書籍情報には、それぞれの利用条件が適用されます。
