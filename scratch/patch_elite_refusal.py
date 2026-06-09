import sys
sys.stdout.reconfigure(encoding='utf-8')

target = "Compiler_Modules/orchestrator.py"

with open(target, "r", encoding="utf-8") as f:
    content = f.read()

OLD_MARKER = (
    '                          profile_data["editing_source"] = "none"\n'
    '                                profile_data["editor_authority"] = True \n'
    '                                logger.info("\u26aa [EDITOR_SOURCE]=none | [ELITE_REFUSAL] Content not worth editing.")\n'
    '                            else:\n'
    '                                profile_data["editing_source"] = "fallback"\n'
    '                                profile_data["fallback_mode"] = True\n'
    '                                logger.warning("\U0001f4c9 [EDITOR_SOURCE]=fallback | Gemini output invalid. Using Python fallback.")\n'
    '                            break'
)

if OLD_MARKER not in content:
    # Try to find and print anchor text for exact matching
    idx = content.find('editing_source"] = "none"')
    print("EXACT CONTEXT:")
    print(repr(content[idx-50:idx+600]))
    sys.exit(1)

NEW_BLOCK = (
    '                          profile_data["editing_source"] = "moment_fallback"\n'
    '                                profile_data["editor_authority"] = False\n'
    '                                profile_data["fallback_mode"] = True\n'
    '                                logger.warning(\n'
    '                                    "\u26aa [EDITOR_SOURCE]=none | [ELITE_REFUSAL] Gemini returned no segments "\n'
    '                                    "after 3 retries. Building moment-driven fallback timeline."\n'
    '                                )\n'
    '                                # -- [MOMENT FALLBACK] Build timeline from candidate_moments --\n'
    '                                # Prevents: 0 segments -> cannot reconstruct -> Compilation Failed\n'
    '                                _fallback_candidates = sorted(\n'
    '                                    [m for m in profile_data.get("candidate_moments", []) if isinstance(m, dict)],\n'
    '                                    key=lambda m: float(m.get("composite_score", m.get("score", m.get("rank_base", 0.0)))),\n'
    '                                    reverse=True\n'
    '                                )\n'
    '                                _fallback_segs = []\n'
    '                                _seg_dur = 4.0\n'
    '                                _roles = ["hook", "buildup", "climax"]\n'
    '                                for _fi, _fm in enumerate(_fallback_candidates[:3]):\n'
    '                                    _ft = float(_fm.get("time", _fm.get("timestamp", 0.0)))\n'
    '                                    _fs = max(0.0, _ft - 0.5)\n'
    '                                    _fe = min(duration, _ft + _seg_dur)\n'
    '                                    if _fe > _fs + 0.5:\n'
    '                                        _fallback_segs.append({\n'
    '                                            "clip_id": 0,\n'
    '                                            "start": round(_fs, 3),\n'
    '                                            "end": round(_fe, 3),\n'
    '                                            "role": _roles[_fi] if _fi < len(_roles) else "buildup",\n'
    '                                            "transition": "hard_cut",\n'
    '                                            "reason": "moment_fallback",\n'
    '                                            "impact": 0.5,\n'
    '                                            "clarity": 0.5,\n'
    '                                        })\n'
    '                                if len(_fallback_segs) >= 2:\n'
    '                                    profile_data["editing_timeline"] = _fallback_segs\n'
    '                                    logger.info(\n'
    '                                        f"\u2705 [MOMENT_FALLBACK] Built {len(_fallback_segs)} segments from top candidate moments."\n'
    '                                    )\n'
    '                                else:\n'
    '                                    logger.warning(\n'
    '                                        "\u26a0\ufe0f [MOMENT_FALLBACK] Insufficient candidate moments -- render will likely fail."\n'
    '                                    )\n'
    '                            else:\n'
    '                                profile_data["editing_source"] = "fallback"\n'
    '                                profile_data["fallback_mode"] = True\n'
    '                                logger.warning("\U0001f4c9 [EDITOR_SOURCE]=fallback | Gemini output invalid. Using Python fallback.")\n'
    '                            break'
)

content = content.replace(OLD_MARKER, NEW_BLOCK, 1)

with open(target, "w", encoding="utf-8") as f:
    f.write(content)

# Verify
with open(target, "r", encoding="utf-8") as f:
    verify = f.read()
if "moment_fallback" in verify:
    print("PATCH APPLIED OK")
else:
    print("ERROR: patch not found in output file")
