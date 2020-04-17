
RoseType = {}

class Genotype:
    def __init__(self, zero_alpha: str):
        assert zero_alpha.isalpha()
        self._num = len(zero_alpha)
        
        bit2alpha = []
        alpha2bit = {}
        for i, c in enumerate(reversed(zero_alpha)):
            if c.islower():
                alpha_table = {0b00: c*2, 0b01: c.upper()+c, 0b11: c.upper()*2}
            else:
                alpha_table = {0b00: c*2, 0b01: c+c.lower(), 0b11: c.lower()*2}
            bit2alpha.append(alpha_table)
            for j, alpha in alpha_table.items():
                assert alpha, not alpha in alpha2bit
                alpha2bit[alpha] = j

        self._bit2alpha = bit2alpha
        self._alpha2bit = alpha2bit

    def alpha(self, numeric: int) -> str:
        a = []
        for i in range(self._num):
            if i != 0:
                numeric = numeric >> 2
            a.append(self._bit2alpha[i][numeric & 0b11])

        return ''.join(reversed(a))

    def numeric(self, alpha: str) -> int:
        n = 0
        for i in range(0, len(alpha), 2):
            if i != 0:
                n = n << 2
            n = n | self._alpha2bit[alpha[i:i+2]]
        
        return n


if __name__ == '__main__':
    g = Genotype('ryWs')
    print(g.alpha(0xd4))
    print(hex(g.numeric('RRYYWwss')))
