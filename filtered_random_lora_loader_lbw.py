"""
Filtered Random LoRA Loader (Advanced) Node for ComfyUI
キーワードフィルタ + LoRA Block Weight 対応ランダムLoRA選択・適用ノード

Author: Your Name
Version: 1.2.0
License: MIT

機能:
- 1つのフォルダから複数のLoRAをランダム選択
- キーワードフィルタで絞り込み（AND/OR）
- メタデータ検索（ファイル名 or メタデータ内）
- LoRA Block Weight (LBW) 対応
- SD1.5 / SDXL 対応
- プリセット + カスタム設定
- キャッシュ機能で高速化
- 直列接続推奨
"""

import os
import random
import re
import json
import folder_paths
import comfy.sd


# LBW プリセット定義
SDXL_PRESETS = {
    "Style Focused": "1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "Character Focused": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "Structure/Composition Only": "1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    "Balanced / Soft": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0"
}

SD15_PRESETS = {
    "Style Focused": "1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "Character Focused": "1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "Structure/Composition Only": "1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    "Balanced / Soft": "1,1,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0"
}


class FilteredRandomLoRALoaderLBW:
    """キーワードフィルタ付きランダムLoRA選択・適用ノード（1グループ）"""
    
    # クラス変数（全インスタンスで共有するメタデータキャッシュ）
    _metadata_cache = {}
    _opencv_warning_shown = False  # opencv警告表示フラグ
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                
                # 共通設定
                "token_normalization": (
                    ["none", "mean", "length", "length+mean"],
                    {"default": "none"}
                ),
                "weight_interpretation": (
                    ["comfy", "A1111", "compel", "comfy++", "down_weight"],
                    {"default": "comfy"}
                ),
                
                # 追加プロンプト
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
                
                # フォルダ設定（1つのみ）
                "lora_folder_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Path to LoRA folder"
                }),
                "include_subfolders": ("BOOLEAN", {
                    "default": True,
                    "label": "Include subfolders"
                }),
                "unique_by_filename": ("BOOLEAN", {
                    "default": True,
                    "label": "Unique by filename (exclude duplicates)"
                }),
                
                # キーワードフィルタ設定
                "keyword_filter": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Keywords (space-separated, e.g., 'style anime' or \"anime style\" red)"
                }),
                "filter_mode": (["AND", "OR"], {
                    "default": "AND"
                }),
                "search_in_metadata": ("BOOLEAN", {
                    "default": False,
                    "label": "Search in metadata (slower)"
                }),
                
                # LoRA設定
                "model_strength": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.6-0.9"
                }),
                "clip_strength": ("STRING", {
                    "default": "1.0",
                    "multiline": False,
                    "placeholder": "e.g., 1.0 or 0.6-0.9"
                }),
                "num_loras": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 20,
                    "step": 1
                }),
                
                # LoRA Block Weight (LBW) 設定
                "weight_mode": ([
                    "Normal (All 1.0)",
                    "Style Focused",
                    "Character Focused",
                    "Structure/Composition Only",
                    "Balanced / Soft",
                    "Preset: Random",
                    "Direct Input"
                ], {
                    "default": "Normal (All 1.0)"
                }),
                "lbw_input": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Comma-separated weights (SDXL: 20 elements, SD1.5: 17 elements)"
                }),
                
                # トリガーワード設定
                "trigger_word_source": (
                    ["json_combined", "json_random", "json_sample_prompt", "metadata"],
                    {"default": "json_combined"}
                ),
                
                # seed
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff
                }),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP", "STRING", "STRING", "CONDITIONING", "CONDITIONING", "IMAGE")
    RETURN_NAMES = ("MODEL", "CLIP", "positive_text", "negative_text", "positive", "negative", "preview")
    FUNCTION = "load_loras"
    CATEGORY = "loaders"
    
    def load_loras(self, model, clip, token_normalization, weight_interpretation,
                   additional_prompt_positive, additional_prompt_negative,
                   lora_folder_path, include_subfolders, unique_by_filename,
                   keyword_filter, filter_mode, search_in_metadata,
                   model_strength, clip_strength, num_loras,
                   weight_mode, lbw_input,
                   trigger_word_source, seed):
        """メイン処理"""
        
        # seedの設定
        random.seed(seed)
        
        # LBW ウェイトの取得
        lbw_weights = self._get_lbw_weights(weight_mode, lbw_input)
        
        # 初期値
        final_positive = additional_prompt_positive.strip()
        final_negative = additional_prompt_negative.strip()
        
        # num_loras が 0 の場合はスキップ
        if num_loras == 0:
            print("[FilteredRandomLoRALoaderLBW] num_loras=0, skipping LoRA application")
            empty_preview = self._generate_preview_batch([])
            return self._generate_outputs(model, clip, final_positive, final_negative,
                                         token_normalization, weight_interpretation, empty_preview)
        
        # フォルダパスが空の場合はスキップ
        if not lora_folder_path.strip():
            print("[FilteredRandomLoRALoaderLBW] Warning: lora_folder_path is empty, skipping")
            empty_preview = self._generate_preview_batch([])
            return self._generate_outputs(model, clip, final_positive, final_negative,
                                         token_normalization, weight_interpretation, empty_preview)
        
        # LoRAファイル一覧を取得
        lora_files = self._find_lora_files(lora_folder_path, include_subfolders)
        
        if not lora_files:
            print(f"[FilteredRandomLoRALoaderLBW] Warning: No LoRA files found in {lora_folder_path}")
            empty_preview = self._generate_preview_batch([])
            return self._generate_outputs(model, clip, final_positive, final_negative,
                                         token_normalization, weight_interpretation, empty_preview)
        
        # キーワードフィルタリング
        filtered_files = self._filter_lora_files(
            lora_files, keyword_filter, filter_mode, search_in_metadata
        )
        
        if not filtered_files:
            print(f"[FilteredRandomLoRALoaderLBW] Warning: No LoRAs found matching filter '{keyword_filter}'")
            empty_preview = self._generate_preview_batch([])
            return self._generate_outputs(model, clip, final_positive, final_negative,
                                         token_normalization, weight_interpretation, empty_preview)
        
        # ファイル名でユニーク化（重複ファイル名を除外）
        if unique_by_filename:
            filtered_files = self._unique_by_filename(filtered_files)
            if not filtered_files:
                print(f"[FilteredRandomLoRALoaderLBW] Warning: No LoRAs after deduplication")
                empty_preview = self._generate_preview_batch([])
                return self._generate_outputs(model, clip, final_positive, final_negative,
                                             token_normalization, weight_interpretation, empty_preview)
        
        # ランダム選択（重複なし、不足時は重複で埋める）
        available_count = len(filtered_files)
        
        if num_loras <= available_count:
            # 十分な数がある場合は重複なしで選択
            selected_loras = random.sample(filtered_files, num_loras)
        else:
            # 不足する場合は全て選択後、再選択で埋める
            selected_loras = filtered_files.copy()
            remaining = num_loras - available_count
            
            print(f"[FilteredRandomLoRALoaderLBW] Warning: Requested {num_loras} LoRAs but only {available_count} available. Adding {remaining} duplicates.")
            
            # 不足分をランダムに追加（重複あり）
            for _ in range(remaining):
                selected_loras.append(random.choice(filtered_files))
            
            # 最終的にシャッフル
            random.shuffle(selected_loras)
        
        # LoRA適用
        lora_info_parts = []
        sample_negative_parts = []  # json_sample_prompt用のnegative収集
        preview_images = []  # プレビュー画像収集
        
        for lora_path in selected_loras:
            # 強度を取得
            model_str = self._get_random_strength(model_strength)
            clip_str = self._get_random_strength(clip_strength)
            
            # LoRA適用（LBW対応）
            model, clip = self._apply_lora(model, clip, lora_path, model_str, clip_str, lbw_weights)
            
            # LoRA情報を記録（LBW対応）
            lora_name = os.path.splitext(os.path.basename(lora_path))[0]
            if lbw_weights:
                # LBW形式: <lora:name:model:clip:lbw=weights>
                lora_notation = f"<lora:{lora_name}:{model_str}:{clip_str}:lbw={lbw_weights}>"
            else:
                # 通常形式: <lora:name:model:clip>
                lora_notation = f"<lora:{lora_name}:{model_str}:{clip_str}>"
            
            # トリガーワード取得
            if trigger_word_source == "json_sample_prompt":
                # 作例プロンプト取得（positive/negative両方）
                sample_positive, sample_negative = self._get_sample_prompt_from_json(lora_path)
                trigger_words = sample_positive
                if sample_negative:
                    sample_negative_parts.append(sample_negative)
            else:
                trigger_words = self._get_trigger_words(lora_path, trigger_word_source)
            
            # 結合
            if trigger_words:
                lora_info_parts.append(f"{lora_notation}, {trigger_words}")
            else:
                lora_info_parts.append(lora_notation)
            
            # プレビュー画像を読み込み
            preview = self._load_preview_image_as_tensor(lora_path)
            if preview is not None:
                preview_images.append(preview)
        
        # 最終プロンプト生成
        lora_info = ", ".join(lora_info_parts)
        
        # positive_text
        parts_positive = []
        if final_positive:
            parts_positive.append(final_positive)
        parts_positive.append(lora_info)
        final_positive = ", ".join(parts_positive)
        
        # negative_text
        # 1. additional_prompt_negative
        # 2. json_sample_promptからのnegative
        if sample_negative_parts:
            sample_negative_combined = ", ".join(sample_negative_parts)
            if final_negative:
                final_negative = f"{final_negative}, {sample_negative_combined}"
            else:
                final_negative = sample_negative_combined
        
        # プレビュー画像バッチ生成
        preview_batch = self._generate_preview_batch(preview_images)
        
        return self._generate_outputs(model, clip, final_positive, final_negative,
                                     token_normalization, weight_interpretation, preview_batch)
    
    def _find_lora_files(self, folder_path, include_subfolders):
        """フォルダ内のLoRAファイルを検索"""
        if not os.path.exists(folder_path):
            print(f"[FilteredRandomLoRALoaderLBW] Error: Folder not found: {folder_path}")
            return []
        
        lora_files = []
        extensions = ['.safetensors', '.pt', '.ckpt']
        
        if include_subfolders:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        lora_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in extensions):
                    lora_files.append(file_path)
        
        return lora_files
    
    def _parse_keywords(self, keyword_filter):
        """
        キーワードをパース（スペース区切り、"..."でフレーズ対応）
        
        例:
          "anime style" → ["anime", "style"]
          "anime style" red → ["anime style", "red"]
          "anime style" "vibrant colors" → ["anime style", "vibrant colors"]
        """
        if not keyword_filter.strip():
            return []
        
        import re
        
        # ダブルクォート内のフレーズを抽出
        pattern = r'"([^"]+)"|(\S+)'
        matches = re.findall(pattern, keyword_filter)
        
        # (quoted, unquoted) のタプルから値を取得
        keywords = [m[0] if m[0] else m[1] for m in matches]
        
        # 小文字化
        keywords = [kw.lower() for kw in keywords if kw]
        
        return keywords
    
    def _unique_by_filename(self, lora_files):
        """
        ファイル名でユニーク化（重複ファイル名を除外）
        
        Args:
            lora_files: LoRAファイルパスのリスト
        
        Returns:
            list: ファイル名がユニークなファイルパスのリスト
        
        例:
            ["/path/style/anime.safetensors", "/path/backup/anime.safetensors"]
            → ["/path/style/anime.safetensors"]  # 最初に見つかったものを保持
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
                print(f"[FilteredRandomLoRALoaderLBW] Duplicate filename detected: {filename}")
                print(f"  Keeping: {seen_names[filename]}")
                print(f"  Skipping: {file_path}")
        
        return unique_files
    
    def _filter_lora_files(self, lora_files, keyword_filter, filter_mode="OR", search_in_metadata=False):
        """キーワードでLoRAファイルをフィルタリング"""
        if not keyword_filter.strip():
            return lora_files  # フィルタなし = 全ファイル
        
        # キーワードをパース（スペース区切り、"..."でフレーズ対応）
        keywords = self._parse_keywords(keyword_filter)
        if not keywords:
            return lora_files
        
        # メタデータ検索が無効な場合（デフォルト）
        if not search_in_metadata:
            # ファイル名のみ検索（超高速）
            filtered = []
            for lora_path in lora_files:
                filename = os.path.splitext(os.path.basename(lora_path))[0].lower()
                if filter_mode == "AND":
                    if all(kw in filename for kw in keywords):
                        filtered.append(lora_path)
                else:
                    if any(kw in filename for kw in keywords):
                        filtered.append(lora_path)
            return filtered
        
        # メタデータ検索が有効な場合（初回は遅い）
        total = len(lora_files)
        filtered = []
        
        print(f"[FilteredRandomLoRALoaderLBW] Building metadata cache for {total} files...")
        
        for i, lora_path in enumerate(lora_files):
            # 進捗表示（100個ごと）
            if i > 0 and i % 100 == 0:
                print(f"[FilteredRandomLoRALoaderLBW] Progress: {i}/{total} ({int(i/total*100)}%)")
            
            filename = os.path.splitext(os.path.basename(lora_path))[0].lower()
            search_target = filename
            
            # メタデータからキーワード取得（キャッシュ利用）
            metadata_keywords = self._get_metadata_keywords(lora_path)
            if metadata_keywords:
                search_target = f"{filename} {metadata_keywords}"
            
            # フィルタリング
            if filter_mode == "AND":
                if all(kw in search_target for kw in keywords):
                    filtered.append(lora_path)
            else:
                if any(kw in search_target for kw in keywords):
                    filtered.append(lora_path)
        
        print(f"[FilteredRandomLoRALoaderLBW] Cache built. Filtered {len(filtered)}/{total} files.")
        
        return filtered
    
    def _get_metadata_keywords(self, lora_path):
        """
        メタデータからキーワードを取得（キャッシュ付き）
        
        検索対象:
          1. model_name（トップレベル）
          2. civitai.name
          3. civitai.trainedWords（全パターンを結合、重複除去）
          4. civitai.model.name
          5. civitai.model.tags
          6. tags（トップレベル）
          7. 埋め込みメタデータ（ss_tag_frequency等）
        
        Returns:
            str: 検索用キーワード文字列（小文字、スペース区切り）
        """
        # キャッシュ確認
        if lora_path in self._metadata_cache:
            return self._metadata_cache[lora_path]
        
        # メタデータ読み込み
        metadata = self._load_json_metadata(lora_path)
        keywords_parts = []
        
        if metadata:
            # 1. トップレベルのmodel_name
            model_name = metadata.get("model_name", "")
            if model_name:
                keywords_parts.append(model_name)
            
            # civitaiセクション
            civitai = metadata.get("civitai", {})
            
            # 2. civitai.name
            civitai_name = civitai.get("name", "")
            if civitai_name:
                keywords_parts.append(civitai_name)
            
            # 3. civitai.trainedWords
            trained_words = civitai.get("trainedWords", [])
            if trained_words:
                all_words = []
                for pattern in trained_words:
                    # カンマ区切りで分割
                    words = [w.strip() for w in pattern.split(',')]
                    all_words.extend(words)
                # 重複除去（順序維持）
                unique_words = list(dict.fromkeys(all_words))
                keywords_parts.extend(unique_words)
            
            # civitai.modelセクション
            model_info = civitai.get("model", {})
            
            # 4. civitai.model.name
            model_info_name = model_info.get("name", "")
            if model_info_name:
                keywords_parts.append(model_info_name)
            
            # 5. civitai.model.tags
            model_tags = model_info.get("tags", [])
            if model_tags:
                keywords_parts.extend(model_tags)
            
            # 6. トップレベルのtags（通常は5と同じ内容だが念のため）
            top_tags = metadata.get("tags", [])
            if top_tags:
                keywords_parts.extend(top_tags)
        
        # 重複除去（順序維持）
        unique_keywords = list(dict.fromkeys(keywords_parts))
        
        # 小文字化してスペース区切りで結合
        keywords = " ".join(unique_keywords).lower()
        
        # キャッシュに保存
        self._metadata_cache[lora_path] = keywords
        
        return keywords
    
    def _load_json_metadata(self, lora_path):
        """
        メタデータファイルまたは埋め込みメタデータを読み込み
        
        優先順位:
          1. .metadata.json（ComfyUI Lora Manager）
          2. .info（Civitai Helper）
          3. 埋め込みメタデータ
        """
        base_path = os.path.splitext(lora_path)[0]
        
        # 1. .metadata.json
        metadata_json_path = f"{base_path}.metadata.json"
        if os.path.exists(metadata_json_path):
            try:
                with open(metadata_json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[FilteredRandomLoRALoaderLBW] Warning: Failed to load {metadata_json_path}: {e}")
        
        # 2. .info
        info_path = f"{base_path}.info"
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[FilteredRandomLoRALoaderLBW] Warning: Failed to load {info_path}: {e}")
        
        # 3. 埋め込みメタデータ
        embedded = self._load_embedded_metadata(lora_path)
        if embedded:
            return embedded
        
        return None
    
    def _load_embedded_metadata(self, lora_path):
        """LoRAファイルから埋め込みメタデータを読み込み（Civitai形式に変換）"""
        try:
            from safetensors.torch import safe_open
            
            with safe_open(lora_path, framework="pt") as f:
                metadata = f.metadata()
                
                if not metadata:
                    return None
                
                # Civitai形式に変換
                civitai_format = {"civitai": {}}
                
                # ss_tag_frequency からトリガーワード抽出
                if "ss_tag_frequency" in metadata:
                    try:
                        tag_freq_str = metadata.get("ss_tag_frequency", "{}")
                        tag_freq = json.loads(tag_freq_str)
                        
                        all_tags = []
                        for dataset_name, tags_dict in tag_freq.items():
                            sorted_tags = sorted(tags_dict.items(), key=lambda x: x[1], reverse=True)
                            top_tags = [tag for tag, freq in sorted_tags[:20]]
                            all_tags.extend(top_tags)
                        
                        if all_tags:
                            unique_tags = list(dict.fromkeys(all_tags))
                            civitai_format["civitai"]["trainedWords"] = [", ".join(unique_tags)]
                    except:
                        pass
                
                # modelspec.trigger_word
                if "modelspec.trigger_word" in metadata:
                    trigger_word = metadata.get("modelspec.trigger_word", "")
                    if trigger_word and "trainedWords" not in civitai_format["civitai"]:
                        civitai_format["civitai"]["trainedWords"] = [trigger_word]
                
                # ss_output_name
                if "ss_output_name" in metadata:
                    model_name = metadata.get("ss_output_name", "")
                    if model_name:
                        civitai_format["model_name"] = model_name
                
                return civitai_format if civitai_format["civitai"] else None
                
        except Exception as e:
            return None
    
    def _get_trigger_words(self, lora_path, trigger_word_source):
        """トリガーワードを取得"""
        if trigger_word_source == "metadata":
            # 埋め込みメタデータのみ参照
            return self._get_trigger_words_from_embedded(lora_path)
        elif trigger_word_source == "json_sample_prompt":
            # 作例プロンプト取得
            sample_positive, sample_negative = self._get_sample_prompt_from_json(lora_path)
            return sample_positive
        elif trigger_word_source == "json_random":
            # ランダム選択
            return self._get_trigger_words_random(lora_path)
        else:  # json_combined
            # 全結合
            return self._get_trigger_words_combined(lora_path)
    
    def _get_trigger_words_combined(self, lora_path):
        """全トリガーワードを結合"""
        metadata = self._load_json_metadata(lora_path)
        if not metadata:
            return ""
        
        trained_words = metadata.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            return ""
        
        all_words = []
        for pattern in trained_words:
            # LoRA構文を削除してから分割
            pattern = self._remove_lora_syntax(pattern)
            words = [w.strip() for w in pattern.split(',')]
            all_words.extend(words)
        
        unique_words = list(dict.fromkeys(all_words))
        return ", ".join(unique_words)
    
    def _get_trigger_words_random(self, lora_path):
        """トリガーワードからランダムに1つ選択"""
        metadata = self._load_json_metadata(lora_path)
        if not metadata:
            return ""
        
        trained_words = metadata.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            return ""
        
        # LoRA構文を削除
        selected = random.choice(trained_words)
        return self._remove_lora_syntax(selected)
    
    def _get_sample_prompt_from_json(self, lora_path):
        """作例プロンプトをランダムに取得"""
        metadata = self._load_json_metadata(lora_path)
        if not metadata:
            return "", ""
        
        images = metadata.get("civitai", {}).get("images", [])
        if not images:
            return "", ""
        
        valid_images = [img for img in images if "meta" in img and img["meta"]]
        if not valid_images:
            return "", ""
        
        selected_image = random.choice(valid_images)
        meta = selected_image["meta"]
        
        positive = meta.get("prompt", "")
        negative = meta.get("negativePrompt", "")
        
        # LoRA構文削除（両方）
        positive = self._remove_lora_syntax(positive)
        negative = self._remove_lora_syntax(negative)
        
        return positive, negative
    
    def _get_trigger_words_from_embedded(self, lora_path):
        """埋め込みメタデータから直接トリガーワード取得"""
        embedded = self._load_embedded_metadata(lora_path)
        if not embedded:
            return ""
        
        trained_words = embedded.get("civitai", {}).get("trainedWords", [])
        if not trained_words:
            return ""
        
        return trained_words[0] if trained_words else ""
    
    def _remove_lora_syntax(self, text):
        """プロンプトからLoRA構文を削除"""
        pattern = r'<lora:[^>]+>'
        return re.sub(pattern, '', text)
    
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
            print("[FilteredRandomLoRALoaderLBW] PIL/torch not available for preview")
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
            print(f"[FilteredRandomLoRALoaderLBW] Folder read error: {e}")
        
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
            print(f"[FilteredRandomLoRALoaderLBW] Static image load error ({image_path}): {e}")
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
            print(f"[FilteredRandomLoRALoaderLBW] Animated image load error ({image_path}): {e}")
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
            if not FilteredRandomLoRALoader._opencv_warning_shown:
                print("=" * 60)
                print("[FilteredRandomLoRALoaderLBW] Video Preview Support")
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
                FilteredRandomLoRALoader._opencv_warning_shown = True
            return None
        except Exception as e:
            print(f"[FilteredRandomLoRALoaderLBW] Video load error ({video_path}): {e}")
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
            print(f"[FilteredRandomLoRALoaderLBW] Image resize/convert error: {e}")
            return None
    
    def _get_lbw_weights(self, weight_mode, lbw_input):
        """
        LBW ウェイトを取得（型は自動検出されるため、ここではプリセットのみ処理）
        
        Returns:
            str: カンマ区切りのウェイト文字列、または None (Normal mode)
        """
        # Normal (All 1.0) の場合は None を返す（LBW構文なし）
        if weight_mode == "Normal (All 1.0)":
            return None
        
        # Preset: Random の場合
        if weight_mode == "Preset: Random":
            presets = ["Style Focused", "Character Focused", 
                      "Structure/Composition Only", "Balanced / Soft"]
            weight_mode = random.choice(presets)
            print(f"[FilteredRandomLoRALoaderLBW] Random preset selected: {weight_mode}")
        
        # Direct Input の場合
        if weight_mode == "Direct Input":
            weights = lbw_input.strip()
            
            # 空欄の場合はNone（Normal All 1.0として扱う）
            if not weights:
                print(f"[FilteredRandomLoRALoaderLBW] Direct Input is empty, using Normal (All 1.0)")
                return None
            
            # 数値チェックのみ（要素数チェックは _apply_lora で自動調整）
            try:
                weight_list = [w.strip() for w in weights.split(',')]
                for w in weight_list:
                    float(w)
                return weights
            except ValueError:
                print(f"[FilteredRandomLoRALoaderLBW] Error: Invalid number in LBW input")
                print(f"[FilteredRandomLoRALoaderLBW] Using default (All 1.0)")
                return None
        
        # プリセットの場合（SDXLプリセットを使用、_apply_loraで自動調整）
        if weight_mode in SDXL_PRESETS:
            return SDXL_PRESETS[weight_mode]
        else:
            print(f"[FilteredRandomLoRALoaderLBW] Unknown weight_mode: {weight_mode}")
            return None
    
    def _get_random_strength(self, strength_str):
        """強度をランダム取得（範囲指定は0.1刻み、固定値は小数点2桁）"""
        import re
        strength_str = strength_str.strip()
        
        # 範囲指定のパターンマッチ
        range_pattern = r'^(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*)$'
        match = re.match(range_pattern, strength_str)
        
        if match:
            try:
                # 範囲の上限下限を1桁に丸める
                min_val = round(float(match.group(1)), 1)
                max_val = round(float(match.group(2)), 1)
                
                # 0.1刻みの値のリストを生成
                values = []
                current = min_val
                while current <= max_val + 0.01:  # 浮動小数点誤差対策
                    values.append(round(current, 1))
                    current += 0.1
                
                if not values:
                    return "1.0"
                
                # ランダムに1つ選択
                selected = random.choice(values)
                return str(selected)
            except:
                return "1.0"
        else:
            # 単一値（小数点2桁に丸める）
            try:
                value = float(strength_str)
                return str(round(value, 2))
            except:
                return "1.0"
    
    def _apply_lora(self, model, clip, lora_path, model_strength, clip_strength, lbw_weights=None):
        """LoRAを適用（LBW対応）"""
        try:
            model_strength_f = float(model_strength)
            clip_strength_f = float(clip_strength)
            
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            
            # LBWが指定されている場合
            if lbw_weights:
                # LoRAファイルからSD1.5/SDXLを自動検出
                detected_type = self._detect_lora_type(lora)
                
                # ウェイトリストに変換
                weights_list = [float(w.strip()) for w in lbw_weights.split(',')]
                
                # 要素数チェック（検出された型に基づく）
                expected_count = 20 if detected_type == "SDXL" else 17
                if len(weights_list) != expected_count:
                    print(f"[FilteredRandomLoRALoaderLBW] Warning: LoRA is {detected_type} but got {len(weights_list)} weights (expected {expected_count})")
                    print(f"[FilteredRandomLoRALoaderLBW] Adjusting weights to match LoRA type...")
                    
                    # ウェイトを調整
                    if len(weights_list) < expected_count:
                        # 足りない場合は1.0で埋める
                        weights_list.extend([1.0] * (expected_count - len(weights_list)))
                    else:
                        # 多い場合は切り詰める
                        weights_list = weights_list[:expected_count]
                
                # LoRAのキーを解析してブロックウェイトを適用
                lora_with_weights = self._apply_block_weights(lora, weights_list, model_strength_f)
                
                # MODEL/CLIPに適用
                model_lora, clip_lora = comfy.sd.load_lora_for_models(
                    model, clip, lora_with_weights, 1.0, clip_strength_f
                )
            else:
                # 通常適用
                model_lora, clip_lora = comfy.sd.load_lora_for_models(
                    model, clip, lora, model_strength_f, clip_strength_f
                )
            
            return model_lora, clip_lora
        except Exception as e:
            print(f"[FilteredRandomLoRALoaderLBW] Warning: Failed to apply LoRA {lora_path}: {e}")
            import traceback
            traceback.print_exc()
            return model, clip
    
    def _detect_lora_type(self, lora_dict):
        """
        LoRAファイルからSD1.5/SDXLを自動検出
        
        Args:
            lora_dict: LoRAの辞書
        
        Returns:
            "SDXL" or "SD1.5"
        """
        # input_blocksの最大番号を確認
        max_input_block = -1
        for key in lora_dict.keys():
            if "input_blocks" in key:
                import re
                match = re.search(r'input_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    max_input_block = max(max_input_block, block_num)
        
        # SD1.5: input_blocks_0~8 (9個)
        # SDXL: input_blocks_0~8 (9個) ← 同じ！
        
        # output_blocksの最大番号を確認
        max_output_block = -1
        for key in lora_dict.keys():
            if "output_blocks" in key:
                import re
                match = re.search(r'output_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    max_output_block = max(max_output_block, block_num)
        
        # SD1.5: output_blocks_0~11 (12個)
        # SDXL: output_blocks_0~8 (9個)
        
        if max_output_block >= 9:
            # output_blocks が 9以上 → SD1.5
            return "SD1.5"
        else:
            # output_blocks が 8以下 → SDXL
            return "SDXL"
    
    def _apply_block_weights(self, lora_dict, weights_list, base_strength):
        """
        LoRAのテンソルにブロックウェイトを適用
        
        Args:
            lora_dict: LoRAの辞書
            weights_list: ウェイトのリスト（SD1.5: 17, SDXL: 20）
            base_strength: ベース強度
        
        Returns:
            ウェイト適用済みのLoRA辞書
        """
        # ブロック名のマッピング（SD1.5/SDXL共通のパターン）
        # キー名の例:
        # "lora_unet_input_blocks_0_0.weight" → INブロック
        # "lora_unet_middle_block_0.weight" → MIDブロック
        # "lora_unet_output_blocks_0_0.weight" → OUTブロック
        
        weighted_lora = {}
        
        for key, value in lora_dict.items():
            weight_multiplier = base_strength
            
            # UNetのLoRAキーのみ処理
            if "lora_unet" in key:
                block_index = self._get_block_index(key, len(weights_list))
                if block_index is not None and block_index < len(weights_list):
                    weight_multiplier = base_strength * weights_list[block_index]
            
            # ウェイトを適用
            weighted_lora[key] = value * weight_multiplier
        
        return weighted_lora
    
    def _get_block_index(self, key, num_weights):
        """
        LoRAキー名からブロックインデックスを取得
        
        Args:
            key: LoRAのキー名
            num_weights: ウェイト数（17 or 20）
        
        Returns:
            ブロックインデックス（0から始まる）
        """
        # BASE（常に0番目）
        if "time_embed" in key or "label_emb" in key:
            return 0
        
        # SD1.5の場合（17要素）
        if num_weights == 17:
            # INPUT blocks (IN01, IN02, IN04, IN05, IN07, IN08)
            if "input_blocks" in key:
                # input_blocks_X_... の X を抽出
                import re
                match = re.search(r'input_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    # SD1.5のINブロックマッピング
                    # IN01=1, IN02=2, IN04=3, IN05=4, IN07=5, IN08=6
                    in_mapping = {1: 1, 2: 2, 4: 3, 5: 4, 7: 5, 8: 6}
                    if block_num in in_mapping:
                        return in_mapping[block_num]
            
            # MIDDLE block (M00 = index 7)
            elif "middle_block" in key:
                return 7
            
            # OUTPUT blocks (OUT03-OUT11 = index 8-16)
            elif "output_blocks" in key:
                import re
                match = re.search(r'output_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    # OUT03-OUT11 → index 8-16
                    if block_num >= 3 and block_num <= 11:
                        return 8 + (block_num - 3)
        
        # SDXLの場合（20要素）
        elif num_weights == 20:
            # INPUT blocks (IN00-IN08 = index 1-9)
            if "input_blocks" in key:
                import re
                match = re.search(r'input_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    if block_num <= 8:
                        return 1 + block_num
            
            # MIDDLE block (M00 = index 10)
            elif "middle_block" in key:
                return 10
            
            # OUTPUT blocks (OUT00-OUT08 = index 11-19)
            elif "output_blocks" in key:
                import re
                match = re.search(r'output_blocks_(\d+)', key)
                if match:
                    block_num = int(match.group(1))
                    if block_num <= 8:
                        return 11 + block_num
        
        # デフォルト: BASEとして扱う
        return 0
    
    
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
    
    def _generate_outputs(self, model, clip, final_positive, final_negative,
                         token_normalization, weight_interpretation, preview_batch):
        """CONDITIONING生成と出力"""
        try:
            from nodes import CLIPTextEncode
            
            # LoRA構文を削除してクリーンなプロンプトにする
            clean_positive = self._remove_lora_syntax(final_positive) if final_positive else ""
            clean_negative = self._remove_lora_syntax(final_negative) if final_negative else ""
            
            # CONDITIONING生成
            positive_conditioning = CLIPTextEncode().encode(
                clip=clip,
                text=clean_positive
            )[0]
            
            negative_conditioning = CLIPTextEncode().encode(
                clip=clip,
                text=clean_negative
            )[0]
            
            return (model, clip, final_positive, final_negative, 
                   positive_conditioning, negative_conditioning, preview_batch)
        except Exception as e:
            print(f"[FilteredRandomLoRALoaderLBW] Error generating outputs: {e}")
            # エラー時は黒画像
            try:
                import torch
                black_image = torch.zeros((1, 1240, 1240, 3), dtype=torch.float32)
            except:
                black_image = None
            return (model, clip, final_positive, final_negative, None, None, black_image)
