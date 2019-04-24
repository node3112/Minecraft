import os
from terrain import BiomeGenerator
import globals as G

width = 79
height = 28

try:
    # Windows
    from msvcrt import getch


    class TerminalContext:
        def __enter__(self):
            pass
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
except ImportError:
    # Linux
    import sys, termios, tty, shutil


    class TerminalContext:
        def __enter__(self):
            self.fd = sys.stdin.fileno()
            self.old_settings = termios.tcgetattr(self.fd)
            new_settings = termios.tcgetattr(self.fd)
            new_settings[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON)
            new_settings[3] &= ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(self.fd, termios.TCSADRAIN, new_settings)
            # tty.setraw(sys.stdin.fileno())

        def __exit__(self, exc_type, exc_val, exc_tb):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


    def getch():
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        try:
            ch = sys.stdin.read(1)
        except KeyboardInterrupt:
            exit()
        return ch


    (width, height) = shutil.get_terminal_size((width, height))
    height -= 2

with open(os.path.join(G.game_dir, "world", "seed"), "r") as f:
    SEED = f.read()

biome_generator = BiomeGenerator(SEED)
current_x = 0
current_z = 0

DESERT, PLAINS, MOUNTAINS, SNOW, FOREST = list(range(5))
letters = ["D","P","M","S","F"]

print("Okay, click on the console window again, then use the arrow keys.")

with TerminalContext() as t:
    while True:
        key = getch()
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if key == "w":
            current_z -= 5
        elif key == "d":
            current_x += 5
        elif key == "s":
            current_z += 5
        elif key == "a":
            current_x -= 5
        elif key == "q":
            exit()
        string = ""
        for y in range(current_z, current_z + height):
            for x in range(current_x, current_x + width):
                string += letters[biome_generator.get_biome_type(x, y)]
            string += "\n"
        print(string + "Current position: (%s-%s %s-%s)" % (
            current_x * 8,
            (current_x + width) * 8,
            current_z * 8,
            (current_z + height) * 8),
              )
