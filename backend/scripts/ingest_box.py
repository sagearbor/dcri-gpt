#!/usr/bin/env python
"""
Box Document Ingestion Script

Usage:
    python -m scripts.ingest_box --folder-id 0 --max-files 100
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import os

sys.path.append(str(Path(__file__).parent.parent))

from app.tools.box_tool import BoxRAGTool
from app.core.config import settings
from boxsdk import OAuth2, Client
from boxsdk.exception import BoxAPIException
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BoxIngester:
    def __init__(self, client_id: str, client_secret: str, enterprise_id: str, jwt_key_id: str, rsa_private_key: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.enterprise_id = enterprise_id
        self.jwt_key_id = jwt_key_id
        self.rsa_private_key = rsa_private_key
        self.client = None
    
    def authenticate(self):
        """Authenticate with Box API using JWT"""
        try:
            from boxsdk import JWTAuth
            
            auth = JWTAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                enterprise_id=self.enterprise_id,
                jwt_key_id=self.jwt_key_id,
                rsa_private_key=self.rsa_private_key
            )
            
            self.client = Client(auth)
            
            # Test authentication
            current_user = self.client.user().get()
            logger.info(f"Successfully authenticated as: {current_user.name}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def list_documents(self, folder_id: str = "0", max_files: int = 100) -> List[Dict]:
        """List all documents in a Box folder"""
        try:
            folder = self.client.folder(folder_id)
            documents = []
            
            # Get folder info
            folder_info = folder.get()
            logger.info(f"Scanning folder: {folder_info.name}")
            
            # Iterate through items
            items = folder.get_items(limit=max_files)
            
            for item in items:
                if item.type == 'file':
                    file_info = self.client.file(item.id).get()
                    documents.append({
                        "file_id": file_info.id,
                        "file_name": file_info.name,
                        "file_type": file_info.extension or "unknown",
                        "folder_path": self._get_folder_path(file_info.parent),
                        "owner": file_info.owned_by.name if file_info.owned_by else "unknown",
                        "modified_date": file_info.modified_at,
                        "size": file_info.size
                    })
                elif item.type == 'folder':
                    # Recursively scan subfolders
                    subdocs = self.list_documents(item.id, max_files - len(documents))
                    documents.extend(subdocs)
                    if len(documents) >= max_files:
                        break
            
            logger.info(f"Found {len(documents)} documents")
            return documents[:max_files]
            
        except BoxAPIException as e:
            logger.error(f"Box API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    def _get_folder_path(self, folder) -> str:
        """Get the full path of a folder"""
        try:
            path_parts = []
            current = folder
            while current and current.id != "0":
                folder_info = self.client.folder(current.id).get()
                path_parts.append(folder_info.name)
                current = folder_info.parent
            
            return "/" + "/".join(reversed(path_parts)) if path_parts else "/"
        except:
            return "/"
    
    def download_document_content(self, file_id: str) -> str:
        """Download the content of a document"""
        try:
            file = self.client.file(file_id)
            
            # For text-based files, get content directly
            try:
                content = file.content()
                return content.decode('utf-8')
            except:
                # For other files, try to get text representation
                try:
                    # Try to get text representation if available
                    representations = file.get_representations()
                    for rep in representations:
                        if rep.representation == 'text':
                            return rep.content
                except:
                    pass
                
                # Return metadata as fallback
                file_info = file.get()
                return f"[File: {file_info.name}, Type: {file_info.extension}, Size: {file_info.size} bytes]"
                
        except Exception as e:
            logger.error(f"Error downloading document {file_id}: {e}")
            return ""
    
    async def ingest_to_vector_store(self, documents: List[Dict]):
        """Ingest documents into the vector store"""
        try:
            # Initialize the Box RAG tool
            tool = BoxRAGTool(config={"folder_id": documents[0].get("folder_id") if documents else None})
            
            if not tool.validate_config():
                logger.error("Box RAG Tool validation failed")
                return False
            
            # Prepare documents for ingestion
            docs_to_ingest = []
            for doc in documents:
                content = self.download_document_content(doc["file_id"])
                if content:
                    docs_to_ingest.append({
                        "file_id": doc["file_id"],
                        "file_name": doc["file_name"],
                        "content": content,
                        "file_type": doc["file_type"],
                        "folder_path": doc["folder_path"],
                        "owner": doc["owner"],
                        "modified_date": doc["modified_date"]
                    })
                    logger.info(f"Prepared document: {doc['file_name']}")
            
            if docs_to_ingest:
                success = await tool.ingest_documents(docs_to_ingest)
                if success:
                    logger.info(f"Successfully ingested {len(docs_to_ingest)} documents")
                else:
                    logger.error("Failed to ingest documents")
                return success
            else:
                logger.warning("No documents to ingest")
                return False
                
        except Exception as e:
            logger.error(f"Error during ingestion: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Ingest Box documents into vector store")
    parser.add_argument("--folder-id", default="0", help="Box folder ID to ingest (0 for root)")
    parser.add_argument("--max-files", type=int, default=100, help="Maximum number of files to ingest")
    parser.add_argument("--client-id", help="Box client ID (or set BOX_CLIENT_ID env var)")
    parser.add_argument("--client-secret", help="Box client secret (or set BOX_CLIENT_SECRET env var)")
    parser.add_argument("--enterprise-id", help="Box enterprise ID (or set BOX_ENTERPRISE_ID env var)")
    parser.add_argument("--jwt-key-id", help="Box JWT key ID (or set BOX_JWT_KEY_ID env var)")
    parser.add_argument("--rsa-private-key-file", help="Path to RSA private key file")
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    client_id = args.client_id or os.getenv("BOX_CLIENT_ID") or settings.BOX_CLIENT_ID
    client_secret = args.client_secret or os.getenv("BOX_CLIENT_SECRET") or settings.BOX_CLIENT_SECRET
    enterprise_id = args.enterprise_id or os.getenv("BOX_ENTERPRISE_ID") or settings.BOX_ENTERPRISE_ID
    jwt_key_id = args.jwt_key_id or os.getenv("BOX_JWT_KEY_ID")
    
    # Read RSA private key
    rsa_private_key = None
    if args.rsa_private_key_file:
        try:
            with open(args.rsa_private_key_file, 'r') as f:
                rsa_private_key = f.read()
        except Exception as e:
            logger.error(f"Failed to read RSA private key: {e}")
            return 1
    else:
        rsa_private_key = os.getenv("BOX_RSA_PRIVATE_KEY")
    
    if not all([client_id, client_secret, enterprise_id, jwt_key_id, rsa_private_key]):
        logger.error("Missing Box credentials. Please provide all required authentication parameters")
        return 1
    
    logger.info(f"Starting Box ingestion from folder {args.folder_id}")
    
    ingester = BoxIngester(client_id, client_secret, enterprise_id, jwt_key_id, rsa_private_key)
    
    # Authenticate
    if not ingester.authenticate():
        logger.error("Authentication failed")
        return 1
    
    # List documents
    documents = ingester.list_documents(args.folder_id, args.max_files)
    if not documents:
        logger.warning("No documents found")
        return 0
    
    # Ingest documents
    success = await ingester.ingest_to_vector_store(documents)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)