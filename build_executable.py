import os
import sys
import customtkinter
import PyInstaller.__main__

def build_app():
    """
    Enterprise Build Pipeline.
    Dynamically locates CustomTkinter assets and compiles the SmartSafe v28 executable.
    """
    # Locate the CustomTkinter library to bundle its internal themes and fonts
    ctk_path = os.path.dirname(customtkinter.__file__)
    # The source path should be the customtkinter package directory itself.
    # The destination path inside the bundle should also be 'customtkinter'.
    ctk_data_arg = f"{ctk_path}{os.pathsep}customtkinter"
    
    print("[BUILD] Initiating SmartSafe v28 Production Build...")
    
    PyInstaller.__main__.run([
        'main.py',
        '--name=SmartSafe_v28',
        '--windowed', # Suppress terminal console in production
        f'--add-data={ctk_data_arg}', # Corrected path for CustomTkinter assets
        '--hidden-import=bcrypt',                         # Auth module
        '--hidden-import=cryptography',                   # E2EE module
        '--noconfirm',          # Automatically overwrite previous builds
    ])

if __name__ == "__main__":
    build_app()