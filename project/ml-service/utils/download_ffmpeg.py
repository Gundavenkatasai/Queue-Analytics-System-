import os
import sys
import urllib.request
import zipfile
import shutil
import logging

logger = logging.getLogger(__name__)

def download_ffmpeg():
    """
    Downloads the pre-compiled ffmpeg release essentials zip from gyan.dev
    and extracts only ffmpeg.exe to the ml-service root directory.
    """
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ml_service_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_path = os.path.join(ml_service_dir, "ffmpeg.exe")
    temp_zip = os.path.join(ml_service_dir, "ffmpeg_temp.zip")

    logger.info("=" * 60)
    logger.info("⚡ STARTING AUTOMATIC FFmpeg BINARY DOWNLOAD")
    logger.info(f"Target URL: {url}")
    logger.info(f"Destination: {target_path}")
    logger.info("=" * 60)

    try:
        # Define a custom progress reporter
        def report_progress(block_num, block_size, total_size):
            read_so_far = block_num * block_size
            if total_size > 0:
                percent = min(100, (read_so_far * 100) // total_size)
                sys.stdout.write(f"\rDownloading FFmpeg: {percent}% ({read_so_far // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\rDownloading FFmpeg: {read_so_far // 1024} KB read")
                sys.stdout.flush()

        # Perform the download
        urllib.request.urlretrieve(url, temp_zip, reporthook=report_progress)
        sys.stdout.write("\n")
        logger.info("✓ Download complete. Extracting ffmpeg.exe...")

        # Extract only ffmpeg.exe from the ZIP
        extracted = False
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    logger.info(f"Found ffmpeg.exe in zip: {member}")
                    with zip_ref.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted = True
                    logger.info(f"✓ Successfully extracted ffmpeg.exe to {target_path}")
                    break

        if not extracted:
            logger.error("❌ Could not find ffmpeg.exe inside the downloaded ZIP file.")
            return False

        # Cleanup
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
            logger.info("✓ Temporary ZIP file cleaned up.")

        logger.info("🎉 FFmpeg deployment successful!")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download/extract FFmpeg: {e}")
        if os.path.exists(temp_zip):
            try:
                os.remove(temp_zip)
            except Exception:
                pass
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    download_ffmpeg()
