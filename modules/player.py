class Player:
    def __init__(self, name, id, pos, switch, order, sub, sub_id, status, team):
        self.name = name
        self.id = id
        self.pos = pos
        self.switch = switch
        self.order = order

        self.sub = sub
        self.sub_id = sub_id
        self.status = status # 'available', 'entered', 'removed'
        self.team = team
        self.pbp_name = None