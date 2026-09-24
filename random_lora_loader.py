"""
RandomLoRALoader - ComfyUI Custom Node V1

【仕様概要】
指定した3つのフォルダ内のLoRAをランダムに選択し、MODELとCLIPに適用するノード

【入力】
- MODEL: ベースモデル
- CLIP: ベーステキストエンコーダー

【出力】
- MODEL: LoRA適用後のモデル
- CLIP: LoRA適用後のCLIP
- positive_text: 適用したLoRA情報とトリガーワード（positive確認用）
  形式: 追加プロンプト（1行目）+ 各LoRA情報（改行区切り）
- negative_text: negativeプロンプト（json_sample_prompt選択時のみ）
- CONDITIONING (positive): 追加プロンプト+トリガーワード適用後のconditioning
- CONDITIONING (negative): 作例取得時のnegativeプロンプト

【設定項目】（表示順）
1. token_normalization: none/mean/length/length+mean（共通）
2. weight_interpretation: comfy/A1111/compel/comfy++/down_weight（共通）
3. additional_prompt: 追加プロンプト（トリガーワードと結合してCONDITIONINGに適用）（共通）
4-8. グループ1設定（例：style用）
   - lora_folder_path_1: LoRAフォルダの絶対パス
   - include_subfolders_1: サブフォルダを含めるか
   - model_strength_1: MODEL適用強度
   - clip_strength_1: CLIP適用強度
   - num_loras_1: 選択するLoRA個数
9-13. グループ2設定（例：character用）
   - lora_folder_path_2: LoRAフォルダの絶対パス
   - include_subfolders_2: サブフォルダを含めるか
   - model_strength_2: MODEL適用強度
   - clip_strength_2: CLIP適用強度
   - num_loras_2: 選択するLoRA個数
14-18. グループ3設定（例：concept用）
   - lora_folder_path_3: LoRAフォルダの絶対パス
   - include_subfolders_3: サブフォルダを含めるか
   - model_strength_3: MODEL適用強度
   - clip_strength_3: CLIP適用強度
   - num_loras_3: 選択するLoRA個数
19. trigger_word_source: json_combined/json_random/json_sample_prompt/metadata（共通）
20. seed: ランダム選択のシード値（共通、ComfyUI標準のcontrol_before_generateで制御）

【その他仕様】
- メタデータ読み取り優先順位:
  1. {LoRAファイル名}.metadata.json (ComfyUI Lora Manager)
  2. {LoRAファイル名}.info (Civitai Helper)
  3. LoRA本体ファイルの埋め込みメタデータ
- trigger_word_source="metadata"時は埋め込みメタデータのみを参照
- 同じLoRAの重複選択なし（不足時は再選択で埋める）
- json_sample_prompt選択時はpositive/negativeを分離
- 作例プロンプト内のLoRA記述（<lora:xxx:x.x>）は削除
- LoRA適用はpositiveのみ
- 空のフォルダ指定はスキップ（エラーなし）
- 全グループ空でもエラーなし（空テキスト出力）
"""

import os
import json
import random
import glob
import re
from pathlib import Path
import folder_paths
import comfy.sd
import comfy.utils

# LoRA埋め込みメタデータ読み込み用
try:
    from safetensors.torch import safe_open
    SAFETENSORS_AVAILABLE = True
except ImportError:
    SAFETENSORS_AVAILABLE = False
    print("[RandomLoRALoader] safetensors not available, embedded metadata reading disabled")

class RandomLoRALoader:
    """ランダムLoRA選択・適用ノード（3グループ対応）"""
    
    # クラス変数（opencv警告表示フラグ）
    _opencv_warning_shown = False
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "token_normalization": (
                    ["none", "mean", "length", "length+mean"],
                    {
                        "default": "none"
                    }
                ),
                "weight_interpretation": (
                    ["comfy", "A1111", "compel", "comfy++", "down_weight"],
                    {
                        "default": "A1111"
                    }
                ),
                "additional_prompt_positive": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Additional positive prompt"
                }),
                "additional_prompt_negative": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Additional negative prompt"
                }),
                # グループ1
                "lora_folder_path_1": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Group 1 LoRA folder path (e.g., style)"
                }),
                "include_subfolders_1": ("BOOLEAN", {
                    "default": True
                }),
                "unique_by_filename_1": ("BOOLEAN", {
                    "default": True,
                    "label": "Unique by filename (exclude duplicates)"
                }),
                "model_strength_1": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "clip_strength_1": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "num_loras_1": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                # グループ2
                "lora_folder_path_2": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Group 2 LoRA folder path (e.g., character)"
                }),
                "include_subfolders_2": ("BOOLEAN", {
                    "default": True
                }),
                "unique_by_filename_2": ("BOOLEAN", {
                    "default": True,
                    "label": "Unique by filename (exclude duplicates)"
                }),
                "model_strength_2": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "clip_strength_2": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "num_loras_2": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                # グループ3
                "lora_folder_path_3": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Group 3 LoRA folder path (e.g., concept)"
                }),
                "include_subfolders_3": ("BOOLEAN", {
                    "default": True
                }),
                "unique_by_filename_3": ("BOOLEAN", {
                    "default": True,
                    "label": "Unique by filename (exclude duplicates)"
                }),
                "model_strength_3": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "clip_strength_3": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.4-0.8"
                }),
                "num_loras_3": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "display": "number"
                }),
                # 共通設定
                "trigger_word_source": (
                    ["json_combined", "json_random", "json_sample_prompt", "metadata"],
                    {
                        "default": "json_combined"
                    }
                ),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number"
                }),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "CONDITIONING", "CONDITIONING", "IMAGE", "STRING")
    # 0〜6番はv1.4.0以前と位置・型とも同じ（保存済みワークフローは出力を番号で接続するため）。
    # v1.4.0での変更:
    #   positive_text (2番) … <lora:...> を含まない。positive (CONDITIONING) にエンコード
    #                         される文字列そのもの
    #   lora_text     (7番) … 以前の positive_text の内容（<lora:...> 付き）。記録用
    RETURN_NAMES = ("MODEL", "CLIP", "positive_text", "negative_text", "positive", "negative", "preview", "lora_text")
    FUNCTION = "load_random_loras"
    CATEGORY = "loaders"
    
    def _find_lora_files(self, folder_path, include_subfolders):
        """
        指定フォルダ内のLoRAファイル（.safetensors / .pt / .ckpt）を検索
        
        Args:
            folder_path: 検索対象フォルダの絶対パス
            include_subfolders: サブフォルダを含めるか
        
        Returns:
            list: LoRAファイルパスのリスト
        """
        if not os.path.exists(folder_path):
            print(f"[RandomLoRALoader] フォルダが存在しません: {folder_path}")
            return []
        
        lora_files = []
        # Filtered版と対象拡張子を揃えている
        extensions = ['.safetensors', '.pt', '.ckpt']

        if include_subfolders:
            # glob の "**" はシンボリックリンクのディレクトリを辿らないため
            # os.walk(followlinks=True) に置き換えている。ComfyUI本体の
            # フォルダスキャン (folder_paths.recursive_search) と挙動を揃える
            # ためで、これがないとリンク先にしか存在しないLoRAが、
            # ComfyUIネイティブのドロップダウンには出るのにここでは
            # 候補に入らない、という食い違いが起きる。
            #
            # realpathの集合はリンクを辿る代償。リンクが循環している場合に
            # スキャンが無限ループするのを防ぎ、同じフォルダに2本のリンクが
            # 張られている場合の二重スキャンも抑止する。
            seen_dirs = set()
            for root, dirs, files in os.walk(folder_path, followlinks=True):
                real_root = os.path.realpath(root)
                if real_root in seen_dirs:
                    dirs[:] = []
                    continue
                seen_dirs.add(real_root)
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        lora_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in extensions):
                    lora_files.append(file_path)

        # ソートして返す。以前は列挙順がファイルシステム任せだったため、
        # 同じシードでもマシンが変われば選ばれるLoRAが違っていた。
        # ソートすることでシード指定が環境をまたいで再現するようになる。
        lora_files = sorted(lora_files)
        print(f"[RandomLoRALoader] 検出されたLoRA数: {len(lora_files)}")
        return lora_files
    
    def _select_random_loras(self, lora_files, num_loras, seed):
        """
        LoRAファイルをランダムに選択（重複なし、不足時は再選択）
        
        Args:
            lora_files: LoRAファイルパスのリスト
            num_loras: 選択する個数
            seed: ランダムシード
        
        Returns:
            list: 選択されたLoRAファイルパスのリスト
        """
        if not lora_files:
            return []
        
        random.seed(seed)
        
        # 重複なしで選択できる最大数
        available_count = len(lora_files)
        
        if num_loras <= available_count:
            # 十分な数がある場合は重複なしで選択
            return random.sample(lora_files, num_loras)
        else:
            # 不足する場合は全て選択後、再選択で埋める
            selected = lora_files.copy()
            remaining = num_loras - available_count
            
            # 不足分をランダムに追加
            for _ in range(remaining):
                selected.append(random.choice(lora_files))
            
            # 最終的にシャッフル
            random.shuffle(selected)
            return selected
    
    def _unique_by_filename(self, lora_files, group_name=""):
        """
        ファイル名でユニーク化（重複ファイル名を除外）
        
        Args:
            lora_files: LoRAファイルパスのリスト
            group_name: グループ名（ログ用）
        
        Returns:
            list: ファイル名がユニークなファイルパスのリスト
        """
        seen_names = {}
        unique_files = []
        
        for file_path in lora_files:
            filename = os.path.basename(file_path)
            
            if filename not in seen_names:
                seen_names[filename] = file_path
                unique_files.append(file_path)
            else:
                # 重複検出時はログ出力
                print(f"[RandomLoRALoader] {group_name}: Duplicate filename detected: {filename}")
                print(f"  Keeping: {seen_names[filename]}")
                print(f"  Skipping: {file_path}")
        
        return unique_files
    
    def _parse_strength(self, strength_str):
        """
        強度文字列をパースして値を返す
        
        対応形式:
        - "1.0" → 1.0（そのまま）
        - "0.55" → 0.55（そのまま）
        - "0.4-0.8" → 0.4, 0.5, 0.6, 0.7, 0.8からランダム（0.1刻み）
        - "0.44-0.82" → 0.4, 0.5, 0.6, 0.7, 0.8からランダム（範囲を1桁に丸める）
        - "-0.8--0.3" → -0.8, -0.7, -0.6, ..., -0.3からランダム（マイナス範囲対応）
        
        Args:
            strength_str: 強度文字列
        
        Returns:
            float: 実際に使用する強度値
        """
        import re
        strength_str = str(strength_str).strip()
        
        # 範囲指定のパターンマッチ（マイナス値対応）
        # 例: "0.6-0.9", "-0.8--0.3", "-0.5-0.5", "0.3--0.7"
        range_pattern = r'^(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*)$'
        match = re.match(range_pattern, strength_str)
        
        if match:
            try:
                # 範囲の上限下限を1桁に丸める
                min_val = round(float(match.group(1)), 1)
                max_val = round(float(match.group(2)), 1)
                
                # バリデーション
                if min_val < -10.0 or max_val > 10.0:
                    raise ValueError("強度は -10.0 〜 10.0 の範囲で指定してください")
                if min_val > max_val:
                    raise ValueError("最小値は最大値より小さくしてください")
                
                # 0.1刻みの値のリストを生成
                values = []
                current = min_val
                while current <= max_val + 0.01:  # 浮動小数点誤差対策
                    values.append(round(current, 1))
                    current += 0.1
                
                # 念のため空リストチェック
                if not values:
                    print(f"[RandomLoRALoader] ❌ 範囲指定エラー、1.0を使用")
                    return 1.0
                
                # ランダムに1つ選択
                selected = random.choice(values)
                print(f"[RandomLoRALoader] 強度範囲 {min_val}-{max_val} から {selected} を選択")
                return selected
                
            except ValueError as e:
                print(f"[RandomLoRALoader] ❌ 強度パースエラー: {e}")
                print(f"[RandomLoRALoader] 💡 使用例: '1.0' または '0.4-0.8'")
                return 1.0
            except Exception as e:
                print(f"[RandomLoRALoader] ❌ 予期しないエラー: {e}")
                return 1.0
        else:
            # 通常の数値（そのまま使用）
            try:
                value = float(strength_str)
                if value < -10.0 or value > 10.0:
                    print(f"[RandomLoRALoader] ❌ 強度 {value} は範囲外、1.0を使用")
                    return 1.0
                return value
            except:
                print(f"[RandomLoRALoader] ❌ 強度 '{strength_str}' を解析できません、1.0を使用")
                print(f"[RandomLoRALoader] 💡 使用例: '1.0' または '0.4-0.8'")
                return 1.0
    
    def _load_json_metadata(self, lora_path):
        """
        外部JSONファイルまたはLoRA埋め込みメタデータを読み込む
        
        優先順位:
        1. {filename}.metadata.json (ComfyUI Lora Manager形式)
        2. {filename}.info (Civitai Helper形式)
        3. LoRA本体ファイルの埋め込みメタデータ
        
        Args:
            lora_path: LoRAファイルパス (.safetensors / .pt / .ckpt)
        
        Returns:
            dict: JSONデータ（読み込み失敗時はNone）
        """
        # 拡張子を除いたファイル名を取得
        base_name = os.path.splitext(lora_path)[0]
        
        # 優先順位1: .metadata.json (ComfyUI Lora Manager)
        json_path_metadata = f"{base_name}.metadata.json"
        if os.path.exists(json_path_metadata):
            try:
                with open(json_path_metadata, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[RandomLoRALoader] JSON読み込みエラー ({json_path_metadata}): {e}")
        
        # 優先順位2: .info (Civitai Helper)
        json_path_info = f"{base_name}.info"
        if os.path.exists(json_path_info):
            try:
                with open(json_path_info, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[RandomLoRALoader] JSON読み込みエラー ({json_path_info}): {e}")
        
        # 優先順位3: LoRA本体ファイルの埋め込みメタデータ
        embedded_data = self._load_embedded_metadata(lora_path)
        if embedded_data:
            return embedded_data
        
        # どれも見つからない
        print(f"[RandomLoRALoader] メタデータが見つかりません: {base_name}")
        return None
    
    def _load_embedded_metadata(self, lora_path):
        """
        LoRA本体ファイルの埋め込みメタデータを読み込む
        
        Args:
            lora_path: LoRAファイルパス (.safetensors)
        
        Returns:
            dict: メタデータ（読み込み失敗時はNone）
        """
        if not SAFETENSORS_AVAILABLE:
            return None
        
        # safe_open は .safetensors しか読めない。.pt/.ckpt も候補に含むように
        # なったため、ここで弾いておかないと選択のたびにエラーログが出る
        if not lora_path.lower().endswith(".safetensors"):
            return None
        
        if not os.path.exists(lora_path):
            return None
        
        try:
            with safe_open(lora_path, framework="pt", device="cpu") as f:
                metadata = f.metadata()
                
                if not metadata:
                    return None
                
                # ss_tag_frequency（kohya_ss形式）からトリガーワード抽出
                if "ss_tag_frequency" in metadata:
                    tag_freq_str = metadata.get("ss_tag_frequency", "{}")
                    try:
                        tag_freq = json.loads(tag_freq_str)
                        # 最も頻度の高いタグセットを取得
                        if tag_freq:
                            # 各データセットのタグを結合
                            all_tags = []
                            for dataset_tags in tag_freq.values():
                                all_tags.extend(dataset_tags.keys())
                            
                            # 重複除去
                            unique_tags = list(dict.fromkeys(all_tags))
                            
                            # Civitai形式に変換
                            trigger_words = ", ".join(unique_tags[:20])  # 上位20個
                            
                            return {
                                "civitai": {
                                    "trainedWords": [trigger_words]
                                }
                            }
                    except json.JSONDecodeError:
                        pass
                
                # その他のメタデータフィールドからトリガーワード抽出
                if "modelspec.trigger_word" in metadata:
                    trigger = metadata["modelspec.trigger_word"]
                    return {
                        "civitai": {
                            "trainedWords": [trigger]
                        }
                    }
                
                # ss_output_name（モデル名）
                if "ss_output_name" in metadata:
                    output_name = metadata["ss_output_name"]
                    return {
                        "civitai": {
                            "trainedWords": [output_name]
                        }
                    }
                
                return None
                
        except Exception as e:
            print(f"[RandomLoRALoader] 埋め込みメタデータ読み込みエラー ({lora_path}): {e}")
            return None
    
    def _get_trigger_words_combined(self, lora_path):
        """
        JSONから全トリガーワードパターンを結合して取得（重複除去）
        
        Args:
            lora_path: LoRAファイルパス
        
        Returns:
            str: 全トリガーワードを結合した文字列
        """
        json_data = self._load_json_metadata(lora_path)
        if not json_data:
            return ""
        
        # civitai.trainedWordsを取得
        trained_words = json_data.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            print(f"[RandomLoRALoader] trainedWordsが見つかりません: {lora_path}")
            return ""
        
        # 全パターンを結合して重複除去
        all_tags = []
        for pattern in trained_words:
            tags = [tag.strip() for tag in pattern.split(',')]
            all_tags.extend(tags)
        
        # 重複除去（順序を保持）
        unique_tags = []
        seen = set()
        for tag in all_tags:
            if tag and tag.lower() not in seen:
                unique_tags.append(tag)
                seen.add(tag.lower())
        
        return ", ".join(unique_tags)
    
    def _get_trigger_words_random(self, lora_path):
        """
        JSONからトリガーワードパターンをランダムに1つ選択
        
        Args:
            lora_path: LoRAファイルパス
        
        Returns:
            str: ランダムに選択されたトリガーワードパターン
        """
        json_data = self._load_json_metadata(lora_path)
        if not json_data:
            return ""
        
        # civitai.trainedWordsを取得
        trained_words = json_data.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            print(f"[RandomLoRALoader] trainedWordsが見つかりません: {lora_path}")
            return ""
        
        # ランダムに1つ選択
        selected_pattern = random.choice(trained_words)
        
        # パターン内で重複除去
        tags = [tag.strip() for tag in selected_pattern.split(',')]
        unique_tags = []
        seen = set()
        for tag in tags:
            if tag and tag.lower() not in seen:
                unique_tags.append(tag)
                seen.add(tag.lower())
        
        return ", ".join(unique_tags)
    
    def _get_sample_prompt_from_json(self, lora_path):
        """
        JSONから作例プロンプトをランダムに1つ取得
        作例プロンプト内のLoRA記述を削除
        
        Args:
            lora_path: LoRAファイルパス
        
        Returns:
            tuple: (positive_prompt, negative_prompt)
        """
        json_data = self._load_json_metadata(lora_path)
        if not json_data:
            return "", ""
        
        # civitai.imagesを取得
        images = json_data.get("civitai", {}).get("images", [])
        if not images:
            print(f"[RandomLoRALoader] imagesが見つかりません: {lora_path}")
            return "", ""
        
        # metaを持つ画像のみをフィルタ（metaがNoneでないことも確認）
        valid_images = [img for img in images if "meta" in img and img["meta"] is not None]
        if not valid_images:
            print(f"[RandomLoRALoader] metaを持つ画像が見つかりません: {lora_path}")
            return "", ""
        
        # ランダムに1つ選択
        selected_image = random.choice(valid_images)
        meta = selected_image.get("meta", {})
        
        positive = meta.get("prompt", "")
        negative = meta.get("negativePrompt", "")
        
        # LoRA記述を削除（<lora:xxx:x.x>または<lora:xxx:x.x:x.x>形式）
        lora_pattern = r'<lora:[^>]+>'
        positive = re.sub(lora_pattern, '', positive)
        negative = re.sub(lora_pattern, '', negative)
        
        # 複数の空白やカンマを整理
        positive = re.sub(r'\s*,\s*,+\s*', ', ', positive)  # 連続カンマを1つに
        positive = re.sub(r'^\s*,\s*|\s*,\s*$', '', positive)  # 先頭末尾のカンマ削除
        positive = re.sub(r'\s+', ' ', positive).strip()  # 複数空白を1つに
        
        negative = re.sub(r'\s*,\s*,+\s*', ', ', negative)
        negative = re.sub(r'^\s*,\s*|\s*,\s*$', '', negative)
        negative = re.sub(r'\s+', ' ', negative).strip()
        
        return positive, negative
    
    def _get_trigger_words_from_embedded(self, lora_path):
        """
        LoRA埋め込みメタデータから直接トリガーワードを取得
        外部JSONファイルを無視して、LoRA本体ファイルのみを参照
        
        Args:
            lora_path: LoRAファイルパス
        
        Returns:
            str: トリガーワード
        """
        embedded_data = self._load_embedded_metadata(lora_path)
        if not embedded_data:
            return ""
        
        # civitai.trainedWordsを取得（_load_embedded_metadataで変換済み）
        trained_words = embedded_data.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            return ""
        
        # 最初のパターンを使用（埋め込みデータは通常1つ）
        return trained_words[0] if trained_words else ""
    
    def _load_lora(self, model, clip, lora_path, model_strength, clip_strength):
        """
        LoRAをMODELとCLIPに適用
        
        Args:
            model: 入力MODEL
            clip: 入力CLIP
            lora_path: LoRAファイルパス
            model_strength: MODEL適用強度
            clip_strength: CLIP適用強度
        
        Returns:
            tuple: (適用後MODEL, 適用後CLIP)
        """
        try:
            # LoRA読み込み時の警告を完全抑制
            import logging
            import warnings
            import sys
            import os
            import builtins
            
            # Pythonの警告を一時的に無効化
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                
                # 全ロガーのログレベルを一時的に上げる
                loggers_to_suppress = [
                    logging.getLogger("comfy"),
                    logging.getLogger("comfy.sd"),
                    logging.getLogger("comfy.utils"),
                    logging.getLogger(),  # rootロガー
                ]
                original_levels = {}
                for logger in loggers_to_suppress:
                    original_levels[logger] = logger.level
                    logger.setLevel(logging.CRITICAL)
                
                # 標準出力・標準エラー出力を両方とも一時的にリダイレクト
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                devnull = open(os.devnull, 'w')
                sys.stdout = devnull
                sys.stderr = devnull
                
                # builtins.printも一時的に無効化（最終手段）
                original_print = builtins.print
                def silent_print(*args, **kwargs):
                    # "lora key not loaded"を含むメッセージだけ抑制
                    message = ' '.join(str(arg) for arg in args)
                    if 'lora key not loaded' not in message.lower():
                        original_print(*args, **kwargs, file=old_stdout)
                builtins.print = silent_print
                
                try:
                    lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
                    
                    # MODELにLoRA適用
                    model_lora, _ = comfy.sd.load_lora_for_models(
                        model, None, lora, model_strength, 0
                    )
                    
                    # CLIPにLoRA適用
                    _, clip_lora = comfy.sd.load_lora_for_models(
                        None, clip, lora, 0, clip_strength
                    )
                    
                    return model_lora, clip_lora
                finally:
                    # すべてを元に戻す
                    builtins.print = original_print
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                    devnull.close()
                    
                    # ログレベルを元に戻す
                    for logger, level in original_levels.items():
                        logger.setLevel(level)
        
        except Exception as e:
            print(f"[RandomLoRALoader] LoRA読み込みエラー ({lora_path}): {e}")
            return model, clip
    
    def _remove_lora_syntax(self, text):
        """
        テキストから<lora:xxx:0.8>形式の構文を削除
        
        Args:
            text: 入力テキスト
        
        Returns:
            LoRA構文を削除したテキスト
        """
        if not text:
            return text
        
        # <lora:filename:strength> または <lora:filename:model_str:clip_str> を削除
        text = re.sub(r'<lora:[^>]+>', '', text)
        
        # 連続カンマを整理
        text = re.sub(r',(\s*,)+', ',', text)  # 3つ以上連続しても1回で詰める
        
        # 行頭・行末の空白とカンマを削除
        text = text.strip().strip(',').strip()
        
        return text
    
    def _load_preview_image_as_tensor(self, lora_path):
        """
        プレビュー画像をTensorとして読み込み（部分一致、長辺1240px）
        
        検索方法:
          LoRAファイル名（拡張子除く）で始まるファイルを検索
          優先順位:
            1. 静止画像 (.png, .jpg, .jpeg, .webp)
            2. 動画ファイル (.gif, .webp, .mp4, .webm) の1フレーム目
          
          例: style_anime_v1.safetensors
            → style_anime_v1.png
            → style_anime_v1_preview.jpg
            → style_anime_v1.gif (1フレーム目)
            → style_anime_v1.mp4 (1フレーム目、opencv-pythonが必要)
            → STYLE_ANIME_V1.PNG (大文字小文字無視)
        
        リサイズ:
          長辺を1240pxに統一（アスペクト比保持）
        
        Returns:
            torch.Tensor: (H, W, C) 形式、見つからない場合はNone
        """
        try:
            from PIL import Image
            import numpy as np
            import torch
        except ImportError:
            return None
        
        # LoRAファイル名（拡張子なし）
        base_name = os.path.splitext(os.path.basename(lora_path))[0]
        folder = os.path.dirname(lora_path)
        
        # ファイル拡張子（優先順位順）
        static_image_exts = ('.png', '.jpg', '.jpeg')
        animated_image_exts = ('.gif', '.webp')  # Pillowで対応可能
        video_exts = ('.mp4', '.webm', '.avi', '.mov')  # opencv-python必要
        
        try:
            # 同じフォルダ内のファイルを検索
            files = os.listdir(folder)
            
            # 部分一致するファイルを収集
            matched_files = []
            for file in files:
                if file.lower().startswith(base_name.lower()):
                    matched_files.append(file)
            
            if not matched_files:
                return None
            
            # 優先順位でソート
            def get_priority(filename):
                lower = filename.lower()
                if any(lower.endswith(ext) for ext in static_image_exts):
                    return 0  # 最優先
                elif any(lower.endswith(ext) for ext in animated_image_exts):
                    return 1  # 次優先
                elif any(lower.endswith(ext) for ext in video_exts):
                    return 2  # 最後
                else:
                    return 999  # その他
            
            matched_files.sort(key=get_priority)
            
            # 各ファイルを試す
            for file in matched_files:
                preview_path = os.path.join(folder, file)
                lower_file = file.lower()
                
                # 静止画像
                if any(lower_file.endswith(ext) for ext in static_image_exts):
                    img = self._load_static_image(preview_path)
                    if img is not None:
                        return img
                
                # アニメーション画像（GIF/WebP）
                elif any(lower_file.endswith(ext) for ext in animated_image_exts):
                    img = self._load_animated_image_first_frame(preview_path)
                    if img is not None:
                        return img
                
                # 動画ファイル（opencv-python必要）
                elif any(lower_file.endswith(ext) for ext in video_exts):
                    img = self._load_video_first_frame(preview_path)
                    if img is not None:
                        return img
        
        except Exception as e:
            print(f"[RandomLoRALoader] Folder read error: {e}")
        
        return None
    
    def _load_static_image(self, image_path):
        """静止画像を読み込み"""
        try:
            from PIL import Image
            import numpy as np
            import torch
            
            img = Image.open(image_path).convert('RGB')
            return self._resize_and_convert_image(img)
        except Exception as e:
            print(f"[RandomLoRALoader] Static image load error ({image_path}): {e}")
            return None
    
    def _load_animated_image_first_frame(self, image_path):
        """アニメーション画像（GIF/WebP）の1フレーム目を読み込み"""
        try:
            from PIL import Image
            import numpy as np
            import torch
            
            img = Image.open(image_path)
            
            # 1フレーム目に移動
            if hasattr(img, 'seek'):
                img.seek(0)
            
            img = img.convert('RGB')
            return self._resize_and_convert_image(img)
        except Exception as e:
            print(f"[RandomLoRALoader] Animated image load error ({image_path}): {e}")
            return None
    
    def _load_video_first_frame(self, video_path):
        """動画ファイルの1フレーム目を読み込み（opencv-python必要）"""
        try:
            import cv2
            from PIL import Image
            import numpy as np
            import torch
            
            # OpenCVで動画を開く
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None
            
            # 1フレーム目を読み込み
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
            
            # BGR → RGB 変換
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # PIL Imageに変換
            img = Image.fromarray(frame_rgb)
            
            return self._resize_and_convert_image(img)
        
        except ImportError:
            # opencv-pythonがインストールされていない（初回のみ警告）
            if not RandomLoRALoader._opencv_warning_shown:
                print("=" * 60)
                print("[RandomLoRALoader] Video Preview Support")
                print("=" * 60)
                print(f"Video file detected: {os.path.basename(video_path)}")
                print("opencv-python is not installed.")
                print("")
                print("To enable video preview support, install:")
                print("  pip install opencv-python")
                print("")
                print("Static images (.png/.jpg) and animated images (.gif/.webp)")
                print("will continue to work without opencv-python.")
                print("=" * 60)
                RandomLoRALoader._opencv_warning_shown = True
            return None
        except Exception as e:
            print(f"[RandomLoRALoader] Video load error ({video_path}): {e}")
            return None
    
    def _resize_and_convert_image(self, img):
        """画像をリサイズしてTensorに変換"""
        try:
            from PIL import Image
            import numpy as np
            import torch
            
            # 長辺を1240pxにリサイズ（アスペクト比保持）
            width, height = img.size
            max_size = 1240
            
            if max(width, height) > max_size:
                # 長辺が1240pxを超える場合はリサイズ
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            elif max(width, height) < max_size:
                # 長辺が1240px未満の場合は拡大
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # numpy配列に変換 (H, W, C)
            img_array = np.array(img).astype(np.float32) / 255.0
            # Tensor化
            return torch.from_numpy(img_array)
        
        except Exception as e:
            print(f"[RandomLoRALoader] Image resize/convert error: {e}")
            return None
    
    def _generate_preview_batch(self, preview_images):
        """
        プレビュー画像のバッチを生成（1240pxに統一、パディング）
        
        Args:
            preview_images: list of torch.Tensor (各々 H, W, C、長辺1240px)
        
        Returns:
            torch.Tensor: (B, 1240, 1240, C) 形式
        """
        try:
            import torch
            import torch.nn.functional as F
        except ImportError:
            return None
        
        if not preview_images:
            # プレビュー画像なし → 黒画像1枚（1240x1240）
            black_image = torch.zeros((1, 1240, 1240, 3), dtype=torch.float32)
            return black_image
        
        # 全て1240x1240にパディング
        padded_images = []
        target_size = 1240
        
        for img in preview_images:
            h, w, c = img.shape
            
            # パディングが必要か確認
            if h == target_size and w == target_size:
                padded_images.append(img)
            else:
                # パディング量を計算（中央配置）
                pad_h = target_size - h
                pad_w = target_size - w
                pad_top = pad_h // 2
                pad_bottom = pad_h - pad_top
                pad_left = pad_w // 2
                pad_right = pad_w - pad_left
                
                # (H, W, C) → (C, H, W) に変換してパディング
                img_chw = img.permute(2, 0, 1)  # (C, H, W)
                
                # F.pad: (left, right, top, bottom)
                padded = F.pad(img_chw, (pad_left, pad_right, pad_top, pad_bottom), value=0)
                
                # (C, H, W) → (H, W, C) に戻す
                padded = padded.permute(1, 2, 0)
                padded_images.append(padded)
        
        # バッチ化 (B, 1240, 1240, C)
        preview_batch = torch.stack(padded_images, dim=0)
        return preview_batch
    
    def _encode_prompt(self, clip, text, token_normalization, weight_interpretation):
        """
        プロンプトをCLIPでエンコードしてCONDITIONINGを生成
        
        Args:
            clip: CLIP
            text: プロンプトテキスト
            token_normalization: none/mean/length/length+mean
            weight_interpretation: comfy/A1111/compel/comfy++/down_weight
        
        Returns:
            CONDITIONING
        """
        # CLIPのエンコードメソッドを呼び出し
        # Note: ComfyUIの実装に依存するため、実際のAPIに合わせて調整が必要
        try:
            # token_normalizationの設定を反映
            tokens = clip.tokenize(text)
            
            # weight_interpretationに応じた処理
            # （実際の実装はComfyUIの内部APIに依存）
            
            cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
            
            return [[cond, {"pooled_output": pooled}]]
        
        except Exception as e:
            print(f"[RandomLoRALoader] プロンプトエンコードエラー: {e}")
            # フォールバック: 空のCONDITIONING
            return [[clip.encode(""), {}]]
    
    def load_random_loras(
        self,
        model,
        clip,
        token_normalization,
        weight_interpretation,
        additional_prompt_positive,
        additional_prompt_negative,
        # グループ1
        lora_folder_path_1,
        include_subfolders_1,
        unique_by_filename_1,
        model_strength_1,
        clip_strength_1,
        num_loras_1,
        # グループ2
        lora_folder_path_2,
        include_subfolders_2,
        unique_by_filename_2,
        model_strength_2,
        clip_strength_2,
        num_loras_2,
        # グループ3
        lora_folder_path_3,
        include_subfolders_3,
        unique_by_filename_3,
        model_strength_3,
        clip_strength_3,
        num_loras_3,
        # 共通
        trigger_word_source,
        seed
    ):
        """
        メイン処理：ランダムLoRA選択・適用（3グループ対応）
        
        Returns:
            tuple: (MODEL, CLIP, lora_text_output, negative_text_output, positive_conditioning, negative_conditioning)
        """
        # seedをそのまま使用（ComfyUIのcontrol_before_generateで制御される）
        print(f"[RandomLoRALoader] 使用seed: {seed}")
        
        # 全テキスト出力用のリスト
        all_text_parts = []
        
        # 全positive/negativeプロンプトを蓄積
        all_positive_parts = []
        all_negative_parts = []
        
        # プレビュー画像収集
        preview_images = []
        
        # 3つのグループを処理
        groups = [
            (lora_folder_path_1, include_subfolders_1, unique_by_filename_1, model_strength_1, clip_strength_1, num_loras_1, "Group 1"),
            (lora_folder_path_2, include_subfolders_2, unique_by_filename_2, model_strength_2, clip_strength_2, num_loras_2, "Group 2"),
            (lora_folder_path_3, include_subfolders_3, unique_by_filename_3, model_strength_3, clip_strength_3, num_loras_3, "Group 3"),
        ]
        
        for folder_path, include_subs, unique_by_name, model_str, clip_str, num, group_name in groups:
            # フォルダパスが空、またはnum_lorasが0の場合はスキップ
            if not folder_path.strip() or num == 0:
                print(f"[RandomLoRALoader] {group_name}: スキップ（フォルダ未指定またはnum=0）")
                continue
            
            # LoRAファイルを検索
            lora_files = self._find_lora_files(folder_path, include_subs)
            
            if not lora_files:
                print(f"[RandomLoRALoader] {group_name}: LoRAファイルが見つかりませんでした")
                continue
            
            # ファイル名でユニーク化（重複ファイル名を除外）
            if unique_by_name:
                lora_files = self._unique_by_filename(lora_files, group_name)
                if not lora_files:
                    print(f"[RandomLoRALoader] {group_name}: ユニーク化後にファイルがありません")
                    continue
            
            # ランダムにLoRAを選択（全グループ共通のseedを使用）
            selected_loras = self._select_random_loras(lora_files, num, seed)
            
            print(f"[RandomLoRALoader] {group_name}: {len(selected_loras)}個のLoRAを選択")
            
            # 各LoRAを順次適用
            for lora_path in selected_loras:
                lora_name = os.path.splitext(os.path.basename(lora_path))[0]
                
                # 強度文字列をパース（ランダム範囲対応）
                actual_model_str = self._parse_strength(model_str)
                actual_clip_str = self._parse_strength(clip_str)
                
                # LoRA適用ログ（ファイル名と強度を表示）
                print(f"[RandomLoRALoader]   → {lora_name} (MODEL:{actual_model_str}, CLIP:{actual_clip_str})")
                
                # LoRAをMODELとCLIPに適用
                model, clip = self._load_lora(model, clip, lora_path, actual_model_str, actual_clip_str)
                
                # トリガーワードを取得（ソースに応じて処理を分岐）
                if trigger_word_source == "json_combined":
                    trigger_words = self._get_trigger_words_combined(lora_path)
                    all_positive_parts.append(trigger_words)
                    trigger_display = trigger_words
                
                elif trigger_word_source == "json_random":
                    trigger_words = self._get_trigger_words_random(lora_path)
                    all_positive_parts.append(trigger_words)
                    trigger_display = trigger_words
                
                elif trigger_word_source == "json_sample_prompt":
                    positive_prompt, negative_prompt = self._get_sample_prompt_from_json(lora_path)
                    all_positive_parts.append(positive_prompt)
                    all_negative_parts.append(negative_prompt)
                    trigger_display = positive_prompt
                
                elif trigger_word_source == "metadata":
                    trigger_words = self._get_trigger_words_from_embedded(lora_path)
                    all_positive_parts.append(trigger_words)
                    trigger_display = trigger_words
                
                # テキスト出力に追加（末尾にカンマを付ける）
                lora_notation = f"<lora:{lora_name}:{actual_model_str}:{actual_clip_str}>"
                all_text_parts.append(f"{lora_notation}, {trigger_display},")
                
                # プレビュー画像を読み込み
                preview = self._load_preview_image_as_tensor(lora_path)
                if preview is not None:
                    preview_images.append(preview)
        
        # テキスト出力を結合（追加プロンプトを先頭に配置、末尾にカンマを付ける）
        if additional_prompt_positive.strip():
            # 追加プロンプトの末尾にカンマがなければ追加
            additional_with_comma = additional_prompt_positive.strip()
            if not additional_with_comma.endswith(','):
                additional_with_comma += ','
            if all_text_parts:
                # LoRAがある場合: 追加プロンプト + LoRA情報
                lora_text_output = additional_with_comma + "\n" + "\n".join(all_text_parts)
            else:
                # LoRAがない場合: 追加プロンプトのみ（末尾カンマなし）
                lora_text_output = additional_prompt_positive.strip()
        else:
            # 追加プロンプトなし
            if all_text_parts:
                # LoRAのみ
                lora_text_output = "\n".join(all_text_parts)
            else:
                # 何もない
                lora_text_output = ""
        
        # negativeテキスト出力
        # 1. json_sample_promptからのnegative
        sample_negative = ", ".join([n for n in all_negative_parts if n])
        # 2. additional_prompt_negativeと結合
        negative_parts = []
        if additional_prompt_negative.strip():
            negative_parts.append(additional_prompt_negative.strip())
        if sample_negative:
            negative_parts.append(sample_negative)
        negative_text_output = ", ".join(negative_parts)
        
        # positiveプロンプトを結合してCONDITIONINGを生成（追加プロンプトを含める）
        final_positive_parts = []
        if additional_prompt_positive.strip():
            # LoRA構文を削除してクリーンなプロンプトにする
            cleaned_prompt = self._remove_lora_syntax(additional_prompt_positive.strip())
            if cleaned_prompt:  # 削除後に空でなければ追加
                final_positive_parts.append(cleaned_prompt)
        final_positive_parts.extend([p for p in all_positive_parts if p])
        positive_text = ", ".join(final_positive_parts)
        positive_conditioning = self._encode_prompt(
            clip, positive_text, token_normalization, weight_interpretation
        )
        
        # negativeプロンプトを結合してCONDITIONINGを生成
        final_negative_parts = []
        if additional_prompt_negative.strip():
            cleaned_negative = self._remove_lora_syntax(additional_prompt_negative.strip())
            if cleaned_negative:
                final_negative_parts.append(cleaned_negative)
        final_negative_parts.extend([n for n in all_negative_parts if n])
        negative_text = ", ".join(final_negative_parts)
        negative_conditioning = self._encode_prompt(
            clip, negative_text, token_normalization, weight_interpretation
        )
        
        total_loras = len(all_text_parts)
        if total_loras > 0:
            print(f"[RandomLoRALoader] 適用完了: 合計{total_loras}個のLoRA")
        elif additional_prompt_positive.strip():
            print(f"[RandomLoRALoader] 適用完了: LoRAなし、追加プロンプトのみ使用")
        else:
            print(f"[RandomLoRALoader] 適用完了: LoRAなし、プロンプトなし")
        
        # プレビュー画像バッチ生成
        preview_batch = self._generate_preview_batch(preview_images)
        
        # positive_text = positive にエンコードした文字列そのもの（<lora:...> なし）
        return (model, clip, positive_text, negative_text_output, positive_conditioning,
                negative_conditioning, preview_batch, lora_text_output)
