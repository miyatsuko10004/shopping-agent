# 🛒 Shopping Agent (ショッピング最安値探索エージェント)

ユーザーの自然言語指示（予算、スペック要件、カテゴリなど）をもとに、主要ショッピングサイト・家電量販店・各種専門店を横断巡回し、要件を満たす最安値商品および最安ショップを自律的に特定・比較するAIエージェントハーネスです。

---

## 🌟 主な特徴

1. **価格比較サイト（価格.com）を起点とした高網羅性・高速度横断探索**:
   - Amazon、楽天市場、Yahoo!ショッピング、ヨドバシ.com、ビックカメラ、エディオン、Joshin、ヤマダウェブコム、専門店など、数千店舗の出品価格・送料・在庫情報を一度に横断取得。
   - 各ECモールのBot検知（Cloudflare/CAPTCHA等）で遮断されるリスクを回避し、高速かつ安定したデータ取得を実現。
2. **自然言語指示のスマート解析（ハイブリッド対応）**:
   - 「16GBメモリのMacBook Airで15万円以内」「ノイキャン付きイヤホン 1万円台」などの自然言語指示から、キーワード・予算範囲・必須スペックを自動抽出。
   - **LLM連携（Gemini / OpenAI API）**: APIキー設定時は高度な文脈把握で要件抽出。
   - **スタンドアロンモード**: APIキーがない環境でも正規表現・ヒューリスティック抽出で100%単体動作。
3. **実質最安値（本体価格＋送料）の正確な計算**:
   - 本体価格だけでなく「送料」を含めた総額（税込）でランキングを自動計算。
   - 「在庫あり」「即納」「取り寄せ」などの在庫ステータスや決済方法も可視化。
4. **多彩な出力形式**:
   - ターミナル用リッチテーブル表示（Rich）
   - エージェント回答・ドキュメント用 Markdown出力
   - OpenCodeや外部パイプライン連携用 構造化JSON出力
5. **エージェントスキル（Skill）として統合済み**:
   - `.agents/skills/shopping-search/SKILL.md` を同梱しており、AntigravityやOpenCodeから自然言語でそのまま呼び出し可能。

---

## 🚀 クイックスタート

### 動作要件
- Python >= 3.12
- `uv` (インストールされていない場合は `brew install uv` または `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### セットアップ
```bash
git clone <repository-url>
cd shopping-agent
uv sync
```

---

## 💻 使い方 (CLI)

### 1. 自然言語での探索・最安値ランキング取得
```bash
# 基本的な検索（予算や要件を含めた自然言語指示）
uv run shopping-agent search "ノイズキャンセリング ワイヤレスイヤホン 1万円台"

# 上限・下限予算を明示的に指定
uv run shopping-agent search "iPad 64GB" --budget-max 60000

# Markdown形式で出力（ファイル保存も可能）
uv run shopping-agent search "M3 MacBook Air 16GB" -f markdown -o report.md

# 機械可読なJSON形式で出力
uv run shopping-agent search "PS5 本体" -f json
```

### 2. 特定商品の全ショップ詳細価格比較
```bash
uv run shopping-agent compare "https://kakaku.com/item/J0000047497/"
```

### 3. 主なCLIオプション
| オプション | 短縮 | 説明 | デフォルト |
| :--- | :--- | :--- | :--- |
| `--limit` | `-n` | 候補商品の取得件数 | `5` |
| `--details` | `-d` | 各ショップ詳細（送料・在庫）を取得する上位商品の数 | `3` |
| `--format` | `-f` | 出力フォーマット (`table`, `markdown`, `json`) | `table` |
| `--budget-max` | `-b` | 上限予算（円） | 自然言語から自動抽出 |
| `--budget-min` | - | 下限予算（円） | 自然言語から自動抽出 |
| `--output` | `-o` | 結果の保存先ファイルパス | なし（標準出力） |
| `--no-llm` | - | LLMを使用せず純粋ルールベースで実行 | LLM優先 |

---

## 🤖 エージェント・OpenCodeとの連携

### OpenCode / Antigravity からの利用
本リポジトリには `.agents/skills/shopping-search/SKILL.md` が配置されているため、エージェント環境（Antigravity / OpenCode等）から「〜の最安値を探して」と依頼するだけで、エージェントが自動的に本ハーネスを実行し、最適な最安値商品を推薦します。

### Pythonコードからの直接利用
```python
from shopping_agent.agent import ShoppingAgent

agent = ShoppingAgent()
result = agent.search_and_rank("4K モニター 27インチ 3万円以下", limit=5)

for item in result.items:
    print(f"{item.name} - 最安値: ¥{item.min_price:,}")
    for offer in item.offers:
        print(f"  [{offer.shop_name}] ¥{offer.total_price:,} ({offer.stock})")

agent.close()
```

---

## 🔧 環境変数（オプション）

LLMを利用した高度な指示解析を行う場合は、以下のいずれかを設定してください（設定なしでもルールベースで動作します）。
- `GEMINI_API_KEY`: Google Gemini APIキー
- `OPENAI_API_KEY`: OpenAI APIキー (必要に応じて `OPENAI_BASE_URL` も指定可能)
