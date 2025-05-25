import os
import asyncio
import multiprocessing as mp
from dotenv import load_dotenv
from openai import OpenAI
from schemas import MessageBase

from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma  # ✅ 최신 방식
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

from duckduckgo_search import DDGS
from newspaper import Article

# ✅ Mac에서 멀티프로세싱 문제 방지
mp.set_start_method("fork", force=True)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ✅ 환경 변수 로드
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
GPT_MODEL = "gpt-4o-mini"

# ✅ HuggingFace 임베딩 모델 초기화
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"batch_size": 1, "normalize_embeddings": False}
)

# ✅ Chroma 벡터스토어 설정
vector_store = Chroma(
    embedding_function=embedding_model,
    persist_directory="./chroma_db"
)

# ✅ GPT로 키워드 추출
def extract_keywords_with_gpt(message):
    prompt = f"""
메시지에서 핵심 키워드(고유 명사, 은어, 인물, 제품 이름 등)를 추출해줘.
메시지: {message}

결과는 파이썬 리스트 형태로 반환해줘.
예: ["소크라테스", "상무님"]
"""
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return eval(response.choices[0].message.content)
    except Exception as e:
        print("❗ 키워드 추출 실패:", e)
        return []

# ✅ DuckDuckGo 검색
def search_web_pages(query, max_results=3):
    with DDGS() as ddgs:
        return [r["href"] for r in ddgs.text(query, max_results=max_results)]

# ✅ 기사 본문 추출
def extract_text_from_url(url):
    try:
        article = Article(url, language='ko')
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print("❗ URL 추출 실패:", e)
        return ""

# ✅ 문서 임베딩 및 추가
def add_docs_to_vectorstore(texts, source_name):
    new_docs = [Document(page_content=t, metadata={"source": source_name}) for t in texts]
    new_docs = filter_complex_metadata(new_docs)
    vector_store.add_documents(new_docs)

# ✅ 웹 기반 문서 자동 추가
def expand_rag_with_web(message_content):
    keywords = extract_keywords_with_gpt(message_content)
    print("🔍 추출된 키워드:", keywords)

    all_texts = []
    for kw in keywords:
        urls = search_web_pages(kw)
        print(f"🔗 {kw} 관련 URL:", urls)
        for url in urls:
            text = extract_text_from_url(url)
            if text:
                all_texts.append(text)

    if all_texts:
        add_docs_to_vectorstore(all_texts, "web")
        print(f"✅ {len(all_texts)} 개 웹 문서 추가됨.")
    else:
        print("⚠️ 웹에서 유의미한 자료를 찾지 못했습니다.")

# ✅ 메시지 처리 RAG + GPT
def process_message(message: MessageBase):
    content = f"""
    Sender: {message.sender_id}
    Subject: {message.subject}
    Content: {message.content}
    """

    try:
        results = vector_store.similarity_search(message.content, k=5)
    except Exception as e:
        print("❗ Similarity search failed:", e)
        results = []

    contexts = " ".join([r.page_content for r in results]) if results else "No context found."

    system_prompt = """\
You are an assistant that processes internal messages.
Your tasks:
1. Extract important keywords from the message (especially slangs or named entities).
2. Use context to understand any unclear terms.
3. Classify the message into one of the categories: "deadline", "payment", "public", "office", "others".
4. Return output as JSON with fields: keywords, summary, category.
"""

    user_prompt = f"""
Message Metadata and Content:
{content}

Context for understanding:
{contexts}

Respond in the following format:
{{
  "keywords": [...],
  "summary": "...",
  "category": "..."
}}
"""

    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print("❗ OpenAI API call failed:", e)
        return "{}"

# ✅ 외부에서 호출 가능한 전체 파이프라인
def run_rag_pipeline(message: MessageBase):
    try:
        expand_rag_with_web(message.content)
        return process_message(message)
    except Exception as e:
        print("❗ 전체 RAG 처리 실패:", e)
        return "{}"