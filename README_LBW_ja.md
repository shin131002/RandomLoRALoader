# Filtered Random LoRA Loader (LBW)

**LoRAブロックウェイト（LBW）対応、SD1.5/SDXL自動検出付き**

![FilteredRandomLoRALoader(LBW)ワークフロー例](./images/lbw_final_single.webp)

---

## 概要

Filtered Random LoRA Loader (LBW) は、Filtered Random LoRA LoaderにLoRAブロックウェイト（LBW）機能を追加したノードです。U-Netのどの部分にLoRAを適用するかを細かく制御できます。

---

## 主な機能

### **基本機能（Filtered Random LoRA Loaderと共通）**
- ✅ 1つのフォルダからLoRAをランダム選択
- ✅ キーワードフィルタ（AND/ORモード）
- ✅ メタデータ検索（ファイル名または埋め込みメタデータ）
- ✅ プレビュー画像（静止画・アニメーション画像・動画に対応）
- ✅ トリガーワードの取得
- ✅ ファイル名による重複除外
- ✅ そのまま直列接続が可能

### **拡張機能（LBW）**
- ✅ **LoRAブロックウェイト（LBW）対応**：U-Netのブロックごとに個別の強度を設定し、画風・キャラクター・構図などを分離して制御
- ✅ **SD1.5/SDXLの自動検出**
- ✅ **4つのプリセットモード＋カスタム入力**
- ✅ **ウェイト数の自動調整**

---

## LoRAブロックウェイト（LBW）

### **LBWとは？**

LoRAブロックウェイトを使うと、U-Netのどの部分にLoRAを効かせるかを制御できます。Stable DiffusionのU-Netは次の3つの部分で構成されています。

```
INPUT blocks  → 構造、構図、レイアウト
   ↓
MIDDLE block  → 全体的な特徴
   ↓
OUTPUT blocks → 画風、ディテール、細部の調整
```

ブロックごとにウェイトを調整することで、LoRAの効き方を細かく制御できます。

---

## ウェイトモード

### **1. Normal (All 1.0)** - デフォルト
すべてのブロックのウェイトが1.0（LBWを使わない通常のLoRA適用）です。

---

### **2. Style Focused（画風特化）**
OUTPUTブロックのみを有効にします。

**SDXL:** `1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`

**向いているもの:**
- 画風LoRA（アニメ風、水彩風など）
- スタイルLoRA、エフェクトLoRA
- 見た目の雰囲気を変えたい場合

**効果:**
- ✅ 画風が強く変わる
- ❌ 構図やキャラクターはほとんど変わらない（既存の構図を保ちたい場合に最適）

---

### **3. Character Focused（キャラ重視）**
INPUT前半＋MIDDLE＋OUTPUTを有効にします。

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`

**向いているもの:**
- キャラクターLoRA、人物LoRA
- コンセプトLoRA
- 顔や特徴を保ちたい場合

**効果:**
- ✅ キャラクターの特徴が強く出る
- ✅ 全体的にバランスの取れた効き方

---

### **4. Structure/Composition Only（構造・構図のみ）**
INPUT＋MIDDLEブロックのみを有効にします。

**SDXL:** `1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`  
**SD1.5:** `1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`

**向いているもの:**
- ポーズLoRA
- 構図LoRA、レイアウトLoRA

**効果:**
- ✅ 構造やポーズが強く変わる
- ❌ 画風はほとんど変わらない

---

### **5. Balanced / Soft（バランス・穏やか）**
選んだブロックに穏やかに適用します。OUTPUT後半を弱めて過剰な効きを防ぎます。

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0`  
**SD1.5:** `1,1,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0`

**向いているもの:**
- 控えめに効かせたい場合、微調整
- 複数のLoRAを併用するワークフロー
- 汎用LoRA

**効果:**
- ✅ バランスの取れた穏やかな効き方で、自然な仕上がり
- ✅ 複数のLoRAを重ねやすい

---

### **6. Preset: Random**
上記4つのプリセットから、実行ごとに1つをランダムに選びます。

```
weight_mode: "Preset: Random"
→ 実行ごとに4つのプリセットから1つ選択
```

**向いているもの:**
- 試行錯誤
- バリエーションの生成
- ランダムな効果

---

### **7. Direct Input**
ウェイトを直接指定します。

**形式:**
- SDXL: カンマ区切りで20個の値
- SD1.5: カンマ区切りで17個の値

**例（SDXL）:**
```
weight_mode: "Direct Input"
lbw_input: "1,0.5,0.5,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.7,0.7,0.7,1,1,1,1,1,1,1"
```

**自動調整:**
- 要素数が足りない場合：末尾を1.0で埋める
- 要素数が多すぎる場合：末尾から切り詰める

---

## ブロック構造

### **SDXL（20要素）**
```
BASE, IN00-IN08 (9), MID (1), OUT00-OUT08 (9)
```

| インデックス | ブロック | 役割 |
|------------|---------|------|
| 0 | BASE | 全体ベース |
| 1-9 | INPUT (IN00-08) | 構造・構図 |
| 10 | MIDDLE (M00) | 中間特徴 |
| 11-19 | OUTPUT (OUT00-08) | 画風・ディテール |

**ウェイト例:**
```
1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1
BASE,IN00-08 (OFF),M00,OUT00-08 (ON)
→ OUTPUTブロックのみLoRA適用（画風特化）
```

### **SD1.5（17要素）**
```
BASE, IN01,IN02,IN04,IN05,IN07,IN08 (6), MID (1), OUT03-OUT11 (9)
```

| インデックス | ブロック | 役割 |
|------------|---------|------|
| 0 | BASE | 全体ベース |
| 1-6 | INPUT (IN01,02,04,05,07,08) | 構造・構図 |
| 7 | MIDDLE (M00) | 中間特徴 |
| 8-16 | OUTPUT (OUT03-11) | 画風・ディテール |

**ウェイト例:**
```
1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1
BASE,IN (OFF),M00,OUT (ON)
→ OUTPUTブロックのみLoRA適用（画風特化）
```

---

## 自動検出

### **LoRAタイプの検出**

ノードはモデル構造を解析して、LoRAがSD1.5用かSDXL用かを自動で判定します。

- **SD1.5**: `output_blocks_0`〜`output_blocks_11`（12ブロック）
- **SDXL**: `output_blocks_0`〜`output_blocks_8`（9ブロック）

```
SDXL検出 → 20要素のウェイトを使用
SD1.5検出 → 17要素のウェイトを使用
```

**モデルの種類を手動で指定する必要はありません** ✅

---

### **ウェイト数の自動調整**

入力したウェイトの数が、検出したLoRAタイプと合わない場合は自動で調整します。

**例1: 足りない場合**
```
入力: 1,0,0（3要素）
検出: SDXL（20要素必要）
→ 自動調整: 1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
```

**例2: 多すぎる場合**
```
入力: 1,0,0,...,0,0,0（25要素）
検出: SDXL（20要素必要）
→ 自動調整: 1,0,0,...,0,0,0（先頭20要素のみ）
```

---

## 使い方

### **基本的なワークフロー**

```
[Filtered Random LoRA Loader (LBW)]
  MODEL → [KSampler]
  CLIP → [CLIP Text Encode]
  lora_text → [Show Text]（任意、確認用）
```

**手順:**

1. **ノードを配置**
   ```
   [Filtered Random LoRA Loader (LBW)]
   ```

2. **フォルダとキーワードを設定**
   ```
   lora_folder_path: "path/to/loras"
   keyword_filter: "anime style"
   num_loras: 1
   ```

3. **LBWモードを選択**
   ```
   weight_mode: "Style Focused"
   ```

4. **MODEL/CLIPを接続**
   ```
   MODEL → [KSampler]
   CLIP → [CLIP Text Encode]
   ```

### **パラメータ**

#### **LoRA設定**
- `lora_folder_path`: LoRAフォルダのパス
- `num_loras`: 適用するLoRAの数（0〜20）
- `model_strength`: MODELに対するLoRAの強度（例: "1.0" または "0.6-0.9"）
- `clip_strength`: CLIPに対するLoRAの強度（例: "1.0" または "0.6-0.9"）

> フォルダスキャンの挙動（対象拡張子、シンボリックリンクの追跡、候補リストのソート）は他のノードと共通です。詳細は[README_ja.md の「フォルダスキャンについて」](README_ja.md#フォルダスキャンについて)を参照してください。

#### **キーワードフィルタ**
- `keyword_filter`: スペース区切りのキーワード（例: `style anime` や `"anime style" red`）
- `filter_mode`: AND / OR
- `search_in_metadata`: JSONや埋め込みメタデータも検索対象にする（遅くなります）

#### **LBW設定**
- `weight_mode`: Normal / 4つのプリセット / Random / Direct Input
- `lbw_input`: カスタムウェイト（Direct Inputモードのみ）

#### **その他**
- `trigger_word_source`: トリガーワードの取得方法
- `seed`: ランダムシード

---

## 出力形式

### **LBW構文**

LBWを適用した場合、`lora_text`出力（v1.4.0より前は`positive_text`）にLBW構文が含まれます。

**Normal (All 1.0):**
```
<lora:style_anime:0.8:0.8>
```

**LBW適用時（Style Focused、SDXL）:**
```
<lora:style_anime:0.8:0.8:lbw=1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1>
```

**注:** LBWはノード内部でMODELに適用済みです。`lora_text`の構文は、記録や他のノードでの再利用のためのものです。

---

## 使用例

### **例1: 画風のみ変更**

```
[Load Checkpoint] → [Filtered Random LoRA Loader (LBW)]
                     weight_mode: "Style Focused"
                     keyword_filter: "anime"
                     ↓
                     [KSampler]
```

**結果:** 構図はそのまま、画風のみアニメ風に

---

### **例2: 複数LoRAで段階適用**

```
[Load Checkpoint]
  ↓
[Filtered Random LoRA Loader (LBW)] (Structure/Composition Only)
  keyword_filter: "pose"
  ↓
[Filtered Random LoRA Loader (LBW)] (Style Focused)
  keyword_filter: "watercolor"
  ↓
[KSampler]
```

**結果:** ポーズ調整 → 水彩画風適用

---

### **例3: キャラ + 画風**

```
[Load Checkpoint]
  ↓
[Filtered Random LoRA Loader (LBW)] (Character Focused)
  keyword_filter: "character_name"
  ↓
[Filtered Random LoRA Loader (LBW)] (Style Focused)
  keyword_filter: "art_style"
  ↓
[KSampler]
```

**結果:** キャラ特徴保持 + 画風変更

---

## ヒント・Tips

### **1. プリセット選択ガイド**

| LoRAタイプ | 推奨プリセット | 理由 |
|-----------|--------------|------|
| 画風・スタイル | Style Focused | OUTPUTブロックが画風を担うため |
| キャラクター | Character Focused | IN＋MID＋OUTのバランスで特徴を保つため |
| ポーズ・構図 | Structure/Composition Only | INPUTブロックがレイアウトを担うため |
| 汎用・微調整 | Balanced / Soft | 穏やかで重ねやすいため |

---

### **2. 効果の見え方**

プリセットごとの違いが**見えやすい**条件:
- ✅ 強めのLoRA（model_strengthが高い）
- ✅ 1つだけ適用（num_loras=1）
- ✅ 画風・コンセプト系のLoRA

違いが**見えにくい**条件:
- ⚠️ 弱めのLoRA（model_strengthが低い）
- ⚠️ 複数のLoRAを同時に適用
- ⚠️ 学習の効き方がブロック全体に均等に分散しているLoRA

---

### **3. ウェイト0 = 効果なし**

すべてのウェイトを0にすると、LoRAの効果は完全に無効になります。
```
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
```
これはLoRAを適用しないのと同じです。

**ウェイト調整の目安:**
- **0**: 完全無効
- **0.5**: 弱め
- **1.0**: 標準
- **1.5以上**: 強め（効きすぎに注意）

---

### **4. 直列接続**

LoRAごとに異なるLBW設定を使いたい場合は、ノードを直列に接続します。
```
[Filtered Random LoRA Loader (LBW)] (Style Focused)
  ↓
[Filtered Random LoRA Loader (LBW)] (Character Focused)
  ↓
[KSampler]
```

1つのノード内で選ばれたLoRAは、すべて同じLBW設定で適用されます。

**コツ:**
- **構造 → 画風の順**が基本
- 強度もノードごとに個別に調整可能

---

### **5. トラブルシューティング**

**効果が出ない場合:**
- ウェイトがすべて0になっていないか確認
- LoRAが正しく読み込まれているか確認
- コンソールでLBW適用のメッセージを確認

**効果が強すぎる場合:**
- model_strengthを下げる
- Balanced / Softプリセットを試す
- ウェイトを0.5〜0.8に調整

---

## 要件

### **⚠️ 対応モデル**
**本ノードはSD1.5とSDXLモデル専用です。**

- ✅ **対応:** Stable Diffusion 1.5、Stable Diffusion XL（SDXL）
- ❌ **非対応:** Flux、SD3、SDXL Turbo、Pony、その他のアーキテクチャ

LBW機能は、SD1.5/SDXLのU-Netアーキテクチャ専用に設計されています。他のモデルタイプでは正常に動作しません。

---

### **依存関係**
- ComfyUI
- Pillow（ComfyUIに含まれる）
- torch（ComfyUIに含まれる）

### **⚠️ オプション: 動画プレビュー**
**動画ファイルのプレビュー（.mp4, .webm, .avi, .mov）にはopencv-pythonが必要です:**
```bash
pip install opencv-python
```

**opencv-pythonなしの場合:**
- ✅ 静止画・アニメーション画像は動作
- ❌ 動画ファイルは黒画面

---

## プレビュー画像

以下の形式に対応しています（優先順位順）。

1. **静止画像**（.png, .jpg, .jpeg）
2. **アニメーション画像**（.gif, .webp） - 1フレーム目
3. **動画ファイル**（.mp4, .webm, .avi, .mov） - 1フレーム目（opencv-pythonが必要）

LoRAのファイル名に一致するプレビューファイルを自動で探します。

**ファイルマッチング:**
- LoRAファイル名で始まるファイル（大文字小文字は区別しない）
- 例: `style_anime.safetensors` にマッチ:
  - `style_anime.png` ✅
  - `style_anime_preview.jpg` ✅
  - `STYLE_ANIME.PNG` ✅

---

## 上級者向け: カスタムプリセット

独自のプリセットを作成したり、既存のプリセットを変更したい場合は、ソースファイルを直接編集できます。

### **編集方法**

**ファイル位置:**
```
ComfyUI/custom_nodes/RandomLoRALoader/filtered_random_lora_loader_lbw.py
```

**編集箇所:** 29〜41行目（SDXL用が`SDXL_PRESETS`、SD1.5用が`SD15_PRESETS`）

### **例1: 独自プリセット追加**

```python
SDXL_PRESETS = {
    "Style Focused": "1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "Character Focused": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "Structure/Composition Only": "1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    "Balanced / Soft": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0",
    # ↓ 独自プリセット
    "My Custom Mix": "0.5,0.5,0.5,0.5,0,0,0,0,0,0,1,0.8,0.8,0.8,0.8,0.8,0.5,0.5,0.5,0.5"
}
```

### **例2: 既存プリセット調整**

```python
SDXL_PRESETS = {
    # Style Focusedをより強く
    "Style Focused": "1,0,0,0,0,0,0,0,0,0,0,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.2",
    
    # Character Focusedをマイルドに
    "Character Focused": "0.8,0.8,0.8,0.8,0,0,0,0,0,0,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8",
    ...
}
```

### **例3: プリセット名変更**

```python
SDXL_PRESETS = {
    "画風特化": "1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "キャラ重視": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "構図のみ": "1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    ...
}
```

### **重要な注意事項**

⚠️ **編集前に:**
- 元ファイルのバックアップを作成
- Python構文（カンマ、引用符）に注意

⚠️ **ウェイト数:**
- SDXLプリセット: 必ず20要素
- SD1.5プリセット: 必ず17要素
- 要素数が合わない場合は自動調整されますが、正確に指定する方が確実です

⚠️ **編集後:**
- ComfyUIを完全に再起動して変更を適用
- コンソールで構文エラーが出ていないか確認

💡 **ヒント:** ファイル編集が面倒な場合は「Direct Input」モードを使ってください！

---

## 免責事項

- 技術サポートは提供しません
- 動作の保証はありません
- 今後のComfyUIのアップデートとの互換性は保証しません
- バグ報告や機能要望に対応できない場合があります
- 自己責任でご利用ください

---

## 更新履歴

### v1.2.0（2026-01-13）
- ✅ LoRAブロックウェイト（LBW）対応を追加
- ✅ SD1.5/SDXLの自動検出
- ✅ 4つのプリセットモード＋カスタム入力
- ✅ ウェイト数の自動調整
- ✅ 動画プレビュー対応（.mp4, .webm等）

### v1.1.0（2026-01-04）
- ✅ Filtered Random LoRA Loaderを追加
- ✅ キーワードフィルタ（AND/ORモード）
- ✅ メタデータ検索に対応
- ✅ プレビュー画像の表示

### v1.0.0（2025-12-30）
- ✅ 初回リリース
- ✅ Random LoRA Loader（3グループ）

---

## ライセンス

MIT License

---

## 作者

konohana

---

**ブロックウェイトで精密なLoRA制御を楽しんでください！** 🎨✨
