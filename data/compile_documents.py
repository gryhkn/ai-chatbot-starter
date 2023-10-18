# Add documents to the vectorstore, which is on the database, through an embeddings model
import sys
import os

from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings, VertexAIEmbeddings
from llama_index import VectorStoreIndex, ServiceContext, StorageContext
from llama_index.embeddings import LangchainEmbedding
from llama_index.node_parser import SimpleNodeParser
from llama_index.vector_stores import CassandraVectorStore

sys.path.append("../")

from chatbot_api.compile_docs import convert_scraped_files_to_documents
from integrations.astra import init_astra, init_astra_get_table_name
from integrations.google import init_gcp, GECKO_EMB_DIM
from integrations.openai import OPENAI_EMB_DIM

dotenv_path = "../.env"
load_dotenv(dotenv_path)

init_astra()
table_name = init_astra_get_table_name()

# Provider for LLM
llm_provider = os.getenv("LLM_PROVIDER", "openai")
if llm_provider == "openai":
    embedding_model = LangchainEmbedding(
        OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-ada-002"))
    )
else:
    init_gcp()
    embedding_model = LangchainEmbedding(
        VertexAIEmbeddings(model_name=os.getenv("GOOGLE_EMBEDDINGS_MODEL", "textembedding-gecko@latest"))
    )

embedding_dimension = OPENAI_EMB_DIM if llm_provider == "openai" else GECKO_EMB_DIM

vectorstore = CassandraVectorStore(
    session=None,
    keyspace=None,
    table=table_name,
    embedding_dimension=embedding_dimension,
)

storage_context = StorageContext.from_defaults(vector_store=vectorstore)
service_context = ServiceContext.from_defaults(
    llm=None,
    embed_model=embedding_model,
    node_parser=SimpleNodeParser.from_defaults(
        # According to https://genai.stackexchange.com/questions/317/does-the-length-of-a-token-give-llms-a-preference-for-words-of-certain-lengths
        # tokens are ~4 chars on average, so estimating 1,000 char chunk_size & 500 char overlap as previously used
        chunk_size=250,
        chunk_overlap=125,
    ),
)


# Perform embedding and add to vectorstore
def add_documents(folder_path):
    documents = convert_scraped_files_to_documents(folder_path)
    VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=service_context,
        show_progress=True,
    )


def list_folders(directory):
    return [
        d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))
    ]

if __name__ == '__main__':
    for folder in list_folders("."):
        add_documents(folder)
