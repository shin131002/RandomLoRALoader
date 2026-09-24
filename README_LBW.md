# Filtered Random LoRA Loader (LBW)

**LoRA Block Weight (LBW) support with automatic SD1.5/SDXL detection**

![FilteredRandomLoRALoader(LBW) Workflow Example](./images/lbw_final_single.webp)

---

## Overview

Filtered Random LoRA Loader (LBW) is the Filtered Random LoRA Loader with LoRA Block Weight (LBW) support added. It lets you control precisely which parts of the U-Net a LoRA is applied to.

---

## Features

### **Core Features (shared with Filtered Random LoRA Loader)**
- ✅ Random LoRA selection from a single folder
- ✅ Keyword filtering (AND/OR modes)
- ✅ Metadata search (filename or embedded metadata)
- ✅ Preview images (static/animated/video support)
- ✅ Trigger word extraction
- ✅ Duplicate removal by filename
- ✅ Direct serial connection support

### **Advanced Features (LBW)**
- ✅ **LoRA Block Weight (LBW) support**: set a separate strength for each U-Net block to control style, character, composition and so on independently
- ✅ **Automatic SD1.5/SDXL detection**
- ✅ **4 preset modes + custom input**
- ✅ **Automatic weight adjustment**

---

## LoRA Block Weight (LBW)

### **What is LBW?**

LoRA Block Weight lets you control which parts of the U-Net the LoRA affects. The Stable Diffusion U-Net is made up of three parts:

```
INPUT blocks  → Structure, composition, layout
   ↓
MIDDLE block  → Overall features
   ↓
OUTPUT blocks → Style, details, fine-tuning
```

By adjusting the weight of each block, you can precisely control the LoRA's effect.

---

## Weight Modes

### **1. Normal (All 1.0)** - Default
All blocks weighted at 1.0 (standard LoRA application, no LBW).

---

### **2. Style Focused**
Enables OUTPUT blocks only.

**SDXL:** `1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`

**Best for:**
- Style LoRAs (anime style, watercolor, etc.)
- Art style and effect LoRAs
- Changing the visual aesthetic

**Effect:**
- ✅ Strong style changes
- ❌ Minimal structure/character changes (ideal when you want to keep the existing composition)

---

### **3. Character Focused**
Enables INPUT (early) + MIDDLE + OUTPUT blocks.

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1`  
**SD1.5:** `1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1`

**Best for:**
- Character and person LoRAs
- Concept LoRAs
- Preserving faces/features

**Effect:**
- ✅ Strong character features
- ✅ Balanced overall effect

---

### **4. Structure/Composition Only**
Enables INPUT + MIDDLE blocks only.

**SDXL:** `1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`  
**SD1.5:** `1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0`

**Best for:**
- Pose LoRAs
- Composition and layout LoRAs

**Effect:**
- ✅ Strong structure/pose changes
- ❌ Minimal style changes

---

### **5. Balanced / Soft**
Soft application across selected blocks. The later OUTPUT blocks are turned down to avoid over-application.

**SDXL:** `1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0`  
**SD1.5:** `1,1,1,1,0,0,0,1,1,1,1,1,0,0,0,0,0`

**Best for:**
- Subtle effects and fine adjustment
- Multi-LoRA workflows
- General-purpose LoRAs

**Effect:**
- ✅ Balanced, gentle application with a natural finish
- ✅ Good for stacking multiple LoRAs

---

### **6. Preset: Random**
Randomly picks one of the 4 presets above on each run.

```
weight_mode: "Preset: Random"
→ One of the 4 presets is picked on each run
```

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
weight_mode: "Direct Input"
lbw_input: "1,0.5,0.5,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.7,0.7,0.7,1,1,1,1,1,1,1"
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

| Index | Block | Role |
|-------|-------|------|
| 0 | BASE | Overall base |
| 1-9 | INPUT (IN00-08) | Structure/composition |
| 10 | MIDDLE (M00) | Intermediate features |
| 11-19 | OUTPUT (OUT00-08) | Style/details |

**Weight example:**
```
1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1
BASE,IN00-08 (OFF),M00,OUT00-08 (ON)
→ LoRA applied to OUTPUT blocks only (style focused)
```

### **SD1.5 (17 elements)**
```
BASE, IN01,IN02,IN04,IN05,IN07,IN08 (6), MID (1), OUT03-OUT11 (9)
```

| Index | Block | Role |
|-------|-------|------|
| 0 | BASE | Overall base |
| 1-6 | INPUT (IN01,02,04,05,07,08) | Structure/composition |
| 7 | MIDDLE (M00) | Intermediate features |
| 8-16 | OUTPUT (OUT03-11) | Style/details |

**Weight example:**
```
1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1
BASE,IN (OFF),M00,OUT (ON)
→ LoRA applied to OUTPUT blocks only (style focused)
```

---

## Automatic Detection

### **LoRA Type Detection**

The node automatically detects whether a LoRA is SD1.5 or SDXL by analyzing the model structure:

- **SD1.5**: `output_blocks_0` to `output_blocks_11` (12 blocks)
- **SDXL**: `output_blocks_0` to `output_blocks_8` (9 blocks)

```
SDXL detected  → 20-element weights are used
SD1.5 detected → 17-element weights are used
```

**You don't need to specify the model type manually!** ✅

---

### **Weight Adjustment**

If the number of weights doesn't match the detected LoRA type, it is adjusted automatically:

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
  lora_text → [Show Text] (optional, for debugging)
```

**Steps:**

1. **Place the node**
   ```
   [Filtered Random LoRA Loader (LBW)]
   ```

2. **Set the folder and keywords**
   ```
   lora_folder_path: "path/to/loras"
   keyword_filter: "anime style"
   num_loras: 1
   ```

3. **Choose the LBW mode**
   ```
   weight_mode: "Style Focused"
   ```

4. **Connect MODEL/CLIP**
   ```
   MODEL → [KSampler]
   CLIP → [CLIP Text Encode]
   ```

### **Parameters**

#### **LoRA Settings**
- `lora_folder_path`: Path to LoRA folder
- `num_loras`: Number of LoRAs to apply (0-20)
- `model_strength`: LoRA strength for MODEL (e.g., "1.0" or "0.6-0.9")
- `clip_strength`: LoRA strength for CLIP (e.g., "1.0" or "0.6-0.9")

> Folder scanning behaviour (supported extensions, symbolic links, sorted candidate order) is shared with the other nodes — see [Folder Scanning](README.md#folder-scanning) in the main README.

#### **Keyword Filter**
- `keyword_filter`: Space-separated keywords (e.g., `style anime` or `"anime style" red`)
- `filter_mode`: AND / OR
- `search_in_metadata`: Search in JSON/embedded metadata (slower)

#### **LBW Settings**
- `weight_mode`: Normal / 4 Presets / Random / Direct Input
- `lbw_input`: Custom weights (only for Direct Input mode)

#### **Other**
- `trigger_word_source`: Trigger word extraction method
- `seed`: Random seed

---

## Output Format

### **LBW Syntax**

When LBW is applied, the `lora_text` output (`positive_text` before v1.4.0) includes LBW syntax:

**Normal (All 1.0):**
```
<lora:style_anime:0.8:0.8>
```

**With LBW (Style Focused, SDXL):**
```
<lora:style_anime:0.8:0.8:lbw=1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1>
```

**Note:** The LBW is applied internally to the MODEL. The syntax in `lora_text` is for reference/re-use with other nodes.

---

## Examples

### **Example 1: Change the style only**

```
[Load Checkpoint] → [Filtered Random LoRA Loader (LBW)]
                     weight_mode: "Style Focused"
                     keyword_filter: "anime"
                     ↓
                     [KSampler]
```

**Result:** The composition stays the same; only the style becomes anime-like

---

### **Example 2: Staged application with multiple LoRAs**

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

**Result:** Pose adjustment → watercolor style applied

---

### **Example 3: Character + style**

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

**Result:** Character features preserved + style changed

---

## Tips

### **1. Preset Selection Guide**

| LoRA Type | Recommended Preset | Why |
|-----------|-------------------|-----|
| Style/Art | Style Focused | OUTPUT blocks control style |
| Character | Character Focused | Balanced IN+MID+OUT preserves features |
| Pose/Composition | Structure/Composition Only | INPUT blocks control layout |
| General/fine adjustment | Balanced / Soft | Gentle, stackable effect |

---

### **2. Effect Visibility**

The difference between presets is **more visible** with:
- ✅ Strong LoRAs (high model_strength)
- ✅ Single LoRA application (num_loras=1)
- ✅ Style or concept LoRAs

The difference is **less visible** with:
- ⚠️ Weak LoRAs (low model_strength)
- ⚠️ Multiple LoRAs applied simultaneously
- ⚠️ LoRAs whose training effect is spread evenly across blocks

---

### **3. Zero Weight = No Effect**

Setting all weights to 0 completely disables the LoRA effect:
```
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
```
This is equivalent to not applying the LoRA at all.

**Weight guide:**
- **0**: Completely off
- **0.5**: Weaker
- **1.0**: Standard
- **1.5 or more**: Stronger (watch for over-application)

---

### **4. Serial Connection**

For applying different LBW settings to different LoRAs, connect nodes in series:
```
[Filtered Random LoRA Loader (LBW)] (Style Focused)
  ↓
[Filtered Random LoRA Loader (LBW)] (Character Focused)
  ↓
[KSampler]
```

All LoRAs within a single node instance use the same LBW setting.

**Tips:**
- **Structure → style** is the basic order
- Strength can also be adjusted per node

---

### **5. Troubleshooting**

**If there is no effect:**
- Check that the weights aren't all 0
- Check that the LoRA is loaded correctly
- Check the console for the LBW application message

**If the effect is too strong:**
- Lower model_strength
- Try the Balanced / Soft preset
- Adjust the weights to 0.5–0.8

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

**File matching:**
- Files that start with the LoRA filename (case-insensitive)
- Example: matches for `style_anime.safetensors`:
  - `style_anime.png` ✅
  - `style_anime_preview.jpg` ✅
  - `STYLE_ANIME.PNG` ✅

---

## Advanced: Custom Presets

To create your own presets or change the existing ones, you can edit the source file directly.

### **How to Edit**

**File location:**
```
ComfyUI/custom_nodes/RandomLoRALoader/filtered_random_lora_loader_lbw.py
```

**Lines to edit:** 29–41 (`SDXL_PRESETS` for SDXL, `SD15_PRESETS` for SD1.5)

### **Example 1: Add your own preset**

```python
SDXL_PRESETS = {
    "Style Focused": "1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "Character Focused": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "Structure/Composition Only": "1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    "Balanced / Soft": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0",
    # ↓ Your own preset
    "My Custom Mix": "0.5,0.5,0.5,0.5,0,0,0,0,0,0,1,0.8,0.8,0.8,0.8,0.8,0.5,0.5,0.5,0.5"
}
```

### **Example 2: Adjust an existing preset**

```python
SDXL_PRESETS = {
    # Make Style Focused stronger
    "Style Focused": "1,0,0,0,0,0,0,0,0,0,0,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.2,1.2",
    
    # Make Character Focused milder
    "Character Focused": "0.8,0.8,0.8,0.8,0,0,0,0,0,0,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8,0.8",
    ...
}
```

### **Example 3: Rename presets**

```python
SDXL_PRESETS = {
    "Style Only": "1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1",
    "Character First": "1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1",
    "Composition Only": "1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0",
    ...
}
```

### **Important Notes**

⚠️ **Before editing:**
- Make a backup of the original file
- Watch the Python syntax (commas, quotes)

⚠️ **Number of weights:**
- SDXL presets: exactly 20 elements
- SD1.5 presets: exactly 17 elements
- Mismatched counts are auto-adjusted, but specifying them exactly is more reliable

⚠️ **After editing:**
- Fully restart ComfyUI to apply the changes
- Check the console for syntax errors

💡 **Tip:** If editing the file is a hassle, use the "Direct Input" mode!

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

konohana

---

**Enjoy precise LoRA control with Block Weights!** 🎨✨
