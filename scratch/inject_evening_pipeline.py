import sys

content = open('Actress_Modules/actress_scheduler.py', 'r', encoding='utf-8', errors='replace').read()

marker = '# Scheduler Loop (runs in background thread)'

evening_code = '''
# ===========================================================================
# Evening Pipeline  (6 PM IST harvest -> face-off clips ready by 6:30 PM)
# ===========================================================================

EVENING_CLIPS_PER_ACCOUNT = 6
EVENING_POLL_SLOTS        = 2


def run_evening_pipeline():
    """
    Triggered at 6:00 PM IST (12:30 UTC).
    1. Scrape 6 clips per account
    2. Remove pinned posts
    3. Check avoid-list (shortcode + hash)
    4. Sort by gender: women -> AMTCE fast-track; men -> normal PublishQueue
    5. Process women clips (<=6 min each)
    6. Write The_json/hotness_poll_schedule.json for 6:30 PM face-off announce
    """
    import concurrent.futures
    from Download_Modules.apify_downloader import apify_scrape_actress_accounts
    from Download_Modules.downloader       import download_video
    from Actress_Modules.actress_ledger    import get_ledger, extract_shortcode
    from Actress_Modules.channel_router    import (
        get_source_accounts, resolve_channel, detect_gender_from_name, CHANNEL_WOMEN,
    )

    logger.info("=" * 60)
    logger.info("AMTCE EVENING PIPELINE -- 6 PM Harvest Starting")
    logger.info("%s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    source_accounts = get_source_accounts()
    if not source_accounts:
        logger.warning("[EVENING] No source accounts -- skipping")
        return

    ledger        = get_ledger()
    downloads_dir = os.getenv("DOWNLOADS_DIR", "downloads")

    logger.info("[EVENING] Scraping %d account(s) x %d clips each",
                len(source_accounts), EVENING_CLIPS_PER_ACCOUNT)

    all_reels = apify_scrape_actress_accounts(
        actress_name      = "evening_pipeline",
        source_accounts   = source_accounts,
        limit_per_account = EVENING_CLIPS_PER_ACCOUNT,
    )

    if not all_reels:
        logger.warning("[EVENING] Apify returned no reels -- aborting")
        return

    logger.info("[EVENING] %d reels from Apify", len(all_reels))
    women_queue = []
    men_queue   = []

    for reel in all_reels:
        video_url = reel.get("videoUrl", "")
        if not video_url:
            continue

        # Strip pinned posts
        if reel.get("isPinned") or reel.get("is_pinned") or reel.get("pinned"):
            logger.info("[EVENING] Pinned post removed: %s", reel.get("shortcode", "?"))
            continue

        # Avoid-list: shortcode check (pre-download)
        shortcode = reel.get("shortcode")
        if not shortcode:
            post_url  = reel.get("url") or reel.get("postUrl") or video_url
            shortcode = extract_shortcode(post_url)
        if shortcode and ledger.shortcode_seen(shortcode):
            logger.info("[EVENING] Shortcode %s in avoid-list -- skip", shortcode)
            continue

        # Gender sort via channel_router
        ig_id = reel.get("ownerUsername", "").lower()
        actress_folder, actress_title, is_nsfw = resolve_channel(ig_id, reel)
        gender = "women" if actress_folder == CHANNEL_WOMEN else "men"
        if gender == "men" and " " in actress_title:
            try:
                if detect_gender_from_name(actress_title) == "female":
                    gender         = "women"
                    actress_folder = CHANNEL_WOMEN
            except Exception:
                pass

        logger.info("[EVENING] @%s gender=%s title=%s", ig_id, gender, actress_title)

        # Download
        os.environ["SKIP_AUDIO_EXTRACT"] = "true"
        video_path, _ = download_video(video_url)
        os.environ.pop("SKIP_AUDIO_EXTRACT", None)
        if not video_path:
            continue

        # Avoid-list: hash check (post-download)
        if ledger.hash_seen(video_path):
            if shortcode:
                ledger.commit_with_channel(shortcode, video_path, actress_folder)
            try:
                os.remove(video_path)
            except Exception:
                pass
            continue

        safe_ch      = actress_folder.replace(" ", "_")
        safe_nm      = _safe_title(actress_title)
        batch_folder = _next_batch_folder("{}_{}".format(safe_ch, safe_nm), downloads_dir)
        idx          = len(women_queue) + len(men_queue) + 1
        video_path   = _organize_clip(video_path, actress_title, batch_folder, idx)
        _inject_niche(video_path, actress_folder, actress_title)
        ledger.commit_with_channel(shortcode, video_path, actress_folder)

        if gender == "women" and len(women_queue) < EVENING_POLL_SLOTS:
            women_queue.append((video_path, actress_title, actress_folder, shortcode))
            logger.info("[EVENING] Women queue [%d/%d]: %s",
                        len(women_queue), EVENING_POLL_SLOTS, os.path.basename(video_path))
        else:
            men_queue.append((video_path, actress_title, actress_folder, shortcode))
            logger.info("[EVENING] Men -> PublishQueue: %s", os.path.basename(video_path))

        if len(women_queue) >= EVENING_POLL_SLOTS and len(men_queue) >= 2:
            break

    # Process women clips through AMTCE (max 6 min ceiling each)
    poll_slots = []
    for video_path, actress_title, actress_folder, shortcode in women_queue:
        logger.info("[EVENING] AMTCE processing: %s", os.path.basename(video_path))
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    _auto_publish_clip,
                    video_path, actress_title, actress_folder, shortcode,
                )
                fut.result(timeout=360)
        except concurrent.futures.TimeoutError:
            logger.warning("[EVENING] Processing timed out (6 min cap): %s",
                           os.path.basename(video_path))
        except Exception as pe:
            logger.error("[EVENING] Processing error: %s", pe)

        processed = os.path.join(
            "Processed Shorts",
            os.path.splitext(os.path.basename(video_path))[0] + ".mp4"
        )
        if not os.path.exists(processed):
            processed = video_path
        poll_slots.append({"actress": actress_title, "video_path": processed})

    # Queue men clips normally
    for video_path, actress_title, actress_folder, shortcode in men_queue:
        PublishQueue.add(video_path, actress_title, actress_folder, shortcode=shortcode)

    # Write hotness_poll_schedule.json (read by job_announce at 6:30 PM)
    sched = {
        "session_date": datetime.now().strftime("%Y-%m-%d"),
        "written_at":   time.time(),
    }
    if poll_slots:
        sched["post_a"] = poll_slots[0]
    if len(poll_slots) >= 2:
        sched["post_b"] = poll_slots[1]

    try:
        os.makedirs("The_json", exist_ok=True)
        tmp = "The_json/hotness_poll_schedule.json.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sched, f, indent=2)
        os.replace(tmp, "The_json/hotness_poll_schedule.json")
        logger.info("[EVENING] Poll schedule written: A=%s | B=%s",
                    sched.get("post_a", {}).get("actress", "N/A"),
                    sched.get("post_b", {}).get("actress", "N/A"))
    except Exception as we:
        logger.error("[EVENING] Failed to write poll schedule: %s", we)

    logger.info("EVENING PIPELINE COMPLETE -- women=%d | men=%d",
                len(women_queue), len(men_queue))


'''

pos = content.find(marker)
if pos == -1:
    print("ERROR: marker not found")
    sys.exit(1)

new_content = content[:pos] + evening_code + content[pos:]
with open('Actress_Modules/actress_scheduler.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("OK: inserted {} chars at pos {}".format(len(evening_code), pos))
