from __future__ import print_function

import os
import matplotlib.pyplot as plt
from optparse import OptionParser

def seperate_log(logname):
    log_file = open(logname,"r")
    log=log_file.read()
    log_file.close()

    segments=[]
    segment=[]
    for line in log.split('\n'):
        if not line:
            continue

        if line[:2]==">>" or line[:2]=="= " :
            segments.append(segment)
            segment=[]

        segment.append(line)

    player_segments = []
    for segment in segments:
        if ">>play" in segment[0]:
            player_segments.append(segment)

    lz_segments=[]
    for segment in segments:
        if ">>genmove" in segment[0]:
            lz_segments.append(segment)

    if ">>genmove b" in lz_segments[0][0]:
        print("lz is black")
        is_black = True
    else:
        print("lz is white")
        is_black = False

    return player_segments, lz_segments, is_black

def move2sgf(move):
    sgf_coord = "abcdefghijklmnopqrs"
    lz_coord = "ABCDEFGHJKLMNOPQRST"

    if (move == "pass"):
        return "tt"

    index1 = lz_coord.index(move[0])
    index2 = 19 - int(move[1:])
    sgf_move = sgf_coord[index1] + sgf_coord[index2]
    return(sgf_move)

def get_player_move(segment, is_black):
    line = segment[0]
    if (is_black):
        move = line.split(">>play W ")[1].split("\r")[0].strip()
        sgf_move = ";W[%s]NOW" % move2sgf(move)
    else:
        move = line.split(">>play B ")[1].split("\r")[0].strip()
        sgf_move = ";B[%s]NOW" % move2sgf(move)
    return sgf_move

def get_lz_move(segment, is_black):
    moves = []
    win_rates = []
    playouts = []
    sequences = []
    for err_line in segment:
        if " ->" in err_line:
            if err_line[0]==" ":
                move = err_line.split(" ->")[0].strip()
                moves.append(move)

                win_rate = float(err_line.split("(V:")[1].split('%')[0].strip())
                win_rates.append(win_rate)

                nodes=err_line.strip().split("(")[0].split("->")[1].replace(" ","")
                playouts.append(int(nodes))

                sequence=err_line.split("PV: ")[1].strip()
                sequences.append(sequence)

    pv = []
    pv.append(get_lz_pv(sequences[0], is_black))
    add_pv2 = False
    # if no big differences, add two variations
    if (abs(win_rates[0]-win_rates[1]) < 3 and playouts[0] < 5*playouts[1]):
        add_pv2 = True
        pv.append(get_lz_pv(sequences[1], is_black))

    if (is_black):
        sgf_move = "(;B[%s]C[LZ win rate: %5.2f\nMain Variation: %s]NOW)" % \
            (move2sgf(moves[0]), win_rates[0], sequences[0])
        sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
            (win_rates[0],  playouts[0], pv[0])
        if (add_pv2):
            sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
                (win_rates[1],  playouts[1], pv[1])
    else:
        sgf_move = "(;W[%s]C[LZ win rate: %5.2f\nMain Variation: %s]NOW)" % \
            (move2sgf(moves[0]), win_rates[0], sequences[0])
        sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
            (win_rates[0],  playouts[0], pv[0])
        if (add_pv2):
            sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
                (win_rates[1],  playouts[1], pv[1])

    return sgf_move

def get_lz_pv(sequence, is_black):
    pv = ""
    for move in sequence.split(' '):
        if (is_black):
            pv += ";B[%s]" % move2sgf(move)
        else:
            pv += ";W[%s]" % move2sgf(move)
        is_black = not is_black
    pv = pv[1:]
    return pv

def create_sgf(logname):
    player_segments, lz_segments, is_black = seperate_log(logname)

    content = "(;FF[4]CA[UTF-8]KM[7.5]SZ[19]\nNOW)"
    if (is_black):
        for (lz, pl) in zip(lz_segments, player_segments):
            lz_move = get_lz_move(lz, is_black)
            content = content.split("NOW")[0] + lz_move + content.split("NOW")[1]
            pl_move = get_player_move(pl, is_black)
            content = content.split("NOW")[0] + pl_move + content.split("NOW")[1]
        print(content)
    else:
        for (pl, lz) in zip(player_segments, lz_segments):
            pl_move = get_player_move(pl, is_black)
            content = content.split("NOW")[0] + pl_move + content.split("NOW")[1]
            lz_move = get_lz_move(lz, is_black)
            content = content.split("NOW")[0] + lz_move + content.split("NOW")[1]
        print(content)
    content = content.split("NOW")[0] + content.split("NOW")[1]

    return content, lz_segments

def parse_lz_winrate(lz_segments):
    playouts_history = []
    value_network_history = []
    for segment in lz_segments:
        for err_line in segment:
            if " ->" in err_line:
                if err_line[0]==" ":
                    nodes=err_line.strip().split("(")[0].split("->")[1].replace(" ","")
                    playouts_history.append(int(nodes))

                    value_network=err_line.split("(V:")[1].split('%')[0].strip()
                    #for Leela Zero, the value network is used as win rate
                    value_network_history.append(float(value_network))

                    break
    return value_network_history, playouts_history

def plot_lz_winrate(lz_segments):
    value_network_history, playouts_history = parse_lz_winrate(lz_segments)

    game_length = len(value_network_history)
    moves = [2*x for x in range(game_length)]

    fig = plt.figure(figsize=(12, 8))
    ax1 = fig.add_subplot(111)
    ax1.set_ylim(-10, 110)
    ax1.plot(moves, value_network_history, label="win rate")
    ax1.set_ylabel("win rate %")
    ax1.legend(loc=2)
    ax1.hlines(50, 0, 2*game_length, color="red")
    ax1.set_title("Win Rate of LZ ")

    ax2 = ax1.twinx()
    ax2.plot(moves, playouts_history, label="playouts", color="orange")
    ax2.set_ylabel("# of playouts")
    ax2.legend(loc=1)
    ax2.set_xlabel("steps")

    return fig

def main(logname):
    filepath, tempfilename = os.path.split(logname)
    filename, extension = os.path.splitext(tempfilename)

    content, lz_segments = create_sgf(logname)

    sgf = open(filename+'.sgf', 'w')
    sgf.write(content)
    sgf.close()

    fig = plot_lz_winrate(lz_segments)
    fig.savefig(filename+'.png', dpi=200)

if __name__ == '__main__':
    parser = OptionParser()

    parser.add_option(
        "-l", "--log",
        action="store",
        dest="logname",
        default="log.txt",
        type="string",
        help="path to LZ log file"
    )

    (options, args) = parser.parse_args()

    main(options.logname)
