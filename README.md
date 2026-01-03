# Random LoRA Loader for ComfyUI

**English | [日本語版 README](./README_ja.md)**

A ComfyUI custom node for randomly selecting and applying LoRAs from multiple folders. You can combine different types of LoRAs (styles, characters, concepts, etc.) from separate folders.

![Workflow Example](./images/workflow.webp)

## Key Features

- **3-Group Support**: Select LoRAs from up to 3 different folders
- **Multi-Source Metadata Reading**: Automatically retrieve trigger words and sample prompts with priority order:
  1. `.metadata.json` format (ComfyUI Lora Manager) - Priority 1
  2. `.info` format (Civitai Helper) - Priority 2
  3. **Embedded metadata in LoRA file** - Priority 3 (NEW)
- **Strength Randomization**: Randomize strength with range specification (e.g., `0.4-0.8`)
- **Flexible Trigger Word Retrieval**:
  - `json_combined`: Combine all trigger word patterns (with deduplication)
  - `json_random`: Randomly select one pattern
  - `json_sample_prompt`: Randomly retrieve sample prompts
  - **`metadata`**: Read directly from embedded metadata (NEW)
- **Sample Prompt Optimization**: Automatically remove LoRA syntax from samples and apply node-configured strength
- **Dual Text Outputs**: Separate positive_text and negative_text outputs
- **ComfyUI Standard Seed Control**: Supports fixed/randomize/increment/decrement
- **Wildcard Encode Integration**: Works seamlessly with Wildcard Encode (Inspire)
- **LoRA Syntax Auto-Removal**: Cleans up LoRA syntax in additional_prompt to prevent noise

## Installation

### Requirements

- ComfyUI (works with standard installation)
- **No additional libraries required** ✅

### Steps

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/shin131002/RandomLoRALoader.git
# Or manually create RandomLoRALoader folder and copy files
```

Restart ComfyUI.

**Note:** Uses only Python standard library and ComfyUI bundled libraries, so no `pip install` needed.

### Uninstallation

```bash
# Navigate to custom_nodes folder
cd ComfyUI/custom_nodes

# Remove RandomLoRALoader folder
rm -rf RandomLoRALoader

# On Windows
rmdir /s RandomLoRALoader
```

Or manually delete the RandomLoRALoader folder and restart ComfyUI.

## Usage

### Basic Usage

1. **Add Node**: Search for "Random LoRA Loader" in the node browser
2. **Connect MODEL/CLIP**: Connect base model and CLIP to inputs
3. **Set Folder Paths**: 
   - Group 1: Style LoRA folder path
   - Group 2: Character LoRA folder path (optional)
   - Group 3: Concept LoRA folder path (optional)
4. **Configure Each Group**:
   - `num_loras`: Number of LoRAs to select from each group
   - `model_strength` / `clip_strength`: Application strength (fixed value or random range)
5. **Connect Outputs**:
   - `MODEL` / `CLIP`: Connect to KSampler
   - `positive` / `negative`: Connect to Set Conditioning or KSampler
   - `positive_text` / `negative_text`: Connect to Show Text for verification (recommended)

### Wildcard Encode Integration (Recommended)

This node works seamlessly with Wildcard Encode (Inspire) for dynamic prompt generation combined with random LoRA selection.

![Wildcard Encode Workflow](./images/wildcard_workflow.webp)

#### Recommended Connection

```
[Wildcard Encode (Inspire)]
  text: "__style__, {red|blue|green}, <lora:base_effect:0.5>"
  ↓
  ├─ populated_text ──→ [Random LoRA Loader]
  │                     additional_prompt
  └─ MODEL/CLIP ──────→ model/clip input
  
[Random LoRA Loader]
  Folder 1: character LoRAs
  Folder 2: concept LoRAs
  ↓
  MODEL/CLIP/CONDITIONING → [KSampler]
```

#### How It Works

1. **Wildcard Encode Processing**:
   - Wildcard expansion: `__style__` → "anime style"
   - Choice expansion: `{red|blue|green}` → "blue"
   - LoRA syntax processing: `<lora:base_effect:0.5>` → applied to MODEL
   - Result: `populated_text` = "anime style, blue, <lora:base_effect:0.5>"

2. **Random LoRA Loader Processing**:
   - **Auto-removes LoRA syntax** from `populated_text`: "anime style, blue"
   - Random LoRA selection: character_alice, concept_magic
   - Final prompt: "anime style, blue, alice, blonde hair, magic circle"
   - MODEL/CLIP: base_effect + character_alice + concept_magic (all applied)

#### Benefits

- ✅ Delegate wildcard functionality to Wildcard Encode (specialized tool)
- ✅ Delegate random LoRA selection to this node (simple configuration)
- ✅ Prompt information fully inherited
- ✅ LoRA syntax automatically cleaned (no noise)

### 3-Group Example

```
Group 1: style LoRAs
  - num_loras_1: 2
  - model_strength_1: "0.6-0.9"  ← Random
  - clip_strength_1: "0.6-0.9"   ← Random

Group 2: character LoRAs
  - num_loras_2: 1
  - model_strength_2: "1.0"      ← Fixed
  - clip_strength_2: "1.0"       ← Fixed

Group 3: Unused
  - lora_folder_path_3: (empty)
  - num_loras_3: 0

→ Result: 2 style LoRAs (variable strength) + 1 character LoRA (fixed strength) = 3 LoRAs total
```

## Settings

### Common Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `token_normalization` | Token normalization method | `none` |
| `weight_interpretation` | Prompt emphasis notation interpretation | `A1111` |
| `additional_prompt` | Additional prompt (combined with trigger words) | (empty) |
| `trigger_word_source` | Trigger word source | `json_combined` |
| `seed` | Random selection seed | `0` |

#### Important Notes on additional_prompt

**Supported:**
- Regular prompt text
- Text input from other nodes (e.g., Wildcard Encode's `populated_text`)

**Not Supported (automatically removed):**
- `<lora:xxx:0.8>` format LoRA syntax
- `{a|b|c}` format wildcard syntax
- `__filename__` format wildcard syntax

**Why:**
- This node applies LoRAs via folder specification
- Wildcard functionality should be handled by dedicated nodes (Wildcard Encode, etc.)
- Writing LoRA syntax causes **filename to become meaningful tokens as noise**

**Example (problematic case):**
```
Input: "1girl, <lora:anime_style:0.8>, beautiful"
↓
CLIP tokenization: [1girl, lora, anime, style, 0, 8, beautiful]
                            ^^^^^ ^^^^^
                            Unintended words added to prompt ❌
```

**Correct usage:**
```
additional_prompt: "1girl, beautiful"  ← No LoRA syntax ✅
LoRA application: Use folder specification feature ✅
```

Or, when connecting from Wildcard Encode, LoRA syntax is automatically removed:
```
[Wildcard Encode] populated_text: "1girl, <lora:style:0.8>, beautiful"
       ↓
[This Node] additional_prompt received → LoRA syntax auto-removed
       ↓
Final prompt: "1girl, beautiful" ✅
```

### Group Settings (1-3)

Each group can be configured individually:

| Setting | Description | Default |
|---------|-------------|---------|
| `lora_folder_path_X` | LoRA folder absolute path | (empty) |
| `include_subfolders_X` | Include subfolders | `true` |
| `model_strength_X` | MODEL application strength | `"1.0"` |
| `clip_strength_X` | CLIP application strength | `"1.0"` |
| `num_loras_X` | Number of LoRAs to select | Group 1: `1`, Groups 2/3: `0` |

## Strength Specification (Important)

Strength fields accept **fixed values** or **random ranges**.

### Fixed Value

```
Input: "1.0"
→ Always applied at 1.0

Input: "0.55"
→ Always applied at 0.55
```

**Features:**
- Input value used as-is
- Up to 2 decimal places (e.g., `0.55`)

### Random Range

```
Input: "0.4-0.8"
→ Randomly selects from 0.4, 0.5, 0.6, 0.7, 0.8 (0.1 increments)

Input: "0.5-1.0"
→ Randomly selects from 0.5, 0.6, 0.7, 0.8, 0.9, 1.0

Input: "0.44-0.82"
→ Randomly selects from 0.4, 0.5, 0.6, 0.7, 0.8
   (Range automatically rounded to 1 decimal place)
```

**Features:**
- Specify range with hyphen (`-`)
- Values generated in 0.1 increments
- Range bounds with 2+ decimal places are rounded to 1 decimal place
- Different value selected each execution

### Error Handling

```
Input: "abc" or invalid format
→ Error logged, processed with strength 1.0
```

**Error message example:**
```
[RandomLoRALoader] ❌ Cannot parse strength 'abc', using 1.0
[RandomLoRALoader] 💡 Usage: '1.0' or '0.4-0.8'
```

### Verifying Actual Strength

Actual strength used can be verified in `positive_text` output:

```
<lora:style_anime:0.7:0.6>, anime style, vibrant,
               ↑   ↑
          MODEL    CLIP
          strength strength
```

**Recommended:** Connect Show Text node to `positive_text` to verify actual strength.

## MODEL Strength vs CLIP Strength

### Basic Concept

- **MODEL strength**: Affects image itself (art style, composition, colors)
- **CLIP strength**: Affects prompt understanding (trigger word effectiveness)

### Recommended Settings

**Beginners / General Use:**
```
model_strength: "1.0"
clip_strength: "1.0"
```
Using same value for both is the standard approach.

**Advanced / Fine-tuning:**
```
model_strength: "0.7"
clip_strength: "1.0"
```
For cases like wanting subtle art style but strong trigger word effect.

**Randomization for Experimentation:**
```
model_strength: "0.6-0.9"
clip_strength: "0.6-0.9"
```
For testing various strength combinations.

## Trigger Word Retrieval Methods

### json_combined (All Combined)

Combines all trigger word patterns and removes duplicates.

**Example:**
```json
"trainedWords": [
  "character, red hair, blue eyes, uniform",
  "character, red hair, blue eyes, casual clothes"
]
```
↓
```
Output: character, red hair, blue eyes, uniform, casual clothes
```

### json_random (Random Selection)

Randomly selects one pattern from trigger words.

**Example:**
```json
"trainedWords": [
  "character, red hair, blue eyes, uniform",
  "character, red hair, blue eyes, casual clothes"
]
```
↓
```
Output: character, red hair, blue eyes, casual clothes (random)
```

### json_sample_prompt (Sample Retrieval)

Randomly retrieves one sample prompt from JSON.

- Outputs both positive_text and negative_text
- Automatically removes `<lora:xxx:x.x>` syntax from samples
- Generates new LoRA syntax with node-configured strength

**Example:**
```json
"images": [{
  "meta": {
    "prompt": "1girl, <lora:style:0.8>, beautiful",
    "negativePrompt": "bad quality, worst quality"
  }
}]
```
↓
```
positive_text: 1girl, beautiful (LoRA syntax removed)
negative_text: bad quality, worst quality
```

### metadata (Embedded Metadata Only - NEW)

Reads trigger words **directly from LoRA file's embedded metadata**, ignoring external `.metadata.json` and `.info` files.

**Supported metadata fields:**
- `ss_tag_frequency`: kohya_ss format tag frequency (extracts top 20 tags)
- `modelspec.trigger_word`: Trigger word
- `ss_output_name`: Model name

**Use case:**
- When you want to use only the metadata embedded by the LoRA trainer
- When external JSON files contain incorrect information
- For LoRAs without external metadata files

**Example:**
```
LoRA file contains embedded metadata:
  ss_tag_frequency: {"dataset1": {"alice": 150, "blonde": 120, ...}}
  ↓
Output: alice, blonde, blue_eyes, ...
```

**Note:** Other modes (`json_combined`, `json_random`, `json_sample_prompt`) use external files with priority, falling back to embedded metadata if external files are not found.

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `MODEL` | MODEL | Model with LoRA applied |
| `CLIP` | CLIP | CLIP with LoRA applied |
| `positive_text` | STRING | LoRA info and positive prompt |
| `negative_text` | STRING | Negative prompt (json_sample_prompt only) |
| `positive` | CONDITIONING | Positive conditioning |
| `negative` | CONDITIONING | Negative conditioning |

### positive_text Output Example

```
1girl, beautiful,
<lora:style_anime_v2:0.7:0.6>, anime style, vibrant colors,
<lora:character_alice:1.0:1.0>, alice, blonde hair, blue eyes,
```

## Required File Structure

**Metadata files or embedded data** required for trigger word retrieval.

### Priority Order

The node reads metadata in the following priority order:

1. **`.metadata.json`** (ComfyUI Lora Manager format)
2. **`.info`** (Civitai Helper format)
3. **Embedded metadata in LoRA file** (Always available if LoRA was trained with metadata)

### 1. ComfyUI Lora Manager format (Recommended)

```
/path/to/lora/
├── style_anime_v2.safetensors
├── style_anime_v2.metadata.json  ← ComfyUI Lora Manager
├── character_alice.safetensors
└── character_alice.metadata.json
```

### 2. Civitai Helper format

```
/path/to/lora/
├── style_anime_v2.safetensors
├── style_anime_v2.info  ← Civitai Helper
├── character_alice.safetensors
└── character_alice.info
```

### 3. Embedded metadata (No external file needed)

```
/path/to/lora/
├── style_anime_v2.safetensors  ← Contains embedded metadata
└── character_alice.safetensors  ← Contains embedded metadata
```

**Note:** 
- If external files (`.metadata.json` or `.info`) exist, they take priority over embedded metadata (except when using `trigger_word_source: metadata`)
- When `trigger_word_source` is set to `metadata`, only embedded metadata is read, ignoring external files

### Generating metadata files

**ComfyUI Lora Manager (Recommended):**
- [ComfyUI Lora Manager](https://github.com/willmiao/ComfyUI-Lora-Manager)
- Generates `.metadata.json` files

**Civitai Helper:**
- [Civitai Helper](https://github.com/butaixianran/Stable-Diffusion-Webui-Civitai-Helper)
- Generates `.info` files (also supported)

**Embedded metadata:**
- Automatically created during LoRA training with kohya_ss or other trainers
- No additional tools required

## Troubleshooting

### Cannot retrieve trigger words

**For external metadata files:**
- Check if metadata file exists (`.metadata.json` or `.info`)
- Verify JSON contains `civitai.trainedWords` or `civitai.images`
- Confirm filename matches `{LoRAfilename}.metadata.json` or `{LoRAfilename}.info`

**For embedded metadata:**
- Set `trigger_word_source` to `metadata` to read directly from LoRA file
- Check if LoRA was trained with metadata (most modern LoRAs include this)
- Supported fields: `ss_tag_frequency`, `modelspec.trigger_word`, `ss_output_name`


### additional_prompt with LoRA syntax doesn't work

**Symptom:**
```
additional_prompt: "<lora:anime_style:0.8>, 1girl"
→ anime_style not applied
```

**Cause:**
This node doesn't interpret `<lora:xxx:0.8>` syntax. LoRA syntax is automatically removed.

**Solution:**
1. Use folder specification feature for LoRA application
2. When integrating with Wildcard Encode (Inspire), let it handle LoRA syntax

### Unintended words in prompt

**Symptom:**
```
additional_prompt: "<lora:anime_style:0.8>"
→ "anime", "style" words automatically added
```

**Cause:**
v1.0.0 and later automatically remove LoRA syntax, so this issue doesn't occur.
If using older version, LoRA syntax filename part was interpreted as tokens.

**Solution:**
- Update node to latest version
- Don't write LoRA syntax in additional_prompt

### LoRA not applied

- Verify folder path is correct
- Check `num_loras` isn't 0
- Check ComfyUI console for error logs

### Strength not as intended

- Check `positive_text` output with Show Text
- Displays actual strength like `<lora:xxx:0.7:0.6>`
- With random range specification, different value selected each time
- Check console for strength selection log: `[RandomLoRALoader] Selected 0.6 from range 0.4-0.8`

### Strength input error

**Symptom:**
```
[RandomLoRALoader] ❌ Cannot parse strength 'abc', using 1.0
```

**Solution:**
- Use correct format: `"1.0"` or `"0.4-0.8"`
- Range specification must use hyphen (`-`)
- Node won't crash with invalid input, operates with 1.0

### Default values not displayed

- Completely restart ComfyUI
- Clear browser cache (Ctrl+Shift+R)
- Delete and re-add node

### Console shows many "lora key not loaded" messages

**Symptom:**
```
lora key not loaded: lora_unet_input_blocks_4_1_proj_in.alpha
lora key not loaded: lora_unet_input_blocks_4_1_proj_in.lora_down.weight
...
```

**Cause and Solution:**

These messages are compatibility warnings output by ComfyUI core and **don't affect functionality**. Displayed when some keys in LoRA file aren't compatible with current model, but compatible keys apply normally.

v1.0.0 and later automatically suppress these warning messages. If still displayed in large quantities:

1. Verify node file is latest version
2. Restart ComfyUI
3. If still appears and functionality is fine, safe to ignore

## Tips & Tricks

### Using as a LoRA Syntax Filter Only

You can use this node as a simple LoRA syntax remover without applying any LoRAs.

**Setup:**
- Set all `num_loras` to `0` (or leave all folder paths empty)
- Connect Wildcard Encode's `populated_text` to `additional_prompt`
- Connect `positive_text` output to next node

**Use case:**
- Remove LoRA syntax from Wildcard Encode output
- Clean up prompts before passing to other nodes
- Use Wildcard Encode's LoRA processing while removing the syntax for compatibility

**Example workflow:**
```
[Wildcard Encode (Inspire)]
  text: "__style__, {red|blue|green}, <lora:base_effect:0.5>"
  ↓
  populated_text: "anime style, blue, <lora:base_effect:0.5>"
  (LoRA already applied to MODEL by Wildcard Encode)
  ↓
[Random LoRA Loader]
  num_loras: 0, 0, 0  ← No LoRA application
  additional_prompt ← Connected from populated_text
  ↓
  positive_text: "anime style, blue,"  ← LoRA syntax removed ✅
  ↓
[Next Node]
```

**Benefits:**
- ✅ Removes `<lora:filename:strength>` syntax that can become noise tokens
- ✅ No need for separate text processing nodes
- ✅ Works with any text containing LoRA syntax

## Disclaimer and Support Policy

### About This Node

This custom node was developed for personal use and is being shared publicly.

### Support

- ❌ **No technical support provided**
  - Usage questions
  - Environment setup assistance
  - Individual troubleshooting support

- ❌ **No warranty**
  - Operation in specific environments
  - Compatibility with future ComfyUI updates
  - Liability for data loss, etc.

### Community Contributions

The following are welcome but not guaranteed to be addressed:

- ✅ Bug reports (Issues)
- ✅ Pull requests
- ✅ Feature suggestions

### Terms of Use

- Use entirely at your own risk
- Test thoroughly before production use
- Author assumes no liability for any issues

## License

MIT License

Copyright (c) 2025

This software is provided "as is" without any express or implied warranties.

## Changelog

### v1.0.0 (2024-12-30)
- Initial public release
- 3-group support (select from different folders)
- Strength randomization (range specification: `0.4-0.8`)
- External JSON reading (Civitai Helper compatible)
- Auto-remove LoRA syntax in sample prompts
- **Auto-remove LoRA syntax in additional_prompt** (noise prevention)
- Separate positive_text/negative_text outputs
- Wildcard Encode (Inspire) integration
- Fully local operation (no API required)

## References

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI Lora Manager](https://github.com/willmiao/ComfyUI-Lora-Manager) - Generates `.metadata.json` (Recommended)
- [Civitai Helper](https://github.com/butaixianran/Stable-Diffusion-Webui-Civitai-Helper) - Generates `.info` (Also supported)
