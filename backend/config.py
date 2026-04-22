import os
import json
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class FolderConfig(BaseSettings):
    path: str
    enabled: bool = True
    id: Optional[str] = None
    
    @property
    def clean_path(self) -> str:
        return os.path.normpath(self.path)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore'
    )
    
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5:3b", alias="OLLAMA_MODEL")
    ollama_embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="OLLAMA_EMBEDDING_MODEL")
    ollama_timeout: int = Field(default=300, alias="OLLAMA_TIMEOUT")
    
    document_folders: str = Field(default=r"E:\Mario@work\RKI", alias="DOCUMENT_FOLDERS")
    
    vector_store_type: str = Field(default="chroma", alias="VECTOR_STORE_TYPE")
    vector_store_path: str = Field(default="./data/chroma_db", alias="VECTOR_STORE_PATH")
    
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    
    tesseract_cmd: Optional[str] = Field(default=None, alias="TESSERACT_CMD")
    enable_ocr: bool = Field(default=True, alias="ENABLE_OCR")
    
    enable_file_watcher: bool = Field(default=True, alias="ENABLE_FILE_WATCHER")
    debounce_seconds: int = Field(default=3, alias="DEBOUNCE_SECONDS")
    
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=1, alias="API_WORKERS")
    
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", alias="LOG_FILE")
    
    _folders_config_path: str = "./data/folders_config.json"
    
    @field_validator('document_folders', mode='before')
    @classmethod
    def parse_folders(cls, v):
        if isinstance(v, str):
            return v
        return v
    
    def get_folders_list(self) -> List[FolderConfig]:
        folders = []
        for i, folder_path in enumerate(self.document_folders.split(',')):
            folder_path = folder_path.strip()
            if folder_path:
                folders.append(FolderConfig(
                    path=folder_path,
                    enabled=True,
                    id=f"folder_{i}"
                ))
        return folders
    
    def get_active_folders(self) -> List[FolderConfig]:
        all_folders = self.get_folders_list()
        saved_folders = self._load_saved_folders()
        
        folder_map = {f.path: f for f in all_folders}
        
        for sf in saved_folders:
            if sf.path in folder_map:
                folder_map[sf.path] = sf
            else:
                folder_map[sf.path] = sf
        
        return [f for f in folder_map.values() if f.enabled]
    
    def _load_saved_folders(self) -> List[FolderConfig]:
        config_path = Path(self._folders_config_path)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [FolderConfig(**item) for item in data.get('folders', [])]
            except Exception:
                pass
        return []
    
    def save_folders(self, folders: List[FolderConfig]) -> None:
        config_path = Path(self._folders_config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({'folders': [f.model_dump() for f in folders]}, f, indent=2)
    
    def validate_folders(self) -> List[str]:
        errors = []
        for folder in self.get_active_folders():
            path = Path(folder.path)
            if not path.exists():
                errors.append(f"Folder does not exist: {folder.path}")
            elif not os.access(folder.path, os.R_OK):
                errors.append(f"Folder is not readable: {folder.path}")
        return errors
    
    def get_vector_store_dir(self) -> Path:
        path = Path(self.vector_store_path)
        if not path.is_absolute():
            base_dir = Path(__file__).parent.parent
            path = base_dir / path
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_log_dir(self) -> Path:
        path = Path(self.log_file)
        if not path.is_absolute():
            base_dir = Path(__file__).parent.parent
            path = base_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = AppSettings()