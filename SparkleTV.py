import os
import shutil
import requests
from hashlib import md5
import logging
from concurrent.futures import ThreadPoolExecutor

# Configurações globais
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = os.path.join(os.getcwd(), "iMPlayer")
TIMEOUT = 10  # Timeout configurável
RETRIES = 3  # Número de tentativas

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_file(url, save_path, retries=RETRIES):
    """Baixa um arquivo e valida sua integridade."""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Tentativa {attempt}/{retries}: {url}")
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if response.status_code == 200:
                with open(save_path, 'wb') as file:
                    file.write(response.content)
                
                if os.path.getsize(save_path) > 0:
                    file_hash = md5(open(save_path, 'rb').read()).hexdigest()
                    logger.info(f"Arquivo salvo: {save_path} | MD5: {file_hash}")
                    return True
                else:
                    logger.error(f"Erro: Arquivo corrompido {save_path}")
            else:
                logger.error(f"Erro {response.status_code}: {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao baixar {url}: {e}")

    return False

def main():
    """Gerencia os downloads."""
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files_to_download = {
        "m3u": {
            "Playlist.m3u": "http://m3u4u.com/m3u/3wk1y24kx7uzdevxygz7",
            "PiauiTV.m3u": "http://m3u4u.com/m3u/jq2zy9epr3bwxmgwyxr5",
            "M3U_FILE.m3u": "http://m3u4u.com/m3u/782dyqdrqkh1xegen4zp",
            "Playlists.m3u": "https://gitlab.com/josieljefferson12/playlists/-/raw/main/m3u4u_proton.me.m3u",
            "PITV.m3u": "https://gitlab.com/josieljefferson12/playlists/-/raw/main/PiauiTV.m3u"
        },
        "xml.gz": {
            "Playlist.epg.xml": "http://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
            "PiauiTV.epg.xml": "http://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
            "M3U_FILE.epg.xml": "http://m3u4u.com/epg/782dyqdrqkh1xegen4zp"
        }
    }

    logger.info("Iniciando downloads...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(download_file, url, os.path.join(OUTPUT_DIR, filename)): filename
            for ext, files in files_to_download.items()
            for filename, url in files.items()
        }

        for future in futures:
            if not future.result():
                logger.error(f"Falha ao baixar {futures[future]}")

    logger.info("Downloads finalizados.")

if __name__ == "__main__":
    main()
