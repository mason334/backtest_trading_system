import pandas as pd
import traceback
import numpy as np
import random
import itertools


def build_deck_frame():
    df = pd.DataFrame()
    i = 0
    all_suits = [1,2,3,4]
    for suit in all_suits:
        for number in range(0, 13):
            df.loc[i, 'Card_ID'] = i
            df.loc[i, 'Suit'] = suit
            df.loc[i, 'Number'] = number+1
            i += 1
    return df


def deal_cards(cards):
    s = list(range(52))
    random.shuffle(s)
    _players = {}
    _player_decks = {}
    for j in range(1, 5):
        _players[f'player_{j}'] = s[-5:]
        del s[-5:]
        _player_decks[f'player_{j}'] = pd.DataFrame()
    print(_players, _player_decks)
    for keys, values in _players.items():
        print(keys)
        print(values)
        for card_id in values:
            _player_decks[f"{keys}"] = _player_decks[f"{keys}"].append(cards.loc[cards['Card_ID'] == card_id], ignore_index=True)
    return _players, _player_decks

# 计算分数
def score(_player_decks):
    _player_scores = {}
    for j in range(1, 5):
        _player_scores[f'player_{j}'] = {'score_bull': 0, 'score_point': 0, 'score_max': 0, 'score_suit': 0}

    _i = 0
    for _keys in _player_decks:
        print(f'this is the {_i}th combination')
        _i += 1
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
                _player_scores[_keys]['score_bull'] = 1
                for i in x:
                    score_deck.remove(i)
                _player_scores[_keys]['score_point'] = (sum(score_deck) % 10)
                break
        score_max = max(list(_player_decks[_keys]['Number']))
        _player_scores[_keys]['score_max'] = score_max
        suit_df = _player_decks[_keys].loc[_player_decks[_keys]['Number'] == score_max]
        _player_scores[_keys]['score_suit'] = max(list(suit_df['Suit']))

deck = build_deck_frame()

print(deck)

players, player_decks = deal_cards(deck)
print(players)
for keys, values in player_decks.items():
    print(keys, values)

score(player_decks)
