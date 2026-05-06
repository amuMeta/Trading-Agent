"""
金融知识库初始化脚本

预填充股票投资相关的专业知识到向量数据库：
1. A股交易规则
2. 财务指标解读
3. 技术分析基础知识
4. 风险管理原则
5. 行业分析框架

使用方法:
    python -m src.rag.init_knowledge_base
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.engine import get_rag_engine


FINANCE_KNOWLEDGE = [
    {
        "content": """股票基本面分析核心指标解读：

一、盈利能力指标
1. 净利润（Net Profit）：企业税后利润，反映最终经营成果
2. 毛利率（Gross Margin）= (营业收入 - 营业成本) / 营业收入，反映定价权和成本控制能力
3. 净利率（Net Margin）= 净利润 / 营业收入，反映最终盈利能力
4. ROE（净资产收益率）= 净利润 / 净资产，反映股东权益回报水平，ROE>15%为优质公司
5. ROA（总资产收益率）= 净利润 / 总资产，反映资产利用效率

二、成长能力指标
1. 营收增长率：营业收入同比或环比增长情况
2. 净利润增长率：净利润同比或环比增长情况
3. 季度环比增长：连续季度变化趋势

三、财务健康指标
1. 资产负债率 = 总负债 / 总资产，消费类<60%，金融类<90%为合理
2. 流动比率 = 流动资产 / 流动负债，>1.5表示短期偿债能力良好
3. 速动比率 = (流动资产-存货) / 流动负债，>1表示理想

四、估值指标
1. PE（市盈率）= 股价 / 每股收益，行业平均水平15-25倍，银行/钢铁等周期股例外
2. PB（市净率）= 股价 / 每股净资产，<1为破净，>5为高估
3. PS（市销率）= 股价 / 每股销售额，适用于成长型公司
4. EV/EBITDA：企业价值与息税折旧前利润比值

五、现金流指标
1. 经营现金流/净利润比值：>1为优质，说明利润是真金白银
2. 自由现金流（FCF）：经营现金流 - 资本支出
3. 分红率：分红/净利润，稳定分红率30-50%为佳""",
        "metadata": {"category": "fundamental_analysis", "source": "financial_indicators"}
    },
    {
        "content": """A股交易规则汇总：

一、交易时间
1. 竞价时间：9:15-9:25（开盘集合竞价）、9:30-11:30、13:00-15:00
2. 盘后定价交易：15:05-15:30（以收盘价成交）

二、交易单位
1. 最小买入单位：100股（1手）
2. 最小卖出单位：100股或不足100股的零股
3. 申报价格最小变动单位：0.01元

三、涨跌幅限制
1. 普通股票：上下10%
2. ST/*ST股票：上下5%
3. 新股上市首日：上下44%
4. 科创板/创业板：上下20%
5. 退市整理期股票：上下20%

四、交易制度
1. T+1制度：当天买入不能当天卖出
2. 竞价交易：价格优先、时间优先原则
3. 主板最大申报数量：100万股
4. 科创板最大申报数量：100万股

五、费用构成
1. 佣金：不超过成交金额的0.3%，起点5元
2. 印花税：卖出时收取0.1%（仅卖出）
3. 过户费：沪市收取0.001%，深市免收

六、风险控制规则
1. 异常波动停牌核查机制
2. 熔断机制（已暂停）
3. 异动公告制度""",
        "metadata": {"category": "trading_rules", "source": "a_share_rules"}
    },
    {
        "content": """技术分析核心指标与应用：

一、趋势指标
1. 移动平均线（MA）
   - 5日均线：短期趋势，短期操作参考
   - 20日均线：中期趋势，重要支撑/压力位
   - 60日均线：中长期趋势，牛熊分界线
   - 黄金交叉：短期均线向上穿越长期均线，看涨信号
   - 死亡交叉：短期均线向下穿越长期均线，看跌信号

2. MACD（指数平滑异同移动平均线）
   - DIF线 > 0且MACD柱状图放大：多头趋势
   - DIF线 < 0且MACD柱状图放大：空头趋势
   - 金叉：DIF上穿DEA，看涨
   - 死叉：DIF下穿DEA，看跌

二、动量指标
1. RSI（相对强弱指标）
   - RSI>80：超买区域，可能回调
   - RSI<20：超卖区域，可能反弹
   - 50为多空分界线

2. KDJ（随机指标）
   - K值>80超买，D值>80超买
   - K值<20超卖，D值<20超卖
   - 金叉：K上穿D
   - 死叉：K下穿D

三、成交量分析
1. 量增价涨：上涨趋势中放量为健康信号
2. 量增价跌：可能见顶信号
3. 地量：成交量极度萎缩，可能见底
4. 天量：历史高位天量可能见顶

四、支撑与压力
1. 前期高点/低点
2. 均线系统支撑
3. 跳空缺口回补""",
        "metadata": {"category": "technical_analysis", "source": "technical_indicators"}
    },
    {
        "content": """投资组合风险管理原则：

一、仓位管理
1. 单只股票仓位不超过总市值20%
2. 单一行业仓位不超过总市值30%
3. 持仓集中度：前5大股票不超过60%
4. 现金仓位：保留5-10%应对突发情况

二、止损原则
1. 亏损止损：单只股票亏损超过7-10%考虑止损
2. 技术止损：跌破重要支撑位（均线、趋势线）止损
3. 逻辑止损：公司基本面发生恶化时止损
4. 时间止损：3个月内未如预期上涨重新评估

三、分散化原则
1. 行业分散：配置3-5个不同行业
2. 周期分散：兼顾成长股和价值股
3. 市值分散：大中小盘均衡配置
4. 地区分散：A股、港股、美股适度配置

四、风险控制指标
1. 最大回撤控制：控制在15-20%以内
2. 夏普比率：>1为良好，>2为优秀
3. 波动率控制：单日最大跌幅不超过3%

五、情绪管理
1. 不追涨杀跌
2. 不重仓单一股票
3. 不频繁交易
4. 制定计划并严格执行""",
        "metadata": {"category": "risk_management", "source": "portfolio_management"}
    },
    {
        "content": """行业分析框架与估值方法：

一、行业生命周期
1. 初创期：行业刚起步，技术不成熟，风险高
2. 成长期：需求快速增长，行业标准形成，竞争激烈
3. 成熟期：市场饱和，竞争格局稳定，龙头效应明显
4. 衰退期：需求下降，行业萎缩

二、行业竞争分析（五力模型）
1. 行业内现有竞争者：数量、实力、市场份额
2. 潜在进入者：壁垒高低（技术、品牌、资金）
3. 替代品威胁：替代品性能和性价比
4. 供应商议价能力：集中度、可替代性
5. 客户议价能力：采购量、信息透明度

三、行业估值方法
1. 银行业：PB估值为主，0.5-1.5倍为合理
2. 保险业：PEV（内含价值）估值
3. 房地产业：NAV（净资产价值）估值
4. 消费品：PE+品牌溢价
5. 周期行业：PB+景气度指标

四、龙头公司特征
1. 市场份额领先
2. 定价能力强
3. 现金流充裕
4. 研发投入高
5. 管理层优秀""",
        "metadata": {"category": "industry_analysis", "source": "valuation_methods"}
    },
    {
        "content": """基本面分析报告框架：

一、公司概述
1. 公司基本信息（名称、代码、主营业务）
2. 股权结构与股东情况
3. 公司发展历程与里程碑

二、行业分析
1. 行业规模与增速
2. 竞争格局与市场地位
3. 行业发展趋势与政策影响

三、业务分析
1. 主营构成与收入占比
2. 核心产品/服务分析
3. 商业模式与盈利模式
4. 产能布局与供应能力

四、财务分析
1. 盈利能力（收入、利润、毛利率趋势）
2. 成长能力（增速分析）
3. 财务健康（负债结构、现金流）
4. 估值水平（PE、PB、EV/EBITDA）

五、风险因素
1. 行业风险
2. 经营风险
3. 财务风险
4. 政策风险

六、投资结论
1. 核心逻辑
2. 目标价位
3. 风险收益比""",
        "metadata": {"category": "analysis_framework", "source": "research_report_template"}
    },
    {
        "content": """财务报表关键阅读要点：

一、资产负债表
1. 资产结构：流动/非流动资产比例
2. 负债结构：有息/无息负债比例
3. 所有者权益：实收资本、资本公积、未分配利润
4. 重点关注：应收账款、存货、商誉、有息负债

二、利润表
1. 营业收入：增速及构成
2. 营业成本：成本结构及变化趋势
3. 四项费用：销售、管理、研发、财务费用
4. 净利润：扣非净利润（非经常性损益前）

三、现金流量表
1. 经营现金流：>0且持续增长为佳
2. 投资现金流：负值说明在扩张
3. 筹资现金流：了解融资活动
4. 重点：经营现金流/净利润比值>1

四、财务配平关系
1. 资产负债表 = 利润表 + 现金流量表
2. 资产 = 负债 + 所有者权益
3. 现金及等价物期末 - 期初 = 经营 + 投资 + 筹资

五、财报附注关注点
1. 会计政策变更
2. 重要子公司情况
3. 关联交易
4. 或有负债""",
        "metadata": {"category": "financial_statements", "source": "financial_report_reading"}
    },
    {
        "content": """价值投资核心原则：

一、核心理念
1. 买股票就是买公司：关注企业内在价值
2. 安全边际：以低于内在价值的价格买入
3. 长期持有：陪伴优质企业成长
4. 能力圈：不投不懂的公司

二、估值方法
1. 绝对估值法
   - DCF（现金流折现）：预测未来现金流并折现
   - DDM（股息折现）：适用于高分红企业

2. 相对估值法
   - PE：与行业平均、历史水平对比
   - PB：破净股可能存在价值陷阱
   - PS：适用于成长型企业

三、优质公司特征
1. 护城河：品牌、技术、网络效应、成本优势
2. 稳定盈利能力：连续多年ROE>15%
3. 良好现金流：经营现金流持续为正
4. 合理分红：分红率稳定且可持续
5. 优秀管理层：诚实守信、能力出众

四、常见价值陷阱
1. 低PE陷阱：夕阳行业或一次性收益
2. 低PB陷阱：资产质量差或会计处理问题
3. 破净陷阱：银行股坏账、周期股高峰

五、卖出时机
1. 估值过高：明显高于内在价值
2. 基本面恶化：公司竞争力下降
3. 发现更好机会：更高风险收益比
4. 系统性风险：市场整体泡沫""",
        "metadata": {"category": "value_investing", "source": "investment_philosophy"}
    },
    {
        "content": """成长股投资分析框架：

一、成长股特征
1. 营收增速：连续3年>20%
2. 净利润增速：连续3年>25%
3. 所处行业：符合经济发展方向
4. 市场份额：持续提升

二、成长来源分析
1. 行业渗透率：还有多大增长空间
2. 市占率提升：从竞争对手抢夺份额
3. 新产品/新市场：开拓新业务领域
4. 并购整合：外延式增长

三、成长股估值
1. PEG = PE / 净利润增速，<1为低估
2. PS = 市值 / 营收，适用于初期成长股
3. EV/S：企业价值/销售额

四、成长股风险
1. 估值泡沫：高增长预期难兑现
2. 竞争加剧：蓝海变红海
3. 资金链断裂：快速扩张消耗现金
4. 技术替代：被新产品颠覆

五、成长股筛选指标
1. 营收增速>30%
2. 毛利率稳定或提升
3. 研发投入占比>5%
4. 员工数量增长
5. 预收账款增加（产品供不应求）""",
        "metadata": {"category": "growth_investing", "source": "growth_stock_analysis"}
    },
    {
        "content": """资金流向分析要点：

一、资金流向分类
1. 主力资金：机构投资者大额买卖
2. 散户资金：中小投资者买卖
3. 北向资金：外资通过沪股通/深股通买入
4. 南向资金：内地投资者买入港股

二、资金流向指标
1. 超大单净流入：单笔>100万元
2. 大单净流入：单笔>20万元
3. 中单/小单净流入：反映散户情绪

三、北向资金分析
1. 连续净买入：外资持续看好
2. 重点持仓：贵州茅台、宁德时代等核心资产
3. 行业偏好：消费、新能源、科技

四、资金流向应用
1. 跟庄操作：跟随主力资金方向
2. 反向指标：极端贪婪/恐惧时反转
3. 趋势确认：资金流入配合价格上涨

五、资金流与股价关系
1. 价涨量增：上涨趋势健康
2. 价涨量缩：上涨动力可能不足
3. 放量滞涨：可能见顶
4. 缩量下跌：可能见底""",
        "metadata": {"category": "money_flow", "source": "institutional_flow_analysis"}
    }
]


def init_finance_knowledge(clear_existing: bool = False) -> dict:
    """
    初始化金融知识库

    Args:
        clear_existing: 是否清空现有数据

    Returns:
        dict: 初始化结果统计
    """
    print("=" * 60)
    print("金融知识库初始化")
    print("=" * 60)

    try:
        engine = get_rag_engine()
        print(f"RAG引擎: {'已连接' if engine.is_initialized else '未初始化'}")

        if clear_existing:
            print("清空现有 finance_knowledge 集合...")
            try:
                engine.delete_collection("finance_knowledge")
                print(f"  [OK] 集合不存在或已清空")
            except:
                print("  ℹ 集合不存在或已清空")

        texts = [item["content"] for item in FINANCE_KNOWLEDGE]
        metadatas = [item["metadata"] for item in FINANCE_KNOWLEDGE]

        count = engine.add_documents(
            texts=texts,
            metadatas=metadatas,
            collection_name="finance_knowledge"
        )

        info = engine.get_collection_info("finance_knowledge")

        print(f"\n[OK] 知识库初始化完成")
        print(f"  - 新增文档: {len(texts)} 篇")
        print(f"  - 总片段数: {count}")
        print(f"  - 集合文档数: {info.get('count', 0)}")

        print("\n知识类别:")
        categories = set(item["metadata"]["category"] for item in FINANCE_KNOWLEDGE)
        for cat in sorted(categories):
            print(f"  - {cat}")

        return {
            "status": "success",
            "documents_added": len(texts),
            "chunks_added": count,
            "total_in_collection": info.get("count", 0),
            "categories": list(categories)
        }

    except Exception as e:
        print(f"\n[FAIL] 初始化失败: {e}")
        return {"status": "error", "error": str(e)}


def test_knowledge_retrieval():
    """测试知识检索"""
    print("\n" + "=" * 60)
    print("知识检索测试")
    print("=" * 60)

    try:
        engine = get_rag_engine()

        test_queries = [
            "如何分析股票的基本面",
            "A股交易规则有哪些",
            "技术分析指标怎么看",
            "如何控制投资风险"
        ]

        for query in test_queries:
            print(f"\n查询: {query}")
            results = engine.search(query, top_k=2, collection_name="finance_knowledge")
            for i, r in enumerate(results, 1):
                print(f"  [{i}] score={r['score']:.3f}: {r['content'][:80]}...")
            if not results:
                print("  (无结果)")

    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="金融知识库初始化")
    parser.add_argument("--clear", action="store_true", help="清空现有数据")
    parser.add_argument("--test", action="store_true", help="仅运行测试")
    args = parser.parse_args()

    if args.test:
        test_knowledge_retrieval()
    else:
        result = init_finance_knowledge(clear_existing=args.clear)
        if result["status"] == "success":
            if input("\n是否运行检索测试? (y/N): ").strip().lower() == "y":
                test_knowledge_retrieval()