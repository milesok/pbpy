import re
import play
import sub

def parse_half(g, half):
    for play in half:
        parse(play)
        g.play += 1
    g.advance_half()

def parse(pbp_txt, g):
    [type, txt] = get_type(pbp_txt)
    if type == 's':
        s = sub.Sub(pbp_txt, g)
        return s
        # g.make_sub(s)
    elif type == 'p':
        p = play.Play(pbp_txt, g)
        return p
        # p.execute(g)

def get_type(s): #  PLAY OR SUB -> BREAK DOWN INTO PARTS
    """
    checks whether play is a substitution, returns list
    containing name of player substituted in, sub type/position,
    and player substituted out if applicable
    Parameters
    ----------
    s : str
        pbp string

    Returns
    -------
    list
        substitution summary: [sub in, sub type/position,
        sub out or None]
    bool
        false if there is no substitution
    """
    s = s.replace('/ ', '/ to x')
    subtest = re.search(r"^([A-Za-z,\. '-]*?(?= [a-z])|\/) (pinch (?:hit|ran)|to [0-9a-z]{1,2})* *(?:for ([A-Za-z,\. '-]*?)\.$)*", s)
    if not subtest is None:
        subtest = [subtest.group(1), subtest.group(2), subtest.group(3)]
        if not subtest[1] is None:
            return ['s', subtest]
    return ['p', s.split(':')]
