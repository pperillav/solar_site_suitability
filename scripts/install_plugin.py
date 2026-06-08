import argparse
import os
import pathlib
import shutil


DEFAULT_TARGET = pathlib.Path.home() / "AppData" / "Roaming" / "QGIS" / "QGIS3" / "profiles" / "default" / "python" / "plugins"


def copy_plugin(source_dir, target_dir):
    source_dir = pathlib.Path(source_dir).resolve()
    target_dir = pathlib.Path(target_dir).resolve()
    if not source_dir.exists():
        raise FileNotFoundError(f"No existe la carpeta fuente del plugin: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / source_dir.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source_dir, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return destination


def main():
    parser = argparse.ArgumentParser(description="Instala el plugin GeoSolar Suitability en el perfil local de QGIS.")
    parser.add_argument("--source", default="solar_site_suitability", help="Carpeta fuente del plugin.")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Carpeta destino de plugins de QGIS.")
    args = parser.parse_args()

    destination = copy_plugin(args.source, args.target)
    print(destination)


if __name__ == "__main__":
    main()
