import re

import pandas as pd

import modules.lineup as lineup
import modules.names as names
import modules.parse as parse
import modules.play as play
import modules.scrape as scrape
import modules.sub as sub
import modules.ref as ref
import modules.ui as ui
import modules.player as player

# TODO: Add check for a player that isn't at bat or on base


class Game:
    """Object representing one game
    """

    def __init__(self, id):
        self.id = id

        # keep track of whether there is an error in parsing the game
        self.error = False

        # keep track of where in the game we are
        self.play = {'play_idx': 0, 'play_of_inn': 0,
                     'pbp_idx': 0, 'pbp_of_inn': 0}
        # self.play_list_id = scrape.get_game_id('https://stats.ncaa.org/game/box_score/' + id)
        # self.meta = get_info(id) #should be separate db table

        # keep track of inning/half/outs/runners/score info
        # Runners could be tracked using ids based on lineup order?
        self.state = {'inning': 1, 'half': 0, 'outs': 0,
                      'runners': ['', '', '', ''], 'score': [0, 0]}
        self.flags = {'ph': 0, 'pr': 0, }
        self.output = []
        self.subs = []
        # scrape the play by play based on id

    def setup_game(self):
        self.lineups = [lineup.Lineup(self.id, 0), lineup.Lineup(
            self.id, 1)]  # 2 lineup objects, 2 sub lists
        self.play_list = get_pbp(self.id)
        # create lineups based on game id
        for lu in self.lineups:
            names.match_all(lu, self.play_list)
        # create a dictionary of names to go between the lineup and play by play
        # TODO: what if we kept track of everyone using an id which just pointed to the lineup or whatever

        # check subs based on the box score with play by play
        # TODO: clean them up if there's an error
        self.check_subs()
        self.check_order()

        # remove pbp lines that aren't plays or subs
        self.clean_game()

        raw = {
            'plays': self.play_list,
            'lineups': {'away': {'lineup': [p.__dict__ for p in self.lineups[0].lineup], 'subs': [p.__dict__ for p in self.lineups[0].subs]},
                        'home': {'lineup': [p.__dict__ for p in self.lineups[1].lineup], 'subs': [p.__dict__ for p in self.lineups[1].subs]}},
            'subs': self.subs
        }

        return raw

    def reparse_game(self, d):
        self.play_list = d['plays']
        self.lineups = [lineup.Lineup('', 0), lineup.Lineup('', 1)]
        self.lineups[0].lineup = []
        for i in (range(len(d['lineups']['away']['lineup']))):
            p = player.Player('', '', '', '', '', '', '', '', '')
            p.__dict__.update(d['lineups']['away']['lineup'][i])
            self.lineups[0].lineup.append(p)

        self.lineups[0].subs = []
        for i in (range(len(d['lineups']['away']['subs']))):
            p = player.Player('', '', '', '', '', '', '', '', '')
            p.__dict__.update(d['lineups']['away']['subs'][i])
            self.lineups[0].subs.append(p)

        self.lineups[1].lineup = []
        for i in (range(len(d['lineups']['home']['lineup']))):
            p = player.Player('', '', '', '', '', '', '', '', '')
            p.__dict__.update(d['lineups']['home']['lineup'][i])
            self.lineups[1].lineup.append(p)

        self.lineups[1].subs = []
        for i in (range(len(d['lineups']['home']['subs']))):
            p = player.Player('', '', '', '', '', '', '', '', '')
            p.__dict__.update(d['lineups']['home']['subs'][i])
            self.lineups[1].subs.append(p)

        self.subs = {int(k): v for k, v in d['subs'].items()}

    def check_order(self):
        """looking at the play-by-play hitter order and the box score orders and finding discrepancies
        """
        for team in [0, 1]:
            names = {
                player.pbp_name: player.id for player in self.lineups[team].lineup}
            names.update(
                {player.pbp_name: player.id for player in self.lineups[team].subs})
            plays = [p for p in all_plays(
                self.play_list, team) if parse.get_type(p) == 'p']
            primaries = []
            for p in plays:
                for n in list(names.keys()):
                    if not n == '':
                        p = p.replace(n + ' ', '|' + names[n] + ' ')
                # TODO: there might be a better fix if this is a problem again - there was a problem with 'struck out, stole second'
                run = [cd for cd in ref.run_play_codes.keys() if cd in p.split('|')[1].replace(
                    ', out', '') and not 'struck out' in p and not 'walked' in p]
                if not (len(run) > 0 or 'advanced' in p.split(' ')[1]):
                    if not p.split(' ')[0].split('|')[1] in primaries[-3:]:
                        primaries.append(p.split(' ')[0].split('|')[1])
            pbp_order = {}
            for i in range(len(primaries)):
                p = primaries[i]
                if not p in pbp_order.keys():
                    pbp_order.update({p: i % 9 + 1})
            orders = {
                player.id: player.order for player in self.lineups[team].lineup}
            orders.update(
                {player.id: player.order for player in self.lineups[team].subs})
            mismatch = [p for p in pbp_order.keys() if pbp_order[p]
                        != orders[p]]
            for player_id in mismatch:
                for player in self.lineups[team].subs:
                    if player.id == player_id:
                        player.order = pbp_order[player_id]
                for player in self.lineups[team].lineup:
                    if player.id == player_id:
                        player.order = pbp_order[player_id]
            # Look at extra pbp subs and try to reset up the game so it matches better

    def check_subs(self):
        """Matches substitutions in play by play to box score and raises errors for mismatches
        """
        sub_regex = r"^([A-Za-z,\. '-]*?(?= [a-z])|\/) (pinch (?:hit|ran)|to [0-9a-z]{1,2})* *(?:for ([A-Za-z,\. '-]*?)\.$)*"
        sub_plays = [p for half in self.play_list for p in half if not re.search(
            sub_regex, p).group(2) is None or '/' in p]
        subs_from_box = {}

        for i in [0, 1]:
            lineup = self.lineups[i]
            for player in lineup.lineup:
                if len(player.switch) > 0:
                    for pos in player.switch:
                        s = {'name': player.name, 'id': player.id,
                             'pos': pos, 'team': i}
                        subs_from_box[len(subs_from_box)] = s

            for player in lineup.subs:
                if len(player.switch) > 0:
                    for pos in player.switch:
                        s = {'name': player.name, 'id': player.id,
                             'pos': pos, 'team': i}
                        subs_from_box[len(subs_from_box)] = s

            for player in lineup.subs:
                if not player.sub == '':
                    s = {'name': player.name, 'id': player.id, 'pos': player.pos,
                         'replaces': player.sub, 'replaces_id': player.sub_id, 'team': i}
                    subs_from_box[len(subs_from_box)] = s

        unmatched = 0
        while len(sub_plays) - unmatched > 0:
            p = sub_plays[unmatched]
            [sub_in, pos, sub_out] = sub.parse_sub(p)
            if len(subs_from_box) > 0:
                for i in range(0, len(subs_from_box)):
                    lineup = self.lineups[subs_from_box[i]['team']]
                    player_in = [p.name for p in lineup.lineup if p.pbp_name ==
                                sub_in] + [p.name for p in lineup.subs if p.pbp_name == sub_in]
                    if len(player_in) > 0 and subs_from_box[i]['name'] in player_in:
                        if 'replaces' in subs_from_box[i].keys():
                            player_out = [p.name for p in lineup.lineup if p.pbp_name == sub_out] + [
                                p.name for p in lineup.subs if p.pbp_name == sub_out]
                            if subs_from_box[i]['replaces'] in player_out:
                                subs_from_box[i]['text'] = p
                                sub_plays.remove(p)
                                break
                        else:
                            if 'pos' in subs_from_box[i].keys():
                                if subs_from_box[i]['pos'] == pos:
                                    subs_from_box[i]['text'] = p
                                    sub_plays.remove(p)
                                    break
                    if i == len(subs_from_box)-1:
                        unmatched += 1
            else:
                unmatched += 1

        if len(sub_plays) > 0:
            parsed = []
            for p in sub_plays:
                parsed.append(sub.parse_sub(p))
            for i in parsed:
                # If two players are substituted for each other then
                # the SID subbed them into the wrong place in the lineup
                # 99% sure on this
                # so if there's a match here we want to go back into the subs and switch who they entered the game for
                # and also check if theres a discrepancy in the order from the box score
                matches = [[pl[0], pl[2]]
                           for pl in parsed if pl[2] == i[0] and pl[0] == i[2]]
                if len(matches) > 0:
                    for team in [0, 1]:
                        names = {
                            player.pbp_name: player.id for player in self.lineups[team].lineup}
                        names.update(
                            {player.pbp_name: player.id for player in self.lineups[team].subs})
                        if matches[0][0] in names.keys() and matches[0][1] in names.keys():
                            ids = [names[matches[0][0]], names[matches[0][1]]]
                            switch = []
                            for s in range(len(subs_from_box)):
                                sb = subs_from_box[s]
                                if sb['id'] in ids and 'replaces' in sb:
                                    switch.append(s)
                            if len(switch) > 1:
                                sub1 = subs_from_box[switch[0]]
                                sub2 = subs_from_box[switch[1]]
                                rep1 = [sub1['replaces'], sub1['replaces_id']]
                                rep2 = [sub2['replaces'], sub2['replaces_id']]
                                subs_from_box[switch[0]]['replaces'] = rep2[0]
                                subs_from_box[switch[0]
                                              ]['replaces_id'] = rep2[1]
                                subs_from_box[switch[1]]['replaces'] = rep1[0]
                                subs_from_box[switch[1]
                                              ]['replaces_id'] = rep1[1]
                                for player in self.lineups[team].subs:
                                    if player.id == sub1['id']:
                                        player.sub = rep2[0]
                                        player.sub_id = rep2[1]
                                    if player.id == sub2['id']:
                                        player.sub = rep1[0]
                                        player.sub_id = rep1[1]
                    parsed.remove(i)

            for i in range(0, len(subs_from_box)):
                sb = subs_from_box[i]
                if not 'text' in sb.keys():
                    team = sb['team']
                    names = {
                        player.pbp_name: player.id for player in self.lineups[team].lineup}
                    names.update(
                        {player.pbp_name: player.id for player in self.lineups[team].subs})
                    
                    [n1, n2, n3, n4, n5] = ['']*5
                    [s1, s2, s3] = [0]*3
                    p2 = ''
                    for j in range(len(sub_plays)):
                        sp = sub_plays[j]
                        if '/ ' in sp:
                            n5 = names[sub.parse_sub(sp)[2]] # cacchione
                            s3 = j
                        if sub.parse_sub(sp)[0] in names:
                            if sb['id'] == names[sub.parse_sub(sp)[0]]:
                                n1 = sb['id'] #denson
                                if sub.parse_sub(sp)[2] in names:
                                    n3 = names[sub.parse_sub(sp)[2]] # cacchione
                                    s1 = j
                        if sub.parse_sub(sp)[2] in names:
                            if sb['replaces_id'] == names[sub.parse_sub(sp)[2]]:
                                n2 = sb['replaces_id'] #ferri
                                if sub.parse_sub(sp)[0] in names:
                                    n4 =  names[sub.parse_sub(sp)[0]] #cacchione
                                    p2 = sub.parse_sub(sp)[1]
                                    s2 = j

                    if not n3 == '' and n3 == n4 and n4 == n5:
                        subs_from_box[i]['replaces_id'] = n3
                        subs_from_box[i]['text'] = sub_plays[s1]
                        idx = len(subs_from_box)
                        subs_from_box[idx] = ({'id': n4, 'pos': p2, 'replaces_id': n2, 'team': team, 'text': sub_plays[s2]})
                        subs_from_box[idx+1] = ({'replaces_id': n5, 'team': team, 'text': sub_plays[s3]})
                        sub_plays.pop(s1)
                        sub_plays.pop(s2-1)
                        sub_plays.pop(s3-1)
                if not 'text' in subs_from_box[i].keys():
                    # self.error = True
                    print("ERROR: not all subs accounted for")
                    print(subs_from_box[i])
        
        # burns = [play for half in self.play_list for play in half if '/ ' in play]
        # for b in burns:

        self.subs = subs_from_box
        # TODO: handle subs for various types of errors

    def create_plays(self):
        """For each play in the pbp text, create either a play or sub object
        """
        g = []
        for half in range(0, len(self.play_list)):
            h = []
            for p in self.play_list[half]:
                if parse.get_type(p) == 'p':
                    team = 0 if half % 2 == 0 else 1
                    names = {
                        player.name: player.pbp_name for player in self.lineups[team].lineup}
                    names.update(
                        {player.name: player.pbp_name for player in self.lineups[team].subs})

                    ids = {
                        player.name: player.id for player in self.lineups[team].lineup}
                    ids.update(
                        {player.name: player.id for player in self.lineups[team].subs})

                    new_play = play.Play(p, names, ids)
                    new_play.get_type(self.lineups, team)
                    new_play.create_events()
                    h.append(new_play)
                elif parse.get_type(p) == 's':
                    new_sub = None
                    for i in range(0, len(self.subs)):
                        if 'text' in self.subs[i]:
                            if self.subs[i]['text'] == p:
                                sub_idx = self.subs[i]
                                if '/ ' in p:
                                    new_sub = sub.Removal(
                                        sub_idx['team'], sub_idx['replaces_id'], p)
                                elif not 'replaces_id' in sub_idx.keys():
                                    new_sub = sub.PositionSwitch(
                                        sub_idx['team'], sub_idx['id'], sub_idx['pos'], p)
                                elif half % 2 == sub_idx['team']:
                                    if ' ran ' in p:
                                        sub_type = 'pr'
                                    elif ' hit ' in p or ' to dh ' in p:
                                        sub_type = 'ph'
                                    else:
                                        sub_type = 'o'
                                    new_sub = sub.OffensiveSub(
                                        sub_idx['team'], sub_idx['id'], sub_idx['replaces_id'], sub_type, p)
                                else:
                                    new_sub = sub.DefensiveSub(
                                        sub_idx['team'], sub_idx['id'], sub_idx['replaces_id'], sub.parse_sub(p)[1], p)
                    if new_sub is None:
                        if '/ ' in p:
                            team = (half + 1) % 2
                            pbp_ids = {
                                player.pbp_name: player.id for player in self.lineups[team].lineup}
                            pbp_ids.update(
                                {player.pbp_name: player.id for player in self.lineups[team].subs})

                            new_sub = sub.Removal(
                                team, pbp_ids[sub.parse_sub(p)[2]], p)
                        else:
                            # just look for if the player coming out is in the game, and take him out and switch for player coming in,
                            # otherwise if the player coming in is in the game and switch his position,
                            # otherwise substitute the player into the game maybe(?)
                            [name, pos, sub_out] = sub.parse_sub(p)
                            for team in [0, 1]:
                                all_players = [player for player in self.lineups[team].lineup] + [
                                    player for player in self.lineups[team].subs]
                                # and (pos == player.pos or pos in player.switch)]
                                possible = [
                                    player.pbp_name for player in all_players if name == player.pbp_name]
                                if len(possible) == 1:
                                    pbp_ids = {
                                        player.pbp_name: player.id for player in self.lineups[team].lineup}
                                    pbp_ids.update(
                                        {player.pbp_name: player.id for player in self.lineups[team].subs})
                                    if not sub_out is None:
                                        out_possible = [player.pbp_name for player in all_players if sub_out == player.pbp_name and (
                                            pos == player.pos or pos in player.switch)]
                                        if len(possible) == 1 and len(out_possible) == 1:
                                            if (half % 2) == team:
                                                new_sub = sub.OffensiveSub(
                                                    team, pbp_ids[possible[0]], pbp_ids[out_possible[0]], pos, p)
                                            else:
                                                new_sub = sub.DefensiveSub(
                                                    team, pbp_ids[possible[0]], pbp_ids[out_possible[0]], pos, p)
                                    else:
                                        new_sub = sub.PositionSwitch(
                                            team, pbp_ids[possible[0]], pos, p)
                    if not new_sub is None:
                        h.append(new_sub)
                    else:
                        self.error = True
            g.append(h)
        self.events = g

    def execute_game(self):
        for h in self.events:
            for e in h:
                # print(e.text)
                if "sub" in str(type(e)):
                    self.lineups[e.team].make_sub(e)
                    if 'OffensiveSub' in str(type(e)):
                        if e.sub_type == 'pr':
                            for r in self.state['runners']:
                                if not r == '':
                                    if r.id == e.sub:
                                        r.id = e.player
                    # print(e.text)
                    # print(
                    #     'inning: ' + str(self.state['inning']) + ' - half: ' + str(self.state['half']))
                    # ui.print_lineups(self)
                    # ui.print_subs(self)
                else:
                    check = check_lineup(
                        self.lineups[(self.state['half'] + 1) % 2].lineup)
                    if not check:
                        self.error = True
                        print(e.text)
                        print(
                            'inning: ' + str(self.state['inning']) + ' - half: ' + str(self.state['half']))
                        ui.print_lineups(self)
                        ui.print_subs(self)
                    output = self.execute_play(e)
                    self.output.append(output)
                    self.play['play_of_inn'] += 1
                    self.play['play_idx'] += 1
                self.play['pbp_idx'] += 1
                self.play['pbp_of_inn'] += 1

            self.state['half'] += 1
            self.state['outs'] = 0
            if self.state['half'] > 1:
                self.state['half'] = 0
                self.state['inning'] += 1
            self.state['runners'] = ['']*4
            self.play['pbp_of_inn'] = 0
            self.play['play_of_inn'] = 0
        seq = False
        for row in self.output:
            if 'pitch_seq_tx' in row:
                if not row['pitch_seq_tx'] == '':
                    seq = True
                    break
        if seq:
            for row in self.output:
                if 'pitch_seq_tx' in row:
                    in_play = 'X' if row['event_cd'] in [2,19,20,21,22,23,18] else ''
                    row['pitch_seq_tx'] = row['pitch_seq_tx'] + in_play
        return self.output

    def execute_play(self, p):
        # print(p.__dict__)
        # print([e.__dict__ for e in p.events])
        new_runners = ['']*4
        p.defense = self.get_defense()
        # maybe check? batter = self.lineups.get_batter(self.state['half'], p.order)
        run_text = ['']*4

        for e in reversed(p.events):
            if type(e) == play.RunEvent:
                for i in range(1, 4):
                    if self.state['runners'][i] != '':  # TODO: replace names with ids
                        runner = self.state['runners'][i]
                        if runner.id == e.id:
                            p.dest[i] = e.dest[1] if e.dest[1] == 0 else e.dest[0]
                        run_text[i] = e.text
            else:
                r = play.Runner(e.id, p.defense[0])
                if e.code in [17, 18]:
                    r.resp = ''
                self.state['runners'][0] = r
                p.dest[0] = e.dest[1] if e.dest[1] == 0 else e.dest[0]

        # advance runners, calculate outs and runs
        for i in range(0, 4):
            if p.dest[i] != '':
                if p.dest[i] in [1, 2, 3]:
                    new_runners[p.dest[i]] = self.state['runners'][i]
                elif p.dest[i] == 4:
                    self.state['score'][self.state['half'] % 2] += 1
                elif p.dest[i] == 0:
                    p.event_outs += 1
            else:
                if self.state['runners'][i] != '':
                    new_runners[i] = self.state['runners'][i]

        # get output
        output = self.get_output(p)

        self.state['outs'] += p.event_outs
        self.state['runners'] = new_runners
        return output

        # self.output.append(self.get_output(p))
        # print('play no: ' + str(self.play))
        # # print(self.play_list[self.state['half']][self.play_of_inn])

        # if self.leadoff_fl == True:
        #     self.leadoff_fl = False
        # self.runners = new_runners
        # self.dest = ['']*4
        # self.outs += self.event_outs
        # self.event_outs = 0

        # self.sub = []

    def get_output(self, p):
        output = {
            'game_id': self.id,
            'inn_ct': self.state['inning'],
            'bat_home_id': self.state['half'],
            'outs_ct': self.state['outs'],
            'away_score_ct': self.state['score'][0],
            'home_score_ct': self.state['score'][1],
            'bat_id': self.lineups[self.state['half']].lineup[p.order-1].id,
            # 'bat_hand_cd': , # TODO: go through situational splits to get left/right
            'bat_lineup_id': p.order,
            # this should come from same player object as batter id
            'bat_fld_cd': ref.pos_codes[self.lineups[self.state['half']].lineup[p.order-1].pos],
            'bat_dest_id': p.dest[0],
            'run1_dest_id': p.dest[1],
            'run2_dest_id': p.dest[2],
            'run3_dest_id': p.dest[3],


            # TODO: putouts/assists
            # 'batter_play': loc if type(self.last_play.events[0]) == 'play.BatEvent' else '',
            'pit_id': p.defense[0],
            # 'bat_hand_cd': , # TODO: go through situational splits to get left/right
            'pos2_fld_id': p.defense[1],
            'pos3_fld_id': p.defense[2],
            'pos4_fld_id': p.defense[3],
            'pos5_fld_id': p.defense[4],
            'pos6_fld_id': p.defense[5],
            'pos7_fld_id': p.defense[6],
            'pos8_fld_id': p.defense[7],
            'pos9_fld_id': p.defense[8],
            'base1_run_id': self.state['runners'][1].id if self.state['runners'][1] != '' else '',
            'run1_resp_pit_id': self.state['runners'][1].resp if self.state['runners'][1] != '' else '',

            # 'run_1_play': '', #defense
            'base2_run_id': self.state['runners'][2].id if self.state['runners'][2] != '' else '',
            'run2_resp_pit_id': self.state['runners'][2].resp if self.state['runners'][2] != '' else '',
            # 'run_2_play': '',
            'base3_run_id': self.state['runners'][3].id if self.state['runners'][3] != '' else '',
            'run3_resp_pit_id': self.state['runners'][3].resp if self.state['runners'][3] != '' else '',
            # 'run_3_play': '',
            # 'full_event': p.event, #
            'leadoff_fl': 1 if self.play['play_of_inn'] == 0 else 0,
            'event_cd': p.events[0].code,
            'bat_event_fl': 1 if p.type == 'b' else 0,
            'event_outs_ct': p.event_outs,
            # 'fielder': '', # don't need unless there's an out??
            # 'batted_ball': '', #
            # 'errors': {}, #Need to add dropped foul (13)
            # # 'ph_fl': , Not necessary b/c position will be 10?
            # 'SB_FL': 1 if p.events[0].code == 4 else 0, all redundant right?
            # 'CS_FL': 1 if p.events[0].code == 6 else 0,
            # 'PK_FL': 1 if p.events[0].code == 8 else 0,
            # 'wp_fl': 1 if p.events[0].code ==
            # 'DP_FL': 1 if p.event_outs == 2 else 0, redundant?
            # 'TP_FL': 1 if p.event_outs == 3 else 0,
            # 'sub_fl': self.sub, # new, position, removed,
            # 'po': {}, #,
            # 'assist': {},
            # 'event_tx': self.get_event_tx(p),
            'event_id': self.play['play_idx'],
            'pbp_tx': p.text,
        }
        if p.type == 'b':
            output.update(
                {
                    'balls_ct': p.events[0].count[0],
                    'strikes_ct': p.events[0].count[1],
                    # TODO: add x if in play
                    'pitch_seq_tx': p.events[0].seq if not p.events[0].seq is None else '',
                    'rbi_ct': p.events[0].rbi,
                    'h_fl': 1 if p.events[0].code in [20, 21, 22, 23] else 0,
                    'ab_fl': 1 if p.events[0].code in [2, 3, 18, 19, 20, 21, 22, 23] and not 'SF' in p.events[0].flags or 'SAC' in p.events[0].flags else 0,
                    'sh_fl': 1 if 'SAC' in p.events[0].flags else 0,
                    'sf_fl': 1 if 'SF' in p.events[0].flags else 0,
                    'bunt_fl': 1 if 'B' in p.events[0].flags else 0,
                }
            )
        return output

    def get_defense(self):
        return self.lineups[(self.state['half'] + 1) % 2].get_defense()

    def clean_game(self):

        for i in range(0, len(self.play_list)):
            delete = []
            half = self.play_list[i]
            for j in range(0, len(half)):
                p = half[j]
                a = [player.pbp_name for player in self.lineups[0].lineup if player.pbp_name + ' ' in p] + \
                    [player.pbp_name for player in self.lineups[0].subs if player.pbp_name + ' ' in p]
                h = [player.pbp_name for player in self.lineups[1].lineup if player.pbp_name + ' ' in p] + \
                    [player.pbp_name for player in self.lineups[1].subs if player.pbp_name + ' ' in p]
                if len(h) == 0 and len(a) == 0 and not '/ ' in p:
                    delete.append(j)
                if 'failed pickoff attempt.' in p:
                    delete.append(j)
            deleted = 0
            for k in delete:
                self.play_list[i].pop(k-deleted)
                deleted += 1

    # def output(self):
    #     pass


def get_pbp(game_id) -> list:
    """ extracts pbp text from table

    :param game_id: unique game id
    :type game_id: int
    :return: Play by play text as a list of lists, with each sublist containing play by play for a half inning
    :rtype: list
    """
    table = scrape.get_table(
        'https://stats.ncaa.org/game/play_by_play/' + str(game_id))
    skip = True
    score = False
    plays = []
    game = []
    none = 0
    i = 0
    half = 1
    for element in table:
        for e in element:
            if e.text == "Score":
                score = True
            elif score:
                skip = False
                score = False
                i = -1
            elif not skip:
                i += 1
                if e.text is None:
                    none += 1
                elif e.text[0:3] == " R:":
                    skip = True
                    none = 0
                    half += 1
                    game.append(clean_plays(plays))
                    plays = []
                elif half % 2 != 0:
                    if i % 3 == 0:
                        plays.append(e.text)
                        none = 0
                    if none > 2:
                        half += 1
                        none = 0
                        game.append(clean_plays(plays))
                        plays = []
                if half % 2 == 0 and not e.text is None:
                    if (i-2) % 3 == 0:
                        plays.append(e.text)
                        none = 0
    return game


def clean_plays(plays) -> list:
    new_plays = []
    for p in plays:
        if 'challenged' in p or 'review' in p:
            p = 'No play.'
        if not 'No play.' in p:
            if p[0:3] == 'for':
                p = '/ ' + p
            if 'fielder\'s choice' in p or 'fielders choice' in p:
                fc = re.search(
                    r"(out at first [a-z0-9]{1,2} to [a-z0-9]{1,2}, )reached on a fielder's choice", p)
                if not fc is None:
                    p = p.replace(fc.group(1), '')
                p = p.replace(', picked off', '')                
            p = p.replace('did not advance', 'no advance')
            p = p.replace('3a', ':').replace(';', ':').replace(
                ': ', ':').replace('a muffed throw', 'an error')
        if not(parse.get_type(p) == 'p' and len(play.find_events(p)) == 0) and not parse.get_type(p) == 'n':
            new_plays.append(p)
    return new_plays


def check_lineup(lineup):
    # Rules:
    # must have all defensive positions
    # must have numbers 1-9 in order (10 is pitcher)
    # if dh position, then must have 10 if not then must only have 9
    # no removed players allowed
    pos_list = ['p', 'c', '1b', '2b', '3b', 'ss', 'lf', 'cf', 'rf', 'dh']
    order_list = list(range(1, 11))
    pinch = 0
    for player in lineup:
        if player.pos in pos_list:
            pos_list.remove(player.pos)
        elif player.pos in ['pr', 'ph']:
            pinch += 1
        else:
            print("ERROR: multiple players listed at " + player.pos)
            return False
        if player.order in order_list:
            order_list.remove(player.order)
        else:
            print("ERROR: multiple players listed at " + str(player.order))
            return False
    if 10 in order_list and not 'dh' in pos_list:
        print("ERROR: missing position " + str(pos_list))
        return False
    if len(order_list) == 0 and not len(pos_list) - pinch == 0:
        print("ERROR: missing position " + str(pos_list))
        return False
    if len(pos_list) == 0 and not len(order_list) == 0:
        print("ERROR: missing order " + str(order_list))
        return False
    if len(order_list) > 0 and not order_list == [10]:
        print("ERROR: missing order " + str(order_list))
        return False
    if len(pos_list) > 0 and not pos_list == ['dh']:
        print("ERROR: missing position " + str(pos_list))
        return False
    return True


def all_plays(play_list, team):
    # Maybe create a new module of helper functions
    """helper function to list all plays for one side

    :param play_list: list of play by play strings
    :type play_list: list
    :param team: 'h' for home or 'a' for away or other for all plays in the game
    :type team: str
    :return: list of play strings
    :rtype: list
    """
    out = []
    for i in range(0, len(play_list)):
        x = play_list[i]
        for p in x:
            if (team == 0) ^ (i % 2 == 1) or not team in [0, 1]:
                out.append(p)
    return out
