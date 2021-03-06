import re

import pandas as pd

import string

import modules.names as names
import modules.ref as ref


class Play:
    def __init__(self, text, names, ids):
        self.text = text
        self.type = ''
        self.play_names = play_names(text, names)

        #pbp names to full names
        self.names = {names[k]:k for k in names.keys() if names[k] in self.play_names.keys()}

        #pbp names to id
        self.ids = {names[k]:ids[k] for k in names.keys() if names[k] in self.play_names.keys()}

        self.parts = self.split_play()
        self.order = 0
        
        self.dest = ['']*4

        self.event_outs = 0
        self.defense = ['']*9
    
    def split_play(self):
        new_text = self.text
        parts = []
        splits = list(self.play_names.keys())
        for i in range(0, len(splits)):
            name = splits[i]
            split = new_text.split(splits[i] + " ")
            new_text = split[0]
            player_text = split[1]
            if not 'no advance' in player_text:
                parts.insert(0, {'player':name, 'text': player_text})
        return parts
    
    def get_type(self, lineups, team):
        lu = lineups[team].lineup
        sub = lineups[team].subs
        self.order = lineups[team].order
        order_names = [player.pbp_name for player in lu if player.order == self.order]
        order_names.extend([player.pbp_name for player in sub if player.order == self.order])
        if self.parts[0]['player'] in order_names:
            self.type = 'b'
            lineups[team].order = self.order % 9 + 1
        else:
            self.type = 'r'

    def create_events(self):
        self.events = []
        if self.type == 'b':
            self.events.append(BatEvent(self.parts[0], self.ids[self.parts[0]['player']]))
            if len(self.parts) > 1:
                for part in self.parts[1:]:
                    self.events.append(RunEvent(part, self.ids[part['player']]))
        else:
            for part in self.parts:
                self.events.append(RunEvent(part, self.ids[part['player']]))
            if get_simple_run_event(self.events[0].text) is None:
                for e in range(1,len(self.events)):
                    sre = get_simple_run_event(self.events[e].text)
                    if not sre is None:
                        self.events[0].text = self.events[0].text + sre
                        break
            self.events[0].deconstruct_text()
            

class BatEvent:
    def __init__(self, part, id):
        self.player = part['player']
        self.text = part['text']
        self.id = id

        self.rbi = None
        self.flags = None
        self.bb_loc = None
        self.count = None
        self.seq = None

        self.event = None
        self.code = None

        self.deconstruct_text()

        # [self.event, self.code] = get_event(self.text, 'b')
        # [self.det_event, self.det_abb] = get_det_event(self.text, 'b')
        # self.ev_code = ref.event_codes[self.code]
        # self.player = get_primary(self.text, self.event)
        # self.fielders = get_fielders(text, self.event)
        # self.loc = self.get_loc()
        # self.dest = self.get_bat_dest()
        # self.correct_fielders()

    def deconstruct_text(self):
        pbp = self.text
        # print(pbp)
        self.get_info()
        pbp = pbp.split('(')[0]
        if ', RBI' in pbp:
            self.rbi = 1
            pbp = pbp.split(', RBI')[0]
        elif ' RBI' in pbp:
            self.rbi = int(pbp.split(' RBI')[0][-1])
            pbp = pbp.split(', ' + str(self.rbi) + ' RBI')[0]
        else:
            self.rbi = 0
            
        self.flags = get_flags(pbp)
        if len(self.flags) > 0:
            pbp = pbp.split(', ' + self.flags[0])[0]

        run = get_run(pbp)
        if len(run) > 1:
            if len(get_run(pbp.split(run[1])[0])) > 0:
                pbp = pbp.split(run[1])[0]
                self.dest = ref.run_codes[run[-1]]
            else:
                self.dest = ref.run_codes[run[0]]
        else:
            self.dest = ref.run_codes[run[0]]

        loc = get_loc(pbp)
        if len(loc) > 0:
            self.bb_loc = ref.loc_codes[loc[0]]
            if self.count == [0,0]:
                self.seq = 'X'
            elif not self.seq is None:
                self.seq.join('X') 
        #TODO: Add assists and putouts
        #TODO: Add bb type

        self.event = get_event(pbp)
        self.code = ref.event_codes[ref.codes[get_simple_event(pbp)]]

        # print(self.__dict__)
                

    def get_info(self):
        if '(' in self.text:
            #TODO: If count in any of the events, fill in rest with 0-0, otherwise n/a
            count = re.search(r'[0-3]-[0-2]', self.text).group(0)
            self.count = count.split('-')
            self.seq = re.search(r'[KFBS]*(?=\))', self.text).group(0)
        else:
            self.count = ['','']
            self.seq = ''



    # def correct_fielders(self):
    #     if self.event == 'grounded out':
    #         if len(self.fielders) == 1:
    #             self.fielders.append(3)



def get_run(text):
    run = [key for key in ref.run_codes.keys() if key in text]
    sorted_run = [k for k, v in sorted({r:text.index(r) for r in run}.items(), key=lambda item:item[1])]
    return sorted_run

def get_loc(text):
    loc = [key for key in ref.loc_codes.keys() if key in text]
    sorted_loc = [k for k, v in sorted({l:text.index(l) for l in loc}.items(), key=lambda item:item[1])]
    return sorted_loc

def get_flags(text):
    flag = [key for key in ref.flag_codes.keys() if key in text]
    sorted_flags = [ref.flag_codes[k] for k, v in sorted({l:text.index(l) for l in flag}.items(), key=lambda item:item[1])]
    return sorted_flags

def get_event(text):
    ev = [key for key in ref.mod_codes.keys() if key in text]
    sorted_ev = [k for k, v in sorted({l:text.index(l) for l in ev}.items(), key=lambda item:item[1])]
    return sorted_ev

def get_simple_event(text):
    ev = [key for key in ref.codes.keys() if key in text]
    sorted_ev = [k for k, v in sorted({l:text.index(l) for l in ev}.items(), key=lambda item:item[1])]
    if len(sorted_ev) == 0:
        print("NO EVENT FOUND")
        print(text)
    return sorted_ev[0]

def get_simple_run_event(text):
    ev = [key for key in ref.run_play_codes.keys() if key in text]
    sorted_ev = [k for k, v in sorted({l:text.index(l) for l in ev}.items(), key=lambda item:item[1])]
    if len(sorted_ev) == 0 or 'out at' in sorted_ev[0]:
        if 'advanced' in text.split(' ')[0] or 'scored' in text.split(' ')[0]:
            if 'error' in text:
                # TODO: are there any situations where this wouldn't be a failed pickoff?
                return 'failed pickoff attempt'
            else:
                return 'stole'
        if 'out' in text.split(' ')[0]:
            if 'at second c to ' in text:
                return 'caught stealing'
            elif 'at third c to 3b' in text:
                return 'caught stealing'
            else:
             return 'picked off'
            # TODO: would this happen for a caught stealing?
    return sorted_ev[0] if len(sorted_ev) > 0 else None



class RunEvent:
    def __init__(self, part, id):
        self.player = part['player']
        self.text = part['text']
        self.event = get_event(self.text)
        self.dest = get_run_dest(self.text)
        self.id = id

        self.event = None
        self.code = None

        # [self.event, self.code] = get_event(self.text, 'r')
        # [self.det_event, self.det_abb] = get_det_event(self.text, 'r')
        # self.ev_code = ref.event_codes[self.det_abb] if not self.det_abb == '' else ''
        # if not self.det_event == '' and self.text.index(self.det_event) < self.text.index(self.event):
        #     self.player = get_primary(self.text, self.det_event)
        # else:
        #     self.player = get_primary(self.text, self.event)
        # self.dest = self.get_run_dest()

    def deconstruct_text(self):
        pbp = self.text
        self.event = get_event(pbp)
        self.code = ref.event_codes[ref.codes[get_simple_run_event(pbp)]]

def get_run_dest(text):
    if 'picked off' in text and not ' out at ' in text:
        return [-1, 0]
    return [ref.run_codes[key] for key in ref.run_codes.keys() if key in text][-1]


class Runner:
    def __init__(self, id, pitcher):
        self.id = id
        self.resp = pitcher

def find_events(text):
    """find pbp events within a play by play string

    :param text: play by play string
    :type text: str
    :return: list of events in order of occurence in the string
    :rtype: list
    """    
    events = {key: text.index(key) for key in ref.all_codes if key in text}
    sort_events = {k: v for k, v in sorted(events.items(), key=lambda item: item[1])}
    return list(sort_events.keys())

# def get_det_event(text, type):
#     e = [[key, ref.mod_codes[key]] for key in ref.mod_codes.keys() if key in text]
#     if e == []:
#         return ['','']
#     else:
#         return e[0]

def play_names(text, names):
    """get player names and indexes within the play by play strings

    :param text: play by play text
    :type text: str
    :param names: name directory of offensive team
    :type names: dict
    """
    # print([string.capwords(name) for name in names.values()])
    # print("".join([s.capitalize() + ' ' if s[0].isupper() else s + ' ' for s in text.replace(':', ': ').split(' ')]))
    # print([name.lower().capitalize() for name in names.values if string.capwords(name.lower()) + ' ' in "".join([s.capitalize() for s in text.split(':')])])
    players = {name: text.index(name) for name in names.values() if string.capwords(name) + ' ' in "".join([s.capitalize() + ' ' if s[0].isupper() else s + ' ' for s in text.replace(':', ': ').split(' ')])}
    # print(players)
    return({k: v for k, v in sorted(players.items(), key=lambda item: item[1], reverse=True)})

def get_fielders(text, event):
    return [ref.pos_codes[key] for key in ref.pos_codes.keys() if key in text.split(' ' + event)[1]]

