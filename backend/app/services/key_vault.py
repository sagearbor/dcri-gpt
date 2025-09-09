import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from app.core.config import settings

logger = logging.getLogger(__name__)


class KeyVaultService:
    def __init__(self):
        self._client = None
        self._cache: Dict[str, Any] = {}
        self._is_production = settings.ENVIRONMENT == "production"
        
        if self._is_production and settings.AZURE_KEY_VAULT_URL:
            self._initialize_azure_client()
    
    def _initialize_azure_client(self):
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import ClientSecretCredential
            
            credential = ClientSecretCredential(
                tenant_id=settings.AZURE_TENANT_ID,
                client_id=settings.AZURE_CLIENT_ID,
                client_secret=settings.AZURE_CLIENT_SECRET
            )
            
            self._client = SecretClient(
                vault_url=settings.AZURE_KEY_VAULT_URL,
                credential=credential
            )
            logger.info("Azure Key Vault client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault client: {e}")
            self._client = None
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        secret_value = None
        
        if self._is_production and self._client:
            try:
                secret = self._client.get_secret(secret_name)
                secret_value = secret.value
                self._cache[secret_name] = secret_value
                logger.debug(f"Retrieved secret '{secret_name}' from Key Vault")
            except Exception as e:
                logger.error(f"Error retrieving secret '{secret_name}': {e}")
                secret_value = default
        else:
            env_var_name = secret_name.upper().replace("-", "_")
            secret_value = os.getenv(env_var_name, default)
            if secret_value:
                logger.debug(f"Retrieved secret '{secret_name}' from environment variable")
        
        return secret_value
    
    def get_connection_string(self, alias: str) -> Optional[str]:
        mapping = {
            "sql_primary": "SQL-CONNECTION-STRING",
            "sql_readonly": "SQL-READONLY-CONNECTION-STRING",
            "sharepoint": "SHAREPOINT-CONNECTION-STRING",
            "box": "BOX-CONNECTION-STRING",
            "redis": "REDIS-CONNECTION-STRING"
        }
        
        secret_name = mapping.get(alias)
        if not secret_name:
            logger.error(f"Unknown connection string alias: {alias}")
            return None
        
        return self.get_secret(secret_name)
    
    def get_api_key(self, service: str) -> Optional[str]:
        mapping = {
            "openai": "OPENAI-API-KEY",
            "azure_openai": "AZURE-OPENAI-API-KEY",
            "sharepoint_client": "SHAREPOINT-CLIENT-SECRET",
            "box_client": "BOX-CLIENT-SECRET"
        }
        
        secret_name = mapping.get(service)
        if not secret_name:
            logger.error(f"Unknown API key service: {service}")
            return None
        
        return self.get_secret(secret_name)
    
    def clear_cache(self):
        self._cache.clear()
        logger.info("Key Vault cache cleared")


@lru_cache()
def get_key_vault_service() -> KeyVaultService:
    return KeyVaultService()