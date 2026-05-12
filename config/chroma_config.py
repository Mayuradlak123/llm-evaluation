import os
import chromadb
from dotenv import load_dotenv
from .logger import logger

load_dotenv()

def get_chroma_client():
    try:
        # Connect to Chroma Cloud
        api_key = os.getenv("CHROMA_API_KEY")
        tenant = os.getenv("CHROMA_TENANT")
        database = os.getenv("CHROMA_DATABASE")
        
        if not api_key:
            logger.warning("CHROMA_API_KEY not found in environment. Falling back to local/remote client logic.")
            # Fallback to local/remote if cloud key is missing
            return chromadb.HttpClient(
                host=os.getenv("CHROMA_HOST", "localhost"),
                port=int(os.getenv("CHROMA_PORT", 8000))
            )

        client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )
        
        # Test connection
        client.heartbeat()
        logger.info(f"Successfully connected to Chroma Cloud (Tenant: {tenant}, DB: {database})")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Chroma Cloud: {str(e)}")
        return None

chroma_client = get_chroma_client()
