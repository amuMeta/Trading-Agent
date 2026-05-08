"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface DocumentInfo {
  name: string;
  count: number;
  exists: boolean;
  sample_docs: Array<{
    id: string;
    content_preview: string;
    metadata: Record<string, unknown>;
  }>;
}

interface UploadResult {
  status: string;
  filename?: string;
  chars?: number;
  chunks?: number;
  error?: string;
}

interface RecallResult {
  content: string;
  score: number;
  metadata: Record<string, unknown>;
}

export default function KnowledgePage() {
  const [activeTab, setActiveTab] = useState<"recall" | "upload" | "manage">("recall");
  const [collectionName, setCollectionName] = useState("user_knowledge");
  const [kbInfo, setKbInfo] = useState<DocumentInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);

  // 新增：所有集合列表
  const [allCollections, setAllCollections] = useState<Array<{name: string; count: number}>>([]);
  // 新增：快速搜索
  const [quickSearch, setQuickSearch] = useState("");
  const [quickSearchResults, setQuickSearchResults] = useState<RecallResult[]>([]);

  // 召回测试相关
  const [query, setQuery] = useState("");
  const [recallResults, setRecallResults] = useState<RecallResult[]>([]);
  const [testing, setTesting] = useState(false);
  const [tested, setTested] = useState(false);

  useEffect(() => {
    fetchAllCollections();
  }, []);

  const fetchAllCollections = async () => {
    try {
      const res = await fetch("/api/rag/collections");
      if (res.ok) {
        const data = await res.json();
        setAllCollections(data.collections || []);
      }
    } catch (error) {
      console.error("获取集合列表失败:", error);
    }
  };

  const fetchKbInfo = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/rag/knowledge/info?collection=${collectionName}`);
      if (res.ok) {
        const data = await res.json();
        setKbInfo(data);
      }
    } catch (error) {
      console.error("获取知识库信息失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSearch = async () => {
    if (!quickSearch.trim() || !collectionName) return;

    try {
      const res = await fetch("/api/rag/knowledge/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: quickSearch,
          top_k: 5,
          collection: collectionName,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setQuickSearchResults(data.results || []);
      }
    } catch (error) {
      console.error("快速搜索失败:", error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadResult(null);

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }
    formData.append("collection", collectionName);

    try {
      const res = await fetch("/api/rag/upload/multiple", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadResult(data);
        setUploadProgress(100);
        fetchKbInfo();
        fetchAllCollections();
      } else {
        const error = await res.json();
        setUploadResult({ status: "error", error: error.detail || "上传失败" });
      }
    } catch (error) {
      setUploadResult({ status: "error", error: "网络错误" });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  };

  const handleDeleteKb = async () => {
    if (!confirm("确定要清空整个知识库吗？此操作不可恢复！")) return;

    try {
      const res = await fetch(`/api/rag/knowledge?collection=${collectionName}`, {
        method: "DELETE",
      });

      if (res.ok) {
        alert("知识库已清空");
        fetchKbInfo();
        fetchAllCollections();
      }
    } catch (error) {
      console.error("删除失败:", error);
    }
  };

  const handleRecallTest = async () => {
    if (!query.trim() || testing) return;

    setTesting(true);
    setTested(false);
    setRecallResults([]);

    try {
      const res = await fetch("/api/rag/knowledge/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          top_k: 5,
          collection: collectionName,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setRecallResults(data.results || []);
      }
    } catch (error) {
      console.error("召回测试失败:", error);
    } finally {
      setTesting(false);
      setTested(true);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return "text-green-600";
    if (score >= 0.7) return "text-blue-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreLabel = (score: number) => {
    if (score >= 0.9) return "高相关";
    if (score >= 0.7) return "中相关";
    if (score >= 0.5) return "低相关";
    return "弱相关";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors text-sm"
            >
              ← 返回主界面
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-gray-800">📚 知识库管理</h1>
              <p className="text-sm text-gray-500">管理您的私有金融知识库</p>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            知识库: <span className="font-medium">{collectionName}</span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto p-6">
        {/* Tab切换 */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab("recall")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "recall"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
            }`}
          >
            🔍 召回测试
          </button>
          <button
            onClick={() => setActiveTab("upload")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "upload"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
            }`}
          >
            📤 上传文档
          </button>
          <button
            onClick={() => setActiveTab("manage")}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === "manage"
                ? "bg-blue-500 text-white"
                : "bg-white text-gray-700 hover:bg-gray-100 border border-gray-200"
            }`}
          >
            📋 文档管理
          </button>
        </div>

        {/* Tab内容 */}
        {activeTab === "recall" && (
          <div className="space-y-6">
            {/* 召回测试区域 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <h2 className="text-lg font-semibold text-gray-800">🔍 召回测试</h2>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  当前知识库: {kbInfo?.count || 0} 个片段
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-4">
                输入查询文本，测试知识库是否能正确召回相关内容。不经过LLM生成，直接展示向量检索结果。
              </p>

              <div className="flex gap-3">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRecallTest()}
                  placeholder="输入查询文本，例如：公司的营收增长情况、年报核心内容..."
                  className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={testing}
                />
                <button
                  onClick={handleRecallTest}
                  disabled={testing || !query.trim()}
                  className="bg-blue-500 text-white px-6 py-3 rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                >
                  {testing ? "测试中..." : "开始测试"}
                </button>
              </div>
            </div>

            {/* 召回结果 */}
            {tested && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  📊 召回结果 (top_k=5)
                </h3>

                {recallResults.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-3">🔎</div>
                    <div className="text-lg font-medium mb-2">未召回任何结果</div>
                    <div className="text-sm">
                      知识库中可能没有与&quot;{query}&quot;相关的内容
                    </div>
                    <div className="text-sm text-gray-400 mt-2">
                      建议：1. 检查上传的文档是否包含相关内容 | 2. 尝试不同的关键词
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {recallResults.map((result, index) => (
                      <div
                        key={index}
                        className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className="bg-blue-500 text-white text-sm font-medium px-2 py-1 rounded">
                              #{index + 1}
                            </span>
                            <span className="text-sm font-medium text-gray-700">
                              {typeof result.metadata?.filename === 'string'
                                ? result.metadata.filename
                                : "未知来源"}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-sm font-medium ${getScoreColor(result.score)}`}
                            >
                              {(result.score * 100).toFixed(1)}%
                            </span>
                            <span
                              className={`text-xs px-2 py-1 rounded ${
                                result.score >= 0.7
                                  ? "bg-green-100 text-green-700"
                                  : result.score >= 0.5
                                  ? "bg-yellow-100 text-yellow-700"
                                  : "bg-red-100 text-red-700"
                              }`}
                            >
                              {getScoreLabel(result.score)}
                            </span>
                          </div>
                        </div>

                        <div className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 mb-3">
                          {result.content}
                        </div>

                        {result.metadata && Object.keys(result.metadata).length > 0 && (
                          <div className="text-xs text-gray-400">
                            {typeof result.metadata?.file_extension === 'string' && (
                              <span className="mr-3">
                                类型: {result.metadata.file_extension}
                              </span>
                            )}
                            {typeof result.metadata?.file_size_mb === 'number' && (
                              <span>
                                大小: {result.metadata.file_size_mb} MB
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}

                    <div className="text-xs text-gray-500 text-center pt-4 border-t">
                      共召回 {recallResults.length} 条结果 | 相似度阈值建议: ≥70%
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 召回说明 */}
            <div className="bg-blue-50 rounded-xl p-4 text-blue-800">
              <div className="font-medium mb-2">💡 召回测试说明</div>
              <ul className="text-sm space-y-1">
                <li>• 召回测试用于验证知识库中的文档是否能被正确检索</li>
                <li>• 相似度 ≥70% 通常表示高质量匹配</li>
                <li>• 如召回结果不理想，可尝试：上传更多相关文档 / 调整查询关键词</li>
                <li>• 此功能不经过LLM生成，直接返回向量检索结果</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === "upload" && (
          <div className="space-y-6">
            {/* 上传区域 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                <div className="text-5xl mb-4">📄</div>
                <div className="text-lg font-medium text-gray-700 mb-2">
                  拖拽文件到此处或点击上传
                </div>
                <div className="text-sm text-gray-500 mb-4">
                  支持格式：PDF, Word(.docx), TXT, Markdown
                </div>
                <label className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 cursor-pointer font-medium transition-colors">
                  <span>选择文件</span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt,.md"
                    multiple
                    onChange={handleFileUpload}
                    disabled={uploading}
                    className="hidden"
                  />
                </label>
              </div>

              {/* 上传进度 */}
              {uploading && (
                <div className="mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">上传中...</span>
                    <span className="text-sm text-gray-600">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* 上传结果 */}
              {uploadResult && (
                <div
                  className={`mt-4 p-4 rounded-lg ${
                    uploadResult.status === "success"
                      ? "bg-green-50 text-green-800"
                      : "bg-red-50 text-red-800"
                  }`}
                >
                  {uploadResult.status === "success" ? (
                    <div>
                      <div className="font-medium">✅ 上传成功！</div>
                      <div className="text-sm mt-1">
                        {uploadResult.filename && `文件名: ${uploadResult.filename}`}
                        {uploadResult.chars && `，字符数: ${uploadResult.chars}`}
                        {uploadResult.chunks && `，切片数: ${uploadResult.chunks}`}
                      </div>
                    </div>
                  ) : (
                    <div className="font-medium">❌ 上传失败</div>
                  )}
                  {uploadResult.error && (
                    <div className="text-sm mt-1">{uploadResult.error}</div>
                  )}
                </div>
              )}
            </div>

            {/* 批量上传说明 */}
            <div className="bg-blue-50 rounded-xl p-4 text-blue-800">
              <div className="font-medium mb-2">💡 批量上传提示</div>
              <ul className="text-sm space-y-1">
                <li>• 支持同时选择多个文件进行批量上传</li>
                <li>• PDF和Word文档会自动提取文本内容</li>
                <li>• 文档会被分割成小块存入向量数据库</li>
                <li>• 上传后可使用召回测试验证检索效果</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === "manage" && (
          <div className="space-y-6">
            {/* 知识库概览 - 全部集合 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">📊 知识库概览</h2>
                <button
                  onClick={fetchKbInfo}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors flex items-center gap-1"
                >
                  <span>🔄</span> 刷新
                </button>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">加载中...</div>
              ) : allCollections.length > 0 ? (
                <div className="space-y-4">
                  {/* 统计卡片 */}
                  <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-blue-600">{allCollections.length}</div>
                      <div className="text-sm text-blue-600 mt-1">集合数量</div>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {allCollections.reduce((sum, c) => sum + c.count, 0)}
                      </div>
                      <div className="text-sm text-green-600 mt-1">文档片段总数</div>
                    </div>
                    <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-purple-600">
                        {allCollections.filter(c => c.count > 0).length}
                      </div>
                      <div className="text-sm text-purple-600 mt-1">有数据的集合</div>
                    </div>
                    <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {allCollections.reduce((sum, c) => sum + c.count, 0) > 0 ? "✅" : "❌"}
                      </div>
                      <div className="text-sm text-orange-600 mt-1">知识库状态</div>
                    </div>
                  </div>

                  {/* 集合列表 */}
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">集合名称</th>
                          <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">文档数</th>
                          <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">状态</th>
                          <th className="px-4 py-3 text-center text-sm font-medium text-gray-600">操作</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {allCollections.map((col) => (
                          <tr key={col.name} className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                                <span className="font-medium text-gray-800">{col.name}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className={`px-2 py-1 rounded-full text-sm font-medium ${
                                col.count > 0
                                  ? "bg-green-100 text-green-700"
                                  : "bg-gray-100 text-gray-500"
                              }`}>
                                {col.count} 片段
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <span className={`px-2 py-1 rounded text-xs ${
                                col.count > 0
                                  ? "bg-green-100 text-green-600"
                                  : "bg-yellow-100 text-yellow-600"
                              }`}>
                                {col.count > 0 ? "已索引" : "空"}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => {
                                    setCollectionName(col.name);
                                    fetchKbInfo();
                                  }}
                                  className="px-3 py-1 text-xs bg-blue-100 text-blue-600 rounded hover:bg-blue-200 transition-colors"
                                >
                                  查看
                                </button>
                                {col.count > 0 && (
                                  <button
                                    onClick={() => {
                                      setCollectionName(col.name);
                                      setActiveTab("recall");
                                    }}
                                    className="px-3 py-1 text-xs bg-green-100 text-green-600 rounded hover:bg-green-200 transition-colors"
                                  >
                                    搜索
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">暂无数据</div>
              )}
            </div>

            {/* 当前选中集合详情 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">
                  📁 当前选中: <span className="text-blue-600">{collectionName}</span>
                </h2>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={collectionName}
                    onChange={(e) => setCollectionName(e.target.value)}
                    placeholder="输入集合名称"
                    className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={fetchKbInfo}
                    className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
                  >
                    切换
                  </button>
                </div>
              </div>

              {loading ? (
                <div className="text-center py-8 text-gray-500">加载中...</div>
              ) : kbInfo ? (
                <div className="space-y-4">
                  {/* 集合统计 */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-gray-700">{kbInfo.count}</div>
                      <div className="text-sm text-gray-500 mt-1">文档片段</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4 text-center">
                      <div className="text-2xl font-bold text-gray-700">{kbInfo.sample_docs?.length || 0}</div>
                      <div className="text-sm text-gray-500 mt-1">示例文档</div>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4 text-center">
                      <div className={`text-2xl font-bold ${kbInfo.exists ? "text-green-600" : "text-red-600"}`}>
                        {kbInfo.exists ? "✅" : "❌"}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">数据库状态</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">暂无数据</div>
              )}
            </div>

            {/* 示例文档 */}
            {kbInfo?.sample_docs && kbInfo.sample_docs.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-gray-800">📝 文档片段预览</h2>
                  <span className="text-sm text-gray-500">共 {kbInfo.sample_docs.length} 条示例</span>
                </div>
                <div className="space-y-4">
                  {kbInfo.sample_docs.map((doc, index) => (
                    <div
                      key={doc.id || index}
                      className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="bg-blue-500 text-white text-xs font-medium px-2 py-1 rounded">
                            #{index + 1}
                          </span>
                          <span className="font-medium text-gray-700">
                            {typeof doc.metadata?.filename === 'string'
                              ? doc.metadata.filename
                              : typeof doc.metadata?.source === 'string'
                              ? doc.metadata.source
                              : `文档 ${index + 1}`}
                          </span>
                        </div>
                        {typeof doc.metadata?.category === 'string' && (
                          <span className="text-xs px-2 py-1 bg-purple-100 text-purple-600 rounded">
                            {String(doc.metadata.category)}
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-gray-600 line-clamp-3 bg-white rounded p-3 border border-gray-100">
                        {doc.content_preview}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 快速搜索 */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">🔍 快速搜索</h2>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={quickSearch}
                  onChange={(e) => setQuickSearch(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleQuickSearch()}
                  placeholder="输入关键词快速搜索当前集合..."
                  className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleQuickSearch}
                  className="bg-blue-500 text-white px-6 py-3 rounded-xl hover:bg-blue-600 font-medium transition-colors"
                >
                  搜索
                </button>
              </div>
              {quickSearchResults.length > 0 && (
                <div className="mt-4 space-y-2">
                  <div className="text-sm text-gray-500 mb-2">找到 {quickSearchResults.length} 条结果</div>
                  {quickSearchResults.map((result, index) => (
                    <div key={index} className="bg-gray-50 rounded-lg p-3 text-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-700">#{index + 1}</span>
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-600 rounded">
                          相似度: {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="text-gray-600 line-clamp-2">{result.content}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 危险操作 */}
            <div className="bg-red-50 rounded-xl p-6 border border-red-200">
              <h2 className="text-lg font-semibold text-red-800 mb-2">⚠️ 危险操作</h2>
              <p className="text-sm text-red-600 mb-4">
                清空知识库将删除所有已上传的文档，此操作不可恢复！
              </p>
              <button
                onClick={handleDeleteKb}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium transition-colors"
              >
                🗑️ 清空知识库
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}