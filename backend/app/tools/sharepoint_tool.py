from typing import Any, Dict, Optional, List
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.tools.base import Tool, ToolResult, ToolExecutionError
from app.services.key_vault import get_key_vault_service
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class SharePointRAGTool(Tool):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="SharePoint_Search",
            description="Search and retrieve information from SharePoint documents. Can find policies, procedures, documentation, and other organizational content.",
            config=config
        )
        self.key_vault = get_key_vault_service()
        self.site_url = config.get("site_url") if config else None
        self.collection_name = config.get("collection_name", "sharepoint_docs") if config else "sharepoint_docs"
        self.top_k = config.get("top_k", 5) if config else 5
        self.embeddings = None
        self.chroma_client = None
        self.collection = None
        self._initialize()
    
    def _initialize(self):
        try:
            api_key = settings.AZURE_OPENAI_API_KEY or self.key_vault.get_api_key("azure_openai")
            
            if not api_key:
                logger.warning("No Azure OpenAI API key found, SharePoint RAG Tool will not be available")
                return
            
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-ada-002",
                openai_api_key=api_key,
                openai_api_base=settings.AZURE_OPENAI_ENDPOINT,
                openai_api_type="azure",
                deployment="text-embedding-ada-002",
                openai_api_version=settings.AZURE_OPENAI_API_VERSION
            )
            
            persist_directory = settings.CHROMA_PERSIST_DIRECTORY
            
            self.chroma_client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )
            
            try:
                self.collection = self.chroma_client.get_collection(self.collection_name)
                logger.info(f"SharePoint RAG Tool connected to existing collection: {self.collection_name}")
            except:
                logger.warning(f"Collection '{self.collection_name}' not found. Will be created when documents are ingested.")
                
        except Exception as e:
            logger.error(f"Failed to initialize SharePoint RAG Tool: {e}")
            self.embeddings = None
            self.chroma_client = None
    
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> ToolResult:
        if not self.embeddings or not self.chroma_client:
            return ToolResult(
                success=False,
                error="SharePoint RAG Tool is not properly configured. Please check embeddings and vector store settings."
            )
        
        try:
            if not self.collection:
                return ToolResult(
                    success=False,
                    error=f"No documents found in collection '{self.collection_name}'. Please run ingestion first."
                )
            
            query_embedding = self.embeddings.embed_query(query)
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=self.top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["documents"][0]:
                return ToolResult(
                    success=True,
                    data="No relevant documents found for your query.",
                    metadata={"query": query, "results_count": 0}
                )
            
            formatted_results = self._format_results(results, query)
            
            return ToolResult(
                success=True,
                data=formatted_results,
                metadata={
                    "query": query,
                    "results_count": len(results["documents"][0]),
                    "collection": self.collection_name,
                    "site_url": self.site_url
                }
            )
            
        except Exception as e:
            logger.error(f"SharePoint RAG Tool execution error: {e}")
            return ToolResult(
                success=False,
                error=f"Failed to search SharePoint documents: {str(e)}"
            )
    
    def _format_results(self, results: Dict, query: str) -> str:
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        
        formatted = f"Found {len(documents)} relevant documents for query: '{query}'\n\n"
        
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances), 1):
            relevance_score = 1 - distance
            
            formatted += f"**Result {i}** (Relevance: {relevance_score:.2%})\n"
            
            if metadata:
                if "title" in metadata:
                    formatted += f"Title: {metadata['title']}\n"
                if "source" in metadata:
                    formatted += f"Source: {metadata['source']}\n"
                if "modified_date" in metadata:
                    formatted += f"Modified: {metadata['modified_date']}\n"
            
            formatted += f"Content:\n{doc[:500]}...\n\n"
            formatted += "-" * 50 + "\n\n"
        
        return formatted
    
    def validate_config(self) -> bool:
        if not self.embeddings:
            logger.error("SharePoint RAG Tool: Embeddings not initialized")
            return False
        
        if not self.chroma_client:
            logger.error("SharePoint RAG Tool: ChromaDB client not initialized")
            return False
        
        return True
    
    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> bool:
        if not self.chroma_client or not self.embeddings:
            logger.error("Cannot ingest documents: Tool not properly initialized")
            return False
        
        try:
            if not self.collection:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"source": "sharepoint", "site_url": self.site_url}
                )
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            all_texts = []
            all_metadatas = []
            all_ids = []
            
            for doc in documents:
                chunks = text_splitter.split_text(doc["content"])
                
                for i, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    all_metadatas.append({
                        "source": doc.get("source", "unknown"),
                        "title": doc.get("title", "Untitled"),
                        "modified_date": doc.get("modified_date", ""),
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    })
                    all_ids.append(f"{doc.get('id', 'doc')}_{i}")
            
            if all_texts:
                embeddings = self.embeddings.embed_documents(all_texts)
                
                self.collection.add(
                    embeddings=embeddings,
                    documents=all_texts,
                    metadatas=all_metadatas,
                    ids=all_ids
                )
                
                logger.info(f"Successfully ingested {len(documents)} documents ({len(all_texts)} chunks) into {self.collection_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to ingest documents: {e}")
            return False