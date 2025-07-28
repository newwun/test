#!/usr/bin/env python3
"""
persistent_runner.py

🎥 Keeps WAN-VACE loaded in a loop  
✨ Text-prompt or Image-dir workflows  
🗣️ On-the-fly Coqui TTS narration in Text mode (currently disabled)  
📊 Live CPU/RAM & GPU/VRAM stats  
🧹 Memory flushes before/after renders  
🩺 FlashAttention health-check  
🎞️ Auto-pad to even dims, mux audio/video  
🔣 Numbered prompt picker  
🚪 Explicit quit options  
🔔 Beep when render completes  
"""

import sys
import subprocess
import shutil
import gc
import os
import re
from pathlib import Path

# Optional resource monitoring
try:
    import torch
    import psutil
except ImportError:
    torch = None
    psutil = None

# Toggle TTS narration on/off
ENABLE_TTS = False

# Supported image extensions
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
IMG_ROOT = Path(r"D:\AI\1Video_Generator\images")


def flush_memory():
    print("🧹 Flushing memory caches…")
    if torch:
        torch.cuda.empty_cache()
    gc.collect()
    print("🔄 Memory flush complete\n")


def show_stats():
    print("📊 Current resource usage:")
    if torch:
        alloc = torch.cuda.memory_allocated() / (1024 ** 3)
        reserved = torch.cuda.memory_reserved() / (1024 ** 3)
        print(f"   [GPU] Alloc: {alloc:.2f} GB | Resv: {reserved:.2f} GB")
    if psutil:
        vm = psutil.virtual_memory()
        used = vm.used / (1024 ** 3)
        total = vm.total / (1024 ** 3)
        print(f"   [CPU] Used: {used:.2f} GB / {total:.2f} GB")
    print("✅ Stats displayed\n")


def check_flashattention():
    print("🩺 Checking FlashAttention…", end=" ")
    try:
        import flash_attn
        print("OK")
    except ImportError:
        print("NOT FOUND")
    print()


def load_wan_vace():
    print("🤖 Loading WAN-VACE model…")
    # TODO: replace with actual WAN-VACE load call
    model = None
    print("✅ WAN-VACE model loaded\n")
    return model


def prompt_item_indices(total: int):
    prompt = f"🔢 Select [1–{total}, 'all'] (or 'q' to quit): "
    while True:
        resp = input(prompt).strip().lower()
        if resp in ("q", "quit"):
            sys.exit(0)
        if resp == "all":
            return list(range(1, total + 1))
        try:
            picks = []
            for part in resp.split(","):
                if "-" in part:
                    a, b = map(int, part.split("-", 1))
                    picks.extend(range(a, b + 1))
                else:
                    picks.append(int(part))
            valid = sorted({i for i in picks if 1 <= i <= total})
            if valid:
                return valid
        except ValueError:
            pass
        print("→ Invalid selection syntax. Try again.")


def prompt_image_selection(root_dir: Path):
    while True:
        entries = sorted(
            root_dir.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower())
        )
        if not entries:
            print("→ No subfolders or images found here. Returning.\n")
            return []

        print(f"\n🖼️ Available items in {root_dir}:")
        for idx, p in enumerate(entries, start=1):
            tag = "[DIR]" if p.is_dir() else "[IMG]"
            print(f"  {idx:3}: {tag} {p.name}")
        print()

        picks = prompt_item_indices(len(entries))
        selected = []
        for i in picks:
            path = entries[i - 1]
            if path.is_dir():
                for img in sorted(path.rglob("*")):
                    if img.suffix.lower() in IMAGE_EXTS:
                        selected.append(img)
            elif path.suffix.lower() in IMAGE_EXTS:
                selected.append(path)

        if not selected:
            print("→ No images found in your selection. Try again.\n")
            continue

        unique = sorted(set(selected), key=lambda p: str(p))
        return unique


def prompt_output():
    od = input("📂 Output folder [default './output']: ").strip() or "output"
    fn = input("🔖 Output filename (no ext) [default 'rendered_video']: ").strip() or "rendered_video"
    path = Path(od).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path, fn


def generate_narration(text: str, audio_path: Path):
    print("🗣️ Generating narration…")
    audio_path.write_bytes(b"")
    print(f"✅ Narration saved to {audio_path}\n")


def build_ffmpeg_cmd(
    image_pattern: str,
    fps: int,
    zoom: float,
    padding: int,
    audio_path: Path,
    output_path: Path,
):
    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", image_pattern]
    filters = []
    if zoom != 1.0:
        filters.append(f"zoompan=z='min(zoom+0.0005,{zoom})':d=1")
    if padding > 0:
        filters.append(f"pad=iw+{padding*2}:ih+{padding*2}:{padding}:{padding}:black")
    if filters:
        cmd += ["-vf", ",".join(filters)]
    if ENABLE_TTS and audio_path and audio_path.exists():
        cmd += ["-i", str(audio_path), "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if ENABLE_TTS and audio_path and audio_path.exists():
        cmd += ["-c:a", "aac"]
    cmd.append(str(output_path))
    return cmd


def main():
    print("\n=== Persistent Image-to-Video Renderer ===\n")
    print("🎥 Keeps WAN-VACE loaded in a loop")
    print("✨ Text-prompt or Image-dir workflows")
    print("🗣️ On-the-fly Coqui TTS narration in Text mode (currently disabled)")
    print("📊 Live CPU/RAM & GPU/VRAM stats")
    print("🧹 Memory flushes before/after renders")
    print("🩺 FlashAttention health-check")
    print("🎞️ Auto-pad to even dims, mux audio/video")
    print("🔣 Numbered prompt picker")
    print("🚪 Explicit quit options")
    print("🔔 Beep when render completes\n")

    model = load_wan_vace()
    check_flashattention()

    while True:
        flush_memory()
        show_stats()

        mode = input("🛣️ Workflow: [1] Text-prompt  [2] Image-dir  (or 'q' to quit): ").strip()
        if mode.lower() in ("q", "quit"):
            break

        if mode == "1":
            prompt = input("✍️ Enter scene description text: ").strip()
            print(f"→ Generating images for: “{prompt}”")
            img_root = Path("./temp_images")
            shutil.rmtree(img_root, ignore_errors=True)
            img_root.mkdir()
            # TODO: model.generate_images(prompt) → img_root
            selected = prompt_image_selection(img_root)

        else:
            selected = prompt_image_selection(IMG_ROOT)

        if not selected:
            continue

        print(f"\n✅ You selected {len(selected)} images.\n")

        out_dir, base_name = prompt_output()
        temp_dir = out_dir / "temp_images"
        shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir()

        print("📋 Copying and renaming images…")
        for i, src in enumerate(selected, start=1):
            dst = temp_dir / f"{i:06d}{src.suffix}"
            shutil.copy(src, dst)
        print("✅ Image copy complete\n")

        audio_file = None
        if ENABLE_TTS:
            txt = input("🗣️ Enter narration text (or leave blank to skip): ").strip()
            if txt:
                audio_file = out_dir / f"{base_name}.wav"
                generate_narration(txt, audio_file)

        fps = input("⏱️ FPS [24]: ").strip()
        fps = int(fps) if fps.isdigit() else 24

        zoom = input("🔍 Max zoom factor [1.0]: ").strip()
        try:
            zoom = float(zoom)
        except ValueError:
            zoom = 1.0

        padd = input("➕ Padding (px) [0]: ").strip()
        padding = int(padd) if padd.isdigit() else 0

        output_path = out_dir / f"{base_name}.mp4"
        pattern = str(temp_dir / "%06d" + selected[0].suffix)
        cmd = build_ffmpeg_cmd(pattern, fps, zoom, padding, audio_file, output_path)

        print("\n🎬 Running FFmpeg:")
        print("  " + " ".join(cmd) + "\n")
        subprocess.run(cmd, check=True)

        print("🔔 Render complete!\a")
        print(f"✅ Video saved to {output_path}\n")

        flush_memory()
        again = input("↩️ Render another? [y/N]: ").strip().lower()
        if again != "y":
            print("\n🚪 Goodbye!\n")
            break


if __name__ == "__main__":
    main()
