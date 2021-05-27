import random
import simpy
import math
import sys


# First  define some global variables
class G:
    RANDOM_SEED = 33
    SIM_TIME = 1000000


class SlotObject(object):
    def __init__(self, time):
        self.slot = time

    def ret(self):
        return self.slot

    def set(self, time):
        self.slot = time


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
            self.transmit_slots.append(SlotObject(G.SIM_TIME))
        self.hosts = []
        # Created multiple Host_Process classes so that I wouldn't need if statements every time a
        # host attempted to retransmit, making code faster
        if algo == "pp":
            for x in range(N):
                self.hosts.append(Host_Process_pp(env, self.transmit_slots[x], arrival_rate))
        elif algo == "op":
            for x in range(N):
                self.hosts.append(Host_Process_op(env, self.transmit_slots[x], N, arrival_rate))
        elif algo == "beb":
            for x in range(N):
                self.hosts.append(Host_Process_beb(env, self.transmit_slots[x], arrival_rate))
        elif algo == "lb":
            for x in range(N):
                self.hosts.append(Host_Process_lb(env, self.transmit_slots[x], arrival_rate))
        else:
            print("algo must be \'pp\', \'op\', \'beb\', or \'lb\'")
            exit()
        self.host_indices = []
        self.action = env.process(self.run())

    def run(self):
        while True:
            active_nodes = 0
            self.host_indices.clear()
            # print("Current time: " + str(self.env.now))
            for x in range(self.N):
                if self.transmit_slots[x].ret() == self.env.now:
                    active_nodes += 1
                    self.host_indices.append(x)
                    # print(str(x) + " attemping to transmit")
            if active_nodes == 1:
                self.successes.increment()
                self.hosts[self.host_indices[0]].success()
            elif active_nodes > 1:
                for x in range(len(self.host_indices)):
                    self.hosts[self.host_indices[x]].retransmit()
            yield self.env.timeout(1)


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
                # ("packet arrived at time " + str(self.env.now) + ", attempting to transmit at time " + str(math.ceil(self.env.now)))
                self.transmit_slot.set(math.ceil(self.env.now))

    def retransmit(self):
        count = 1
        while (random.random() >= 0.5):
            count += 1
        self.transmit_slot.set(math.ceil(self.env.now) + count)
        # print("Will attempt to retransmit at time " + str(math.ceil(self.env.now) + count))

    def success(self):
        self.queued_packets -= 1
        # print("Packet successfully transmitted!")
        if self.queued_packets > 0:
            self.transmit_slot.set(math.ceil(self.env.now))
        else:
            self.transmit_slot.set(G.SIM_TIME)


class Host_Process_op(object):
    def __init__(self, env, transmit_slot, N, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.p = 1 / N
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())

    def arrival(self):
        while True:
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    def retransmit(self):
        count = 1
        while (random.random() >= self.p):
            count += 1
        self.transmit_slot.set(math.ceil(self.env.now) + count)

    def success(self):
        self.queued_packets -= 1
        if self.queued_packets > 0:
            self.transmit_slot.set(math.ceil(self.env.now))
        else:
            self.transmit_slot.set(G.SIM_TIME)


class Host_Process_beb(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())
        self.retransmission_attempts = 0

    def arrival(self):
        while True:
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    def retransmit(self):
        self.retransmission_attempts += 1
        k = min(self.retransmission_attempts, 10)
        delay = random.randint(0, 2 ** k)
        self.transmit_slot.set(math.ceil(self.env.now + delay + 0.1))

    def success(self):
        self.queued_packets -= 1
        self.retransmission_attempts = 0
        if self.queued_packets > 0:
            self.transmit_slot.set(math.ceil(self.env.now))
        else:
            self.transmit_slot.set(G.SIM_TIME)


class Host_Process_lb(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())
        self.retransmission_attempts = 0

    def arrival(self):
        while True:
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    def retransmit(self):
        self.retransmission_attempts += 1
        k = min(self.retransmission_attempts, 1024)
        delay = random.randint(0, k)
        self.transmit_slot.set(math.ceil(self.env.now + delay + 0.1))

    def success(self):
        self.queued_packets -= 1
        self.retransmission_attempts = 0
        if self.queued_packets > 0:
            self.transmit_slot.set(math.ceil(self.env.now))
        else:
            self.transmit_slot.set(G.SIM_TIME)


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
    # print(str(arriv_rate * N))
    # print(str(successes.ret()))
    # print(str(successes.ret()/G.SIM_TIME))
    print("Number of Nodes: " + str(N) + ", Retransmission Policy: " + algo + ", Arrival rate: " + str(arriv_rate) + ", Throughput: " + str(successes.ret()/G.SIM_TIME) + ", N * lambda: " + str(arriv_rate * N))


if __name__ == '__main__': main()
