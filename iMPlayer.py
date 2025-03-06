import os
import shutil
import requests
from hashlib import md5
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações globais
HEADERS = {"User-Agent": "Mozilla/5.0"}
OUTPUT_DIR = os.path.join(os.getcwd(), "iMPlayer")
TIMEOUT = 10  # Timeout configurável
RETRIES = 3  # Número de tentativas de download

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_file(url, save_path, retries=RETRIES):
    """
    Baixa um arquivo da URL fornecida e sobrescreve se já existir.
    """
    for attempt in range(retries):
        try:
            logger.info(f"Tentativa {attempt + 1} de {retries}: Baixando arquivo de: {url}")
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)

            if response.status_code == 200:
                # Garante que o diretório de destino exista
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # Salva o conteúdo do arquivo
                with open(save_path, 'wb') as file:
                    file.write(response.content)
                
                # Verifica se o arquivo foi salvo corretamente
                if os.path.getsize(save_path) > 0:
                    logger.info(f"Arquivo salvo com sucesso: {save_path}")
                    
                    # Calcula o hash MD5 do arquivo
                    with open(save_path, 'rb') as file:
                        file_hash = md5(file.read()).hexdigest()
                    logger.info(f"Hash MD5 do arquivo: {file_hash}")
                    return True
                else:
                    logger.error(f"Erro: Arquivo vazio ou corrompido: {save_path}")
            else:
                logger.error(f"Falha ao baixar {url}. Código: {response.status_code}")
        except requests.exceptions.Timeout:
            logger.error(f"Erro: Timeout ao baixar {url}")
        except requests.exceptions.ConnectionError:
            logger.error(f"Erro: Problema de conexão ao baixar {url}")
        except Exception as e:
            logger.error(f"Erro inesperado ao baixar {url}: {e}")

    logger.error(f"Falha ao baixar {url} após {retries} tentativas.")
    return False

def main():
    # Remove a pasta iMPlayer antes de baixar os arquivos
    logger.info("Limpando diretório anterior...")
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Lista de arquivos para download
    files_to_download = {
        "m3u": [
            "http://m3u4u.com/m3u/3wk1y24kx7uzdevxygz7",
            "http://m3u4u.com/m3u/jq2zy9epr3bwxmgwyxr5",
            "http://m3u4u.com/m3u/782dyqdrqkh1xegen4zp",
            "https://gitlab.com/josieljefferson12/playlists/-/raw/main/PiauiTV.m3u",
            "https://gitlab.com/josieljefferson12/playlists/-/raw/main/m3u4u_proton.me.m3u"
        ],
        "xml.gz": [
            "http://m3u4u.com/epg/3wk1y24kx7uzdevxygz7",
            "http://m3u4u.com/epg/jq2zy9epr3bwxmgwyxr5",
            "http://m3u4u.com/epg/782dyqdrqkh1xegen4zp"
        ]
    }

    # Processa o download dos arquivos
    logger.info("Iniciando download dos arquivos...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for ext, urls in files_to_download.items():
            for index, url in enumerate(urls, start=1):
                save_path = os.path.join(OUTPUT_DIR, f"iMPlayer_{index}.{ext}")
                futures.append(executor.submit(download_file, url, save_path))

        for future in as_completed(futures):
            if not future.result():
                logger.error("Erro durante o download de um arquivo.")

    logger.info("Download concluído.")

if __name__ == "__main__":
    main()
