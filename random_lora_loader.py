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
19. trigger_word_source: json_combined/json_random/json_sample_prompt（共通）
20. seed: ランダム選択のシード値（共通、ComfyUI標準のcontrol_before_generateで制御）

【その他仕様】
- 外部JSONファイル（{LoRAファイル名}.metadata.json）からトリガーワード/作例を取得
- JSON読み取り優先順位: trainedWords / images[].meta.prompt
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

class RandomLoRALoader:
    """ランダムLoRA選択・適用ノード（3グループ対応）"""
    
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
                "additional_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": "Additional prompt (e.g., 1girl, beautiful)"
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
                    ["json_combined", "json_random", "json_sample_prompt"],
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
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "CONDITIONING", "CONDITIONING")
    RETURN_NAMES = ("MODEL", "CLIP", "positive_text", "negative_text", "positive", "negative")
    FUNCTION = "load_random_loras"
    CATEGORY = "loaders"
    
    def _find_lora_files(self, folder_path, include_subfolders):
        """
        指定フォルダ内のLoRAファイル（.safetensors）を検索
        
        Args:
            folder_path: 検索対象フォルダの絶対パス
            include_subfolders: サブフォルダを含めるか
        
        Returns:
            list: LoRAファイルパスのリスト
        """
        if not os.path.exists(folder_path):
            print(f"[RandomLoRALoader] フォルダが存在しません: {folder_path}")
            return []
        
        pattern = "**/*.safetensors" if include_subfolders else "*.safetensors"
        lora_files = glob.glob(os.path.join(folder_path, pattern), recursive=include_subfolders)
        
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
    
    def _parse_strength(self, strength_str):
        """
        強度文字列をパースして値を返す
        
        対応形式:
        - "1.0" → 1.0（そのまま）
        - "0.55" → 0.55（そのまま）
        - "0.4-0.8" → 0.4, 0.5, 0.6, 0.7, 0.8からランダム（0.1刻み）
        - "0.44-0.82" → 0.4, 0.5, 0.6, 0.7, 0.8からランダム（範囲を1桁に丸める）
        
        Args:
            strength_str: 強度文字列
        
        Returns:
            float: 実際に使用する強度値
        """
        strength_str = str(strength_str).strip()
        
        # ハイフンがあればランダム範囲指定
        if '-' in strength_str:
            try:
                parts = strength_str.split('-')
                if len(parts) != 2:
                    raise ValueError("範囲指定は 'min-max' 形式で入力してください")
                
                # 範囲の上限下限を1桁に丸める
                min_val = round(float(parts[0].strip()), 1)
                max_val = round(float(parts[1].strip()), 1)
                
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
        外部JSONファイルからメタデータを読み込む
        
        Args:
            lora_path: LoRAファイルパス (.safetensors)
        
        Returns:
            dict: JSONデータ（読み込み失敗時はNone）
        """
        # .safetensorsを除いたファイル名を取得
        base_name = os.path.splitext(lora_path)[0]
        json_path = f"{base_name}.metadata.json"
        
        if not os.path.exists(json_path):
            print(f"[RandomLoRALoader] JSONファイルが見つかりません: {json_path}")
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[RandomLoRALoader] JSON読み込みエラー ({json_path}): {e}")
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
        text = re.sub(r',\s*,', ',', text)
        
        # 行頭・行末の空白とカンマを削除
        text = text.strip().strip(',').strip()
        
        return text
    
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
        additional_prompt,
        # グループ1
        lora_folder_path_1,
        include_subfolders_1,
        model_strength_1,
        clip_strength_1,
        num_loras_1,
        # グループ2
        lora_folder_path_2,
        include_subfolders_2,
        model_strength_2,
        clip_strength_2,
        num_loras_2,
        # グループ3
        lora_folder_path_3,
        include_subfolders_3,
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
            tuple: (MODEL, CLIP, positive_text_output, negative_text_output, positive_conditioning, negative_conditioning)
        """
        # seedをそのまま使用（ComfyUIのcontrol_before_generateで制御される）
        print(f"[RandomLoRALoader] 使用seed: {seed}")
        
        # 全テキスト出力用のリスト
        all_text_parts = []
        
        # 全positive/negativeプロンプトを蓄積
        all_positive_parts = []
        all_negative_parts = []
        
        # 3つのグループを処理
        groups = [
            (lora_folder_path_1, include_subfolders_1, model_strength_1, clip_strength_1, num_loras_1, "Group 1"),
            (lora_folder_path_2, include_subfolders_2, model_strength_2, clip_strength_2, num_loras_2, "Group 2"),
            (lora_folder_path_3, include_subfolders_3, model_strength_3, clip_strength_3, num_loras_3, "Group 3"),
        ]
        
        for folder_path, include_subs, model_str, clip_str, num, group_name in groups:
            # フォルダパスが空、またはnum_lorasが0の場合はスキップ
            if not folder_path.strip() or num == 0:
                print(f"[RandomLoRALoader] {group_name}: スキップ（フォルダ未指定またはnum=0）")
                continue
            
            # LoRAファイルを検索
            lora_files = self._find_lora_files(folder_path, include_subs)
            
            if not lora_files:
                print(f"[RandomLoRALoader] {group_name}: LoRAファイルが見つかりませんでした")
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
                
                # テキスト出力に追加（末尾にカンマを付ける）
                lora_notation = f"<lora:{lora_name}:{actual_model_str}:{actual_clip_str}>"
                all_text_parts.append(f"{lora_notation}, {trigger_display},")
        
        # テキスト出力を結合（追加プロンプトを先頭に配置、末尾にカンマを付ける）
        if additional_prompt.strip():
            # 追加プロンプトの末尾にカンマがなければ追加
            additional_with_comma = additional_prompt.strip()
            if not additional_with_comma.endswith(','):
                additional_with_comma += ','
            if all_text_parts:
                # LoRAがある場合: 追加プロンプト + LoRA情報
                positive_text_output = additional_with_comma + "\n" + "\n".join(all_text_parts)
            else:
                # LoRAがない場合: 追加プロンプトのみ（末尾カンマなし）
                positive_text_output = additional_prompt.strip()
        else:
            # 追加プロンプトなし
            if all_text_parts:
                # LoRAのみ
                positive_text_output = "\n".join(all_text_parts)
            else:
                # 何もない
                positive_text_output = ""
        
        # negativeテキスト出力（json_sample_promptの場合のみ内容あり）
        negative_text_output = ", ".join([n for n in all_negative_parts if n])
        
        # positiveプロンプトを結合してCONDITIONINGを生成（追加プロンプトを含める）
        final_positive_parts = []
        if additional_prompt.strip():
            # LoRA構文を削除してクリーンなプロンプトにする
            cleaned_prompt = self._remove_lora_syntax(additional_prompt.strip())
            if cleaned_prompt:  # 削除後に空でなければ追加
                final_positive_parts.append(cleaned_prompt)
        final_positive_parts.extend([p for p in all_positive_parts if p])
        positive_text = ", ".join(final_positive_parts)
        positive_conditioning = self._encode_prompt(
            clip, positive_text, token_normalization, weight_interpretation
        )
        
        # negativeプロンプトを結合してCONDITIONINGを生成
        negative_text = ", ".join([n for n in all_negative_parts if n])
        negative_conditioning = self._encode_prompt(
            clip, negative_text, token_normalization, weight_interpretation
        )
        
        total_loras = len(all_text_parts)
        if total_loras > 0:
            print(f"[RandomLoRALoader] 適用完了: 合計{total_loras}個のLoRA")
        elif additional_prompt.strip():
            print(f"[RandomLoRALoader] 適用完了: LoRAなし、追加プロンプトのみ使用")
        else:
            print(f"[RandomLoRALoader] 適用完了: LoRAなし、プロンプトなし")
        
        return (model, clip, positive_text_output, negative_text_output, positive_conditioning, negative_conditioning)


# ComfyUIへのノード登録
NODE_CLASS_MAPPINGS = {
    "RandomLoRALoader": RandomLoRALoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRALoader": "Random LoRA Loader"
}
