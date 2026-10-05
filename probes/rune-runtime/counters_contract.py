"""Counter matrix and independently fixed fixture answers."""
CASES=[(m,None) for m in ['floor','empty-context','context','runtime']]+[(m,w) for m,w in [('compile','answer'),('run','empty'),('run','answer'),('run','numeric'),('run','strings'),('run','fib'),('phases','answer'),('reuse','answer'),('reuse','numeric'),('reuse','fib')]]
def identities():return {(base,m,w) for base in ('old','new') for m,w in CASES}
def expected_output(mode,work):
 if mode in ('floor','empty-context','context','runtime','compile'):return ''
 values={'empty':'','answer':'42\n','numeric':'3\n','strings':'208893\nitem:1|item:2|item:\nitem:19999|item:20000\n','fib':'196418\n'}
 return values[work]*(20 if mode=='reuse' else 1)
