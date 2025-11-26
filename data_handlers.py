import requests
import json
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

class CardDataHandler:
    def __init__(self):
        pass
    def get_commander_data(self, commander, time_period, min_event_size,max_standing):
        """获取特定指挥官的数据"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        data = {
            "query": None,
            "variables": {
                "commander": commander,
                "showStaples": False,
                "showEntries": True,
                "showCardDetail": False,
                "sortBy": "TOP",
                "timePeriod": time_period,
                "minEventSize": min_event_size
            },
            "extensions": {
                "pastoria-id": "ad8859e838edd29f99ce513dae32fc1a"
            }
        }

        try:
            response = requests.post(
                "https://edhtop16.com/api/graphql",
                headers=headers,
                data=json.dumps(data),
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            response_data = response.json()



            edges = response_data['data']['commander']['entries']['edges']
            filtered_decks = [
                edge['node']
                for edge in edges
                if edge['node']['standing'] <= max_standing
            ]

            return filtered_decks

        except Exception as e:
            print(f"获取 {commander} 数据时出错: {e}")
            return []

    def count_card_in_decks(self, deck_data_list, card_name):
        """统计卡牌在套牌列表中的出现次数（多线程优化版）"""
        total_decks = len(deck_data_list)
        used_decks = 0

        # 使用线程池并发处理套牌检查
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有检查任务
            future_to_deck = {
                executor.submit(self.check_card_in_deck, deck_data.get('decklist', ''), card_name): deck_data
                for deck_data in deck_data_list
                if deck_data.get('decklist', '')
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_deck):
                try:
                    if future.result():
                        used_decks += 1
                except Exception as e:
                    print(f"检查套牌时出错: {e}")

        return used_decks, total_decks

    def check_card_in_deck(self, url, card_name):
        """检查单个套牌中是否包含特定卡牌"""
        if not url:
            return False

        try:
            # 处理moxfield链接
            if "moxfield.com" in url:
                api_url = url.replace(
                    "https://www.moxfield.com/decks/",
                    "https://api2.moxfield.com/v3/decks/all/"
                )
                deck_response = requests.get(api_url, timeout=10)
                deck_response.raise_for_status()

                deck_data = deck_response.json()

                # 检查主牌区
                for card_info in deck_data.get('boards', {}).get('mainboard', {}).get('cards', {}).values():
                    if card_info['card']['name'].lower() == card_name.lower():
                        return True

                # 检查指挥官区
                for card_info in deck_data.get('boards', {}).get('commanders', {}).get('cards', {}).values():
                    if card_info['card']['name'].lower() == card_name.lower():
                        return True

            else:
                # 处理其他网站
                deck_response = requests.get(url, timeout=10)
                deck_response.raise_for_status()
                # 只提取copyDecklist函数内的文本内容
                full_content = deck_response.text

                # 查找copyDecklist函数中的内容
                start_marker = "const decklistContent = `"
                end_marker = "`;"

                start_index = full_content.find(start_marker)
                if start_index != -1:
                    start_index += len(start_marker)
                    end_index = full_content.find(end_marker, start_index)
                    if end_index != -1:
                        content = full_content[start_index:end_index]
                    else:
                        content = ""
                else:
                    content = ""

                # 解析卡牌列表 (假定格式为 "数量 卡牌名")
                for line in content.split('\n'):
                    parts = line.strip().split(' ', 1)
                    if len(parts) == 2 and parts[0].isdigit():
                        card_name_in_deck = parts[1]
                        if card_name_in_deck.lower() == card_name.lower():
                            return True

            return False
        except Exception as e:
            print(f"处理套牌 {url} 时出错: {e}")
            return False