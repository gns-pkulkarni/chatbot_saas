import asyncio

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from backend.app.models.schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from backend.app.services.indexer import index_website_content, index_document_content
from backend.app.services.scrapper import scrape_website_text, scrape_website_text_sync
from backend.app.services.document_extractor import process_uploaded_file
from backend.app.utils.supabase_client import supabase
from .auth import get_current_active_user
import uuid
import logging
import traceback

router = APIRouter(prefix="/knowledgebase", tags=["KnowledgeBase"])

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

@router.post("/add", response_model=KnowledgeBaseResponse)
async def add_knowledge_base(
    name: str = Form(...),
    type: str = Form(...),  # 'url' or 'document'
    source_url: str = Form(None),
    file: UploadFile = File(None),
    current_user: dict = Depends(get_current_active_user)
):
    knowledge_base_id = str(uuid.uuid4())
    user_id = current_user["id"]
    
    # Check user's plan limits before adding knowledge base
    try:
        # Get user's subscription and plan details
        client_result = supabase.table("saas_client_profiles")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not client_result.data:
            raise HTTPException(status_code=403, detail="No client profile found")
        
        client_id = client_result.data[0]["id"]
        
        # Get active subscription with plan details
        sub_result = supabase.table("saas_subscriptions")\
            .select("*, saas_plans(max_sites, max_documents, can_upload_docs)")\
            .eq("client_id", client_id)\
            .eq("status", "active")\
            .execute()
        
        if not sub_result.data:
            raise HTTPException(status_code=403, detail="No active subscription found")
        
        plan_info = sub_result.data[0].get("saas_plans", {})
        max_sites = plan_info.get("max_sites", 1)
        max_documents = plan_info.get("max_documents", 0)
        can_upload_docs = plan_info.get("can_upload_docs", False)
        
        # Count existing knowledge bases by type
        existing_kbs = supabase.table("saas_knowledge_base")\
            .select("type")\
            .eq("user_id", user_id)\
            .eq("status", "active")\
            .execute()
        
        url_count = sum(1 for kb in existing_kbs.data if kb["type"] == "url")
        doc_count = sum(1 for kb in existing_kbs.data if kb["type"] == "document")
        
        # Check limits based on type
        if type == "url":
            if max_sites != -1 and url_count >= max_sites:  # -1 means unlimited
                raise HTTPException(
                    status_code=403, 
                    detail=f"upgrade_required:sites:You've reached the maximum limit of {max_sites} website(s) for your current plan. Please upgrade to add more websites."
                )
        elif type == "document":
            if not can_upload_docs:
                raise HTTPException(
                    status_code=403, 
                    detail="upgrade_required:documents:Document uploads are not available in your current plan. Please upgrade to a higher plan to upload and manage documents."
                )
            if max_documents != -1 and doc_count >= max_documents:  # -1 means unlimited
                raise HTTPException(
                    status_code=403, 
                    detail=f"upgrade_required:documents:You've reached the maximum limit of {max_documents} document(s) for your current plan. Please upgrade to add more documents."
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking plan limits: {str(e)}")
        # Continue without limit check if there's an error
    
    # Store knowledge base info in DB FIRST (with pending status)
    try:
        logger.info(f"Creating knowledge base record - Name: {name}, Type: {type}, URL: {source_url}")
        kb_data = {
            "id": knowledge_base_id,
            "user_id": user_id,
            "name": name,
            "type": type,
            "source_url": source_url if type == "url" else None,
            "document_name": file.filename if type == "document" and file else None,
            "status": "pending"  # Start with pending status
        }
        result = supabase.table("saas_knowledge_base").insert(kb_data).execute()
        logger.info(f"Knowledge base record created with ID: {knowledge_base_id}")
    except Exception as e:
        logger.error(f"DB Insertion error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Failed to create knowledge base record")
    
    # Now process the content
    try:
        
        if type == "url":
            if not source_url:
                raise HTTPException(status_code=400, detail="source_url is required for type 'url'")
            
            # Scrape website content
            logger.info("Scraping website content...")
            try:
                # text_content = await scrape_website_text(source_url)
                text_content = await asyncio.to_thread(scrape_website_text_sync, source_url)
                logger.debug(f"Scraped content: {text_content[:100] if text_content else 'None'}...")
            except Exception as scrape_error:
                logger.error(f"Error during scraping: {str(scrape_error)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Scraping error: {str(scrape_error)}")
                
            if not text_content:
                logger.error("Failed to scrape website content")
                raise HTTPException(status_code=400, detail="Failed to scrape website content")
            
            # Index scraped content
            logger.info("Indexing website content...")
            try:
                index_result = index_website_content(user_id, source_url, text_content, knowledge_base_id)
                if not index_result:
                    logger.error("Failed to index website content")
                    raise HTTPException(status_code=500, detail="Failed to index website content")
            except Exception as index_error:
                logger.error(f"Error during indexing: {str(index_error)}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Indexing error: {str(index_error)}")

        elif type == "document":
            if not file:
                raise HTTPException(status_code=400, detail="File is required for type 'document'")
            
            # Process uploaded file
            logger.info("Processing uploaded file...")
            file_content = await file.read()
            document_name = file.filename
            text_content = await process_uploaded_file(file_content, document_name)
            logger.debug(f"Extracted content: {text_content[:100]}...")
            if not text_content:
                logger.error("Failed to extract document content")
                raise HTTPException(status_code=400, detail="Failed to extract document content")
            
            # Index document content
            logger.info("Indexing document content...")
            if not index_document_content(user_id, document_name, text_content, knowledge_base_id):
                logger.error("Failed to index document content")
                raise HTTPException(status_code=500, detail="Failed to index document content")

        else:
            logger.error("Invalid type, must be 'url' or 'document'")
            raise HTTPException(status_code=400, detail="Invalid type, must be 'url' or 'document'")
            
        # If we reach here, indexing was successful, update status to active
        logger.info("Updating knowledge base status to active")
        supabase.table("saas_knowledge_base").update({"status": "active"}).eq("id", knowledge_base_id).execute()
        
    except HTTPException:
        # If there was an error, update status to failed
        logger.error("Processing failed, updating status to failed")
        supabase.table("saas_knowledge_base").update({"status": "failed"}).eq("id", knowledge_base_id).execute()
        raise
    except Exception as ex:
        # If there was an error, update status to failed
        logger.error(f"Unexpected error: {str(ex)}")
        logger.error(traceback.format_exc())
        supabase.table("saas_knowledge_base").update({"status": "failed"}).eq("id", knowledge_base_id).execute()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(ex)}")

    logger.info("Knowledge base added successfully")
    return result.data[0]

@router.delete("/delete/{kb_id}")
async def delete_knowledge_base(kb_id: str, current_user: dict = Depends(get_current_active_user)):
    # Check if KB belongs to user
    check_result = supabase.table("saas_knowledge_base")\
        .select("id")\
        .eq("id", kb_id)\
        .eq("user_id", current_user["id"])\
        .execute()
    
    if not check_result.data:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Delete from vector store first
    try:
        supabase.table("saas_knowledge_base_vectors").delete().eq("knowledge_base_id", kb_id).execute()
    except Exception as e:
        logger.error(f"Error deleting vectors: {str(e)}")
    
    # Delete knowledge base record
    supabase.table("saas_knowledge_base").delete().eq("id", kb_id).execute()
    
    return {"message": "Knowledge base deleted successfully"}
