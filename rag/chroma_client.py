"""ChromaDB client setup for the RAG prototype.

Creates a persistent local store and returns the editing_patterns collection
configured with the default embedding function.
"""

import os
import time
import logging
import concurrent.futures
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import hashlib
import numpy as np

logger = logging.getLogger("chroma_client")

class SimpleHashingEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Fallback embedding function that generates deterministic vectors via hashing.
    Used when onnxruntime/DefaultEmbeddingFunction is unavailable or hanging.
    """
    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        embeddings = []
        for text in input:
            # Create a deterministic 384-dim vector based on the text hash
            seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            # 384 dimensions match the all-MiniLM-L6-v2 model size
            vector = rng.standard_normal(384).tolist()
            embeddings.append(vector)
        return embeddings

class GeminiFallbackEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """Secondary fallback: uses Google's Gemini API for embeddings."""
    def __init__(self, api_key: str):
        self._ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=api_key)
        
    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        try:
            return self._ef(input)
        except Exception as e:
            logger.error(f"[GEMINI_EF] Failed: {e}")
            # Final fallback to hashing if API fails
            return SimpleHashingEmbeddingFunction()(input)

def get_collection(collection_name: str = "editing_patterns"):
    """Return a Chroma collection with resilient embeddings."""

    store_path = Path(__file__).resolve().parent / "chroma_store"
    store_path.mkdir(parents=True, exist_ok=True)

    # 1. Check for manual override
    force_fallback = os.getenv("CHROMA_EF_FORCE_FALLBACK", "no").lower() in ("yes", "true", "1")
    
    # 2. Check for failure flag (skip ONNX if it recently timed out/failed)
    failure_flag = store_path / ".onnx_failed"
    skip_onnx = False
    if failure_flag.exists():
        try:
            # If it failed in the last 24 hours, skip to avoid startup delay
            if time.time() - failure_flag.stat().st_mtime < 86400:
                skip_onnx = True
                logger.info("[CHROMA] Skipping ONNX attempt due to recent failure flag.")
        except Exception:
            pass

    embedding_function = None

    # 3. Attempt Default ONNX Load
    if not force_fallback and not skip_onnx:
        try:
            timeout = int(os.getenv("CHROMA_EF_TIMEOUT", "30"))
            logger.info(f"[CHROMA] Attempting DefaultEmbeddingFunction (ONNX) - {timeout}s timeout...")
            
            def _get_ef():
                ef = embedding_functions.DefaultEmbeddingFunction()
                # Force load the model by running a dummy embedding
                ef(["test"]) 
                return ef

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_get_ef)
                try:
                    embedding_function = future.result(timeout=timeout)
                    logger.info("✅ [CHROMA] DefaultEmbeddingFunction loaded successfully.")
                    # Clean up flag if it now works
                    if failure_flag.exists():
                        try: failure_flag.unlink()
                        except: pass
                except concurrent.futures.TimeoutError:
                    logger.warning(f"⚠️ [CHROMA] DefaultEmbeddingFunction TIMEOUT ({timeout}s).")
                    try: failure_flag.touch()
                    except: pass
                except Exception as e:
                    logger.error(f"⚠️ [CHROMA] DefaultEmbeddingFunction failed: {e}")
                    try: failure_flag.touch()
                    except: pass
        except Exception as e:
            logger.error(f"[CHROMA] Unexpected error during ONNX load: {e}")

    # 4. Fallback Chain
    if embedding_function is None:
        # Try Gemini API if available (high quality fallback)
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Manual fallback to Credentials/.env if environment is missing it
        if not api_key:
            try:
                from dotenv import load_dotenv
                cred_env = Path(__file__).resolve().parent.parent / "Credentials" / ".env"
                if cred_env.exists():
                    load_dotenv(cred_env)
                    api_key = os.getenv("GEMINI_API_KEY")
            except:
                pass

        if api_key:
            logger.info("[CHROMA] Using GeminiFallbackEmbeddingFunction.")
            embedding_function = GeminiFallbackEmbeddingFunction(api_key=api_key)
        else:
            logger.warning("[CHROMA] No Gemini API key found for fallback. Using SimpleHashing-Fallback.")
            embedding_function = SimpleHashingEmbeddingFunction()

    # 5. Initialize Client (with automatic recovery for corrupted stores)
    from chromadb.config import Settings
    
    settings = Settings(anonymized_telemetry=False)
    
    try:
        client = chromadb.PersistentClient(
            path=str(store_path),
            settings=settings
        )
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )
    except (Exception, BaseException) as e:
        # Check for the specific Rust panic or common corruption indicators
        err_str = str(e)
        is_panic = "panicked" in err_str or "out of range" in err_str
        
        if is_panic:
            logger.error(f"🚨 [CHROMA] Fatal Rust Panic detected: {err_str}")
            logger.info("🔄 [CHROMA] Attempting automatic recovery by resetting the store...")
            
            # Rename the corrupted store
            backup_path = store_path.with_name(f"chroma_store_corrupted_{int(time.time())}")
            try:
                # Ensure client is closed if it partially opened
                client = None
                import gc
                gc.collect()
                
                os.rename(str(store_path), str(backup_path))
                logger.info(f"✅ [CHROMA] Corrupted store moved to {backup_path.name}")
                
                # Re-create empty directory
                store_path.mkdir(parents=True, exist_ok=True)
                
                # Retry initialization
                client = chromadb.PersistentClient(
                    path=str(store_path),
                    settings=settings
                )
                collection = client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=embedding_function,
                )
                logger.info("✅ [CHROMA] Fresh store initialized successfully.")
                
            except Exception as recovery_err:
                logger.error(f"❌ [CHROMA] Recovery failed: {recovery_err}")
                raise e # Re-raise original if recovery fails
        else:
            raise e # Not a panic, just re-raise
    
    return collection
