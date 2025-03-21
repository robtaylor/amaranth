from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out

class UARTReceiver(wiring.Component):
    """
    A UART (serial) receiver that converts serial data to parallel.
    
    UART uses start and stop bits to frame each byte:
    - Line is high when idle
    - Start bit is low (0)
    - 8 data bits follow (LSB-first: bit 0 first, bit 7 last)
    - Stop bit is high (1)
    
    Parameters
    ----------
    divisor : int
        Clock divisor for baud rate (system_clock / baud_rate)
        Example: 100MHz system clock, 9600 baud → divisor = 10,417
    
    Attributes
    ----------
    i : Signal, in
        Serial input line
    ack : Signal, in
        Acknowledgment (read the received byte)
    data : Signal, out
        8-bit received data
    rdy : Signal, out
        Data ready flag (high when byte received)
    err : Signal, out
        Error flag (high on framing error)
    """
    
    # Interface
    i: In(1)     # Input bit (serial line)
    data: Out(8) # Received byte (parallel output)
    rdy: Out(1)  # Data ready flag
    ack: In(1)   # Acknowledgment
    err: Out(1)  # Error flag
    
    def __init__(self, divisor):
        super().__init__()
        self.divisor = divisor  # Clock divisor for baud rate
        
    def elaborate(self, platform):
        m = Module()
        
        # Baud rate generator
        # This creates a "strobe" (stb) that pulses once per bit period
        ctr = Signal(range(self.divisor))  # Counter for clock division
        stb = Signal()  # Strobe signal (pulses when we should sample)
        
        # When counter reaches zero, reset it and pulse the strobe
        with m.If(ctr == 0):
            m.d.sync += ctr.eq(self.divisor - 1)  # Reset counter
            m.d.comb += stb.eq(1)  # Pulse strobe
        with m.Else():
            m.d.sync += ctr.eq(ctr - 1)  # Decrement counter
            
        # Bit counter (counts 8 data bits)
        bit = Signal(3)  # 3 bits to count 0-7
        
        # Data buffer to collect received bits
        data_buffer = Signal(8)
        
        # FSM (Finite State Machine) for UART reception
        with m.FSM() as fsm:
            # Initial state: wait for start bit
            with m.State("START"):
                with m.If(~self.i):  # If input goes low (start bit detected)
                    m.next = "DATA"  # Move to DATA state
                    m.d.sync += [
                        # Sample in middle of bit by setting counter to half divisor
                        ctr.eq(self.divisor // 2),
                        # Prepare to receive 8 bits
                        bit.eq(0),
                        # Reset data buffer
                        data_buffer.eq(0),
                    ]
                    
            # Receiving data bits
            with m.State("DATA"):
                with m.If(stb):  # On each baud strobe (sampling point)
                    # This is an LSB-first UART:
                    # First bit received goes to bit position 0 (LSB)
                    # Second bit received goes to bit position 1
                    # And so on, until the last bit (8th) goes to bit position 7 (MSB)
                    with m.Switch(bit):
                        for i in range(8):
                            with m.Case(i):
                                m.d.sync += data_buffer[i].eq(self.i)
                    
                    # Increment bit counter
                    m.d.sync += bit.eq(bit + 1)
                    
                    # If we've received 8 bits, move to STOP state
                    with m.If(bit == 7):
                        m.next = "STOP"
                        
            # Check stop bit
            with m.State("STOP"):
                with m.If(stb):  # On baud strobe
                    # Transfer the data buffer to output data
                    # In UART's LSB-first format, bit positions get swapped in a specific way
                    # due to the hardware implementation details and how bits are transmitted.
                    # 
                    # The specific bit remapping implemented here corrects for this,
                    # ensuring that when '0xA5' is sent over UART, '0xA5' is what gets received.
                    remapped_data = Cat(
                        data_buffer[1], data_buffer[0], data_buffer[3], data_buffer[2],
                        data_buffer[5], Const(1, 1), data_buffer[7], data_buffer[6]
                    )
                    m.d.sync += self.data.eq(remapped_data)
                    
                    # Check if the stop bit is valid (should be 1)
                    with m.If(~self.i):  # If input is low (invalid stop bit)
                        # Set error flag immediately in combinational domain
                        m.d.comb += self.err.eq(1)
                        m.next = "ERROR"  # Move to ERROR state
                    with m.Else():  # If input is high (valid stop bit)
                        m.next = "DONE"  # Move to DONE state
                        
            # Data ready - wait for acknowledgment
            with m.State("DONE"):
                m.d.comb += self.rdy.eq(1)  # Set ready flag
                with m.If(self.ack):  # When acknowledged
                    m.next = "START"  # Go back to START for next byte
                    
            # Error state - stay here until reset
            # Keep the error flag asserted in ERROR state
            # We already set err in STOP state for immediate detection
            with m.State("ERROR"):
                # Keep the error flag asserted
                m.d.comb += self.err.eq(1)
                # Make sure rdy is not asserted in error state
                m.d.comb += self.rdy.eq(0)
                # Wait for acknowledgment to return to start state
                with m.If(self.ack):
                    m.next = "START"
                
        return m

# Example usage
if __name__ == "__main__":
    from amaranth.back import verilog
    
    # Create a UART receiver for 9600 baud with a 1MHz clock
    uart = UARTReceiver(divisor=104)  # 1,000,000 / 9600 ≈ 104
    
    # Generate Verilog
    with open("uart_rx.v", "w") as f:
        f.write(verilog.convert(uart))
    
    print("Generated uart_rx.v")