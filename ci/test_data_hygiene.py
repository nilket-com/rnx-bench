import unittest

class DataHygiene(unittest.TestCase):
	def check_data(self, files, entries=None, baseline=None, exemptions=None):
		from data_hygiene import check
		return check(files, {'entries':entries or {}, 'duplicate_exemptions':exemptions or {}}, baseline or {})

	def test_thresholds_and_config(self):
		self.assertFalse(self.check_data({'a.json':b'x'*16384}))
		self.assertTrue(self.check_data({'a.json':b'x'*16385}))
		self.assertFalse(self.check_data({'Cargo.lock':b'x'*20000}))
		entry={'class':'source-configuration','reason':'reviewed policy','max_bytes':20000}
		self.assertFalse(self.check_data({'policy.json':b'x'*20000},{'policy.json':entry}))

	def test_live_loader_and_dead_reference(self):
		data=b'x'*20000;expression='Path("fixtures").glob("*.json")'
		entry={'class':'live-fixture','reason':'fixture loader','max_bytes':20000,'consumer':{'path':'reader.py','expression':expression}}
		self.assertFalse(self.check_data({'a.json':data,'reader.py':expression.encode()},{'a.json':entry}))
		self.assertTrue(self.check_data({'a.json':data,'README.md':expression.encode()},{'a.json':entry}))
		entry['consumer']['expression']='NAME = "a.json"'
		self.assertTrue(self.check_data({'a.json':data,'reader.py':b'NAME = "a.json"'},{'a.json':entry}))

	def test_new_megabyte_and_growth(self):
		files={'a.json':b'x'*1048576};entry={'class':'reviewed-retention','reason':'fixture retained','max_bytes':1048576}
		self.assertTrue(self.check_data(files,{'a.json':entry}))
		self.assertFalse(self.check_data(files,{'a.json':entry},baseline={'a.json':1048576}))
		self.assertTrue(self.check_data(files,{'a.json':entry},baseline={'a.json':1024}))
		entry['allow_large']=True
		self.assertFalse(self.check_data(files,{'a.json':entry}))
		entry['max_bytes']-=1
		self.assertTrue(self.check_data(files,{'a.json':entry}))

	def test_duplicate_exact_exemption(self):
		import hashlib
		data=b'x'*4096;files={'a.json':data,'b.json':data};sha=hashlib.sha256(data).hexdigest()
		self.assertTrue(self.check_data(files))
		exempt={sha:{'paths':['a.json','b.json'],'reason':'distinct pinned corpus cases'}}
		self.assertFalse(self.check_data(files,exemptions=exempt))
		files['c.json']=data
		self.assertTrue(self.check_data(files,exemptions=exempt))
		self.assertFalse(self.check_data({'a.rs':data,'b.rs':data}))
