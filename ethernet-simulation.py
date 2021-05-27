import sys

if(len(sys.argv) != 4):
    print("must give exactly 3 parameters: number of nodes, retransmission algorithm (pp, op, beb, lb), arrival rate")
    exit()

N = sys.argv[1]
algo = sys.argv[2]
arrivRate = sys.argv[3]


