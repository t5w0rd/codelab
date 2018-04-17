class Unit(object):
	"""docstring for Unit"""
	# MIN_LEVEL = 0
	MAX_LEVEL = 100
	MIN_HP = 10.0
	MAX_HP = 20.0
	MIN_ATK = 1.0
	MAX_ATK = 2.0
	MIN_AMR = 0.0
	MAX_AMR = 1.0

	def __init__(self, name, level = 0):
		super(Unit, self).__init__()
		self.name = name
		self.setLevel(level)
		self.hp = self.mhp

	def damagedBy(self, atk, unit, fake = False):
		atk = atk * 1.0  / (self.amr + 1.0)
		if not fake:
			self.hp = max(0, self.hp - atk)
		return atk

	def attack(self, unit, fake = False):
		atk = self.atk
		atk = unit.damagedBy(atk, self, fake)
		return atk

	def reset(self):
		self.hp = self.mhp

	def status(self):
		stat = {'mhp': self.mhp, 'hp': self.hp, 'atk': self.atk, 'amr': self.amr}
		return stat

	def setLevel(self, level):
		self.level = level
		self.mhp = self.level * (Unit.MAX_HP - Unit.MIN_HP) / Unit.MAX_LEVEL + Unit.MIN_HP
		self.atk = self.level * (Unit.MAX_ATK - Unit.MIN_ATK) / Unit.MAX_LEVEL + Unit.MIN_ATK
		self.amr = self.level * (Unit.MAX_AMR - Unit.MIN_AMR) / Unit.MAX_LEVEL + Unit.MIN_AMR
	

def battle(u1, u2):
	rd = 1
	while u1.hp > 0 and u2.hp > 0:
		ohp1 = u1.hp
		ohp2 = u2.hp
		atk1 = u1.attack(u2)
		atk2 = u2.attack(u1)
		print 'R%d\t%s(Lv%d) %.2g/%.2g  -%.2g    %s(Lv%d) %.2g/%.2g  -%.2g' % (rd, u1.name, u1.level, ohp1, u1.mhp, atk2, u2.name, u2.level, ohp2, u2.mhp, atk1)
		rd += 1

	def printResult(u):
		if u.hp > 0:
			aod = 'ALIVE'
		else:
			aod = 'DEAD'
		print '%s(Lv%d) %.2g/%.2g is %s' % (u.name, u.level, u.hp, u.mhp, aod)

	printResult(u1)
	printResult(u2)

