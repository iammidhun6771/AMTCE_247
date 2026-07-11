try:
    from graphify.reasoning_visualizer import visualize_anton_reasoning
    _GRAPHVIZ_AVAILABLE = True
except ImportError:
    _GRAPHVIZ_AVAILABLE = False

def generate_anton_visual(problem: str):
    if not _GRAPHVIZ_AVAILABLE:
        print("Graphviz not installed — skipping visual map generation.")
        return
    path = ["DeepSeek (Brute Force)", "Gemini (Validation)"]
    visualize_anton_reasoning(problem, path, "anton_reasoning_latest")
    print("Generated visual map of Anton's reasoning in anton_reasoning_latest.png")
