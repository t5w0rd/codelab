from genotype import Genotype
from typing import Dict, Union, List, Tuple


class LivingFactory:
    def __init__(self, name: str, genotype: Genotype, phenotype: Dict[int, str]):
        self.name = name
        self.gt = genotype
        self.pt = phenotype

    def Living(self, gt: Union[int, str]):
        o = _Living(self, gt)
        return o


class _Living:
    def __init__(self, factory: LivingFactory, genotype: Union[int, str]):
        self._factory = factory
        if isinstance(genotype, str):
            genotype = self._factory.gt.numeric(genotype)
        self._gt = genotype

    @property
    def genotype(self):
        return self._factory.gt.alpha(self._gt)

    @property
    def genotype_n(self):
        return self._gt

    @property
    def phenotype(self):
        return self._factory.pt[self._gt]

    def cross(self, l) -> List[Tuple]:
        children = self._factory.gt.multiply(self.genotype_n, l.genotype_n)
        ret = ((self._factory.Living(gt_n), gt_p) for gt_n, gt_p in children)
        return ret

    def __mul__(self, rhs):
        return self.cross(rhs)

    def __repr__(self):
        return '{}({})'.format(self._factory.name, self.genotype_n)

    def __str__(self):
        return '{}({})'.format(self.phenotype, self.genotype)


if __name__ == '__main__':
    gt = Genotype('ryWs')
    from phenotype import rose
    f = LivingFactory('Rose', gt, rose)

    r = f.Living(0xc1)
    y = f.Living(0x30)
    w = f.Living(0x04)

    for l, p in r*r:
        print(l, p)

