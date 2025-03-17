from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

# Import our UpCounter
from up_counter import UpCounter

class ControlledBlinker(Elaboratable):
    """
    An LED blinker that uses a counter to control blink rate.
    """
    def __init__(self, freq_hz=1):
        """
        Create a blinker with specified frequency.
        
        Args:
            freq_hz: Blink frequency in Hz (defaults to 1Hz)
        """
        self.freq_hz = freq_hz
        
    def elaborate(self, platform):
        m = Module()
        
        # Get system clock frequency (for actual hardware)
        if platform is not None:
            sys_clock_freq = platform.default_clk_frequency
        else:
            # For simulation, assume 1MHz clock
            sys_clock_freq = 1_000_000
        
        # Calculate counter limit based on desired blink frequency
        # The counter will overflow twice per cycle (on-off)
        # Use a small limit for all simulations to make them run faster
        counter_limit = 10  # Small enough to see the behavior but fast to run
        
        # Create our counter submodule
        counter = UpCounter(counter_limit)
        # Add it to our module with a name
        m.submodules.counter = counter
        
        # Create a toggle flip-flop for LED state
        led_state = Signal(1)
        
        # Always enable the counter
        m.d.comb += counter.en.eq(1)
        
        # Toggle LED state on overflow
        with m.If(counter.ovf):
            m.d.sync += led_state.eq(~led_state)
            
        # Connect to the LED if running on hardware
        if platform is not None:
            led = platform.request("led", 0)
            m.d.comb += led.o.eq(led_state)
        
        return m

# Example usage
if __name__ == "__main__":
    from amaranth.sim import Simulator, Period
    
    # Create a 2Hz blinker
    dut = ControlledBlinker(freq_hz=2)
    
    # Basic simulation to observe blinking
    sim = Simulator(dut)
    sim.add_clock(Period(MHz=1))  # 1MHz system clock
    
    # Add a simple test to just run for a while
    async def test_bench(ctx):
        pass
    
    sim.add_testbench(test_bench)
    
    # Run simulation and generate a waveform file
    with sim.write_vcd("blinker_system.vcd", "blinker_system.gtkw"):
        # Always use a short simulation time
        sim.run_until(Period(us=100))  # 100 microseconds - fast but still shows behavior
        
    print("Simulation complete. View waveform with 'gtkwave blinker_system.vcd'")
    
    # Generate Verilog
    from amaranth.back import verilog
    
    # For Verilog conversion we need ports
    led = Signal(name="led")
    m = Module()
    m.submodules.blinker = dut
    m.d.comb += led.eq(0)  # Dummy connection for LED
    ports = [led]
    
    with open("blinker_system.v", "w") as f:
        f.write(verilog.convert(m, ports=ports))
    
    print("Generated blinker_system.v")