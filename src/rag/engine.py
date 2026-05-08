"""
金融RAG引擎 - LangChain版本
使用LangChain的ChatOpenAI进行LLM调用
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# 显式加载.env文件
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)

# ChromaDB
import chromadb
from chromadb.config import Settings as ChromaSettings

# LangChain LLM
try:
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("[RAG] Warning: langchain_openai not available")


# 简单的文档类
class Document:
    def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
        self.page_content = page_content
        self.metadata = metadata or {}


# 简单的文本分割
def simple_text_splitter(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        
        # 尝试在句号或换行处分割
        for sep in ["。\n", "\n", "。", ". "]:
            pos = chunk.rfind(sep)
            if pos > chunk_size - 100:
                pos = -1
            if pos > 0:
                chunk = chunk[:pos + 1]
                end = start + pos + 1
                break
        
        chunks.append(chunk.strip())
        start = end - overlap if end - overlap > start else end
    
    return chunks if chunks else [text]


@dataclass
class RAGConfig:
    persist_directory: str = "./data/chroma_db"
    embedding_model: str = "BAAI/bge-base-zh-v1.5"
    embedding_device: str = "cpu"
    local_embedding_path: Optional[str] = None
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50


class FinanceRAGEngine:
    """金融RAG引擎"""
    
    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._embedding = None
        self._llm = None
        self._init_components()
    
    def _init_components(self):
        """初始化组件"""
        # 调试输出API密钥状态
        _debug_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        print(f"[RAG] 环境变量加载: {'成功' if _debug_key else '未找到密钥'}")
        if _debug_key:
            print(f"[RAG] API_KEY前缀: {_debug_key[:10]}...")
        
        print(f"[RAG] 配置: embedding={self.config.embedding_model}, llm={self.config.llm_provider}/{self.config.llm_model}")
        
        # ChromaDB客户端
        print(f"[RAG] ChromaDB path: {self.config.persist_directory}")
        self.client = chromadb.PersistentClient(
            path=self.config.persist_directory,
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
        )
        print(f"[RAG] ChromaDB client initialized, collections: {self.client.list_collections()}")
        
        # 初始化LLM
        self._init_llm()
        
        self._initialized = True
        print("[RAG] RAG引擎初始化完成")
    
    def _init_llm(self):
        """初始化LangChain LLM"""
        if not LANGCHAIN_AVAILABLE:
            print("[RAG] LangChain不可用，使用requests备用方案")
            return
        
        try:
            # 获取API密钥
            api_key = (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("DASHSCOPE_API_KEY")
                or self.config.llm_api_key
            )
            
            # 获取base_url
            base_url = os.getenv("LLM_BASE_URL") or self.config.llm_base_url or ""
            
            # 获取model
            model = os.getenv("LLM_MODEL") or self.config.llm_model or "deepseek-chat"
            
            # 自动判断提供商
            if "deepseek" in base_url or "deepseek" in model:
                provider = "deepseek"
            elif "openai" in base_url or "api.openai" in base_url:
                provider = "openai"
            elif "dashscope" in base_url or "qwen" in model:
                provider = "qwen"
            else:
                provider = self.config.llm_provider
            
            print(f"[RAG] LLM初始化: provider={provider}, model={model}")
            
            # 根据提供商设置LLM
            if provider == "qwen":
                # 通义千问
                try:
                    from langchain_community.chat_models import ChatTongyi
                    self._llm = ChatTongyi(
                        model_name=model,
                        temperature=self.config.llm_temperature,
                        streaming=True
                    )
                    print("[RAG] 通义千问LLM初始化成功")
                except ImportError:
                    print("[RAG] langchain_community.chat_models.ChatTongyi 不可用")
                    self._llm = None
            else:
                # OpenAI兼容接口 (DeepSeek, OpenAI等)
                _base_url = base_url or "https://api.deepseek.com/v1"
                self._llm = ChatOpenAI(
                    model=model,
                    api_key=api_key,
                    base_url=_base_url,
                    temperature=self.config.llm_temperature,
                    streaming=True
                )
                print(f"[RAG] {provider} LLM初始化成功")
                
        except Exception as e:
            print(f"[RAG] LLM初始化失败: {e}")
            self._llm = None
    
    @property
    def llm(self):
        """获取LLM对象"""
        if self._llm is None:
            self._init_llm()
        return self._llm
    
    @property
    def is_initialized(self) -> bool:
        return getattr(self, "_initialized", False)
    
    def _load_embedding(self):
        """加载embedding模型"""
        if self._embedding is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = self.config.local_embedding_path or self.config.embedding_model
                self._embedding = SentenceTransformer(model_name)
                print(f"[RAG] Embedding模型加载成功: {model_name}")
            except Exception as e:
                print(f"[RAG] Embedding不可用 ({e})，使用关键词匹配作为后备方案")
                self._embedding = None
                return

            try:
                chromadb_dir = os.path.join(os.path.expanduser("~"), ".cache", "chroma")
                onnx_dir = os.path.join(chromadb_dir, "onnx_models")
                if not os.path.exists(onnx_dir):
                    print(f"[RAG] ChromaDB ONNX模型不存在，下载中（这可能需要几分钟）...")
            except:
                pass

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本嵌入"""
        if self._embedding is None:
            return [[0.0] * 768 for _ in texts]
        embeddings = self._embedding.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def _keyword_search(
        self, query: str, collection, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """基于关键词的简单搜索（无embedding时的后备方案）"""
        all_docs = collection.get()

        if not all_docs or not all_docs.get("documents"):
            return []

        docs = all_docs["documents"]
        metadatas = all_docs.get("metadatas", [{}] * len(docs))
        ids = all_docs.get("ids", [str(i) for i in range(len(docs))])

        query_keywords = set(query.lower().split())
        results = []

        for i, doc in enumerate(docs):
            doc_lower = doc.lower()
            score = sum(1 for kw in query_keywords if kw in doc_lower) / max(len(query_keywords), 1)

            if score > 0:
                results.append({
                    "id": ids[i] if i < len(ids) else str(i),
                    "content": doc,
                    "score": min(score * 2, 1.0),
                    "metadata": metadatas[i] if i < len(metadatas) else {}
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_vectorstore(self, collection_name: str = "finance_knowledge"):
        """获取向量存储"""
        self._load_embedding()
        if self._embedding is None:
            raise RuntimeError("Embedding模型未加载")
        
        from langchain_community.vectorstores import Chroma
        return Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self._embedding
        )
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "finance_knowledge"
    ) -> int:
        """添加文档到向量库"""
        if not texts:
            return 0
        
        self._load_embedding()
        
        try:
            collection = self.client.get_collection(collection_name)
        except:
            collection = self.client.create_collection(collection_name)
        
        # 分割并嵌入
        all_chunks = []
        all_ids = []
        all_embeddings = []
        all_metadatas = []

        for i, text in enumerate(texts):
            chunks = simple_text_splitter(text, self.config.chunk_size, self.config.chunk_overlap)
            for j, chunk in enumerate(chunks):
                doc_id = f"{i}_{j}" if not ids else f"{ids[i]}_{j}"
                all_chunks.append(chunk)
                all_ids.append(doc_id)
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                all_metadatas.append(meta)
        
        # 批量嵌入
        if all_chunks:
            all_embeddings = self._get_embeddings(all_chunks)

        if not all_embeddings or all_embeddings == [[0.0] * 768] * len(all_chunks):
            collection.add(
                ids=all_ids,
                documents=all_chunks,
                metadatas=all_metadatas
            )
        else:
            collection.add(
                ids=all_ids,
                embeddings=all_embeddings,
                documents=all_chunks,
                metadatas=all_metadatas
            )
        
        print(f"[RAG] 已添加 {len(all_chunks)} 个文档片段到 {collection_name}")
        return len(all_chunks)

    def add_file(
        self,
        file_path: str,
        collection_name: str = "user_knowledge",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加单个文件到向量库

        Args:
            file_path: 文件路径
            collection_name: 集合名称
            metadata: 额外的元数据

        Returns:
            Dict: 包含状态、文件名、字符数等信息
        """
        from src.rag.document_loader import load_document, get_file_info

        try:
            file_info = get_file_info(file_path)
            text = load_document(file_path)

            file_metadata = {
                "filename": file_info["name"],
                "file_extension": file_info["extension"],
                "file_size": file_info["size"],
                "file_size_mb": file_info["size_mb"],
            }

            if metadata:
                file_metadata.update(metadata)

            count = self.add_documents(
                texts=[text],
                metadatas=[file_metadata],
                ids=[f"file_{file_info['name']}_{int(os.urandom(8).hex(), 16)}"],
                collection_name=collection_name
            )

            return {
                "status": "success",
                "filename": file_info["name"],
                "chars": len(text),
                "chunks": count,
                "collection": collection_name
            }

        except FileNotFoundError:
            return {"status": "error", "error": f"文件不存在: {file_path}"}
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": f"处理文件失败: {str(e)}"}

    def add_files(
        self,
        file_paths: List[str],
        collection_name: str = "user_knowledge"
    ) -> List[Dict[str, Any]]:
        """
        批量添加文件到向量库

        Args:
            file_paths: 文件路径列表
            collection_name: 集合名称

        Returns:
            List[Dict]: 每个文件的处理结果
        """
        results = []
        for file_path in file_paths:
            result = self.add_file(file_path, collection_name)
            results.append(result)
        return results

    def get_collection_info(self, collection_name: str = "user_knowledge") -> Dict[str, Any]:
        """
        获取集合信息

        Args:
            collection_name: 集合名称

        Returns:
            Dict: 集合信息
        """
        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()

            sample_docs = []
            try:
                results = collection.get(limit=3)
                if results.get("documents"):
                    for i, doc in enumerate(results["documents"]):
                        sample_docs.append({
                            "id": results["ids"][i] if results.get("ids") else None,
                            "content_preview": doc[:200] + "..." if len(doc) > 200 else doc,
                            "metadata": results["metadatas"][i] if results.get("metadatas") else {}
                        })
            except:
                pass

            return {
                "name": collection_name,
                "count": count,
                "exists": True,
                "sample_docs": sample_docs
            }
        except Exception:
            return {
                "name": collection_name,
                "count": 0,
                "exists": False,
                "sample_docs": []
            }

    def delete_collection_data(
        self,
        collection_name: str = "user_knowledge",
        filter_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        删除集合中的数据

        Args:
            collection_name: 集合名称
            filter_ids: 要删除的文档ID列表，如果为None则删除整个集合

        Returns:
            Dict: 删除结果
        """
        try:
            if filter_ids is None:
                self.client.delete_collection(collection_name)
                return {"status": "success", "message": f"集合 {collection_name} 已删除"}
            else:
                collection = self.client.get_collection(collection_name)
                collection.delete(ids=filter_ids)
                return {"status": "success", "deleted": len(filter_ids)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def search(
        self,
        query: str,
        top_k: int = 5,
        collection_name: str = "finance_knowledge"
    ) -> List[Dict[str, Any]]:
        """检索相关文档"""
        self._load_embedding()

        try:
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            print(f"[RAG] Search: collection={collection_name}, count={count}, query={query[:50]}...")
        except Exception as e:
            print(f"[RAG] Search: collection '{collection_name}' not found: {e}")
            return []

        if self._embedding is None:
            return self._keyword_search(query, collection, top_k)

        try:
            query_embedding = self._get_embeddings([query])[0]
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, collection.count())
            )

            output = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    output.append({
                        "content": doc,
                        "score": 1.0 - results['distances'][0][i] if results.get('distances') else 0.5,
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') else {}
                    })

            return output
        except Exception as e:
            print(f"[RAG] 向量检索失败，使用关键词搜索: {e}")
            return self._keyword_search(query, collection, top_k)
    
    def delete_collection(self, collection_name: str):
        try:
            self.client.delete_collection(collection_name)
        except: pass
    
    def list_collections(self) -> List[str]:
        return [col.name for col in self.client.list_collections()]
    
    def get_collection_count(self, collection_name: str) -> int:
        try:
            return self.client.get_collection(collection_name).count()
        except: return 0
    
    def chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        collection_name: str = "finance_knowledge"
    ) -> Dict[str, Any]:
        """RAG对话 - 使用LangChain LLM"""
        # 检索
        search_results = self.search(query, top_k, collection_name)
        
        # 构建上下文
        context = "\n\n".join([
            f"【文档{i + 1}】{r['content'][:300]}..."
            for i, r in enumerate(search_results)
        ])
        
        history_text = ""
        if conversation_history:
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else 'AI'}: {msg['content'][:150]}"
                for msg in conversation_history[-5:]
            ])
        
        full_prompt = f"""你是一个专业的金融AI助手。请根据以下参考文档回答用户的问题。

参考文档：
{context}

对话历史：
{history_text}

用户问题：{query}

要求：1.优先使用参考文档 2.没有相关信息时如实说明 3.保持专业易懂

回答："""
        
        # 使用LangChain LLM
        try:
            if self.llm is not None:
                response = self.llm.invoke(full_prompt)
                answer = response.content if hasattr(response, 'content') else str(response)
            else:
                # 备用：使用requests
                answer = self._chat_with_requests(full_prompt)
        except Exception as e:
            print(f"[RAG] LLM调用失败: {e}")
            answer = f"生成回答出错: {str(e)}"
        
        return {"answer": answer, "sources": search_results}
    
    def _chat_with_requests(self, prompt: str) -> str:
        """使用requests备用调用"""
        import requests
        
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
        )
        base_url = os.getenv("LLM_BASE_URL") or "https://api.deepseek.com/v1"
        model = os.getenv("LLM_MODEL") or "deepseek-chat"
        
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                timeout=60
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"请求失败: {resp.status_code}"
        except Exception as e:
            return f"请求出错: {str(e)}"
    
    def stream_chat(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        collection_name: str = "finance_knowledge"
    ):
        """流式RAG对话 - 使用LangChain LLM"""
        # 检索
        search_results = self.search(query, top_k, collection_name)
        
        context = "\n\n".join([
            f"【文档{i + 1}】{r['content'][:300]}..."
            for i, r in enumerate(search_results)
        ])
        
        history_text = ""
        if conversation_history:
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else 'AI'}: {msg['content'][:150]}"
                for msg in conversation_history[-5:]
            ])
        
        full_prompt = f"""你是一个专业的金融AI助手。请根据以下参考文档回答用户的问题。

参考文档：
{context}

对话历史：
{history_text}

用户问题：{query}

要求：1.优先使用参考文档 2.没有相关信息时如实说明 3.保持专业易懂

回答："""
        
        # 使用LangChain LLM流式输出
        try:
            if self.llm is not None:
                for chunk in self.llm.stream(full_prompt):
                    content = getattr(chunk, 'content', '') or ''
                    if content:
                        yield {"type": "content", "content": content}
            else:
                # 备用：使用requests
                for content in self._stream_with_requests(full_prompt):
                    yield {"type": "content", "content": content}
        except Exception as e:
            yield {"type": "error", "error": str(e)}
        
        # 返回来源
        yield {"type": "sources", "sources": search_results[:top_k]}
    
    def _stream_with_requests(self, prompt: str):
        """使用requests备用流式调用"""
        import requests
        
        api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
        )
        base_url = os.getenv("LLM_BASE_URL") or "https://api.deepseek.com/v1"
        model = os.getenv("LLM_MODEL") or "deepseek-chat"
        
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": True},
                stream=True, timeout=60
            )
            
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode('utf-8', errors='ignore')
                    if decoded.startswith('data: '):
                        if decoded.strip() == 'data: [DONE]':
                            break
                        try:
                            data = json.loads(decoded[6:])
                            content = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                yield content
                        except:
                            pass
        except Exception as e:
            yield f"请求出错: {str(e)}"


# 全局引擎
_rag_engine: Optional[FinanceRAGEngine] = None


def get_rag_engine(config: Optional[RAGConfig] = None) -> FinanceRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        if config is None:
            from src.core.paths import PROJECT_ROOT, CHROMA_DB_DIR
            local_model_path = str(PROJECT_ROOT / "models" / "bge-base-zh-v1.5")
            config = RAGConfig(
                local_embedding_path=local_model_path,
                persist_directory=str(CHROMA_DB_DIR)
            )
            print(f"[RAG] Using ChromaDB path: {config.persist_directory}")
        _rag_engine = FinanceRAGEngine(config)
    return _rag_engine


def index_session_reports(
    report_dir: Path = None,
    collection_name: str = "session_reports"
) -> Dict[str, Any]:
    from src.export.json_to_markdown import JSONToMarkdownConverter
    from src.core.paths import SESSION_DIR

    engine = get_rag_engine()
    report_dir = report_dir or SESSION_DIR
    
    if not report_dir.exists():
        return {"status": "error", "message": f"目录不存在: {report_dir}"}
    
    texts, metadatas, errors = [], [], []
    
    converter = JSONToMarkdownConverter(dump_dir=str(report_dir))

    for json_file in sorted(report_dir.glob("session_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:100]:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            markdown_content = converter._generate_markdown(data)
            texts.append(markdown_content)
            metadatas.append({
                "session_id": json_file.stem,
                "user_query": data.get("user_query", "")[:200],
            })
        except Exception as e:
            errors.append(f"{json_file.name}: {e}")
    
    indexed = engine.add_documents(texts, metadatas, collection_name=collection_name) if texts else 0
    return {"status": "success", "indexed": indexed, "errors": errors, "collection": collection_name}


def create_knowledge_base(name: str = "finance_knowledge", description: str = "金融知识库") -> bool:
    try:
        get_rag_engine()
        return True
    except: return False


__all__ = ["FinanceRAGEngine", "RAGConfig", "get_rag_engine", "index_session_reports", "create_knowledge_base", "Document", "simple_text_splitter"]