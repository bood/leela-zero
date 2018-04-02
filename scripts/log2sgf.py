import os
import argparse
import matplotlib.pyplot as plt


def seperate_log(logname):
    log_file = open(logname,"r")
    log=log_file.read()
    log_file.close()

    segments = []
    segment = []
    for line in log.split('\n'):
        if not line:
            continue

        if line[:2]==">>" or line[:2]=="= " :
            segments.append(segment)
            segment=[]

        segment.append(line)

    black_segments = []
    white_segments = []
    lz_segments = []
    is_black = None
    for segment in segments:
        if ">>genmove b" in segment[0]:
            if is_black == False:
                raise Exception("Cannot determine LZ is white or black")
            is_black = True
            black_segments.append(segment)
        elif ">>play B" in segment[0]:
            black_segments.append(segment)
        elif ">>genmove w" in segment[0]:
            if is_black == True:
                raise Exception("Cannot determine LZ is white or black")
            is_black = False
            white_segments.append(segment)
        elif ">>play W" in segment[0]:
            white_segments.append(segment)

    print("lz is %s" % ("black" if is_black else "white"))

    if is_black:
        lz_segments = black_segments
        player_segments = white_segments
    else:
        player_segments = black_segments
        lz_segments = white_segments

    return player_segments, lz_segments, is_black


def move2sgf(move):
    sgf_coord = "abcdefghijklmnopqrs"
    lz_coord = "ABCDEFGHJKLMNOPQRST"

    if move == "pass" or move == "PASS":
        return "tt"

    index1 = lz_coord.index(move[0])
    index2 = 19 - int(move[1:])
    sgf_move = sgf_coord[index1] + sgf_coord[index2]
    return sgf_move


def get_player_move(segment, is_black, lz_variation=None):
    line = segment[0]
    if is_black:
        move = line.split(">>play W ")[1].split("\r")[0].strip()
        sgf_move = "(;W[%s]NOW)" % move2sgf(move)
        if lz_variation:
            sgf_move += lz_variation
    else:
        move = line.split(">>play B ")[1].split("\r")[0].strip()
        sgf_move = "(;B[%s]NOW)" % move2sgf(move)
        if lz_variation:
            sgf_move += lz_variation
    return sgf_move


def get_lz_move(segment, is_black, last_win_rate):
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

    if not win_rates:
        move = "pass"
        if ">>play" in segment[0]:
            move = segment[0].split(" ")[2].strip()
            print move
        win_rates = [0]
        playouts = [0]
        moves = [move]
        sequences = [move]

    pv = []
    pv.append(get_lz_pv(sequences[0], is_black, ignore_first=True))

    # if no big differences, add two variations
    add_pv2 = False
    if (len(win_rates) > 1):
        if (abs(win_rates[0]-win_rates[1]) < 3 and playouts[0] < 5*playouts[1]):
            add_pv2 = True
            pv.append(get_lz_pv(sequences[1], is_black))

    if last_win_rate:
        win_rate_delta = win_rates[0] - last_win_rate
    else:
        win_rate_delta = 0.0

    if is_black:
        sgf_move = "(;B[%s]C[LZ win rate: %5.2f (%5.2f)\nMain Variation: %s]NOW)" % \
            (move2sgf(moves[0]), win_rates[0], win_rate_delta, sequences[0])
        lz_variation = "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
            (win_rates[0],  playouts[0], pv[0])
        if add_pv2:
            sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
                (win_rates[1],  playouts[1], pv[1])
    else:
        sgf_move = "(;W[%s]C[LZ win rate: %5.2f  (%5.2f)\nMain Variation: %s]NOW)" % \
            (move2sgf(moves[0]), win_rates[0], win_rate_delta, sequences[0])
        lz_variation = "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
            (win_rates[0],  playouts[0], pv[0])
        if add_pv2:
            sgf_move += "(;C[LZ win rate: %5.2f\nPlayouts: %d]%s)" % \
                (win_rates[1],  playouts[1], pv[1])

    return sgf_move, lz_variation, win_rates[0]


def get_lz_pv(sequence, is_black, ignore_first=False):
    pv = ""
    start_index = 1 if ignore_first else 0
    for move in sequence.split(' ')[start_index:]:
        if is_black != ignore_first:
            pv += ";B[%s]" % move2sgf(move)
        else:
            pv += ";W[%s]" % move2sgf(move)
        is_black = not is_black
    pv = pv[1:]
    return pv


def create_sgf(logname):
    player_segments, lz_segments, is_black = seperate_log(logname)

    content = "(;FF[4]CA[UTF-8]KM[7.5]SZ[19]\nNOW)"
    lz_variation = None
    lz_win_rate = None
    if is_black:
        for (lz, pl) in zip(lz_segments, player_segments):
            (lz_move, lz_variation, lz_win_rate) = get_lz_move(lz, is_black, lz_win_rate)
            content = content.split("NOW")[0] + lz_move + content.split("NOW")[1]
            pl_move = get_player_move(pl, is_black, lz_variation)
            content = content.split("NOW")[0] + pl_move + content.split("NOW")[1]
    else:
        for (pl, lz) in zip(player_segments, lz_segments):
            pl_move = get_player_move(pl, is_black, lz_variation)
            content = content.split("NOW")[0] + pl_move + content.split("NOW")[1]
            (lz_move, lz_variation, lz_win_rate) = get_lz_move(lz, is_black, lz_win_rate)
            content = content.split("NOW")[0] + lz_move + content.split("NOW")[1]
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
                    # For Leela Zero, the value network is used as win rate
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
    _, tempfilename = os.path.split(logname)
    filename, _ = os.path.splitext(tempfilename)

    content, lz_segments = create_sgf(logname)

    sgf = open(filename+'.sgf', 'w')
    sgf.write(content)
    sgf.close()

    fig = plot_lz_winrate(lz_segments)
    fig.savefig(filename+'.png', dpi=200)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--log', 
        dest='logname', 
        default="log.txt", 
        help='Path to LZ log file.')

    args = parser.parse_args()

    main(args.logname)
