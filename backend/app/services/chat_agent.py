from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.callbacks.manager import get_openai_callback
from backend.app.utils.config import SUPABASE_VECTOR_TABLE, SUPABASE_MATCH_FUNC
from backend.app.utils.supabase_client import supabase
from backend.app.services.chat_history import save_chat_history
import os

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

def get_chat_response(user_id: str, message: str, chat_history: list) -> str:
    try:
        embedding = OpenAIEmbeddings()
        vectordb = SupabaseVectorStore(
            client=supabase,
            embedding=embedding,
            table_name=SUPABASE_VECTOR_TABLE,
            query_name=SUPABASE_MATCH_FUNC
        )
        
        retriever = vectordb.as_retriever(
            search_kwargs={"filter": {"user_id": user_id}, "k": 10}
        )
        
        # Define prompt (only accepts `question`)
        custom_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template="""
            You are an intelligent assistant trained to answer questions based ONLY on the given context.
            Answer using **Markdown** formatting when possible.

            - Think carefully about synonyms or indirect mentions.
            - If the context includes the answer in any form, extract and summarize it.
            - ONLY if it's truly unrelated, politely inform the user that the information is not available and provide the contact details 
            (email, phone number(s), or contact page URL) from the content, so the user can reach out directly.

            Context:
            {context}

            Question: {question}
            Answer:
            """
        )

        # Build the chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model="gpt-4o", temperature=0),
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": custom_prompt},
            input_key="question",
            output_key="answer"
        )

        with get_openai_callback() as cb:
            result = qa_chain.invoke({"question": message})
        answer = result["answer"]

        # Print token usage & cost for THIS call
        # print(f"Prompt tokens: {cb.prompt_tokens}")
        # print(f"Completion tokens: {cb.completion_tokens}")
        # print(f"Total tokens: {cb.total_tokens}")
        # print(f"Estimated cost (USD): {cb.total_cost:.6f}")

        # Getting token usage and cost per message
        input_tokens = cb.prompt_tokens
        output_tokens = cb.completion_tokens
        total_cost_usd = cb.total_cost
        # Save chat history
        save_chat_history(user_id, message, answer, input_tokens, output_tokens, total_cost_usd)
        
        return answer

    except Exception as e:
        print(f"Chat error: {e}")
        return "I'm sorry, I encountered an error while processing your request. Please try again later."
