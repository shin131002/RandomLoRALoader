# Changelog

All notable changes to this project will be documented in this file.

## [1.3.0] - 2026-09-11

### Fixed

#### Symlinked folders were skipped during scanning
- Folder scans now follow symbolic links, matching ComfyUI's own behaviour (`folder_paths.recursive_search` uses `followlinks=True`)
- Previously, a subfolder that was a symlink was skipped entirely, so LoRAs behind a link never appeared as candidates — even though they showed up fine in ComfyUI's native LoRA dropdown
- Affects all three nodes:
  - **Random LoRA Loader**: `glob.glob("**/*.safetensors")` replaced with `os.walk(followlinks=True)` (glob's `**` does not descend into symlinked directories)
  - **Filtered Random LoRA Loader** / **Filtered Random LoRA Loader (LBW)**: `os.walk()` now passes `followlinks=True`
- Symlink loops are detected via a `realpath` set and skipped, so a cyclic link cannot hang the scan
- A folder reachable through two different links is no longer scanned twice

#### Redundant error logging on non-safetensors LoRAs
- `_load_embedded_metadata` now returns early for `.pt` / `.ckpt` files instead of calling `safe_open`, which can only read `.safetensors`
- Previously every selected `.pt` / `.ckpt` produced a spurious "metadata read error" log line
- Trigger words for these formats still come from `.metadata.json` / `.info` sidecar files as before

### Changed

#### Seed reproducibility — candidate list is now sorted
- The candidate file list is sorted before random selection
- Previously the order came straight from the filesystem, so **the same seed could produce different selections on different machines**. Sorting makes a seed reproducible across environments
- ⚠️ Because the ordering changed, an existing workflow may select a different set of LoRAs after upgrading even with a fixed seed. If a result you were relying on changes, re-roll or re-pick the seed

#### Random LoRA Loader: extension support aligned with the Filtered nodes
- Now scans `.safetensors`, `.pt`, and `.ckpt` (previously `.safetensors` only)
- All three nodes now return an identical candidate list for the same folder
- Extension matching is case-insensitive, so `.SAFETENSORS` is picked up on Linux as well (glob was case-sensitive there)

---

## [1.2.0] - 2026-01-13

### Added

#### New Node: Filtered Random LoRA Loader (LBW)
- **LoRA Block Weight (LBW) support** for precise effect control
- **Automatic SD1.5/SDXL detection** - no manual model type selection needed
- **4 preset modes**: Style Focused, Character Focused, Structure/Composition Only, Balanced/Soft
- **Preset: Random mode** - randomly selects one of the 4 presets
- **Direct Input mode** - custom weight specification with auto-adjustment
- **Automatic weight adjustment** - handles mismatched element counts
  - Too few elements: pads with 1.0 at the end
  - Too many elements: truncates from the end
- U-Net block structure support:
  - SDXL: 20 elements (BASE + IN:9 + MID:1 + OUT:9)
  - SD1.5: 17 elements (BASE + IN:6 + MID:1 + OUT:9)
- LBW syntax output in `positive_text` for Wildcard Encode compatibility
- Includes all features from Filtered Random LoRA Loader

#### Video Preview Support (All Nodes)
- Video file preview support (.mp4, .webm, .avi, .mov)
- Extracts first frame as static image
- Requires optional `opencv-python` dependency
- Graceful fallback to black screen with warning if opencv-python not installed
- Priority order: static images → animated images → video files

### Changed

#### Model Compatibility
- ⚠️ **Explicitly SD1.5/SDXL only** - other architectures (Flux, SD3, etc.) not supported
- LBW feature specifically designed for SD1.5/SDXL U-Net structure

#### Dependencies
- Added optional dependency: `opencv-python` (for video preview only)
- Core functionality works without opencv-python

### Technical Details

#### LBW Implementation
- Direct tensor weight manipulation for precise block control
- Automatic LoRA type detection via output_blocks analysis
- Compatible with serial node chaining (different LBW per node)
- Zero weight (all 0) = complete LoRA disable

#### Preview Image Processing
- Pillow-only support: .png, .jpg, .jpeg, .gif, .webp (always works)
- opencv-python support: .mp4, .webm, .avi, .mov (optional)
- First-frame extraction for animated/video formats
- Consistent 1240px preprocessing

### Performance
- No performance impact when LBW not used (Normal mode)
- Metadata caching unchanged from v1.1.0

---

## [1.1.0] - 2026-01-04

### Added

#### New Node: Filtered Random LoRA Loader
- Single folder with keyword filtering capabilities
- Space-separated keyword search with phrase support (`"..."`)
- AND/OR filtering modes
- Metadata search with caching (instant 2nd+ time)
- Designed for chaining multiple instances
- Supports all features from Random LoRA Loader

#### Preview Image Output (Both Nodes)
- New `preview` output (IMAGE type)
- Long edge resized to 1240px (aspect ratio preserved)
- Center-padded to 1240x1240 for batch compatibility
- Partial filename matching (case-insensitive)
- Example: `anime_v1.safetensors` matches `anime_v1.png`, `anime_v1_preview.jpg`, etc.

#### Duplicate Filename Handling (Both Nodes)
- New `unique_by_filename` parameter (default: `True`)
- Prevents selecting same LoRA from different subfolders
- Example: `/style/lora.safetensors` and `/backup/lora.safetensors` → only one selected
- Logs duplicate detections with paths

### Changed

#### Both Nodes
- **Breaking**: Split `additional_prompt` into `additional_prompt_positive` and `additional_prompt_negative`
- Unified strength precision to 1 decimal place (was 2 for Filtered, 1 for Random)
- Improved LoRA syntax removal from CONDITIONING generation

#### Filtered Random LoRA Loader
- Better handling when `num_loras` exceeds available files (fills with duplicates)
- Removed `control_after_generate` (use ComfyUI's default seed control)

### Fixed

#### Both Nodes
- Fixed negative_text output in `json_sample_prompt` mode
- Fixed LoRA syntax (`<lora:...>`) appearing in metadata trigger words
- Fixed parameter order consistency

#### Random LoRA Loader
- Fixed duplicate parameter in INPUT_TYPES

### Performance

#### Metadata Search Caching
- Initial load time (SSD):
  - 1,000 files: ~2 seconds
  - 5,000 files: ~10 seconds
  - 10,000 files: ~20 seconds
  - 20,000 files: ~40 seconds
  - 50,000 files: ~100 seconds
- 2nd+ time: Instant (<100ms)
- Memory usage: ~150MB per 10,000 files
- Progress display for large collections

---

## [1.0.0] - 2025-12-30

### Initial Release

#### Random LoRA Loader
- 3-group folder selection
- Multi-source metadata reading (`.metadata.json`, `.info`, embedded)
- Strength randomization with range specification
- Multiple trigger word sources
- Sample prompt support with LoRA syntax removal
- Wildcard Encode (Inspire) compatibility

#### Core Features
- No additional dependencies (uses Python stdlib + ComfyUI)
- Automatic trigger word extraction
- CONDITIONING output with cleaned prompts
- Seed control integration
