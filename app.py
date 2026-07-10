import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
CORS(app)

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError("没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

import feedparser


def get_news_data():

    rss_url = "https://feeds.bbci.co.uk/news/technology/rss.xml"

    feed = feedparser.parse(rss_url)

    news = []

    for item in feed.entries[:10]:

        news.append({
            "title": item.title,
            "source": "BBC Technology",
            "url": item.link
        })

    return news

@app.route("/")
def home():
    return "新闻 AI Agent 后端运行正常"


@app.route("/api/summary", methods=["GET", "POST"])
def generate_summary():
    try:
        # 接收网页发送来的新闻
        data = request.get_json(silent=True) or {}
        news_data = data.get("news")

        # 暂时没有真实新闻时，使用演示新闻
        if not news_data:
            news_data = get_news_data()

        news_text = json.dumps(
            news_data,
            ensure_ascii=False
        )[:6000]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": """
你是一个新闻摘要 AI Agent。

请分析用户提供的新闻，完成以下任务：

1. 找出最重要的新闻
2. 合并重复内容
3. 按重要程度排序
4. 生成4张新闻摘要卡片
5. 只输出JSON数组，不要输出解释和Markdown

必须严格使用以下格式：

[
  {
    "category": "分类",
    "headline": "简短标题",
    "summary": "简单易懂的摘要",
    "source": "新闻来源"
  }
]
"""
                },
                {
                    "role": "user",
                    "content": f"请分析以下新闻：\n{news_text}"
                }
            ],
            temperature=0.3
        )

        raw_text = response.choices[0].message.content.strip()

        # 清除模型偶尔添加的 Markdown 代码块
        raw_text = raw_text.replace("```json", "")
        raw_text = raw_text.replace("```", "")
        raw_text = raw_text.strip()

        cards = json.loads(raw_text)

        if not isinstance(cards, list):
            raise ValueError("AI 返回的内容不是卡片数组")

        return jsonify({
            "success": True,
            "cards": cards
        })

    except json.JSONDecodeError:
        return jsonify({
            "success": False,
            "error": "AI 返回的数据格式不正确，请再次点击生成"
        }), 500

    except Exception as error:
        print("生成摘要失败：", error)

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)