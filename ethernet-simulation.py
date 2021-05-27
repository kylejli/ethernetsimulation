import random
import simpy
import math
import sys


# First  define some global variables
class G:
    RANDOM_SEED = 33
    SIM_TIME = 2
    P = 0.5


class SlotObject(object):
    def __init__(self, time):
        self.slot = time

    def ret(self):
        return self.slot


class CountObject(object):
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def ret(self):
        return self.count


class Receiver_Process(object):
    def __init__(self, env, N, algo, arrival_rate, successes):
        self.env = env
        self.N = N
        self.successes = successes
        self.transmit_slots = []
        for x in range(N):
            self.transmit_slots.append(G.SIM_TIME)
        self.hosts = []
        for x in range(N):
            self.hosts.append(Host_Process_pp(env, self.transmit_slots[x], arrival_rate))
        self.host_indices = []
        self.action = env.process(self.run())

    def run(self):
        while True:
            active_nodes = 0
            self.host_indices.clear()
            for x in range(self.N):
                if self.transmit_slots[x] == self.env.now:
                    active_nodes += 1
                    self.host_indices.append(x)
            if active_nodes == 1:
                self.successes.increment()
                self.hosts[self.host_indices[0]].success()
            elif active_nodes > 1:
                for x in len(self.host_indices):
                    self.hosts[self.host_indices[x]].retransmit()


class Host_Process_pp(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())

    def arrival(self):
        while True:
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            if self.queued_packets == 1:
                self.transmit_slot = math.ceil(self.env.now)

    def retransmit(self):
        count = 1
        while (random.random() >= G.P):
            count += 1
        self.transmit_slot = count

    def success(self):
        self.queued_packets -= 1
        if self.queued_packets > 0:
            self.transmit_slot = math.ceil(self.env.now)
        else:
            self.transmit_slot = G.SIM_TIME


def main():
    if (len(sys.argv) != 4):
        print("must give exactly 3 parameters: number of nodes, retransmission algorithm (pp, op, beb, lb), arrival rate")
        exit()

    N = int(sys.argv[1])
    algo = sys.argv[2]
    arriv_rate = float(sys.argv[3])

    random.seed(G.RANDOM_SEED)

    env = simpy.Environment()
    successes = CountObject()
    Receiver_Process(env, N, algo, arriv_rate, successes)
    env.run(until=G.SIM_TIME)
    print(str(arriv_rate * N))
    print(str(successes.ret()))


if __name__ == '__main__': main()
