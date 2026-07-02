from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.log import setLogLevel

class CustomTopo(Topo):
    def build(self):
        # Create hosts and switch
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        s1 = self.addSwitch('s1')

        # Link h1 to s1 with 0.2 ms delay
        self.addLink(h1, s1, 
	#delay='0.2ms'
	)

        # Link s1 to h2 with 3.5 Mbps bandwidth
        self.addLink(s1, h2, 
	#bw=0.025,
	#delay='0.2ms'
	)

def run():
    topo = CustomTopo()
    # Replace with your remote ONOS controller IP
    controller_ip = '192.168.1.100'
    net = Mininet(topo=topo, controller=lambda name: RemoteController(name, ip=controller_ip), link=TCLink)
    
    net.start()

    # --- MANUAL TRAFFIC CONTROL CONFIGURATION ---
    # Configure Switch Interface (s1-eth2) facing Host 2
    # rate 24kbit: Enforces serialization delay (even for 0.1 pps)
    # limit 100000: Ensures no drops (huge buffer)
    s1 = net.get('s1')
    s1.cmd('tc qdisc replace dev s1-eth2 root netem rate 24kbit limit 100000')
    # =========================
    # MINIMAL ADDITION START
    # =========================
    #import time

    #h1 = net.get('h1')
    #h2 = net.get('h2')

    #print("*** Waiting 5 seconds after netem...")
    #time.sleep(5)

    #print("*** Starting receiver on h2...")
    #h2.cmd('xterm -hold -e "mgen input recv.mgn &> mgm_recv.log" &')

    #print("*** Waiting 5 seconds before starting sender...")
    #time.sleep(5)

    #print("*** Starting sender on h1...")
    #h1.cmd('xterm -hold -e "./run_mgn_multiple_rates.sh" &')
    # =========================
    # MINIMAL ADDITION END
    # =========================

    # (Optional) Apply the same to h2's upload interface if traffic is bidirectional
    #h2 = net.get('h2')
    #h2.cmd('tc qdisc replace dev h2-eth0 root netem rate 24kbit limit 100000')
    # ------------------------------------------

    net.interact()
    #print("Network is up. Use CLI to test.")
    #net.pingAll()
    #net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()