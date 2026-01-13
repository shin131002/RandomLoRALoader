"""
RandomLoRALoader Custom Node for ComfyUI
ランダムLoRA選択・適用ノード
"""

from .random_lora_loader import RandomLoRALoader
from .filtered_random_lora_loader import FilteredRandomLoRALoader

# LBW版は任意（読み込めない場合はスキップ）
try:
    from .filtered_random_lora_loader_lbw import FilteredRandomLoRALoaderLBW
    HAS_LBW = True
except Exception as e:
    print(f"[RandomLoRALoader] Failed to load LBW version: {e}")
    HAS_LBW = False

NODE_CLASS_MAPPINGS = {
    "RandomLoRALoader": RandomLoRALoader,
    "FilteredRandomLoRALoader": FilteredRandomLoRALoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRALoader": "Random LoRA Loader",
    "FilteredRandomLoRALoader": "Filtered Random LoRA Loader",
}

# LBW版が利用可能な場合のみ追加
if HAS_LBW:
    NODE_CLASS_MAPPINGS["FilteredRandomLoRALoaderLBW"] = FilteredRandomLoRALoaderLBW
    NODE_DISPLAY_NAME_MAPPINGS["FilteredRandomLoRALoaderLBW"] = "Filtered Random LoRA Loader (LBW)"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
