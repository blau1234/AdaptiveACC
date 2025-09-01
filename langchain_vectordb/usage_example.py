
# LangChain向量数据库使用示例
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# 加载现有向量数据库
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=1536
)

vector_store = Chroma(
    persist_directory="langchain_vectordb",
    embedding_function=embeddings,
    collection_name="ifcopenshell_langchain_docs"
)

# 创建检索器
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}
)

# 检索示例
query = "如何创建墙体几何"
relevant_docs = retriever.get_relevant_documents(query)

for i, doc in enumerate(relevant_docs):
    print(f"文档 {i+1}:")
    print(f"内容: {doc.page_content[:200]}...")
    print(f"元数据: {doc.metadata}")
    print()
