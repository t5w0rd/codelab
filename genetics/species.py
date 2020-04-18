from .genotype import Genotype
from typing import Dict, Union, List, Tuple


def species_class(name: str, base_genotype: Genotype, base_phenotype: Dict[int, str]):
    class _Species:
        def __init__(self, genotype: Union[int, str]):
            if isinstance(genotype, str):
                genotype = base_genotype.numeric(genotype)
            self._gt = genotype

        @property
        def genotype(self):
            return base_genotype.alpha(self._gt)

        @property
        def genotype_n(self):
            return self._gt

        @property
        def phenotype(self):
            return base_phenotype[self._gt]

        def cross(self, l) -> List[Tuple]:
            children = base_genotype.multiply(self.genotype_n, l.genotype_n)
            cls = type(self)
            ret = [(cls(gt_n), gt_p) for gt_n, gt_p in children]
            return ret

        def __mul__(self, rhs):
            return self.cross(rhs)

        def __repr__(self):
            #return '{}({})'.format(name, self.genotype_n)
            return '{}({}/{}/{})'.format(name, self.genotype, self.genotype_n, self.phenotype)

        def __str__(self):
            return '{}({}/{}/{})'.format(name, self.genotype, self.genotype_n, self.phenotype)

    _Species.__name__ = name
    return _Species


if __name__ == '__main__':
    gt = Genotype('ryWs')
    from .phenotype import rose
    Rose = species_class('Rose', gt, rose)

    r = Rose(0xc1)
    y = Rose(0x30)
    w = Rose(0x04)

    for l, p in r*r:
        print(l, p)

