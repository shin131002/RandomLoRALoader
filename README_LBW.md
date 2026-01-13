# Filtered Random LoRA Loader (LBW)

**LoRA Block Weight (LBW) support with automatic SD1.5/SDXL detection**

![FilteredRandomLoRALoader(LBW) Workflow Example](./images/lbw_final_single.webp)

---

## Features

### **Core Features (from Filtered Random LoRA Loader)**
- ✅ Random LoRA selection from a single folder
- ✅ Keyword filtering (AND/OR modes)
- ✅ Metadata search (filename or embedded metadata)
- ✅ Preview images (static/animated/video support)
- ✅ Trigger word extraction
- ✅ Duplicate removal by filename
- ✅ Direct serial connection support

### **Advanced Features (LBW)**
- ✅ **LoRA Block Weight (LBW) support**
- ✅ **Automatic SD1.5/SDXL detection**
- ✅ **4 preset modes + custom input**
- ✅ **Automatic weight adjustment**

---

## LoRA Block Weight (LBW)

### **What is LBW?**

LoRA Block Weight allows you to control which parts of the U-Net model are affected by the LoRA:

- **INPUT blocks**: Structure, composition, layout
- **MIDDLE block**: Overall features
- **OUTPUT blocks**: Style, details, fine-tuning

By adjusting weights for each block, you can precisely control the LoRA's effect.

---

## Weight Modes

### **1. Normal (All 1.0)** - Default
All blocks weighted at 1.0 (standard LoRA application, no LBW).

---

### **2. Style Focused**
Emphasizes OUTPUT blocks only.

**Best for:**
- Style LoRAs
- Art style transfer
- Visual aesthetic changes

**SDXL:** `1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`

**Effect:**
- ✅ Strong style changes
- ❌ Minimal structure/character changes

---

### **3. Character Focused**
Emphasizes INPUT (early) + MIDDLE + OUTPUT blocks.

**Best for:**
- Character LoRAs
- Face/feature preservation
- Balanced application

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`

**Effect:**
- ✅ Strong character features
- ✅ Balanced overall effect

---

### **4. Structure/Composition Only**
Emphasizes INPUT + MIDDLE blocks only.

**Best for:**
- Pose LoRAs
- Composition LoRAs
- Layout/structure control

**SDXL:** `1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`  
**SD1.5:** `1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`

**Effect:**
- ✅ Strong structure/pose changes
- ❌ Minimal style changes

---

### **5. Balanced / Soft**
Soft application across selected blocks.

**Best for:**
- Subtle effects
- Multi-LoRA workflows
- General-purpose LoRAs

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0`  
**SD1.5:** `1,1,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0`

**Effect:**
- ✅ Balanced, gentle application
- ✅ Good for stacking multiple LoRAs

---

### **6. Preset: Random**
Randomly selects one of the 4 presets above.

**Best for:**
- Experimentation
- Variation generation
- Random effects

---

### **7. Direct Input**
Custom weight specification.

**Format:**
- SDXL: 20 comma-separated values
- SD1.5: 17 comma-separated values

**Example (SDXL):**
```
1,0.5,0.5,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.7,0.7,0.7,1,1,1,1,1,1,1
```

**Auto-adjustment:**
- If too few elements: pads with 1.0 at the end
- If too many elements: truncates from the end

---

## Block Structure

### **SDXL (20 elements)**
```
BASE, IN00-IN08 (9), MID (1), OUT00-OUT08 (9)
```

### **SD1.5 (17 elements)**
```
BASE, IN01,IN02,IN04,IN05,IN07,IN08 (6), MID (1), OUT03-OUT11 (9)
```

---

## Automatic Detection

### **LoRA Type Detection**

The node automatically detects whether a LoRA is SD1.5 or SDXL by analyzing the model structure:

- **SD1.5**: `output_blocks_0` to `output_blocks_11` (12 blocks)
- **SDXL**: `output_blocks_0` to `output_blocks_8` (9 blocks)

**You don't need to specify the model type manually!** ✅

---

### **Weight Adjustment**

If the number of weights doesn't match the detected LoRA type:

**Example 1: Too few weights**
```
Input: 1,0,0 (3 elements)
Detected: SDXL (requires 20)
→ Auto-adjusted: 1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
```

**Example 2: Too many weights**
```
Input: 1,0,0,...,0,0,0 (25 elements)
Detected: SDXL (requires 20)
→ Auto-adjusted: 1,0,0,...,0,0,0 (first 20 only)
```

---

## Usage

### **Basic Workflow**

```
[Filtered Random LoRA Loader (LBW)]
  MODEL → [KSampler]
  CLIP → [CLIP Text Encode]
  positive_text → [Show Text] (optional, for debugging)
```

### **Parameters**

#### **LoRA Settings**
- `lora_folder_path`: Path to LoRA folder
- `num_loras`: Number of LoRAs to apply (0-20)
- `model_strength`: LoRA strength for MODEL (e.g., "1.0" or "0.6-0.9")
- `clip_strength`: LoRA strength for CLIP (e.g., "1.0" or "0.6-0.9")

#### **Keyword Filter**
- `keyword_filter`: Space-separated keywords (e.g., `style anime` or `"anime style" red`)
- `filter_mode`: AND / OR
- `search_in_metadata`: Search in JSON/embedded metadata (slower)

#### **LBW Settings** (New!)
- `weight_mode`: Normal / 4 Presets / Random / Direct Input
- `lbw_input`: Custom weights (only for Direct Input mode)

#### **Other**
- `trigger_word_source`: Trigger word extraction method
- `seed`: Random seed

---

## Output Format

### **LBW Syntax**

When LBW is applied, the `positive_text` output includes LBW syntax:

**Normal (All 1.0):**
```
<lora:style_anime:0.8:0.8>
```

**With LBW (Style Focused, SDXL):**
```
<lora:style_anime:0.8:0.8:lbw=1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1>
```

**Note:** The LBW is applied internally to the MODEL. The syntax in `positive_text` is for reference/re-use with other nodes.

---

## Tips

### **1. Preset Selection Guide**

| LoRA Type | Recommended Preset | Why |
|-----------|-------------------|-----|
| Style/Art | Style Focused | OUTPUT blocks control style |
| Character | Character Focused | Balanced IN+MID+OUT for features |
| Pose/Composition | Structure/Composition Only | INPUT blocks control layout |
| General | Balanced / Soft | Gentle, stackable effect |

---

### **2. Effect Visibility**

The difference between presets is **more visible** with:
- ✅ Strong LoRAs (high model_strength)
- ✅ Single LoRA application (num_loras=1)
- ✅ Style or concept LoRAs

The difference is **less visible** with:
- ⚠️ Weak LoRAs (low model_strength)
- ⚠️ Multiple LoRAs applied simultaneously
- ⚠️ LoRAs with evenly distributed training

---

### **3. Zero Weight = No Effect**

Setting all weights to 0 completely disables the LoRA effect:
```
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
```
This is equivalent to not applying the LoRA at all.

---

### **4. Serial Connection**

For applying different LBW settings to different LoRAs:
```
[Filtered Random LoRA Loader (LBW)] (Style Focused)
  ↓
[Filtered Random LoRA Loader (LBW)] (Character Focused)
  ↓
[KSampler]
```

All LoRAs within a single node instance use the same LBW setting.

---

## Requirements

### **⚠️ Supported Models**
**This node is designed for SD1.5 and SDXL models ONLY.**

- ✅ **Supported:** Stable Diffusion 1.5, Stable Diffusion XL (SDXL)
- ❌ **NOT Supported:** Flux, SD3, SDXL Turbo, Pony, or other architectures

The LBW feature specifically targets SD1.5/SDXL U-Net architecture. Other model types will not work correctly.

---

### **Dependencies**
- ComfyUI
- Pillow (included with ComfyUI)
- torch (included with ComfyUI)

### **⚠️ Optional: Video Preview**
**For video preview support (.mp4, .webm, .avi, .mov), opencv-python is REQUIRED:**
```bash
pip install opencv-python
```

**Without opencv-python:**
- ✅ Static/animated images work
- ❌ Video files show black screen

---

## Preview Images

Supports the following formats (in priority order):

1. **Static images** (.png, .jpg, .jpeg)
2. **Animated images** (.gif, .webp) - first frame
3. **Video files** (.mp4, .webm, .avi, .mov) - first frame (requires opencv-python)

The node automatically searches for preview files matching the LoRA filename.

---

## Disclaimer

- No technical support provided
- No warranty or guarantee of functionality
- No guaranteed compatibility with future ComfyUI updates
- Bug reports and feature requests may not be addressed
- Use at your own risk

---

## Changelog

### v1.2.0 (2026-01-13)
- ✅ Added LoRA Block Weight (LBW) support
- ✅ Automatic SD1.5/SDXL detection
- ✅ 4 preset modes + custom input
- ✅ Automatic weight adjustment
- ✅ Video preview support (.mp4, .webm, etc.)

### v1.1.0 (2026-01-04)
- ✅ Added Filtered Random LoRA Loader
- ✅ Keyword filtering with AND/OR modes
- ✅ Metadata search support
- ✅ Preview image display

### v1.0.0 (2025-12-30)
- ✅ Initial release
- ✅ Random LoRA Loader (3 groups)

---

## License

MIT License

---

## Author

Your Name

---

**Enjoy precise LoRA control with Block Weights!** 🎨✨
