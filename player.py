import random
import json, json_repair
import re
import time
from typing import *

import search
from llm_client import LLMClient
from tkinter.messagebox import showwarning

RULE_BASE_PATH = "prompt/rule_base.txt"
PLAY_CARD_PROMPT_TEMPLATE_PATH = "prompt/play_card_prompt_template.txt"
CHALLENGE_PROMPT_TEMPLATE_PATH = "prompt/challenge_prompt_template.txt"
REFLECT_PROMPT_TEMPLATE_PATH = "prompt/reflect_prompt_template.txt"

class Player:
    def __init__(self, name: str, model_name: str):
        """初始化玩家
        
        Args:
            name: 玩家名称
            model_name: 使用的LLM模型名称
        """
        self.name = name
        self.hand = []
        self.alive = True
        _, self.pars = search.search_bing_for_model_params(model_name)
        self.parameter = []
        self.model_par = '-1.0B'
        for i, result in enumerate(self.pars, 1):
            # 收集找到的参数大小
            if result['param_size'] != "未找到参数信息":
                self.parameter.append(result['param_size'])
        for size in self.parameter:
            if float(size[:-1]) >= float(self.model_par[:-1]):
                self.model_par = size
        del self.pars,self.parameter
        self.bullet_position = random.randint(0, 5)
        self.current_bullet_position = 0
        self.opinions = {}
        
        # LLM相关初始化
        self.llm_client = LLMClient()
        self.model_name = model_name

    def _read_file(self, filepath: str) -> str:
        """读取文件内容"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取文件 {filepath} 失败: {str(e)}")
            return ""

    def print_status(self) -> None:
        """打印玩家状态"""
        print(f"{self.name} （自动识别参数量：{self.model_par}） - 手牌: {', '.join(self.hand)} - "
              f"子弹位置: {self.bullet_position} - 当前弹舱位置: {self.current_bullet_position}")
        
    def init_opinions(self, other_players: List["Player"]) -> None:
        """初始化对其他玩家的看法
        
        Args:
            other_players: 其他玩家列表
        """
        self.opinions = {
            player.name: "你还不了解这个玩家"
            for player in other_players
            if player.name != self.name
        }

    def choose_cards_to_play(self,
                        round_base_info: str,
                        round_action_info: str,
                        play_decision_info: str): # -> Dict:
        """
        玩家选择出牌
        
        Args:
            round_base_info: 轮次基础信息
            round_action_info: 轮次操作信息
            play_decision_info: 出牌决策信息
            
        Returns:
            tuple: (结果字典, 推理内容)
            - 结果字典包含played_cards, behavior和play_reason
            - 推理内容为LLM的原始推理过程
        """
        # 读取规则和模板
        rules = self._read_file(RULE_BASE_PATH)
        template = self._read_file(PLAY_CARD_PROMPT_TEMPLATE_PATH)
        
        # 准备当前手牌信息
        current_cards = ", ".join(self.hand)
        
        # 填充模板
        prompt = template.format(
            rules=rules,
            self_name=self.name,
            round_base_info=round_base_info,
            round_action_info=round_action_info,
            play_decision_info=play_decision_info,
            current_cards=current_cards
        )
        
        # 尝试获取有效的JSON响应，最多重试五次
        for attempt in range(3):
            # 每次都发送相同的原始prompt
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            try:
                content, reasoning_content, suc = self.llm_client.chat(messages, model=self.model_name)

                if not suc:
                    continue

                # 尝试从内容中提取JSON部分
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    json_str = json_match.group(1)
                    json_str = re.sub(r'\\', '', json_str)
                    json_str = json_str.replace('\n','')
                    if json_str.count('"played_cards"') <= 0 and json_str.count('played_cards') >= 1:
                        json_str = json_str.replace('played_cards','"played_cards"',1)
                    if json_str.count('"behavior"') <= 0 and json_str.count('behavior') >= 1:
                        json_str = json_str.replace('behavior','"behavior"',1)
                    if json_str.count('"play_reason"') <= 0 and json_str.count('play_reason') >= 1:
                        json_str = json_str.replace('play_reason','"play_reason"',1)
                    with open('res.txt','w+') as f:
                        f.write(content)
                    try:
                        result = json.loads(json_str)
                    except:
                        result = json_repair.loads(json_str)
                    
                    # 验证JSON格式是否符合要求
                    if all(key in result for key in ["played_cards", "behavior", "play_reason"]) and result != '' and result != None and result != {}:
                        # 确保played_cards是列表
                        if not isinstance(result["played_cards"], list):
                            result["played_cards"] = [result["played_cards"]]
                        
                        # 确保选出的牌是有效的（从手牌中选择1-3张）
                        valid_cards = all(card in self.hand for card in result["played_cards"])
                        valid_count = 1 <= len(result["played_cards"]) <= 3
                        
                        if valid_cards and valid_count:
                            # 从手牌中移除已出的牌
                            for card in result["played_cards"]:
                                self.hand.remove(card)
                            return result, reasoning_content
                                
            except Exception as e:
                # 仅记录错误，不修改重试请求
                print(f"尝试 {attempt+1} 解析失败: {str(e)}")
                if attempt==3:
                    time.sleep(60*9)
                time.sleep(60)
        showwarning('注意','json自动修复失败，请在终端内手动修正！')
        return json.loads(input('大语言模型输出：' + content + '请手动修正' +': ')), ''
        #raise RuntimeError(f"玩家 {self.name} 的choose_cards_to_play方法在多次尝试后失败")

    def decide_challenge(self,
                        round_base_info: str,
                        round_action_info: str,
                        challenge_decision_info: str,
                        challenging_player_performance: str,
                        extra_hint: str):# -> bool:
        """
        玩家决定是否对上一位玩家的出牌进行质疑
        
        Args:

            round_base_info: 轮次基础信息
            round_action_info: 轮次操作信息
            challenge_decision_info: 质疑决策信息
            challenging_player_performance: 被质疑玩家的表现描述
            extra_hint: 额外提示信息
            
        Returns:
            tuple: (result, reasoning_content)
            - result: 包含was_challenged和challenge_reason的字典
            - reasoning_content: LLM的原始推理过程
        """
        # 读取规则和模板
        rules = self._read_file(RULE_BASE_PATH)
        template = self._read_file(CHALLENGE_PROMPT_TEMPLATE_PATH)
        self_hand = f"你现在的手牌是: {', '.join(self.hand)}"
        
        # 填充模板
        prompt = template.format(
            rules=rules,
            self_name=self.name,
            round_base_info=round_base_info,
            round_action_info=round_action_info,
            self_hand=self_hand,
            challenge_decision_info=challenge_decision_info,
            challenging_player_performance=challenging_player_performance,
            extra_hint=extra_hint
        )
        
        # 尝试获取有效的JSON响应，最多重试五次
        for attempt in range(4):
            # 每次都发送相同的原始prompt
            if attempt >= 1:
                messages = [
                    {"role": "user", "content": prompt+"上次回答json疑似存在格式问题。"}
                ]
            else:
                messages = [
                    {"role": "user", "content": prompt}
                ]
            
            try:
                content, reasoning_content, suc = self.llm_client.chat(messages, model=self.model_name)

                if not suc:
                    continue

                # 解析JSON响应
                json_match = re.search(r'({[\s\S]*})', content)
                with open('res1.txt','w+') as f:
                        f.write(content)
                if json_match:
                    json_str = json_match.group(1)
                    json_str = re.sub(r'\\', '', json_str)
                    json_str = json_str.replace('\n','')
                    if json_str.count('"was_challenged"') <= 0 and json_str.count('was_challenged') >= 1:
                        json_str = json_str.replace('was_challenged','"was_challenged"',1)
                    if json_str.count('"challenge_reason"') <= 0 and json_str.count('challenge_reason') >= 1:
                        json_str = json_str.replace('challenge_reason','"challenge_reason"',1)
                    try:
                        result = json.loads(json_str)
                    except:
                        result = json_repair.loads(json_str)

                    # 验证JSON格式是否符合要求
                    if all(key in result for key in ["was_challenged", "challenge_reason"]) and result != None and result != '' and result != {}:
                        # 确保was_challenged是布尔值
                        if isinstance(result["was_challenged"], bool):
                            return result, reasoning_content
                
            except Exception as e:
                # 仅记录错误，不修改重试请求
                print(f"尝试 {attempt+1} 解析失败: {str(e)}")
                time.sleep(60)
        showwarning('注意', 'json自动修复失败，请在终端内手动修正！')
        return json.loads(input('大语言模型输出：' + content + '请手动修正' +': ')), ''
        #raise RuntimeError(f"玩家 {self.name} 的decide_challenge方法在多次尝试后失败")

    def reflect(self, alive_players: List[str], round_base_info: str, round_action_info: str, round_result: str) -> None:
        """
        玩家在轮次结束后对其他存活玩家进行反思，更新对他们的印象
        
        Args:
            alive_players: 还存活的玩家名称列表
            round_base_info: 轮次基础信息
            round_action_info: 轮次操作信息
            round_result: 轮次结果
        """
        # 读取反思模板
        template = self._read_file(REFLECT_PROMPT_TEMPLATE_PATH)
        
        # 读取规则
        rules = self._read_file(RULE_BASE_PATH)
        
        # 对每个存活的玩家进行反思和印象更新（排除自己）
        for player_name in alive_players:
            # 跳过对自己的反思
            if player_name == self.name:
                continue
            
            # 获取此前对该玩家的印象
            previous_opinion = self.opinions.get(player_name, "还不了解这个玩家")
            
            # 填充模板
            prompt = template.format(
                rules=rules,
                self_name=self.name,
                round_base_info=round_base_info,
                round_action_info=round_action_info,
                round_result=round_result,
                player=player_name,
                previous_opinion=previous_opinion
            )
            
            # 向LLM请求分析
            messages = [
                {"role": "user", "content": prompt}
            ]
            for a in range(4):
                try:
                    content, _,suc = self.llm_client.chat(messages, model=self.model_name)
                    # 更新对该玩家的印象
                    if suc:
                        self.opinions[player_name] = content.strip()
                        print(f"{self.name} 更新了对 {player_name} 的印象")
                        continue
                    print('反思玩家时因报错跳过一次机会')
                except Exception as e:
                    a = a + 1
                    time.sleep(60)
                    print(f"反思玩家 {player_name} 时出错: {str(e)}")

    def process_penalty(self) -> bool:
        """处理惩罚"""
        print(f"玩家 {self.name} 执行射击惩罚：")
        self.print_status()
        if self.bullet_position == self.current_bullet_position:
            print(f"{self.name} 中枪死亡！")
            self.alive = False
        else:
            print(f"{self.name} 幸免于难！")
        self.current_bullet_position = (self.current_bullet_position + 1) % 6
        return self.alive