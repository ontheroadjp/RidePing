# この電車に乗ってるよ - Specification

## 1. 目的
本書は、初見エンジニアが現行実装を正確に理解し、改修を安全に行うための仕様書。
対象は 2026-04-29 時点の実装。

---

## 2. システム概要
- サーバ: FastAPI
- テンプレート: Jinja2
- DB: SQLite (`data/app.db`)
- 認証: SessionMiddleware
- 通知: テキストファイル追記 (`notifications/notification-YYYYMMDD.txt`)
- 対象路線: 都営大江戸線（子どもごとに複数路線設定は可能）

主要モジュール:
- `app/main.py`: FastAPIアプリ生成、SessionMiddleware、static mount、router登録
- `app/auth.py`: セッションロール判定、親/子ガード
- `app/db.py`: SQLite接続、スキーマ作成、初期データ、軽量マイグレーション
- `app/timetable.py`: mini-tokyo-3d取得、駅順、時刻表ベース列車位置、検証ロジック
- `app/notifications.py`: 通知テキストファイル出力
- `app/paths.py`: `BASE_DIR`, `DB_PATH`, `NOTIFICATION_DIR`
- `app/view.py`: Jinja2テンプレート設定、開発UI表示フラグ
- `app/routers/auth.py`: `/`, `/login`, `/logout`
- `app/routers/parent.py`: 親トップ、子ども管理、路線管理
- `app/routers/child.py`: 子画面、乗車報告
- `app/routers/api.py`: `/api/trains`, `/api/debug/timetable`

データ取得方針:
- 現行MVP: `mini-tokyo-3d` 公開時刻表データ（登録不要）を使用
- `ODPT_CONSUMER_KEY` は設定状態をUIへ表示するために残しているが、現行の列車描画ロジックは `timetable_trains()` に統一

---

## 3. データソース仕様

### 3.1 mini-tokyo-3d（登録不要・優先利用）
取得元（GitHub Raw）:
- `data/railways.json`
- `data/stations.json`
- `data/train-timetables/toei-oedo.json`

用途:
- 駅順・駅名マスタ
- 路線色
- 時刻表ベース列車候補

キャッシュ:
- プロセス内キャッシュ 30 分（`MINI_TOKYO_CACHE_TTL_SEC`）

### 3.2 ODPT（将来拡張）
- 将来的にリアルタイム遅延・在線情報を統合する候補
- 現時点では画面/APIの列車描画には使用しない

---

## 4. 認証・ロール

### 4.1 ロール
- 親: 管理画面（受信履歴・子ども管理）
- 子: 乗車連絡画面のみ

### 4.2 セッションキー
- `role`
- `parent_id`
- `child_id`（子ログイン時）

### 4.3 ガード関数
- `require_parent(request)`
- `require_child(request)`

未認証/権限不一致は `/login` へリダイレクト。

---

## 5. DB仕様

### 5.1 `parent_account`
- `id` PK
- `parent_login_id` UNIQUE
- `password_hash` (SHA-256)
- `parent_email`
- `home_station`（旧名残）
- `direction`（旧名残）

### 5.2 `child_account`
- `id` PK
- `parent_id` FK
- `child_login_id` UNIQUE
- `password_hash`
- `child_name`

### 5.3 `child_route`
- `id` PK
- `child_id` FK
- `route_name`
- `railway_id`
- `home_station`
- `destination_station`
- `direction` (`down`/`up`)

意味:
- 子ども 1 : N 路線
- 子画面で route を切替

### 5.4 `ride_report`
- `id` PK
- `parent_id`, `child_id`
- `child_name`
- `train_number`
- `from_station`, `to_station`
- `home_station`
- `eta_home`
- `created_at`

### 5.5 初期データ
- 親: `parent1 / parent123`
- 子: `child1 / child123`
- 子route: `大江戸線 / 都庁前 / down`

---

## 6. 画面仕様

## 6.1 ログイン (`/login`)
- role / ID / password 入力
- `DEV_UI_ENABLED=1` のときのみ、開発用カードを表示
  - 親/子の開発ログインボタン
  - 初期アカウント表示

### 開発用UI分離ルール
- 本番UI領域と開発UI領域は分離
- 開発機能は `開発用コンポーネント` カード内のみ表示
- 1ページ内に複数の開発用カード配置可

## 6.2 親トップ (`/parent`)
- 主表示: 受信履歴
- ヘッダメニュー（☰）:
  - 子どもアカウント管理
  - 通知先メール変更（ダイアログ）
  - ログアウト

## 6.3 子ども管理 (`/parent/children`)
- 子ども一覧
- 新規追加ボタン（ダイアログ）

## 6.4 子ども編集 (`/parent/children/{id}`)
常設はボタン中心:
- アカウント編集
- 路線追加
- 子ども削除

全操作はダイアログ実行。
路線一覧には各路線削除ボタン（確認ダイアログ）。

## 6.5 子画面 (`/trains`)
- 路線選択（子route）
- 路線図（縦）
- 全駅表示
- 駅の○は縦ライン中心に重ねる
- 始点/終点外へラインを突き出さない
- 列車チップを上→下に移動
- 列車タップで送信ダイアログ

路線図レイアウト:
- `#line-map` を十分に高く取り、駅間ピッチを拡大
- スクロールで全区間表示可能

---

## 7. 列車表示ロジック

## 7.1 基本
- 列車候補は時刻表ベース
- 補完列車（次発補完、固定モック補完）は禁止
- 該当列車がない時間帯は列車表示0件

## 7.2 時刻表判定
通常の子画面/APIは `timetable_trains()` を使い、mini-tokyo-3d の時刻表から現在時刻に該当する列車だけを描画する。
- 各列車 `tt` を走査
- 区間 `dep <= now <= next_arr` なら走行中として採用
- 駅停車 `arr <= now <= dep` なら停車中として採用
- 対象日は平日/土休日を判定し、祝日は土休日ダイヤ扱い
- ループ路線の重複駅は `station_sequence_for_destination()` の駅列と照合し、常に表示上の上→下へ進む区間だけ採用

補完列車や旧モック関数は使わない。通常表示では時刻表に該当する列車だけを返す。

## 7.3 重なり回避
- 描画時 `resolveOverlaps()` で最小間隔を確保
- 視覚上の同位置重なりを防止

---

## 8. 始発時刻表示仕様（重要）

### 8.1 表示ルール
- 各駅右ラベルに `始発: HH:MM` を表示
- ただしその駅の始発発車時刻を過ぎたら非表示
- 判定は駅単位（全体の運行有無では判定しない）

### 8.2 算出ロジック
- 対象時刻表: `toei-oedo.json`
- 方向連動:
  - `down` -> `OuterLoop`
  - `up` -> `InnerLoop`
- 深夜終電側の混入防止:
  - `03:00` 未満の時刻は始発算出対象外

### 8.3 停車表示との関係
- 停車中は `出発: HH:MM` を優先表示
- 発車後は駅の基底ラベルへ戻す
  - 基底ラベルは `始発: HH:MM` か空文字

---

## 9. 通知仕様
- 保存先: `notifications/notification-YYYYMMDD.txt`
- 1送信ごとに追記
- 内容:
  - To
  - Subject
  - 子ども名
  - 列車番号
  - 現在区間
  - 最寄駅
  - 到着予定
  - 通知時刻

---

## 10. ルーティング一覧

### 共通
- `GET /`
- `GET /login`
- `POST /login`
- `POST /logout`

### 親
- `GET /parent`
- `POST /parent/settings`
- `GET /parent/children`
- `POST /parent/children`
- `GET /parent/children/{child_id}`
- `POST /parent/children/{child_id}/update`
- `POST /parent/children/{child_id}/delete`
- `POST /parent/children/{child_id}/routes`
- `POST /parent/children/{child_id}/routes/{route_id}/delete`

### 子
- `GET /trains?route_id=...`
- `POST /report`

---

## 11. 環境変数
- `ODPT_CONSUMER_KEY`: ODPTキー設定状態の表示（現行の列車描画には未使用）
- `SESSION_SECRET`: セッション鍵
- `DEV_UI_ENABLED`: 開発用カード表示 (`1`/`0`)

---

## 12. 既知の制約
1. パスワードハッシュがSHA-256単体（本番はbcrypt/argon2へ）
2. CSRF未実装
3. 入力バリデーション最小限
4. ETAは簡易推定（時刻表/位置連動の厳密計算ではない）

---

## 13. 開発手順
```bash
npm run setup
npm run dev
```
`npm run setup` は `venv` 作成、依存インストール、`data/app.db` 初期化、`notifications/` 作成まで行う。
アクセス: `http://127.0.0.1:8000`
ポート変更: `PORT=8010 npm run dev`

DBのみ初期化:
```bash
npm run db:init
```

時刻表検証:
```bash
npm run debug:timetable:hikarigaoka
npm run debug:timetable:tochomae
npm run test:timetable
```

全回帰テスト:
```bash
npm test
```

全回帰テストと時刻表検証をまとめて実行:
```bash
npm run check
```

主なテスト対象:
- 認証/ログアウト/不正ログイン
- 親画面アクセス制御、子ども追加、子ども編集画面
- 子画面アクセス制御、列車選択画面
- `/api/trains`, `/api/debug/timetable`
- 乗車報告のDB保存と通知テキスト出力

---

## 14. 今後改修時の注意
- 列車表示は「時刻表ベース厳格運用」を維持すること
- 0件時に擬似列車を作らないこと
- 開発用UIは本番UI領域に混在させないこと
- 子ども向け操作は常に最小タップ数を意識すること

---

## 15. 変更履歴
- 2026-04-29: 全面更新
  - mini-tokyo-3d 公開データ利用
  - 時刻表ベース厳格化
  - 始発表示ルール更新
  - 開発用UI分離ルール明文化
