承知しました。自律的な開発エージェントが実装に着手できるよう、**「何を作るか（要求定義）」**と**「どう設計すべきか（アーキテクチャ・共通設計の勘所）」**に絞って、全体像を定義します。

---

# Matome 2.0: "Knowledge Installation" Update - 要求定義書

## 1. プロジェクト目的

既存の「静的な要約生成ツール（CLI）」を、**「インタラクティブな知識獲得ツール（GUI）」**へと進化させる。
ユーザーが情報の抽象度を自在に行き来し、自身のメンタルモデルに合わせて知識を再構築できる体験（Semantic Zooming）を提供する。

## 2. 機能要件 (Functional Requirements)

### 機能A: Semantic Zooming Engine (DIKW-Reverse Logic)

RAPTORのツリー構造を、「要約」ではなく「抽象度の階層（DIKWモデル）」として再定義・生成するロジック。

* **L1: Wisdom (Root)**
* **定義:** 文脈を極限まで削ぎ落とした「哲学・アフォリズム・教訓」。
* **要件:** 全体を20〜40文字程度の「ワンメッセージ」に圧縮する。


* **L2: Knowledge (Branches)**
* **定義:** Wisdomを支える「論理構造・メンタルモデル」。
* **要件:** 具体例ではなく、「なぜそう言えるのか」という構造（Framework/Mechanism）を抽出する。


* **L3: Information (Twigs)**
* **定義:** 実行可能な「アクションプラン・ルール・手順」。
* **要件:** 読者が明日から使える形式（How-to/Checklist）で出力する。


* **L4: Data (Leaves)**
* **定義:** 原文のチャンク（Evidence）。
* **要件:** 上位レイヤーからいつでも参照可能な状態でリンクされる。



### 機能B: Matome Canvas (Interactive UI)

生成されたDIKWツリーを可視化し、対話的に書き換えるためのGUI（Panel製）。

* **View: ピラミッド・ナビゲーション**
* 初期表示は L1 (Wisdom) のみ。
* ユーザーのクリック操作（ドリルダウン）により、L2 → L3 と詳細が開示される。


* **Action: インタラクティブ修正 (Refinement)**
* 特定のノードに対し、チャット形式で修正指示を出せる（例：「もっと小学生向けに」「ここを箇条書きで」）。
* 修正結果は即座にDBに保存され、ツリー構造に反映される。



---

# システム設計指針・共通化設計 (Architectural Design Guidelines)

実装担当者が迷わないよう、特に**「CLIとGUIの共存」**と**「拡張性」**に関わる重要設計ポイントを指示します。

## 1. 【共通設計】プロンプト・ストラテジーパターン (Prompt Strategy Pattern)

`SummarizationAgent` 内に `if level == 0` のような分岐を乱立させないこと。要約ロジックを切り出し、注入可能にする。

* **設計指示:**
* `PromptStrategy` インターフェースを定義する。
* 「Wisdom生成用」「Knowledge生成用」「Action生成用」など、目的ごとの具象クラスを作成する。
* `SummarizationAgent` は、初期化時または実行時にこの Strategy を受け取り、それに基づいてLLMを叩く仕様に変更する。
* これにより、Canvas側で「要約モード」と「修正モード」を切り替える際も、Strategyを差し替えるだけで対応可能になる。



## 2. 【データ設計】ノードメタデータの標準化 (Node Metadata Schema)

既存の `SummaryNode` の `metadata` フィールドを活用し、DIKW階層を管理する。DBスキーマ変更は行わず、JSON構造で吸収する。

* **設計指示:** `metadata` に以下のキーを必須とする。
* `dikw_level`: `"wisdom" | "knowledge" | "information" | "data"`
* `is_user_edited`: `bool` （ユーザーが手動修正したノードは、後のバッチ処理等で上書きされないようにロックする）
* `refinement_history`: `list[str]` （どのような修正指示を行ったかの履歴）



## 3. 【アーキテクチャ】Interactive Engine Wrapper

既存の `RaptorEngine` は「全自動バッチ処理」に特化しているため、これを無理に改造しない。

* **設計指示:**
* GUI用の操作クラスとして、`InteractiveRaptorEngine` (または `RaptorController`) を新設する。
* このクラスは `DiskChunkStore` と `SummarizationAgent` を保持する。
* **責務:**
1. **Single Node Refinement:** 指定された `node_id` のみを再生成し、DB更新するメソッド。
2. **Parent Consistency (Optional):** 子ノードが書き換わった際、必要であれば親ノードに「再要約フラグ」を立てる、あるいは即時再計算するロジック（※初期フェーズでは必須としないが、設計余地は残す）。





## 4. 【GUI設計】MVVMパターンの採用 (Panel Design)

Panelの実装コードがスパゲッティ化しないよう、明確に分離する。

* **設計指示:**
* **Model:** `DiskChunkStore` から取得した `SummaryNode` オブジェクトそのもの。
* **ViewModel:** `InteractiveSession` クラス。
* 「現在選択中のノードID」「編集中フラグ」「ユーザー入力テキスト」などの状態（State）を `param` ライブラリで管理する。
* ViewはこのViewModelを監視（Watch）し、変更があったら自動描画するように実装する。


* **View:** レイアウト定義。ロジックを持たせない。



## 5. 【注意点】DB接続の並行性 (Concurrency)

`chunks.db` (SQLite) は、CLIでの書き込みとCanvasでの読み書きが競合する可能性がある。

* **指示:**
* `DiskChunkStore` のDB接続処理において、トランザクション管理（コミット/ロールバック）が確実に行われるよう、Context Manager (`with` 構文) の利用を徹底する。
* Canvasからの書き込み時は、短時間のロックで済むよう、処理（LLM生成）が終わってから書き込みを行う設計にする（生成中にDBをロックし続けない）。



---

以上の指針に基づき、まずは **「PromptStrategyの分離」** と **「InteractiveEngineの作成」** から実装を開始してください。