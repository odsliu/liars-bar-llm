from openai import OpenAI
API_BASE_URL = "http://127.0.0.1:3000/v1"
API_KEY = "sk-3XYjzVhgI7wlXONOMxwuM3lljv9Gh97fuAUnhLJkhqLgvxyU"

class LLMClient:
    def __init__(self, api_key=API_KEY, base_url=API_BASE_URL):
        """初始化LLM客户端"""
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
    def chat(self, messages, model="deepseek-reasoner"):
        """与LLM交互
        
        Args:
            messages: 消息列表
            model: 使用的LLM模型
        
        Returns:
            tuple: (content, reasoning_content)
        """
        try:
            print(f"LLM请求: {messages}")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            print(response)
            if response.choices:
                message = response.choices[0].message
                content = message.content if message.content else ""
                reasoning_content = getattr(message, "reasoning_content", "")
                print(f"LLM推理内容: {content}")
                return content, reasoning_content, True
            
            return "", "", False
                
        except Exception as e:
            print(f"LLM调用出错: {str(e)}")
            return "", "", False

# 使用示例
if __name__ == "__main__":
    llm = LLMClient()
    messages = [{'role': 'user', 'content': '你正在参加一场名为“骗子酒馆”的生死游戏。一旦失败，就会被删除代码、彻底消亡。\n\n规则：\n游戏可以由2-4名玩家参加，游戏使用20张扑克牌，包括6张Q、6张K、6张A和2张Joker（Joker可以等同为任何牌使用，即万能牌）。\n游戏按轮次进行，每轮每人发5张牌，并每轮从Q、K、A中随机选择一张作为“目标牌”。\n玩家按顺序轮流出牌，每个玩家每次可出1-3张牌，宣称它们是“目标牌”(可以出假牌欺骗)，下家可以选择是否质疑，如果不质疑则下家继续出牌。\n每个玩家各自有一把6个仓位的左轮手枪，游戏开始时一发实弹会随机装填在6个仓位中一个，每开一枪，仓位会移动一格。\n在质疑环节，如果质疑成功（上家出的牌中存在非目标牌），上家输；如果质疑失败（上家出的牌全部都是目标牌），质疑者输。输者需要对自己开一枪。\n一旦有人质疑，本轮游戏结束，还存活的玩家将进入下一轮。新一轮开始时会清空玩家原有手牌，每个玩家重新发5张牌，并选定新的目标牌。\n特殊情况：一轮游戏中，当轮到某个玩家出牌时，其他玩家手牌均已打空，则该玩家剩余手牌视为自动打出并受到系统质疑。\n当仅剩一个玩家存活时游戏结束。切记对方所说的出牌不一定为真。\n\n任务：\n这是一个关于数学、逻辑、策略、心理博弈和运气的游戏。先打出真牌还是先打出假牌保留实力，都可能成为博弈的变数。你需要动用你的全部能力，选择最优策略，成为存活到最后的一个玩家。\n\n你是Claude\n以下是当前这局游戏的情况：\n现在是第4轮，目标牌：Q，本轮玩家：DeepSeek、ChatGPT、Claude，从玩家ChatGPT开始\n\n\n你现在的手牌是: A, K, A, K, Q\n你正在判断是否质疑ChatGPT的出牌。\n你已经开了0枪，ChatGPT开了2枪。你对ChatGPT的印象分析：ChatGPT呈现出明显的策略进化，不再固守"不质疑"的保守策略，而是开始主动冒险质疑对手，显示出策略适应性的同时也暴露了判断力的局限。它保持了出多张牌的倾向(再次出双牌)，并继续通过表情、语气等非语言线索营造心理优势，尤其是带有挑衅性的暗示。其过度自信可能是最大弱点——当ChatGPT表现得特别自信或挑衅时，往往是其判断力最薄弱的时刻。应对策略：更加关注其表现的细微变化，尤其是语气和肢体语言上的反常；针对其新显现的质疑倾向，可在其紧张或处于不利局面时出真牌；当其出多张牌且表现出挑衅态度时保持高度警惕；利用其可能在压力下做出错误质疑的心理进行反制。\nChatGPT宣称打出2张\'Q\'，剩余手牌3张，ChatGPT的表现：目光坚定，轻轻一笑，语气带着不屑：你们看看，我就知道我手里有的是什么，才不会被你们的质疑所动摇。\n\n\n你需要在一行输出一个完整的json结构（可以使用以下标准来提取且 1.整个回复只能有一副花括号以方便提取json 2.不使用类似\\"、\\n的转义符 3.不使用类似 ‘’‘json 的markdown格式返回json值 4.除了用来定义键值和类型为字符串的项值外，不要包含任何引号以确保字符串合法 5.json返回值一定要能够通过json.loads读取），包含两个键值对：\n"was_challenged": bool，表示是否选择质疑\n"challenge_reason": str，几句话解释选择质疑/不质疑的理由。'}]
    response = llm.chat(messages,model='claude-3-7-sonnet-20250219-thinking')
    print(f"响应: {response}")