# 乗ったよ / RidePing (MVP)

大江戸線固定のスマホ向けWebアプリです。

- DB: SQLite (`data/app.db`)
- 通知: メール送信の代わりにテキストファイル出力 (`notifications/`)
- 列車表示: mini-tokyo-3d 公開時刻表データを使った時刻表ベース表示

## セットアップ

```bash
npm run setup
```

`venv` 作成、Python依存インストール、SQLite DB初期化まで実行されます。
初期アカウント:
- 親: `parent1 / parent123`
- 子: `child1 / child123`

## 起動

```bash
npm run dev
```

ブラウザで `http://127.0.0.1:8000` を開く。
ポートを変える場合は `PORT=8010 npm run dev` のように指定する。

## テスト

```bash
npm test
```

時刻表検証も含める場合:

```bash
npm run check
```

## ODPT連携（将来拡張）

ODPTのコンシューマキーを取得して環境変数を設定。
現時点の列車描画は mini-tokyo-3d 時刻表ベースで、ODPTキーは設定状態の表示用途です。

```bash
export ODPT_CONSUMER_KEY="your_key"
npm run dev
```

## 使い方

1. ホームで保護者メール、子ども名、最寄駅を保存
2. `今乗ってる電車を選ぶ` を押す
3. 候補から選択して送信
4. `notifications/notification-YYYYMMDD.txt` に通知本文が追記される
