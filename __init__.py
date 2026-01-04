"""
RandomLoRALoader Custom Node for ComfyUI
ランダムLoRA選択・適用ノード
"""

from .random_lora_loader import RandomLoRALoader
from .filtered_random_lora_loader import FilteredRandomLoRALoader

NODE_CLASS_MAPPINGS = {
    "RandomLoRALoader": RandomLoRALoader,
    "FilteredRandomLoRALoader": FilteredRandomLoRALoader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RandomLoRALoader": "Random LoRA Loader",
    "FilteredRandomLoRALoader": "Filtered Random LoRA Loader"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
