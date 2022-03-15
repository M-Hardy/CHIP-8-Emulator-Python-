import random
import sys
import pyglet

#LOGGING = False

KEY_MAP = { pyglet.window.key._1: 0x1,
            pyglet.window.key._2: 0x2,
            pyglet.window.key._3: 0x3,
            pyglet.window.key._4: 0xc,
            pyglet.window.key.Q: 0x4,
            pyglet.window.key.W: 0x5,
            pyglet.window.key.E: 0x6,
            pyglet.window.key.R: 0xd,
            pyglet.window.key.A: 0x7,
            pyglet.window.key.S: 0x8,
            pyglet.window.key.D: 0x9,
            pyglet.window.key.F: 0xe,
            pyglet.window.key.Z: 0xa,
            pyglet.window.key.X: 0,
            pyglet.window.key.C: 0xb,
            pyglet.window.key.V: 0xf
}

class cpu (pyglet.window.Window):
    memory = [0] * 4096                # memory: max 4096 bytes
    gpio = [0] * 16                    # registers: max 16 8-bit registers
    display_buffer = [0] * 64 * 32     # 64*32 display
    stack = []                         # stack pointer - includes address of topmost 
                                            # stack element, has at most 16 elements in it at 
                                            # any given time (can ignore 16 element limitation
                                            # with python list - can just pop/append at will)
    key_inputs = [0] * 16              #input is 16-button keyboard
    opcode = 0
    index = 0                          #16-bit index register
    delay_timer = 0                    #timer register 1: delays
    sound_timer = 0                    #timer register 2: sound
    should_draw = False
    pc = 0                             #16-bit program counter 
    vx = 0
    vy = 0
    pixel = pyglet.image.load('pixel.png')
    buzz = pyglet.resource.media('buzz.wav', streaming=False)
    logging = False
    
    funcmap = {}               
    fonts = [   0xF0, 0x90, 0x90, 0x90, 0xF0, # Character: 0
                0x20, 0x60, 0x20, 0x20, 0x70, # Character: 1
                0xF0, 0x10, 0xF0, 0x80, 0xF0, # Character: 2
                0xF0, 0x10, 0xF0, 0x10, 0xF0, # Character: 3
                0x90, 0x90, 0xF0, 0x10, 0x10, # Character: 4
                0xF0, 0x80, 0xF0, 0x10, 0xF0, # Character: 5
                0xF0, 0x80, 0xF0, 0x90, 0xF0, # Character: 6
                0xF0, 0x10, 0x20, 0x40, 0x40, # Character: 7
                0xF0, 0x90, 0xF0, 0x90, 0xF0, # Character: 8
                0xF0, 0x90, 0xF0, 0x10, 0xF0, # Character: 9
                0xF0, 0x90, 0xF0, 0x90, 0x90, # Character: A
                0xE0, 0x90, 0xE0, 0x90, 0xE0, # Character: B
                0xF0, 0x80, 0x80, 0x80, 0xF0, # Character: C
                0xE0, 0x90, 0x90, 0x90, 0xE0, # Character: D
                0xF0, 0x80, 0xF0, 0x80, 0xF0, # Character: E
                0xF0, 0x80, 0xF0, 0x80, 0x80  # Character: F
            ]

    def log(self, msg):
        if self.logging == True:
            print(msg) 


    def _0ZZZ(self):
        extracted_op = self.opcode & 0xf0ff
        try:
            self.funcmap[extracted_op]()
        except:
            print("Unknown instruction: %X" % self.opcode)

    def _0ZZ0(self):                            
        self.log("Clears the screen")
        self.display_buffer = [0]*64*32 
        self.should_draw = True

    def _0ZZE(self):
        self.log("Returns from subroutine")
        self.pc = self.stack.pop()

    def _1ZZZ(self):
        self.log("Jumps to address NNN.")
        self.pc = self.opcode & 0x0fff

    def _2ZZZ(self):
        self.log("Call subroutine at nnn")
        self.stack.append(self.pc)
        self.pc = self.opcode & 0x0fff

    def _3ZZZ(self):
        self.log("Skip next instruction if Vx = kk")
        if self.gpio[self.vx] == (self.opcode & 0x00ff):
            self.pc += 2

    def _4ZZZ(self):
        self.log("Skips the next instruction if VX doesn't equal NN.")
        if self.gpio[self.vx] != (self.opcode & 0x00ff):
            self.pc += 2

    def _5ZZZ(self):
        self.log("Skips the next instruction if VX equals VY.")
        if self.gpio[self.vx] == self.gpio[self.vy]:
            self.pc += 2

    def _6ZZZ(self):
        self.log("Set Vx = kk")
        self.gpio[self.vx] = self.opcode & 0x00ff
    
    def _7ZZZ(self):
        self.log("Set Vx = Vx + kk")
        self.gpio[self.vx] += self.opcode & 0x0ff
    
    def _8ZZZ(self):
        extracted_op = self.opcode & 0xf00f
        extracted_op += 0xff0
        try:
            self.funcmap[extracted_op]()
        except:
            print("Unknown instruction: %X" % self.opcode)
    
    def _8ZZ0(self):
        self.log("Set Vx = Vy")
        self.gpio[self.vx] = self.gpio[self.vy]

    def _8ZZ1(self):
        self.log("Set Vx OR Vy")
        self.gpio[self.vx] |= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ2(self):
        self.log("Set Vx = Vx AND Vy")
        self.gpio[self.vx] &= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ3(self):
        self.log("Set Vx = Vx XOR Vy")
        self.gpio[self.vx] ^= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ4(self):
        self.log("Adds VY to VX. VF is set to 1 when there's a carry,\
            and to 0 when there isn't.")
        if self.gpio[self.vx] + self.gpio[self.vy] > 0xff:
            self.gpio[0xf] = 1
        else:
            self.gpio[0xf] = 0
        self.gpio[self.vx] += self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ5(self):
        self.log("VY is subtracted from VX. VF is set to 0 when there's\
            a borrow, and 1 when there isn't.")
        if self.gpio[self.vy] > self.gpio[self.vx]:
            self.gpio[0xf] = 0
        else:
            self.gpio[0xf] = 1
        self.gpio[self.vx] -= self.gpio[self.vy]
        self.gpio[self.vx] &= 0xff

    def _8ZZ6(self):
        self.log("Set Vx = Vx SHR 1")
        self.gpio[0xf] = self.gpio[self.vx] & 0x0001
        self.gpio[self.vx] >> 1

    def _8ZZ7(self):
        self.log("Set Vx = Vy - Vx, set VF = NOT borrow")
        if self.gpio[self.vx] > self.gpio[self.vy]:
            self.gpio[0xf] = 0
        else:
            self.gpio[0xf] = 1
        self.gpio[self.vx] = self.gpio[self.vy] - self.gpio[self.vx]
        self.gpio[self.vx] &= 0xff

    def _8ZZE(self):
        self.log("Set Vx = Vx SHL 1")
        self.gpio[0xf] = (self.gpio[self.vx] & 0x00f0) >> 7
        self.gpio[self.vx] << 1
        self.gpio[self.vx] &= 0xff

    def _9ZZZ(self):
        self.log("Skip next instruction if Vx != Vy")
        if self.gpio[self.vx] != self.gpio[self.vy]:
            self.pc += 2

    def _AZZZ(self):
        self.log("Set I = nnn")
        self.index = self.opcode & 0x0fff

    def _BZZZ(self):
        self.log("Jump to location nnn + V0")
        self.pc = (self.opcode & 0x0fff) + self.gpio[0x0]

    def _CZZZ(self):
        self.log("Set Vx = random byte AND kk")
        rand = random.randrange(0, 256)
        self.gpio[self.vx] = (self.opcode & 0x00ff) & rand
        self.gpio[self.vx] &= 0xff

    def _DZZZ(self):
        self.log("Draw a sprite")
        self.gpio[0xf] = 0
        x = self.gpio[self.vx] & 0xff
        y = self.gpio[self.vy] & 0xff
        height = self.opcode & 0x000f
        row = 0
        while row < height:
            curr_row = self.memory[row + self.index]
            pixel_offset = 0
            while pixel_offset < 8:
                loc = x + pixel_offset + ((y + row) * 64)
                pixel_offset += 1
                if (y + row) >= 32 or (x + pixel_offset - 1) >= 64:
                    continue #ignore pixels outside the screen
                mask = 1 << 8-pixel_offset
                curr_pixel = (curr_row & mask) >>(8-pixel_offset)
                self.display_buffer[loc] ^= curr_pixel
                if self.display_buffer[loc] == 0:
                    self.gpio[0xf] = 1
                else:
                    self.gpio[0xf] = 0
            row += 1
        self.should_draw = True

    def _EZZZ(self):
        extracted_op = self.opcode & 0xf00f
        try:
            self.funcmap[extracted_op]()
        except:
            print("Unknown instruction: %X" % self.opcode)

    def _EZZE(self):
        self.log("Skips the next instruction if the key in VX is pressed.")
        key = self.gpio[self.vx] & 0xf
        if self.key_inputs[key] == 1:
            self.pc += 2

    def _EZZ1(self):
        self.log("Skips the next instruction if the key stored in VX isn't pressed.")
        key = self.gpio[self.vx] & 0xf
        if self.key_inputs[key] == 0:
            self.pc += 2
   
    def _FZZZ(self):
        extracted_op = self.opcode & 0xf0ff
        try:
            self.funcmap[extracted_op]()
        except:
            print("Unknown instruction: %X" % self.opcode)

    def _FZ07(self):
        self.log("Set Vx = delay timer value")
        self.gpio[self.vx] = self.delay_timer
    
    def _FZ0A(self):
        self.log("Wait for a key press, store the value of the key in Vx")
        key = self.get_key()
        if key >= 0:
            self.gpio[self.vx] = key
        else:
            self.pc -= 2

    def _FZ15(self):
        self.log("Set delay timer = Vx")
        self.delay_timer = self.gpio[self.vx]
    
    def _FZ18(self):
        self.log("Set sound timer = Vx")
        self.sound_timer = self.gpio[self.vx]
    
    def _FZ1E(self):
        self.log("Set I = I + Vx")
        self.index += self.gpio[self.vx]
        if self.index > 0xfff:
            self.gpio[0xf] = 1
            self.index &= 0xfff
        else:
            self.gpio[0xf] = 0
    
    def _FZ29(self):
        self.log("Set index to point to a character")
        self.index = (5*(self.gpio[self.vx])) & 0xff

    def _FZ33(self):
        self.memory[self.index] =  self.gpio[self.vx] // 100
        self.memory[self.index + 1] = (self.gpio[self.vx] // 10) % 10
        self.memory[self.index + 2] = self.gpio[self.vx] % 10

    def _FZ55(self):
        self.log("Store registers V0 through Vx in memory starting at location I")
        i = 0
        while  i <= self.vx:
            self.memory[self.index + i] = self.gpio[i]
            i += 1
        self.index += self.vx + 1

    def _FZ65(self):
        self.log("Read registers V0 through Vx from memory starting at location I")
        i = 0
        while i <= self.vx:
            self.gpio[i] = self.memory[self.index + i]
            i += 1
        self.index += self.vx + 1
        
    def __init__(self, *args, **kwargs):
        super(cpu, self).__init__(*args, **kwargs)
        self.funcmap = {0x0000: self._0ZZZ,
                        0x00e0: self._0ZZ0,
                        0x00ee: self._0ZZE,
                        0x1000: self._1ZZZ,
                        0x2000: self._2ZZZ,
                        0x3000: self._3ZZZ,
                        0x4000: self._4ZZZ,
                        0x5000: self._5ZZZ,
                        0x6000: self._6ZZZ,
                        0x7000: self._7ZZZ,
                        0x8000: self._8ZZZ,
                        0x8FF0: self._8ZZ0,
                        0x8FF1: self._8ZZ1,
                        0x8FF2: self._8ZZ2,
                        0x8FF3: self._8ZZ3,
                        0x8FF4: self._8ZZ4,
                        0x8FF5: self._8ZZ5,
                        0x8FF6: self._8ZZ6,
                        0x8FF7: self._8ZZ7,
                        0x8FFE: self._8ZZE,
                        0x9000: self._9ZZZ,
                        0xA000: self._AZZZ,
                        0xB000: self._BZZZ,
                        0xC000: self._CZZZ,
                        0xD000: self._DZZZ,
                        0xE000: self._EZZZ,
                        0xE00E: self._EZZE,
                        0xE001: self._EZZ1,
                        0xF000: self._FZZZ,
                        0xF007: self._FZ07,
                        0xF00A: self._FZ0A,
                        0xF015: self._FZ15,
                        0xF018: self._FZ18,
                        0xF01E: self._FZ1E,
                        0xF029: self._FZ29,
                        0xF033: self._FZ33,
                        0xF055: self._FZ55,
                        0xF065: self._FZ65
                    }

    def initialize(self):
        self.clear()
        self.memory = [0] * 4096                
        self.gpio = [0] * 16                    
        self.display_buffer = [0] * 64 * 32     
        self.stack = []                                                                                                                                                               
        self.key_inputs = [0] * 16              
        self.opcode = 0
        self.index = 0                          
        self.delay_timer = 0                    
        self.sound_timer = 0                    
        self.should_draw = False
        self.key_wait = False
        self.pc = 0x200                 

        i = 0
        while i < 80:                           # load 80-char font set
            self.memory[i] = self.fonts[i]      # 80 is upper bound because each char is 5 bytes
            i += 1                              # and there are 16 hex characters (80/5 = 16)      
                                                # basically we storing each hex char from our class
                                                # fonts dictionary to memory  

    def load_rom(self, rom_path):
        self.log("Loading %s..." % rom_path)
        binary = open(rom_path, "rb").read()    # "rb" argument = "read in binary mode" -> binary mode = images
        i = 0
        while i < len(binary):
            self.memory[i + 0x200] = binary[i]           # ord(binary[i])
            i += 1

    def cycle(self):
        self.opcode = (self.memory[self.pc] << 8) | self.memory[self.pc + 1]

        self.vx = (self.opcode & 0x0f00) >> 8   # 1. store 2nd and 3rd nibbles of opcode into
        self.vy = (self.opcode & 0x00f0) >> 4   #    registers vx and vy -> 2nd and 3rd nibbles in opcode 
                                                #    usually store the associated general purpose register(s)
                                                #    that the opcode uses to execute its instruction
                                                #    we will use these nibbles as indexes for self.gpio
                                                #    (e.g. self.gpio[self.vx]), which is a class variable of 
                                                #    our cpu that contains all 16 of our 8-bit general purpose 
                                                #    registers to access the correct register

        self.pc += 2                            # 2. increment program counter 2 bytes = 16 bits =
                                                #    default chip 8 instruction size is 16 bits)

        extracted_op = self.opcode & 0xf000     # 3. check ops, lookup op and execute
        try:
            self.funcmap[extracted_op]()        #    call the associated method for the opcode
        except:
            print("Unknown instruction: %X" % self.opcode)

        if self.delay_timer > 0:                #decrement timers
            self.delay_timer -= 1
        if self.sound_timer > 0:
            self.sound_timer -= 1
            if self.sound_timer == 0:           #play a sound with pyglet
                self.buzz.play()    
    
    def draw(self):
        if self.should_draw:                    #draw
            self.clear()
            i = 0
            while i < 2048:
                if self.display_buffer[i] == 1: #draw a square pixel
                    self.pixel.blit((i%64)*10, 310 - ((i/64)* 10))
                i += 1
        self.flip()
        self.should_draw = False
    
    def get_key(self):
        i = 0
        while i < 16:
            if self.key_inputs[i] == 1:
                return i
            i += 1
        return -1                               # key pressed is not valid input

    def on_key_press(self, symbol, modifiers):
        self.log("Key pressed: %r" % symbol)
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 1
            if self.key_wait:
                self.key_wait = False
        else:
            super(cpu, self).on_key_press(symbol, modifiers)

    def on_key_release(self, symbol, modifiers):
        self.log("Key released: %r" % symbol)
        if symbol in KEY_MAP.keys():
            self.key_inputs[KEY_MAP[symbol]] = 0

    def main(self):
        if len(sys.argv) <= 1 or len(sys.argv) > 3:
            print("Usage: python chip8.py <path to chip8 rom> <log>")
            print("     : <log> - if 'log' present, prints log messages to console")
            return
        if len(sys.argv) == 3:
            if sys.argv[2] == "log":
                self.logging = True  
        self.initialize()
        self.load_rom(sys.argv[1])
        while not self.has_exit:
            self.dispatch_events()
            self.cycle()
            self.draw()
        
###   BEGIN EMULATION     ###     
chip8emu = cpu(640, 320)
chip8emu.main()