"""
下载优化的中文情感分析预训练模型
使用 uer/roberta-base-finetuned-dianping-chinese 模型，专为中文评论情感分析优化
"""
import os
import sys
from pathlib import Path


def download_bert_model():
    """下载预训练的中文情感分析 BERT 模型"""
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        # 设置国内镜像源
        os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
        
        # 使用公开可用的中文情感分析模型
        # uer/roberta-base-finetuned-dianping-chinese 是在大众点评评论上fine-tune的模型
        model_name = "uer/roberta-base-finetuned-dianping-chinese"
        models_dir = Path(__file__).parent.parent / "models"
        model_path = models_dir / "bert-sentiment-model"
        
        print("开始下载模型: " + model_name)
        print("目标路径: " + str(model_path))
        print("这可能需要 5-15 分钟（取决于网络速度）...")
        
        # 下载 tokenizer
        print("正在下载 tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        # 下载模型
        print("正在下载模型文件...")
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        # 保存到本地
        models_dir.mkdir(exist_ok=True, parents=True)
        print("正在保存到本地...")
        tokenizer.save_pretrained(str(model_path))
        model.save_pretrained(str(model_path))
        
        print("模型下载完成！已保存到: " + str(model_path))
        print("后续使用将直接从本地加载，无需再下载")
        
        # 验证文件完整性
        expected_files = ['config.json', 'pytorch_model.bin', 'tokenizer.json', 'vocab.txt']
        print("\n验证文件完整性:")
        for file_name in expected_files:
            file_path = model_path / file_name
            if file_path.exists():
                print("  [OK] " + file_name)
            else:
                print("  [缺失] " + file_name)
        
        return True
        
    except ImportError:
        print("缺少依赖，请先运行:")
        print("pip install -i https://mirrors.aliyun.com/pypi/simple/ transformers torch")
        return False
    except Exception as e:
        print("下载失败: " + str(e))
        print("建议：")
        print("1. 检查网络连接")
        print("2. 试试用其他镜像源")
        print("3. 或者直接用方案 1（词典方法）")
        return False


if __name__ == "__main__":
    # 设置 stdout 编码
    sys.stdout.reconfigure(encoding='utf-8')
    download_bert_model()
