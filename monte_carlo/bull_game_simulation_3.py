import pandas as pd
import traceback
import numpy as np
import random
import itertools
from tqdm import tqdm


class Context:
    def __init__(self):
        self.player1 = {}
        self.player2 = {}
        self.player3 = {}
        self.player4 = {}

        self.players_list = [self.player1, self.player2, self.player3, self.player4]

        self.cash_record = pd.DataFrame()

        self.rounds_to_play = 1
        self.stake = 0

    def initialize(self, **kwargs):
        i = 1
        for player in self.players_list:
            player['cash'] = kwargs['start_cash']
            player['name'] = f'player{i}'
            player['cards_deck'] = pd.DataFrame()
            player['cards_number'] = []
            player['score'] = pd.DataFrame()

            i += 1
        self.rounds_to_play = kwargs['rounds_to_play']
        self.stake = kwargs['stake']

    @staticmethod
    def init_card_deck_df():
        df = pd.DataFrame()
        i = 0
        all_suits = [1, 2, 3, 4]
        for suit in all_suits:
            for number in range(0, 13):
                df.loc[i, 'Card_ID'] = i
                df.loc[i, 'Suit'] = suit
                df.loc[i, 'Number'] = number+1
                i += 1
        return df

    def deal_cards(self, cards):
        # cards 是一个dataframe，包括了一叠按顺序排好的牌
        s = list(range(52))
        random.shuffle(s)  # 将牌号打乱
        _players = {}
        _player_decks = {}

        # 将牌发到player手中，每人5张
        for player in self.players_list:
            player['cards_deck'] = pd.DataFrame()
            player['cards_number'] = s[-5:]
            del s[-5:]
            for card_id in player['cards_number']:
                player['cards_deck'] = player['cards_deck'].append(cards.loc[cards['Card_ID'] == card_id], ignore_index=True)

        return _player_decks

    # 计算分数
    def score(self, **_player_decks):

        # _player_scores = {}
        # for j in range(1, 5):
        #     _player_scores[f'player_{j}'] = {'score_bull': 0, 'score_point': 0, 'card_max': 0, 'score_suit':0}
        player_score_df = pd.DataFrame(
            columns=['player', 'score_bull', 'score_point', 'card_max', 'score_suit', 'total_score'])
        _i = 0
        # for _keys in _player_decks:
        #     score_deck = list(_player_decks[_keys]['Number'])

        # 从player中取所有出牌的点数，计算分数
        for player in self.players_list:
            score_deck = list(player['cards_deck']['Number'])

            # 将J，Q，K替换为 10，参与牛的计算
            for card in range(len(score_deck)):
                if score_deck[card] > 10:
                    score_deck[card] = 10

            # 列出所有可能的3个的组合，转换为list，计算是否能够凑成10
            combos = list(itertools.combinations(score_deck, 3))
            # itertools.combinations returns an iterator.
            # An iterator is something that you can apply for on.
            # Usually, elements of an iterator is computed as soon as you fetch it, so there is no penalty of copying all the content to memory, unlike a list.
            for x in combos:
                if sum(x) % 10 == 0:

                    # _player_scores[_keys]['score_bull'] = 1
                    player_score_df.loc[_i, 'score_bull'] = 1 #计算是否有牛
                    for k in x: #在有牛的情况下，计算牛的点数
                        score_deck.remove(k)
                    # _player_scores[_keys]['score_point'] = (sum(score_deck) % 10)
                    player_score_df.loc[_i, 'score_point'] = (sum(score_deck) % 10)
                    if (sum(score_deck) % 10) == 0: # 处理满牛的情况，将结果整除10余数是0的情况，将分数改为10
                        player_score_df.loc[_i, 'score_point'] = 10
                    break
                else:
                    player_score_df.loc[_i, 'score_bull'] = 0
                    player_score_df.loc[_i, 'score_point'] = 0

            # card_max = max(list(_player_decks[_keys]['Number']))
            card_max = max(list(player['cards_deck']['Number']))
            # _player_scores[_keys]['score_max'] = card_max
            player_score_df.loc[_i, 'card_max'] = card_max
            suit_df = player['cards_deck'].loc[player['cards_deck']['Number'] == card_max] #找到最大点数牌的花色
            # _player_scores[_keys]['score_suit'] = max(list(suit_df['Suit']))
            # player_score_df.loc[_i, 'score_suit'] = max(list(suit_df['Suit']))
            player_score_df.loc[_i, 'score_suit'] = max(list(suit_df['Suit']))
            player_score_df.loc[_i, 'player'] = player['name']
            _i += 1

        player_score_df.sort_values(by=['score_bull', 'score_point', 'card_max', 'score_suit'], ascending=False, inplace=True)
        player_score_df.reset_index(inplace=True, drop=True)
        player_score_df.reset_index(inplace=True)
        player_score_df.rename(columns={'index': 'ranking'}, inplace=True)

        # 将player的ranking按名字输出到 player obj中
        for player in self.players_list:
            player['score'] = player_score_df.loc[player_score_df['player'] == player['name']]


def play(initial_settings, _output_path):
    context = Context()
    context.initialize(**initial_settings)
    for rounds in tqdm(range(1, context.rounds_to_play)):
        cards = context.init_card_deck_df()
        hand_cards = context.deal_cards(cards)
        context.score(**hand_cards)
        for counter_player in [context.player2, context.player3, context.player4]:
            player1_ranking = context.player1['score']['ranking'].values[0]
            player1_score_points = context.player1['score']['score_point'].values[0]
            counter_player_ranking = counter_player['score']['ranking'].values[0]
            counter_player_score_points = counter_player['score']['score_point'].values[0]
            if player1_ranking < counter_player_ranking:
                if (player1_score_points >= 7) and (player1_score_points < 10):
                    context.player1['cash'] += context.stake * 2
                    counter_player['cash'] -= context.stake * 2
                elif player1_score_points == 10:
                    context.player1['cash'] += context.stake * 3
                    counter_player['cash'] -= context.stake * 3
                else:
                    context.player1['cash'] += context.stake
                    counter_player['cash'] -= context.stake
            else:
                if (counter_player_score_points >= 7) and (counter_player_score_points < 10):
                    context.player1['cash'] -= context.stake * 2
                    counter_player['cash'] += context.stake * 2
                elif counter_player_score_points == 10:
                    context.player1['cash'] -= context.stake * 3
                    counter_player['cash'] += context.stake * 3
                else:
                    context.player1['cash'] -= context.stake
                    counter_player['cash'] += context.stake

        for player in context.players_list:
            context.cash_record.loc[player['name'], f'{rounds}'] = player['cash']
            name = player['name']
            # print(f'this is {name} ')
            # print(player['cards_deck'])
    context.cash_record.to_csv(f'{_output_path}\\cash_record_{context.rounds_to_play}.csv')


init_settings = {
    'rounds_to_play': 10002,
    'stake': 10,
    'start_cash': 1000
}

output_path = 'E:\\Strategy_output\\bull_card_simulation\\2022-2-11'
play(init_settings, output_path)

