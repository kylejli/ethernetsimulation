import random
import simpy
import math
import sys


# First  define some global variables
class G:
    RANDOM_SEED = 33
    SIM_TIME = 1000000

# Time slot object
# Can set and return the time slot that it contains
class SlotObject(object):
    def __init__(self, time):
        self.slot = time

    def ret(self):
        return self.slot

    def set(self, time):
        self.slot = time


# Count object
# Initialized as zero
# can increment and return the count
class CountObject(object):
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def ret(self):
        return self.count

# Receiver Process
# When initialized also initializes all the host processes
class Receiver_Process(object):
    # constructor initializes host processes
    def __init__(self, env, N, algo, arrival_rate, successes):
        self.env = env
        self.N = N
        self.successes = successes
        # transmit_slots is an array that holds the next transmit slot of each host process
        self.transmit_slots = []
        # initialize transmit_slots to be SIM_TIME (not transmitting)
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
        # host_indices is array that holds the indices of the hosts that are trying to transmit in the current slot
        self.host_indices = []
        self.action = env.process(self.run())

    def run(self):
        while True:
            # active_nodes keep track of how many nodes/ hosts are trying to transmit in the current slot
            active_nodes = 0
            # clear host_indices
            self.host_indices.clear()
            # check each host process if transmit_slot is current slot
            for x in range(self.N):
                # if transmit_slot is current slot then increment active_nodes and append index to host_indices
                if self.transmit_slots[x].ret() == self.env.now:
                    active_nodes += 1
                    self.host_indices.append(x)
            # if only one active node, then successful
            if active_nodes == 1:
                # increment successes
                self.successes.increment()
                # call host process success function
                self.hosts[self.host_indices[0]].success()
            # if multiple active nodes, then must retransmit
            elif active_nodes > 1:
                for x in range(len(self.host_indices)):
                    self.hosts[self.host_indices[x]].retransmit()
            # sleep until next time slot
            yield self.env.timeout(1)

# 0.5-persistent host process
class Host_Process_pp(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        # queued_packets is number of packets in host process buffer
        self.queued_packets = 0
        self.action = env.process(self.arrival())

    # arrival process
    def arrival(self):
        while True:
            # sleep for amount of time determined by Poisson process with rate arrival_rate
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            # if buffer was empty, and new packet arrives try to transmit at next time slot
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    # 0.5-persistent retransmit function (after unsuccessful transmission)
    def retransmit(self):
        # tries to transmit at each slot with probability 0.5 until success (binomial distribution)
        count = 1
        while (random.random() >= 0.5):
            count += 1
        self.transmit_slot.set(math.ceil(self.env.now) + count)

    # success function
    def success(self):
        # remove successful packet (decrement dequeued_packets)
        self.queued_packets -= 1
        # if there is another packet in buffer, attempt to transmit at next time slot
        if self.queued_packets > 0:
            # add 0.1 because we want next time slot
            self.transmit_slot.set(math.ceil(self.env.now + 0.1))
        # otherwise set transmit_slot to SIM_TIME (dont transmit)
        else:
            self.transmit_slot.set(G.SIM_TIME)

# 1/N-persistent host process
class Host_Process_op(object):
    def __init__(self, env, transmit_slot, N, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.p = 1 / N
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())

    # arrival process
    def arrival(self):
        while True:
            # sleep for amount of time determined by Poisson process with rate arrival_rate
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            # if buffer was empty, and new packet arrives try to transmit at next time slot
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    # 1/N-persistent retransmit function (after unsuccessful transmission)
    def retransmit(self):
        # tries to transmit at each slot with probability 1/N until success (binomial distribution)
        count = 1
        while (random.random() >= self.p):
            count += 1
        self.transmit_slot.set(math.ceil(self.env.now) + count)

    # success function
    def success(self):
        # remove successful packet (decrement dequeued_packets)
        self.queued_packets -= 1
        # if there is another packet in buffer, attempt to transmit at next time slot
        if self.queued_packets > 0:
            # add 0.1 because we want next time slot
            self.transmit_slot.set(math.ceil(self.env.now + 0.1))
        # otherwise set transmit_slot to SIM_TIME (dont transmit)
        else:
            self.transmit_slot.set(G.SIM_TIME)

# binomial exponential backoff host process
class Host_Process_beb(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())
        # keep number of retransmission attempts
        self.retransmission_attempts = 0

    # arrival process
    def arrival(self):
        while True:
            # sleep for amount of time determined by Poisson process with rate arrival_rate
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            # if buffer was empty, and new packet arrives try to transmit at next time slot
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    # binomial exponential backoff retransmit function (after unsuccessful transmission)
    def retransmit(self):
        # retransmit after delay uniformly distributed from [0, 2^K]
        # where K = min(retransmission_attempts, 10)
        self.retransmission_attempts += 1
        k = min(self.retransmission_attempts, 10)
        delay = random.randint(0, 2 ** k)
        # add 0.1 because cant retransmit on same time slot
        self.transmit_slot.set(math.ceil(self.env.now + delay + 0.1))

    # success function
    def success(self):
        # remove successful packet (decrement dequeued_packets)
        self.queued_packets -= 1
        # reset retransmission_attempts
        self.retransmission_attempts = 0
        # if there is another packet in buffer, attempt to transmit at next time slot
        if self.queued_packets > 0:
            # add 0.1 because we want next time slot
            self.transmit_slot.set(math.ceil(self.env.now + 0.1))
        # otherwise set transmit_slot to SIM_TIME (dont transmit)
        else:
            self.transmit_slot.set(G.SIM_TIME)

# linear backoff host process
class Host_Process_lb(object):
    def __init__(self, env, transmit_slot, arrival_rate):
        self.env = env
        self.transmit_slot = transmit_slot
        self.arrival_rate = arrival_rate
        self.queued_packets = 0
        self.action = env.process(self.arrival())
        # keep number of retransmission attempts
        self.retransmission_attempts = 0

    # arrival process
    def arrival(self):
        while True:
            # sleep for amount of time determined by Poisson process with rate arrival_rate
            yield self.env.timeout(random.expovariate(self.arrival_rate))
            self.queued_packets += 1
            # if buffer was empty, and new packet arrives try to transmit at next time slot
            if self.queued_packets == 1:
                self.transmit_slot.set(math.ceil(self.env.now))

    # linear backoff retransmit function (after unsuccessful transmission)
    def retransmit(self):
        # retransmit after delay uniformly distributed from [0, K]
        # where K = min(retransmission_attempts, 1024)
        self.retransmission_attempts += 1
        k = min(self.retransmission_attempts, 1024)
        delay = random.randint(0, k)
        # add 0.1 because cant retransmit on same time slot
        self.transmit_slot.set(math.ceil(self.env.now + delay + 0.1))

    # success process
    def success(self):
        # remove successful packet (decrement dequeued_packets)
        self.queued_packets -= 1
        # reset retransmission_attempts
        self.retransmission_attempts = 0
        # if there is another packet in buffer, attempt to transmit at next time slot
        if self.queued_packets > 0:
            # add 0.1 because we want next time slot
            self.transmit_slot.set(math.ceil(self.env.now + 0.1))
        # otherwise set transmit_slot to SIM_TIME (dont transmit)
        else:
            self.transmit_slot.set(G.SIM_TIME)


def main():
    # check that there are 3 arguments
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
    # print("Number of Nodes: " + str(N) + ", Retransmission Policy: " + algo + ", Arrival rate: " + str(arriv_rate) + ", Throughput: " + str(successes.ret()/G.SIM_TIME) + ", N * lambda: " + str(arriv_rate * N))

    # print throughput (successes divided by total slots)
    print("{:.2f}".format(successes.ret()/G.SIM_TIME, 2))



if __name__ == '__main__': main()
