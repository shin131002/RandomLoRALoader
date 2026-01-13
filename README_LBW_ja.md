# Filtered Random LoRA Loader (LBW) - 詳細ガイド

**LoRAブロックウェイト（LBW）対応版**

![FilteredRandomLoRALoader(LBW)ワークフロー例](./images/lbw_final_single.webp)

---

## 概要

Filtered Random LoRA Loader (LBW) は、LoRAブロックウェイト（LBW）機能を追加した高度なノードです。U-Netのどの部分にLoRAを適用するかを細かく制御できます。

---

## 主な機能

### **✅ LoRAブロックウェイト（LBW）対応**
- U-Netのブロックごとに個別の強度を設定
- 画風、キャラクター、構図などを分離制御

### **✅ 自動SD1.5/SDXL検出**
- LoRAファイルを自動判定
- ウェイト数を自動調整

### **✅ 4つのプリセットモード**
- Style Focused（画風特化）
- Character Focused（キャラ重視）
- Structure/Composition Only（構造・構図のみ）
- Balanced / Soft（バランス・穏やか）

### **✅ カスタム入力**
- Direct Inputモードで任意のウェイトを指定
- Preset: Randomモードでランダムプリセット選択

---

## LBWとは？

### **LoRAブロックウェイトの仕組み**

Stable DiffusionのU-Netは以下の3つの部分で構成されています:

```
INPUT blocks  → 構造、構図、レイアウト
   ↓
MIDDLE block  → 全体的な特徴
   ↓
OUTPUT blocks → 画風、ディテール、細部調整
```

LBWを使うと、**各ブロックに異なるLoRA強度を設定**できます。

---

## ブロック構造

### **SDXL（20要素）**

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

---

### **SD1.5（17要素）**

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

## プリセット詳細

### **1. Style Focused（画風特化）**

**SDXL:** `1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`

**特徴:**
- OUTPUTブロックのみ有効
- 構図を変えず画風のみ適用
- 既存の構図を保ちたい場合に最適

**用途:**
- 画風LoRA（アニメ風、水彩風など）
- スタイルLoRA
- エフェクトLoRA

---

### **2. Character Focused（キャラ重視）**

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`

**特徴:**
- INPUT前半 + MIDDLE + OUTPUT有効
- キャラクターの特徴を保持
- バランスの取れた適用

**用途:**
- キャラクターLoRA
- 人物LoRA
- コンセプトLoRA

---

### **3. Structure/Composition Only（構造・構図のみ）**

**SDXL:** `1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`  
**SD1.5:** `1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`

**特徴:**
- INPUT + MIDDLEブロックのみ有効
- 画風を変えず構図のみ変更
- ポーズや構図調整に最適

**用途:**
- ポーズLoRA
- 構図LoRA
- レイアウトLoRA

---

### **4. Balanced / Soft（バランス・穏やか）**

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0`  
**SD1.5:** `1,1,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0`

**特徴:**
- 全体的に穏やかな適用
- OUTPUT後半を弱めて過剰適用を防止
- 自然な仕上がり

**用途:**
- 汎用LoRA
- 微調整用
- 複数LoRA併用時

---

## 使い方

### **基本的な使い方**

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

---

### **Direct Inputモード**

カスタムウェイトを直接入力:

```
weight_mode: "Direct Input"
lbw_input: "1,0.5,0.5,0,0,0,0,0,0,0,1,1,1,1,1,1,0.5,0.5,0.5,0.5"
```

**ルール:**
- カンマ区切り
- SDXL: 20要素、SD1.5: 17要素
- 要素数が合わない場合は自動調整

---

### **Preset: Randomモード**

毎回異なるプリセットをランダム選択:

```
weight_mode: "Preset: Random"
→ 実行ごとに4つのプリセットから1つ選択
```

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

| LoRAタイプ | 推奨プリセット |
|-----------|--------------|
| 画風・スタイル | Style Focused |
| キャラクター | Character Focused |
| ポーズ・構図 | Structure/Composition Only |
| 汎用・微調整 | Balanced / Soft |

---

### **2. 直列接続のコツ**

- **構造 → 画風の順**が基本
- 各ノードで異なるLBW設定可能
- 強度も個別に調整可能

---

### **3. ウェイト調整のコツ**

- **0**: 完全無効
- **0.5**: 弱め
- **1.0**: 標準
- **1.5以上**: 強め（過剰に注意）

---

### **4. トラブルシューティング**

**効果が出ない場合:**
- すべて0になっていないか確認
- LoRAが正しく読み込まれているか確認
- コンソールでLBW適用メッセージを確認

**効果が強すぎる場合:**
- model_strengthを下げる
- Balanced / Softプリセットを試す
- ウェイトを0.5～0.8に調整

---

## 自動検出

### **SD1.5 / SDXL自動判定**

ノードは自動的にLoRAタイプを検出:

```
SDXL検出 → 20要素ウェイト使用
SD1.5検出 → 17要素ウェイト使用
```

**ユーザーは何も設定不要** ✨

---

### **ウェイト数自動調整**

入力したウェイト数が合わない場合、自動調整:

```
入力: 15要素（不足）
検出: SDXL（20要素必要）
→ 末尾に1.0を5個追加

入力: 25要素（過剰）
検出: SDXL（20要素必要）
→ 末尾から5個カット
```

---

## 要件

### **⚠️ 対応モデル**
**本ノードはSD1.5とSDXLモデル専用です。**

- ✅ **対応:** Stable Diffusion 1.5、Stable Diffusion XL（SDXL）
- ❌ **非対応:** Flux、SD3、SDXL Turbo、Pony、その他のアーキテクチャ

LBW機能は、SD1.5/SDXLのU-Netアーキテクチャ専用に設計されています。他のモデルタイプではLBWが正常に動作しません。

---

### **依存関係**
- ComfyUI
- Pillow（ComfyUIに含まれる）
- torch（ComfyUIに含まれる）

### **⚠️ オプション: 動画プレビュー**
**動画ファイルプレビュー（.mp4, .webm, .avi, .mov）にはopencv-pythonが必須です:**
```bash
pip install opencv-python
```

**opencv-pythonなしの場合:**
- ✅ 静止画/アニメ画像は動作
- ❌ 動画ファイルは黒画面

---

## プレビュー画像

以下の形式に対応（優先順位順）:

1. **静止画像**（.png, .jpg, .jpeg） - 常に動作
2. **アニメ画像**（.gif, .webp） - 1フレーム目、常に動作
3. **動画ファイル**（.mp4, .webm, .avi, .mov） - 1フレーム目、opencv-python必要

**ファイルマッチング:**
- LoRAファイル名で始まるファイル（大文字小文字無視）
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

**編集箇所:** 29～41行目

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
- 要素数が合わない場合は自動調整されますが、正確に指定する方が良いです

⚠️ **編集後:**
- ComfyUIを完全に再起動して変更を適用
- コンソールで構文エラーを確認

💡 **ヒント:** ファイル編集が面倒な場合は、「Direct Input」モードを使ってください！

---

## 更新履歴

### v1.2.0（2026-01-13）
- ✅ LoRAブロックウェイト（LBW）対応追加
- ✅ SD1.5/SDXL自動検出
- ✅ 4つのプリセットモード＋カスタム入力
- ✅ ウェイト数自動調整
- ✅ 動画プレビュー対応（.mp4, .webm等）

### v1.1.0（2026-01-04）
- ✅ Filtered Random LoRA Loader追加
- ✅ キーワードフィルタリング（AND/ORモード）
- ✅ メタデータ検索対応
- ✅ プレビュー画像表示

### v1.0.0（2025-12-30）
- ✅ 初回リリース
- ✅ Random LoRA Loader（3グループ）

---

## ライセンス

MIT License

---

## 作者

Your Name

---

**ブロックウェイトで精密なLoRA制御を楽しんでください！** 🎨✨
