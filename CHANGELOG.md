# Changelog

All notable changes to this project will be documented in this file.

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

## [1.0.0] - 2025-12-XX

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
