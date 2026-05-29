import gradio as gr
import os
import subprocess
import sys
import shutil

# Facefusion path relative to this script
AMTCE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACEFUSION_DIR = os.path.join(AMTCE_ROOT, "models", "facefusion")
FACEFUSION_SCRIPT = os.path.join(FACEFUSION_DIR, "facefusion.py")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def swap_face(source_image, target_media, provider):
    if not source_image or not target_media:
        yield None, "Please upload both a source face and a target image/video."
        return
    
    if not os.path.isfile(FACEFUSION_SCRIPT):
        yield None, f"Could not find facefusion.py at: {FACEFUSION_SCRIPT}"
        return

    # Get file extension of target media
    ext = os.path.splitext(target_media)[1]
    
    # Generate an output file path
    output_filename = f"swapped_output{ext}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    # Remove existing output if it exists to avoid confusion
    if os.path.exists(output_path):
        os.remove(output_path)
    
    cmd = [
        sys.executable, FACEFUSION_SCRIPT, "headless-run",
        "--execution-providers", provider,
        "--log-level", "debug",
        "-s", source_image,
        "-t", target_media,
        "-o", output_path
    ]
    
    # If using GPU, we can enable the enhancer safely
    if provider == "cuda":
        cmd.extend(["--processors", "face_swapper", "face_enhancer"])
    else:
        # Default CPU mode
        cmd.extend([
            "--processors", "face_swapper"
        ])

    yield None, f"Starting FaceFusion with {provider} provider...\n"
    logs = f"Starting FaceFusion with {provider} provider...\n"

    try:
        # Run process and stream output
        process = subprocess.Popen(
            cmd,
            cwd=FACEFUSION_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Read line by line and yield updates to Gradio UI
        for line in iter(process.stdout.readline, ''):
            logs += line
            # Keep logs reasonably sized for UI (last 200 lines)
            log_lines = logs.split('\n')
            if len(log_lines) > 200:
                logs = '\n'.join(log_lines[-200:])
            yield None, logs
            
        process.stdout.close()
        return_code = process.wait(timeout=1200)
        
        if return_code == 0 and os.path.isfile(output_path):
            logs += "\nSuccess! Check your swapped media."
            yield output_path, logs
        else:
            logs += f"\nError (Code {return_code})"
            yield None, logs
            
    except subprocess.TimeoutExpired:
        yield None, logs + "\nProcess timed out. Video might be too long."
    except Exception as e:
        yield None, logs + f"\nAn error occurred: {str(e)}"

# Gradio Interface
with gr.Blocks(title="AMTCE Face Swapper") as app:
    gr.Markdown("# AMTCE Face Swapper")
    gr.Markdown("Standalone interface for FaceFusion")
    
    with gr.Row():
        with gr.Column():
            source_face = gr.Image(type="filepath", label="Source Face (The face you want to use)")
            target_media = gr.File(label="Target Image or Video (Where to put the face)")
            provider_dropdown = gr.Dropdown(choices=["cpu", "cuda", "tensorrt"], value="cuda", label="Execution Provider")
            
            swap_button = gr.Button("Swap Face", variant="primary")
            
        with gr.Column():
            output_media = gr.File(label="Swapped Output")
            status_text = gr.Textbox(label="Status / Logs", lines=5)
            
    swap_button.click(
        fn=swap_face,
        inputs=[source_face, target_media, provider_dropdown],
        outputs=[output_media, status_text]
    )

if __name__ == "__main__":    # Detect Colab
    is_colab = "google.colab" in sys.modules
    app.launch(inbrowser=not is_colab, server_port=7865, share=is_colab)
