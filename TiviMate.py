import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import gzip
import io
import logging
from urllib.parse import urlparse
from git import Repo

# Configuração de logging
LOG_FILE = "epg_update.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Diretório de saída
OUTPUT_DIR = "iMPlayer"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# URLs da playlist e EPG
PLAYLIST_URLS = {
    "Playlists.m3u": "http://m3u4u.com/m3u/3wk1y24kx7uzdevxygz7",
    "PiauiTV.m3u": "http://m3u4u.com/m3u/jq2zy9epr3bwxmgwyxr5",
    "M3U_FILE.m3u": "http://m3u4u.com/m3u/782dyqdrqkh1xegen4zp"
}
EPG_URLS = {
    "Playlists.epg.xml": "http://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
    "PiauiTV.epg.xml": "http://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
    "M3U_FILE.epg.xml": "http://m3u4u.com/epg/782dyqdrqkh1xegen4zp"
}

# Configurações do GitHub
GITHUB_REPO = os.getenv("GITHUB_REPO", "josieljefferson12/iMPlayer")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")


def validate_url(url):
    """Verifica se a URL é válida e se usa HTTP ou HTTPS"""
    parsed = urlparse(url)
    return parsed.scheme in ["http", "https"] and bool(parsed.netloc)


def download_file(url, file_name):
    """Baixa o arquivo, descompacta se necessário e salva no diretório `iMPlayer`"""
    if not validate_url(url):
        logging.error(f"URL inválida: {url}")
        return None

    file_path = os.path.join(OUTPUT_DIR, file_name)
    logging.info(f"Baixando {file_name} de {url}...")

    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Erro ao baixar {url}: {e}")
        return None

    content = response.content
    if content[:2] == b'\x1f\x8b':  # Verifica se é um arquivo Gzip
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                content = gz.read().decode("utf-8")
        except OSError:
            logging.error("Erro ao descompactar Gzip.")
            return None
    else:
        content = content.decode("utf-8")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

    logging.info(f"Arquivo salvo: {file_path}")
    return content


def parse_epg(epg_xml):
    """Processa XML do EPG e retorna um dicionário com os programas"""
    logging.info("Processando EPG...")
    epg_data = {}

    try:
        context = ET.iterparse(io.StringIO(epg_xml), events=("start", "end"))
        _, root = next(context)

        for event, elem in context:
            if event == "end" and elem.tag == "programme":
                channel = elem.get("channel")
                title = elem.findtext("title", "Sem título")
                desc = elem.findtext("desc", "")
                start = elem.get("start")
                stop = elem.get("stop")

                if channel:
                    epg_data.setdefault(channel, []).append({
                        "start": start, "stop": stop, "title": title, "description": desc
                    })

                root.clear()  # Economiza memória

        return epg_data
    except ET.ParseError as e:
        logging.error(f"Erro ao processar XML: {e}")
        return {}


def push_to_github(file_name):
    """Commit e push para o GitHub se houver mudanças"""
    logging.info("Verificando atualizações no GitHub...")

    repo_dir = "."
    repo = Repo(repo_dir)
    file_path = os.path.join(OUTPUT_DIR, file_name)

    # Verifica se há mudanças antes de fazer commit
    repo.git.add(file_path)
    if repo.is_dirty(untracked_files=True):
        repo.index.commit(f"Atualização automática do EPG - {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        repo.remote("origin").push(refspec=f"{GITHUB_BRANCH}:{GITHUB_BRANCH}")
        logging.info(f"Push realizado para {file_name}")
    else:
        logging.info(f"Nenhuma alteração detectada em {file_name}, push não necessário.")


if __name__ == "__main__":
    try:
        logging.info("Iniciando atualização do EPG...")

        for file_name, playlist_url in PLAYLIST_URLS.items():
            epg_file = file_name.replace(".m3u", ".epg.xml")
            epg_url = EPG_URLS.get(epg_file)
            if not epg_url:
                logging.warning(f"EPG não encontrado para {file_name}")
                continue

            download_file(playlist_url, file_name)
            epg_content = download_file(epg_url, epg_file)

            if epg_content:
                parse_epg(epg_content)
                push_to_github(epg_file)

        logging.info("Processo concluído com sucesso!")
    except Exception as e:
        logging.error(f"Erro durante execução: {e}")
