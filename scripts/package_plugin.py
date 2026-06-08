import argparse
import os
import pathlib
import zipfile


DEFAULT_EXCLUDES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


def should_skip(path):
    return any(part in DEFAULT_EXCLUDES for part in path.parts)


def build_zip(source_dir, output_zip):
    source_dir = pathlib.Path(source_dir).resolve()
    output_zip = pathlib.Path(output_zip).resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_dir() or should_skip(file_path.relative_to(source_dir)):
                continue
            archive_name = pathlib.Path(source_dir.name) / file_path.relative_to(source_dir)
            archive.write(file_path, archive_name.as_posix())

    return output_zip


def main():
    parser = argparse.ArgumentParser(description="Empaqueta el plugin GeoSolar Suitability en un archivo ZIP.")
    parser.add_argument(
        "--source",
        default="solar_site_suitability",
        help="Carpeta fuente del plugin.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join("dist", "solar_site_suitability.zip"),
        help="Ruta del ZIP de salida.",
    )
    args = parser.parse_args()

    output_zip = build_zip(args.source, args.output)
    print(output_zip)


if __name__ == "__main__":
    main()
