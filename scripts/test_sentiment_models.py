"""
测试情感分析模型效果
比较 V1（词典方法）和 V2（BERT）的效果
"""
import sys
sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])

from engines.clustering.sentiment_analyzer_v1 import sentiment_analyzer_v1
from engines.clustering.sentiment_analyzer_v2 import get_bert_analyzer

# 测试样本
test_samples = [
    ("这本书非常精彩，强烈推荐！", "正面"),
    ("内容很枯燥，不建议购买", "负面"),
    ("情节跌宕起伏，人物刻画细腻", "正面"),
    ("浪费时间，完全不值这个价", "负面"),
    ("一般般吧，不算太好也不算太差", "中立"),
    ("刚开始觉得一般，后来越看越精彩", "正面"),
    ("包装精美，但内容空洞", "负面"),
    ("非常失望，和预期差距太大", "负面"),
    ("值得一读，收获很多", "正面"),
    ("不太推荐，性价比不高", "负面"),
]

def test_v1():
    print("=" * 50)
    print("测试 V1 模型（词典方法）")
    print("=" * 50)
    
    correct = 0
    for text, expected in test_samples:
        sentiment, confidence = sentiment_analyzer_v1.analyze(text)
        result = "✓" if sentiment == expected else "✗"
        if sentiment == expected:
            correct += 1
        print("[{}] 文本: {}".format(result, text))
        print("    预测: {} (置信度: {:.2f}) | 预期: {}".format(sentiment, confidence, expected))
        print()
    
    accuracy = correct / len(test_samples)
    print("V1 准确率: {:.2%}".format(accuracy))
    return accuracy

def test_v2():
    print("=" * 50)
    print("测试 V2 模型（BERT）")
    print("=" * 50)
    
    try:
        analyzer = get_bert_analyzer(use_gpu=False)
        
        correct = 0
        for text, expected in test_samples:
            sentiment, confidence = analyzer.analyze(text)
            result = "✓" if sentiment == expected else "✗"
            if sentiment == expected:
                correct += 1
            print("[{}] 文本: {}".format(result, text))
            print("    预测: {} (置信度: {:.2f}) | 预期: {}".format(sentiment, confidence, expected))
            print()
        
        accuracy = correct / len(test_samples)
        print("V2 准确率: {:.2%}".format(accuracy))
        return accuracy
        
    except Exception as e:
        print("BERT 模型加载失败: {}".format(e))
        return 0

if __name__ == "__main__":
    # 设置编码
    sys.stdout.reconfigure(encoding='utf-8')
    
    v1_acc = test_v1()
    print()
    v2_acc = test_v2()
    print()
    
    print("=" * 50)
    print("对比结果")
    print("=" * 50)
    print("V1 (词典方法): {:.2%}".format(v1_acc))
    print("V2 (BERT):    {:.2%}".format(v2_acc))
    
    if v2_acc > v1_acc:
        print("BERT 模型效果更好！")
    else:
        print("词典方法效果更好（或模型加载失败）")
