#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


class SourceMapExtractorError(Exception):
    pass


def load_sourcemap_from_file(file_path: str) -> dict:
    path = Path(file_path)

    if not path.is_file():
        raise SourceMapExtractorError(f"Arquivo não encontrado: {file_path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_sourcemap_from_url(url: str) -> dict:
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise SourceMapExtractorError("A URL deve usar http ou https")

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")

            if response.status != 200:
                raise SourceMapExtractorError(f"HTTP status inválido: {response.status}")

            raw_data = response.read()

    except Exception as exc:
        raise SourceMapExtractorError(f"Erro ao baixar sourcemap: {exc}") from exc

    try:
        return json.loads(raw_data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceMapExtractorError("Resposta não contém JSON válido") from exc


def safe_join(base_dir: Path, unsafe_path: str) -> Path:
    """
    Trata o diretório de output como raiz.

    Exemplos:
    /home/user/app/src/main.ts
      -> <output>/home/user/app/src/main.ts

    ../node_modules/pkg/file.js
      -> <output>/node_modules/pkg/file.js

    ../../src/app/file.ts
      -> <output>/src/app/file.ts
    """

    normalized = unsafe_path.replace("\\", "/").strip()

    if not normalized:
        raise SourceMapExtractorError("Path vazio ignorado")

    if "://" in normalized:
        raise SourceMapExtractorError(f"Path com scheme ignorado: {unsafe_path}")

    # Paths absolutos passam a ser relativos ao output.
    normalized = normalized.lstrip("/")

    parts = []

    for part in normalized.split("/"):
        if part in {"", "."}:
            continue

        # Em sourcemaps, ../ costuma ser path lógico relativo ao bundle.
        # Para extração segura, descartamos o salto para cima e mantemos
        # o restante dentro do diretório de output.
        if part == "..":
            continue

        # Bloqueia paths Windows absolutos: C:/Users/...
        if part.endswith(":"):
            raise SourceMapExtractorError(f"Path Windows absoluto bloqueado: {unsafe_path}")

        parts.append(part)

    if not parts:
        raise SourceMapExtractorError(f"Path inválido ignorado: {unsafe_path}")

    candidate = base_dir.joinpath(*parts).resolve()
    base_resolved = base_dir.resolve()

    try:
        candidate.relative_to(base_resolved)
    except ValueError:
        raise SourceMapExtractorError(f"Path traversal bloqueado: {unsafe_path}")

    return candidate


def extract_sources(sourcemap: dict, output_dir: str) -> int:
    output_base = Path(output_dir).resolve()
    output_base.mkdir(parents=True, exist_ok=True)

    sources = sourcemap.get("sources")
    sources_content = sourcemap.get("sourcesContent")

    if not isinstance(sources, list):
        raise SourceMapExtractorError("Sourcemap inválido: campo 'sources' ausente ou inválido")

    if not isinstance(sources_content, list):
        raise SourceMapExtractorError("Sourcemap inválido: campo 'sourcesContent' ausente ou inválido")

    if len(sources) != len(sources_content):
        raise SourceMapExtractorError(
            "Sourcemap inválido: 'sources' e 'sourcesContent' possuem tamanhos diferentes"
        )

    extracted = 0

    for source_path, source_content in zip(sources, sources_content):
        if not isinstance(source_path, str):
            continue

        if source_content is None:
            continue

        if not isinstance(source_content, str):
            source_content = str(source_content)

        try:
            destination = safe_join(output_base, source_path)
        except SourceMapExtractorError as exc:
            print(f"[WARN] {exc}", file=sys.stderr)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("w", encoding="utf-8", newline="") as f:
            f.write(source_content)

        extracted += 1
        print(f"[OK] {destination}")

    return extracted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrai arquivos originais de um .js.map para um diretório seguro."
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", help="Caminho local para o arquivo .js.map")
    input_group.add_argument("--url", help="URL HTTP/HTTPS do arquivo .js.map")

    parser.add_argument(
        "--output",
        required=True,
        help="Diretório onde os arquivos extraídos serão gravados",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.file:
            sourcemap = load_sourcemap_from_file(args.file)
        else:
            sourcemap = load_sourcemap_from_url(args.url)

        total = extract_sources(sourcemap, args.output)
        print(f"\nExtração concluída. Arquivos gravados: {total}")
        return 0

    except json.JSONDecodeError as exc:
        print(f"[ERRO] JSON inválido: {exc}", file=sys.stderr)
        return 1

    except SourceMapExtractorError as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print("\n[ERRO] Execução interrompida pelo usuário", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())