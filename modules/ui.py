def print_lineups(game):
    print('\n')
    print("AWAY")
    for player in game.lineups[0].lineup:
        print_player(player)
    print("\nHOME")
    for player in game.lineups[1].lineup:
        print_player(player)

def print_subs(game):
    print('\n')
    print("AWAY")
    for player in game.lineups[0].subs:
        print_player(player)
    print("\nHOME")
    for player in game.lineups[1].subs:
        print_player(player)


def print_player(player):
    print(player.pos + " "*(3-len(player.pos)) + "| " + player.name + " "*(20-len(player.name)) + str(player.order))
    # print("switch: " + str(player.switch) + " | sub: " + player.sub)

def print_play(play):
    pass

def print_state(game):
    runners = game.state['runners']
    print('\n')
    print('Score: ' + str(game.state['a_score']) + '-' + str(game.state['h_score']))
    print('I: ' + ('t' if game.state['half'] == 0 else 'b') + str(game.state['inning']))
    print('O: ' + str(game.state['outs']))
    print('1B: ' + runners[0])
    print('2B: ' + runners[1])
    print('3B: ' + runners[2])
