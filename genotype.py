from typing import Union, List, Tuple


mul_table = {
    0b0000: ((0b00, 1.0),),
    0b0001: ((0b01, 0.5), (0b00, 0.5),),
    0b0011: ((0b01, 1.0),),
    0b0101: ((0b11, 0.25), (0b01, 0.50), (0b00, 0.25),),
    0b0111: ((0b11, 0.5), (0b01, 0.5),),
    0b1111: ((0b11, 1.0),)
}


def gt_mul(gt1, gt2):
    if gt1 <= gt2:
        return mul_table[(gt1<<2)|gt2]
    else:
        return mul_table[(gt2<<2)|gt1]



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

    def multiply(self, gt1: Union[str, int], gt2: Union[str, int]) -> List[Tuple[int, float]]:
        if isinstance(gt1, str):
            gt1 = self.numeric(gt1)

        if isinstance(gt2, str):
            gt2 = self.numeric(gt2)

        ret = []
        a = [()] * (self._num + 1)
        for i in range(self._num):
            if i != 0:
                gt1 = gt1 >> 2
                gt2 = gt2 >> 2
            a[self._num-i-1] = gt_mul((gt1 & 0b11), (gt2 & 0b11))

        st = []
        i = 0
        gt_n, gt_p = (0b0, 1.0)
        while True:
            l = len(st)
            if i < len(a[l]):
                cur_n, cur_p = a[l][i]
                st.append((i, gt_n, gt_p))
                i = 0
                gt_n = (gt_n << 2) | cur_n
                gt_p = gt_p * cur_p
            else:
                if l == 0:
                    break

                if len(st) == len(a) - 1:
                    ret.append((gt_n, gt_p))

                i, gt_n, gt_p = st.pop()
                i = i + 1

        return ret



if __name__ == '__main__':
    g = Genotype('ryWs')
    print(g.alpha(0xd4))
    print(hex(g.numeric('RRYYWwss')))
    gt1, gt2 = 'rryyWwss', 'rryyWwss'
    res = g.multiply(gt1, gt2)
    print(gt1, gt2)
    for gt_n, gt_p in res:
        print(g.alpha(gt_n), gt_p)
