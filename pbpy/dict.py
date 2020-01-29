import pandas as pd

teamindex = pd.read_csv(
    'https://raw.githubusercontent.com/milesok/ncaa-baseball/master/data/teams.csv')

codes = {
    'singled': '1B',
    'doubled': '2B',
    'tripled': '3B',
    'homered': 'HR',
    'flied out': 'O',
    'flied into double play': 'O',
    'flied into triple play': 'O',
    'popped up': 'O',
    'popped out': 'O',
    'popped into double play': 'O',
    'popped into triple play': 'O',
    'lined into double play': 'O',
    'lined into triple play': 'O',
    'lined out': 'O',
    'struck out looking': 'SO',
    'struck out swinging': 'SO',
    'struck out': 'SO',
    'grounded out': 'O',
    'out at first': 'O',  # ONLY FOR BATTERS - check on this for fielding
    'grounded into double play': 'O',
    'hit into double play': 'O',
    'hit into triple play': 'O',
    'fouled into double play': 'O',
    'fouled out': 'O',  # when doing fielders, add f after fielder code
    'infield fly': 'O',
    'hit by pitch': 'HBP',
    'walked': 'BB',
    'stole': 'SB',
    'picked off': 'PO',
    'caught stealing': 'CS',
    'wild pitch': 'WP',
    'passed ball': 'PB',
    'balk': 'BK',
    'out on batter\'s interference': 'BINT',
    'reached on catcher\'s interference': 'C',
    'reached on a throwing error': 'E',
    'reached on a fielding error': 'E',
    'reached on an error': 'E',
    'reached first on a dropped fly' : 'E',
    'reached on a dropped fly' : 'E',
    'reached on a fielder\'s choice': 'FC',
    'indifference' : 'DI'
}
mod_codes = {
    'singled': '1B',
    'doubled': '2B',
    'tripled': '3B',
    'homered': 'HR',
    'flied out': 'F',
    'flied into double play': 'FDP',
    'flied into triple play': 'FTP',
    'popped up': 'P',
    'popped out': 'P',
    'infield fly': 'P',  # label w/ flag?
    'popped into double play': 'PDP',
    'popped into triple play': 'PTP',
    'lined into double play': 'LDP',
    'lined into triple play': 'LTP',
    'lined out': 'L',
    'struck out looking': 'KL',
    'struck out swinging': 'KS',
    'struck out': 'K',
    'grounded out': 'G',
    'out at first': 'G',  # ONLY FOR BATTERS - check on this for fielding
    'grounded into double play': 'GDP',
    'hit into double play': 'GDP',
    'hit into triple play': 'GTP',
    'fouled into double play': 'FDP',
    'fouled out': 'FL',  # when doing fielders, add f after fielder code
    'hit by pitch': 'HBP',
    'walked': 'BB',
    'stole': 'SB',
    'picked off': 'PO',
    'caught stealing': 'CS',
    'wild pitch': 'WP',
    'passed ball': 'PB',
    'balk': 'BK',
    'out on batter\'s interference': 'BINT',
    'reached on catcher\'s interference': 'C',
    'error': 'E',
    'dropped fly': 'E',
    'a throwing error': 'TH',
    'fielder\'s choice': 'FC'
}
event_codes = {
    'G': 2,
    'F': 2,
    'P': 2,
    'L': 2,
    'FL': 2,
    'GDP': 2,
    'FDP' : 2,
    'BINT': 2,
    'O' : 2,
    'KL': 3,
    'KS': 3,
    'K': 3,
    'SO': 3,
    'SB': 4,
    'DI': 5,
    'CS': 6,
    'PO': 8,
    'WP': 9,
    'PB': 10,
    'BK': 11,
    'BB': 14,
    'IBB': 15,
    'HBP': 16,
    'C': 17,
    'E': 18,
    'FC': 19,
    '1B': 20,
    '2B': 21,
    '3B': 22,
    'HR': 23
}
pos_codes = {
    'p': 1,
    'c': 2,
    '1b': 3,
    '2b': 4,
    '3b': 5,
    'ss': 6,
    'lf': 7,
    'cf': 8,
    'rf': 9,
    'dh': 10,
    'ph': 11,
    'pr': 12
}
base_codes = {
    'first': 1,
    'second': 2,
    'third': 3,
    'home': 4,
    'scored': 4,
    'out': 0
}
run_codes = {
    'reached first': [1,1],
    'reached on': [1,1],
    'singled': [1,1],
    'walked': [1,1],
    'hit by pitch': [1,1],
    'doubled': [2,1],
    'advanced to second': [2,1],
    'stole second': [2,1],
    'tripled': [3,1],
    'advanced to third': [3,1],
    'stole third': [3,1],
    'homered': [4,1],
    'scored': [4,1],
    'stole home': [4,1],
    'grounded out':[1,0],
    'grounded into double play':[1,0],
    'grounded into triple play':[1,0],
    'hit into double play':[1,0],
    'hit into triple play':[1,0],
    'fouled': [0,0],
    'flied':[0,0],
    'popped':[0,0],
    'lined':[0,0],
    'infield fly':[0,0],
    'out at first': [1,0],
    'out at second': [2,0],
    'out at third': [3,0],
    'out at home': [4,0],
    'out on the play': [0,0],
    'struck out': [0,0],
    'out on batter\'s interference': [0,0],
    'reached on catcher\'s interference': [1,0]
}
loc_codes = {
    'to pitcher': 1,
    'to catcher': 2,
    'to first base': 3,
    'through the right side': 34,
    'to second base': 4,
    'to third base': 5,
    'through the left side': 56,
    'to shortstop': 6,
    'to left field': 7,
    'down the lf line': 7,
    'to left center': 78,
    'to center field': 8,
    'up the middle': 46,
    'to right center': 89,
    'to right': 9,
    'down the rf line': 9
}
sub_codes = {
'pinch hit for' : 'PH',
'pinch ran for' : 'PR',
' to ' : 'DEF'
}
