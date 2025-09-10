from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.schema import Document
from backend.app.utils.supabase_client import supabase
from backend.app.utils.config import SUPABASE_VECTOR_TABLE, SUPABASE_MATCH_FUNC
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List
import os

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

def index_documents(knowledge_base_id: str, documents: List[Document]) -> bool:
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Indexing {len(documents)} documents for knowledge_base_id: {knowledge_base_id}")
        
        # Check if OpenAI API key is set
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY not set")
            
        embedding = OpenAIEmbeddings()
        
        # Custom implementation to handle knowledge_base_id column
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        
        total_chunks = 0
        for doc in documents:
            # Split document into chunks
            chunks = splitter.split_documents([doc])
            logger.info(f"Document split into {len(chunks)} chunks")
            total_chunks += len(chunks)
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding_vector = embedding.embed_query(chunk.page_content)
                
                # Prepare data for insertion
                data = {
                    "content": chunk.page_content,
                    "embedding": embedding_vector,
                    "metadata": chunk.metadata,
                    "knowledge_base_id": knowledge_base_id  # Direct column
                }
                
                # Insert into Supabase
                result = supabase.table(SUPABASE_VECTOR_TABLE).insert(data).execute()
                logger.debug(f"Inserted chunk {i+1}/{len(chunks)} with ID: {result.data[0]['id'] if result.data else 'Unknown'}")
            
        logger.info(f"Successfully indexed {total_chunks} chunks from {len(documents)} documents")
        return True
    except Exception as e:
        logger.error(f"Error indexing documents: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def index_website_content(user_id: str, site_url: str, text: str, knowledge_base_id: str) -> bool:
    try:
        documents = [
            Document(
                page_content=text,
                metadata={
                    "user_id": user_id,
                    "source_url": site_url,
                    "document_name": None,
                    "knowledge_base_id": knowledge_base_id
                }
            )
        ]
        return index_documents(knowledge_base_id, documents)
    except Exception as e:
        print(f"Error indexing site content: {e}")
        return False

def index_document_content(user_id: str, document_name: str, text: str, knowledge_base_id: str) -> bool:
    try:
        documents = [
            Document(
                page_content=text,
                metadata={
                    "user_id": user_id,
                    "source_url": None,
                    "document_name": document_name,
                    "knowledge_base_id": knowledge_base_id
                }
            )
        ]
        return index_documents(knowledge_base_id, documents)
    except Exception as e:
        print(f"Error indexing document content: {e}")
        return False
