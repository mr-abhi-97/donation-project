import os
import shutil
from PIL import Image

def generate_icons():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    source_png = os.path.join(workspace_dir, "app_icon.png")
    dest_ico = os.path.join(workspace_dir, "app_icon.ico")
    
    if not os.path.exists(source_png):
        raise FileNotFoundError(f"Source icon not found at {source_png}")
        
    print(f"Loading base logo from: {source_png}")
    im = Image.open(source_png).convert("RGBA")
    print(f"Original size: {im.size}, Mode: {im.mode}")
    
    # Square padding to maintain crisp aspect ratio without stretching
    max_dim = max(im.width, im.height)
    square_im = Image.new("RGBA", (max_dim, max_dim), (255, 255, 255, 0))
    offset = ((max_dim - im.width) // 2, (max_dim - im.height) // 2)
    square_im.paste(im, offset, im)
    
    # Multi-resolution ICO export for Windows desktop & browser favicons
    icon_resolutions = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    square_im.save(dest_ico, format="ICO", sizes=icon_resolutions)
    print(f"Exported multi-resolution icon to: {dest_ico}")
    print(f"Embedded resolutions: {icon_resolutions}")
    
    # Deploy to Next.js App Router and public directories
    deploy_targets = [
        os.path.join(workspace_dir, "frontend", "src", "app", "icon.png"),
        os.path.join(workspace_dir, "frontend", "public", "app_icon.png"),
        os.path.join(workspace_dir, "frontend", "public", "icon.png"),
    ]
    for target in deploy_targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(source_png, target)
        print(f"Deployed PNG icon -> {target}")

    ico_targets = [
        os.path.join(workspace_dir, "frontend", "src", "app", "favicon.ico"),
        os.path.join(workspace_dir, "frontend", "public", "favicon.ico"),
    ]
    for target in ico_targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(dest_ico, target)
        print(f"Deployed ICO icon -> {target}")

    print("\nAll icon assets generated and deployed successfully!")

if __name__ == "__main__":
    generate_icons()
