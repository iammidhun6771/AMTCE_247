# Graph Report - D:\AMTCE\Core_Modules  (2026-06-02)

## Corpus Check
- 20 files · ~12,227 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 261 nodes · 448 edges · 20 communities detected
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 110 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]

## God Nodes (most connected - your core abstractions)
1. `EditorMemory` - 36 edges
2. `_load_state()` - 26 edges
3. `StrategyOptimizer` - 20 edges
4. `SelfOptimizingEditor` - 18 edges
5. `VideoLog` - 18 edges
6. `AnalyticsEngine` - 17 edges
7. `MemoryUpdater` - 15 edges
8. `RetentionAnalyzer` - 15 edges
9. `_save_state()` - 14 edges
10. `PatternExtractor` - 13 edges

## Surprising Connections (you probably didn't know these)
- `MemoryUpdater` --uses--> `EditorMemory`  [INFERRED]
  D:\AMTCE\Core_Modules\memory_updater.py → D:\AMTCE\Core_Modules\editor_memory.py
- `memory_updater.py Writes extracted patterns into editor_memory using EWMA updat` --uses--> `EditorMemory`  [INFERRED]
  D:\AMTCE\Core_Modules\memory_updater.py → D:\AMTCE\Core_Modules\editor_memory.py
- `Applies a list of editing_pattern observations to the EditorMemory store.` --uses--> `EditorMemory`  [INFERRED]
  D:\AMTCE\Core_Modules\memory_updater.py → D:\AMTCE\Core_Modules\editor_memory.py
- `Upsert all patterns into memory and rebuild aggregate scores.          Args:` --uses--> `EditorMemory`  [INFERRED]
  D:\AMTCE\Core_Modules\memory_updater.py → D:\AMTCE\Core_Modules\editor_memory.py
- `SelfOptimizingEditor` --uses--> `EditorMemory`  [INFERRED]
  D:\AMTCE\Core_Modules\self_optimizing_editor.py → D:\AMTCE\Core_Modules\editor_memory.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.1
Nodes (26): AnalyticsEngine, analytics_engine.py Fetches YouTube Analytics data for a published video.  Re, Fetches per-video analytics from YouTube Analytics API.      Args:         cr, MemoryUpdater, PatternExtractor, Attributes retention events to editing decisions.      Inputs:         retention, Identifies meaningful engagement events from a retention curve.      Args:, RetentionAnalyzer (+18 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (24): ApifyQuotaState, _default_state(), HarvestState, _load_state(), _parse_hhmm(), PublisherState, Manages harvest slot tracking and catch-up logic.      Usage:         state = Ha, Reset daily counters when a new day starts. (+16 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (18): EditorMemory, Reads and writes the persistent editing pattern memory.      Args:         path:, Load memory from disk, or return a fresh empty memory., Atomic write to disk., Insert or update a pattern entry using EWMA.          Args:             key:, Recompute arc_scores and persona_scores as weighted mean of pattern scores., Public save — call after a batch of upserts., memory_updater.py Writes extracted patterns into editor_memory using EWMA updat (+10 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (16): AccountScrapeThrottle, get_account_scrape_throttle(), get_apify_quota(), get_harvest_state(), get_publisher_state(), get_scraped_posts_registry(), log_full_status(), salesman_state.py — AMTCE Intelligent Salesman State Engine ==================== (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.27
Nodes (4): NarrativeCoherenceEngine, Narrative Coherence Engine  Validates and lightly corrects the segment sequence, Compute Kendall tau-b for a list of ranks., Ensures timeline coherence without breaking existing outputs.

### Community 5 - "Community 5"
Cohesion: 0.2
Nodes (7): _confidence_from_samples(), find_similar_pattern(), _pattern_key(), editor_memory.py Persistent pattern memory store with EWMA (Exponentially Weight, Canonical key for a pattern observation., Finds a memory-backed editing preference for a given moment signature.     Curre, Sigmoid-like confidence from sample count.     0 samples → 0.0, 3 samples → ~0.5

### Community 6 - "Community 6"
Cohesion: 0.28
Nodes (8): calculate_score(), normalize_signals(), segment_validator.py -------------------- STRICT Video Segment Validation System, Normalize all signals across candidates and selected segments to [0, 1]., Find nearest signal value within a time window., Compute score = 0.35*M + 0.30*R + 0.20*V + 0.15*E, resolve_signal(), validate_segments()

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (4): Return a synthetic snapshot for testing without API access., Fetch views, avg view duration, likes., Fetch audience retention curve.         Returns list of {"t": float, "pct": flo, Fetch a complete analytics snapshot for one video.          Args:

### Community 8 - "Community 8"
Cohesion: 0.29
Nodes (6): _find_segment_at(), _learning_weight(), pattern_extractor.py Maps retention analysis events to the editing decisions tha, Weight reflects how trustworthy this single pattern observation is.     High-mag, Return the first segment containing time t ± window, or None., Returns a list of editing_pattern dicts, one per attributed event.         Event

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (5): retention_analyzer.py Analyzes a YouTube audience retention curve to find engage, Simple moving average over pct values., Composite engagement score [0,1].          Formula:           base = avg_pct / 1, Analyze one analytics_snapshot and return retention_peaks.          Returns None, _smooth()

### Community 10 - "Community 10"
Cohesion: 0.29
Nodes (6): _apply_soe_hints(), orchestrator_soe_patch.py Integration patch for Compiler_Modules/orchestrator.py, # IMPORTANT: only override if the memory-suggested arc's score is at least, Record the upload provenance for future learning.     Safe to call even if SOE i, Fetch current optimization signals and inject them as soft hints     into profil, _record_upload_to_soe()

### Community 11 - "Community 11"
Cohesion: 0.29
Nodes (4): PerceptionEngine, Perception Engine: detects salient events from temporal signals., Detect energy spikes based on delta between consecutive samples., Detect spikes, pauses, reaction timing, motion bursts.

### Community 12 - "Community 12"
Cohesion: 0.29
Nodes (4): Story Builder: generate clip segments around detected moments with reaction offs, Build a simple hook→build→payoff timeline., Convert semantic moments into non-overlapping segments., StoryBuilder

### Community 13 - "Community 13"
Cohesion: 0.29
Nodes (4): Temporal Signal Builder for EditorBrainV3., Create a 0.5s-sampled signal stream with combined energy., Resample detector outputs into a uniform timeline., TemporalSignalBuilder

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (4): MeaningEngine, Meaning Engine: interpret perceptual events into viewer-relevant moments., Convert spikes into interpreted moments., Map low-level spikes into semantic moment labels.

### Community 15 - "Community 15"
Cohesion: 0.4
Nodes (3): PacingEngine, Pacing Engine: detect emotional energy waves., Identify rising/peak/falling energy regions in temporal stream.

### Community 16 - "Community 16"
Cohesion: 0.4
Nodes (3): Reward Scorer: compute confidence for an edit plan., Blend hook timing, moment strength, arc completeness, and coherence., RewardScorer

### Community 17 - "Community 17"
Cohesion: 0.5
Nodes (3): Learning stability gate to clamp extreme pattern weights., Clamp weight fields to prevent overfitting., stabilize()

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Core_Modules — Self-Optimizing Editor Intelligence Sub-System =================

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Convenience constructor: builds a VideoLog entry from EditorBrainV3 output.

## Knowledge Gaps
- **87 isolated node(s):** `analytics_engine.py Fetches YouTube Analytics data for a published video.  Re`, `Fetches per-video analytics from YouTube Analytics API.      Args:         cr`, `Return a synthetic snapshot for testing without API access.`, `Fetch views, avg view duration, likes.`, `Fetch audience retention curve.         Returns list of {"t": float, "pct": flo` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (2 nodes): `__init__.py`, `Core_Modules — Self-Optimizing Editor Intelligence Sub-System =================`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Convenience constructor: builds a VideoLog entry from EditorBrainV3 output.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EditorMemory` connect `Community 2` to `Community 0`, `Community 5`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `AnalyticsEngine` connect `Community 0` to `Community 13`, `Community 7`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `SelfOptimizingEditor` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `EditorMemory` (e.g. with `MemoryUpdater` and `memory_updater.py Writes extracted patterns into editor_memory using EWMA updat`) actually correct?**
  _`EditorMemory` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `StrategyOptimizer` (e.g. with `SelfOptimizingEditor` and `self_optimizing_editor.py Master controller for the Self-Optimizing Editor subs`) actually correct?**
  _`StrategyOptimizer` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `SelfOptimizingEditor` (e.g. with `AnalyticsEngine` and `EditorMemory`) actually correct?**
  _`SelfOptimizingEditor` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `VideoLog` (e.g. with `SelfOptimizingEditor` and `self_optimizing_editor.py Master controller for the Self-Optimizing Editor subs`) actually correct?**
  _`VideoLog` has 10 INFERRED edges - model-reasoned connections that need verification._