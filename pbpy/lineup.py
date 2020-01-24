import scrape
import pandas as pd


class Lineups:
    def __init__(self, game_id):
        [self.a_lineup, self.a_sub, self.h_lineup,
            self.h_sub] = get_lineups(game_id)

    def make_sub(self, s, g):
        if s.team == 'a':
            lu = self.a_lineup
        elif s.team == 'h':
            lu = self.h_lineup
        if '/' in s.sub_in:
            if len(lu[lu['pos']=='P']) > 1:
                lu = lu[0:9]
        if s.pos == 'pr':
            for r in g.runners:
                if r != '':
                    if r.name == s.sub_out:
                        r.name = s.sub_in
        if s.pos == 'ph':
            order = g.a_order if s.team == 'a' else g.h_order
            lu.iloc[order]['name'] = s.sub_in
            lu.iloc[order]['pos'] = 'PH'
        elif s.sub_out is None:
            lu.loc[lu['pos'] == s.pos.upper(), 'pos'] = ''
            lu.loc[lu['name'] == s.sub_in, 'pos'] = s.pos.upper()
        else:
            lu.loc[lu['name'] == s.sub_out, 'name'] = s.sub_in
            lu.loc[lu['name'] == s.sub_in, 'pos'] = s.pos.upper()
        if s.team == 'a':
            self.a_lineup = lu
        elif s.team == 'h':
            self.h_lineup = lu


    def get_batter(self, game):
        if game.half % 2 == 0:
            return game.lineups.a_lineup.iloc[game.a_order]['name']
        else:
            return game.lineups.h_lineup.iloc[game.h_order]['name']

    def all_names(self, team):
        if team == 'h':
            return self.h_lineup['name'].to_list() + self.h_sub
        elif team == 'a':
            return self.a_lineup['name'].to_list() + self.a_sub

    def get_defense(self, team):
        pos_list = ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']
        d = []
        if team == 'h':
            l = self.h_lineup
        elif team == 'a':
            l = self.a_lineup
        for p in pos_list:
            if len(l[l['pos'] == p]) > 0:
                d.append(l[l['pos'] == p]['name'].item())
            else:
                d.append('')
        return d


def get_lineups(game_id):
    player = False
    pos = False
    lineup = []
    away = []
    home = []
    away_pos = []
    home_pos = []
    pos_list = []
    team = 0
    pos_team = 0
    i = 0
    j = 0
    skip = True
    table = scrape.get_table(
        'https://stats.ncaa.org/game/box_score/' + str(game_id))
    for element in table:
        j = 0
        for row in element:
            i = 0
            for cell in row:
                i += 1
                if i == 1 and not cell.text is None:
                    if cell.text == "Fielding":
                        skip = False
                    elif not skip:
                        if not '\n' in cell.text:
                            lineup.append(cell.text)
            j += 1
            if j == 2:
                if row.text == "Pos":
                    pos = True
                elif pos and row.text == None:
                    pos = False
                    if pos_team == 0:
                        away_pos = pos_list
                        away = lineup
                        pos_team = 1
                    else:
                        home_pos = pos_list
                        home = lineup
                    pos_list = []
                    lineup = []
                elif pos:
                    pos_list.append(row.text.split('/')[0])
    return compile_lineups(away, away_pos, home, home_pos)


def get_index(list, type):
    if type == "l":
        return [i for i, s in enumerate(list) if not '\xa0' in s]
    elif type == "s":
        return [i for i, s in enumerate(list) if '\xa0' in s]


def list_index(list, index):
    return [list[i] for i in index]


def compile_lineups(away, away_pos, home, home_pos):
    a_lu = list_index(away, get_index(away, 'l'))
    a_lu_pos = list_index(away_pos, get_index(away, 'l'))
    a_sub = [s.replace('\xa0', '')
             for s in list_index(away, get_index(away, 's'))]
    h_lu = list_index(home, get_index(home, 'l'))
    h_lu_pos = list_index(home_pos, get_index(home, 'l'))
    h_sub = [s.replace('\xa0', '')
             for s in list_index(home, get_index(home, 's'))]
    a_lineup = pd.DataFrame({'name': a_lu, 'pos': a_lu_pos})
    h_lineup = pd.DataFrame({'name': h_lu, 'pos': h_lu_pos})
    return [a_lineup, a_sub, h_lineup, h_sub]
