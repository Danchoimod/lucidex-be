import re
from pathlib import Path

def bump_version():
    main_py_path = Path(__file__).parent / "backend" / "src" / "main.py"
    if not main_py_path.exists():
        # Fallback path if script is inside backend directory
        main_py_path = Path(__file__).parent / "src" / "main.py"

    content = main_py_path.read_text(encoding="utf-8")
    
    # Regex to find version="x.y.z"
    match = re.search(r'version="(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("❌ Could not find version string in main.py")
        return

    major, minor, patch = map(int, match.groups())
    new_patch = patch + 1
    new_version = f"{major}.{minor}.{new_patch}"
    
    new_content = re.sub(
        r'version="\d+\.\d+\.\d+"',
        f'version="{new_version}"',
        content
    )
    
    main_py_path.write_text(new_content, encoding="utf-8")
    print(f"🚀 Version bumped from {major}.{minor}.{patch} -> {new_version} in {main_py_path.name}")

if __name__ == "__main__":
    bump_version()
