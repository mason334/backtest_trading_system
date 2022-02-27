import pandas as pd
import traceback
import numpy as np
import random
import itertools

class Context:
    def __init__(self):
        self.player1_cash = 0
        self.player2_cash = 0
        self.player3_cash = 0
        self.player4_cash = 0
        self.rounds_to_play = 1

    def initialize(self, **kwargs):
        self.player1_cash = kwargs['player1_cash']
        self.player2_cash = kwargs['player2_cash']
        self.player3_cash = kwargs['player3_cash']
        self.player4_cash = kwargs['player4_cash']
        self.rounds_to_play = kwargs['rounds_to_play']

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

    @staticmethod
    def deal_cards(cards):
        s = list(range(52))
        random.shuffle(s)
        _players = {}
        _player_decks = {}
        for j in range(1, 5):
            _players[f'player_{j}'] = s[-5:]
            del s[-5:]
            _player_decks[f'player_{j}'] = pd.DataFrame()
        for keys, values in _players.items():
            for card_id in values:
                _player_decks[f"{keys}"] = _player_decks[f"{keys}"].append(cards.loc[cards['Card_ID'] == card_id], ignore_index=True)
        return _players, _player_decks


    # 计算分数
    @staticmethod
    def score(**_player_decks):
        print(_player_decks)
        player_score_df = pd.DataFrame(columns=['player', 'score_bull', 'score_point', 'card_max', 'score_suit', 'total_score'])
        # _player_scores = {}
        # for j in range(1, 5):
        #     _player_scores[f'player_{j}'] = {'score_bull': 0, 'score_point': 0, 'card_max': 0, 'score_suit':0}

        _i = 0
        for _keys in _player_decks:
            score_deck = list(_player_decks[_keys]['Number'])

            # 将J，Q，K替换为 10，参与牛的计算
            for card in range(len(score_deck)):
                if score_deck[card] > 10:
                    score_deck[card] = 10

            # 列出所有挑选出3个的组合，转换为list
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

            card_max = max(list(_player_decks[_keys]['Number']))
            # _player_scores[_keys]['score_max'] = card_max
            player_score_df.loc[_i, 'card_max'] = card_max
            suit_df = _player_decks[_keys].loc[_player_decks[_keys]['Number'] == card_max]
            # _player_scores[_keys]['score_suit'] = max(list(suit_df['Suit']))
            player_score_df.loc[_i, 'score_suit'] = max(list(suit_df['Suit']))
            player_score_df.loc[_i, 'player'] = _keys
            _i += 1
        player_score_df.sort_values(by=['score_bull', 'score_point', 'card_max', 'score_suit'], ascending=False, inplace=True)
        player_score_df.reset_index(inplace=True, drop=True)
        player_score_df.reset_index(inplace=True)
        player_score_df.rename(columns={'index': 'ranking'}, inplace=True)

        return player_score_df


    def clearing(self, player_score_df):


deck = init_card_deck_df()

players, player_decks = deal_cards(deck)

print(score(player_decks))


