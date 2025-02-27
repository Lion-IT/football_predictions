import os
import shutil

def clean_folder(folder_path):
    """
    Usuwa wszystkie pliki i podfoldery z danego folderu.
    :param folder_path: Ścieżka do folderu, który ma zostać wyczyszczony.
    """
    if not os.path.exists(folder_path):
        print(f"Folder {folder_path} nie istnieje.")
        return

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            # Usuwa pliki
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            # Usuwa foldery
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Błąd podczas usuwania {file_path}: {e}")