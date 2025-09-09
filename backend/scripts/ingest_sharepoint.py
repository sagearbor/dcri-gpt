#!/usr/bin/env python
"""
SharePoint Document Ingestion Script

Usage:
    python -m scripts.ingest_sharepoint --site-url https://yourorg.sharepoint.com/sites/yoursite --folder /Shared%20Documents
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
import os

sys.path.append(str(Path(__file__).parent.parent))

from app.tools.sharepoint_tool import SharePointRAGTool
from app.core.config import settings
import requests
from msal import ConfidentialClientApplication
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SharePointIngester:
    def __init__(self, site_url: str, client_id: str, client_secret: str, tenant_id: str):
        self.site_url = site_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
    
    def authenticate(self):
        """Authenticate with Microsoft Graph API"""
        try:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            
            app = ConfidentialClientApplication(
                self.client_id,
                authority=authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Successfully authenticated with Microsoft Graph")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_site_id(self) -> str:
        """Get the SharePoint site ID from the site URL"""
        try:
            site_path = self.site_url.replace("https://", "").replace("http://", "")
            domain = site_path.split("/")[0]
            site_name = "/".join(site_path.split("/")[1:])
            
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                f"{self.graph_base_url}/sites/{domain}:/{site_name}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()["id"]
            else:
                logger.error(f"Failed to get site ID: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting site ID: {e}")
            return None
    
    def list_documents(self, site_id: str, folder_path: str = "/Shared%20Documents") -> List[Dict]:
        """List all documents in a SharePoint folder"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Get drive ID
            drive_response = requests.get(
                f"{self.graph_base_url}/sites/{site_id}/drive",
                headers=headers
            )
            
            if drive_response.status_code != 200:
                logger.error(f"Failed to get drive: {drive_response.text}")
                return []
            
            drive_id = drive_response.json()["id"]
            
            # List items in folder
            items_response = requests.get(
                f"{self.graph_base_url}/drives/{drive_id}/root:{folder_path}:/children",
                headers=headers
            )
            
            if items_response.status_code != 200:
                logger.error(f"Failed to list items: {items_response.text}")
                return []
            
            documents = []
            for item in items_response.json().get("value", []):
                if "file" in item:  # It's a file, not a folder
                    documents.append({
                        "id": item["id"],
                        "name": item["name"],
                        "web_url": item["webUrl"],
                        "modified_date": item["lastModifiedDateTime"],
                        "size": item["size"]
                    })
            
            logger.info(f"Found {len(documents)} documents in {folder_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    def download_document_content(self, site_id: str, document_id: str) -> str:
        """Download the content of a document"""
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            # Get drive ID
            drive_response = requests.get(
                f"{self.graph_base_url}/sites/{site_id}/drive",
                headers=headers
            )
            
            if drive_response.status_code != 200:
                return ""
            
            drive_id = drive_response.json()["id"]
            
            # Download content
            content_response = requests.get(
                f"{self.graph_base_url}/drives/{drive_id}/items/{document_id}/content",
                headers=headers
            )
            
            if content_response.status_code == 200:
                # For text files, decode content
                try:
                    return content_response.content.decode('utf-8')
                except:
                    # For binary files, you might want to use a document parser
                    return f"[Binary content - {len(content_response.content)} bytes]"
            else:
                logger.error(f"Failed to download document: {content_response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error downloading document: {e}")
            return ""
    
    async def ingest_to_vector_store(self, documents: List[Dict], site_id: str):
        """Ingest documents into the vector store"""
        try:
            # Initialize the SharePoint RAG tool
            tool = SharePointRAGTool(config={"site_url": self.site_url})
            
            if not tool.validate_config():
                logger.error("SharePoint RAG Tool validation failed")
                return False
            
            # Prepare documents for ingestion
            docs_to_ingest = []
            for doc in documents:
                content = self.download_document_content(site_id, doc["id"])
                if content:
                    docs_to_ingest.append({
                        "id": doc["id"],
                        "title": doc["name"],
                        "content": content,
                        "source": doc["web_url"],
                        "modified_date": doc["modified_date"]
                    })
                    logger.info(f"Prepared document: {doc['name']}")
            
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
    parser = argparse.ArgumentParser(description="Ingest SharePoint documents into vector store")
    parser.add_argument("--site-url", required=True, help="SharePoint site URL")
    parser.add_argument("--folder", default="/Shared%20Documents", help="Folder path to ingest")
    parser.add_argument("--client-id", help="SharePoint client ID (or set SHAREPOINT_CLIENT_ID env var)")
    parser.add_argument("--client-secret", help="SharePoint client secret (or set SHAREPOINT_CLIENT_SECRET env var)")
    parser.add_argument("--tenant-id", help="SharePoint tenant ID (or set SHAREPOINT_TENANT_ID env var)")
    
    args = parser.parse_args()
    
    # Get credentials from args or environment
    client_id = args.client_id or os.getenv("SHAREPOINT_CLIENT_ID") or settings.SHAREPOINT_CLIENT_ID
    client_secret = args.client_secret or os.getenv("SHAREPOINT_CLIENT_SECRET") or settings.SHAREPOINT_CLIENT_SECRET
    tenant_id = args.tenant_id or os.getenv("SHAREPOINT_TENANT_ID") or settings.SHAREPOINT_TENANT_ID
    
    if not all([client_id, client_secret, tenant_id]):
        logger.error("Missing SharePoint credentials. Please provide client-id, client-secret, and tenant-id")
        return 1
    
    logger.info(f"Starting SharePoint ingestion from {args.site_url}")
    
    ingester = SharePointIngester(args.site_url, client_id, client_secret, tenant_id)
    
    # Authenticate
    if not ingester.authenticate():
        logger.error("Authentication failed")
        return 1
    
    # Get site ID
    site_id = ingester.get_site_id()
    if not site_id:
        logger.error("Failed to get site ID")
        return 1
    
    logger.info(f"Site ID: {site_id}")
    
    # List documents
    documents = ingester.list_documents(site_id, args.folder)
    if not documents:
        logger.warning("No documents found")
        return 0
    
    # Ingest documents
    success = await ingester.ingest_to_vector_store(documents, site_id)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)