import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import gzip
import io
import logging
from urllib.parse import urlparse
from git import Repo  # Certifique-se de que gitpython está instalado

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# URLs da playlist e EPG
PLAYLIST_URL = "https://gitlab.com/josieljefferson12/playlists/-/raw/main/m3u4u_proton.me.m3u"
EPG_URL = "http://m3u4u.com/epg/3wk1y24kx7uzdevxygz7"

# Configurações do GitHub
GITHUB_REPO = os.getenv("GITHUB_REPO", "josieljefferson12/iMPlayer")
GITHUB_TOKEN = os.getenv("iMPlayer_GITHUB_TOKEN")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
OUTPUT_FILE = "playlist.epg.xml"


def validate_url(url):
    """Valida se uma URL é válida."""
    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])


def download_file(url, file_name):
    """Baixa um arquivo da URL, verifica se está compactado e retorna o conteúdo."""
    if not validate_url(url):
        raise ValueError(f"URL inválida: {url}")

    logging.info(f"Baixando arquivo de {url}...")
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, stream=True)

    if response.status_code != 200:
        raise Exception(f"Erro ao baixar arquivo: {url}, Status: {response.status_code}")

    content = response.content
    if content[:2] == b'\x1f\x8b':  # Verifica se é Gzip
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                content = gz.read().decode("utf-8")
        except OSError:
            raise Exception("Erro ao descompactar Gzip.")
    else:
        content = content.decode("utf-8")

    with open(file_name, "w", encoding="utf-8") as file:
        file.write(content)

    logging.info(f"Arquivo salvo: {file_name}")
    return content


def parse_epg(epg_xml):
    """Processa o XML do EPG e retorna um dicionário com os programas por canal."""
    logging.info("Processando EPG...")
    try:
        context = ET.iterparse(io.StringIO(epg_xml), events=("start", "end"))
        context = iter(context)
        event, root = next(context)

        epg_data = {}
        for event, elem in context:
            if event == "end" and elem.tag == "programme":
                channel = elem.get("channel")
                start = elem.get("start")
                stop = elem.get("stop")
                title = elem.findtext("title", "Sem título")
                desc = elem.findtext("desc", "")

                if channel not in epg_data:
                    epg_data[channel] = []

                epg_data[channel].append({"start": start, "stop": stop, "title": title, "description": desc})
                root.clear()  # Limpa elementos processados para economizar memória

        return epg_data
    except ET.ParseError as e:
        raise Exception(f"Erro ao processar XML: {e}")


def generate_epg_xml(playlist, epg_data):
    """Gera um novo XML baseado no EPG baixado."""
    logging.info("Gerando EPG atualizado...")
    root = ET.Element("tv")
    channels = playlist.strip().split("\n")

    for i in range(0, len(channels), 2):
        if not channels[i].startswith("#EXTINF:"):
            continue

        channel_info = channels[i].split(",")
        channel_name = channel_info[-1].strip()

        tvg_id = None
        for part in channel_info[0].split(" "):
            if part.startswith("tvg-id="):
                tvg_id = part.split('"')[1]
                break

        if not tvg_id or tvg_id not in epg_data:
            continue

        channel_elem = ET.SubElement(root, "channel", id=tvg_id)
        ET.SubElement(channel_elem, "display-name").text = channel_name

        for program in epg_data[tvg_id]:
            programme_elem = ET.SubElement(
                root, "programme", start=program["start"], stop=program["stop"], channel=tvg_id
            )
            ET.SubElement(programme_elem, "title").text = program["title"]
            ET.SubElement(programme_elem, "desc").text = program["description"]

    return ET.tostring(root, encoding="utf-8", method="xml").decode("utf-8")


def push_to_github(file_content, file_name):
    """Faz commit e push do EPG atualizado no GitHub."""
    logging.info("Enviando para o GitHub...")
    repo_dir = "repo"
    repo_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"

    if os.path.exists(repo_dir):
        repo = Repo(repo_dir)
    else:
        repo = Repo.clone_from(repo_url, repo_dir)

    file_path = os.path.join(repo_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(file_content)

    repo.git.add(file_name)
    repo.index.commit(f"Atualização automática do EPG em {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    repo.remote(name="origin").push(refspec=f"{GITHUB_BRANCH}:{GITHUB_BRANCH}")

    logging.info("Push concluído!")


if __name__ == "__main__":
    try:
        logging.info("Iniciando processo de atualização do EPG...")

        playlist = download_file(PLAYLIST_URL, "playlist.m3u")
        epg_xml = download_file(EPG_URL, "playlist.epg.xml")

        epg_data = parse_epg(epg_xml)
        epg_final_xml = generate_epg_xml(playlist, epg_data)

        push_to_github(epg_final_xml, OUTPUT_FILE)

        logging.info("Processo concluído com sucesso!")
    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
